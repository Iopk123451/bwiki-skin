# -*- coding: utf-8 -*-
"""Create / update MediaWiki:BWIKI.css|BWIKI.js via api.php, then verify injection.

Usage:
  python -u q_custom_pages.py seed-probe   # write probe content
  python -u q_custom_pages.py seed-final   # write documented scaffold
  python -u q_custom_pages.py verify       # check DOM order + effects
"""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp import Cdp

# Credentials live in a git-ignored .secrets.env (see ftp_push._load_secrets).
try:
    from ftp_push import _load_secrets
    _load_secrets()
except Exception:
    pass

B = os.environ.get("MW_HOST", "https://opk-test.infinityfree.me").rstrip("/")
USER = os.environ.get("MW_USER", "")
PW = os.environ.get("MW_PASS", "")
if not USER or not PW:
    sys.exit("MW_USER / MW_PASS 未配置：请在 mw-build/.secrets.env 写入")

PROBE_CSS = "/* BWIKI skin custom CSS (probe) */\nbody { --bwiki-custom-probe: 1; }\n"
PROBE_JS = "/* BWIKI skin custom JS (probe) */\nwindow.__bwikiCustomJs = 'ok';\n"

FINAL_CSS = """/* ===================================================================
 * MediaWiki:BWIKI.css
 * -------------------------------------------------------------------
 * 只在 BWIKI 皮肤（skin=bwiki）下生效，加载位置在
 * bundle/*.css -> skin.css -> tune.css 之后（inline <style>），
 * 因此同特异性规则可以直接覆盖皮肤样式，不必加 !important。
 *
 * 适合放：站点级内容区样式、模板配套样式、信息框配色等。
 * 不适合放：皮肤自身的布局修复（那些改动请走 resources/tune.css，
 *           并递增 HookHandler::BUNDLE_VERSION）。
 *
 * 注意：登录 / 创建账号 / 参数设置等受限页面不会应用本页样式。
 * =================================================================== */

/* 在此下方书写你的样式 */
"""

FINAL_JS = """/* ===================================================================
 * MediaWiki:BWIKI.js
 * -------------------------------------------------------------------
 * 只在 BWIKI 皮肤下执行，且延迟到 mediawiki.util 与 jQuery 就绪之后，
 * 因此可以直接使用 $ 和 mw.* 助手。
 *
 * 适合放：站点级小交互（返回顶部、外链新窗口、信息框折叠等）。
 * 不适合放：抽屉/下拉/吸顶等皮肤自身交互（那些在 resources/skin.js）。
 * =================================================================== */

/* 在此下方书写你的代码 */
"""

EDIT_JS = """
(async () => {
  const api = %s + '/api.php';
  const tok = await (await fetch(api + '?action=query&meta=tokens&type=csrf&format=json', {credentials:'same-origin'})).json();
  const out = [];
  const edits = %s;
  for (const e of edits) {
    const body = new URLSearchParams({action:'edit', title:e.title, text:e.text,
      summary:e.summary, token: tok.query.tokens.csrftoken, format:'json',
      bot:'1', watchlist:'nochange'});
    const r = await (await fetch(api, {method:'POST', body, credentials:'same-origin'})).json();
    out.push({title:e.title, result: r.edit ? {res:r.edit.result, newrev:!!r.edit.newrevid, oldrev:!!r.edit.oldrevid} : r});
  }
  return JSON.stringify(out);
})()
"""

VERIFY_JS = """
(async () => {
  // inline <style>/<script> position relative to skin stylesheets
  const head = Array.from(document.head.children);
  const idx = (pred) => head.findIndex(pred);
  const tune = idx(el => el.tagName === 'LINK' && el.href.indexOf('tune.css') >= 0);
  const skin = idx(el => el.tagName === 'LINK' && el.href.indexOf('skin.css') >= 0);
  const inlineStyles = head.filter(el => el.tagName === 'STYLE' && el.textContent.indexOf('BWIKI.css') >= 0).length;
  const customJs = head.filter(el => el.tagName === 'SCRIPT' && el.textContent.indexOf('BWIKI.js') >= 0).length;
  const probeVar = getComputedStyle(document.body).getPropertyValue('--bwiki-custom-probe').trim();
  const cssHrefs = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(l => l.href.split('/').pop().slice(0, 46));
  return JSON.stringify({
    headLen: head.length, tuneIdx: tune, skinIdx: skin,
    inlineStyleBlocks: inlineStyles, inlineScriptBlocks: customJs,
    probeVar: probeVar, jsFlag: window.__bwikiCustomJs || null,
    stylesheets: cssHrefs,
    ver: (document.querySelector('link[href*="tune.css"]') || {}).href || ''
  }, null, 1);
})()
"""


def session():
    c = Cdp(port=9886, url=B + "/index.php?title=%E9%A6%96%E9%A1%B5", width=1280, height=900).start()
    for _ in range(25):
        t, _ = c.js("document.title")
        if t:
            return c
        time.sleep(1.5)
        c.reload(wait=3)
    return c


def login(c):
    js = """
(async () => {
  const api = %s + '/api.php';
  const t = await (await fetch(api + '?action=query&meta=tokens&type=login&format=json', {credentials:'same-origin'})).json();
  const body = new URLSearchParams({action:'clientlogin', username:%s, password:%s,
    logintoken:t.query.tokens.logintoken, loginreturnurl:%s + '/', format:'json'});
  const r = await (await fetch(api, {method:'POST', body, credentials:'same-origin'})).json();
  return JSON.stringify(r.clientlogin || r);
})()
""" % (json.dumps(B), json.dumps(USER), json.dumps(PW), json.dumps(B))
    print("LOGIN:", c.evalb64(js)[0])


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "verify"
    c = session()
    try:
        if mode == "verify":
            c.goto(B + "/index.php?title=%E9%A6%96%E9%A1%B5", wait=7)
            time.sleep(2)
            print(c.evalb64(VERIFY_JS)[0])
            return
        login(c)
        if mode == "seed-probe":
            edits = [
                {"title": "MediaWiki:BWIKI.css", "text": PROBE_CSS, "summary": "BWIKI custom CSS probe"},
                {"title": "MediaWiki:BWIKI.js", "text": PROBE_JS, "summary": "BWIKI custom JS probe"},
            ]
        else:
            edits = [
                {"title": "MediaWiki:BWIKI.css", "text": FINAL_CSS, "summary": "BWIKI 自定义样式挂载点（说明页）"},
                {"title": "MediaWiki:BWIKI.js", "text": FINAL_JS, "summary": "BWIKI 自定义脚本挂载点（说明页）"},
            ]
        print(c.evalb64(EDIT_JS % (json.dumps(B), json.dumps(edits)))[0])
    finally:
        c.close()


if __name__ == "__main__":
    main()

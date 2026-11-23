#!/usr/bin/env python3
"""把 BWIKI 官方样式包（从 wiki.biligame.com/wdjs/1145 抓取）本地化进皮肤资源目录。

- 校验下载资源有效性
- 生成源站已 403 的老图标的等效 SVG
- 重写 CSS 内 url() 为自托管绝对路径
"""
import os
import re
import shutil

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ref1145')
SKIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'BWIKI')
BUNDLE = os.path.join(SKIN, 'resources', 'bundle')
IMG = os.path.join(BUNDLE, 'img')
FONTS = os.path.join(BUNDLE, 'fonts')

os.makedirs(IMG, exist_ok=True)
os.makedirs(FONTS, exist_ok=True)

BASE_IMG = '/skins/BWIKI/resources/bundle/img'
BASE_FONT = '/skins/BWIKI/resources/bundle/fonts'

# ---------------------------------------------------------------- 图标生成
STAR = '<path d="M8 1.2l2.1 4.3 4.7.7-3.4 3.3.8 4.7L8 11.9l-4.2 2.3.8-4.7L1.2 6.2l4.7-.7z" fill="{fill}" stroke="{stroke}" stroke-width="0.6"/>'


def svg_star(fill, stroke):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">'
            + STAR.format(fill=fill, stroke=stroke) + '</svg>')


def make_icons():
    icons = {}

    def wrap(body, size='16', vb='0 0 16 16'):
        return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s" width="%s" height="%s">%s</svg>'
                % (vb, size, size, body))

    icons['search-ltr.svg'] = wrap(
        '<path d="M10.6 9.4a5 5 0 1 0-1.2 1.2l3.6 3.6a.85.85 0 0 0 1.2-1.2z" fill="#5f6b7a"/>'
        '<circle cx="6.6" cy="6.6" r="4.2" fill="none" stroke="#5f6b7a" stroke-width="1.6"/>')
    icons['magnify-clip-ltr.svg'] = icons['search-ltr.svg']
    icons['magnify-clip-rtl.svg'] = icons['search-ltr.svg']
    icons['search-close.svg'] = wrap(
        '<path d="M4 4l8 8M12 4l-8 8" stroke="#9099a4" stroke-width="1.8" fill="none" stroke-linecap="round"/>')
    icons['external-link-ltr-icon.svg'] = wrap(
        '<path d="M6.5 2.5H3.2A1.2 1.2 0 0 0 2 3.7v9.1a1.2 1.2 0 0 0 1.2 1.2h9.1a1.2 1.2 0 0 0 1.2-1.2V9.5" '
        'fill="none" stroke="#5f6b7a" stroke-width="1.3"/>'
        '<path d="M9.5 2h4.5v4.5M14 2L8 8" fill="none" stroke="#5f6b7a" stroke-width="1.3"/>')
    icons['tab-break.svg'] = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 24" width="1" height="24">'
                              '<rect width="1" height="24" fill="#c8c9ca"/></svg>')
    icons['portal-break.svg'] = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 28" width="1" height="28">'
                                 '<rect width="1" height="28" fill="#e3e5e8"/></svg>')
    icons['tab-normal-fade.svg'] = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 34" width="1" height="34">'
                                    '<rect width="1" height="34" fill="#f6f7f8"/></svg>')
    icons['tab-current-fade.svg'] = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 34" width="1" height="34">'
                                     '<rect width="1" height="34" fill="#ffffff"/></svg>')
    icons['page-fade.svg'] = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 6 90" width="6" height="90">'
                              '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0">'
                              '<stop offset="0" stop-color="#ffffff" stop-opacity="0"/>'
                              '<stop offset="1" stop-color="#ffffff" stop-opacity="1"/></linearGradient></defs>'
                              '<rect width="6" height="90" fill="url(#g)"/></svg>')
    icons['watch-icon.svg'] = svg_star('#b6bcbf', '#8a9196')
    icons['watch-icon-hl.svg'] = svg_star('#f5c142', '#d99b12')
    icons['unwatch-icon.svg'] = svg_star('#ffffff', '#8a9196')
    icons['unwatch-icon-hl.svg'] = svg_star('#ffffff', '#d99b12')
    icons['watch-icon-loading.svg'] = svg_star('#dfe3e6', '#b6bcbf')
    icons['user-avatar.svg'] = wrap(
        '<circle cx="8" cy="8" r="7.2" fill="#e6eaee" stroke="#c3c9cf" stroke-width="0.8"/>'
        '<circle cx="8" cy="6.2" r="2.4" fill="#9aa3ab"/>'
        '<path d="M3.2 13.4a4.9 4.9 0 0 1 9.6 0z" fill="#9aa3ab"/>')
    spinner = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">'
               '<g><circle cx="8" cy="8" r="6" fill="none" stroke="#c8ced4" stroke-width="2"/>'
               '<path d="M8 2a6 6 0 0 1 6 6" fill="none" stroke="#4a90d9" stroke-width="2" stroke-linecap="round">'
               '<animateTransform attributeName="transform" type="rotate" from="0 8 8" to="360 8 8" '
               'dur="0.9s" repeatCount="indefinite"/></path></g></svg>')
    icons['spinner.svg'] = spinner
    icons['ajax-loader.svg'] = spinner
    icons['video-loading.svg'] = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">'
                                  '<g><circle cx="16" cy="16" r="12" fill="none" stroke="#dfe3e6" stroke-width="3"/>'
                                  '<path d="M16 4a12 12 0 0 1 12 12" fill="none" stroke="#4a90d9" stroke-width="3" '
                                  'stroke-linecap="round"><animateTransform attributeName="transform" type="rotate" '
                                  'from="0 16 16" to="360 16 16" dur="1s" repeatCount="indefinite"/></path></g></svg>')
    icons['logo_pcr.svg'] = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 40" width="40" height="40">'
                             '<rect width="40" height="40" rx="8" fill="#fb7299"/>'
                             '<path d="M11 15l9 5-9 5z" fill="#fff"/></svg>')
    icons['blank.svg'] = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1" width="1" height="1">'
                          '<rect width="1" height="1" fill="#ffffff" fill-opacity="0"/></svg>')

    for name, content in icons.items():
        with open(os.path.join(IMG, name), 'w', encoding='utf-8') as f:
            f.write(content)
    return len(icons)


# ---------------------------------------------------------------- URL 重写
REPLACEMENTS = [
    (re.compile(r'\.\./fonts/(glyphicons-halflings-regular\.[a-z0-9]+)'), BASE_FONT + r'/\1'),
    (re.compile(r'https://staticwiki\.biligame\.com/skins/Vector/images/([a-z0-9-]+)\.png[^)\'"]*'),
     BASE_IMG + r'/\1.svg'),
    (re.compile(r'https://staticwiki\.biligame\.com/resources/src/mediawiki\.legacy/images/([a-z0-9-]+)\.gif[^)\'"]*'),
     BASE_IMG + r'/\1.svg'),
    (re.compile(r'https://staticwiki\.biligame\.com/resources/src/mediawiki\.skinning/images/'
                r'(magnify-clip-[a-z]+)\.png[^)\'"]*'), BASE_IMG + r'/\1.svg'),
    (re.compile(r'(?:https?:)?//(?:static\.biligame\.net)/common/images/(bilibili-logo-[a-z]+\.png)'),
     BASE_IMG + r'/\1'),
    (re.compile(r'(?:\.\./)+(?:resources/)?assets/images/video-loading\.gif'), BASE_IMG + '/video-loading.svg'),
    (re.compile(r'url\(/blhx/load\.php[^)]*\)'), 'url(%s/blank.svg)' % BASE_IMG),
    (re.compile(r'(?:\.\./)*resources/assets/images/src/assets/imgs/menu/logo_pcr\.png[^)\'"]*'),
     BASE_IMG + '/logo_pcr.svg'),
    (re.compile(r'https?://static\.biligame\.net/game-center/img/sns/weibo\.png'), BASE_IMG + '/logo_pcr.svg'),
    (re.compile(r'url\((?:[\'"]?)(?:https?:)?//[^)\'"]+(?:[\'"]?)\)'), 'url(%s/blank.svg)' % BASE_IMG),
]

BUNDLE_FILES = [
    'bootstrap.min.css',
    'rank-buddle.css',
    'vector.css',
    'styles.css',
    'toapp-buddle.css',
    'pluginsCommon-buddle.css',
]


def rewrite(name):
    src = os.path.join(SRC, name)
    with open(src, 'r', encoding='utf-8', errors='replace') as f:
        css = f.read()
    before = len(re.findall(r'url\(', css))
    for pat, rep in REPLACEMENTS:
        css = pat.sub(rep, css)
    out = os.path.join(BUNDLE, name)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(css)
    remaining = re.findall(r'url\(([^)]{0,90})\)', css)
    external = [u for u in remaining if 'http' in u or u.startswith('//')]
    return before, len(external), external[:6]


def main():
    n = make_icons()
    print('生成 SVG 图标:', n)
    # 有效位图资源
    for f in ('bilibili-logo-game.png', 'bilibili-logo-white.png'):
        shutil.copy(os.path.join(SRC, 'img', f), os.path.join(IMG, f))
        print('复制', f)
    for f in os.listdir(os.path.join(SRC, 'fonts')):
        shutil.copy(os.path.join(SRC, 'fonts', f), os.path.join(FONTS, f))
    print('字体:', len(os.listdir(FONTS)))
    for name in BUNDLE_FILES:
        b, ext, sample = rewrite(name)
        print('%s: url()=%d, 残留外链=%d %s' % (name, b, ext, sample if ext else ''))
    print('bundle 输出:', os.listdir(BUNDLE))


if __name__ == '__main__':
    main()

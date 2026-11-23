#!/usr/bin/env python3
"""Authenticated maintenance helper for the local MediaWiki test site.

Network requests are sent through curl because the hosting provider applies a
JavaScript/AES browser challenge that urllib cannot reliably traverse here.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse

PYLIBS = r"C:\Users\Administrator\.workbuddy\binaries\python\pylibs"
if PYLIBS not in sys.path:
    sys.path.insert(0, PYLIBS)

from Crypto.Cipher import AES

BASE = "https://opk-test.infinityfree.me"
API = BASE + "/api.php"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126"
CONTENT_NAMESPACES = [0, 10, 14, 828]
CURL = os.environ.get("CURL_BIN", "curl")


class CurlClient:
    def __init__(self) -> None:
        handle = tempfile.NamedTemporaryFile(prefix="bwiki-cookie-", suffix=".txt", delete=False)
        self.cookie_file = handle.name
        handle.close()
        challenge = self.request(BASE + "/")
        values = re.findall(r'toNumbers\("([0-9a-f]{32})"\)', challenge)
        if len(values) >= 3:
            solved = AES.new(
                bytes.fromhex(values[0]),
                AES.MODE_CBC,
                bytes.fromhex(values[1]),
            ).decrypt(bytes.fromhex(values[2])).hex()
            with open(self.cookie_file, "w", encoding="utf-8", newline="\n") as cookie_file:
                cookie_file.write("# Netscape HTTP Cookie File\n")
                cookie_file.write(
                    "opk-test.infinityfree.me\tFALSE\t/\tFALSE\t0\t__test\t" + solved + "\n"
                )

    def request(self, url: str, form: dict[str, str] | None = None) -> str:
        command = [
            CURL,
            "-sS",
            "--max-time",
            "45",
            "-A",
            USER_AGENT,
            "-c",
            self.cookie_file,
            "-b",
            self.cookie_file,
        ]
        if form is not None:
            for key, value in form.items():
                command.extend(["--data-urlencode", f"{key}={value}"])
        command.append(url)
        result = subprocess.run(command, check=True, capture_output=True)
        return result.stdout.decode("utf-8-sig", "replace")

    def api(self, params: dict[str, str], post: bool = False) -> dict:
        params = {**params, "format": "json", "formatversion": "2"}
        if post:
            raw = self.request(API, params)
        else:
            raw = self.request(API + "?" + urllib.parse.urlencode(params))
        return json.loads(raw)


def login(client: CurlClient, username: str, password: str) -> str:
    token = client.api({"action": "query", "meta": "tokens", "type": "login"})["query"]["tokens"]["logintoken"]
    result = client.api(
        {
            "action": "login",
            "lgname": username,
            "lgpassword": password,
            "lgtoken": token,
        },
        post=True,
    )
    status = result.get("login", {}).get("result", "Unknown")
    if status != "Success":
        raise RuntimeError("Login failed: " + json.dumps(result, ensure_ascii=False))
    return status


def csrf_token(client: CurlClient) -> str:
    return client.api({"action": "query", "meta": "tokens"})["query"]["tokens"]["csrftoken"]


def list_pages(client: CurlClient, namespaces: list[int]) -> list[dict]:
    pages: list[dict] = []
    for namespace in namespaces:
        continuation: dict[str, str] = {}
        while True:
            result = client.api(
                {
                    "action": "query",
                    "list": "allpages",
                    "apnamespace": str(namespace),
                    "aplimit": "max",
                    **continuation,
                }
            )
            pages.extend(result.get("query", {}).get("allpages", []))
            continuation = result.get("continue", {})
            if not continuation:
                break
    return pages


def edit_page(client: CurlClient, token: str, title: str, text: str, summary: str) -> dict:
    return client.api(
        {
            "action": "edit",
            "title": title,
            "text": text,
            "summary": summary,
            "token": token,
        },
        post=True,
    )


def delete_page(client: CurlClient, token: str, title: str, reason: str) -> dict:
    return client.api(
        {
            "action": "delete",
            "title": title,
            "reason": reason,
            "token": token,
        },
        post=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["list", "clean", "configure"])
    args = parser.parse_args()
    username = os.environ.get("MW_USER", "")
    password = os.environ.get("MW_PASS", "")
    if not username or not password:
        raise RuntimeError("MW_USER and MW_PASS are required")

    client = CurlClient()
    login(client, username, password)
    userinfo = client.api({"action": "query", "meta": "userinfo", "uiprop": "rights|groups"})["query"]["userinfo"]
    print("logged_in_as=" + userinfo.get("name", ""))

    pages = list_pages(client, CONTENT_NAMESPACES + [8])
    if args.action == "list":
        print(json.dumps(pages, ensure_ascii=False, indent=2))
        return 0

    token = csrf_token(client)
    backrooms_pattern = re.compile(
        r"(?:^|[ /:_-])(level|entity|backrooms|opk)(?:$|[ /:_-])|后室|实体列表|编辑指南|原创层级|翻译数据库",
        re.IGNORECASE,
    )

    if args.action == "clean":
        deleted: list[str] = []
        for page in pages:
            title = page.get("title", "")
            if backrooms_pattern.search(title):
                result = delete_page(client, token, title, "清理旧后室分支测试内容")
                if "delete" in result:
                    deleted.append(title)
        print("deleted=" + json.dumps(deleted, ensure_ascii=False))
        return 0

    sidebar = """* navigation
** mainpage|首页
** recentchanges-url|最近更改
** randompage-url|随机页面
** helppage|MediaWiki帮助
* SEARCH
* TOOLBOX
* LANGUAGES
"""
    main_page = """= BWIKI 测试站 =

这是一个用于测试 MediaWiki 皮肤、模板与站点功能的独立测试站点。

* [[特殊:最近更改|最近更改]]
* [[特殊:特殊页面|特殊页面]]
* [[MediaWiki:Sidebar|导航配置]]

当前默认皮肤：'''BWIKI'''。
"""
    results = {
        "sidebar": edit_page(client, token, "MediaWiki:Sidebar", sidebar, "配置 BWIKI 测试站导航"),
        "main_page": edit_page(client, token, "首页", main_page, "重置为 BWIKI 测试站首页"),
        "sitenotice": edit_page(client, token, "MediaWiki:Sitenotice", "", "清空旧站点公告"),
        "common_css": edit_page(client, token, "MediaWiki:Common.css", "", "清空旧站点级样式，改由 BWIKI 皮肤提供"),
        "common_js": edit_page(client, token, "MediaWiki:Common.js", "", "清空旧站点级脚本，改由 BWIKI 皮肤提供"),
    }
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

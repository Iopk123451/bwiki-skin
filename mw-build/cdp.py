"""Minimal CDP driver: starts headless Edge and evaluates JS over DevTools protocol.

No third-party dependency: the WebSocket client is implemented on top of sockets.
"""
import base64
import json
import os
import socket
import struct
import subprocess
import time
import urllib.request

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ROOT = r"C:\Users\Administrator\WorkBuddy\2026-10-24-10-36-24\mw-build"


class WS:
    def __init__(self, url):
        assert url.startswith("ws://")
        rest = url[5:]
        hostport, path = rest.split("/", 1)
        path = "/" + path
        host, port = hostport.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            "GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % (path, hostport, key)
        )
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(4096)
        self.buf = buf.split(b"\r\n\r\n", 1)[1]

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise IOError("socket closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text):
        data = text.encode()
        header = bytearray([0x81])
        n = len(data)
        mask = os.urandom(4)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        header += mask
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(bytes(header) + masked)

    def recv(self, timeout=30):
        """Return one complete text message (may span frames)."""
        self.sock.settimeout(timeout)
        parts = []
        while True:
            b0, b1 = self._read(2)
            fin = b0 & 0x80
            opcode = b0 & 0x0F
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n) if n else b""
            if opcode == 0x8:
                raise IOError("server closed ws")
            if opcode in (0x1, 0x0):
                parts.append(payload)
            if fin:
                break
        return b"".join(parts).decode("utf-8", "replace")


class Cdp:
    def __init__(self, port=9700, url="about:blank", profile=None, mobile=False,
                 width=1280, height=900, ua=None):
        self.port = port
        self.profile = profile or os.path.join(ROOT, "cdpprof-%d" % port)
        self.proc = None
        self.ws = None
        self.id = 0
        self.width, self.height, self.mobile = width, height, mobile
        self.ua = ua
        self.url = url
        self.events = []

    def start(self, wait=12):
        args = [
            EDGE, "--remote-debugging-port=%d" % self.port,
            "--user-data-dir=%s" % self.profile,
            "--window-size=%d,%d" % (self.width, self.height),
            "--no-first-run", "--no-default-browser-check",
            "--headless=new", "--disable-gpu", "--mute-audio", self.url,
        ]
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + wait
        target = None
        while time.time() < deadline:
            time.sleep(1)
            try:
                data = json.loads(urllib.request.urlopen(
                    "http://127.0.0.1:%d/json" % self.port, timeout=5).read())
            except Exception:
                continue
            pages = [t for t in data if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
            if pages:
                target = pages[0]
                break
        if not target:
            raise RuntimeError("no devtools target")
        self.ws = WS(target["webSocketDebuggerUrl"])
        self.call("Runtime.enable")
        self.call("Log.enable")
        self.call("Page.enable")
        if self.ua:
            self.call("Network.setUserAgentOverride", userAgent=self.ua,
                      acceptLanguage="zh-CN,zh;q=0.9")
        self.call("Emulation.setDeviceMetricsOverride", width=self.width, height=self.height,
                  deviceScaleFactor=1, mobile=self.mobile,
                  screenOrientation={"type": "portraitPrimary", "angle": 0})
        return self

    def call(self, method, timeout=30, **params):
        self.id += 1
        msg = json.dumps({"id": self.id, "method": method, "params": params or {}})
        self.ws.send(msg)
        while True:
            raw = self.ws.recv(timeout)
            obj = json.loads(raw)
            if "id" in obj and obj["id"] == self.id:
                return obj
            self.events.append(obj)

    def goto(self, url, wait=10):
        self.call("Page.navigate", url=url)
        time.sleep(wait)

    def reload(self, wait=6):
        self.call("Page.reload", ignoreCache=True)
        time.sleep(wait)

    def js(self, code, timeout=25):
        """Evaluate an expression; returns (value_string, error_string)."""
        try:
            obj = self.call("Runtime.evaluate", expression=code, returnByValue=True,
                            awaitPromise=True, timeout=timeout)
        except (TimeoutError, OSError, IOError) as exc:
            return None, "timeout: %s" % exc
        if "error" in obj:
            return None, json.dumps(obj["error"], ensure_ascii=False)[:400]
        outer = obj.get("result", {})
        if "exceptionDetails" in outer:
            return None, json.dumps(outer["exceptionDetails"], ensure_ascii=False)[:500]
        res = outer.get("result", outer)
        return res.get("value"), None

    def evalb64(self, code, timeout=25):
        """Evaluate arbitrary multi-line JS via base64 + eval(atob())."""
        b = base64.b64encode(code.encode("utf-8")).decode()
        expr = 'eval(atob("%s"))' % b
        return self.js(expr, timeout=timeout)

    def wait_for(self, selector, tries=40):
        code = '(function(){return !!document.querySelector(%s);})()' % json.dumps(selector)
        for i in range(tries):
            try:
                v, err = self.js(code, timeout=20)
            except (TimeoutError, OSError, IOError):
                v, err = None, "timeout"
            if v is True:
                return True
            time.sleep(1)
        return False

    def shot(self, path):
        obj = self.call("Page.captureScreenshot", format="png", captureBeyondViewport=False,
                        timeout=60)
        data = obj.get("result", {}).get("data")
        if data:
            with open(path, "wb") as fh:
                fh.write(base64.b64decode(data))
            return True
        return False

    def close(self):
        try:
            self.ws.sock.close()
        except Exception:
            pass
        if self.proc:
            self.proc.kill()
        time.sleep(1)


IPHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
DESKTOP_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0")

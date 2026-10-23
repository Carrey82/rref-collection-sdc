"""
security header 的单测 —— 守住导师反馈里的第一条。

为什么单独写这个文件：
  安全头是「改了没人看得见、删了也没人发现」的那类代码。导师给的 D+ 就是因为
  一条都没有。代码加上之后，如果没有任何测试守着，下一次有人为了图方便把 CSP
  放宽（比如为了让某个页面能跑一段 JS），线上就悄悄退回 D+，而所有功能测试
  仍然是绿的。所以这里测的不是功能，是「约束还在不在」。

跑法：cd rref-collection-sdc && python3 -m unittest discover -s tests -q
"""
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

import app  # noqa: E402


# 头名 -> 必须出现的片段。用片段而不是全等，是为了允许以后加指令但不允许删掉核心。
EXPECTED = {
    "Content-Security-Policy": "default-src 'none'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-Permitted-Cross-Domain-Policies": "none",
    "Strict-Transport-Security": "max-age=",
}


class SecurityHeaderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 让测试输出别被访问日志淹没（进程内改，不影响运行中的服务）
        app.Handler.log_message = lambda *a, **k: None
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def request(self, path):
        url = "http://127.0.0.1:%d%s" % (self.port, path)
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                return r.status, r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.headers

    def test_200_page_carries_every_header(self):
        status, headers = self.request("/")
        self.assertEqual(status, 200)
        for name, fragment in EXPECTED.items():
            self.assertIsNotNone(headers.get(name), "%s missing on 200 page" % name)
            self.assertIn(fragment, headers.get(name), "%s has an unexpected value" % name)

    def test_404_page_carries_every_header(self):
        # 漏洞最常藏在错误页上：主流程加了头、error 分支忘了加，是典型写法
        status, headers = self.request("/this-route-does-not-exist")
        self.assertEqual(status, 404)
        for name in EXPECTED:
            self.assertIsNotNone(headers.get(name), "%s missing on 404 page" % name)

    def test_csp_still_blocks_inline_scripts(self):
        _, headers = self.request("/")
        csp = headers.get("Content-Security-Policy", "")
        # default-src 'none' 是脚本被禁的唯一原因；没人显式写 script-src，
        # 所以一旦有页面需要 JS，CSP 会静默拦掉 —— 见下面那个模板测试。
        self.assertIn("default-src 'none'", csp)
        self.assertNotIn("script-src", csp)
        self.assertNotIn("'unsafe-eval'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("form-action 'self'", csp)
        self.assertIn("base-uri 'none'", csp)

    def test_permissions_policy_keeps_camera_closed(self):
        # camera=() 是「拍照识别」这条路走不通的原因；放开它等于打开一个新入口
        _, headers = self.request("/")
        policy = headers.get("Permissions-Policy", "")
        for feature in ("camera=()", "microphone=()", "geolocation=()"):
            self.assertIn(feature, policy)


class TemplateScriptTest(unittest.TestCase):
    """页面里一旦出现 <script>，CSP 会静默拦掉它 —— 功能看起来「写了但没生效」。

    这个测试把「不许写 JS」从口头约定变成一条会变红的断言。
    """

    def test_no_template_contains_script_tag(self):
        tpl_dir = os.path.join(ROOT, "templates")
        offenders = []
        for name in sorted(os.listdir(tpl_dir)):
            if not name.endswith(".html"):
                continue
            with open(os.path.join(tpl_dir, name), encoding="utf-8") as f:
                if "<script" in f.read().lower():
                    offenders.append(name)
        self.assertEqual(offenders, [], "CSP forbids scripts; found <script> in: %s" % offenders)

    def test_security_headers_constant_is_not_empty(self):
        # 防止有人为了调试把整个 dict 清空
        self.assertGreaterEqual(len(app.SECURITY_HEADERS), 9)


if __name__ == "__main__":
    unittest.main()

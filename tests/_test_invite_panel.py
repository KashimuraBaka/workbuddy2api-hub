"""邀请面板（国内版）：后端代码路径、面板接线与文案词典。

    python tests/_test_invite_panel.py

背景：活动页 https://www.workbuddy.cn/events/invite/ 没有「绑定」按钮——只要带着
`?inviteCode=` 打开、登录态就绪，页面自己就会 POST 一次 /bind。面板把这条自动
行为拆成两个手动动作：读本账号的邀请码、按需把别人给的码绑进来。

这个套件钉四件事：
  1. 读写都只认国内版账号（国际版 / 无凭证在发请求之前就拒掉）；
  2. 邀请码与进度的字段口径（来自活动页 chunk 的映射函数：invite_code /
     expires_at / invite_count / valid_invite_count / total_credits / cap_value）；
  3. 绑定把上游业务码翻成能读的原因（12310 已绑过 / 12311 非活动期新用户 /
     12313 自己的码 / 12314 不适用 / 12319 不存在），业务拒绝不是异常；
  4. 面板接线：账号行有「邀请」入口（仅国内版、非 API Key 账号）、面板里显示的是
     邀请码而不是分享链接、静态文案在英文词典里有词条、服务端路由已挂上。
"""
import io
import json
import os
import re
import sys
import unittest
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import wb_invite as I  # noqa: E402


class FakeAccount(object):
    def __init__(self, realm="cn", token="tok-abc", uid="uid-0001"):
        self.realm = realm
        self.access_token = token
        self.uid = uid
        self.proxy = ""

    def web_headers(self):
        return {
            "Authorization": "Bearer " + self.access_token,
            "X-User-Id": self.uid,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://www.workbuddy.ai",
            "Referer": "https://www.workbuddy.ai/app",
            "User-Agent": "test-agent",
        }


class _Resp(object):
    def __init__(self, payload=None, raw=None):
        self._b = raw if raw is not None else json.dumps(payload).encode("utf-8")

    def read(self, n=None):
        data = self._b
        self._b = b""
        return data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _http_error(url, code, body=""):
    return urllib.error.HTTPError(url, code, "boom", {},
                                  io.BytesIO(body.encode("utf-8")))


class FakeUpstream(object):
    """按路径后缀返回预设响应，并记录每一条出站请求。"""

    def __init__(self, routes=None):
        self.routes = routes or {}
        self.requests = []

    def opener(self, req, timeout=30, proxy=""):
        raw = req.data or b""
        record = {
            "url": req.full_url,
            "method": req.get_method(),
            "headers": dict(req.header_items()),
            "body": json.loads(raw.decode("utf-8")) if raw else None,
            "proxy": proxy,
        }
        self.requests.append(record)
        for suffix, handler in self.routes.items():
            if req.full_url.endswith(suffix):
                if callable(handler):
                    return handler(req)
                return _Resp(handler)
        raise AssertionError("unexpected upstream call: %s" % req.full_url)


class InviteApiTests(unittest.TestCase):
    def setUp(self):
        self.account = FakeAccount()
        self._orig = I._accounts.urlopen
        self.upstream = FakeUpstream()
        I._accounts.urlopen = self.upstream.opener

    def tearDown(self):
        I._accounts.urlopen = self._orig

    def route(self, suffix, payload=None, raw=None):
        self.upstream.routes[suffix] = payload if raw is None else (
            lambda req: _Resp(raw=raw))

    # --- 读 ---------------------------------------------------------------
    def test_fetch_code_parses_the_activity_payload(self):
        self.route("/my-code", {"code": 0, "msg": "OK",
                                "data": {"invite_code": "kbrqgxbzgcki87",
                                         "expires_at": "never"}})
        got = I.fetch_code(self.account)
        self.assertEqual(got, {"inviteCode": "kbrqgxbzgcki87",
                               "expiresAt": "never"})

    def test_fetch_progress_parses_the_counters(self):
        self.route("/my-progress", {"code": 0, "data": {
            "invite_code": "z7l83oaeovby04wm", "invite_count": 3,
            "valid_invite_count": 2, "total_credits": 250,
            "cap_reached": False, "cap_value": 30000, "invited_users": []}})
        got = I.fetch_progress(self.account)
        self.assertEqual(got, {"inviteCount": 3, "validInviteCount": 2,
                               "totalCredits": 250, "capReached": False,
                               "capValue": 30000})
        # 面板只显示计数：被邀请人名单（含昵称）不往面板搬。
        self.assertNotIn("invitedUsers", got)

    def test_read_uses_the_cn_origin_and_the_invite_page_referer(self):
        self.route("/my-code", {"code": 0, "data": {"invite_code": "abc12345"}})
        I.fetch_code(self.account)
        req = self.upstream.requests[0]
        self.assertEqual(req["method"], "GET")
        self.assertEqual(req["url"],
                         "https://www.workbuddy.cn/activity/workbuddy/invitation/v2/my-code")
        # web_headers() 默认写的是国际版 Origin：这条链路要贴着活动页自己走。
        self.assertEqual(req["headers"].get("Origin"), "https://www.workbuddy.cn")
        self.assertEqual(req["headers"].get("Referer"),
                         "https://www.workbuddy.cn/events/invite/")
        self.assertEqual(req["headers"].get("Authorization"), "Bearer tok-abc")

    def test_intl_account_is_rejected_before_any_request(self):
        with self.assertRaises(I.InviteError) as ctx:
            I.fetch_code(FakeAccount(realm="intl"))
        self.assertEqual(ctx.exception.status, 400)
        self.assertIn("国内版", str(ctx.exception))
        self.assertEqual(self.upstream.requests, [])

    def test_account_without_token_is_rejected(self):
        with self.assertRaises(I.InviteError) as ctx:
            I.fetch_progress(FakeAccount(token=""))
        self.assertEqual(ctx.exception.status, 400)
        self.assertEqual(self.upstream.requests, [])

    # --- 绑 ---------------------------------------------------------------
    def test_bind_success(self):
        self.route("/bind", {"code": 0, "msg": "OK"})
        got = I.bind(self.account, " 90bo33l8vee ")
        self.assertTrue(got["ok"])
        self.assertEqual(got["code"], 0)
        self.assertIn("成功", got["message"])
        # 前后空格去掉再提交：从网页复制时常带空白。
        self.assertEqual(self.upstream.requests[0]["body"],
                         {"inviteCode": "90bo33l8vee"})
        self.assertEqual(self.upstream.requests[0]["method"], "POST")

    def test_business_rejections_are_results_not_exceptions(self):
        cases = {
            12310: "已绑定过",
            12311: "新注册",
            12312: "已结束",
            12313: "自己的邀请码",
            12314: "不适用",
            12316: "拒绝",
            12319: "不存在",
        }
        for code, fragment in cases.items():
            self.upstream.requests = []
            self.route("/bind", {"code": code, "msg": "upstream text"})
            got = I.bind(self.account, "abc12345")
            self.assertFalse(got["ok"], code)
            self.assertEqual(got["code"], code)
            self.assertIn(fragment, got["message"], code)

    def test_unknown_business_code_falls_back_to_upstream_message(self):
        self.route("/bind", {"code": 12399, "msg": "blocked by risk control"})
        got = I.bind(self.account, "abc12345")
        self.assertFalse(got["ok"])
        self.assertEqual(got["code"], 12399)
        self.assertEqual(got["message"], "blocked by risk control")

    def test_blank_and_malformed_codes_are_client_errors(self):
        for bad in ("", "   ", "ab", "邀请码", "a" * 33,
                    "https://www.workbuddy.cn/events/invite/?inviteCode=abc"):
            with self.assertRaises(I.InviteError) as ctx:
                I.bind(self.account, bad)
            self.assertEqual(ctx.exception.status, 400, bad)
        self.assertEqual(self.upstream.requests, [])

    def test_expired_credential_says_what_to_do(self):
        self.upstream.routes["/bind"] = (
            lambda req: (_ for _ in ()).throw(
                _http_error(req.full_url, 401, "")))
        with self.assertRaises(I.InviteError) as ctx:
            I.bind(self.account, "abc12345")
        self.assertEqual(ctx.exception.status, 502)
        self.assertIn("刷新凭证", str(ctx.exception))

    def test_non_json_body_is_reported_not_crashed(self):
        self.upstream.routes["/my-code"] = lambda req: _Resp(raw=b"<html>waf</html>")
        with self.assertRaises(I.InviteError) as ctx:
            I.fetch_code(self.account)
        self.assertIn("JSON", str(ctx.exception))


class PanelWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "dashboard.html"), encoding="utf-8") as fh:
            cls.html = fh.read()
        with open(os.path.join(ROOT, "wb_proxy.py"), encoding="utf-8") as fh:
            cls.proxy = fh.read()

    def test_account_row_has_an_invite_button_for_cn_accounts_only(self):
        self.assertIn('openInvitePanel(', self.html)
        gate = re.search(
            r"\(a\.realm === 'cn' && !a\.apiKey\s*\?\s*'<button class=\"sec mini\" "
            r"onclick=\"openInvitePanel", self.html)
        self.assertIsNotNone(gate, "「邀请」按钮应按国内版 + 非 API Key 账号渲染")

    def test_panel_shows_the_code_itself_not_a_share_url(self):
        self.assertIn('id="inviteCodeValue"', self.html)
        self.assertNotIn("events/invite/?inviteCode=", self.html,
                         "面板只显示邀请码，不要拼分享链接")
        self.assertIn("copyInviteCode", self.html)

    def test_panel_exposes_a_manual_bind_form(self):
        for needle in ('id="inviteBindInput"', 'id="inviteBindBtn"',
                       'id="inviteBindResult"', 'submitInviteBind()',
                       "postJSON('/accounts/invite'",
                       "postJSON('/accounts/invite/bind'"):
            self.assertIn(needle, self.html)

    def test_static_panel_copy_has_english_entries(self):
        labels = [
            ("邀请", "Invite"),
            ("我的邀请码", "My invite code"),
            ("受邀（输入邀请码）", "Accept an invite (enter a code)"),
            ("输入邀请码", "Enter invite code"),
            ("绑定", "Bind"),
        ]
        for zh, en in labels:
            self.assertIn("'%s': '%s'" % (zh, en), self.html,
                          "英文词典缺「%s」" % zh)

    def test_server_routes_are_wired(self):
        self.assertIn("import wb_invite", self.proxy)
        self.assertIn('if path == "/accounts/invite":', self.proxy)
        self.assertIn('if path == "/accounts/invite/bind":', self.proxy)
        self.assertIn("def _route_accounts_invite(self, payload):", self.proxy)
        self.assertIn("def _route_accounts_invite_bind(self, payload):", self.proxy)

    def test_hant_phrase_keeps_register_traditional(self):
        """繁体字表逐字替换只会得到「冊」；「註冊」必须走短语表。"""
        self.assertIn('"注册": "註冊"', self.html)

    def test_bind_route_logs_without_the_code_itself(self):
        start = self.proxy.index("def _route_accounts_invite_bind")
        end = self.proxy.index("\n    def ", start + 10)
        block = self.proxy[start:end]
        self.assertIn("code_len", block)
        self.assertNotIn("code=%s", block, "邀请码本身不要进日志")

    def test_target_helper_follows_the_error_sentinel_idiom(self):
        """_error() 自己回包、返回 None；别再写成 (account, self._error(...))。

        写错成元组时 account 会是 None 而 error 也是 None，调用方继续往下走，
        等于对着 None 发请求——响应已经发过一次，第二次回包只会留下 traceback。
        """
        start = self.proxy.index("def _invite_target")
        end = self.proxy.index("\n    def ", start + 10)
        block = self.proxy[start:end]
        self.assertIn('self._error(404, "no such account"', block)
        self.assertIn("return None", block)
        self.assertNotIn("return None, self._error", self.proxy)
        for route in ("def _route_accounts_invite(self", "def _route_accounts_invite_bind"):
            body_start = self.proxy.index(route)
            body_end = self.proxy.index("\n    def ", body_start + 10)
            self.assertIn("account = self._invite_target(payload)",
                          self.proxy[body_start:body_end])


if __name__ == "__main__":
    unittest.main()

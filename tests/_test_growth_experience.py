"""桌面端行为链与专家体验任务的判据回归。

    python tests/_test_growth_experience.py

背景（2026-10-23 线上截图）：成长任务里的「体验 WorkBuddy「发现应用」」与四条
「体验「X」专家」（中国电商运营专家 / 抖音策略师 / 商家宣传页与海报设计师 /
直播电商教练）长期停在「进行中 0/1」，一键做任务也点不亮。根因不是上游关门，
而是本仓把前四个当成「只认桌面端真实操作」跳过、后四个根本没登记——而上游
认的是**整套桌面指纹 + 事件链**，补齐就能纯 API 点亮（workbuddy2api-panel
已在真实账号上验证，本仓用 baka 账号复验）。

这个套件钉住四件事：
  1. 任务登记完整性（专家参数齐全、id 唯一、Buddy/RichMeow/Library 都接入了动作）；
  2. 专家市场搜索按 expert_id 精确落位（同名条目不能取首条），失败时退回静态参数；
  3. 事件形状与服务端契约（完整桌面指纹、expert_actual_use 的 requestId 必须是
     服务端回的真实 id、mode/type/cost 对齐真实样本）；
  4. 进度达标后自动领奖，且链动作失败时不再空等/重复发链。
"""
import io
import json
import os
import sys
import unittest
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import wb_fingerprint as F  # noqa: E402
import wb_tasks as T  # noqa: E402

SERVER_REQUEST_ID = "cmb-0123456789abcdef0123456789abcdef"


class FakeAccount(object):
    def __init__(self):
        self.uid = "u-experience-test"
        self.nickname = "tester"
        self.realm = "cn"
        self.product = "workbuddy"
        self.proxy = ""
        self.access_token = "tok"
        self.enterprise_id = ""
        self.credits = {"remain": 100}

    def headers(self, kind="chat", **kwargs):
        return {"Authorization": "Bearer " + self.access_token,
                "X-User-Id": self.uid}


class _Resp(object):
    """urlopen 的最小替身：既能整段 read()，也能按块 read(n)（SSE 用）。"""

    def __init__(self, payload=None, raw=None):
        self._b = raw if raw is not None else json.dumps(payload).encode("utf-8")
        self._pos = 0

    def read(self, n=None):
        if n is None:
            data = self._b[self._pos:]
            self._pos = len(self._b)
            return data
        data = self._b[self._pos:self._pos + n]
        self._pos += len(data)
        return data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _http_error(url, code, body):
    return urllib.error.HTTPError(url, code, "boom", {},
                                  io.BytesIO(body.encode("utf-8")))


class _Upstream(object):
    """记录出站请求的假上游：市场搜索 / 真实对话 / report 三端点。"""

    def __init__(self):
        self.requests = []
        self.market_fail = False
        self.market_experts = []
        self.chat_sse = ('data: {"id":"%s","choices":[{"delta":{"content":"2"}}]}\n\n'
                         % SERVER_REQUEST_ID).encode("utf-8")
        self.on_report = None

    def calls(self, suffix):
        return [r for r in self.requests if r["url"].endswith(suffix)]

    def opener(self, req, timeout=30, proxy=""):
        raw = req.data or b""
        body = json.loads(raw.decode("utf-8")) if raw else None
        record = {"url": req.full_url, "headers": dict(req.header_items()),
                  "body": body}
        self.requests.append(record)
        if req.full_url.endswith(T.EXPERT_MARKET_PATH):
            if self.market_fail:
                raise _http_error(req.full_url, 502, "market unavailable")
            return _Resp({"code": 0, "msg": "OK",
                          "data": {"total_count": len(self.market_experts),
                                   "experts": self.market_experts}})
        if req.full_url.endswith("/v2/chat/completions"):
            return _Resp(raw=self.chat_sse)
        if req.full_url.endswith("/v2/report"):
            if self.on_report:
                self.on_report(body)
            return _Resp({"code": 0, "msg": "OK", "data": {}})
        raise _http_error(req.full_url, 404, "not found")


class GrowthExperienceTests(unittest.TestCase):
    def setUp(self):
        self.account = FakeAccount()
        self.upstream = _Upstream()
        self._orig_urlopen = T._accounts.urlopen
        self._orig_fetch = T.fetch_growth_tasks
        self._orig_claim = T.claim_task
        T._accounts.urlopen = self.upstream.opener

    def tearDown(self):
        T._accounts.urlopen = self._orig_urlopen
        T.fetch_growth_tasks = self._orig_fetch
        T.claim_task = self._orig_claim

    # ------------------------------------------------------------------
    # 登记完整性
    # ------------------------------------------------------------------

    def test_expert_experience_specs_registered(self):
        codes = [code for code, spec in T.TASK_SPECS.items()
                 if spec.get("kind") == "experience"]
        self.assertEqual(sorted(codes), [
            "expert_use_bowangwang", "expert_use_douyinyin",
            "expert_use_maidehao", "expert_use_shangjia_xuanchuan"])
        seen = set()
        for code in codes:
            spec = T.TASK_SPECS[code]
            expert = spec["expert"]
            self.assertTrue(expert["id"].startswith("ex_"), code)
            self.assertTrue(expert["name"], code)
            self.assertTrue(expert["title"], code)
            self.assertTrue(expert["version"], code)
            self.assertEqual(expert["type"], "agent", code)
            self.assertNotIn(expert["id"], seen, "两个任务用了同一个专家 id")
            seen.add(expert["id"])
            self.assertIn(expert["title"], spec["name"], code)

    def test_desktop_tasks_are_wired_to_chain_actions(self):
        self.assertEqual(T.TASK_SPECS["Buddy_App"]["kind"], "buddyapp")
        self.assertEqual(T.TASK_SPECS["Buddy_App_QQ"]["kind"], "buddyapp")
        self.assertEqual(T.TASK_SPECS["RichMeow_Chat"]["kind"], "richmeow")
        self.assertEqual(T.TASK_SPECS["Library_read"]["kind"], "library")
        for kind in ("richmeow", "buddyapp", "library", "experience"):
            self.assertIn(kind, T.CHAIN_TASK_KINDS)
        # 旧的「只认桌面端」跳过名单必须消失：留着就会再次静默跳过这四个任务。
        self.assertFalse(hasattr(T, "DESKTOP_ONLY_TASKS"))

    def test_desktop_fingerprint_triples_are_realm_specific(self):
        cn = F.get_desktop_fingerprint("u1", "n", realm="cn")
        intl = F.get_desktop_fingerprint("u1", "n", realm="intl")
        self.assertEqual(cn["ideVersion"], "5.8.3")
        self.assertEqual(cn["commit"], "db0e9b51b7fa0b383f41f5b0b83dd442c8557918")
        self.assertEqual(cn["releaseDate"], 1792029498676)
        self.assertEqual(len(cn["qimei36"]), 36)
        int(cn["qimei36"], 16)                       # 必须是裸 hex
        self.assertEqual(intl["ideVersion"], "5.8.4")
        self.assertEqual(intl["commit"], "73952edb48da46bd0b244661efe22f4f247c4977")
        self.assertNotIn("qimei36", intl)            # 国际版一条都不带

    # ------------------------------------------------------------------
    # 专家体验链
    # ------------------------------------------------------------------

    def _douyinyin_experts(self):
        spec = T.TASK_SPECS["expert_use_douyinyin"]["expert"]
        return [
            # 同名的另一个专家排第一：取首条会打错专家（不计数）。
            {"expert_id": "ex_WmcyDlsTPaiS", "expert_type": "agent",
             "display_name_zh": "抖音策略师", "profession_zh": "抖音全域增长策略师",
             "version": "1.0.0", "categories": []},
            {"expert_id": spec["id"], "expert_type": "agent",
             "display_name_zh": "斗音音", "profession_zh": "抖音策略师",
             "version": "9.9.9", "categories": ["expert-marketing"]},
        ]

    def test_expert_chain_picks_market_entry_by_id(self):
        spec = dict(T.TASK_SPECS["expert_use_douyinyin"]["expert"])
        self.upstream.market_experts = self._douyinyin_experts()
        logs = []
        ok = T.run_expert_experience(self.account, spec, logs, gap=0)
        self.assertTrue(ok, logs)

        market = self.upstream.calls(T.EXPERT_MARKET_PATH)
        self.assertEqual(len(market), 1)
        self.assertEqual(market[0]["body"]["keyword"], spec["title"])
        self.assertEqual(market[0]["body"]["page"], 1)

        reports = [r for r in self.upstream.calls("/v2/report")]
        self.assertEqual(len(reports), 2, "召唤链与使用链应各上报一次")
        summon = reports[0]["body"]
        self.assertEqual([e["eventCode"] for e in summon],
                         ["web_element_click", "expert_summon_click", "expert_summoned"])
        clicked = summon[1]
        self.assertEqual(clicked["id"], spec["id"])
        self.assertEqual(clicked["version"], "9.9.9", "没读市场条目")
        self.assertEqual(clicked["name"], "斗音音")
        self.assertEqual(clicked["expertTitle"], "抖音策略师")

        use_events = reports[1]["body"]
        created = next(e for e in use_events if e["eventCode"] == "agent_task_created")
        self.assertTrue(created["has_expert"])
        self.assertEqual(created["expert_id"], spec["id"])
        self.assertEqual(created["expert_name"], "斗音音")
        actual = next(e for e in use_events if e["eventCode"] == "expert_actual_use")
        self.assertEqual(actual["id"], spec["id"])
        self.assertEqual(actual["mode"], "LOCAL")
        self.assertEqual(actual["type"], "")
        self.assertEqual(actual["cost"], 0)
        self.assertEqual(actual["requestId"], SERVER_REQUEST_ID)
        self.assertEqual(actual["messageId"], "msg-" + SERVER_REQUEST_ID[-8:])

        # 真实对话必须带 X-Expert-Id，且用的是服务端回的真实 id 去 JOIN 事件。
        chat = self.upstream.calls("/v2/chat/completions")
        self.assertEqual(len(chat), 1)
        headers = {k.lower(): v for k, v in chat[0]["headers"].items()}
        self.assertEqual(headers.get("x-expert-id"), spec["id"])

        # 每条事件都必须带整套桌面指纹——缺 ideName/extName 上游就不认。
        for event in summon + use_events:
            self.assertEqual(event["ideName"], "WorkBuddy")
            self.assertEqual(event["ideType"], "WorkBuddy")
            self.assertEqual(event["extName"], "workbuddy-desktop")
            self.assertEqual(event["ideVersion"], "5.8.3")
            self.assertEqual(event["commit"], F.DESKTOP_TRIPLES["cn"][1])
            self.assertEqual(event["releaseDate"], F.DESKTOP_TRIPLES["cn"][2])
            self.assertEqual(len(event["qimei36"]), 36)
            self.assertEqual(event["userId"], self.account.uid)
        # X-Domain 必须是裸主机名，不是带 scheme 的 URL。
        report_headers = {k.lower(): v for k, v in reports[0]["headers"].items()}
        self.assertEqual(report_headers.get("x-domain"), T._chat_host())
        self.assertNotIn("://", report_headers.get("x-domain", ""))

    def test_expert_market_failure_falls_back_to_static_spec(self):
        spec = dict(T.TASK_SPECS["expert_use_maidehao"]["expert"])
        self.upstream.market_fail = True
        logs = []
        ok = T.run_expert_experience(self.account, spec, logs, gap=0)
        self.assertTrue(ok, logs)
        self.assertEqual(len(self.upstream.calls(T.EXPERT_MARKET_PATH)), 1,
                         "搜索失败也要试一次（结果只用于校正）")
        summon = self.upstream.calls("/v2/report")[0]["body"]
        clicked = summon[1]
        self.assertEqual(clicked["id"], spec["id"])
        self.assertEqual(clicked["version"], spec["version"])

    def test_expert_chat_without_server_request_id_reports_failure(self):
        spec = dict(T.TASK_SPECS["expert_use_shangjia_xuanchuan"]["expert"])
        self.upstream.market_fail = True
        self.upstream.chat_sse = b'data: {"id":"not-a-server-id"}\n\n'
        logs = []
        ok = T.run_expert_experience(self.account, spec, logs, gap=0)
        self.assertFalse(ok)
        self.assertTrue(any("真实对话失败" in line for line in logs), logs)
        # 召唤链已发（它不是判据的最后一环），但使用链不能发假 requestId。
        reports = self.upstream.calls("/v2/report")
        self.assertEqual(len(reports), 1)
        self.assertFalse(any(e["eventCode"] == "expert_actual_use"
                             for e in reports[0]["body"]))

    # ------------------------------------------------------------------
    # Buddy 应用 / 桌面对话 / 资料库
    # ------------------------------------------------------------------

    def test_buddy_app_reports_five_event_chain(self):
        logs = []
        ok = T._run_desktop_action(self.account, "buddyapp", {}, logs, gap=0)
        self.assertTrue(ok, logs)
        reports = self.upstream.calls("/v2/report")
        self.assertEqual(len(reports), 1)
        events = reports[0]["body"]
        self.assertEqual([e["eventCode"] for e in events], [
            "buddyapp_discover_click", "buddyapp_show", "buddyapp_enter_click",
            "buddyapp_auth_confirm_click", "buddyapp_bindaccount_skip_click"])
        for event in events:
            self.assertEqual(event["buddyId"], T.BUDDY_APP_ID)
            self.assertEqual(event["buddyName"], T.BUDDY_APP_NAME)
            self.assertEqual(event["mode"], "LOCAL")
            self.assertEqual(event["extName"], "workbuddy-desktop")

    def test_richmeow_reports_successful_desktop_chat_chain(self):
        logs = []
        ok = T._run_desktop_action(self.account, "richmeow", {}, logs, gap=0)
        self.assertTrue(ok, logs)
        events = self.upstream.calls("/v2/report")[0]["body"]
        codes = [e["eventCode"] for e in events]
        self.assertEqual(codes, [
            "agent_task_created", "chat_message_send", "chat_request_send",
            "chat_message_response", "chat_message_status", "chat_request_response"])
        reply = next(e for e in events if e["eventCode"] == "chat_message_response")
        self.assertTrue(reply["isSuccessful"])
        self.assertEqual(reply["finishReason"], "stop")

    def test_library_uses_web_report_channel(self):
        logs = []
        ok = T._run_desktop_action(self.account, "library", {}, logs, gap=0)
        self.assertTrue(ok, logs)
        reports = self.upstream.calls("/v2/report")
        self.assertEqual(len(reports), 1)
        self.assertTrue(reports[0]["url"].startswith(T.WEB_BASE))
        headers = {k.lower(): v for k, v in reports[0]["headers"].items()}
        self.assertEqual(headers.get("x-client-platform"), "web")
        self.assertEqual(headers.get("referer"), T.LIBRARY_DOC_URL)
        event = reports[0]["body"][0]
        self.assertEqual(event["eventCode"], "web_element_click")
        self.assertEqual(event["elementId"], "library_doc_intro_click")
        self.assertEqual(event["pageURL"], T.LIBRARY_DOC_URL)
        self.assertEqual(len(event["machineId"]), 36)

    # ------------------------------------------------------------------
    # 进度回读与领奖
    # ------------------------------------------------------------------

    def _stub_progress_task(self, code, state):
        def fetch(account):
            return [{"task_code": code, "status": state["status"],
                     "current": state["current"], "target": 1,
                     "name": code, "jump_url": "", "task_type": "single",
                     "reward_credit": 100, "reward_energy": 5}]
        T.fetch_growth_tasks = fetch

    def test_progress_claims_buddy_app_after_async_scoring(self):
        state = {"status": "accepted", "current": 0}
        self._stub_progress_task("Buddy_App", state)

        def on_report(events):
            # 模拟上游异步计分：事件上报后才变 1/1。
            if any(e.get("eventCode") == "buddyapp_enter_click" for e in events):
                state.update(status="completed", current=1)
        self.upstream.on_report = on_report

        claimed = []

        def claim(account, code):
            claimed.append(code)
            return {"ok": True, "credit": 100, "energy": 5}
        T.claim_task = claim

        task = {"task_code": "Buddy_App", "status": "accepted", "current": 0,
                "target": 1, "task_type": "single", "jump_url": ""}
        logs = []
        earned = T._progress_one(self.account, task, logs, gap=0)
        self.assertEqual(earned, 100, logs)
        self.assertEqual(claimed, ["Buddy_App"])
        self.assertEqual(len(self.upstream.calls("/v2/report")), 1)
        self.assertTrue(any("领奖成功" in line for line in logs), logs)

    def test_failed_chain_does_not_poll_or_claim(self):
        spec = dict(T.TASK_SPECS["expert_use_bowangwang"]["expert"])
        self.upstream.market_fail = True
        self.upstream.chat_sse = b"data: {}\n\n"     # 拿不到 requestId
        claimed = []
        T.claim_task = lambda account, code: claimed.append(code) or {
            "ok": True, "credit": 50}
        task = {"task_code": "expert_use_bowangwang", "status": "accepted",
                "current": 0, "target": 1, "task_type": "single", "jump_url": ""}
        logs = []
        started = __import__("time").monotonic()
        earned = T._progress_one(self.account, task, logs, gap=0)
        elapsed = __import__("time").monotonic() - started
        self.assertEqual(earned, 0)
        self.assertFalse(claimed, "链失败后不该去领一个必然失败的奖")
        self.assertLess(elapsed, 20, "链失败后不该再空等计分窗口")
        self.assertTrue(any("真实对话失败" in line for line in logs), logs)


if __name__ == "__main__":
    unittest.main()

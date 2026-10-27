"""wb_tasks.py —— 国内版成长任务与日常福利全自动完成引擎

包含功能：
1. 成长任务查询、批量接取 (accept)、构造事件上报点亮 (report)、领奖入账 (claim)。
2. 连续打卡 (streak) 与能量 (energy) 余额查询。
3. 猫猫旅行 (buddy travel) 状态查询、自动派出与自动领奖。
4. 严格遵守 >= 1.0s 防风控间隔，并使用 wb_fingerprint 的稳定设备指纹。
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import wb_accounts as _accounts
import wb_fingerprint
import wb_identity

# 默认 https://copilot.tencent.com；WB_CN_CHAT_UPSTREAM 可覆盖（见 wb_identity.CN_CHAT_BASE）。
CHAT_BASE = wb_identity.CN_CHAT_BASE
BILL_BASE = "https://www.codebuddy.cn"
WEB_BASE = "https://www.workbuddy.cn"
#: 本模块只跑国内版，桌面端 UA 与 wb_identity 同一来源，避免两处各写一份
#: 版本号（国际版 5.8.4 对齐时就是这么漏掉一份的）。
DESKTOP_UA = wb_identity.DESKTOP_UA_CN
WEB_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"

#: 桌面端行为链与网页行为类任务的判据常量。
#:
#: 这些任务认的不是「一个 eventCode」，而是**整套桌面指纹 + 事件链**：客户端
#: 在真实操作后经同一个 POST /v2/report 上报多条事件，每条都带 ideName /
#: ideType=WorkBuddy、extName=workbuddy-desktop、包三元组 commit/releaseDate
#: 与设备标识。只发业务字段会被上游忽略或落到 heartbeat，进度永远是 0/1，
#: 领奖必然 400 "task not completed"——这正是它们长期停在「进行中」的原因。
BUDDY_APP_ID = "cb_y5Dy46tPQGGWtueMxXbe"
BUDDY_APP_NAME = "企鹅教师助手"
LIBRARY_DOC_URL = "https://www.workbuddy.cn/space/d/o0KWYeynteVv06UnAZqIFm"
EXPERT_MARKET_PATH = "/portal/operation-platform/market/expert/list"
#: 服务端 requestId 的真实形状（cmb- 前缀 32hex 或裸 32hex）。expert_actual_use
#: 的 requestId 必须是服务端回的真实值——自造 UUID 不计数。
_SERVER_REQUEST_ID = re.compile(r"^(cmb-)?[0-9a-f]{32}$")


_log = lambda msg: None


def set_logger(fn):
    """Route task diagnostics to the caller's logger.

    The growth endpoints swallow their errors so one dead endpoint cannot
    abort a whole cycle. Without a logger those failures are invisible, and an
    upstream change looks identical to "no tasks today".
    """
    global _log
    _log = fn or (lambda msg: None)

TASK_SPECS = {
    "create_canvas": {"kind": "canvas", "target": 1, "reward": 300, "name": "创建设计任务"},
    "template_5": {"kind": "template", "target": 5, "reward": 200, "name": "模板创建任务"},
    "expert_5": {"kind": "expert", "target": 5, "reward": 200, "name": "使用专家助手"},
    "Expert_team_use_3": {"kind": "team", "target": 3, "reward": 150, "name": "使用专家团队"},
    "skill_1": {"kind": "skill", "target": 1, "reward": 100, "name": "体验技能"},
    "automation_1": {"kind": "automation", "target": 1, "reward": 100, "name": "创建自动化任务"},
    "playbook_prompt": {"kind": "playbook", "target": 1, "reward": 100, "name": "灵感案例使用"},
    "Expert_lighthouse": {"kind": "lighthouse", "target": 1, "reward": 100, "name": "轻量云专家使用"},
    "Buddy_App": {"kind": "buddyapp", "target": 1, "reward": 100, "name": "进入 Buddy 应用"},
    "Buddy_App_QQ": {"kind": "buddyapp", "target": 1, "reward": 100, "name": "企鹅教师助手"},
    "Hp_Appearance": {"kind": "skin", "target": 1, "reward": 100, "name": "应用主题外观"},
    "chat_5": {"kind": "chat", "target": 5, "reward": 100, "name": "发起 5 次对话"},
    "Model_chat_GLM5.2": {"kind": "glmchat", "target": 1, "reward": 100, "name": "体验 GLM-5.2"},
    "black_cat": {"kind": "cat", "target": 3, "reward": 100, "name": "夜猫子任务 (23:00-08:00)"},
    "RichMeow_Chat": {"kind": "richmeow", "target": 1, "reward": 100, "name": "桌面对话事件链"},
    "Library_read": {"kind": "library", "target": 1, "reward": 100, "name": "浏览资料库"},
    # 「在专家页搜索并召唤「X」，完成一次对话」类活动任务（2026-10-23 上线，
    # 各 +50 积分 +5 能量，截止 11-20）。专家 id 全部取自任务自身的 jump_url
    # （PC deeplink experts?expertId=ex_…），并与专家市场条目交叉核对过：
    # name 是专家**昵称**，title 才是任务标题里的职业名——判据事件里 name 取
    # 昵称、expertTitle 取职业名，两者都参与服务端校验，不能互换。
    "expert_use_maidehao": {
        "kind": "experience", "target": 1, "reward": 50,
        "expert": {"id": "ex_GDl31WahyIH0", "name": "卖得好", "title": "中国电商运营专家",
                   "version": "1.0.1", "type": "agent"},
        "name": "体验「中国电商运营专家」",
    },
    "expert_use_douyinyin": {
        "kind": "experience", "target": 1, "reward": 50,
        "expert": {"id": "ex_FbY5nlWTqDod", "name": "斗音音", "title": "抖音策略师",
                   "version": "1.0.2", "type": "agent"},
        "name": "体验「抖音策略师」",
    },
    "expert_use_shangjia_xuanchuan": {
        "kind": "experience", "target": 1, "reward": 50,
        "expert": {"id": "ex_Weo3x2EZuSDm", "name": "商家宣传设计师",
                   "title": "商家宣传页与海报设计师", "version": "1.6.0", "type": "agent"},
        "name": "体验「商家宣传页与海报设计师」",
    },
    "expert_use_bowangwang": {
        "kind": "experience", "target": 1, "reward": 50,
        "expert": {"id": "ex_WZY136wV5aMt", "name": "播旺旺", "title": "直播电商教练",
                   "version": "1.0.2", "type": "agent"},
        "name": "体验「直播电商教练」",
    },
    # first_buddy 是 auto 类（上游不接受接取），完成后领奖才发放 Buddy 实例；
    # 它是所有 single 任务与猫猫旅行的前置（"prerequisite not met: first_buddy"）。
    "first_buddy": {"kind": "chat", "target": 1, "reward": 300, "name": "领取一只 Buddy"},
    # 活动任务：在专家页召唤「无畏契约拼豆专家」并完成一次对话。事件里的 id
    # 必须是这个专家的真实 id，否则上游只接受事件但不推进进度。
    "WorkBuddy_Valorant": {"kind": "expert", "target": 1, "reward": 100,
                           "expert": ("ex_xQHHD1u5Jkua", "无畏契约拼豆专家"),
                           "name": "体验「无畏契约拼豆专家」"},
    "wb_wechat_oa_subscribe_task": {"unforgeable": True, "reward": 100,
                                    "reason": "需在微信关注「腾讯 WorkBuddy」公众号满 24 小时",
                                    "name": "关注官方公众号"},
    "Expert_Philanthropy": {"unforgeable": True, "reason": "真实捐款动作", "reward": 0, "name": "公益爱心捐赠"},
}

# ---------------------------------------------------------------------------
# 桌面端行为链 (2026-10 校准)
# ---------------------------------------------------------------------------
# 早前的结论是「RichMeow_Chat / Library_read / Buddy_App / 专家召唤只认桌面端
# 真实操作，伪造事件不会推进进度」。实测证明那只对**造得不像的**事件成立：
# 上游判据是「整套桌面指纹 + 事件链」，客户端在真实操作后上报的每条事件都带
# ideName/ideType=WorkBuddy、extName=workbuddy-desktop、包三元组 commit /
# releaseDate 与设备标识。补齐这些字段、按真实操作顺序发完整事件链后，纯 API
# 即可点亮（workbuddy2api-panel 多账号实测，本仓用 baka 账号复验）。
#
# 因此这些任务不再进「只认桌面端」的跳过名单，由下面的动作函数直接执行：
#   richmeow  桌面成功对话 6 事件链（agent_task_created → chat_request_response）
#   buddyapp  「发现应用」进入五连事件（discover → show → enter → auth → bind skip）
#   library   web 域 web_element_click(library_doc_intro_click)
#   experience 专家页搜索 → 召唤链 → 真实对话（服务端 requestId）→ actual_use
CHAIN_TASK_KINDS = ("richmeow", "buddyapp", "library", "experience")

# 夜猫子任务只在 23:00-08:00 上报才计数, 且每天 1 次、累计 3 天。
NIGHT_TASK_CODES = {"black_cat"}

def in_night_window():
    h = time.localtime().tm_hour
    return h >= 23 or h < 8

# 专家/团队事件必须彼此不同: 桌面端 appendGrowthEvent 按 (eventCode, id) 去重,
# 上游同样只按不同 id 累加进度 —— 重复发同一个 id 进度永远不动。
# 下列 id 已在 2026-09 实测中验证可推进任务进度。
EXPERT_ID_POOL = [
    ("ex_PZw8Gu81HfN4", "运维工程师"), ("ex_ROsDtJbzADFV", "产品经理"),
    ("ex_SMUnl0nJbPix", "UI设计师"), ("ex_ZTR062oVBOCW", "数据分析师"),
    ("ex_a3sSSFBy8qaC", "后端架构师"), ("ex_aG1kvKbq8lPx", "文案策划"),
    ("ex_al1vxtUOYQ10", "测试专家"), ("ex_cZfiyuET9UQP", "安全顾问"),
    ("ex_eggOvQuVP0hq", "算法工程师"), ("ex_hSwsQjkSKnkX", "前端工程师"),
    ("ex_mMbwwmFA9n9P", "项目管理专家"), ("ex_uAQE5POfk7Zh", "增长运营专家"),
    ("ex_uZzSAScSy7FZ", "行业研究员"), ("ex_LHywGrZOtG7G", "数据分析师"),
    ("ex_NX5C8GBciVed", "测试架构师"), ("ex_DdCsaoq4AtcO", "云端运维专家"),
    ("ex_KzqKQguubrNQ", "内容创作专家"), ("ex_2cvvUZQhDyeJ", "腾讯轻量云专家"),
]
# 团队 id 来自官方专家清单 expert_center.json (expertType=team, 共 53 个),
# 前 3 个已在 2026-09 实测验证可推进 Expert_team_use_3。
TEAM_ID_POOL = [
    ("CloudOpsTeam", "运维专家团队"), ("CloudContentTeam", "内容专家团队"),
    ("CloudDevTeam", "研发专家团队"), ("ProductStrategyTeam", "产品战略团队"),
    ("MarketingCampaignTeam", "营销活动团队"), ("SalesBattleTeam", "销售作战团队"),
    ("DesignEngineTeam", "设计引擎团队"), ("HrOperationsTeam", "人力运营团队"),
]


def fetch_growth_tasks(account):
    """查询成长任务列表及当前状态。"""
    if getattr(account, "is_enterprise", lambda: False)():
        return []
    url = CHAT_BASE + "/v2/activity/growth/tasks"
    req = urllib.request.Request(url, headers=account.headers("chat"))
    try:
        with _accounts.urlopen(req, timeout=15, proxy=account.proxy) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_tasks = (data.get("data") or {}).get("tasks") or []
            tasks = []
            for t in raw_tasks:
                code = t.get("task_code") or ""
                spec = TASK_SPECS.get(code, {})
                prog = t.get("progress") or {}
                tasks.append({
                    "task_code": code,
                    "name": t.get("title") or spec.get("name") or code,
                    "description": t.get("description") or t.get("task_desc") or "",
                    "jump_url": t.get("jump_url") or "",
                    "status": t.get("accept_status") or "not_accepted",
                    "task_type": t.get("task_type") or "",
                    "current": prog.get("current", 0),
                    "target": prog.get("target", spec.get("target", 1)),
                    "reward_credit": t.get("reward_credit") or spec.get("reward", 0),
                    "reward_energy": t.get("reward_energy", 0),
                    "unforgeable": bool(spec.get("unforgeable")),
                    "reason": spec.get("reason", ""),
                })
            return tasks
    except Exception as exc:
        return []


def fetch_growth_summary(account):
    """查询连续打卡、猫猫旅行与能量余额。"""
    headers = account.headers("chat")
    out = {"energy": 0, "streak_days": 0, "travel": {"state": "unknown"}}
    # 1. 能量
    try:
        req = urllib.request.Request(CHAT_BASE + "/v2/activity/growth/energy", headers=headers)
        with _accounts.urlopen(req, timeout=10, proxy=account.proxy) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            out["energy"] = (d.get("data") or {}).get("balance", 0)
    except Exception as exc:
        _log(f"growth/energy query failed: {exc}")
    # 2. 连续打卡、连登档位、补签卡与抽奖
    try:
        req = urllib.request.Request(CHAT_BASE + "/activity/growth/streak", headers=headers)
        with _accounts.urlopen(req, timeout=10, proxy=account.proxy) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            data = d.get("data") or {}
            st = data.get("streak") or {}
            out["streak_days"] = st.get("days", 0)
            out["makeup_cards"] = (data.get("makeup_cards") or {}).get("balance", 0)
            redemp = data.get("redemption_status") or {}
            out["tiers"] = redemp.get("tiers") or []
            out["tier_statuses"] = {
                "7d": redemp.get("tier_7d_status", "locked"),
                "14d": redemp.get("tier_14d_status", "locked"),
                "28d": redemp.get("tier_28d_status", "locked"),
            }
    except Exception as exc:
        _log(f"growth/streak query failed: {exc}")
    try:
        req = urllib.request.Request(CHAT_BASE + "/activity/growth/lottery/summary", headers=headers)
        with _accounts.urlopen(req, timeout=10, proxy=account.proxy) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            out["lottery_chances"] = (d.get("data") or {}).get("chances", 0)
    except Exception as exc:
        _log(f"growth/lottery query failed: {exc}")
    # 3. 猫猫旅行
    try:
        req = urllib.request.Request(CHAT_BASE + "/activity/growth/buddy/travel/status", headers=headers)
        with _accounts.urlopen(req, timeout=10, proxy=account.proxy) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            out["travel"] = d.get("data") or {}
    except Exception as exc:
        _log(f"buddy/travel/status query failed: {exc}")
    return out


def fetch_streak_days(account):
    """只读查询账号当前连续打卡天数（GET /activity/growth/streak）。

    失败返回 None，不发写请求。供对话活跃上报后回显连登天数使用。
    """
    try:
        # 成长体系国内国际都有，端点跟着身分走：国际版是 www.workbuddy.ai。
        base = account.chat_base_url() if hasattr(account, "chat_base_url") else CHAT_BASE
        req = urllib.request.Request(base + "/activity/growth/streak",
                                     headers=account.headers("chat"))
        with _accounts.urlopen(req, timeout=10, proxy=account.proxy) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            st = (d.get("data") or {}).get("streak") or {}
            return st.get("days")
    except Exception as exc:
        _log(f"fetch_streak_days failed: {exc}")
        return None

def accept_tasks(account, codes, chunk=20):
    """批量接取任务。

    上游按批返回 results, 单个任务可能 status=accepted / already_accepted /
    其它失败原因。过去这里只返回 bool 且吞掉异常, 接取失败时上层完全看不见,
    于是后续上报的事件全部作用在未接取的任务上 —— 进度永远 0, 领奖必然
    "task not completed", 表现就是"接取了一堆但一个都没点亮"。
    现在返回 {"ok": bool, "accepted": [...], "failed": [...], "msg": str}。
    """
    out = {"ok": True, "accepted": [], "failed": [], "msg": "", "reasons": []}
    if not codes:
        return out
    url = CHAT_BASE + "/v2/activity/growth/tasks/accept"
    for i in range(0, len(codes), max(1, chunk)):
        part = codes[i:i + max(1, chunk)]
        body = json.dumps({"task_codes": part}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers=account.headers("chat"))
        try:
            with _accounts.urlopen(req, timeout=15, proxy=account.proxy) as resp:
                d = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read(300).decode("utf-8", "replace")
            except Exception:
                pass
            out["ok"] = False
            out["msg"] = "HTTP %s: %s" % (exc.code, detail[:200])
            out["failed"].extend(part)
            out["reasons"].append(out["msg"])
            _log(f"accept batch failed: {out['msg']}")
            continue
        except Exception as exc:
            out["ok"] = False
            out["msg"] = str(exc)[:200]
            out["failed"].extend(part)
            _log(f"accept batch failed: {exc}")
            continue
        if d.get("code") != 0:
            out["ok"] = False
            out["msg"] = d.get("msg") or ("code=%s" % d.get("code"))
            out["failed"].extend(part)
            out["reasons"].append(out["msg"])
            _log(f"accept rejected: {out['msg']}")
            continue
        results = (d.get("data") or {}).get("results") or []
        seen = set()
        for item in results:
            code = item.get("task_code")
            st = str(item.get("status") or "")
            seen.add(code)
            if st in ("accepted", "already_accepted"):
                out["accepted"].append(code)
            else:
                out["failed"].append(code)
                out["reasons"].append("%s: %s" % (code, item.get("message") or st))
                _log(f"task {code} accept status={st}")
        for code in part:
            if code not in seen:
                out["failed"].append(code)
    return out


def claim_task(account, code):
    """领取任务奖励。支持 copilot.tencent.com -> www.workbuddy.cn 自动降级。"""
    url = f"{CHAT_BASE}/activity/growth/tasks/{code}/claim"
    req = urllib.request.Request(url, data=b"{}", method="POST", headers=account.headers("chat"))
    try:
        with _accounts.urlopen(req, timeout=15, proxy=account.proxy) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            if d.get("code") == 0:
                data = d.get("data") or {}
                return {"ok": True, "credit": data.get("credit", 0), "energy": data.get("energy", 0)}
            # 200 + 非0码 (典型: 400 task not completed —— 进度还没落账就来领奖)
            _log(f"task {code} claim rejected: {d.get('msg')}")
            return {"ok": False, "credit": 0, "energy": 0, "msg": d.get("msg") or f"code={d.get('code')}"}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace") if exc.fp else ""
        err_msg = f"HTTP {exc.code}"
        try:
            err_msg = json.loads(body).get("msg") or err_msg
        except Exception:
            pass
        if exc.code == 400:
            # 降级到 web 域领奖
            web_url = f"{WEB_BASE}/activity/growth/tasks/{code}/claim"
            web_hdrs = {
                "Authorization": "Bearer " + account.access_token,
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "Origin": WEB_BASE,
                "Referer": f"{WEB_BASE}/profile/growth-center",
                "x-client-platform": "web",
                "User-Agent": WEB_UA,
                "X-User-Id": account.uid,
                "X-Domain": WEB_BASE,
            }
            try:
                req_web = urllib.request.Request(web_url, data=b"{}", method="POST", headers=web_hdrs)
                with _accounts.urlopen(req_web, timeout=15, proxy=account.proxy) as resp:
                    d = json.loads(resp.read().decode("utf-8"))
                    if d.get("code") == 0:
                        data = d.get("data") or {}
                        return {"ok": True, "credit": data.get("credit", 0), "energy": data.get("energy", 0)}
                    _log(f"task {code} web claim rejected: code={d.get('code')} msg={d.get('msg')}")
                    return {"ok": False, "credit": 0, "energy": 0, "msg": d.get("msg") or err_msg}
            except Exception as exc2:
                _log(f"task {code} web claim failed: {exc2}")
        _log(f"task {code} claim failed: {err_msg}")
        return {"ok": False, "credit": 0, "energy": 0, "msg": err_msg}
    except Exception as exc:
        _log(f"task {code} claim failed: {exc}")
    return {"ok": False, "credit": 0, "energy": 0}


def build_event(account, kind, idx=0, expert=None):
    """构造指定类型的真实规范事件数据。

    expert: (expert_id, expert_name) —— 专家/团队类事件必须每次使用不同的 id,
    上游按 (eventCode, id) 去重, 重复 id 不会推进任务进度。
    """
    now = int(time.time() * 1000)
    cid = f"wb-task-{now}-{idx}"
    rid = f"{cid}-req"
    uid = account.uid

    if kind == "canvas":
        return {"eventCode": "wbx_design_canvas_task_create", "timestamp": now,
                "reportDelay": 0, "conversationId": cid, "requestId": rid,
                "source": "summon_keyword", "isCustomModel": False, "name": "",
                "inputLength": 12, "id": f"wbx-canvas-{now}", "cost": 0,
                "isSuccessful": True, "userId": uid}
    if kind == "template":
        return {"eventCode": "agent_task_created_with_template", "timestamp": now,
                "reportDelay": 0, "isCustomModel": True, "id": str(idx),
                "name": "幻灯片", "requestId": rid, "conversationId": cid, "userId": uid}
    if kind in ("expert", "team", "lighthouse"):
        etype = "team" if kind == "team" else "agent"
        if expert:
            ex_id, name = expert
        elif kind == "lighthouse":
            ex_id, name = "ex_2cvvUZQhDyeJ", "腾讯轻量云专家"
        elif kind == "team":
            ex_id, name = "CloudOpsTeam", "运维专家团队"
        else:
            ex_id, name = "ContentCreator", "内容创作专家"
        return {"eventCode": "expert_actual_use", "timestamp": now, "reportDelay": 0,
                "mode": "CLOUD", "id": ex_id, "name": name, "expertTitle": name,
                "type": "02-Engineering", "expertType": etype, "source": "builtin",
                "version": "1.0.2", "cost": 0, "characterCount": 12, "conversationId": cid,
                "requestId": rid, "messageId": rid, "requestModelId": "deepseek-v4-flash",
                "requestModelName": "DeepSeek V4 Flash", "userId": uid}
    if kind == "skill":
        return {"eventCode": "skill_info", "timestamp": now, "reportDelay": 0,
                "skillId": "skill_2096525080079265792", "name": "pptx", "userId": uid}
    if kind == "automation":
        return {"eventCode": "automated_task_create_suc", "timestamp": now, "reportDelay": 0,
                "name": "每周工作整理", "type": "cron", "source": "manually",
                "modelId": "deepseek-v4-flash", "modelIsThinking": False,
                "conversationId": cid, "requestId": rid,
                "schedule": {"type": "recurring", "rrule": "FREQ=WEEKLY;BYDAY=FR;BYHOUR=9;BYMINUTE=0"},
                "prompt": "每周五自动整理本周工作", "userId": uid}
    if kind == "playbook":
        return {"eventCode": "playbook_prompt_send", "timestamp": now, "reportDelay": 0,
                "id": "worker-ledger-freedom-dashboard", "name": "打工人小账本",
                "type": "other", "promptLength": 10, "isOfficial": 1,
                "source": "discover", "conversationId": cid, "requestId": rid, "userId": uid}
    if kind == "skin":
        return {"eventCode": "appearance_skin_apply", "timestamp": now, "reportDelay": 0,
                "action": "apply", "source": "settings_close", "id": "theme-tkmw7j",
                "vipLevel": "free", "series": "craft", "type": "unknown",
                "name": "和平精英激战金秋", "userId": uid}
    if kind in ("chat", "glmchat", "cat"):
        m_id = "glm-5.2" if kind in ("glmchat", "cat") else "deepseek-v4-flash"
        m_nm = "GLM-5.2" if kind in ("glmchat", "cat") else "DeepSeek V4 Flash"
        mode = "night" if kind == "cat" else "craft"
        return {"eventCode": "chat_request_send", "timestamp": now, "reportDelay": 0,
                "mode": mode, "conversationId": cid, "requestId": rid,
                "inputLength": 12, "requestModelId": m_id, "requestModelName": m_nm,
                "isPlan": False, "agentName": "default", "agentType": "conversation",
                "userId": uid}
    return {"eventCode": "heartbeat", "timestamp": now, "userId": uid}


def report_events(account, events, base=None):
    """向上游上报事件数组。

    默认发 copilot.tencent.com (chat 侧) —— 与桌面客户端真实上报地址一致
    (桌面 NetLog: POST https://copilot.tencent.com/v2/report), 2026-09 实测
    该侧事件会实时推进成长任务进度。
    """
    if base is None:
        base = CHAT_BASE
    url = base + "/v2/report"
    headers = account.headers("billing" if base == BILL_BASE else "chat")
    body = json.dumps(events).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with _accounts.urlopen(req, timeout=15, proxy=account.proxy) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            return d.get("code") == 0
    except Exception:
        return False


def _chat_host():
    """X-Domain 用的裸主机名（真机是 copilot.tencent.com，不是带 scheme 的 URL）。

    CHAT_BASE 可被 WB_CN_CHAT_UPSTREAM 覆盖，所以从生效的 base 里取，
    不写死——否则换了上游地址，头里还留着旧域名。
    """
    return urllib.parse.urlsplit(CHAT_BASE).hostname or CHAT_BASE


def _desktop_headers(account):
    """桌面端 /v2/report 与专家市场共用的头族。

    与 account.headers("chat") 的区别：那条是按当前出站身分（CLI / WorkBuddy /
    VSCode）组的业务头；这里固定按**桌面客户端**的形态发，因为判据事件本身就是
    桌面端行为。UA 与 wb_identity 同一来源，避免两处各写一份版本号。
    """
    return {
        "Authorization": "Bearer " + account.access_token,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "User-Agent": DESKTOP_UA,
        "X-Domain": _chat_host(),
        "X-Product": "SaaS",
        "X-Request-ID": wb_fingerprint.generate_request_id(account.uid),
        "X-User-Id": account.uid,
    }


def _desktop_payloads(account, events):
    """给每条事件注入完整桌面指纹；事件自有字段优先（便于覆盖设备标识对齐真机）。"""
    fingerprint = wb_fingerprint.get_desktop_fingerprint(
        account.uid, getattr(account, "nickname", "") or "",
        realm=getattr(account, "realm", "cn"))
    payloads = []
    for event in events:
        item = dict(fingerprint)
        item.update(event)
        payloads.append(item)
    return payloads


def report_desktop_events(account, events):
    """以桌面客户端指纹向 chat 域 /v2/report 上报事件数组。

    与 report_events 的分工：那条走当前出站身分、body 只有业务字段，能点亮
    「上报即计数」的任务；桌面判据任务（RichMeow_Chat / Buddy_App / 专家召唤
    与使用）认整套桌面指纹 + 完整事件链，缺一项进度就不动。
    """
    if not events:
        return False
    url = CHAT_BASE + "/v2/report"
    body = json.dumps(_desktop_payloads(account, events),
                      ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers=_desktop_headers(account))
    try:
        with _accounts.urlopen(req, timeout=15, proxy=account.proxy) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            return d.get("code") == 0
    except Exception as exc:
        _log(f"desktop report failed: {exc}")
        return False


def market_expert_search(account, keyword):
    """专家页搜索：POST /portal/operation-platform/market/expert/list。

    关键词字段名是 keyword —— search_keyword / query / search 都会被忽略、
    返回全量 25318 条。同一关键词会命中多个同名专家（display_name_zh 与
    profession_zh 都参与匹配，如「抖音策略师」命中 10 条含 3 个同名），
    调用方必须按 expert_id 精确落位，不能取首条。
    """
    keyword = (keyword or "").strip()
    if not keyword:
        return []
    body = json.dumps({"page": 1, "page_size": 20, "keyword": keyword}).encode("utf-8")
    headers = _desktop_headers(account)
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(CHAT_BASE + EXPERT_MARKET_PATH, data=body,
                                 method="POST", headers=headers)
    with _accounts.urlopen(req, timeout=15, proxy=account.proxy) as resp:
        d = json.loads(resp.read().decode("utf-8"))
    return (d.get("data") or {}).get("experts") or []


def _resolve_expert(account, expert):
    """用专家市场条目校正任务里登记的静态参数（名称 / 职业名 / 版本 / 分类）。

    市场搜索只用于校正：搜不到（网络失败、或不在前 20 条）就退回登记值，
    召唤链本身不依赖搜索成功。命中时也按 expert_id 精确落位，不取首条。
    """
    resolved = dict(expert or {})
    resolved.setdefault("type", "agent")
    keyword = resolved.get("title") or resolved.get("name") or ""
    try:
        for item in market_expert_search(account, keyword):
            if str(item.get("expert_id") or "") != resolved.get("id"):
                continue
            resolved["name"] = item.get("display_name_zh") or resolved.get("name") or ""
            resolved["title"] = item.get("profession_zh") or resolved.get("title") or ""
            resolved["version"] = item.get("version") or resolved.get("version")
            resolved["type"] = item.get("expert_type") or resolved.get("type") or "agent"
            resolved["categories"] = item.get("categories") or []
            break
    except Exception as exc:
        _log(f"expert market search failed ({resolved.get('id')}): {exc}")
    return resolved


def _expert_category(expert):
    categories = expert.get("categories") or []
    first = categories[0] if categories else ""
    return first if isinstance(first, str) and first else "expert-all"


def _expert_summon_events(expert):
    """「召唤平台专家」事件组（对齐真实抓包：web_element_click + summon + summoned）。"""
    expert_id = expert.get("id") or ""
    name = expert.get("name") or ""
    title = expert.get("title") or name
    category = _expert_category(expert)
    version = expert.get("version") or "1.0.0"
    return [
        {"eventCode": "web_element_click", "source": expert_id, "type": category,
         "version": version, "elementId": "expert_summon_click",
         "elementName": "立即召唤",
         "pageURL": "/C:/Program%20Files/WorkBuddy/resources/app.asar/renderer/index.html"},
        {"eventCode": "expert_summon_click", "id": expert_id, "name": name,
         "expertTitle": title, "type": "expert-all", "position": 0,
         "expertType": expert.get("type") or "agent", "version": version,
         "mode": "LOCAL"},
        {"eventCode": "expert_summoned", "id": expert_id, "name": name,
         "expertTitle": title, "type": "expert-all"},
    ]


def _expert_actual_use_event(expert, conversation_id, request_id):
    """「专家真实使用」事件。

    mode=LOCAL、type=""、cost=0 是对齐真实样本（专家页直连召唤）的三处细节；
    requestId 必须是真实对话里服务端回的值，conversationId 用同一轮会话 id。
    """
    expert_id = expert.get("id") or ""
    name = expert.get("name") or ""
    title = expert.get("title") or name
    return {
        "eventCode": "expert_actual_use", "id": expert_id, "name": name,
        "expertTitle": title, "mode": "LOCAL", "type": "",
        "expertType": expert.get("type") or "agent",
        "source": "builtin", "version": expert.get("version") or "1.0.0",
        "cost": 0, "characterCount": 14,
        "conversationId": conversation_id, "requestId": request_id,
        "messageId": "msg-" + request_id[-8:],
        "requestModelId": "fast-model", "requestModelName": "fast-model",
    }


def _desktop_chat_events(conversation_id, request_id, message_id,
                         model_id="fast-model", model_name="fast-model"):
    """一次「桌面端成功对话」的完整事件链（6 条）。

    agent_task_created → chat_message_send → chat_request_send →
    chat_message_response(isSuccessful) → chat_message_status →
    chat_request_response。RichMeow_Chat 认的就是它；专家体验任务复用它并
    把 agent_task_created 补成带专家的形态。
    """
    now = int(time.time() * 1000)
    sid = {"codebuddy.session_id": conversation_id,
           "codebuddy.conversation_request_id": request_id}
    return [
        {"eventCode": "agent_task_created", "source": "LOCAL", "name": "working",
         "task_target": "local", "mode": "craft", "requestModelId": model_id,
         "requestModelName": model_name, "has_repo": False, "repo_type": "none",
         "workspace_type": "empty", "has_connector": False, "connector_types": [],
         "has_mention": False, "mention_types": [], "has_template": False,
         "action": "", "template_name": "", "has_expert": False, "expert_id": "",
         "expert_name": "", "expert_industry_id": "", "has_skill": False,
         "skill_names": [], "conversationId": conversation_id,
         "messageId": message_id, "buddyId": "", "buddyName": ""},
        {"eventCode": "chat_message_send", "messageId": message_id + "-assistant",
         "historyCount": 0, "isContextTruncated": False, "currentStepCount": 1,
         "traceId": request_id, "rootRequestId": request_id,
         "parentConversationId": conversation_id, "agentName": "cli",
         "agentType": "main"},
        {"eventCode": "chat_request_send", "inputLength": 24, "isPlan": False,
         "isAutoExecuteTerminal": False, "isAutoModify": False, "codebaseEnable": False,
         "maxToken": 0, "maxSteps": 500, "temperature": 0, "maxRetries": 0,
         "mentionContexts": [], "knowledgeId": [], "knowledgeName": [],
         "codebaseId": "", "mentionContextCount": 0, "command": "", "recommendId": "",
         "skillId": "", "skillCount": 0, "totalCount": 0, "traceId": request_id,
         "rootRequestId": request_id, "parentConversationId": conversation_id,
         "agentName": "cli", "agentType": "main", **sid},
        {"eventCode": "chat_message_response", "messageId": message_id + "-assistant",
         "responseModelId": model_id, "inputToken": 120, "outputToken": 80,
         "totalToken": 200, "cachedTokens": 0, "cachedWriteTokens": 0,
         "cachedMissTokens": 0, "isSuccessful": True, "messageErrorCode": "",
         "finishReason": "stop", "firstTokenAt": now, "traceId": request_id,
         "conversationId": conversation_id, "rootRequestId": request_id,
         "parentConversationId": conversation_id, "agentName": "cli",
         "agentType": "main", **sid},
        {"eventCode": "chat_message_status",
         "messageId": message_id + "-assistant", "messageErrorCode": "0",
         "traceId": request_id, "rootRequestId": request_id,
         "parentConversationId": conversation_id, "agentName": "cli",
         "agentType": "main"},
        {"eventCode": "chat_request_response", "mode": "craft", "toolCallCount": 0,
         "inputToken": 120, "outputToken": 80, "totalToken": 200, "cachedTokens": 0,
         "cachedWriteTokens": 0, "cachedMissTokens": 0, "isSuccessful": True,
         "messageErrorCode": "", "finishReason": "stop",
         "rootRequestId": request_id, "parentConversationId": conversation_id},
    ]


def _buddy_app_events(buddy_id=BUDDY_APP_ID, buddy_name=BUDDY_APP_NAME):
    """「发现应用」进入五连事件（discover → show → enter → auth → bind skip）。

    用「企鹅教师助手」作载体：同一组事件既满足 Buddy_App「进入任一应用」，
    也满足 Buddy_App_QQ 的判据应用，两个任务共用一个动作。
    """
    base = {"mode": "LOCAL", "buddyId": buddy_id, "buddyName": buddy_name}

    def event(code, extra=None):
        item = {"eventCode": code}
        item.update(base)
        if extra:
            item.update(extra)
        return item

    ident = {"elementId": buddy_id, "elementName": buddy_name}
    return [
        event("buddyapp_discover_click"),
        event("buddyapp_show", dict(ident, position=2)),
        event("buddyapp_enter_click", dict(ident, position=2, isFirstPage="1")),
        event("buddyapp_auth_confirm_click", ident),
        event("buddyapp_bindaccount_skip_click", ident),
    ]


def report_web_event(account, event_code, page_url, element_id, element_name):
    """以 Web 端指纹向 www.workbuddy.cn/v2/report 上报单事件。

    与桌面指纹（copilot 域）不同：web 域事件是浏览器形状（os/machineId/
    userAgent），Library_read 等页面行为类任务认的是这个通道。
    """
    event = {
        "eventCode": event_code, "timestamp": int(time.time() * 1000),
        "reportDelay": 0, "pageURL": page_url, "elementId": element_id,
        "elementName": element_name, "os": "Win32", "arch": "",
        "osVersion": "10.0", "userAgent": WEB_UA,
        "machineId": wb_fingerprint.derive_hex36(account.uid, "webmachine"),
        "userId": account.uid,
        "userNickname": getattr(account, "nickname", "") or "",
        "enterpriseId": getattr(account, "enterprise_id", "") or "",
    }
    headers = {
        "Authorization": "Bearer " + account.access_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-client-platform": "web",
        "Origin": WEB_BASE,
        "Referer": page_url,
        "User-Agent": WEB_UA,
        "X-User-Id": account.uid,
    }
    req = urllib.request.Request(WEB_BASE + "/v2/report",
                                 data=json.dumps([event]).encode("utf-8"),
                                 method="POST", headers=headers)
    try:
        with _accounts.urlopen(req, timeout=15, proxy=account.proxy) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            return d.get("code") == 0
    except Exception as exc:
        _log(f"web report failed: {exc}")
        return False


def _expert_chat_once(account, expert_id):
    """发一条真实桌面端对话（带 X-Expert-Id），从 SSE 里取服务端 requestId。

    expert_actual_use 的 requestId 必须是服务端回的真实 id（cmb-<32hex> 或
    32hex），自造 UUID 不计数。取到 id 即返回：后续帧只是回复正文，判据不看。
    """
    conversation_id = wb_identity.new_conversation_id()
    body = {
        "model": "fast-model",
        "messages": [
            {"role": "system",
             "content": "You are a helpful assistant. 当前处于中文环境，使用简体中文回答。"},
            {"role": "user", "content": "1+1等于几？直接回答。"},
        ],
        "agent": "cli",
        "temperature": 1,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    headers = account.headers("chat", conversation_id=conversation_id)
    headers["X-Expert-Id"] = expert_id
    headers.setdefault("Content-Type", "application/json")
    headers.setdefault("Accept", "text/event-stream")
    req = urllib.request.Request(CHAT_BASE + "/v2/chat/completions",
                                 data=json.dumps(body).encode("utf-8"),
                                 method="POST", headers=headers)
    with _accounts.urlopen(req, timeout=30, proxy=account.proxy) as resp:
        buf = b""
        search_from = 0
        while len(buf) < (1 << 20):
            chunk = resp.read(8192)
            if not chunk:
                break
            buf += chunk
            index = buf.find(b'"id":"', search_from)
            while index >= 0:
                rest = buf[index + 6:]
                end = rest.find(b'"')
                if end <= 0:
                    break              # 半帧：等下一块
                request_id = rest[:end].decode("utf-8", "replace")
                if _SERVER_REQUEST_ID.match(request_id):
                    return conversation_id, request_id
                search_from = index + 1
                index = buf.find(b'"id":"', search_from)
    raise RuntimeError("SSE 中未找到服务端 requestId")


def run_expert_experience(account, expert, logs, gap=1.0):
    """完成「在专家页搜索并召唤「X」，完成一次对话」类任务。

    判据与 Expert_lighthouse / WorkBuddy_Valorant 同源：召唤链 → 真实对话
    （服务端 requestId）→ expert_actual_use(mode=LOCAL, type="", cost=0)。
    市场搜索只用于校正专家参数，失败也照常走链。
    """
    resolved = _resolve_expert(account, expert)
    logs.append(f"· 召唤专家「{resolved.get('title')}」({resolved.get('id')}) ...")
    if not report_desktop_events(account, _expert_summon_events(resolved)):
        logs.append("! 召唤事件上报失败")
        return False
    time.sleep(gap)
    try:
        conversation_id, request_id = _expert_chat_once(account, resolved.get("id"))
    except Exception as exc:
        logs.append(f"! 真实对话失败: {exc}")
        return False
    events = _desktop_chat_events(conversation_id, request_id,
                                  "msg-" + request_id[-8:])
    for event in events:
        if event.get("eventCode") == "agent_task_created":
            event["has_expert"] = True
            event["expert_id"] = resolved.get("id")
            event["expert_name"] = resolved.get("name") or ""
            event["expert_industry_id"] = ""
    events.append(_expert_actual_use_event(resolved, conversation_id, request_id))
    if not report_desktop_events(account, events):
        logs.append("! 使用事件上报失败")
        return False
    return True


def _run_desktop_action(account, kind, spec, logs, gap=1.0):
    """执行一个桌面端 / 网页行为链任务，返回上报是否成功。

    只负责「把判据事件发出去」；进度回读与领奖由 _progress_one 统一处理
    （上游计分是异步的，在这里领奖必然 400 task not completed）。
    """
    if kind == "richmeow":
        conversation_id = wb_identity.new_conversation_id()
        request_id = wb_identity.new_message_id()
        message_id = wb_identity.new_message_id()
        ok = report_desktop_events(
            account, _desktop_chat_events(conversation_id, request_id, message_id))
        logs.append("· 已上报桌面端成功对话事件链"
                    if ok else "! 桌面端对话事件链上报失败")
        return ok
    if kind == "buddyapp":
        ok = report_desktop_events(account, _buddy_app_events())
        logs.append("· 已上报「发现应用」进入五连事件"
                    if ok else "! Buddy 应用事件上报失败")
        return ok
    if kind == "library":
        ok = report_web_event(account, "web_element_click", LIBRARY_DOC_URL,
                              "library_doc_intro_click", "WorkBuddy资料库介绍")
        logs.append("· 已上报资料库介绍阅读事件"
                    if ok else "! 资料库事件上报失败")
        return ok
    if kind == "experience":
        return run_expert_experience(account, spec.get("expert") or {}, logs, gap)
    logs.append(f"! 未实现的行为链类型: {kind}")
    return False


def _travel_status(account):
    req = urllib.request.Request(CHAT_BASE + "/activity/growth/buddy/travel/status",
                                 headers=account.headers("chat"))
    with _accounts.urlopen(req, timeout=10, proxy=account.proxy) as resp:
        d = json.loads(resp.read().decode("utf-8"))
        return d.get("data") or {}


def ensure_buddy(account, gap=1.0):
    """确保账号已领到 Buddy 实例：没有则完成并领取 first_buddy。

    first_buddy 是 auto 类任务，其奖励（reward_buddy）就是 Buddy 实例；
    single 任务与猫猫旅行都以它为前提。返回是否已就绪。
    """
    tasks = fetch_growth_tasks(account)
    fb = next((t for t in tasks if t["task_code"] == "first_buddy"), None)
    if fb is None:
        return False
    if fb["status"] == "claimed":
        return True
    _progress_one(account, fb, [], gap)
    tasks = fetch_growth_tasks(account)
    fb = next((t for t in tasks if t["task_code"] == "first_buddy"), None)
    return bool(fb and fb["status"] == "claimed")


def _travel_depart(account, lid):
    """派出旅行；返回 (data, err)。成功 data 为响应 data，失败 err 为上游 msg。"""
    body = json.dumps({"location_id": lid}).encode("utf-8")
    req = urllib.request.Request(CHAT_BASE + "/activity/growth/buddy/travel/depart",
                                 data=body, method="POST", headers=account.headers("chat"))
    try:
        with _accounts.urlopen(req, timeout=10, proxy=account.proxy) as resp:
            res = json.loads(resp.read().decode("utf-8"))
        if res.get("code") == 0:
            return res.get("data") or {}, None
        return None, res.get("msg") or ("code=%s" % res.get("code"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read(300).decode("utf-8", "replace")
        except Exception:
            pass
        try:
            msg = json.loads(detail).get("msg") or ("HTTP %s" % exc.code)
        except Exception:
            msg = "HTTP %s%s" % (exc.code, (": " + detail[:120]) if detail else "")
        return None, msg
    except Exception as exc:
        return None, str(exc)


def do_cat_travel(account):
    """检查并执行猫猫旅行 (领奖 / 派出)。"""
    if getattr(account, "is_enterprise", lambda: False)():
        return {"ok": True, "action": "skip", "msg": "企业版账号无成长体系，跳过"}
    headers = account.headers("chat")
    # 1. 查询状态
    try:
        st = _travel_status(account)
    except Exception as exc:
        return {"ok": False, "msg": f"查询旅行状态失败: {exc}"}

    state = st.get("state")
    if state == "arrived":
        # 领奖 (官方前端: POST travel/claim body {})
        req_cl = urllib.request.Request(CHAT_BASE + "/activity/growth/buddy/travel/claim", data=b"{}", method="POST", headers=headers)
        try:
            with _accounts.urlopen(req_cl, timeout=10, proxy=account.proxy) as resp:
                c_res = json.loads(resp.read().decode("utf-8"))
                credit = (c_res.get("data") or {}).get("reward_credit", 0)
                account.fetch_credits()
                return {"ok": True, "action": "claim", "credit": credit, "msg": f"旅行归来领奖成功！获得 {credit} 积分"}
        except Exception as e:
            return {"ok": False, "msg": f"领奖失败: {e}"}

    if state == "idle":
        if st.get("daily_limit_reached"):
            return {"ok": True, "action": "idle", "msg": "猫猫今日已完成旅行，明日 00:00 刷新"}
        # 派出旅行: 官方前端要求 body 携带 {location_id} (目的地清单在
        # travel/config) —— 空 body 会被拒 400 "invalid request"。
        lid = None
        try:
            req_cfg = urllib.request.Request(CHAT_BASE + "/activity/growth/buddy/travel/config", headers=headers)
            with _accounts.urlopen(req_cfg, timeout=10, proxy=account.proxy) as resp:
                cfg = json.loads(resp.read().decode("utf-8"))
                locs = (cfg.get("data") or {}).get("locations") or []
            if locs:
                lid = locs[0].get("id")
        except Exception as exc:
            _log(f"buddy/travel/config query failed: {exc}")
        if lid is None:
            lid = 1
        # 状态里的 buddy_id 是"当前旅行实例"的 id，猫在家 (idle) 时恒为 0，
        # 不能拿它判断有没有 Buddy。以 depart 的 "no active buddy" 为准：
        # 先直接派，失败再补齐 first_buddy（其奖励即 Buddy 实例）重试一次。
        data, err = _travel_depart(account, lid)
        if data is None and "no active buddy" in (err or "").lower():
            if ensure_buddy(account):
                data, err = _travel_depart(account, lid)
            else:
                return {"ok": False,
                        "msg": "还没有 Buddy：需先完成并领取「领取一只 Buddy」任务（新建任务并发起对话）"}
        if data is not None:
            loc = (data.get("location") or {}).get("name") or ""
            return {"ok": True, "action": "depart", "msg": f"猫猫已出发前往「{loc}」，预计数小时后归来！"}
        return {"ok": False, "msg": f"派出旅行失败: {err}"}

    if state == "traveling":
        return {"ok": True, "action": "traveling", "msg": "猫猫正在旅行途中，请稍后再来查看！"}

    return {"ok": True, "action": state, "msg": f"当前状态: {state}"}


def _progress_one(account, t, logs, gap, claim=True):
    """推进单个任务并返回本次到账积分。

    auto 类任务不需要接取（上游 "task does not require acceptance"），事件可
    直接点亮；single 类未接取时上报不计进度，跳过等接取成功。
    """
    code = t["task_code"]
    spec = TASK_SPECS.get(code)
    if not spec or spec.get("unforgeable"):
        if spec and spec.get("reason"):
            logs.append(f"⏭ 任务 [{spec.get('name') or code}] 需真实操作完成: {spec['reason']}, 跳过")
        return 0

    status = t["status"]
    cur = t.get("current", 0)
    tgt = t.get("target", 1)

    if status == "claimed":
        return 0

    # 已完成的任务先领奖 —— 桌面端/夜间任务也可能被真实操作完成
    # (例如用户自己在桌面端用了一次, 或夜里调度器点亮了), 这类任务必须
    # 先结算, 不能因为"只能靠真实操作"就直接跳过丢掉奖励。
    if status == "completed" or cur >= tgt:
        if not claim:
            logs.append(f"⏸ 任务 [{spec['name']}] 已达成，等待手动领取")
            return 0
        res = claim_task(account, code)
        if res.get("ok"):
            cr = res.get("credit", 0)
            logs.append(f"✓ 任务 [{spec['name']}] 领奖成功: +{cr} 积分")
            time.sleep(gap)
            return cr
        logs.append(f"! 任务 [{spec['name']}] 领奖失败: {res.get('msg') or '未知原因'}")
        time.sleep(gap)
        return 0

    # 夜猫子任务只在 23:00-08:00 计数 (每日 01:00 调度器也会自动执行)
    if code in NIGHT_TASK_CODES and not in_night_window():
        logs.append(f"🌙 任务 [{spec['name']}] 仅 23:00-08:00 上报计数, 当前不在窗口, 跳过"
                    f" (每日 01:00 调度器自动执行, 累计 3 天)")
        return 0

    if status == "not_accepted" and t.get("task_type") != "auto":
        # 接取没成功就上报是白费功夫: 上游只对已接取的任务累计进度。
        logs.append(f"⏭ 任务 [{spec['name']}] 仍未接取, 跳过 (先解决接取失败)")
        return 0

    # 需点亮上报 —— 专家/团队事件必须使用互不相同的 id, 否则上游按
    # (eventCode, id) 去重, 进度永远不动。
    need = max(1, tgt - cur)
    kind = spec.get("kind")
    chain = kind in CHAIN_TASK_KINDS
    logs.append(f"正在点亮任务 [{spec['name']}] (需上报 {need} 次)...")
    report_ok = True
    if chain:
        # 桌面端 / 网页行为链：一条完整事件链（含真实对话）才计 1 次，
        # 重复发同一条链不会把进度推到 target 以上。
        report_ok = _run_desktop_action(account, kind, spec, logs, gap)
    else:
        id_pool = None
        if kind in ("expert", "team"):
            id_pool = TEAM_ID_POOL if kind == "team" else EXPERT_ID_POOL
        fixed_expert = spec.get("expert")
        for i in range(need):
            expert = fixed_expert
            if expert is None and id_pool:
                pid, pnm = id_pool[(cur + i) % len(id_pool)]
                expert = (pid, pnm)
            ev = build_event(account, kind, idx=i, expert=expert)
            if not report_events(account, [ev]):
                report_ok = False
            if i < need - 1:
                time.sleep(gap)
    if not report_ok:
        logs.append(f"! 任务 [{spec['name']}] 部分事件上报失败 (上游拒绝), 继续尝试领奖")
        if chain:
            # 链没发出去就没有任何可等的计分，别白等 20 秒再领一次必失败的奖。
            time.sleep(gap)
            return 0

    # 桌面链的计分比普通事件慢（实测 2~8 秒才落账），且每条链只发一次，
    # 不能像普通事件那样等两轮就放弃——否则「已经点亮、只是还没落账」会被
    # 记成失败，下一轮再发一次链（重复消耗真实对话配额）还拿不到奖励。
    time.sleep(3.0 if chain else 1.5)

    # 等上游把进度落账再领奖。普通事件通常 1-3 秒就可见, 因此先快查几次;
    # 只有确实在动才继续等, 免得每个卡住的任务都空等 20 秒 (整轮要几分钟)。
    prog = cur
    for attempt in range(8 if chain else 6):
        fresh = next((x for x in fetch_growth_tasks(account) if x["task_code"] == code), None)
        if fresh:
            prog = fresh.get("current", 0)
            if prog >= tgt or fresh.get("status") in ("completed", "claimed"):
                break
            if chain:
                time.sleep(2.5)
                continue
            if prog > cur:
                # 已经在涨了, 值得多等一会儿
                time.sleep(2.5)
                continue
        if attempt < 2:
            time.sleep(1.5)
        else:
            break
    if prog < tgt:
        logs.append(f"? 任务 [{spec['name']}] 已上报但进度 {prog}/{tgt} 未达成, 领奖顺延到下次运行")
        time.sleep(gap)
        return 0

    # 领奖
    if not claim:
        logs.append(f"⏸ 任务 [{spec['name']}] 已点亮，等待手动领取")
        time.sleep(gap)
        return 0
    res = claim_task(account, code)
    if res.get("ok"):
        cr = res.get("credit", 0)
        logs.append(f"✓ 任务 [{spec['name']}] 点亮并领奖成功: +{cr} 积分")
        time.sleep(gap)
        return cr
    logs.append(f"! 任务 [{spec['name']}] 进度已达 {prog}/{tgt} 但领奖失败: {res.get('msg') or '未知原因'}")
    time.sleep(gap)
    return 0


def run_growth_tasks(account, gap=1.0, claim=True):
    """完整执行批量成长任务点亮与领奖。

    claim=False 只推进进度、不领奖，让用户自己挑时间领取（#507）。
    """
    if account.realm != "cn":
        return {"ok": False, "msg": "国际版不适用国内成长任务中心", "logs": []}
    if getattr(account, "is_enterprise", lambda: False)():
        return {"ok": True, "msg": "企业版账号无成长体系，跳过", "logs": []}

    logs = []
    logs.append(f"开始为账号 {account.nickname or account.uid[:8]} 运行成长任务自动化...")
    tasks = fetch_growth_tasks(account)
    if not tasks:
        logs.append("未能获取到任务清单，请检查网络或账号状态")
        return {"ok": False, "logs": logs, "earned_credit": 0}

    total_earned = 0

    # 0. auto 类任务（如 first_buddy）不需要接取，且可能是其他任务与猫猫旅行
    #    的前置：必须先把它们点亮并领奖（first_buddy 的奖励就是 Buddy 实例），
    #    否则 single 任务接取会报 "prerequisite not met: first_buddy"。
    for t in tasks:
        if t.get("task_type") == "auto":
            total_earned += _progress_one(account, t, logs, gap, claim=claim)

    # 1. 批量接取未接任务（auto 类不接受接取，unforgeable 无法自动化）
    def _needs_accept(x):
        return (x["status"] == "not_accepted" and not x.get("unforgeable")
                and x.get("task_type") != "auto")

    unaccepted = [t["task_code"] for t in tasks if _needs_accept(t)]
    if unaccepted:
        logs.append(f"发现 {len(unaccepted)} 个待接取任务，正在批量接取...")
        acc = accept_tasks(account, unaccepted)
        if acc.get("failed"):
            why = acc.get("msg") or ("; ".join(acc.get("reasons") or [])[:160])
            logs.append(f"! 接取未成功 {len(acc['failed'])} 个: {', '.join(acc['failed'][:5])}"
                        + (" ..." if len(acc["failed"]) > 5 else "")
                        + (f" ({why})" if why else ""))
        if acc.get("accepted"):
            logs.append(f"✓ 已接取 {len(acc['accepted'])} 个任务")
        time.sleep(gap)
        tasks = fetch_growth_tasks(account)
        # 复核一次: 上游偶尔会瞬时拒绝整个批次, 复查后仍处于未接取的再补一次,
        # 否则后面所有上报都作用在未接取的任务上 —— 进度全是 0。
        still = [t["task_code"] for t in tasks if _needs_accept(t)]
        if still:
            logs.append(f"仍有 {len(still)} 个未接取，重试接取一次...")
            retry = accept_tasks(account, still)
            if retry.get("accepted"):
                logs.append(f"✓ 重试接取成功 {len(retry['accepted'])} 个")
            time.sleep(gap)
            tasks = fetch_growth_tasks(account)
        if not tasks:
            logs.append("! 接取后无法获取任务清单，本轮中止")
            return {"ok": False, "logs": logs, "earned_credit": total_earned}
        still_pending = [t["task_code"] for t in tasks if _needs_accept(t)]
        if still_pending:
            logs.append(f"! 仍有 {len(still_pending)} 个任务处于未接取状态，"
                        f"对未接取任务上报事件不会计入进度，本轮跳过这些任务")

    # 2. 处理每个任务（auto 已在第 0 步处理过）
    for t in tasks:
        if t.get("task_type") == "auto":
            continue
        total_earned += _progress_one(account, t, logs, gap, claim=claim)

    # 3. 顺手检查猫猫旅行
    tr_res = do_cat_travel(account)
    if tr_res.get("msg"):
        logs.append(f"猫猫日常: {tr_res.get('msg')}")
        if tr_res.get("credit"):
            total_earned += tr_res.get("credit", 0)

    # 4. 刷新积分余额
    account.fetch_credits()
    logs.append(f"🎉 全部完成！本次累计新增到账: +{total_earned} 积分，当前总剩余: {account.credits.get('remain', 0)} 积分")
    return {"ok": True, "logs": logs, "earned_credit": total_earned, "credits": account.credits}


def run_night_growth(account):
    """夜猫子任务 (black_cat): 每日 23:00-08:00 上报 1 次 GLM-5.2 夜间对话事件,
    每天计 1 次、累计 3 天后可领奖。白天调用会诚实跳过。"""
    if account.realm != "cn":
        return {"ok": False, "msg": "国际版不适用国内成长任务中心", "logs": [], "earned_credit": 0}
    if getattr(account, "is_enterprise", lambda: False)():
        return {"ok": True, "msg": "企业版账号无成长体系，跳过", "logs": [], "earned_credit": 0}
    logs = []
    name = account.nickname or account.uid[:8]
    if not in_night_window():
        return {"ok": True, "earned_credit": 0, "logs": [
            f"[{name}] 当前不在 23:00-08:00 夜间窗口, 夜猫子任务跳过 (每日 01:00 自动执行)"]}
    tasks = fetch_growth_tasks(account)
    t = next((x for x in tasks if x["task_code"] == "black_cat"), None)
    if not t:
        return {"ok": False, "earned_credit": 0, "logs": [f"[{name}] 未获取到夜猫子任务清单"]}
    if t["status"] == "claimed":
        return {"ok": True, "earned_credit": 0, "logs": [f"[{name}] 夜猫子任务已领奖"]}
    if t["status"] == "not_accepted":
        # 上游只对已接取的任务累计进度；夜猫子任务也必须先接取。
        acc_res = accept_tasks(account, ["black_cat"])
        if not acc_res.get("accepted"):
            why = acc_res.get("msg") or ("; ".join(acc_res.get("reasons") or [])[:120])
            logs.append(f"[{name}] 夜猫子任务未接取, 今晚跳过 (先解决接取失败{': ' + why if why else ''})")
            return {"ok": False, "earned_credit": 0, "logs": logs}
        logs.append(f"[{name}] 夜猫子任务已接取")
    cur, tgt = t.get("current", 0), t.get("target", 3)
    if cur >= tgt:
        res = claim_task(account, "black_cat")
        cr = res.get("credit", 0) if res.get("ok") else 0
        account.fetch_credits()
        logs.append(f"[{name}] 夜猫子任务达标, 领奖 {'✓ +' + str(cr) + ' 积分' if res.get('ok') else '! 失败: ' + (res.get('msg') or '')}")
        return {"ok": res.get("ok", False), "earned_credit": cr, "logs": logs}
    ev = build_event(account, "cat", idx=0)
    ok = report_events(account, [ev])
    logs.append(f"[{name}] 上报夜间 GLM-5.2 对话事件: {'成功' if ok else '失败'} (进度 {cur}/{tgt})")
    fresh = None
    for _ in range(4):
        time.sleep(4)
        fresh = next((x for x in fetch_growth_tasks(account) if x["task_code"] == "black_cat"), None)
        if fresh and fresh.get("current", 0) > cur:
            break
    new_cur = fresh.get("current", cur) if fresh else cur
    if new_cur >= tgt:
        res = claim_task(account, "black_cat")
        cr = res.get("credit", 0) if res.get("ok") else 0
        logs.append(f"[{name}] 夜猫子任务完成 {new_cur}/{tgt}, 领奖 {'✓ +' + str(cr) + ' 积分' if res.get('ok') else '! 失败: ' + (res.get('msg') or '')}")
    elif new_cur > cur:
        logs.append(f"[{name}] 今晚 +1 ({new_cur}/{tgt}), 明晚继续, 累计 3 天可领奖")
    else:
        logs.append(f"[{name}] 已上报但进度暂未变化 ({new_cur}/{tgt}), 明晚调度器会继续累计")
    account.fetch_credits()
    earned = 0
    for line in logs:
        m = re.search(r"\+(\d+) 积分", line)
        if m:
            earned = int(m.group(1))
    return {"ok": True, "earned_credit": earned, "logs": logs}

def run_streak_bonus(account):
    """连登管家：补签保连登 -> 礼包/补偿 -> 连登档位兑换 (7d/14d/28d) -> 自动抽奖闭环。

    幂等设计：未解锁/已领/无次数/企业版均安全静默跳过。
    """
    if account.realm != "cn":
        return {"ok": False, "msg": "连登管家仅限国内版账号"}
    if getattr(account, "enterprise_id", None):
        return {"ok": True, "msg": "企业版账号无成长体系，跳过"}

    headers = account.headers("chat")
    logs = []

    # 0. 检查昨日漏签并自动补签
    try:
        req_hm = urllib.request.Request(CHAT_BASE + "/activity/growth/heatmap", headers=headers)
        with _accounts.urlopen(req_hm, timeout=10, proxy=account.proxy) as resp:
            hm_data = json.loads(resp.read().decode("utf-8"))
            cells = (hm_data.get("data") or {}).get("cells", [])
            yesterday_str = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
            y_cell = next((c for c in cells if c.get("date") == yesterday_str), None)
            if y_cell and y_cell.get("score", 0) == 0:
                # 查是否有补签卡
                req_st = urllib.request.Request(CHAT_BASE + "/activity/growth/streak", headers=headers)
                with _accounts.urlopen(req_st, timeout=10, proxy=account.proxy) as st_resp:
                    st_data = json.loads(st_resp.read().decode("utf-8"))
                    cards = ((st_data.get("data") or {}).get("makeup_cards") or {}).get("balance", 0)
                    if cards > 0:
                        body = json.dumps({"target_date": yesterday_str}).encode("utf-8")
                        req_use = urllib.request.Request(CHAT_BASE + "/activity/growth/makeup-cards/use",
                                                         data=body, method="POST", headers=headers)
                        with _accounts.urlopen(req_use, timeout=10, proxy=account.proxy) as use_resp:
                            logs.append(f"已消耗 1 张补签卡补签昨日 ({yesterday_str})")
    except Exception as exc:
        _log(f"makeup yesterday failed: {exc}")

    # 1. 尝试领新手礼包与补偿 (每号一次，无则业务错误静默)
    b_hdrs = account.headers("billing")
    for path, name in [("/billing/meter/claim-gift", "新手礼包"),
                       ("/billing/meter/claim-compensation", "活动补偿")]:
        try:
            req_g = urllib.request.Request(BILL_BASE + path, data=b"{}", method="POST", headers=b_hdrs)
            with _accounts.urlopen(req_g, timeout=10, proxy=account.proxy) as resp:
                d = json.loads(resp.read().decode("utf-8"))
                if d.get("code") == 0:
                    cr = (d.get("data") or {}).get("credit", 0)
                    logs.append(f"领取{name} +{cr}积分")
        except Exception:
            pass

    # 2. 检查 7d/14d/28d 连登档位兑换
    try:
        req_st = urllib.request.Request(CHAT_BASE + "/activity/growth/streak", headers=headers)
        with _accounts.urlopen(req_st, timeout=10, proxy=account.proxy) as resp:
            st_data = json.loads(resp.read().decode("utf-8"))
            redemp = (st_data.get("data") or {}).get("redemption_status") or {}
            tiers = redemp.get("tiers", [])
            statuses = {
                "7d": redemp.get("tier_7d_status"),
                "14d": redemp.get("tier_14d_status"),
                "28d": redemp.get("tier_28d_status"),
            }
            import uuid
            for t in tiers:
                tier_name = t.get("tier")
                status = statuses.get(tier_name)
                if status in ("locked", "claimed"):
                    continue
                body = json.dumps({"tier": tier_name, "client_token": str(uuid.uuid4())}).encode("utf-8")
                req_rd = urllib.request.Request(CHAT_BASE + "/activity/growth/redeem",
                                                data=body, method="POST", headers=headers)
                try:
                    with _accounts.urlopen(req_rd, timeout=10, proxy=account.proxy) as rd_resp:
                        rd_json = json.loads(rd_resp.read().decode("utf-8"))
                        if rd_json.get("code") == 0:
                            logs.append(f"成功兑换连登 {tier_name} 档位")
                except Exception as exc:
                    _log(f"redeem {tier_name} failed: {exc}")
    except Exception as exc:
        _log(f"streak redeem check failed: {exc}")

    # 3. 自动抽奖闭环 (有 chances 则全抽完)
    drawn_count = 0
    try:
        req_lot = urllib.request.Request(CHAT_BASE + "/activity/growth/lottery/summary", headers=headers)
        with _accounts.urlopen(req_lot, timeout=10, proxy=account.proxy) as resp:
            lot_data = json.loads(resp.read().decode("utf-8"))
            chances = (lot_data.get("data") or {}).get("chances", 0)
            import uuid
            for _ in range(chances):
                body = json.dumps({"client_token": str(uuid.uuid4())}).encode("utf-8")
                req_draw = urllib.request.Request(CHAT_BASE + "/activity/growth/lottery/draw",
                                                  data=body, method="POST", headers=headers)
                try:
                    with _accounts.urlopen(req_draw, timeout=10, proxy=account.proxy) as draw_resp:
                        d_res = json.loads(draw_resp.read().decode("utf-8"))
                        if d_res.get("code") == 0:
                            drawn_count += 1
                except Exception as exc:
                    _log(f"lottery draw failed: {exc}")
                    break
                time.sleep(1.0)
            if drawn_count > 0:
                logs.append(f"完成成长抽奖 {drawn_count} 次")
    except Exception as exc:
        _log(f"lottery summary failed: {exc}")

    msg = "; ".join(logs) if logs else "连登状态正常（无需兑换/无抽奖次数）"
    return {"ok": True, "logs": logs, "msg": msg}

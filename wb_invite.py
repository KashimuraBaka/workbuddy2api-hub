"""wb_invite.py —— 国内版邀请活动（邀请码 / 受邀绑定）的读写封装

活动页 https://www.workbuddy.cn/events/invite/ 上**没有**「绑定」按钮：页面只要
带着 `?inviteCode=` 打开、并且登录态就绪，就会自己 POST 一次 `/bind`（前端逻辑
在 events/invite 那个 chunk 里）。面板上的「邀请」把这件自动行为拆成两个手动动作：

  * 读当前账号的邀请码（GET /my-code）与邀请进度（GET /my-progress）；
  * 按需把别人给的邀请码绑到当前账号（POST /bind）。

上游的判定全在服务端：一个账号只能被邀请一次，只认活动期内的新注册用户，自己的
邀请码不能绑自己。这些情况都是 **HTTP 200 + 业务码**（12310 / 12311 / 12313 …），
所以 bind() 把它们原样回给面板、由面板显示原因，而不是抛成「请求失败」——把业务
拒绝包装成网络错误，会让操作者以为重试有用。

凭据沿用 wb_accounts.Account.web_headers()（Bearer + X-User-Id），与面板其它
网页侧动作同一条链路；只有国内版有这套活动，国际版账号直接给 400。
"""
import json
import re
import urllib.error
import urllib.request

import wb_accounts as _accounts

#: 邀请活动接口前缀。抓自活动页 chunk：`D = "/activity/workbuddy/invitation/v2"`。
PATH = "/activity/workbuddy/invitation/v2"
#: 邀请页在网页端的位置，只用来当 Referer（与页面自己发的请求一致）。
PAGE_PATH = "/events/invite/"
TIMEOUT = 20

#: 邀请码只允许字母数字：实测长度 9~16 位（rxstypoiw / z7l83oaeovby04wm），
#: 放宽到 4~32 位既容得下新活动的码，又挡住了粘贴整条链接这种误操作。
CODE_PATTERN = re.compile(r"^[0-9A-Za-z]{4,32}$")

#: 上游业务码 → 中文说明。文案照搬活动页前端，避免同一件事在两种界面里两种说法。
CODE_MESSAGES = {
    0: "邀请绑定成功",
    12310: "该账号已绑定过邀请码，无需重复绑定",
    12311: "仅活动期间新注册用户可绑定邀请码",
    12312: "活动已结束，无法绑定邀请码",
    12313: "不能使用自己的邀请码",
    12314: "该邀请码不适用于当前活动",
    12315: "收货地址已提交锁定，无法修改",
    12316: "绑定请求被拒绝，请联系客服",
    12319: "邀请码不存在，请检查后重试",
}


class InviteError(RuntimeError):
    """邀请接口的失败：status 是给面板看的 HTTP 语义（400 用法错 / 502 上游故障）。"""

    def __init__(self, message, status=502):
        RuntimeError.__init__(self, message)
        self.status = status


def _request(account, path, body=None):
    """向邀请活动接口发一次请求，返回解析后的 JSON 对象。

    只做传输与解析；业务码原样交给调用方判断——/bind 的 12311 不是异常。
    """
    if str(getattr(account, "realm", "")).lower() != "cn":
        raise InviteError("邀请活动仅国内版账号可用", 400)
    if not str(getattr(account, "access_token", "") or ""):
        raise InviteError("该账号没有可用的访问凭证", 400)

    url = _accounts.WEB_ORIGIN_CN + PATH + path
    headers = dict(account.web_headers())
    # web_headers() 的 Origin 固定写的是国际版域名；这条链路要贴着活动页自己的
    # 请求走，改成国内站，Referer 也指向邀请页而不是 /app。
    headers["Origin"] = _accounts.WEB_ORIGIN_CN
    headers["Referer"] = _accounts.WEB_ORIGIN_CN + PAGE_PATH
    data = None
    method = "GET"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with _accounts.urlopen(req, timeout=TIMEOUT,
                               proxy=getattr(account, "proxy", "")) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        # 401 说明凭据失效、429 说明被限流；面板只需要一句能照着做的话。
        if exc.code in (401, 403):
            raise InviteError("账号凭证无效或已过期，请先刷新凭证", 502)
        raise InviteError("上游返回 HTTP %s" % exc.code, 502)
    except Exception as exc:  # noqa: BLE001 - 网络层什么都可能抛
        detail = str(exc)[:160] or exc.__class__.__name__
        raise InviteError("请求上游失败: %s" % detail, 502)

    try:
        payload = json.loads(raw)
    except ValueError:
        raise InviteError("上游返回的不是 JSON（可能被风控页拦截）", 502)
    if not isinstance(payload, dict):
        raise InviteError("上游返回体格式异常", 502)
    return payload


def fetch_code(account):
    """当前账号自己的邀请码。返回 {"inviteCode": str, "expiresAt": str}。"""
    data = _request(account, "/my-code").get("data") or {}
    return {
        "inviteCode": str(data.get("invite_code") or ""),
        # 实测值是 "never"：邀请码本身长期有效，活动的截止日另算。
        "expiresAt": str(data.get("expires_at") or ""),
    }


def fetch_progress(account):
    """邀请进度汇总（只挑面板要显示的计数，不带被邀请人的名单）。"""
    data = _request(account, "/my-progress").get("data") or {}
    return {
        "inviteCount": int(data.get("invite_count") or 0),
        "validInviteCount": int(data.get("valid_invite_count") or 0),
        "totalCredits": data.get("total_credits") or 0,
        "capReached": bool(data.get("cap_reached")),
        "capValue": data.get("cap_value") or 0,
    }


def bind(account, invite_code):
    """把邀请码绑到当前账号。返回 {"ok", "code", "message"}。

    业务拒绝（已绑过 / 非新用户 / 自己的码）是正常结果，不是异常。
    """
    code = str(invite_code or "").strip()
    if not code:
        raise InviteError("请先填写邀请码", 400)
    if not CODE_PATTERN.match(code):
        raise InviteError("邀请码格式不正确（4-32 位字母或数字）", 400)

    payload = _request(account, "/bind", {"inviteCode": code})
    try:
        numeric = int(payload.get("code"))
    except (TypeError, ValueError):
        numeric = -1
    message = CODE_MESSAGES.get(numeric) or str(payload.get("msg") or "").strip()
    return {
        "ok": numeric == 0,
        "code": numeric,
        "message": message or "邀请绑定失败，请稍后重试",
    }

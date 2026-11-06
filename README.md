# WorkBuddy2API-Hub — 国际版、国内版多账号网关中枢

> [!CAUTION]
> **项目停止维护（2026-11-06）**：后续不再更新代码、不跟进上游变化、不再处理新的 issue / PR。感谢大家的 star。

> [!IMPORTANT]
> **项目进入低频维护（2026-10-23） / Low-frequency maintenance**
>
> 大幅降低更新频率与 Issue / PR 处理速度。请先阅读风险说明，再决定是否继续使用。
>
> Updates and responses to issues / pull requests will be significantly reduced. Read the risk notice below before continuing.

> [!WARNING]
> **WorkBuddy 上游正在收紧对非官方客户端的识别与拦截。**
>
> - **封禁**：2026-10-23 下午起，非官方客户端的识别与拦截明显收紧。
> - **维护者**：近期工作压力增大，无法保证及时更新与响应。
> - **可用性**：上游可能随时进一步收紧，导致本项目不可用。
> - **账号风险**：使用非官方客户端造成的风控、限流或封禁，由使用者自行承担。
>
> **Upstream enforcement** tightened detection and blocking of unofficial clients from the afternoon of 2026-10-23. The maintainer is under increased workload and cannot guarantee timely updates or replies. The upstream may tighten further at any time; rate limits, account restrictions or bans caused by using an unofficial client are the user's responsibility.

本项目仅用于协议学习、研究与个人自用。请优先使用官方客户端，不要使用主账号，不要共享账号，也不要用于商业转售。

This project is for protocol research and personal use only. Prefer the official client, do not use your primary account, and do not resell or share access.

<p align="center">
  <a href="https://github.com/ardeyouxipianyi/workbuddy2api-hub/releases"><img src="https://img.shields.io/badge/Release-v2.0.0-2496ED?style=flat-square" alt="Version 2.0.0"></a>
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/API-OpenAI_Compatible-412991?style=flat-square" alt="OpenAI API">
  <img src="https://img.shields.io/badge/Dual_Realm-Intl_&_CN-0DBD8B?style=flat-square" alt="Dual Realm">
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Maintenance-Ended-9f2d2d?style=flat-square" alt="Maintenance ended">
</p>

## 核心特性

- **标准 API 兼容**：将 WorkBuddy（国际版/国内版）与 CodeArts 封装为标准 OpenAI 格式（Chat Completions / Responses），无缝支持 Codex、Claude Code、NextChat 等各类客户端。
- **开箱即用与多端部署**：便携版免装环境（Windows 自带精简运行时），支持 Docker、NAS（群晖/飞牛）一键部署及 OpenWrt 路由器固件。
- **多账号池与出口隔离**：支持浏览器 OAuth 快速导入、每账号独立出口代理槽绑定、设备指纹隔离、自动故障转移与配额轮转。
- **自动化福利与签到**：内置国内版全套成长任务、加油站签到与猫猫旅行，支持国际版每日活跃会话与 CodeArts 自动签到；成长任务里「画布创建、灵感案例、模板使用、模型体验、多轮对话」之外，桌面端行为链、「发现应用」进入链、专家召唤 + 真实对话也都由 API 侧补齐整套桌面指纹后直接点亮领奖（baka 账号实测四条专家任务与四项桌面任务全部 0/1→1/1）。
- **邀请与受邀（国内版）**：账号行「邀请」面板读本账号邀请码与邀请进度（已邀请 / 有效 / 积分上限），也可以填入别人的邀请码手动受邀绑定；国际版与静态 API Key 账号不画这个入口。
- **可视化管理看板**：提供 Web 仪表盘，支持实时请求日志、Token/积分透视、多 API Key 权限分发（模型/账号白名单）与额度护栏。

> ⚡ **Vibe Coding 产物**：本项目为 100% Vibe Coding 协同产物——人类开发者提出架构与业务意图，AI 助手端到端完成逆向分析、链路调度、WAF 指纹脱敏与界面编写。

> 📌 **提交代码贡献前**：请先查看并**严格遵循**贡献手册 [`CONTRIBUTING.md`](CONTRIBUTING.md)——提交格式、测试门禁与端到端冒烟要求都在那里（AI / 智能体请特别注意其中的硬性规则节）。

---

## 💖 赞助商

> 想出现在这里？联系 [ardeyouxipianyi@gmail.com](mailto:ardeyouxipianyi@gmail.com)

<table>
<tr>
<td width="180" align="center" valign="middle">
  <a href="https://agentrouter.org/register?aff=unrV"><img src="https://raw.githubusercontent.com/88lin/picx-images-hosting/master/90C5FAD072EA247822CB88BB32512A41.webp" alt="Agent Router" width="150"></a>
</td>
<td valign="middle"><b><a href="https://agentrouter.org/register?aff=unrV">Agent Router</a></b>&nbsp;是免费公益大模型 API 平台，支持 Claude-opus-5.5、GPT-6 Astra、GPT-6.1 Sol、deepseek-v4-flash 等主流模型，国内直连。注册送 ＄175（每日签到得 ＄25，被邀得 ＄50），支持 GitHub / LinuxDo 登录。</td>
</tr>
</table>


---

## 一、快速启动

### 1. 本机运行

- **Windows**：双击 `start-wb-proxy.bat`（静默后台运行 + 独立日志窗口）；如需前台控制台窗口，双击 `start-wb-proxy-visible.bat`。
- **macOS / Linux**：双击 `start-wb-proxy.command` 或在终端执行 `./start-wb-proxy.sh [端口]`（默认 8788，需要 Python 3.9+）。
- **局域网共享模式**：运行 `start-wb-proxy-lan.bat`（Windows）或 `./start-wb-proxy-lan.sh`（macOS/Linux），首次启动将自动生成高强度 API Key 并在控制台打印。
- 启动后访问：
  - **Web 看板**：`http://127.0.0.1:8788/`（默认访问密码 `admin`，首次登录请在设置中修改）
  - **API 地址**：`http://127.0.0.1:8788/v1`

### 2. Docker 部署

预编译多架构镜像发布在 GHCR，无需本地构建：

**方式一：一键脚本（推荐）**

```bash
# 官方源（直连 GitHub 环境）：
curl -fsSL https://raw.githubusercontent.com/ardeyouxipianyi/workbuddy2api-hub/main/quick-deploy.sh | bash

# 国内网络 / NAS 加速：
curl -fsSL https://gh-proxy.com/https://raw.githubusercontent.com/ardeyouxipianyi/workbuddy2api-hub/main/quick-deploy.sh | sudo bash
```

> 公网部署或配合反向代理：在管道前指定 `WB_DEPLOY_MODE=public bash`，并搭配 Nginx / Caddy / Cloudflare Tunnel 配置 TLS。

**方式二：单文件 Docker Compose**

```yaml
services:
  wb-proxy:
    image: ghcr.io/ardeyouxipianyi/workbuddy2api-hub:latest
    container_name: wb-proxy
    restart: unless-stopped
    ports:
      - "8788:8788"
    environment:
      - HOST=0.0.0.0
      - PORT=8788
      - TZ=Asia/Shanghai
    volumes:
      - ./accounts:/app/accounts    # 账号凭据与配置（持久化）
      - ./usage:/app/usage          # 用量流水日志（持久化）
```

更新镜像：`docker compose pull && docker compose up -d`。

### 3. 启动入口：优先用 `-m`

同一份代码、同一个账号池，`python3 wb_proxy.py` 与 `python3 -m wb_proxy` 的常驻内存差 **47-54 MB**
（Windows 11 / aarch64、Python 3.12-3.14 四套环境实测一致，见 #702）。成因仍在排查，
但只要换成 `-m` 就能拿到这段收益——512 MB 的设备上约 10%。

```bash
cd /path/to/workbuddy2api-hub        # 必须先进入 wb_proxy.py 所在目录
python3 -m wb_proxy --port 8788
```

`-m` 把**当前目录**放进 `sys.path`，而脚本方式放的是脚本所在目录，所以务必先 `cd`。
仓库内的资源路径都基于 `__file__` 解析，不受影响。Docker 镜像和 OpenWrt 包已改用 `-m`；
Windows / macOS 的 `start-wb-proxy.*` 启动脚本暂未改动。

### 4. CodeArts 原生第三出口

网关内置进程内直连华为云 CodeArts，支持聊天 SSE 协议转换与自动签到，无需单独运行第三方桥接服务：
1. 打开看板 →「设置 → CodeArts 接入」，勾选「启用 CodeArts 出口」并保存；
2. 切换至看板顶部「CodeArts」视图，点击「+ 添加账号 (OAuth)」完成华为云授权；
3. 在「设置 → API Key」中新建 Key 并绑定出口为 `CodeArts`（或全局通用）即可调用。

CodeArts 的模型 ID 按上游目录**精确匹配**：`deepseek-v4.1-flash` 与
`deepseek-v4.1-flash-1017` 是两个独立模型，不会互相别名或静默回退。
`/v1/models?realm=codearts` 返回的是账号当前可用的真实目录 ID；调用时请直接使用
返回的完整 ID。

---

## 二、账号接入与 API Key 权限

### 1. 账号添加与代理出口绑定
- 打开看板 `http://127.0.0.1:8788/`，点击「+ 添加账号 (OAuth)」，在浏览器中完成官方登录授权即可自动入库。
- **独立代理出口槽（Proxy Slot）**：在看板中可按需配置并命名 HTTP/SOCKS5 出口代理（支持账号密码认证），支持将账号与特定代理槽位绑定，账号身份请求与出站调用均自动走该代理。

### 2. 多 API Key 权限管理
- 「设置」页支持创建多个独立 API Key：
  - **出口绑定**：可固定走国际版、国内版或 CodeArts；
  - **模型限制**：支持通配符白名单（如 `deepseek*`, `gpt-6-astra`），违规请求本机直接返回 400；
  - **账号白名单**：可精确限定该 Key 仅允许调度的账号范围；
  - **用量透视**：数据看板按 Key 独立统计调用次数、Token 消耗、缓存命中与积分。

---

## 三、客户端接入配置

- **Base URL**：`http://127.0.0.1:8788/v1`（局域网为 `http://<局域网IP>:8788/v1`）
- **API Key**：看板「设置」中添加并绑定的 Key
- **模型名称**：调用 `/v1/models` 中列出的任意官方对齐模型 ID（如 `deepseek-v4.1-flash`, `gpt-6-astra`, `hy3`）

**Codex CLI / Responses API**

```bash
export OPENAI_BASE_URL="http://127.0.0.1:8788/v1"
export OPENAI_API_KEY="你在看板设置中添加并绑定的API_Key"
```

**Claude Code / Anthropic Messages（实验性）**

网关支持实验性 Messages 协议适配，因长会话缓存命中率差异，默认关闭：
```bash
# 网关端设置 WB_ENABLE_ANTHROPIC_MESSAGES=1 开启后生效：
export ANTHROPIC_BASE_URL="http://127.0.0.1:8788"
export ANTHROPIC_API_KEY="你在看板设置中添加并绑定的API_Key"
```

---

## 四、常用环境变量

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `PORT` | `8788` | 网关监听端口 |
| `API_KEY` | 自动生成 | 初始 API Key（看板配置多 Key 后优先由看板管理） |
| `WB_DEPLOY_MODE` | `lan` | 部署模式：`lan`（0.0.0.0）、`local`（127.0.0.1）、`public` |
| `WB_MAX_PAYLOAD_BYTES` | `16777216` | 单请求体上限（字节，默认 16MB，支持 1–256 MB） |
| `WB_ENABLE_ANTHROPIC_MESSAGES` | `0` | 是否开启实验性 Anthropic Messages 协议转换 |
| `WB_BACKGROUND_MODEL_TARGET` | 留空 | 后台模型别名改写目标（如 DSH 客户端自动映射） |
| `WB_CA_BUNDLE` | 留空 | 自签根证书路径（供抓包调试或中间代理使用） |
| `WB_CN_CHAT_UPSTREAM` | 官方默认 | 国内版出站代理地址 |
| `WB_IDENTITY_OS` | 宿主系统 | 仅 CLI 身份：覆盖 `x-stainless-os`（如 `Linux` / `Windows`） |
| `WB_IDENTITY_ARCH` | 宿主架构 | 仅 CLI 身份：覆盖 `x-stainless-arch`（如 `x64` / `arm64`） |
| `WB_IDENTITY_NODE_VERSION` | 官方默认 | 仅 CLI 身份：覆盖 `x-stainless-runtime-version` |

遇到上游 `400 / 11-128` 时，先按 [`docs/TROUBLESHOOTING-11-128.md`](docs/TROUBLESHOOTING-11-128.md) 收集同一请求的
身份、最小请求和提示词对照结果；不要先轮换账号。

---

## 五、主要 API 端点

| 接口 | 方法 | 端点 | 说明 |
|---|---|---|---|
| 聊天补全 | `POST` | `/v1/chat/completions` | 标准 OpenAI 聊天接口（支持流式 SSE 与思维链回填） |
| 交互式响应 | `POST` | `/v1/responses` | OpenAI Responses 协议接口（Codex 专用） |
| 模型目录 | `GET` | `/v1/models` | 获取当前出口对齐的官方可用模型列表 |
| 生图 | `POST` | `/v1/images/generations` | 文生图 / 图生图（需在设置中启用媒体模块） |
| 生视频 | `POST` | `/v1/videos` | 异步生视频任务提交（本地并发排队与空闲调度） |
| 视频状态 | `GET` | `/v1/videos/<id>` | 轮询视频生成进度与结果 |
| 产物下载 | `GET` | `/v1/videos/<id>/content` | 下载视频 MP4 产物直链 |
| 健康检查 | `GET` | `/health` | 网关运行状态、可用账号数与就绪模型分布 |

---

## 六、测试验证

```bash
python tests/run_all.py            # 全部套件
python tests/run_all.py realm      # 只跑名字里含 realm 的
```

- 275 个套件：208 个 Python + 67 个 JS；JS 需要 PATH 上有 `node`，缺失时会跳过并提示。
- `tests/_mobile_check.py` 是独立的 Playwright 手机/桌面布局检查器（需自行安装 Playwright），按需手动运行，不在上面的套件集里。
- CI（`.github/workflows/tests.yml`）跑同一条命令：Ubuntu 上 python 3.9 与 3.12（3.9 是本项目声称的最低版本），Windows 上 python 3.12；推送 `v*` tag 时额外断言 **tag == 源码版本**（`-ci` 演练 tag 豁免）。

---

## 七、版本更新记录 (Changelog)

### Unreleased

- **合并上游 v2.0.0（本地优先，重复登记由本地链实现胜出）**：上游 11-06 第四次把 `main` force-push 回退到 `3990792`（v1.10.1）之后重放 137 个提交，发 v1.10.2～v1.10.11 与 v2.0.0（CodeArts 账号管理 / 视觉 / reasoning / 签到、面板客户端分页与排序、用量缓存补写、小程序 Sequential_Tasks 链式任务、`WB_DUMP_11-128` 取证开关、README 压缩并把细节移入 docs/*），本地 6 个提交随之再次从远端整体消失。这次不是纯并集：上游 `937c179` 也动了成长任务这一块，两边在四个点上真正撞车，逐条按内容与实测判定：① `expert_use_*` 四条被两边各登记一次，字典里重复键后者静默覆盖前者，等于把链任务退回「只发一条事件」的老写法（正是 2026-10-23 报「一直进行中 0/1」的根因），删掉上游那份重复登记、保留本地带 version/type/title 的链形态；② 上游保留 `DESKTOP_ONLY_TASKS`（Buddy_App / Buddy_App_QQ 诚实跳过），本仓实测补齐「发现应用」五连事件链即可 0/1→1/1 并 +100 积分到账，跳过名单继续不恢复，他们的多事件构造（`build_desktop_chat_events`、playbook 一次上报两条）在 else 分支原样保留；③ README 采用上游压缩后的骨架，本地只把套件计数、特性条目与未发布记录搬回去；④ `dashboard.html` 的操作列宽保留本地含「邀请」的 306px（上游的粘性列与客户端分页结构全数保留）。上游其余能力一条不丢。 / Merge upstream v2.0.0 with local priority; where both sides registered the same growth task, the live-verified chain implementation wins. For the fourth time upstream force-pushed, this time rewinding to 3990792 (v1.10.1) and replaying 137 commits into v1.10.2-v1.10.11 and v2.0.0 (CodeArts account management / vision / reasoning / check-in, client-side panel pagination and sorting, usage-cache write-back, the mini-program Sequential_Tasks chains, the WB_DUMP_11-128 forensics switch, and a condensed README that moves detail into docs/*), which dropped all six of our commits again. This was not a clean union: upstream's 937c179 also worked on growth tasks and the two sides met in four places, each settled by content and by what was measured live - the four expert_use_* codes were registered by both and a duplicate dict key silently shadows the first (putting those tasks back on the single-event path that never advanced them, the very bug reported on 10-23), so upstream's duplicate entry is dropped in favour of the chain spec with version/type/title; upstream kept DESKTOP_ONLY_TASKS (honestly skipping Buddy_App / Buddy_App_QQ) while this repo measured the five-event 发现应用 chain lighting Buddy_App 0/1 to 1/1 for +100 credits, so the skip list stays gone and their multi-event builders (build_desktop_chat_events, two playbook events per report) are kept untouched in the else branch; the README takes upstream's condensed skeleton with only our suite count, feature bullets and unreleased entries moved back onto it; and the account table keeps our 306px action column that fits the Invite button inside upstream's new sticky column and client-side pagination. Nothing else of theirs was dropped.

- **合并上游 v1.10.1（本地优先，按内容逐条判定保留）**：上游 11-02 第三次把 `main` force-push 回退——退回 `a797c1d`（v1.10.0）后重放 11 个提交发 v1.10.1（429 带上绝对恢复时刻 #720、工具名称校验丢弃上游不接受的 `function.name` 防 400 / 11133 #726、CodeArts 发`x-ot-session-id` 修掉会话上限与排队 #723、CodeArts OAuth 回调把 `state` 当 `ticket_id`认领 #735、限流测试夹具改按运行时钟推算不再写死日期 #737），本地 5 个提交因此第三次从远端消失。判定仍然逐条比内容而不是取一侧：`git diff a797c1d origin/main` 完全不碰 `wb_tasks.py` / `wb_fingerprint.py` / `wb_invite.py` / `tests/_test_growth_experience.py` / `tests/_test_sanitize_fingerprint.py` / `tests/_test_invite_panel.py` / `tests/_test_agents.py`，wb_proxy 的改动全落在 `normalize_tools` / `RateLimited` / `parse_rate_limit_reset` / `open_upstream` / Handler 路由与 `runtime_settings_view` 附近，没有一行进 sanitize 区域；上游也没有任何邀请实现（全仓只有 `wb_webprompts.py` 的语料里出现「邀请」二字）。所以结果还是并集：本地五项工作（成长任务判据链、@ 路径说明段指纹、v1.9.0 合并修正、v1.10.0 合并、账号「邀请」面板）全部保留，上游 11 个提交全部收下。冲突只有本文件（套件计数 + 更新记录），`dashboard.html` 与 `wb_proxy.py` 自动合并并复核过邀请路由仍在面板鉴权分支内、与 CodeArts 路由互不覆盖。计数按合并后的树重算为 249（186 Python + 63 JS）；版本沿用上游 1.10.1（`server_version` / 运行时 `version` / wrt `PKG_VERSION` 三处一致），本地这五项属于 1.10.1 之后的下一版内容。 / Merge upstream v1.10.1 with local priority, deciding by content: for the third time upstream force-pushed main backwards, rewinding to a797c1d (v1.10.0) and replaying 11 commits as v1.10.1 (absolute reset instants on 429 #720, dropping tool names the upstream rejects so requests stop dying with 400 / 11133 #726, the CodeArts x-ot-session-id fix for the session cap and queueing #723, claiming the OAuth ticket_id carried in state #735, and deriving rate-limit fixture times from the running clock #737), which dropped our five commits again. The verdict is still per-content, not one-sided: `git diff a797c1d origin/main` never touches `wb_tasks.py`, `wb_fingerprint.py`, `wb_invite.py`, or any of our suites, every wb_proxy hunk lands around `normalize_tools` / `RateLimited` / `parse_rate_limit_reset` / `open_upstream` / the handler routes / `runtime_settings_view` with not one line in the sanitize region, and upstream has no invite implementation at all. So this stays a union: all five local work items (growth-task criterion chains, the @-path fingerprint, the v1.9.0 merge fixes, the v1.10.0 merge and the account invite panel) are kept along with all 11 upstream commits. Only this file conflicted; `dashboard.html` and `wb_proxy.py` auto-merged and were reviewed where the invite routes meet the CodeArts ones. The count is recomputed from the merged tree as 249 (186 Python + 63 JS), and the version stays at upstream's 1.10.1 (server_version, the runtime version field and the wrt PKG_VERSION all agree).

- **合并上游 v1.10.0（本地优先，按内容逐条判定保留）**：上游在 11-01 又一次 force-push 把 `main` 退到 `a6a967e`（v1.9.0）之后重放，本地 4 个提交（成长任务判据链、@ 路径说明段指纹、v1.9.0 合并、账号「邀请」面板）因此再次从 main 上消失。这次先逐条比内容再决定去留：上游 32 个提交（v1.9.1 / v1.9.2 / v1.10.0，主体是 CodeArts 原生第三出口、请求体上限面板可调、Key 选择器搜备注、今日活动无记录、最近请求跨天日期、重复设置卡片）**一条都没有实现这四件事**——`git diff a6a967e origin/main` 完全不碰 `wb_tasks.py` / `wb_fingerprint.py` / `tests/_test_growth_experience.py` / `tests/_test_sanitize_fingerprint.py`，sanitize 区域也没有一行改动，所以两边是并集而不是替换，全部保留。冲突只有本文件（套件计数 + 更新记录）；`dashboard.html`、`wb_proxy.py`、`release/portable.txt` 都自动合并，已逐处复核邀请路由与 CodeArts 路由互不覆盖。套件计数按合并后的树重算为 246（183 Python + 63 JS）；版本沿用上游 1.10.0（`server_version` / 运行时 `version` / wrt `PKG_VERSION` 三处一致）。顺带修正邀请条目英文侧的断言数（17 → 19，与 `tests/_test_invite_panel.py` 实际的 19 项一致）。 / Merge upstream v1.10.0 with local priority, keeping each side by content: on 11-01 upstream force-pushed again, rewinding main to a6a967e (v1.9.0) and replaying 32 commits (v1.9.1 / v1.9.2 / v1.10.0, mostly the native CodeArts third exit), which dropped our four commits a second time. Each was compared before deciding: none of the upstream commits implements the growth-task chains, the @-path fingerprint, the v1.9.0 merge or the account invite panel - `git diff a6a967e origin/main` never touches `wb_tasks.py`, `wb_fingerprint.py`, `tests/_test_growth_experience.py` or `tests/_test_sanitize_fingerprint.py`, and no sanitize line changed - so the result is a union, not a replacement, and all four are kept. Only this file conflicted (suite count plus changelog); `dashboard.html`, `wb_proxy.py` and `release/portable.txt` auto-merged and were reviewed where the invite routes meet the CodeArts ones. The suite count is recomputed from the merged tree as 246 (183 Python + 63 JS) and the version stays at upstream 1.10.0 (server_version, the runtime version field and the wrt PKG_VERSION all agree). The invite entry's English assertion count is corrected from 17 to 19, matching the 19 checks in `tests/_test_invite_panel.py`.

- **账号行新增「邀请」入口：看邀请码 + 手动受邀（仅国内版）**：活动页 `https://www.workbuddy.cn/events/invite/` 上并没有「绑定」按钮——只要 URL 带 `?inviteCode=`、登录态就绪，页面自己就会 POST `/bind`；邀请码也只有登录后从 `/my-code` 才读得到。现在账号行操作区多一枚「邀请」，点开面板分两段：**当前账号的邀请码**（邀请码本身而不是分享链接，可一键复制）与邀请进度（已邀请 / 有效 / 积分上限，口径同活动页），以及「受邀」输入框——把别人的邀请码填进来手动绑一次。上游的业务拒绝（`12310` 已绑过 / `12311` 非活动期新用户 / `12313` 自己的码 / `12314` 不适用 / `12319` 不存在）按原因显示，不会被包装成「请求失败」；国际版账号与静态 API Key 账号不画入口（前者没有这套活动，后者没有个人身份）。只读读码不落盘，日志只记 uid 前缀、邀请码长度与业务码。新增 `wb_invite.py`、面板路由 `/accounts/invite` 与 `/accounts/invite/bind`、`tests/_test_invite_panel.py`（19 项）。 / An "Invite" entry on every CN account row: one panel that shows the account's invite code (the code itself, not a share link) plus its invite progress, and a field to bind someone else's code manually. The activity page has no bind button — a page load carrying `?inviteCode=` binds automatically once signed in, and the code is only readable from `/my-code` while signed in. Upstream business rejections (already bound / not a new user during the campaign / your own code / wrong activity / unknown code) are shown with their reason instead of being reported as a request failure; intl accounts and static API-key accounts get no entry. Reads are not persisted, and logs carry only the uid prefix, the code length and the business code. Adds `wb_invite.py`, the `/accounts/invite` and `/accounts/invite/bind` panel routes, and `tests/_test_invite_panel.py` (19 checks).

- **合并上游 v1.9.0（本地优先）**：把 `origin/main` 的 25 个提交（v1.9.0 与 #649/#650/#652/#653/#669/#670/#671/#672/#684/#686）并入本地主线。冲突只有三处，全部按「本地实现优先、上游能力一条不丢」处理：`wb_proxy.py` 的 @ 路径段保留本地那份空白用 `\s+`（能容纳换行排版）的规则，同时吸收 #683 的实测结论与 issue 引用（同一指纹只留一份实现）；`tests/_test_sanitize_fingerprint.py` 两个测试类都保留，一起钉这份实现（本地口径 + #683 的整段五句/作用域/同名 @ 文本断言）；README 的套件计数按合并后的树重算为 232（173 Python + 59 JS），并把历史上叠出来的 11 行旧计数合并成一行。 / Merge upstream v1.9.0 with local priority: the 25 commits on `origin/main` (v1.9.0 plus #649/#650/#652/#653/#669/#670/#671/#672/#684/#686) are now in the local line. Only three files conflicted, all resolved as "local implementation wins, every upstream capability kept": the @-path rule in `wb_proxy.py` keeps the local `\s+` whitespace (it tolerates line-wrapped paragraphs) and absorbs #683's measurements and issue references (one implementation, not two); both test classes in `tests/_test_sanitize_fingerprint.py` stay, pinning that single implementation to the local and the #683 assertions alike; and the README suite count is recomputed from the merged tree as 232 (173 Python + 59 JS), collapsing the eleven stale count lines that had accumulated.

- **合并时修掉三处本地自相矛盾（合并前就已红）**：① `wb_fingerprint.DESKTOP_TRIPLES["cn"]` 还是拆分前的旧三元组（5.8.4 / 2026-09-11 打包），而 headers 侧 `wb_identity.DESKTOP_VERSION_CN` 已是 5.8.3（2026-10-18 两区实跑）——同一台「设备」在两个通道上报不同版本，正是本仓最忌的指纹矛盾；现对齐到本地提交里记录的那份国内版三元组（5.8.3 / `db0e9b…` / 2026-10-15 打包），并新增断言把上报三元组与 `wb_identity` 的版本号钉在一起：以后只改一处就红。② `wb_entitlements.py` 是本地提交重新引入的模块，但 v1.9.0 已按 #505/#609 把它连同 `accounts/model_entitlements.json` 一起删除（「Pro Only」改由目录 tier 表驱动），且全仓无任何 import——按上游的删除口径移除，不再有第二套事实来源。③ `_test_agents.py` 的一键配置断言会读到开发者本机 `accounts/settings.json` 里的勾选清单（CI 无此文件，所以只在带账号数据的机器上假红），已把 `wb_proxy.ACCOUNTS_DIR` 钉到空目录。 / Three local self-contradictions that were already red before the merge: (1) `wb_fingerprint.DESKTOP_TRIPLES["cn"]` still carried the pre-split triple (5.8.4, packaged 2026-09-11) while the header side, `wb_identity.DESKTOP_VERSION_CN`, had already moved to 5.8.3 (two-realm live run on 2026-10-18) — one "device" claiming two versions, exactly the fingerprint inconsistency this repo avoids. It now matches the CN triple recorded by the local commit (5.8.3 / `db0e9b…` / packaged 2026-10-15), and a new assertion ties the report triple to `wb_identity`'s version so editing only one side fails. (2) `wb_entitlements.py` was reintroduced by the local commit, but v1.9.0 removed it together with `accounts/model_entitlements.json` (#505/#609, "Pro Only" is catalogue-tier driven) and nothing imports it — it is gone again, so there is no second source of truth. (3) `_test_agents.py`'s one-click assertion read the developer's own `accounts/settings.json` model selection (CI has no such file, so it only went red on machines with account data); `wb_proxy.ACCOUNTS_DIR` is now pinned to an empty directory.

- **11-128：@ 路径说明段的连续文本指纹**：DSH 的系统提示里 `Tokens prefixed with @ are paths the user explicitly referenced.` 紧跟着 `Relative paths resolve from the workspace root; absolute paths identify files or directories on the host.`，上游按「连续文本」判 400 / 11-128——**单独一句各 200，连排必 400**；且只改第二句无效，改第一句才失配。规则锚定第一句整句，只在 `are paths` 后插入一个 `that`（`… are paths that the user explicitly referenced.`）：一个词都不删、第二句原样保留，句意不变。作用域沿用既有口径（`system` / `developer` / `assistant`，`user` / `tool` 不改写），句子之外的同名文本不受影响；命中判定仍走字面量快路径（先 `in` 探测再跑正则），热路径开销不变。新增 10 项断言。 / Another 11-128 channel fingerprint: the @-path paragraph DSH ships in its system prompt. `Tokens prefixed with @ are paths the user explicitly referenced.` immediately followed by `Relative paths resolve from the workspace root; absolute paths identify files or directories on the host.` trips the upstream's contiguous-text check — **each sentence alone answers 200, the pair always answers 400**, and editing only the second sentence does not clear it while editing the first does. The rule anchors the whole first sentence and inserts a single `that` after `are paths` (`… are paths that the user explicitly referenced.`), deleting no word, leaving the second sentence intact and the meaning unchanged. Scope follows the existing convention (`system` / `developer` / `assistant`; `user` / `tool` untouched) and the same text elsewhere in the prompt is unaffected; detection keeps the literal fast path (an `in` probe before the regex), so hot-path cost is unchanged. Ten assertions added.

- **成长任务：补齐「发现应用」与四条专家体验任务的判据链**（截图复现：它们一直显示「进行中 0/1」，一键做任务也点不亮）：四个桌面端任务被本仓按「只认桌面端真实操作」跳过，`expert_use_*` 则根本没登记——任务被接取成功了（所以是「进行中」），但永远没有动作去推进。上游判据不是单独端点，而是同一 `POST /v2/report` 上的**整套桌面指纹 + 完整事件链**：`ideName/ideType=WorkBuddy`、`extName=workbuddy-desktop`、按 realm 分开的 `commit`/`releaseDate` 三元组（国内版 5.8.3、国际版 5.8.4）、国内版才带的 `qimei36`。现在 `Buddy_App`/`Buddy_App_QQ` 发 buddyapp 五连事件，`RichMeow_Chat` 发成功对话 6 事件链，`Library_read` 走 web 域 `web_element_click`，`expert_use_*` 先用任务 `jump_url` 里的专家 id 在市场结果里**精确落位**（同名条目不取首条），再发召唤链 → 带 `X-Expert-Id` 的真实对话取服务端 requestId → `expert_actual_use(mode=LOCAL, type="", cost=0)`。桌面链的异步计分比普通事件慢，回读窗口放宽到约 20 秒；链本身没发出去时直接判失败，不再空等或领一个必然失败的奖。实测 baka 账号（与截图同款状态）：`Buddy_App` 0/1→1/1 +100、`RichMeow_Chat` 领奖 +100、`Library_read` 0/1→1/1 +100、四条专家任务各 0/1→1/1 +50，共 +500 积分全部到账；新增 `tests/_test_growth_experience.py`（11 项）。 / Growth tasks: complete the criterion chains for the 「发现应用」 and expert-experience tasks (reproduced from the reported screenshot: they sat at "in progress 0/1" and one-click could not light them). The four desktop tasks were skipped as "desktop-only" and the `expert_use_*` codes were never registered, so they were accepted (hence "in progress") but had no action to advance them. The criterion is not a dedicated endpoint: it is the full desktop fingerprint plus the complete event chain on the same `POST /v2/report` — `ideName/ideType=WorkBuddy`, `extName=workbuddy-desktop`, a realm-specific `commit`/`releaseDate` triple (CN 5.8.3, global 5.8.4) and the CN-only `qimei36`. `Buddy_App`/`Buddy_App_QQ` now send the buddyapp five-event chain, `RichMeow_Chat` the six-event successful-chat chain, `Library_read` the web-domain `web_element_click`, and `expert_use_*` resolves the expert id from the task's own `jump_url` against the market list (never the first same-named hit), sends the summon chain, performs a real chat with `X-Expert-Id` to obtain the server requestId, then reports `expert_actual_use(mode=LOCAL, type="", cost=0)`. Desktop scoring is slower than plain events, so the read-back window is about 20 s; a chain that cannot be sent now fails fast instead of waiting or claiming a guaranteed 400. Verified live on the baka account (same state as the screenshot): `Buddy_App` 0/1→1/1 +100, `RichMeow_Chat` claimed +100, `Library_read` 0/1→1/1 +100, the four expert tasks 0/1→1/1 +50 each — +500 credits total. Added `tests/_test_growth_experience.py` (11 checks).

- **用量聚合缓存跳过写盘时不再静默停更**：checkpoint 写盘因状态锁被占、状态暂不可序列化或写入异常而跳过时，按类节流告警并登记后台异步补写（30 秒起指数退避，封顶 15 分钟）；补写成功立即取消，失败继续重试。新增 64MB checkpoint 落后告警、蓝绿双进程临时文件隔离，避免 `remaining` 一类缓存连续多日不落盘、重启后反复全量重折。
- **设置页分组在正體中文 / 英文界面不再整页空白**：分组胶囊靠各区块的 `h2` 标题文字比对归类，界面语言切到正體中文或英文后标题已被 i18n 换掉，比对全部落空、每个区块都归到「日志与系统」，于是点「基础 / 自动化 / 稳定性」时把整页 section 全部 hidden（看起来设置页清空）。现在改用 i18n 翻译前保留的原文比对，三种语言的分组结果一致；另补上漏归的「选择网页活跃提示词」（原来被归到「日志与系统」）。
- **账号分组**（#707）：账号新增可选分组，支持按组筛选、导入时指定分组、单账号编辑、分组启停，以及刷新凭证 / 测试 / 补积分等批量操作仅作用于当前分组；API Key 账号选择器也支持按组选入与移除。
- **API Key 配置示例**（#704）：设置页新增可折叠的 Base URL、cURL 与各协议端点示例，并支持一键复制。
- **检查更新支持代理槽**（#798）：可在设置页指定 GitHub 更新检查使用的代理槽；槽停用或删除后自动回退直连。
- **会话粘滞修复**（#718）：小账号池的长会话不再按页轮换账号，避免前缀缓存丢失和 Token 消耗翻倍。
- **请求体超限 413**（#799）：先返回 413，再在有限时间内排空上传，避免连接重置吞掉响应。
- **CodeArts 参数与模型 ID**（#794 / #797）：输出 token 按模型上限收敛、`stop` 字符串归一化；参数错误返回 400 且不冷却账号。`deepseek-v4.1-flash` 与 `-1017` 为独立模型，精确匹配。
- **提示词改写与模型倍率**（#796 / #774）：恢复退化为空操作的 `SANITIZE_REWRITES`；live 目录的 `x0.00` 不再覆盖已知付费倍率。
- **风控连坐暂停保护可配可立即解除**：设置页「稳定性」新增「风控连坐暂停保护」卡片。上游 403 / 11140 异常行为触发全区域暂停派发时，面板展示实时剩余倒计时，提供「立即解除暂停」一键解冻恢复请求；支持自定义暂停时长（默认 1800 秒，设为 0 可彻底关闭连坐熔断保护），且保存更短时间时即时截断现有倒计时。
- **账号多时面板更顺**：账号表改为客户端分页（每页 50 个，排序与筛选作用在全部账号上再切页；改区域 / 改筛选 / 点表头回第 1 页，账号变少时页码夹回最后一页）；15 秒账号轮询拿回的数据与视图都没变时不再整表重画，且只在显示账号数据的页签（网关、账号、任务，新导航的总览）上跑，切回这些页签时立即拉一次；自动补积分改为只点名缺积分的号（`POST /accounts/credits` 新增 `uids` 列表参数，非列表回 400），每个号每次页面加载最多补一次，不再触发全池逐个刷。手动「一键刷新积分」不变。
- 移除已废弃的 `WB_DEEPSEEK_FLASH_FORCE_SG` 文档行与两个恒返回 `False` 的存根函数（#776）。
- **CodeArts 模型倍率**：`/v1/models?realm=codearts` 的条目新增 `credits`（如 `x0.7`，与 WorkBuddy 目录同一写法），取自上游模型目录的标准档；错峰优惠档不计入，上游没有倍率的模型不带此字段。
- **改善 Claude Code 兼容性**（#733）：`sanitize` 现在把
  `You are Claude Code, Anthropic's official CLI tool for Claude.` 整句中性化；
  旧规则只把 `CLI for Claude` 改写成 `CLI tool for Claude`，反而保留了
  `You are Claude Code` 指纹。覆盖大小写与弯引号，`user` / `tool` 内容不改写。
- **添加账号时可指定登录出口代理槽**：OAuth 登录弹窗新增「登录出口代理」下拉（只在配置了启用的代理槽时出现），申请授权链接、等待回调与拉取账号资料都走选中的槽，登录成功后账号绑定到该槽，避免登录 IP 与后续调用 IP 不一致。默认「直连（不走代理槽）」，与以前完全一样；选「自动」(`proxySlot: "auto"`) 时随机挑一个没绑定账号（含 CodeArts 账号）、也没被其他进行中登录占用的槽，没有空闲槽则直连。已绑定槽的账号用「自动」重登会保留原槽；槽绑定不写进账号的旧版 `proxy` 字段。`/accounts/login/start` 的日志与响应只给代理的 host:port，不含用户名密码；不存在或已停用的槽返回 400。
- 启动检查不再把"端口能连上但一直不答"当成端口空闲。此前 `--probe-only` 用 2 秒超时探 `/health`，卡死的实例只会让它超时，于是判定端口可用、又叠了一层实例；Windows 的 `SO_REUSEADDR` 允许重复监听，内核仍把新连接分给卡死的那个，看板与日志查看器就一直是空的。现在这种情况明确报错（退出码 1）并给出占端口 PID 的查法，不再静默重复启动。
- 部署入口改用 `python3 -m wb_proxy`（OpenWrt init 与 Dockerfile）：同一份代码实测空闲内存少 47-54 MB（#702 / #777）。
- 新增 `WB_DUMP_11_128` 本地取证开关（默认关闭）：`1` 只写脱敏摘要，`full` 额外写出站
  body，文件落在 `usage/11-128-dumps/`；用于定位 Claude Code 专属 11-128 的真实请求差异
  （#733）。摘要不含提示词明文，`full` 含明文但由使用者显式开启。
- **国际版每日活跃总开关**：设置页「国际版每日活跃打卡」新增「定时自动打卡」勾选框（`settings.json` 键 `daily_activity`，`/settings/save` 只收 JSON 布尔）。缺省开启，老安装行为不变；关掉后调度器不再自动跑每日活跃（定时时段、立即巡检保活、启动补跑都跳过，启动补跑留到重新打开后再消费），账号上的手动打卡不受影响。
- **用量缓存写盘不再拖住其他视图**：checkpoint 写盘收集各类聚合状态时，状态锁改为非阻塞尝试；某一类正在锁里全量重折（GB 级 `usage.jsonl` 冷启动要几十分钟）时这一类本次跳过、下次再写，不再连带 `/usage/by-account` 等视图一起卡住（面板「账号加载失败」/ Cloudflare 524）。

完整历史版本与详细变更日志请查阅 **[docs/CHANGELOG.md](docs/CHANGELOG.md)**。

---

## 八、致谢与引用声明 (Credits & References)

在协议逆向、风控规避、任务链路与工程化设计过程中，本项目参考、吸纳并致谢以下优秀开源项目与技术成果（排名不分先后）：

### 核心逆向与协议参考
- **[Sliverkiss/workbuddy2api](https://github.com/Sliverkiss/workbuddy2api)**：成长任务逆向、设备指纹派生（`derive_id`）、调度器（`Scheduler`）与 `reasoning_content` 回填设计；
- **[L0NE-6/WorkBuddy-Daily](https://github.com/L0NE-6/WorkBuddy-Daily)**：国内版微信小程序专属事件指纹与动态专家深链任务模型；
- **[88lin/workbuddy-auto-signin](https://github.com/88lin/workbuddy-auto-signin)**：猫猫日常旅行与成长能量开盲盒（Buddy 盲盒）安全生命周期；
- **[linguo2625469/workbuddy2api-panel](https://github.com/linguo2625469/workbuddy2api-panel)**：国内版连登管家闭环逻辑与轻量对话活跃上报事件；
- **[Zhengyuuuui/workbuddy2api](https://github.com/Zhengyuuuui/workbuddy2api)**：国际版 11140 风控限制识别、冷却规避与故障排查清单；
- **[yuanyuanyuan430/workbuddy2api-hub](https://github.com/yuanyuanyuan430/workbuddy2api-hub)**：国际版 EdgeOne CDN 证书错配排查与活跃上报优雅降级方案；
- **[CangShui/workbuddy-cliproxy-fix](https://github.com/CangShui/workbuddy-cliproxy-fix)** & **[lovingfish/workbuddy-cliproxy](https://github.com/lovingfish/workbuddy-cliproxy)**：早期客户端代理修复与网关通信原型；
- **[mmqz/cpa-multi-plugins](https://github.com/mmqz/cpa-multi-plugins)**：多插件管理与出站调度结构参考；
- **[ardeyouxipianyi/workbuddy2api](https://github.com/ardeyouxipianyi/workbuddy2api)**：国内版早期分发包逆向分析与出站 User-Agent 规范；

### 工程化与生态基础
- **[aodianjun/workbuddy2api-hub](https://github.com/aodianjun/workbuddy2api-hub)**：OpenWrt 路由器打包配方（`.ipk` / `.apk`）与系统服务支持；
- **[astral-sh/python-build-standalone](https://github.com/astral-sh/python-build-standalone)**：Windows 便携版免安装精简独立 Python 运行时构建基石；
- **[deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)**：DSH 客户端协议与提示词指纹清洗规避参考。

感谢所有向本项目提交 PR、反馈 Issue 与分享实测样本的社区贡献者！

---

## 九、免责声明 (Disclaimer)

本项目仅用于协议学习与个人开发测试，不提供任何商业服务或可用性担保。因使用非官方客户端产生的账号风控、限制或封禁由使用者自行承担，请优先使用官方客户端。

## ⭐ Star 趋势

<p align="center">
  <a href="https://star-history.com/#ardeyouxipianyi/workbuddy2api-hub&Date">
    <img src="https://api.star-history.com/svg?repos=ardeyouxipianyi/workbuddy2api-hub&type=Date" alt="Star History Chart" width="760">
  </a>
</p>

# 长期开发计划 (Long-Term Development Plan)

## 终极目标

一个真正可运行、可交付的个人求职操作系统 (AI Career OS)：简历 → 知识库 →
岗位发现 → JD 情报 → 证据约束匹配 → 定制材料 → 模拟面试 → 申请管理 → 成长与
薪酬 → 数据可携带，全部闭环；并且从"问了才答"进化为"替你先做"——定时摄取、
主动提醒、通知中心、每周摘要、语音面试、移动端与生产级交付。

## 当前状态 (2026-10-30)

- **前端**: 897 个 vitest 通过（88 个文件）；`tsc --noEmit` 干净（含并发会话在制的前端增补）。
- **后端**: 非 IT 选集 **1067 条全绿**（`mvn -o -B -Dtest="!*IT" test`；1037 基线 +
  41.1 的 19 条 + 42.1 的 4 条 + 并发会话在制的 7 条导出/导入测试）；含真实栈 IT 的全量（1128 条基线上
  再加本单元与并发会话的新测试）待下一次 `mvn -o -q test` 复核。
- **ai-service**: 1903 passed, 48 failed, 1 skipped（offline: mock/hash）。48 条失败全是
  37/38 新增人口留下的跨语言 census 漂移，在 39.2 父提交的干净检出上逐条重现，已列为
  下一单元；39.2 不新增失败。
- **E2E**: 24/24 golden journey（最近一次真实栈验证）。
- **分支**: main 与 origin 同步（本次推送后）。
- **已完成**: Epic 0–38 全部勾选，Epic 39 进行中（39.1–39.2 已勾选）；38（账号够到自己的动词）在 38.5 收口。36（登录的第二道门）在 36.4 收口：设置页
  安全卡、登录第二步、种子与丢手机的 SECURITY 说明、runbook 的锁门处置。
  最近一段是 19.1–19.9（保存的搜索、定时摄取、通知中心、语音面试、离线壳、
  夜间报告落板）、20–33（部署自检、来信离楼、
  收件箱离应用、退订、导出、开放入口、改地址、邮件计量、遗忘、搜索、后端
  census 补齐、壳层加固、答案留痕、浏览器唤醒）、34（提醒以 RFC 5545 日历
  订阅离开应用，设置页交出签名地址）、35（分钟时钟按提醒自己的时刻响，
  日历事件自带 VALARM）与 36（第二道门的四段：注册/激活、登录第二步、
  换发/关闭、设置页安全卡与登录码字段）与 37（回信的三段：签名入站地址与
  服务商 webhook、双语线索先读的引擎、公司名匹配归档与 `/replies` 页，
  设置页交出地址）。37.4 以 850 个前端测试、81 个文件收口。38.1 先让 26.1 的信落地（确认页四态），以 857 个前端测试、82 个文件收口；38.2 让设置页
交出改地址卡（两封信、四种拒绝各归其位），以 863 个前端测试、82 个文件收口。38.3 让设置页
交出会话卡（每行一段登录、当前这台标出、单关/全关与已关的诚实状态），以 869 个前端测试、83 个文件收口。38.4 让设置页
交出改密码卡（当前密码 + 两遍新密码、成功态说出全部后果），以 874 个前端测试、84 个文件收口。38.5 让设置页
交出销号卡（什么走、什么留下、密码 + 回打地址、确认后才 POST），并让账号在成功后落在公开的
`/account-erased` 页上（token 对丢弃、整页导航离开、无会话也能说清结局），以 877 个前端测试、85 个文件收口。
随后 **Epic 41.1**（提醒到点时的信）以 19 条新后端测试收口，非 IT 选集 1063 条全绿；
**41.2** 让这口钟有了自己的警报（`alerts.yml` 十一条、拒绝计数改说两种信、9 条闸门测试绿）；
**42.1** 让邮件设置不再只住在旧信里（`GET /me/mail/settings` + 设置页邮件卡，4 条后端测试绿）。

## 主线队列（按顺序执行）

1. ~~**13.1 收尾 — Markdown 导出面**~~ 已完成：ai-service 的 render 路由接受
   `format: "markdown"`（与打印文档同节序同词句，diff 工具可读），backend 桥
   原样转发，`/data` 页多一个“下载 Markdown”按钮，API.md 记下三种格式与
   PDF 转换器缺席时返回 HTML 的理由。

2. ~~**13.2 收尾 — 恢复的删除语义**~~ 已完成：`current_state` 补齐 bundle 的
   全部 10 个 section（六个 ai-service 自读、backend 的四节由桥送来）；按 id
   匹配的六节（profile、applications、growth_plans、notes、contacts、
   job_descriptions、interviews）把"包内已无此行"计划成 `delete`，重新摄取的
   三节（resumes、knowledge、memories）按内容或 `(kind, key)` 匹配、永不删除；
   `skip` 的哈希只覆盖 apply 真正写入的字段，apply 逐段报告 `unchanged`。

3. ~~**17.1b 收尾 — 41 条文案 census**~~ 已完成：census 归零
   （`everyOffender()` 为空，`KNOWN` 与 `regen-known.mjs` 一并删除；
   `/growth`、`/offers`、auth 表单、JD 对话框、设置卡片的文案全部走
   `translations.ts` 双语键，字段校验改为返回 `TextIssue`）。

4. **Epic 19 — Proactive Career OS**
   ~~19.1 保存的搜索~~ 已完成：`/saved-searches` GET/POST/DELETE（`V11` +
   服务/控制器，11 个后端测试），criteria 以看板自己的筛选名存成规范 JSONB；
   前端 `lib/saved-search.ts` 负责 URL 状态 ↔ criteria 的双向翻译，`/jobs`
   侧栏的 `SavedSearchPanel` 保存/应用/删除（删除走确认对话框）。
   ~~19.2 定时摄取~~ 已完成：`V12` + `IngestionFeedController`（`/ingestion`
   7 条路由，feeds 每用户 ≤20），`IngestionScheduler` 按 03:20 扫启用订阅，
   `ScheduledIngestionService` 复用 14.3 的确定性引擎并把计划存成 run
   （只记录、不落库改写职位板）；`FeedUrls`/`HttpFeedFetcher` 拒绝私网地址
   并逐跳复核重定向、封顶 5 MB；失败拉取是 `200` 的 failed run 及其原因。
   导入页顶部新增订阅面板（增删改开关、立即运行、运行历史、展开计划）。
   ~~19.3 通知中心~~ 已完成：`V13__notification_states.sql` +
   `NotificationController`（`/notifications` GET + read / read-all / dismiss）。
   不建通知表——条目在读取时从已知来源合成（仪表盘的 14 天 attention 查询
   与最近 7 天的 run），因此条目永远不会和它指向的屏幕不一致；只持久化读者
   状态，按 episode 建键（提醒/久置/每次 run），新 episode 重新变未读，
   当前列表之外的键一律忽略，每次写入返回全新的收件箱。`/notifications`
   页按 kind + 空洞在读者语言里组句，可标记已读、忽略、全部已读并深链回
   申请板 / 运行历史 / 导入页。
   ~~19.4 每周摘要投递~~ 已完成：`V14__weekly_digests.sql` +
   `WeeklyDigestController`（`/digests` GET + `/digests/run` POST），周一
   08:00 的 `WeeklyDigestScheduler` 为每位有申请的用户写下刚结束的一周。
   payload 是冻结快照，重读不会按已变化的数据重算；同一周重写按
   `(user_id, week_start)` 唯一键原地替换；`week_start` 存日期并约束周一，
   读者无从把时间戳换算回周日。来信通过新的 4 参 `insightDigest` 向引擎要
   自己的 7 天窗口（仪表盘保持 14），单个用户失败只记日志、不拖累他人。
   分析页开头的来信卡展示四个数字、最久未动的停滞行与更早来信历史，并可
   手动"生成本周"；`formatDateOnly` 把纯日期按 UTC 呈现。13 个后端测试，
   doc/wire/DTO/paging 门禁全绿，617 后端测试，724 vitest。
   ~~19.5 单版本打印~~ 已完成：ai-service `POST /internal/features/render-resume`
   + `export_render.resume_to_html`（结构化正文按 export 的节序与读者语言排版，
   未解析的版本退回其纯文本），backend `ResumeService.printHtml` 只读该用户
   的版本行、`ResumeVersionController` `POST /resume-versions/{id}/print`
   返回 `{html}`，前端 `usePrintResumeVersion` 在点击手势内先开窗口再写文档
   （弹窗拦截只影响提示，不影响结果），入口在定制面板"打印此版本"与简历
   详情页每个版本的打印按钮。10 个 ai-service 渲染测试、3 个 service 测试、
   11 个 controller 测试，doc/contract/paging 门禁全绿。
   这是"OS 替你先做"的第一层。

5. ~~**Epic 20 — 单版本打印**~~
   ~~定制简历的独立打印视图（复用 export_render 的排版与语言机制），
   让"tailor → 下载 PDF"成为一条完整路径，而不是只打整个数据包。~~
   已完成（19.5，见上）。下一步：19.7 移动端 / PWA（已完成，见下）。

6. ~~**Epic 21 — 语音模拟面试**~~
   ~~STT/TTS 的 provider 接缝 + 面试页的录音/播放；文本面试已有的评分与轨迹
   不重写，只把输入输出换成声音。~~
   已完成（19.6）：ai-service 新增 `Voice` 接缝（`VOICE_PROVIDER=none` 默认、
   `openai_compat`、`mock`——mock 在 prod 被拒），三条内部路由
   （status / transcribe / speak）与四个类型化拒绝；backend `VoiceService`
   在任何语音预算花出之前先验会话归属（别人的 session 直接 404），空转写与
   空音频回 `AI_SERVICE_EMPTY_RESPONSE`，状态路由 best-effort——ai-service
   挂了页面仍有浏览器自带的语音；面试页一个麦克风按钮（MediaRecorder →
   base64 → provider，或部署没有耳朵时用浏览器 SpeechRecognition）和一个
   朗读按钮（provider 的音频，或 speechSynthesis），录音两分钟封顶，麦克风
   被拒有一句人话，文本框始终在。13 个 ai-service 测试、9 个 controller 测试、
   3 个桥接测试、10 个前端 helper 测试。下一步：19.7 移动端 / PWA。

7. ~~**Epic 22 — 移动端 / PWA**~~
   ~~可安装外壳、离线壳、响应式审计（侧栏、看板拖拽、表格滚动）。~~
   已完成（19.7，见 ROADMAP）：manifest + Service Worker + 离线壳页 + 四个
   图标；worker 只预缓存离线页与图标，导航走网络、断网落离线页，构建产物
   `_next/static` 缓存优先并后台刷新，`lib/pwa.ts` 只在生产构建注册；看板
   拖拽手柄补齐 `touch-none`；`pwa.test.ts` 钉住三份文件与四个 PNG。
   下一步：19.8 真实板卡连接器（已完成，见下）。

8. ~~**Epic 23 — 真实板卡连接器**~~
   ~~Greenhouse / Lever 公开 board API 接入既有 `Connector` 协议；
   RSS/JSON 粘贴路径保持为离线后备。~~
   已完成（19.8，见 ROADMAP）：backend 新增 `BoardConnector` 接缝
   （`source()` + `apiUrl()`）与 `BoardConnectors` 选择器——读者给板卡令牌、
   招聘板页面地址或 API 地址，connector 一律落成抓取器要打开的 API URL
   （Greenhouse 补 `content=true`，Lever 补 `mode=json`，EU 页面落
   `api.eu.lever.co`）；认不出的地址回 `FEED_BOARD_INVALID`，所有板共用一句
   读者能照做的说明。跑订阅时把订阅名作为 `company` 传给引擎（板卡负载不带
   公司名，职位自带的公司名仍优先）；engine 的规范化器学会两种负载
   （Greenhouse 的 `jobs` 包装、转义 HTML `content`、`first_published`、字典
   位置；Lever 的裸数组、`text`、`hostedUrl`、毫秒 `createdAt`、
   `categories`、`workplaceType`），按秒读秒级时间戳，规范四值之外的
   commitment 词保留默认值而不是硬造。面板的来源改为三选一，URL 占位与命名
   提示随选择变化。7 个 ai-service 测试、12 个 connector 测试、3 个 service
   测试、1 个前端 helper 测试，658 后端测试，740 vitest。
   下一步：19.9 交付硬化。

9. ~~**Epic 24 — 交付硬化**~~
   ~~夜间备份 + 恢复演练、指标与告警、运行手册更新；把 nightly 的
   eval/IT 结果变成可查的历史而不是日志。~~
   备份与恢复演练、指标/告警、RUNBOOK 已完成并提交（19.9，见 ROADMAP）；
   nightly 结果的可查历史（`nightly_reports` + `/monitoring/nightly-reports`）
   由并发会话在制（V15 与监控页），提交后本项收尾。
   下一步：下面的 Epic — 夜晚的计划落到板上。

10. **Epic — 夜晚的计划落到板上（ingestion apply）**
    19.2 起的每次 pull 都把引擎的 create/update/close 计划存进 run，却从未
    写过职位板：backend 至今没有任何创建 `jobs` 的代码路径，职位只来自 seed。
    "替你先做"因此停在"它看见了"。本 Epic 补上最后一段：
    - `POST /api/v1/ingestion/runs/{id}/apply`：只接受本人、`completed`、
      且未应用过的 run；在一个事务里按计划建公司/职位、刷新已存在的行、
      把计划里 close 的职位置为 closed，并把 `applied_at` / `applied_counts`
      写在 run 上（`V16`）。重复应用是 `409`，不是第二次写入。
    - 计划里的行没有 `posted_at`：职位板的 age 一直是"在板上待了多久"，
      apply 让 `@CreationTimestamp` 继续承担这个定义。
    - 前端运行历史每一行显示"应用此计划"（已应用则显示时间），应用后
      就地更新三个计数；API.md 记路由与两个新错误码。
    - 测试：apply 的建/更/关、公司按名复用、重复应用拒绝、非 completed
      拒绝、跨用户 404；两个前端 helper 测试。
    - 已完成并提交（a0eb950）：`V16` 给 run 加 `applied_at` / `applied_counts`，
      悲观锁读取、`ApplyResult`、两个错误码与 census pin（9 个 service 测试 +
      4 个路由测试）；运行历史每行一个“应用此计划”，已应用则显示时间；API.md
      记下路由与两个新错误码。职位板从此第一次由夜晚的 run 写入。

11. **Epic 33 — 浏览器被叫醒（Web Push）**
    通知中心已经写在收件箱里，但读者必须打开页面才看得见。本 Epic 让 03:20 的
    摄取 sweep 与 08:00 的来信在浏览器里发出声音：VAPID 签名的 Web Push。
    - ~~33.1 订阅登记~~ 已完成（8ea4878）：`V24__push_subscriptions.sql` +
      `/push/subscriptions` 的 POST/DELETE（订阅按 endpoint 唯一，删行只看本人），
      前端 `lib/push.ts` 只负责把 `PushSubscription` 折成后端要的形状。
    - ~~33.2 签名的唤醒离开大楼~~ 已完成：`PushSender` 出站端口
      （`SENT` / `GONE` / `REFUSED` / `NOT_CONFIGURED`）与 VAPID 传输
      （RFC 8030/8292：ES256 JWT 的 `aud` 是 endpoint 的 origin、`TTL` 头、
      空 body；404/410 回 `GONE` 由调用方删行，其他拒绝只计数不重试；
      无键时 `NoopPushSender`，半对键启动即拒绝）。`VapidKeys` 接受 raw
      32 字节或 PKCS#8 私钥并用探针签名验键对。8+7+6 个新测试，872 个
      非 IT 后端测试全绿；配置门禁 33 leaves / 21 readers / 24 fields。
    - ~~33.3 晨间 sweep 发出声音~~ 已完成：`V25` 给 `notification_states` 加
      `pushed_at`（每 episode 一条 ring latch，与邮件的 `notified_at` 互不
      读取）；`awaitingPush` 只取未读、未忽略、未 ring 的条目，一次合并的
      wake 扇给该账号的每台浏览器；至少一台接受才写 latch，`GONE` 当场删行，
      无键的 no-op 不写 latch；`NotificationPushService` 接在 07:30 的定时器
      上（邮件之后，两半各自捕获异常），`careeros.push.delivery` 按
      `sent`/`gone`/`refused`/`not_configured` 计量。8+2+3+3 个新测试，
      886 个非 IT 后端测试全绿；顺带修掉两个 Micrometer 弱引用导致的
      `NaN` flake。
    - ~~33.4 浏览器被叫醒并打开~~ 已完成：`public/sw.js` 处理 `push`
      （浏览器语言的一句话、`careeros-inbox` 合并气泡、`/notifications` 深链）、
      `notificationclick`（已有收件箱标签页则聚焦，否则打开）与
      `pushsubscriptionchange`（用旧 key 重订阅并把新登记 postMessage 给任一
      打开的标签页）。worker 不持令牌：刷新令牌复用会吊销整条 family，同源标签页
      也可能属于不同账号，所以通知不带计数/标题，收件箱由打开的页面自己读。
      设置页的开关（`push-card.tsx`）每次从浏览器重读状态，授权 → 用构建期
      `NEXT_PUBLIC_VAPID_PUBLIC_KEY` 订阅 → 注册，注册失败回滚本地订阅，关闭时
      先 unsubscribe 再删本机那一行；compose 把 `APP_PUSH_VAPID_PUBLIC_KEY` 传成
      前端构建参数，一个变量填两半。27 + 1 个前端测试，829 个前端测试 / 77 文件
      全绿，`tsc` 干净；copy census 136。

12. ~~**Epic 34 — 提醒离开应用（日历订阅）**~~ 已完成：
    后端 `GET /api/v1/calendar.ics?token=…`（无会话，链接即凭证）把该账号每个
    带 `reminder_at` 的申请导成 RFC 5545 文档。新建的 `SignedLink` 抽出 HMAC
    工具，邮件退订与日历共用 `APP_MAIL_LINK_SECRET` 但以用途前缀域分离（两种
    token 互不通用，轮换密钥同时作废全部地址）；`UID` 稳定（改订阅是更新而非
    复制）、`DTSTAMP` 取行自身 `updated_at`（回退 `created_at` 再回退提醒时刻，
    轮询不产生假变更）、30 分钟 `DTEND`、`TRANSP:TRANSPARENT`、75 字节折行与
    TEXT 转义（中文长标题按八位组折，不切半个字）。过期提醒保留——日历是看板
    的镜像，清空提醒才消失；空日历合法；伪造、轮换、缺失与已删账号统一 404
    `CALENDAR_LINK_INVALID`，响应 `text/calendar` + `no-store` + `noindex`。
    `GET /calendar/link` 给设置卡片签名地址；前端 `useCalendarLink` +
    `calendar-card.tsx`（只读地址 + 复制，双语键），`endpoints.test` 的
    `NEVER_REFERENCED` 记下"浏览器从不自己请求 feed"的理由。门禁随人口移动
    （copy census 137、查询参数 44/20）。22 个日历后端测试；API.md、
    architecture.md、DEPLOYMENT、SECURITY 同批更新。

13. ~~**Epic 35 — 提醒按时响（分钟时钟 + 日历闹钟）**~~ 已完成：
    后端 `ReminderScheduler` 用 fixed-delay（`careeros.reminders.tick-ms`，默认
    60000）每分钟问一次 `ApplicationRepository.findUserIdsWithReminderBetween`
    "上一拍到现在有哪些账号的提醒到期"，再由 `NotificationPushService.pushDue`
    走早晨同一条 `notification_states.pushed_at` 闩锁只响一次（浏览器拒绝不记
    闩，下一拍重试；offer/rejected 行不算到期）。首拍只回看一分钟：部署不补响
    旧提醒，停机期间到期的提醒也不补响（看板仍红、次晨 sweep 仍送达）。失败
    的一拍不推进窗口、只记 warn，成功才写 `careeros.reminders.last.tick.timestamp`
    心跳；RUNBOOK 新增"分钟时钟"排障段，DEPLOYMENT 记下开关与心跳。日历侧每个
    `VEVENT` 带 `VALARM`/`ACTION:DISPLAY`/`TRIGGER:PT0M`，未注册推送的手机也能
    在提醒时刻响（订阅源忽略闹钟的客户端维持自身通知设置）。5 + 13 + 3 + 10
    个后端测试；ai-service 心跳词表随第五个时钟移动。

14. ~~**Epic 36 — 登录的第二道门（TOTP 双因素 + 恢复码）**~~ 已完成：
    密码是账号唯一的一道门。36.1 加 `user_mfa` 与 `user_mfa_recovery_codes`
    两张表（V26），TOTP 种子用 `app.security.mfa-secret` 的 AES-GCM 封装后落库；
    `Totp` 实现 RFC 6238（SHA1/30 秒/六位/±一步漂移/无填充 Base32/恒定时间比较）；
    注册与激活都需登录态，激活再问一次当前密码（会话被盗也不能把一部手机挂到
    账号上、在改密后继续存活）；未证明的种子可被覆盖、已启用的不可。36.2 已落地：
    `AuthService.login` 在密码之后核对六位码或一次性恢复码（用后即焚），无码回
    `MFA_REQUIRED`、错码/重放/已用码回 `MFA_INVALID`，而密码错仍是
    `INVALID_CREDENTIALS`（不泄露账号是否开了第二因子）；登录变成写事务，让步数
    与焚码随会话一起提交；限流器新增 MFA 桶（每分钟五次、按登录账号计），只覆盖
    判码的 `/me/mfa/activate`，状态读与发种子留在桶外；SECURITY 记作
    `per signed-in user`，限流 census 因此读到第四个身份。6 + 6 + 4 + 12 + 4 个
    单元用例、`AuthFlowIT` 9 与 `RateLimitIT` 5（第六条读 429）通过，浏览器错误表
    双语同步。36.3 已落地：`POST /me/mfa/recovery-codes` 换发（旧码整批作废、
    新十枚只答一次；密码 + 六位码或一枚打印码），`POST /me/mfa/disable` 关门
    （同样两证，种子与恢复码全删），两条新路与激活共享按账号的 MFA 桶，状态读
    仍在桶外；`GET /me/mfa` 增 `recoveryCodesRemaining`（`me` 负载不背 MFA 字段：
    设置卡本来就要读这个路由，而每次资料读都多查一次 MFA 不值得）；删号时两表
    随 CASCADE 删除并由 `AccountErasureIT` 断言；留存清扫不加第四张表——每账号
    至多十行，换发/关闭/删号都会整批删除。36.4 已落地：设置页新增安全卡——
    状态读 `["mfa"]`（一分钟陈旧，四个写全数失效它，恢复码应答只让状态重读、
    不在本地猜新状态），未开启显示“开始”，待证明可“重新开始”，已开启显示“换发/
    关闭”与剩余恢复码；种子按组分隔、与 `otpauth://` 并列且各带复制；恢复码只在
    应答里出现一次，整页复制后可用“完成”丢弃。登录第二步由 `MFA_REQUIRED` 本身
    驱动：码字段只在密码通过后长出，改邮箱即清空挑战（不让换号的人卡在无关
    的一步），不向陌生人预读状态；`MFA_REQUIRED` 在 auth-recovery 里排到 401
    通用规则之前，免得“请输入验证码”被改写成“会话过期”。新增 `lib/mfa.ts`
    （种子分组、恢复码文本、三个字段校验，8 例）与 `lib/hooks/mfa.ts`（一个
    状态读 + 四个写，全走 `fail`，已知错误码仍说自己的句子）；双语安全卡与
    登录码字段文案、四条失败句；API.md 记下两个入口，SECURITY 写种子静态密封、
    丢手机的代价（一枚打印码登录、再一枚换发或关闭）与轮换 `APP_MFA_SECRET`
    会让所有种子不可读的后果，RUNBOOK 新增“账号被第二因子锁在门外”一节
    （时钟、码的种类、限流桶、种子不可读，以及删两行恢复密码登录的处置）。
    浏览器套件 79 文件 / 842 例、`tsc` 干净；census 随人口移动：失败变异
    86 处 / 12 文件（80 在 hook 处播报、仍是那六个静默、77 次 `fail`），缓存
    写多出第 8 个文件，失效承诺 50 条全部命中已声明且被屏幕挂载的键，登录
    载荷 `[email, password, code]` 由 auth 契约门读可选的 `?` 记下。

15. **Epic 37 — 回信回到应用（入站邮件）**（进行中）
    产品发出的每封信都离开大楼，却从没有一条回来的路：退订与日历链接只读，
    通知中心只合成应用自己算出的信号，招聘方的回复躺在应用看不见的邮箱里。
    本 Epic 给每个账号一个自己的地址，由邮件服务把回复转进来，读信、对上申请、
    落到看板本来就在讲的故事里；不静默改状态——意图只是建议，一键才采纳；
    读不懂的信也仍然是到达的信。
    - 37.1 自己的邮箱：`GET /api/v1/inbound/link` 交地址，
      `POST /api/v1/inbound/mail/{token}` 是匿名 webhook；令牌即凭证
      （`SignedLink` 自有用途前缀 + 账号 id，与日历同构，MAC 截断为 16
      字节、local-part 共 45 字符，守住 RFC 5321 的上限；轮换
      `app.mail.link-secret` 一次作废全部地址）；载荷以 Postmark 入站 JSON
      为准，缺 MessageID 时按四字段 SHA-256 去重，`(user_id, message_key)`
      唯一，重投同答 200 不落第二行；只收纯文本、逐字段限量，限流桶按令牌计；
      伪造/轮换/缺失/已删号统一 404 `INBOUND_LINK_INVALID`，未配
      `app.inbound.domain` 时地址路由回 `INBOUND_NOT_CONFIGURED`；`V27`
      存信，删号 CASCADE。
    - 37.2 引擎读信：ai-service 内部 `POST /internal/features/classify-reply`
      答 `{intent, company, role}`（rejection/interview/offer/info/other），
      先走双语关键词规则、模型只补规则弃权处，offline mock 保持确定；路由进
      `test_forward_features_contract.py`；桥接失败留空意图而不丢信。
    - 37.3 信对上申请：公司名不区分大小写匹配、重名时用职位包含收窄；对上一封
      写 `application_events` 的 `reply` 行（信 id、发件人、主题、意图），通知
      中心多出 `reply:<id>` episode，铃铛会数、晨间推送可响；未对上的信停在
      回复页等“归档到这封申请”；意图映射建议阶段（rejected/interviewing/
      offer），一键才落、只落在信真正归档的申请上；`GET /api/v1/inbound/mails`
      分页读、`POST /api/v1/inbound/mails/{id}/file` 归档。
    - 37.4 回复页：`/replies` 按时间列信——发件人、主题、时间、意图徽章、归档
      到的申请或归档选择器、确认框后的建议阶段按钮；设置页新增地址卡（复制、
      轮换警告、未配置句）。双语、copy census、endpoint 台账与三个 hook 门随
      人口移动；API.md 记四条路由与两个新错误码，SECURITY 记地址是凭证、信是
      随账号删除的用户数据，RUNBOOK 记转发域配置与地址沉默的含义。
    37.1 已落地：`InboundLinks` 由 `SignedLink.token` 的 HMAC 截出 16 字节 MAC，
    45 字符 local-part；`V27__inbound_mails.sql` 唯一键 `(user_id, message_key)` 且
    `ON DELETE CASCADE`；`InboundMailService` 逐字段限长（320/500/20000，代理对安全）、
    缺 MessageID 时按四字段 SHA-256 去重、超前一日的信按到达时间落；`InboundController`
    两扇门，未配置域时地址路由 503 `INBOUND_NOT_CONFIGURED`、webhook 404；限流新增
    `inbound` 桶按令牌计（`RATELIMIT_INBOUND_PER_MINUTE`，默认 10），`RateLimitIT` 第十
    一封得到 429；双语错误句、API.md、SECURITY、DEPLOYMENT 与 `AccountErasureIT` 的入站
    行随人口移动；响应形状 census 182→186、限流 census 四桶→五桶。
    37.2 已落地：`reply_classify.py` 的线索表先读双语（拒信/录用/面试/问询，按表序破并列，
    明确拒信优先，避免“cannot offer you”被读成录用）；规则已定的意图，模型无权改写；公司
    与职位没有线索可循，始终由模型抄录，模型还补线索弃权的意图；offline mock 答中性
    `other` 与两个名字。`POST /internal/features/classify-reply` 进转发契约（请求体只有
    `text`，回答恰为 `{intent, company, role}`）。后端 `AiServiceClient.classifyReply` 由
    `InboundMailService` 在落库后调用——两次独立事务，分类器卡住不占库连接；失败只记警告、
    三列留空（NULL 是“还没读”，不是“没得读”）；重投不再分类。`V28__inbound_mail_reading.sql`
    加 intent/company/role 与五值 CHECK；响应形状 census 的消费者与持有者名单各加
    `InboundMailService`。
    下一步：37.3。
    37.3 已落地：`InboundReplyService` 独占匹配、归档与列表。匹配只认公司名（仓储层
    ignore case），同公司多条投递时用信里职位的包含关系收窄；收窄到零条或两条以上都不归档
    ——错卡上的回复比等待的回复更糟。归档是一次事务里的两行：信记住 `application_id` 与
    `filed_at`，卡的时间线添一条 `reply` 事件（邮件 id、发件人、主题、意图）。`V29` 的
    `application_id` 用 `ON DELETE SET NULL`，删卡让信回到未归档而不是随卡消失。收到即归档
    由 `InboundMailService` 在读数之后调用，独立事务、独立失败——匹配器抛错只损失归档，
    不损失信。同一张卡重复归档是幂等空操作；换一张卡返回 409
    `INBOUND_MAIL_ALREADY_FILED`（第一张卡的时间线已经写明这封信回应它）；别人的信与
    不存在的信同为 404 `INBOUND_MAIL_NOT_FOUND`。建议阶段只在线上作答（rejected /
    interview / offer），任何路由都不替读者移动投递。通知中心新增合成剧集 `reply:<mailId>`
    （已归档、七天内、按收信时间排序，标题取公司、无公司取发件人，链到
    `/replies?mail=<id>`），晨信两种语言都有一句，并在行下印出信自己的主题；`Words`
    末尾加两个字段。前端通知页加 `reply` 分支与两语言键；错误码 census 与
    `ApiErrorCode` 同增两码（37.1 的两个 INBOUND 码此前漏进 census 的钉表，这次一并补上）；
    API.md 记两条路由；endpoint 账本把四个 inbound 路由列进未引用表，读者面两条待 37.4
    落地时移出。
    37.4 已落地：`/replies` 页（`app/(app)/replies/page.tsx`）按时间列信——意图徽章、
    相对时间、公司·职位、主题、发件人，正文收在 `<details>` 里；已归档的信写明落在哪张卡，
    并给出去看板的深链；建议阶段只出现在已归档的信上，走既有的确认框，再由普通的
    `useUpdateApplication` 改状态——没有新路由，也不会自动移动；未归档的信（含服务端收窄
    失败的那封）在这一行里挑卡再归档，看板为空时说明先建投递。`?mail=` 高亮铃铛链来的
    那封，翻页越界由 `lastPageOf` 在布局效应里纠正；picker 的清理用删除键复制而不是解构，
    `applications.isPending` 期间不出“尚未归档”的假话。设置页新增 `InboundCard`：地址
    只读可复制，轮换警告紧贴地址；`INBOUND_NOT_CONFIGURED` 说“这个部署没有收信箱”，
    其他错误才说“再试一次”。`lib/hooks/replies.ts` 是三条路由的唯一读端
    （`mapInboundMail` 把“还没读”留成 null，不借别的意图）。双语加 `nav.replies`、
    `navDescriptions.replies` 与 inbound/replies 两块；copy census 138→140（页面与卡片
    两个 .tsx），endpoint 台账移出三条读者路由（webhook 留在未引用表：只有服务商调它），
    参数钉 46 不变（后端未动）。新增 `replies.test.ts`（3 条）与
    `replies/page.test.tsx`（5 条：英/中、已归档、待归档、空看板、空收件箱）。SECURITY
    记地址是能力、信是随账号删除的用户数据；RUNBOOK 新增“回信一直不到”一节（域转发、
    local-part 不能改写，503 / 404 / 未读数 / 未归档 / 429 五层含义与 `inbound_mails` 查询）。
    下一步：38.1（见下）。

16. **Epic 38 — 账号能伸手够到自己的按钮**（进行中）
    38.0 盘点：Epics 24–26 给账号装了四个动词（改密码、销号、按 family 列/关会话、
    改登录地址），每个都在收口时写着“路由先活着，等前端来”。endpoint 账本里仍躺着
    十条 “the client has not wired”；更糟的是 26.1 的信链到
    `{app.web.base-url}/confirm-email`，而 Next 里从来没有这个页面——要求改地址的
    读者收到一封指向 404 的信。`/mail/preferences/*` 不是缺口（后端渲染的公开页，
    浏览器只导航、不 fetch），其余未引用路由是别名、健康探针与只给服务商调的 webhook。
    据此立 Epic 38：先补已经在信里的那个链接，再补四张设置卡，最后让账本改口。
    - 38.1 确认信的链接落到一个能作答的页面（已完成）：`/confirm-email` 在 `(app)`
      组外、是 `PUBLIC_PAGE_TITLES` 的一条；effect 里读 `?token=`（服务端渲染读不到
      URL），POST 公开的 `/auth/email-change/confirm`。四种诚实状态：作答中、已搬走
      （全端 refresh 已被吊销，所以引导用新地址重新登录而不是假装这个标签页还活着）、
      链接无效（EMAIL_CHANGE_INVALID：未知/已用/过期同答，建议回设置重发）、地址已被
      注册（EMAIL_ALREADY_REGISTERED，token 已被花掉，同一链接不能再试）。没有 token
      先说清楚，也允许粘贴 token。endpoint 账本移出这条路由。
      落地：`app/(auth)/confirm-email/page.tsx` 取 `PUBLIC_PAGE_TITLES` 的标题，
      `components/auth/confirm-email-form.tsx` 是唯一客户端件；两个不是标记的决定——token
      从哪里来、哪种拒绝配哪句话——放在 `lib/email-change.ts`，7 条单测钉住，和
      `auth-recovery.ts` 管重置页算术一样。`useConfirmEmailChange` 走
      `authApi.confirmEmailChange`（`auth: false`），成功后丢掉本地 token 对（搬家会吊销
      所有 refresh token）。账本移出“auth 流程还没有页面”那一行，`nav.test.ts` 与
      `metadata.test.ts` 记下新的公开路由，copy census 140→142。前端 857 个测试 / 82 个。
      tsc 与 eslint 干净；页面在浏览器里走过四种状态（粘贴表单、作答中、已搬走、链接无效），
      API 用桩顶替。
    - 38.2 设置页的改地址卡（已完成）：当前地址、新地址、密码，POST
      `/users/me/email-change`。三个拒绝各有自己的句子而不是服务器英文——
      CURRENT_PASSWORD_INCORRECT / EMAIL_UNCHANGED（trim 且不分大小写）/
      EMAIL_ALREADY_REGISTERED；RATE_LIMITED 是 27.1 的信件计量（一分钟五封）。
      成功态不说“已发送”，而说：两封信都走了，新邮箱拿到会搬家的链接、旧邮箱拿到
      警告，链接作答之前什么都不会变。与落地页共用一组 hook，搬家两侧不会漂移。
      落地：`components/settings/email-change-card.tsx` 放在账户卡旁边；`lib/hooks/account.ts`
      的 `useRequestEmailChange` 是这条路由唯一的引用，账本移出 `/users/me/email-change`。
      新地址用登录表单自己的 `emailIssue` 校验、密码只查有没有；拒绝归到造成它的字段
      （`lib/email-change.ts:addressMoveRefusal`，4 条单测）：密码错归密码框、地址没变或
      已被注册归地址框、计量器的 429 归表单（没有字段造成它）。句子走 `describe` 的
      码表，于是暴出一个真问题：`currentLocale()` 只读 `localStorage`，只采纳过账号语言
      （21.4）的浏览器上，这类句子会在中文页面里说英文——现在回退到 provider 写的 cookie，
      补 2 条单测。成功态把表单换成两封信与两小时窗口。前端 863 个测试 / 82 个文件，
      tsc 与 eslint 干净；卡片在浏览器里走过表单、成功、密码错、限流、地址被占五种状态，
      API 用桩顶替。
    - 38.3 会话卡（已完成）：`GET /users/me/sessions` 按 family 列一台设备——名字、来源地址、
      开始、最后活动、最远到期；正在提问的这台被标出，并写明关掉它就等于登出。
      单关走 `DELETE /users/me/sessions/{familyId}` 与既有确认框；全关是同一动词
      无 id，说明所有设备都会登出、当前标签页只活到 access token 到期。别人的或已关
      的 family 只有一个 404 `LOGIN_SESSION_NOT_FOUND`，页面把它读成“这扇门已经关了”
      并刷新；空列表是诚实状态。
      落地：列表缺的那一个事实——哪一行是正在提问的标签页——由 access token 的
      `fid` claim 补上（`AuthUser.familyId` 可空，旧 token 与旧测试照常解析）；
      `TokenService.listSessions(userId, currentFamilyId)` 标出匹配行，
      `SessionResponse` 多一个 `current`，页面不再拿 user-agent 猜。两种拼写的列表
      路由都把 family 传进去。`JwtServiceTest` 往返 claim 与缺席，
      `TokenServiceSessionsTest` 钉住“标出这一行”和“没有 family 就一行都不标”，
      `SessionsIT` 读笔记本为 current、手机为否。
      前端 `components/settings/sessions-card.tsx` 一行一家：`lib/sessions.ts:deviceLabel`
      把七种浏览器记号与六种系统折成 "Chrome · Windows"，不认识的照原样写（部署自己的
      客户端、未命名设备都有行）。当前行带徽章并写明关掉它是登出；单关与全关共用既有
      `ConfirmDialog`，各自说真实后果；已关的 family 答 `LOGIN_SESSION_NOT_FOUND`，
      `sessionCloseRefusal` 读成“这扇门已经关了”并触发刷新；空列表说明这个标签页只活到
      access token 到期。`lib/hooks/account.ts` 的三个 hook 是路由唯一引用，账本移出
      `/users/me/sessions` 两行，`/me` 别名仍留在表里。copy census 143→144；
      `lib/sessions.test.ts` 6 条。前端 869 个测试 / 83 个文件，tsc 与 eslint 干净；
      卡片在浏览器里走过三行与当前徽章、两种确认框句子、404 提示与刷新、全关之后的
      空状态（API 用桩顶替）。
      这次全量套件还抓出两个 Epic 37 的潜伏问题，一并修好：`AccountErasureIT` 的
      `inbound_mails` 裸插入漏了 Hibernate 在 Java 侧生成的 id；自调用 census 指控
      `InboundMailService.receive`，而它的两次写入必须被分类器调用隔开——现在把这个
      站点连同理由记进清单，而不是硬塞进一个事务。后端 1116 个测试（单元 + IT）全绿。
    - 38.4 改密码卡（已完成）：当前密码 + 两遍新密码，先按记录的（8, 72）校验，PATCH
      `/users/me/password`。CURRENT_PASSWORD_INCORRECT 是再认证失败（与改地址、销号
      同码），PASSWORD_UNCHANGED 按名字拒绝；成功态说真话：所有 refresh token 被
      吊销、别的设备下次刷新下线、本标签页活到 access token 到期——表单换成那句话，
      而不是清空后 toast。
      落地：`components/settings/password-card.tsx` 放在会话卡与两步验证之间，三格
      （当前、新、再输一遍）；`lib/password-change.ts:currentPasswordIssue` 照
      `PasswordChangeRequest.currentPassword` 的 `@NotBlank @Size(max = 72)`（当前值没有
      下限），新值走既有 `passwordIssue` 的 (8, 72)，两遍一致性走 `confirmationIssue`——
      三条都在请求离开发送之前判。`passwordChangeRefusal` 把 `CURRENT_PASSWORD_INCORRECT`
      归当前密码框、`PASSWORD_UNCHANGED` 归新密码框，其余（含 429）归表单。客户端只有
      `PATCH /users/me/password` 一种拼写，body 两个字段各只写一次；`useChangePassword`
      成功后让会话列表失效，于是那堆门如实变成空列表。账本移出 `/users/me/password`
      一行，`/me/password` 别名仍留在表里。copy census 144→145；
      `lib/password-change.test.ts` 5 条。前端 874 个测试 / 84 个文件，tsc 与 eslint 干净；
      卡片在浏览器里走过空表单的三条提示、密码错的框内句子（401 先触发一次刷新、重试后
      才拿到码）、PASSWORD_UNCHANGED 归新密码框、8 字符下限在本地拒发、成功面板换成完整
      后果且会话列表清空（API 用桩顶替）。
    - 38.5 销号卡（已完成）：`components/settings/erase-account-card.tsx` 放在设置页
      最底，写明什么会走（documents.file_key 背后的对象、从 users 级联的每一行）与
      什么不会（备份到保留期结束、已投递的信留在邮箱）；密码 + 回打的地址，先按
      `emailIssue` 与“密码非空”在本地判，`POST /users/me/erase` 只在重申两者的确认
      之后，body 里的地址去掉首尾空格；`lib/erase-account.ts:eraseRefusal` 把
      CURRENT_PASSWORD_INCORRECT 归密码框、CONFIRMATION_MISMATCH 归地址框，其余归
      表单，3 条单测。`useEraseAccount` 丢掉 token 对、清空缓存，然后整页导航到
      `/account-erased`（公开的服务端渲染落地页，读 locale cookie，首次响应就说
      “账号已经删除”，不调用任何 API）。四张卡接线后账本改口：`/me/*` 写成
      MeController 的别名 + 调用它的设置卡（38.2–38.5），mail preferences 写成后端
      渲染的公开页，`/users/me/erase` 一行移出。copy census 145→147；前端 877 个
      测试 / 85 个文件，tsc 与 eslint 干净；浏览器走查（桩 API）：空表单两条必填、
      密码错与地址不符各归其框且确认前不发请求、确认框重申回打地址、带空格提交被
      trim、成功后 token 对为空并落在 `/account-erased`（标题“账号已删除 · AI
      Career OS”），落地页无会话也能渲染且零请求。
    下一步：Epic 38 至此收口（38.1–38.5 全勾选）。

17. **Epic 39 — 部署能回答自己的问题**（进行中）
    盘点：账号的动词都有了屏幕，剩下的是跑这些屏幕的进程自己说不清状态。
    `/api/v1/health` 只报 db 与 Redis，对象存储或 ai-service 已经死了也照样 `ok`（而它们
    负责每个上传文件与每次分析）；compose 只给 postgres/redis/minio 配了健康探针，三个
    应用服务显示 “running” 不代表能作答；启动日志不说它选了哪个邮件传输、哪个存储端点、
    哪个 provider；Spring 默认 immediate 关停，重新部署会切断已经接下的请求。据此立
    Epic 39：
    - 39.1 健康行点名对象存储与 AI 服务（已完成）：`StorageService.available()` 由 MinIO
      适配器用 bucketExists 作答，内存存储按构造为真；`AiServiceClient.healthy()` 由
      HttpAiServiceClient 用只属于探针的 2 秒客户端请求 ai-service 自己的公开 `/health`，
      不带内部令牌——那扇门不问，探针就不递；FakeAiServiceClient 暴露 `aiHealthy`。新的
      `HealthService` 把四个探针放上各自的虚拟线程，共用一条 2 秒预算：超时取消、异常算假、
      未配置存储算假；`status` 四项全真才 `ok`，键序 status/db/redis/storage/ai，控制器
      只转发，永远 200。三处测试：`HealthServiceTest` 8 条（全真、存储假、AI 假、AI 抛错、
      存储缺席、db 假、Redis 抛错、挂住的探针在 100ms 预算内返回且 <2s），
      `HttpAiServiceClientTest` 新增 2 条走真实 socket（公开路由且不带令牌；503 不算健康），
      `HealthIT` 2 条对着真 Postgres/Redis（全真 `ok`；关掉 AI 后 `degraded` 且仍 200）。
      API.md 的健康行（纯散文，避免文档闸门把行内代码读成参数）与 DEPLOYMENT.md 的探针表
      改成四个名字。后端 1128 条全绿（164 份报告，非 IT 选集 1037）。
    - 39.2 compose 等“能作答”而不是“已启动”（已完成）：三个应用服务各配容器内探针——
      ai-service 用 `python -c` + urllib 打自己的 `/health`（镜像有 python 没有 curl/wget，
      500 即非零退出，因为这枚探针是后端启动的闸）；backend 用 busybox `wget` 打
      `/api/v1/health`，`ok` 与 `degraded` 都算 200，依赖故障只被报告、不被重启循环，Docker
      的 5 秒超时高于路由自带的 2 秒预算；frontend 用 `node -e` 的 `fetch` 打 `/`，主机写成
      `localhost` 而不是 `127.0.0.1`——外壳被承认的 origin 就是它，来源 census 读取每个随包
      文件。start_period 两个轻服务 30s、Spring 90s；两份 compose 的 depends_on 全部改成
      `condition: service_healthy`——开发栈的后端从此也等 ai-service，两个前端等后端，生产栈
      后端对 ai-service 从 `service_started` 改为 `service_healthy`。`docker compose config`
      解析开发文件与合并后的生产覆盖。新闸门
      `ai-service/tests/test_the_stack_waits_for_an_app_that_answers.py` 只读 `services:` 段
      （volume 的子项与 service 头同缩进），要求每个应用服务恰好一个 loopback HTTP 探针，
      探针端口必须是该服务发布的容器端口、路径必须是 DEPLOYMENT.md 监控表写的那条，并拒绝
      任何没有 `service_healthy` 的应用服务依赖；干净 fixture 通过，坏 fixture 按三条规则
      逐条点名，数据存储的 `pg_isready` / `mc ready local` 是它不碰的诱饵。DEPLOYMENT.md 新增
      “Startup gating” 三行表。四个部署闸门一起 21 条通过。ai-service 全套 1903 通过、
      48 失败、1 跳过——48 条在父提交的干净检出上完全同样失败，全是 37/38 人口移动留下的
      census 债，本单元一条不碰，修复列为下一单元。后端 1128、前端 877 不变；39.2b 随后把 48 条 census 债清零（五道闸门 8/8、8/8、32/32、9/9、7/7，全套 1951 通过 / 1 跳过、0 失败），未改产品代码。
    - 39.3 启动时用一行说清“我成了什么”（已完成）：`BootReport` 监听 ApplicationReadyEvent，
      打印 `boot: env=... port=... db=host/path redis=host storage=host bucket=name ai=host
      mail=console|smtp push=off|keypair schedulers=[...]`。事实全部来自进程真正绑定的对象——
      AppProperties、Boot 的 datasource 与 Redis 属性、实际选中的 mail/push bean、store bean
      是否存在、上下文里声明 `@Scheduled` 的 bean——不回读环境；URL 只取主机从不回显，读不出的
      值写 `unset`/`unparseable`，push 只报开关、不带 VAPID 密钥。Spring 6.2 的
      `Task.getRunnable()` 返回 `OutcomeTrackingRunnable`，`ScheduledTaskHolder` 报不出 bean 名，
      于是改为上下文扫描，并在真实 AnnotationConfigApplicationContext 上测。`BootReportTest`
      3 条：哨兵机密的精确整句（断言哨兵、`jdbc:`、`postgresql`、`redis://`、`@` 均不出现）、
      三处关闭的 dev 句、坏 URL 只报 unparseable 不回显。RUNBOOK 新增“A stack that looks
      healthy and is the wrong one”，architecture.md 包树加 `boot/`；knob census 把报告登记为
      storage.endpoint、storage.bucket、ai-service.base-url、deployment.env 的读者（只描述、
      不决策）。后端非 IT 1040 全绿（1037+3）；ai-service 全套 1951 通过、1 跳过、0 失败
      （212.73s），knob 闸门 7/7。
    - 39.4 关停先收尾再关门（已完成）：`application.yml` 设 `server.shutdown: graceful` 与
      `spring.lifecycle.timeout-per-shutdown-phase: 30s`——SIGTERM 后连接器停止收新连接，已在进程内
      的请求跑完，超过上界的请求被切断，卡住的请求拖不住一次重部署。两份 compose 给 backend 设
      `stop_grace_period: 40s`（Docker 默认 10s 会先 SIGKILL，抢在 JVM 的 30s 排空之前）；调度器是
      bean，随上下文一起停，不会在旧进程里继续触发。`ShutdownContractTest` 2 条直接读真实文件：
      第一条只认 `application.yml` 的 `server.shutdown`（不是别的 `shutdown:` 行）并要求阶段是有界
      时长；第二条读两份 compose 的 `backend` 块，要求 `stop_grace_period` 至少高出 YAML 阶段 5s。
      RUNBOOK 新增“A redeploy finishes what it started”（四行表：在途请求、超预算请求、跑到一半的
      sweep、排空期间的新连接各付出什么，以及 `Commencing graceful shutdown...` /
      `Graceful shutdown complete` 两行日志）；DEPLOYMENT.md 的 Rolling Updates 补一段。后端非 IT
      1042 全绿（1040+2）；ai-service 全套 1951 通过、1 跳过、0 失败。
    下一步：见下方 Epic 40。

## Epic 40 — 数据包即全部

- 盘点结论（2026-10-30）：`/data` 页承诺“Export everything”，但数据包只有十节；对照 V1–V29 的建表语句，
  五张属于读者本人内容或选择的表不在任何一节里：`conversations`/`messages`（copilot 对话：读者的问题、
  回答、用其材料生成的 artifacts 与引用）、`saved_jobs`（书签及附注）、`saved_searches`（晨间 sweep
  为其发声的常驻查询）、`ingestion_feeds`（读者配置的抓取源）、`inbound_mails`（转发到读者地址的信件、
  分类读数与归档的申请）。恢复无法带回它们，匿名导出也无法隐去它们——因为它们从未在包里。
  刻意不带的只有记账类数据：token/会话、MFA 密钥、推送订阅、通知已读状态、邮件偏好、用量与 agent runs、
  摘要与夜报——它们描述账户做过什么，而不是持有过什么。40.4 把这条分界写成 census。
  同时修正 ROADMAP 里一句过期的“open thread”：恢复的 current state 早已覆盖全部十节（Epic 13 后文），
  原句改为指向该段；EXPORT.md 记录本次测量与排除理由。
- 40.0 完成即本节；40.1 已完成（2026-10-31）对话随包走：新增 `conversations` 节（消息内嵌：role、content、artifacts、
  sources、actions、created_at），AI 半边直接读；匿名导出按字段抹掉标题与正文等；可读半边两种语言加词；
  plan 保留 id（包中省略即退休，消息级联），apply 连同消息写入；schema 升到 1.3.0，旧包仍有效。
- 40.2 常驻选择随包走：`saved_searches` + `ingestion_feeds`（后端所有）；按 id 匹配，省略即取消，
  字段级比较让未变行为 `skip`；匿名包保留 URL（配置不是秘密）。
- 40.3 书签与来信随包走：`saved_jobs`（目标没有该职位时报告而非伪造）+ `inbound_mails`
  （`message_key` 幂等，归档链接指向同一次恢复写入的 application id；匿名包抹掉发件地址、主题与正文）。
- 40.4 分界成为闸门：读 `db/migration` 中所有带 user 归属的表，要求每张要么被某节承载（含
  `messages` 之于 `conversations` 的内嵌），要么在 EXPORT.md 的排除表里写明“记账而非内容”；
  页面所载清单由 bundle 的 manifest 得出，可读半边的节序与 redact 列表共用同一个 section 元组。
  新表出现即按名失败。

下一步：40.2（常驻选择）与本会话 Epic 41 的下一段。

## Epic 41 — 提醒到点时的信

- 盘点结论（2026-10-30）：Epic 35 让分钟时钟（`ReminderScheduler`，默认 60s 一跳）在提醒到期那一刻把
  ring 送给浏览器；Epic 19.4 的信是**晨信**，每天 07:30 一封信把所有到期的提醒合成一句。于是
  没有浏览器的账号在提醒的那一刻什么也收不到，要等到第二天早上。设置页的邮件偏好只有两个 dial
  （weekly / signals），"提醒的即时信"没有位置。
- **41.1** 提醒自己的信（已完成）：`V30__reminder_mail.sql` 给 `mail_preferences` 加
  `reminder_mail`（无行仍=全开）；`MailList.REMINDERS` 成为第三个 slug = URL 段 = 数据库列，
  页面第三段文案明说"关掉不等于消除，晨信仍会带"（时刻而非静音）。`ReminderMailer` 写双语
  （主题带条数、最多列 5 条、超出 `... and N more`、无 title/company 有回退、无 link 回落
  `/applications`、RFC 8058 一键退订指向 `/stop/reminders`）；`ReminderMailService.mailDue(since, until)`
  读一次偏好、遍历 `findUserIdsWithReminderBetween`（已排除 offer/rejected）、从
  `awaitingDelivery` 里只取窗口内 `KIND_REMINDER` 且读者未读未忽略的条目。**不新增 latch**：
  与晨信共用同一条 episode 的 `notified_at`，"一条 episode 只有一封信"，晨信不会重发；
  发送被拒/无地址/无账号都不写 latch，晨信成为后备。`ReminderScheduler` 的 tick 变成两半
  （ring + letter），每半各自捕获异常；只有两半都完成才推进窗口与心跳，任一半失败窗口重试，
  两把 latch 保证重试不重复送。指标复用 `NotificationDeliveryMetrics`
  （`careeros.signals.delivery{outcome=sent|refused}`）。19 条新测试（Mailer 6 / Service 7 /
  Scheduler +4 / 偏好 +2），API.md、architecture.md、DEPLOYMENT.md、RUNBOOK.md、ROADMAP 同步。
- **41.2** 能停的钟成为警报，拒绝计数说出两种信（已完成）：RUNBOOK 自 35.1 起写着"这口钟还没有
  Prometheus 规则"；心跳 `careeros.reminders.last.tick.timestamp` 在，却没有人看。`alerts.yml`
  现在十一条：`CareerOSReminderClockStale` 在 gauge 300 秒（默认 tick 的五个）未动、持续五分钟时
  报警，说明写清"落后的是那一刻，不是提醒本身"（收件箱、晨信、日历仍在）。`CareerOSSignalMailFailing`
  改成数"信"而不是一种信：41.1 的提醒信写同一条 `careeros.signals.delivery{outcome="refused"}`，
  摘要/描述/RUNBOOK 段同时点名两行日志，并说明被拒的提醒由次日晨信兜底、分钟钟不重试。闸门测试读
  调度器默认 tick 推出 300、钉住指标来源与 RUNBOOK 的同一表达式，9 条绿；DEPLOYMENT 的
  规则数（十→十一）与两段邮件文字同步。
  下一步候选（避开并发会话在制的 export/import）：仪表盘 attention 的提醒过期语义、或 Epic 40 提交后接手。

- **Epic 42 — 设置不必靠一封信回来**（本轮起）
  - 盘点结论（2026-10-30）：三个 dial 的唯一入口是信里的签名页（23.1/41.1）。读者把信删了、
    或从没等到周一信，就再也够不到自己的邮件设置——而答案一直在他自己的账号里。`/api/v1/mail/**`
    在 `SecurityConfig` 里整体 `permitAll`（注释明写"加到这个前缀下的路由在被搬走前就是公开的"），
    所以登录态的新路由不能放进去，参照 `/inbound`（匿名 webhook 与登录态列表同 controller 不同路径）
    的做法，放到 `/me` 下面。
  - **42.1** 邮件设置由登录的读者回答（已完成）：新增 `MailSettingsController`
    （`@RequestMapping("/api/v1/me/mail")` + `GET /settings`）→ `record MailSettings(url, weekly,
    signals, reminders)`；三个布尔来自 `MailPreferenceService.receives`（与 sweep 同一列），`url`
    是 `MailLinks.page` 签出的同一张页；响应 `no-store` + `noindex`（地址是凭证）；无会话走
    `CurrentUserArgumentResolver` 的 401。前端 `endpoints.mailSettings`、`MailSettingsRow`、
    `hooks/mail-settings.ts`、`components/settings/mail-card.tsx`（三个 dial 的开/关徽章 + 地址 +
    CopyButton + "打开设置页"，失败是一句话而不是空白开关）、设置页放在日历卡之后；EN/ZH
    `mailLetters` 两块。4 条后端测试（页面地址、三列、no-store、401）+ 2 条前端 hook 测试；
    API.md、DEPLOYMENT.md 同步。
  - 下一步（避开并发会话在制的 export/import）：仪表盘 attention 的提醒过期语义；或 Epic 40
    提交后接手对话随包走。


## 开发协议
（每个任务）

- 先跑相关测试，再改；改完跑三套件相关子集；提交前 `tsc` + lint。
- 实现 + 测试 + 真实 API/UI 接线（无 placeholder 端点）+ 文档/census 同步。
- 每个可交付单元立即 commit + push（遵循仓库现有提交风格）。
- Docker 依赖的 `*IT`、RAG eval、E2E 不在本机假装通过；记录为"需真实栈"。
- 新 AI 结论必须可追溯到证据；offline provider 在 `APP_ENV=prod` 一律拒绝。

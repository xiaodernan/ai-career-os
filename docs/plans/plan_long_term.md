# 长期开发计划 (Long-Term Development Plan)

## 终极目标

一个真正可运行、可交付的个人求职操作系统 (AI Career OS)：简历 → 知识库 →
岗位发现 → JD 情报 → 证据约束匹配 → 定制材料 → 模拟面试 → 申请管理 → 成长与
薪酬 → 数据可携带，全部闭环；并且从"问了才答"进化为"替你先做"——定时摄取、
主动提醒、通知中心、每周摘要、语音面试、移动端与生产级交付。

## 当前状态 (2026-10-30)

- **前端**: 842 个 vitest 通过（79 个文件）；`tsc --noEmit` 干净。
- **后端**: 1062 个测试通过、158 份报告，含真实栈 IT（0 失败 / 0 错误 /
  0 跳过；`mvn -o -q test`；不含 IT 的选集为 974 个）。
- **ai-service**: 1929 passed, 1 skipped (offline: mock/hash)。
- **E2E**: 24/24 golden journey（最近一次真实栈验证）。
- **分支**: main 与 origin 同步（本次推送后）。
- **已完成**: Epic 0–36 全部勾选。36（登录的第二道门）在 36.4 收口：设置页
  安全卡、登录第二步、种子与丢手机的 SECURITY 说明、runbook 的锁门处置。
  最近一段是 19.1–19.9（保存的搜索、定时摄取、通知中心、语音面试、离线壳、
  夜间报告落板）、20–33（部署自检、来信离楼、
  收件箱离应用、退订、导出、开放入口、改地址、邮件计量、遗忘、搜索、后端
  census 补齐、壳层加固、答案留痕、浏览器唤醒）、34（提醒以 RFC 5545 日历
  订阅离开应用，设置页交出签名地址）、35（分钟时钟按提醒自己的时刻响，
  日历事件自带 VALARM）与 36（第二道门的四段：注册/激活、登录第二步、
  换发/关闭、设置页安全卡与登录码字段）。

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
      （`SignedLink` 自有用途前缀 + 账号 id，与日历同构，轮换
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
    下一步：37.1。

## 开发协议（每个任务）

- 先跑相关测试，再改；改完跑三套件相关子集；提交前 `tsc` + lint。
- 实现 + 测试 + 真实 API/UI 接线（无 placeholder 端点）+ 文档/census 同步。
- 每个可交付单元立即 commit + push（遵循仓库现有提交风格）。
- Docker 依赖的 `*IT`、RAG eval、E2E 不在本机假装通过；记录为"需真实栈"。
- 新 AI 结论必须可追溯到证据；offline provider 在 `APP_ENV=prod` 一律拒绝。

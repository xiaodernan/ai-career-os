# 长期开发计划 (Long-Term Development Plan)

## 终极目标

一个真正可运行、可交付的个人求职操作系统 (AI Career OS)：简历 → 知识库 →
岗位发现 → JD 情报 → 证据约束匹配 → 定制材料 → 模拟面试 → 申请管理 → 成长与
薪酬 → 数据可携带，全部闭环；并且从"问了才答"进化为"替你先做"——定时摄取、
主动提醒、通知中心、每周摘要、语音面试、移动端与生产级交付。

## 当前状态 (2026-11-08)

- **前端**: **1158 个 vitest 通过（116 个文件，70.4 落地后 2026-11-08 复测全绿）**；`tsc --noEmit` 干净（2026-11-08 实测）。2026-11-08 中转态曾有一个红——`endpoints.test.ts` 的绑定参数普查随 70.4 的 `q` 过滤参数落地重钉到 59（c220af0），红已结清。
- **后端**: 非 IT 选集 **1205 条全绿，Failures/Errors/Skipped 均为 0，BUILD SUCCESS（2026-11-08 实测，`mvn -B "-Dtest=!*IT" test`）**；*IT 需真实栈，未假装通过。2026-11-08 01:03 的一次同命令运行退出码 1，但事后逐份核对 159 份 surefire 报告：全部 `Failures: 0`，dumpstream 为仓库既有的良性 Windows Manifest 警告；同机并行两套他项目完整 pytest 后重跑，干净 BUILD SUCCESS。异常未复现，原因不写成定论。
- **ai-service**: **2032 passed, 2 skipped**（2026-11-07 实测）。**2026-11-08 全量（c220af0 落地后复测）：2051 passed、2 skipped、0 failed（381s，`pytest ai-service/tests -q`）**——70.4 的红已结清；本轮提交的 roadmap 台账闸门（3）与旅程闸门（2）包含在内。
- **E2E**: 24/24 golden journey（最近一次真实栈验证）。
- **分支**: main 与 origin 同步（本次推送后）。
- **已完成**: Epics 69–73 收口（2026-11-06 → 11-08）：tag 计数、看板答词（70.4：重演列表以 `q` 按公司/职位/模式回答一个词，随 c220af0 收口）、无界面路由审计、联系人窗口翻页、跨栈契约再测量、roadmap 台账闸门、e2e 体检闸门（`tests/test_the_e2e_readme_keeps_its_own_arithmetic.py`，分项计数与标粗总数都对真实 spec 文件对账，三条变异探针实测变红）。
- **已完成（历史）**: Epic 0–38 全部勾选，Epic 39 进行中（39.1–39.2 已勾选）；38（账号够到自己的动词）在 38.5 收口。36（登录的第二道门）在 36.4 收口：设置页
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
**42.1** 让邮件设置不再只住在旧信里（`GET /me/mail/settings` + 设置页邮件卡，4 条后端测试绿）；
**42.2** 让这张卡自己扳动三个开关（`PUT /me/mail/settings/{list}` + Switch 的乐观更新，
3 条后端测试 + 2 条 hook 写面测试绿）；**43.1** 让 attention 卡上的到期提醒就地可答
（`Snooze to tomorrow` / `Clear` 走同一个 PATCH，新行组件 + 5 条 SSR 测试，前端 941 条 / 91 文件）；**43.2** 让收件箱里的提醒也能就地回答（同一对手势落在通知行，新解析函数 + 6 条纯函数测试 + 5 条页面测试）；**45.1** 让已保存搜索的提醒说出自己的名字与条数（回信的句子补上中英测试，前端 941 条 / 91 文件仍全绿）；**45.2** 让收件箱一次读一种 kind，并让空态说清六种来源（新纯函数模块 + 5 条单测 + 6 条页面测试，前端 947 条 / 92 文件）；**45.3** 让未读成为同一行筛选面的第二维（与 kind 叠加、禁用态诚实，948 条 / 92 文件）；**45.4** 让已读的行一次清掉（新后端路由 + 3 条服务测试 + 1 条路由测试，非 IT 选集 1110 条全绿，前端 948 条不变）；**46.1** 让 attention 行说出招聘方的回信（服务端 LATERAL 取最新一封，前端 950 条 / 92 文件）；**46.2** 让那句「谁在等你」可点（负载带上信自己的 id，前端 951 条 / 92 文件）。**47.1** 让申请详情读懂自己带的材料包（新 `/applications/{id}/packet`，按用户解析简历版本、JD 分析与匹配；`*Linked` 区分「未关联」与「已关联但不可读取」，三行各自可点回原页面；3 条服务测试 + 1 条路由测试 + 5 条 SSR 测试 + 2 条归一化测试）。**47.2** 让看板卡片报出材料完整度（复用同一组三个链接，`Packet 2/3` 徽章与缺失项提示；3 条纯函数测试）。**47.3** 让职位详情页知道自己已在流水线（`GET /applications` 新增 `jobId` 收窄，已有申请时「加入流水线」变成指向那张卡的 `已在流水线 · 阶段`；2 条服务测试）。**47.4** 让求职信有归处（新 `application_letters` 表与申请下的存取路由；职位页保存草稿，抽屉读回正文；导出 schema 1.6.0 带上 `cover_letters`，恢复跟随落地的申请；4 条服务测试 + 路由测试 + 4 条 SSR + 2 条归一化测试）。**50.1** 让保存下来的信可以删掉（申请下的删除路由与抽屉确认框；三者同时命中才删，重复删除仍 204；2 条服务测试 + 1 条路由测试，并修正 `/applications` 查询参数普查）。**50.2** 让保存下来的信可以改（原行 PATCH + `updated_at` + 抽屉原地编辑；3 条服务测试 + 1 条路由测试 + 错误码普查 + 1 条 SSR）。**50.3** 让保存下来的信可以带走（复制全文 + 下载 Markdown，文件名按职位 slug、否则退回信的 id；4 条纯函数测试 + 2 条 SSR 测试）。**50.4** 让修改也能拨动语气与长度（与生成器同一份目录 + 真正的「未设置」，`dial()` 保住空串；8 + 3 + 2 条测试；端点普查的请求体读取器也学会 `dial()`）。**51.1** 让职位页的求职信卡片读回这个职位已经存下的信（「已保存 N 封」+ 通往流水线；2 条 SSR 测试）。**51.2** 让那行计数带上 `?application=<id>`，直接打开那张申请的抽屉（1 条 SSR 测试断言）。**51.3** 让空柜子链回职位页的起草卡片（`#cover-letter` 锚点；1 条 SSR 测试）。**52.1** 让 `/search` 的第七组是保存下来的求职信（按正文或职位标题命中，`applicationId` 让命中可打开；2 条仓储测试）。**52.2** 让 ⌘K 面板列出第七组求职信（职位标题做主行、`?application=` 作去处；3 条归一化测试）。**52.3** 让 ⌘K 面板记住最近五条查询（`localStorage`，坏数据与隐私模式都退让；6 + 1 条测试）。**52.4** 让最近搜索可以清空（删键并回答空列表；1 + 1 条测试）。**53.1** 让材料包把求职信也计进去（`packet` 多出 `letters` 计数，按用户收窄；抽屉第四行说「已保存 N 封」/「还没有保存」，全空句子也要求信为 0；2 条服务测试 + 1 条路由断言 + 4 条 SSR 断言 + 2 条归一化测试）。**53.2** 让看板卡片报出自己存了几封信（`GET /applications` 每行带 `letters`，整页一次分组查询；卡片在非零时挂信封徽章「N 封信」；2 条服务测试 + 1 条映射测试 + 2 条 SSR 测试 + 1 条归一化测试）。**53.3** 让搜索到的信直接落在抽屉的求职信那一节（信面板挂 `id="letters"`，命中带 `#letters`，打开后滚过去并抹掉 hash；1 条归一化断言 + 1 条 SSR 断言）。**54.1** 让留下的信把自己的旋钮交给下一封（「照这个样子再写一封」指向 `/jobs/{id}?tone=&length=#cover-letter`，面板从地址采纳目录内的值；5 条纯函数测试 + 2 条 SSR 断言）。**54.2** 让留下的信说得出自己写自哪个简历版本（抽屉按 id 读 `/resume-versions/{id}`，印出「写自 ‹版本名›」并链回 `/resumes/{resumeId}`；2 条 SSR 测试 + 1 条映射测试，端点普查移除一行）。**55.1** 让申请的搜索命中直接打开它的抽屉（href 带上 `?application=<id>`，与 attention 行同一条深链；1 条归一化断言）。**56.1** 让演练写下自己的申请（`interview_sessions.application_id` + POST 接受 `applicationId`，服务按调用者校验并从卡片补齐留空的目标字段；3 条服务测试 + 两条 IT 构造参数）。**56.2 / 56.3** 让抽屉为这张卡开一场演练、让面试列表指回那张卡（「为这个职位演练」直通 `/interviews/{id}`；行上的「打开申请」回到 `?application=` 抽屉；1 条页面测试）。**56.4** 让会话页与报告也指回那张卡（同一个 `interviewApplicationHref` helper；2 条纯函数测试）。
**56.5** 让这条链接跟着备份走（恢复写回 `application_id`，只在目标拥有卡片时保留；计划器按 section 剥掉它，免得每次恢复都重写整份对话；3 条后端单测 + 1 条导出断言 + 1 条计划器测试）。**57.1** 让一张卡的演练成为一份可分享的列表（GET /interview/sessions?applicationId=，按调用者+卡片收窄；页面从 URL 采纳筛选、说清在看哪张卡、两处给出口；2 条后端测试 + 1 条契约用例）。**57.4** 让演练行说出卡片所处阶段（`applicationStatus` 整页一次分组读回，列表画成徽章；1 条服务测试 + 1 条映射测试 + 1 条页面断言，并补齐 resources 普查）。**57.2** 让材料包数出这张卡练过几场（第五行 `rehearsals`，与求职信同一个收窄；非零链到收窄后的面试列表，零不画门；1 条服务测试 + 1 条路由断言 + 2 条归一化断言 + 2 条面板测试）。**57.3** 让收窄列表上的「开始面试」为那张卡开始（创建带上 `applicationId`；1 条契约用例）。

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
- 40.2 常驻选择随包走（已完成 2026-10-31）：`saved_searches` + `ingestion_feeds`（后端所有）；按 id 匹配，省略即取消，
  字段级比较让未变行为 `skip`；匿名包把两节整节保留——筛选与公开地址都不指向某个人，闸门里两节的 `PEOPLE` 集为空、
  `SUBSTANCE` 集逐列写明，所以这是决定而不是遗漏。可读半边两种语言列出搜索的筛选与订阅源地址/开关；plan 的字段比较镜像 apply 的手：搜索名与订阅源名/地址都去空白，`source`/`enabled` 缺省补齐，所以 apply 刚写入的行再次导入仍是 `skip`；apply 写不了的行（缺名字、缺筛选、缺地址）既不承诺也不退休。
  schema 升到 1.4.0，1.3.0 旧包仍有效（`SECTIONS_BY_VERSION` 逐版本持有节集）。
- 40.3 书签与来信随包走（已完成 2026-10-31）：`saved_jobs` + `inbound_mails`（后端所有，schema 1.5.0，1.4.0 旧包仍有效）。
  书签只在其职位仍存在于目标工作区时写入（缺职位的书签计入该节 `skipped` 理由，而不是伪造一行悬空外键）；来信按 `message_key` 幂等折叠（同一 inbox 恢复两次不翻倍），归档链接只在调用者拥有该 application 时恢复。匿名包抹掉发件地址、主题、正文与书签附注；职位的标题/公司、分类读数与时间戳保留。plan 的比较覆盖 apply 实际写入的字段：书签的展示字段、来信由目标决定的 application_id、NULL→空字符串的 NOT NULL 文本都不算内容，所以未改行是 `skip`；apply 写不了的行（书签缺职位 id、来信缺 message_key 或 received_at）既不承诺也不退休。可读半边两种语言写出书签与来信，页面给出两节标签，恢复按节计数。
- 40.4 分界成为闸门（已完成 2026-10-31）：新闸门 `test_every_reader_table_is_carried_or_excluded.py` 解析
  `db/migration` 的每个 `CREATE TABLE`（含 ALTER 补列/补外键），按 `user_id`、`users` 根与 FK 可达闭包
  算出读者表：每张要么在 CARRIED 映射里落到某一节（`messages`→`conversations`、`resume_versions`→`resumes`、
  面试轮次与评估→`interviews` 这类内嵌子表声明父表并同节），要么在 EXPORT.md 的排除表里写明理由；理由只有
  `Bookkeeping:`（账户做过什么）、`Rebuilt:`（恢复时从包内数据重算）、`Shared:`（目录与平台夜报）三种前缀。
  排除表 27 行（9 Rebuilt + 15 Bookkeeping + 3 Shared），闭包 43 张 + 共享 3 张 = 迁移的 46 张；新表出现即按名失败。
  页面不再自带节列表：`lib/export-sections.ts` 只留标签，徽章与 redact 复选框读 `manifest.counts`（服务端逐节计数，
  零也在内），不认识的节回落为可读名字；Markdown/HTML 的节序与 manifest 的计数顺序都钉到 `SECTIONS`。

下一步：Epic 41 的下一段（Epic 40 已在 40.4 收口）。

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
  - **42.2** 卡片自己扳动这些开关（已完成）：新增 `PUT /api/v1/me/mail/settings/{list}`，body
    `{enabled}`（`Boolean` + `@NotNull`：缺字段是 400 `VALIDATION_FAILED` 而不是静默的"关"），
    未知 list 是新码 `MAIL_LIST_UNKNOWN`（400，且 `verify(never())` 证明没写列）；答案复用
    `settings(user)`，仍是 `no-store` 的三布尔。前端 `endpoints.mailSettingsDial`、
    `useSetMailDial`（乐观更新 + 失败回滚 + `failures.mailSettingSave` 的 toast）、`MailCard`
    把状态徽章换成 Switch（写时禁用，避免两笔并发写互相覆盖）。3 条后端 MockMvc 测试 +
    2 条 hook 写面测试；`test_response_shape_contract.py` 的 handler 拒绝名单补入
    `lib/hooks/mail-settings.ts`；API.md、DEPLOYMENT.md、architecture.md 同步。
  - 下一步（避开并发会话在制的 export/import）：仪表盘 attention 的提醒过期语义；或 Epic 40
    的后续单元（40.2 常驻选择随包走）提交后再接手。

- **Epic 43 — 卡片回答自己的问题**（本轮起）
  - 盘点结论（2026-10-30）：attention 卡把「提醒到期」与「两周没有进展」的申请列出来，但到期提醒
    只有两个回答——「明早再说」「不用记了」——都得打开申请对话框才说得出。卡片的本职就是被回答，
    它却只能指路。后端无需新端点：`PATCH /applications/{id}` 已经收 `reminderAt` 与
    `clearReminderAt`，缺的只是入口。
  - **43.1** 到期的提醒在它被读到的地方被回答（已完成）：`Snooze to tomorrow` 把 `reminderAt`
    写成**本地**明天 09:00（`lib/application-edit.ts` 的 `snoozeReminder(now)`：23:50 按下是九小时
    后，不是一天零十分钟；3 条确定性的纯函数测试，含跨月与午夜边界）；`Clear` 走对话框自己的
    `reminderPatch(row.reminderAt, "")`，所以 `clearReminderAt` 仍只在一个文件里被发明，乐观合并、
    提示与回滚都是对话框已有的那一套。两个按钮共用 `useUpdateApplication`（本行写时禁用本行两个按
    钮）；提醒变更现在也刷新收件箱——它把同一条提醒单列成一行。过期行没有按钮：没有可移动的提醒，
    「清除」也无事可清。新组件 `components/dashboard/attention-row.tsx` + 5 条 SSR 测试（含一条把
    两个按钮钉在行链接之外，回答时不会顺带导航）；浏览器源普查 148→149，缓存调用台账
    `invalidateQueries` 52→53。
  - **43.2** 收件箱里的提醒也能就地回答（已完成 2026-11-02）：收件箱把同一条提醒单列一行，
    读者在这里处理通知时仍要打开申请才能回答。两个按钮与 43.1 相同；application id 从条目的
    episode key `reminder:<uuid>:<epoch>` 读出（新纯函数 `lib/notification-reminder.ts` + 6 条
    单测），解析不出的 key 不给按钮——对猜来的 id 发 PATCH 不是 404 就是改错东西。`Clear` 仍走
    `reminderPatch(item.at, "")`，`clearReminderAt` 依旧只在一个文件里被发明；两个写共用
    `useUpdateApplication`，它 settled 时的收件箱失效让被回答的 episode 在服务端停止发送后离场。
    页面测试 5 条（含 key 不合法时没有按钮），中英各两条文案。
  - 下一步候选：attention 行的「谁在等你」（Epic 43 的下一段）；Epic 44 的收尾由并发会话在制。

- **Epic 44 — 删除欠存储副本的那两笔账**（本段起）
  - 盘点结论（2026-11-02）：删简历、删资料、删笔记都已经把 `documents.status` 从 `ready`
    摘走，检索的三条混合通道只认这一个谓词，所以「删了就再也引不到」是成立的。但两笔账没结：
    入库任务不认识删除——它已经在飞行途中，跑完就把 `retired` 改回 `ready`，读者刚删掉的文字
    重新变成证据；上传落进对象存储的字节则永远留在那儿——只有销号会扫掉 file_key，删单条
    不会，而 retired 行连同 chunk 作为审计记录被无限期留着，没有期限。
  - **44.1** 迟到的入库不能复活已删除的文档（已完成 2026-11-02）：`set_status` 的两条语句都带上
    `AND status <> 'retired'`，并回答「这一行动了没有」，于是谁后写都轮到删除赢；`replace_chunks` 先读
    状态，retired 或已经不存在的行一条 chunk 也不写，审计保持原样。pipeline 两处写都听这个答案：
    一开局读到 retired 的任务什么都不写，直接说「文档已退役」；嵌入途中失去这一行的任务在
    `mark_source_ready` 之前停下，不宣布一个并不存在的索引结果。后端迟到的 `markFailed` 也不擦
    退役标记——触发失败不是复活的理由。9 条 ai-service 测试
    （`tests/test_retired_documents_do_not_come_back.py`）+ 2 条后端测试
    （`FileIngestRetirementTest`）；architecture.md 写明 retired 是终态。
  - **44.2** 删条目要收回它上传的对象（已完成 2026-11-02）：`StoredObjectReclaimer` 拿退役交回来的
    key，逐个问两句——还有没有被检索引到的 document 用它，还有没有简历版本把它当原始文件——两句都
    否才删。等待提交写在 reclaimer 里而不是调用方：单条删除自己的事务、整包恢复自己的大事务，都在真正
    提交之后才被判断——回滚的删除动不了文件，存储拒绝也只是把对象留下并记
    `failed`，行删除照旧成立。两句问题之所以都在，是因为一次上传是一个对象后面两行——删简历的入库副本
    时，简历页面还在发同一批字节，于是只有删简历才收得走；切换当前版本那种只退役副本的调用什么都不问。
    结果按 `careeros.storage.objects_reclaimed{outcome}` 计数。10 条 `StoredObjectReclaimTest`
    + 3 条 `ResumeDeleteReclaimTest` + 5 条 `ObjectReclaimIT`（需真实栈），退役测试改为读回 key；
    architecture.md 与 DEPLOYMENT.md 同步这条引用核对。
  - **44.3** 审计记录要有期限（已完成 2026-11-02）：`RetiredEvidencePurger` 在同一个夜间扫描里
    清掉退役超过 `RETENTION_RETIRED_DOCUMENT_DAYS`（默认 180 天）的 document 行，chunk 由 V1 声明的
    `on delete cascade` 随行消失——后端对这张表没有任何仓库，它是 ai-service 写的，所以这两条路径
    是 chunk 唯一的去处。被清掉的行把手里的 key 交给 44.2 的 reclaimer：等这一批行真正提交之后才问
    存储，因为"收回失败"的线索就是这行还写着 key，窗口把行烧掉之前必须先问。还活着、还在索引、
    还能重试的行都不动；仍被 source 指向的 retired 行留着并单独说一句 WARN——悄悄什么都没删的夜里
    和本来没东西可删的夜里长得一样。`documents` 与 `document_chunks` 各自计数（同一语句的活，
    要么一起有读数要么一起缺），沿用那个停摆就会报警的心跳；V31 给 retired 那一片加了部分索引。
    7 条 `RetiredEvidencePurgerTest` + `RetentionSweeperTest` 新增 3 条（共 10）
    + 4 条 `RetiredEvidencePurgeIT`（需真实栈）；architecture.md、DEPLOYMENT.md、RUNBOOK.md、
    alerts.yml 与两份 env 示例同步这个窗口。
  - 下一步候选（避开并发会话正在改的文件）：Epic 44 已闭合，另开下一段。

- **Epic 45 — 每种信号说自己的句子**（本段起）
  - 盘点结论（2026-11-02）：收件箱的后端会发六种 kind，页面只给其中五种自己的徽章与句子。
    `saved_search` 落到通用徽章「Signal」，服务器算出的搜索名与条数都丢失；`reply` 的句子
    虽已写好，却没有一条测试读过它——下一次改动可以让它悄悄消失。
  - **45.1** 已保存搜索的提醒说它找到了什么（已完成 2026-11-02）：`saved_search` 现在有了
    另外五种早已具备的两样东西——徽章「已保存搜索」，以及说出名字与条数的句子
    （`你的已保存搜索「远程 Rust」有 4 个新职位。`，没有名字时用「一个未命名搜索」）。
    它与「拉取建了职位」同用 success 徽章：这是职位板在回答读者自己问过的问题。回信的
    句子（`招聘方回复了你的投递 —— Initech。`）此前只有实现没有测试；现在每种 kind
    一个 fixture，中英各断言两种句子、服务器写下的主题行（`Re: interview`）、
    `/replies?mail=...` 链接与未读数。只动页面测试：服务器本来就在发这两种 kind。
  - **45.2** 收件箱一次读一种，空态说清什么会来（已完成 2026-11-02）：列表上方多了一行
    筛选片——`All` 加当前收件箱里真实存在的每种 kind（按后端声明顺序，带各自的条数），
    选中的片 `aria-pressed` 为真；选择存进地址栏（`useUrlState`），刷新或分享链接落在
    同一个视图，而 `?kind=replied` 这种过期的书签被 `asInboxKind` 判为「不筛选」，宁可不筛
    也不给一个看起来像安静早晨的空表。新纯函数模块 `lib/inbox-filter.ts`：`kindsPresent`
    （只列存在的 kind、按服务器顺序、含条数）、`asInboxKind`（只认页面叫得出名字的六种）、
    `rowsUnder`（无筛选是全部）。空态文案此前只承诺三种来源，现在把六种都说完（失败拉取、
    建了新职位的拉取、找到新职位的已保存搜索、招聘方回复），顶部描述同步。5 条纯函数测试
    + 6 条页面测试；前端 947 条 / 92 文件。
  - **45.3** 只看未读是同一行上的第二维（已完成 2026-11-02）：筛选行右侧一个
    `只看未读` 开关，带收件箱的未读条数；它与某个 kind 的筛选片叠加而不是替换——
    读者可以只要「未读的招聘方回复」。选择走同一套 `useUrlState`（`unread=1`），刷新后
    仍在；`rowsUnder` 增加第三个参数，在 kind 过滤之后再丢掉已读行，屏幕上显示什么仍由
    一个函数回答。未读为 0 且当前不在未读视图时开关禁用（没有东西可筛的按钮是死按钮），
    已经在未读视图里的读者总能退出。多 1 条纯函数测试；前端 948 条 / 92 文件。
  - **45.4** 已读的行一次清掉，未读的行原地不动（已完成 2026-11-02）：收件箱徽章旁多了
    一个 `清掉已读` 动作，把读者已经处理过的行一次收走，未读的信号一个都不动。后端新增
    `POST /notifications/dismiss-read`（`API.md` 同步，正文为空——它不收任何字段），照旧
    用最新的收件箱回答；`dismissRead` 只走可见且已读的行，并按各自的 episode key 记下，
    因此同一个申请的新 episode 会以未读回来，而不是继承这次归档。没有已读行时按钮不
    出现（背后没有东西的动作是死按钮）。3 条服务测试 + 1 条路由测试；后端非 IT 选集
    1110 条全绿；前端 948 条 / 92 文件不变。
  - 下一步候选：attention 行的「谁在等你」，或收件箱按来源分组之外的第三种视图。

- **Epic 46 — 卡片说出谁在等你**（本段起）
  - 盘点结论（2026-11-02）：attention 行只解释「为什么列出来」（提醒到期 / 久无动静），
    可招聘方昨天刚回复这一事实才是让这行值得点开的原因；卡片在读者收件箱里躺着回信时
    仍说「没有进展」，讲的是错的故事。行的 reason 仍由查询自己判定，最新的回信只是随行
    附带，不改谓词也不改计数。
  - **46.1** 申请上的回信在 attention 行上报出名字（已完成 2026-11-02）：attention 查询
    新增一个 `LEFT JOIN LATERAL`——每份申请取 `inbound_mails` 里最新的一封（按收到时间、
    再按 id 倒序，只取一行），负载带上它的主题与时刻（`replySubject` / `replyAt`）。
    行在「久无动静」那句下面多一行：`招聘方 3 天前回复了 · Re: interview`；没有回信的
    申请渲染得和以前完全一样。谓词与计数不动：回信是上下文，不是新的「需要关注」理由。
    2 条 SSR 测试 + 归一化精确形状 + 仓库列映射；前端 950 条 / 92 文件。
  - **46.2** 那句「谁在等你」自己能打开那封信（已完成 2026-11-02）：`AttentionItem` 多带
    一个 `replyId`——同一个 LATERAL 已经取到主题与时刻，顺手把信自己的 id 也带上——行里
    的回信句子变成指向 `/replies?mail=<id>` 的链接，而 `/replies` 页本来就会高亮 URL 里
    点名的卡片。句子移到申请链接之外（浏览器建不出锚点套锚点的页面），仍与标题左对齐；
    负载没有 id（旧缓存行）时句子照旧渲染成文本——指向虚无的链接比没有链接更糟。
    1 条 SSR 测试（`href`）+ 1 条无 id 形状 + 仓库列映射；前端 951 条 / 92 文件。
  - 下一步候选：「谁在等你」成为第七种收件箱信号，或 reply 句子在收件箱行里也指向那封信。


- **Epic 47 — 申请记得它寄出的材料包**（本段起）
  - 盘点结论（2026-11-02）：申请行存了简历版本、JD 分析与匹配三个链接，详情却只把 UUID
    打出来。UUID 不是读者能核对的东西：它不说是哪个版本、是否定制过、JD 问了什么、匹配
    打了多少分。更糟的是，链接存在但行已不可读时，界面只会显示一个无法点击的字符串。
  - **47.1** 材料包按材料读（已完成 2026-11-02）：新增
    `GET /api/v1/applications/{id}/packet`，用原本拥有这些行的用户级仓库解析三个链接——
    简历版本带出简历标题、标签与类型；JD 带出分析器自己的职位/公司，缺失时回落到职位；
    匹配带出分数与所属职位。每个 `*Linked` 开关读申请自己的列，而值在该行不属于调用者
    时为 null：跨账号的 id 既不泄露，也不会被误说成「从未关联」。详情里的 UUID 列表换成
    三行材料包面板，每行可点回原页面。3 条服务测试 + 1 条路由测试 + 5 条 SSR 测试 +
    2 条归一化测试。
  - **47.2** 看板先报出材料完整度（已完成 2026-11-02）：新纯函数 `packetCompleteness`
    读同一组三个链接，按面板顺序返回 `{linked,total,missing}`；卡片在至少有一项时显示
    `材料 2/3` 徽章——不完整是 warning，三项齐是 success——`title` 说出缺的是哪几项。
    一个都没关联的卡片保持安静：计数分不出「还没开始」和「材料坏了」，它不假装分得出。
    3 条纯函数测试。
  - **47.3** 职位详情页知道自己已在流水线（已完成 2026-11-02）：`GET /applications` 接受
    `jobId`，详情页因此只问自己这个职位，而不是把整块看板翻一遍再在内存里筛。动作栏的
    「加入流水线」在已有申请时变成 `已在流水线 · 已投递`，链到那张卡自己的编辑器
    （`?application=<id>`）——再按一次只会多出一张重复卡。同时给 `jobId` 与 `status` 时
    两者都生效：状态是在同一个职位内继续收窄，而不是被悄悄丢掉。2 条服务测试。
  - **47.4** 求职信有归处（已完成 2026-11-02）：新增 `application_letters`（V32），申请的
    详情路由可以存下一封求职信，也可以按新到旧读回；两个路由都从调用者自己的申请出发，
    空正文是 `VALIDATION_FAILED`，生成时的语气与长度随信保留。职位页的草稿面板多一个
    「保存到申请」——不在流水线时按钮禁用并说明原因——申请抽屉则就地把每封信念出来：
    首行、三个刻度和完整正文。导出包以 `cover_letters` 章节带上它们（schema 1.6.0），
    恢复时跟随真正落地的申请 id，不把信挂到别人的新行上。4 条服务测试 + 路由测试 +
    4 条 SSR 测试 + 2 条归一化测试；导出契约 87 条。下一步：让材料包把求职信也计进去。

- **Epic 48 — 桶里那些没有行指向的字节**（本段起）
  - 盘点结论（2026-11-02）：Epic 44 结清了「删除欠存储副本那笔账」——再没有任何行能被引到，
    字节就跟着走，审计记录也上了期限。但仍有两类字节永远没有任何行指向它们。上传是先把对象
    写进桶、再开事务插行（`FileIngestService` 与 `ResumeService` 都是这个顺序），所以事务在
    put 之后失败，桶里就留下一份「生下来就没有行」的对象：44.2 的 reclaimer 从行出发，销号也
    从行出发，两者都看不见它。另一类是 44.3 的窗口烧掉的线索——存储拒绝收回时，key 只写在那行
    退役行里，行随窗口消失，DEPLOYMENT.md 如今只能承认那对象成了孤儿。根因是 `StorageService`
    没有列举：这个桶从来只按数据库恰好点到的 key 走查，没人能问「桶里到底有什么」。
  - **48.1** 端口能列出自己的桶，每个 key 的主人被点名：列举操作回答 key、最后修改与字节数，
    而列举失败或只列出一半必须响亮地失败——一次残缺的列举被读成「桶里没有东西」正是本项目在制
    的那类缺陷。同时立普查：往桶里写的只有那两个服务，能持有 key 的列只有 `documents.file_key`
    与 `resumes.source_file_key`；第三个主人出现时该红的是普查，而不是让它对扫描悄悄隐形。
  - **48.2** 夜间扫描收回到没有任何行指向的对象：列出桶，减去任何状态的行指向的 key（退役行的
    key 仍是 44.2 的线索，不是垃圾），只动过了窗口的对象（给在飞事务留时间），列举失败就一个
    都不删。沿用退扫那个停摆就会报警的心跳，按结果计数，存储拒绝时报警——把 DEPLOYMENT.md 里
    「孤儿」那句从描述变成去处。
  - **48.3** 每个出厂的表要么被规则读，要么被点名豁免：报警门如今只问「规则点名的指标是否注册
    了」，从没反向问「注册了的指标有没有规则读」——`careeros.storage.objects_reclaimed` 就是带着
    「操作员应当去读它」的 RUNBOOK 句子出厂，却没有任何规则读它。方向翻过来，豁免逐条给理由。
  - **48.4** 浏览器唤醒被拒要有规则读，「谁在看这条序列」搬到操作员真正打开的那页上（已完成
    2026-11-05）：48.3 的豁免把整个 push 家族一起免了，理由是四个结局没有共同阈值——对家族成立，
    对单个 tag 不成立。一天三次 `refused` 不是正在流失的注册（那种答复 404/410，同一轮就记成
    `gone` 并当场删行）：没被唤醒的那条通知仍停在未推状态，下一轮还会去问同一个浏览器，所以拒绝
    会重复。第 13 条规则因此只读 `outcome="refused"`。豁免也不再住在门里的 dict：DEPLOYMENT.md
    新增「Every Meter and What Watches It」，21 行对应 Java 注册的 21 条序列，「哪条规则读它」这一格
    与 alerts.yml 双向比对——写的规则必须正好是表达式里点了这条序列的那些，规则来了旧豁免就红，
    规则被删了那行也不能继续声称有人看。
  - 下一步候选（避开并发会话正在改的文件）：Epic 48 到 48.4 已闭合；下一段从盘点开始。


- **Epic 49 — 回信能被找到**（本段起）
  - 盘点结论（2026-11-02）：回信页能翻页，却不能被提问。手里有四十封信、心里只有一个招聘方
    名字的读者，只能一次翻五十封；列表上方的「共几封」说的是整个收件箱，而不是他正在找的
    东西。服务端本来就能回答更窄的问题，只是页面从没问过。49.1 让列表路由绑定 `q`，按主题、
    发件人、公司与职位做大小写无关的子串匹配——正是读者手工会去搜的几个字段——并给搜索下的
    空态它自己的句子。空白的 `q` 必须仍是不提问：搜索框一出现，一次会过滤的空搜索就会把
    每一页变成「没有匹配」。而没有匹配的空态不能借收件箱那句「去拿一个地址」：一个有四十封
    信的人不需要去修一个其实好好的部署。
  - **49.1** 回信可搜索（已完成 2026-11-02）：`GET /inbound/mails` 绑定 `q`，服务端先 trim
    再小写，返回的分页总数描述缩小后的集合。仓库用 `LOCATE` 而不是绑定后的 `LIKE`：读者
    在搜索框里敲 `%`，要找的是百分号，不是「全部回信」；`COALESCE` 让没有公司或职位的信
    仍能被主题或发件人搜到——null 在 `OR` 里不能吞掉别的分支。页面保留草稿框、回车才查询，
    URL 留着这些词，刷新就是同一个问题；搜索下的空态给「清除搜索」，不指向设置页。2 条
    服务测试 + 1 条路由测试 + 3 条 SSR 测试；顺手修掉列表在一整页未归档信件上的 `Map.of()`
    NPE——空 map 拒绝 `byId.get(null)` 的 null 键，过去这一页会 500。前端 964 条 / 94 文件；
    后端 1117 条。
  - **49.2** 回信可以按「说的是什么」筛（已完成 2026-11-03）：`GET /inbound/mails` 在 `q`
    旁边绑定 `intent`——分类器给出的五种读数之一，或 `unread`（它还没读过的信）。两个筛
    选项在同一条查询里同时生效：读数收窄的是这些词，而不是替换它们，分页总数描述的是交
    集。集合之外的字回答 **400** `INBOUND_INTENT_UNKNOWN`：一页空白会读成「你的收件箱里
    没有这些」，而真正的错在筛选上。仓库的页查询把读数当作可空参数、把「未读」当作独立
    布尔，所以「不筛」与「没有读数的信」是两个问题；空白的 `q` 仍是不筛，而不是空房间。
    页面在列表上方画出六枚 chips，选中的那枚留在 URL 里；空态分别说清是词、是筛选、还是
    两者一起没找到——「看全部回信」把两者一起清掉，筛空的页面仍不是空收件箱。4 条服务
    测试 + 1 条路由测试 + 3 条 SSR 测试。
  - **49.3** 搜索读进信的正文（已完成 2026-11-03）：`q` 在信封的四个字段之外也看
    `bodyText`，所以记得「we would like to schedule」的读者能找到说过这句话的那封信，而
    不是一页空白；搜索框的无障碍标签也把正文写进去。新增一条查询文本测试，钉住五个字段
    与两个筛选——这是 mock 住的 service 测试看不到的那一半。没有新路由，没有新参数。
  - **49.4** chips 数出自己会展示的东西（已完成 2026-11-03）：新增
    `GET /inbound/mails/intents`，只按 `q` 收窄的一行分组计数。读数不能收窄计数：选中的
    chip 必须继续显示支撑它这个字的全部信，否则它会在自己被选中的那一页上读成 0。服务端
    补齐六个字——`unread` 在前、五个读数在后、零也出现——一个到零就消失的 chip 是读者
    发现不了的字；null 读数按 `unread` 计，与 49.2 的语义一致。页面把数字画进各自的
    chip，「全部」是六者之和。2 条服务测试 + 1 条路由测试 + 1 条查询文本测试 + 1 条 SSR
    测试；后端 1178 条，前端 1035 条 / 101 文件。
  - 下一步候选：回信列表按「已归档/待归档」筛选（`q` 与 `intent` 之外第三维，收窄并保留
    chips 计数），或给收件箱的空态补一条「去看全部」。每单元照旧：代码 + 测试 + 闸门 +
    文档 + 提交。

- **Epic 50 — 保存下来的信归读者管**（本段起）
  - 盘点结论（2026-11-03）：47.4 让草稿有了归处，却只给了它「新增」和「读取」两个动词。
    一次误存、一次重复保存、一次用错简历版本写下的草稿，都只能永久留在抽屉里；读者没有
    办法把不该在的东西拿走。这正是「能存」还不等于「是自己的」的地方。
  - **50.1** 保存下来的信可以删掉（已完成 2026-11-03）：新增
    `DELETE /applications/{id}/letters/{letterId}`，先按调用者拥有该申请，再只删
    `id + applicationId + userId` 三者同时命中的那一行；已经不在的信仍然回答 204——读者
    的意图已经成立，不需要用 404 再说一遍——而从别的卡片抄来的 id 什么也删不到。抽屉里
    展开的信多一个「删除这封信」，沿用申请自己的破坏性确认框，删除成功后列表在提示消失
    前已经刷新。2 条服务测试 + 1 条路由测试；顺手把 `/applications` 的查询参数从阅读器
    读不懂的展开改为显式键，路由普查因此真的检查 `page/status/jobId/size`，`jobId` 与
    并行会话的 `intent` 也写回了两侧的参数账本。
  - **50.2** 保存下来的信可以改（已完成 2026-11-03）：新增
    `PATCH /applications/{id}/letters/{letterId}`，改的是读者已经留下的那一行，不另起一份
    草稿；正文必填并 trim，传 null 的刻度保持原值、传空串才清掉。`updated_at` 随修改移动，
    抽屉于是说「修改于 …」而不是最初保存的时刻。信已经不在、或属于别的申请/账号时，抛出
    自己的 `APPLICATION_LETTER_NOT_FOUND`，绝不改到别的东西上。抽屉里展开的信多了「修改
    这封信」：正文变成 textarea，带保存与取消；保存成功后列表在提示消失前刷新。3 条服务
    测试 + 1 条路由测试 + 错误码普查 + 1 条新增 SSR 测试。
  - **50.3** 保存下来的信可以带走（已完成 2026-11-03）：抽屉里展开的信多了「复制全文」与
    「下载 Markdown」，都读同一份正文——信已经是读者的，就得能放进真正要发它的那个邮箱里。
    文件名优先用职位的英文标题（`cover-letter-senior-frontend-engineer.md`），标题没有拉丁
    字母时退回这封信自己的 id 前 8 位，中文标题不会塌成同一个 `document`。空信不给这两个
    动作，而不是复制一片空白。4 条纯函数测试 + 2 条新增 SSR 测试。下一步：让材料包把求职信
    也计进去，或让职位页的草稿知道自己已经存过。
  - **50.4** 修改也能拨动刻度（已完成 2026-11-03）：信是带着语气与长度写下的，改词的人也可能
    想改这两个刻度。原地编辑现在从这封信真正保存时的刻度起笔，用生成器同一份目录，并多一个
    真正的「未设置」。第三种状态正是 `dial()` 与 `field()` 并排存在的理由：路由把缺键读成
    「别动」，把空串读成「清掉」，而 `field` 按设计会丢掉空串。目录不认识的旧值（如 `warm`）
    照原样显示，而不是默默空白。8 条纯函数测试 + 3 条请求体测试 + 2 条 SSR 测试；`endpoints.test` 的
    包把求职信也计进去。

- **Epic 51 — 草稿与柜子互相知道**（本段起）
  - 盘点结论（2026-11-03）：信写在职位页、存在流水线里，两块屏幕却互不相认。写的人每生成一次
    都看到「存入申请」，看不出这个职位已经有几封、也无从回头去读。
  - **51.1** 写的人看得见这个职位已经留下什么（已完成 2026-11-03）：职位页的求职信卡片在职位
    进入流水线后读回该申请自己的信，写「这个职位已保存 N 封」，旁边一条通往 `/applications`；
    一旦有信，保存按钮改口叫「再存一份」，不再假装柜子是空的。读取共用抽屉的查询键，存下一封
    之后计数立刻跟着动。2 条 SSR 测试。
  - **51.2** 那行计数直接打开那张卡（已完成 2026-11-03）：原先链到 `/applications`，等于让读者
    到了板上再找一遍；现在带上 `?application=<id>`——attention 行和流水线徽章早就在用的同一条
    深链——板子画出来时那张申请自己的抽屉已经开着。
  - **51.3** 空柜子指向能装满它的那一页（已完成 2026-11-03）：抽屉的空态原本只说「在职位页保存
    的草稿会收在这里」，让读者自己去找那一页。申请带着 `jobId` 时，这句话末尾多一条通往
    `/jobs/{jobId}#cover-letter` 的链接，起草卡片上也挂了同一个 id，锚点落得准；没有职位的申请
    保留原来的提示——没有诚实的去处就别说有。1 条 SSR 测试。下一步：让抽屉直接停在求职信那一节。

- **Epic 52 — 读者留下的一切都找得到**（本段起）
  - 盘点结论（2026-11-03）：`GET /search` 一直能跨六组回答，但 47.4 留下来的信不在其中——草稿只能
    靠打开它所在的卡片去找。而且这个端点在前端从来没有表面：⌘K 面板一直没做，整条跨实体搜索
    都是隐形的。
  - **52.1** 信也能回答搜索（已完成 2026-11-03）：`SearchResponse` 多出第七组 `letters`：信 id、
    它所属的申请、职位标题、180 字摘要与 `updated_at`。匹配既读信的正文，也读职位标题，所以搜
    「Acme」能找到为 Acme 写的那封信；排序键是 `updated_at`，刚改过的那封因此排在组内最前。申请
    id 让命中可被打开——面板唯一诚实的去处是看板的抽屉（51.2）。仓储测试钉住这一组的参数、排序
    的 tie-break，以及那条把职位带出来的 join。2 条仓储测试。
  - **52.2** ⌘K 面板把信也列出来（已完成 2026-11-03）：面板本来就在调 `/search`，但它的组表停在
    第六组，服务端返回的信被解码之后又被丢掉；把这张表和 Java 记录的组件钉在一起的那条契约
    测试，正是这个遗漏一直诚实而不沉默的原因。`letters` 成为第七行：职位标题作主行、正文开头作
    副行、href 是 `/applications?application=<id>`——信没有自己的屏幕，抽屉就是它的家（51.2）。
    没有申请 id 的信退回看板，而不是 `/applications?application=undefined`。3 条归一化测试。下一步：
    让面板记住最近搜过什么。
  - **52.3** 面板记住跑过的查询（已完成 2026-11-03）：读者信得过的查询不必每次重打。面板把最近
    五条放进 `localStorage`——是浏览器的记忆，不是账号的，因为搜索是浏览器的一刻，而面板必须
    在 `/users/me` 回答之前就能用。规则住在 `lib/recent-searches.ts`，因此不需要浏览器也能测：
    trim、比较时折大小写、最新在前、最多五条；坏掉的条目和拒绝写入的隐私模式都不会弄坏面板。
    6 条纯函数测试 + 1 条接线测试。下一步：让最近搜索也能清空。
  - **52.4** 记住的查询也能被忘掉（已完成 2026-11-03）：读者清不掉的列表是记录，不是便利。最近
    搜索组末尾多一条「清空最近搜索」，它删掉那个键并回答自己留下的空列表——面板信的正是这个
    回答，所以拒绝删除的隐私模式不会让界面声称列表还在。1 条纯函数测试 + 1 条接线测试。
    下一步：材料包把求职信也计进去。

- **Epic 53 — 材料包把每一件都数进去**（本段起）
  - 盘点结论（2026-11-03）：材料包（47.1）用三个链接回答「这张申请带着什么」——简历版本、JD
    分析、匹配。47.4 保存下来的求职信根本不在这份回答里，于是抽屉可以一边说「材料包 3/3」，
    一边在下面躺着三封没被数进去的信。信是唯一以「数量」而不是「链接」存在的产物：它没有
    自己的屏幕，也可以有好几封。
  - **53.1** 材料包把求职信也计进去（已完成 2026-11-03）：`GET /applications/{id}/packet` 多出
    `letters`，即这张申请、这位调用者名下的 `application_letters` 行数。和旁边的三个查询一样
    按用户收窄，别人的行永远不会被算成这张卡的。抽屉第四行说「已保存 2 封」或「还没有保存」，
    不挂状态徽章——对一封从未写过的信说「未关联」是假话，而数量本身就是状态。线上类型里
    `letters` 可选、缺失读作 0，旧构建画不出「undefined 封」。材料包全空的句子现在也要求信为
    0。2 条服务测试 + 1 条路由断言 + 4 条 SSR 断言 + 2 条归一化测试。下一步：看板卡片也报出
    信的数量。
  - **53.2** 看板卡片报出自己存了几封信（已完成 2026-11-03）：卡片数得了三件产物（47.2），
    却数不到它们下面保存的信。`GET /applications` 现在每行都带 `letters`，用一次分组查询
    ——`count by application_id where user_id = 调用者`——读完整页，五十张卡也只多一次读，而
    不是五十次。计数和材料包一样是派生的、按用户收窄的；没有信的行不在 map 里，仍然读作 0。
    卡片只在总数大于零时画一枚信封徽章「3 封信」，完整句子放在 title 里；一封都没有的卡不该
    挂一个恒为零的徽章。2 条服务测试 + 1 条映射测试 + 2 条 SSR 测试 + 1 条归一化测试。
    下一步：从 `?application=<id>` 直接停在求职信那一节。
  - **53.3** 搜索到的信直接落在它住的那一节（已完成 2026-11-03）：52.2 的 href 会打开抽屉，
    却停在最上面——搜到正文的读者还得越过表单、时间线和材料包才能找到那封信。求职信面板现在
    带着 `id="letters"`，面板的信用命中以 `#letters` 结尾，抽屉打开后把这一节滚进视野，再用
    `history.replaceState` 把 hash 从地址里抹掉，之后平开同一张卡不会再跳。没有申请的命中仍然
    落到看板、不带 hash。1 条归一化断言 + 1 条 SSR 断言。
- **Epic 54 — 留下的信能起下一封**（本段起）
  - 盘点结论（2026-11-03）：留下来的信是读者自己的东西，写信时用的旋钮也是。抽屉能把语气与长度
    读回来，可要再写一封，读者只能回到职位页、凭记忆把同样的值再选一遍。
  - **54.1** 留下的信把自己的旋钮交给下一封（已完成 2026-11-03）：每封属于某个职位的信，在
    编辑 / 复制 / 下载旁边多一个「照这个样子再写一封」。它的地址是
    `/jobs/{jobId}?tone=…&length=…#cover-letter`：hash 落到起草卡片（51.3），面板在挂载时
    从地址里采纳两个目录内的旋钮——未知的、手改的值一律忽略、保留默认，因为下拉框显示不出的
    值会被静默地拿去生成。离开信时也只放行目录内的值：目录之前存下的 `warm` 不会被打包寄回。
    5 条纯函数测试 + 2 条 SSR 断言。
  - **54.2** 留下的信说得出自己写自哪个简历版本（已完成 2026-11-03）：信行里只有一个
    `resumeVersionId`，是读者用不上的 uuid。抽屉现在为每封带 id 的信读
    `GET /resume-versions/{id}`（一条浏览器从没要过的路由，它因此离开「未接线」普查表），
    印出「写自 ‹版本名›」并链到 `/resumes/{resumeId}`——版本住在那儿，也能在那儿打印。
    读不回来的版本会明说，而不是整行消失：来源丢了本身就是信息。2 条 SSR 测试 + 1 条映射
    测试 + 端点普查移除一行。
- **Epic 55 — 面板里的每一条命中都去它说的地方**（本段起）
  - 盘点结论（2026-11-03）：面板（52.2）学会显示七组，可其中一组仍在说谎——申请的命中带着
    那一行自己的 id，却把它丢掉，让读者落在整块看板上。面板不该一边叫出名字、一边又让读者
    自己去找。
  - **55.1** 申请的命中直接打开它的抽屉（已完成 2026-11-03）：这条 href 原本是光秃秃的
    `/applications`，id 解码完就扔了。现在它是 `/applications?application=<id>`——仪表盘的
    attention 行早就在用的深链（51.2），板子画出来时那张卡的抽屉已经开着。没有 id 的命中
    （线上不会出现的形状）仍然退回看板，而不是 `/applications?application=undefined`。
    1 条归一化断言。
- **Epic 56 — 演练记得自己是为哪张卡做的**（本段起）
  - 盘点结论（2026-11-03）：产品的环线说面试反馈会喂回「学什么、投什么」。会话表带着职位、
    JD 分析与简历版本，却从来没有那张看板卡，所以从卡片开始的演练回不去，列表也说不出它属于
    哪条投递。
  - **56.1** 演练可以写下自己的申请（已完成 2026-11-03）：`interview_sessions` 多出可空的
    `application_id`（V35，`ON DELETE SET NULL`：删掉卡片时练习历史照旧站着，而不是被抹掉）。
    `POST /interview/sessions` 接受 `applicationId`；服务要求这张卡属于调用者——猜来的 id 是
    **404** `APPLICATION_NOT_FOUND`，而不是别人的会话——并把请求留空的每个目标字段（职位、
    JD 分析、简历版本、角色、公司）从卡上补齐。调用者自己给的字仍然优先。3 条服务测试，两条
    原子性 IT 的构造参数同步。
  - **56.2** 抽屉为这张卡开一场演练（已完成 2026-11-03）：「为这个职位演练」坐在材料包下面、
    求职信上面——一键就从这张卡建好会话并跳到 `/interviews/{id}`，落地即第一道题。按钮带着
    创建变更自己的 loading 态；创建失败走 hook 的提示，而不是一次没有回应的点击。
  - **56.3** 面试列表指回那张卡（已完成 2026-11-03）：会话带着申请 id 的行多一个「打开申请」，
    指向 `/applications?application=<id>`——打开那张抽屉的深链（51.2）。自由练习没有卡，就
    没有这条链接。1 条页面测试。
  - **56.4** 会话页与报告也指回去（已完成 2026-11-03）：两个页头都挂同一条「打开申请」，经由
    一个 helper（`lib/interview-target.ts`），列表、面试器、报告三处因此在路由上、以及在
    「自由练习没有卡」这件事上不会各说各话。2 条纯函数测试。
  - **56.5** 这条链接能跟着备份走（已完成 2026-11-03）：导出本来就 `SELECT s.*`，列一直在
    包里；恢复却没写它，于是带回来的每场演练都丢了卡。`applyInterviews` 现在写回它——经由
    一个 `cardLink` helper，与回信的卡同一条规则：只有目标账户拥有这张卡时才保留 id，全新
    账户里演练照旧落地、只丢掉链接，因为这一列是外键而不是文本，盲写会让整行失败。计划器
    按 section 剥掉它，所以「目标没有这张卡」的恢复是 skip，而不是每次都重写整份对话。3 条
    后端单测 + 1 条导出断言 + 1 条计划器测试。
- **Epic 57 — 卡片记得练过什么**（本段起）
  - 盘点结论（2026-11-03）：链接已经双向了一半——列表与报告能打开卡片（56.3/56.4），卡片却
    说不出为它练过几场。演练列表本来就是同一块板，只是要能收窄。
  - **57.1** 一张卡的演练是一份列表（已完成 2026-11-03）：`GET /interview/sessions` 接受可空的
    `applicationId`；查询同时按调用者和卡片收窄，所以猜来的 id 是空页而不是别人的历史。页面像
    页码一样从 URL 采纳 `?application=`——收窄后的列表可分享、刷新也不会悄悄变宽——并说清自己
    在显示哪张卡，留一个出口：页头与空态里的「全部面试」。2 条后端测试 + 1 条契约用例。
  - **57.2** 抽屉数得出练过几场（已完成 2026-11-03）：材料包多出第五行 `rehearsals`，按调用者
    与卡片一起收窄，和求职信同一个数法。它是唯一会链出去的计数：非零就打开
    `/interviews?application=<id>`（57.1 的收窄列表）；零说「还没有演练」，也不画门，因为门后
    没有东西。这也是材料包里第一行关于「投出去之后回来了什么」而不是「寄出去了什么」的事实。
    1 条服务测试 + 1 条路由断言 + 2 条归一化断言 + 2 条面板测试。
  - **57.3** 在卡片的列表上开始演练，就是为这张卡开始（已完成 2026-11-03）：筛选是读者自己选的
    上下文，创建也读它——收窄状态下开始菜单把 `applicationId` 一起交上去。此前按钮开的是自由
    练习，报告上没有卡，而且读者来的那份收窄列表根本不会出现这场新会话。1 条契约用例。
  - **57.4** 行上写着卡片正在哪一阶段（已完成 2026-11-03）：`SessionItem` 多出 `applicationStatus`，
    整页一次分组查询读回（`ApplicationService.stagesOf`，卡片和调用者一起收窄，所以不是自己的卡
    就是缺席而不是借来的）。列表把它画在分数旁边：一张已被拒的卡和一张还在面试中的卡，练过的
    东西不是同一件事。详情也带着它——跑面试的页头和报告页头读的就是这个。1 条服务测试 + 1 条
    映射测试 + 1 条页面断言，并把已经落后三个提交的 resources 普查重新对齐。

- **Epic 58 — 搜索框装的是词，不是模式**（本段起）
  - 盘点结论（2026-11-06）：后端最后一处用 Spring Data 派生方法写「包含」查询的地方就是公司板。派生的
    `...Containing...` 自己把读者的值包进 `%…%`，中间不转义任何东西，所以读者打的字符到了 SQL 就变成
    模式而不是词。别的列表都已经过 `LikePattern` 或 JPQL `LOCATE`，只有它没有——而且这条路由从 #222
    起就答 `?q=`，屏幕却从来没问过它。
  - **58.1** 公司板把 `?q=` 读成字符（已完成 2026-11-06）：查询的分支变成一条 JPQL `searchByName`，
    `LOCATE(:needle, LOWER(c.name)) > 0`——就是 `InboundMailRepository.findPage` 早先用的写法——服务层
    每次请求把针形词 trim 并小写一次，浏览那条分支不变。`SearchNeedleContractTest` 把四个针形词的主人
    当作一个整体普查，并拒绝后端里任何派生「包含」声明或手工包的 `%`；`CompanyNeedleIT` 在真 HTTP 上证明
    匹配（字面的 `%`、字面的 `_`、打错的缩写符号必须匹配不上、空框仍然是整份浏览）。5 条契约测试 +
    3 条不依赖 Docker 的服务测试 + 2 条 IT。
  - **58.2** 公司板问出自己的问题（已完成 2026-11-06）：页头多一个走 `ModuleView` 现有 `actions` 槽的
    `role="search"` 表单——没有为这一块屏新造共享 prop。框里是草稿，回车在同一个 `setUrl` 里写下
    `{ q, page: 0 }`，URL 是「这个列表在显示什么」的唯一记录，所以刷新、后退、粘贴链接会把词和行一起画
    回来（`PAGE_DEFAULTS` 必须声明 `q: undefined`：`hydrateState` 走的是默认值的键，`{ page: 0 }` 会在
    刷新时把词丢掉）。空态分成两种：还没有调研过公司，和没有公司叫这个名字——后者的出口是清除而不是去调研
    一家公司（49.2 的规矩）。收窄仍然是服务端的，所以翻页器数的是命中数而不是整份目录。6 条页面测试（这块
    屏的第一份屏幕测试）+ 窗口闸门多出第五个用例 + 调用点普查重新对齐。

- **Epic 59 — 报告说得出这是这张卡的第几场**（本段起）
  - 盘点结论（2026-11-05）：报告页只说得出一场的分数，说不出这是第一次还是第四次。同一张卡的
    历史已经在列表里了（57.1），报告只需要把同一句话带过来。
  - **59.1** 报告知道自己在卡片历史里的位置（已完成 2026-11-05）：`cardPractice()`（`lib/interview-practice.ts`）
    按 `startedAt` 从早到晚把同一张卡的演练排开，回位置、总数，以及只从有分数的行里取的最好成绩——
    未评分的兄弟是历史，不是结果。报告用会话自带的卡去问 57.1 的收窄查询，在「打开申请」下面写
    「这张申请的第 2/3 场演练 · 最好 84/100」；第一场说「这是第一场」，只有一场时不重复「1/1」；
    多于一场就链回 `/interviews?application=<id>`。查询多一个 `enabled` 开关，并在发请求前剥掉，
    所以线上的请求仍是 57.1 定义的那一个，没有卡就不发查询。3 条纯函数测试 + 翻译键普查。
  - **59.2** 演练那一行说得出练得怎么样（已完成 2026-11-05）：抽屉一直数得清这张卡练过几场，却不说分。
    材料包多出 `bestRehearsalScore`——一次 join 从这张卡已评分的演练摘要里折出最高分，练过但一场都没结束
    时是 null，计数为零时根本不查。那一行写「3 场演练 · 最好 84/100」；零仍然是「还没有演练」，也不画门。
    3 条服务测试 + 1 条路由断言 + 2 条归一化断言 + 1 条面板测试；types 普查随字段带来的五行重新对齐。
  - **59.3** 演练自己的页面说得出这是第几场（已完成 2026-11-05）：面试器页头带着与报告同一句话——
    「这张申请的第 2/3 场演练 · 暂时最好 84/100」——在回答时就看得到。两个页面共用一个 PracticeLine
    组件、折的是同一个 cardPractice()，所以措辞和「自由练习不画」的底线不会各说各话；文案也随第二个
    页面搬到了 interviews.practice.*。5 条组件测试。
- **Epic 60 — 练过的东西成为知识**（本段起）
  - 盘点结论（2026-11-05）：报告会告诉读者该补什么，但这份建议是整场演练里唯一活不过关标签的东西——
    下一场是重新生成的，而 copilot 引用不了一句只存在于组件里的建议。
  - **60.1** 报告的复习建议可以存成笔记（已完成 2026-11-05）：POST /knowledge/notes 本来就会把保存的
    正文摄取进检索，所以笔记是可引用的证据而不是死行。每个复习项多一个「存为知识库笔记」：
    studyNoteDraft() 把主题、理由和资源折成 NoteRequest——标题按端点上限截到 200 字，一项什么都没说时
    用主题当正文——并打上 interview / study 两个标签，知识页因此找得到。写钩子开始带 tags；笔记普查
    把报告记为写方的第二个页面，读方仍只属于面板。3 条纯函数测试 + 2 条标记测试。
  - **60.2** 留下的笔记记得自己来自哪一场（已完成 2026-11-05）：笔记正文末尾多一行出处——有目标职位时写职位，
    否则写日期——于是几个月后这份建议仍有来路，摄取后的片段也会把这一行带进检索。句子由页面组好（两种情形
    各一个键），`studyNoteDraft()` 负责追加，出处为空时干脆不写那一行。2 条纯函数测试。
- **Epic 61 — 报告说得出更强的回答长什么样**（本段起）
  - 盘点结论（2026-11-05）：`better_answers`、`missing_concepts`、`follow_up_questions_to_prepare` 是报告
    声明过的三个字段，却一个读者都没有——评估器每场都写，页面每场都丢。
  - **61.1** 报告显示它拿到的更强回答（已完成 2026-11-06）：`FINALIZE_FIELDS` 声明 `better_answers` 为
    `[{question, model_answer}]`，mock 也正是这个形状，但 `normalize.ts` 从来没问过它。每条改写现在画在
    「薄弱项」与深度轨迹之间——问题一行小字，回答在下面并保留自己的换行——没有回答的行直接丢弃，不画空卡。
    ai-service 把这一对写成 `BETTER_ANSWER_FIELDS`（与复习卡三个名字同一套「契约即数据」）；字段普查把新的
    `row` 接收者绑到它上面，四处计数与报告的十三个读取点随之上移。2 条归一化测试。
  - **61.2** 报告说得出缺口与要准备的追问（已完成 2026-11-06）：`missing_concepts` 与
    `follow_up_questions_to_prepare` 是报告剩下两个没人读的字段。它们现在并排画在「做得好/薄弱」下面——
    没答到的概念，和值得准备的追问——并计入 `hasContent`。至此这个读取器唯一不读的声明名是 `dims`，
    而它属于维度读取器，所以字段普查的差集收成单名，六处计数随这两次读取上移。1 条归一化测试。
  - **61.3** 更强回答也能存成笔记（已完成 2026-11-06）：复习建议可存、改写不可存，让一场报告里最值得引用的一句话
    反而不可检索。`betterAnswerNoteDraft()` 用问题当标题、回答加 60.2 的出处行当正文，标签是 interview/answer；
    点击本身搬进共享的 `KeepAsNoteButton`（一次请求、进行中状态、拒绝第二份的锁），复习卡与改写卡因此不会各说各话；
    笔记普查把共享按钮记为写方的调用者。2 条纯函数测试 + 1 条标记测试。

- **Epic 62 — 重练从上一场漏掉的地方开始**（本段起）
  - 盘点结论（2026-11-06）：61 教会了报告说出漏掉的概念和该准备的问题，但重练看不到它们——新一场是重新
    生成的，想读回建议只能离开页面去翻旧报告。而这张卡的演练历史本来就在同一份收窄查询里。
  - **62.1** 演练一开场就带着上一场的要点（已完成 2026-11-06）：`previousRehearsal()` 按 `startedAt`
    从新到旧排同一张卡的兄弟（同刻用 id 定序），取最新的、状态是 `completed` 且不是本场的那一场——
    还在跑或已放弃的场次没有报告可学。面试器只为这一场多问一次详情，把报告过同一个
    `normalizeInterviewReport`，所以要点读的就是报告里的漏点和复习项。问题上方的虚线卡写出最大的两个
    漏点和第一条该复习的东西，并链回那份报告；一旦开始评分它就不见了。3 条纯函数测试；窗口普查
    重新对齐钩子的 `enabled` 拆包和第三个调用者，信封普查补上两个新的读方。

  - **62.2** 报告把自己的分数放在上一场旁边读（已完成 2026-11-06）：`scoreDelta()` 只在两场都有分数时
    给出 {previous, current, delta}——未评分的行不是零。报告页总览那一行多一个徽章：「62 → 71（+9）」，
    退步时同一个数字换成警示色，打平时写「与上一场持平」；拿来比的正是 62.1 给面试器写要点时取的那一场，
    两个页面说的是同一场。3 条纯函数测试。
  - **62.3** 要点说得出这份建议有多旧、还要准备什么（已完成 2026-11-06）：没有分数和日期的建议很难信——
    卡片开头先写那一场得了多少分、是哪天（「上一场 62/100」+ 日期），并在漏点和复习项旁边补上第一条
    「该准备的问题」。三者任意一个有内容卡片就出现，所以只有准备问题的报告也能给下一场留下要点。
    文案普查顺手补上 59.3–61.3 新增的四个面试组件（152 → 156）。

- **Epic 63 — 报告点到的东西都能留下**（本段起）
  - 盘点结论（2026-11-06）：到 62 为止，报告的每一类建议都有读方了——该补什么、更强的回答长什么样、漏了什么、
    要准备什么——但只有前两类能存成笔记，后两类仍然跟着标签页一起消失。
  - **63.1** 漏掉的概念可以存成笔记（已完成 2026-11-06）：`gapNoteDraft()` 用漏点本身当标题（漏点通常只有
    一行），底下接 60.2 的出处行；没有出处时仍然把概念本身写成正文，而不是 NoteRequest 拒收的空正文，
    漏点为空时退回页面给的标题。标签是 interview/gap，知识页因此分得清漏点和复习项。`GapNoteButton`
    用的就是其它卡片共用的 `KeepAsNoteButton`。3 条纯函数测试；文案普查 156 → 157。
  - **63.2** 要准备的问题可以存成笔记（已完成 2026-11-06）：`prepareNoteDraft()` 用问题当标题——下一轮之前
    读者真正会去搜的那句话——出处行留在正文，标签 interview/prepare。准备卡里的条目变成和漏点卡、复习卡
    一样的行，右边是同一个保留动作。报告的四种建议因此都落到同一个地方：一条可被 copilot 引用的已摄取笔记。
    2 条纯函数测试；文案普查 157 → 158。

- **Epic 64 — 标签变成读者能用的东西**（本段起）
  - 盘点结论（2026-11-06）：报告的保留动作会写标签（interview/study/answer/gap/prepare），知识页因此分得清
    四种建议，行上也从 60.1 起就画着徽章——但手写的笔记没有办法带上标签，也没有任何界面能按标签去问。
  - **64.1** 读者自己写的笔记也能带标签（已完成 2026-11-06）：新建表单和编辑器共用一个宽容的标签输入：中英文
    逗号和换行都能分隔，大小写折叠（「Interview」和「interview」不会变成两个徽章），重复项合并，最多 8 个、
    每个 32 字符——标签是标签，不是文档。编辑器打开时带着笔记现有的标签，保存时走同一个解析器，所以改错标签
    是编辑而不是重打一遍。`useNoteMutations().update` 现在会转发 `tags`。6 条纯函数测试。
  - **64.2** 笔记列表可以只看一个标签（已完成 2026-11-06）：`GET /knowledge/notes` 多一个可选 `tag`；服务层在有
    标签时走原生 `cast(:tag as text) = any(tags)`（列是 Postgres 的 `text[]`，不是 Hibernate 能用 JPQL 走的
    元素集合），空标签仍然是整份列表。面板把五个产品标签放在 `?ntag=` 旁边，刷新与分享都保留，改筛选时回到
    第一页，筛空时说「没有标签为「…」的笔记」。2 条服务测试；知识页自己的闸门与窗口普查随之重新对齐。

- **Epic 65 — 准备清单能走进一场演练**（本段起）
  - 盘点结论（2026-11-06）：`/growth/interview-prep` 回答「该补什么」和「该练什么」——一份清单的两半——然后
    就停住了。开始一场演练只住在 `/interviews` 和职位页，于是刚被告知练什么的读者得离开那句话，从头把上下文
    再拼一遍。
  - **65.1** 准备清单可以变成一场演练（已完成 2026-11-06）：准备结果底下多一个模式菜单，读的是和其它开局面
    共用的 `INTERVIEW_MODES`。创建时把清单提问时用的职位写成会话的 `positionTitle`——后端 create 记录本来
    就绑了这个字段，而前端钩子的 body 类型没带，所以标题会在上线前被丢掉——然后读者直接落进新的一场。
    自由演练没有可继承的职位，这也是它保留的是职位而不是 job id 的原因。3 条闸门测试。

- **Epic 66 — 一场演练可以被丢掉**（本段起）
  - 盘点结论（2026-11-06）：`DELETE /interview/sessions/{id}` 从第一版库表起就在，却一个调用者都没有。开错的、
    放弃的演练永远留在列表里，想让历史干净只能当作没看见。
  - **66.1** 开错的演练可以删掉（已完成 2026-11-06）：`useDeleteInterviewSession` 花掉了页面从来没花过的这个路由，
    并让 `["interview"]` 下的查询一起失效，所以列表、卡片的演练那一行、报告里的对比会同时更新。行上的垃圾桶
    打开全应用共用的确认框；那句话点名什么会走——问题、回答、报告——以及什么会留下：申请卡片，和从那份报告里
    留下的笔记。删掉最后一页最后一行时，列表本来就有的翻页纠正会把它带回存在的页码。1 条页面测试。

- **Epic 67 — 一场演练能熬过标签页**（本段起）
  - 盘点结论（2026-11-06）：面试器的状态只活在这一次挂载里——本地的 `question` 和 `turns` 由开场 POST 种下，
    之后只在本地变。详情响应其实一直带着整份转录，而页面只读了其中一行。
  - **67.1** 重新打开的演练记得已经说过什么（已完成 2026-11-06）：`answeredTurns()` 把服务端的 turn 折成
    面板要画的一问一答：interviewer 行后面跟一个 candidate 行，末尾那条 interviewer 行不算（那是此刻正在
    问的问题），没有上文的问题的 candidate 行跳过而不是硬配给别人的问题，candidate 行自己的
    `evaluation.score` 有就留着。面试器每次挂载只灌一次，且绝不覆盖这次已经答过的内容，所以重新打开后
    转录面板和问题计数与服务器一致。5 条纯函数测试。

  - **67.2** 一场演练可以不生成报告就结束（已完成 2026-11-06）：`PATCH /interview/sessions/{id}` 同样一个调用者都
    没有。结束并评分是现在就要报告，删除是把转录丢掉，而放弃是中间那条路——回答都留下，报告页之后仍能据此生成
    （finalize 读的是 turn，不是状态），列表不再说它进行中。面试器页头带着这个动作，确认框把这三件事说清，
    `["interview"]` 这个键让列表和页头一起更新。1 条契约用例。

- **Epic 68 — 按钮说到做到**（本段起）
  - 盘点结论（2026-11-06）：走查重练这一圈时发现的：报告的「再练一次」是一个指向报告所属那一场的链接。
    已完成的会话在面试器里只画「已结束——打开报告」，所以这个唯一叫「练」的动作只能带着读者绕圈。
  - **68.1** 再练一次真的开始一场演练（已完成 2026-11-06）：它现在花 `useCreateInterviewSession`：有为卡片演练时带
    报告的 `applicationId`，自由演练时把 `jobTitle` 当作 `positionTitle`，并沿用报告自己的 mode。按钮带着创建
    的进行中状态，成功后落在新那场的 id 上。2 条闸门测试。

- **Epic 69 — 留下的笔记知道去哪里读**（本段起）
  - 盘点结论（2026-11-06）：报告的保留动作说「已存入知识库」，然后把读者留在一块列出全部笔记的页面上。能把列表收窄的
    标签 64.1/64.2 已经有了；缺的是从报告走到刚留下那条笔记的一条路，以及标签行对自己每个标签背后有多少条笔记的说法。
  - **69.1** 留下的笔记带一条回去的路（已完成 2026-11-06）：报告的四类建议每条都带 `interview` 加上自己的
    kind（`study`、`answer`、`gap`、`prepare`），所以 `noteHref` 打开最窄的那一个——kind 标签；`interview` 单独会
    一次打开全部四种。没有 kind 标签的手写笔记指向整块列表，而不是一个匹配不到任何东西的筛选。两个保留按钮都走它。
  - **69.2** 标签行数得出每个标签背后的笔记（已完成 2026-11-06）：`GET /knowledge/notes/tags` 读
    `user_notes.tags`，一个 Postgres `text[]`——JPQL 说不出 `unnest(tags)`，所以这是 `UserNoteRepository` 里
    第二条原生语句（64.2 的 `= any(tags)` 是第一条），每个值都绑参，字面量只有列名和 `text` 类型名。repository
    已按数量倒序，service 只改名不重排；没有标签的读者拿到空列表，而不是一条 0。前端 `useKnowledgeNoteTagCounts`
    读 `{data:[...]}` 信封；`tagRow` 把产品自造的五种放前、读者自己的按常用度往后排（最多 7 个）；
    `tagIsInert` 让计数为 0 的标签可见但按不动——正在生效的那个除外，否则删掉最后一条就会把自己锁在筛选里。
    中英文各加 `knowledge.notes.tagEmpty`。`NoteTagFilterTest` 4 条、`lib/note-tags.test.ts` 14 条、
    `lib/hooks/note-tags.test.ts` 5 条。安全普查从六类原生查询改到七类，`SECURITY.md` 点名
    `UserNoteRepository` 与理由；response-shape 的钉子 205 -> 206；窗口排序门学会原生 SQL 允许小写 `order by`。
    后端非 IT 套件 1200 绿；ai-service 2032 通过、2 跳过；前端 1156 通过、116 个文件。

- **Epic 70 — 看板答得出一个词**（本段起）
  - 盘点结论（2026-11-06）：Epic 58 只修了本来就有搜索框的那一块看板，剩下的看板是没有问题可问的——
    投递管道、联系人、演练列表。管道先做，因为它是读者一天里看得最多的看板，而且它的路由本来就在按
    `status` 和 `jobId` 筛，所以它的关键词不能再按老形状多开一条分支。
  - **70.1** `GET /applications` 按字符答一个词（已完成 2026-11-06）：四条只差筛选条件的派生方法合成一条
    `BOARD_WHERE`——`(:status = '' OR ...)` 与 `(:jobId IS NULL OR ...)`，空值是「不筛」而不是「筛空列」；
    词用 `LOCATE(:needle, LOWER(col)) > 0` 查卡片自己的三列（title、company、notes，后两列 `COALESCE`，
    没有备注的卡片也还是一张卡片）。留两条读法对应两个问题：整块看板按更新时间倒序，一列按读者自己排的
    `position`。service 每请求 trim 加小写一次，controller 绑 `?q=`。`ApplicationRepository` 是 needle 名单
    里的第五个。新增 2 条、改写 3 条 service 用例，`ApplicationNeedleIT` 3 条走真的 Postgres：字面 `%`、
    字面 `_`、打错的 `Under_S_ore` 必须什么都找不到、框能读到公司与备注而 `status` 仍在收窄、空格框等于
    整块看板。endpoints census 从 54 条绑参改到 55，API.md 那一行列出这个框。顺带修掉
    `ApiDocParamContractTest` 从 64.2 就带着的误读：`interview`/`study`/`answer` 之间的斜杠被当成一条路径
    `/`，现在一段必须带上字符，同一行里两条真路径改成断言仍然读得到。
  - **70.2** 管道看板问出自己的问题（已完成 2026-11-06）：搜索框放在表头、和「添加」并排，两个动词都还在。
    词走 `?q=` 交给服务端筛，而不是只过滤手里这一页——这样分页器数的是匹配数：141 条匹配、每页 100 条就是
    这个词的两页，旁边的数字来自服务端的 total。`q` 同时写进 `PAGE_DEFAULTS` 和 `useUrlState` 的类型字面量，
    因为水合是照着 defaults 的键走的：defaults 里漏一个键，贴进来的链接就恢复不了它；只带 `application` 的
    链接不管有没有词都照样打开那张卡。草稿框和已提交的话分开存，理由和看板与公司页不同：卡片是要拖的东西，
    半个词就重新请求会把手下正在写的那一页换掉。两种空态各有各的出路（49.2）：没开始的流水线指向建卡表单，
    满是你输入的这个词没有的卡就指向那个框。新增 5 个 key × 2 语言；`applications/page.test.tsx` 是这块屏的
    第一个屏幕测试（6 条，走真的 locale provider、真的 kanban、真的分页器）。两道门跟着改：`WIRE`/`SITES`
    的 `useApplications` 行现在带上 `q`，被这个文件和 `test_applications_deep_link_reaches_any_page.py` 同时
    钉住的 `useUrlState` 字面量加上第三个键。endpoints census 不动——`q` 从 70.1 起就是绑好的参数，这一条只是
    给它配上读者。
  - **70.3** 联系人看板也答一个词（已完成 2026-11-06）：Epic 70 盘的最后一块板，也是唯一一块路由只答裸数组、不分窗的板——
    改变的是「加搜索」的含义，而不是它的拼法。后端：`ContactRepository` 有自己的 `BOARD_WHERE` 和一条
    `findBoard(userId, needle)`，用 `LOCATE(:needle, LOWER(col)) > 0` 读联系人全部的六列——姓名，加上五个可空列
    `COALESCE` 成空串，因为没有邮箱的人照样是读者要找的人；`ORDER BY c.updatedAt DESC, c.id ASC` 保住名单自己的顺序并钉住
    并列。派生的 `findByUserIdOrderByUpdatedAtDesc` 留着：导出包（40.3）要读整份名单，换成带 needle 的读法会从用户自己的备份
    里悄悄丢人。service 每请求 trim 一次、小写一次，controller 绑 `?q=`；`ContactRepository` 是 `SearchNeedleContractTest`
    roster 里的第六个名字，旁边新增一道判形状的用例（六个 `LOCATE` 和 `:needle = ''` 都在，任何 `Containing` 都不许出现）。
    `ContactNeedleIT` 3 条跑在真 Postgres 上：字面的 `%`、字面的 `_`、打错的 `Under_S_ore` 必须谁都找不到、只有一个百分号的
    框只答一个人；词伸进 role、公司、关系、邮箱、备注，而六列里什么都没有的那个人不在答案里；空框、纯空格、大写锁。前端：
    `useContacts(params?: { q?: string })` 把词同时放进请求和 `queryKey`——两个词共用一个键就共用一份缓存，改词就什么也不
    刷新；名单的三个写操作仍然 invalidate `["contacts"]`，react-query 按前缀匹配。裸数组意味着 total 数的就是匹配数，所以空态
    可以怪那个词，而不是怪读者。`/networking` 加上 `useUrlState<{ q?: string }>`（键写进 `PAGE_DEFAULTS`）、草稿与提交分离
    （半个词逐字符请求、每个字符存一份缓存）、`role="search"` 的框和「添加」并排、两种空态各有各的出路（49.2）。新增 5 个
    key × 2 语言；`networking/page.test.tsx` 是这块屏的第一个屏幕测试（6 条：参数对象、从地址恢复的框、两种空态在两种语言里
    各是哪句、框挤不掉一行自己的「起草」、名字并不拼这个词的行照样显示——看板展示服务端答的内容，而不是再筛一遍）。只有一道门
    跟着改：endpoints census 把绑定参数从 55 钉到 56，并把 `GET /contacts q` 加进抽查——这是上一半提交欠下的账。窗口 census
    不动：名单不分页，`useContacts` 保持 `List<ContactItem>` 那一行，调用点既不进 `WIRE` 也不进 `SITES`。给名单加分页是另一个
    问题，这一条刻意没有顺手做。

  - **70.4** 演练列表也答一个词（已完成 2026-11-08）：Epic 70 点的第三块板，这是后端那一半。
    原来是两个派生方法，只差「有没有卡片 id」——整段历史，和某张卡的演练（57.1）——再加一个词就会变成四个。
    现在一个 `BOARD_WHERE` 同时装下 `(:applicationId IS NULL OR s.applicationId = :applicationId)` 与
    `(:needle = '' OR ...)`，词用 `LOCATE(:needle, LOWER(col)) > 0` 问会话自己的三列文字：公司、职位、模式。
    前两列 `COALESCE` 成空串，因为它们是构造上就可能没有的：自由演练不记公司，从职位起的演练可能不记自己的
    职位标题；`ORDER BY s.startedAt DESC, s.id ASC` 保住看板自己的顺序，也把并列钉住——否则同一瞬间开始的
    两场演练，每次请求都可能落在分页线的不同侧。搜索故意不 join 问答表：一场演练在这块板上是一行，接进它的
    题目会把同一行按题目数答好几遍。service 每请求 trim + 小写一次，controller 在已有的 `applicationId`
    旁边绑 `?q=`，`InterviewSessionRepository` 成为 `SearchNeedleContractTest` roster 的第七个名字，
    旁边一条形状门：三处 `LOCATE`、两个 scope、全序都在，两个派生方法名一个都不许再声明。单测新增 3 条
    （词 trim 小写后到达、全是空格等于没输入、词和卡片 id 收窄同一次读），controller 新增 1 条并改靶 1 条。
    `InterviewNeedleIT` 5 条跑在真 Postgres 上：字面 `%`、字面 `_`、打错的 `Under_S_ore` 必须谁都找不到、
    只填一个百分号的框只答那一场而不是整段历史；词走到公司、职位、模式，而什么都不带的那场留在外面，两列文字
    都空的会话仍能靠它有的 mode 被找到；空框与全空格框；卡片 id 和词收窄同一次读，陌生人猜的卡片 id 答
    total 0；五个匹配分成三个不相交窗口——Spring 从那一条 `@Query` 派生的 count 查询在这里被证明重复了
    同一个 needle 子句，而不是数整段历史。API.md 的 `/interview/sessions` 行写上这个框
    （`ApiDocParamContractTest` 正是先因为这条缺失而红），endpoints census 从 58 重新钉到 59
    （`q` 这个名字集合里早就有，动的是答它的路线）。70.5 给这条路线配上读者。
  - **70.5** 演练看板问出自己的问题（待做）：同一套 URL 状态与草稿框纪律走 `/interviews` 和
    `useInterviewSessions`，词进 `queryKey`，两种空态各有各的出路。
- **Epic 71 — 审计先学会不撒谎**（本段起）
  - 盘点结论（2026-11-07）：71.1 的浏览器界面闸门把 181 条公开路由里的 20 条记为「无界面」，其中两条是
    `PATCH`/`DELETE /applications/{}/letters/{}`，理由写着「没有编辑界面」。实测
    `application-letters.tsx` 的 `LetterEditor` 与删除确认框、`actions.ts` 的
    `useUpdateApplicationLetter`/`useDeleteApplicationLetter` 早已随 50.2/50.4 上线，API.md 也把两个动词的
    契约写全了。根因在闸门自己：`_endpoint_keys()` 认得单行箭头，认不得 `endpoints.ts` 里唯一那条
    **模板写在下一行的双参数箭头** `applicationLetter`；key 一丢，两条本来有读者的路由就成了「无 key」，
    台账给它们补了理由，而原来的反向断言只查「理由是否还对应后端存在的路由」，不查「这条理由说的路由
    是不是真没有读者」——于是谎言一路绿灯，71.3 差点照着去重造一个已经存在的界面。
  - **71.1 修正（已完成 2026-11-07）**：解析器补上多行双参数箭头；`_walk()` 返回实测的 `readerless`
    集合，台账改为**双向**判等（无读者的路由必须有理由，有理由的路由必须真的没有读者）；删掉两条假理由，
    第三个用例把 `applicationLetter` 的 key、形状与调用者一起钉住。精确数字：181 条公开路由、
    165 条有读者、16 条无读者、0 孤儿。**变异探针**：把解析分支改成 `None` → 3 个用例全红；
    把假理由写回台账 → 恰好 1 个红（新增的双向断言）。文件已按字节恢复。
  - **71.3 的队列收敛（2026-11-07）**：实测只剩一个真缺口——`GET /jds/{}` 按 id 读已存的 JD，
    而浏览器只花 `POST /jds`（粘贴分析）和 `GET /jds/suggestions`，`endpoints.ts` 里没有任何 key
    指向这条存储读取。封面信两个动词出队，理由是它们的界面本来就在。
  - 复用结论：**解析器丢一个 key，不是「漏数一条路由」，是「凭空造出一个需求」**——而台账会替这个
    假缺口补上一段看起来很合理的理由。凡是「理由台账」型闸门，必须双向判等，并且至少有一个用例
    直接钉住解析器最容易丢的那种写法；只查「理由是否还指着存在的东西」，等于允许它指着任何东西撒谎。
  - **71.3 收口（2026-11-07，以接线而非删端点）**：分析对话框保存 `POST /jds` 返回的 id，重开时经
    `useStoredJd`（`endpoints.jd`）把存储行读回——误关对话框不再让读者为服务端早已持有的文本再付一次
    分析；行不在了（别的会话、库重置）就落回粘贴态且不重试。台账按规则移动：181 条公开路由、
    166 条有读者、15 条无读者、0 孤儿。验证链：审计闸门双向判等证明读者真实存在；journey 新站断言
    存储读回答的正是已分析的那一行；浏览器实测重开出现「已从上次的分析恢复」且无第二次 POST。
  - 复用结论（补）：**缺口清单上每一条都要先答「这个读在等谁」，再决定删还是补。**`GET /jds/{}`
    在等的是「把已花钱的分析拿回来」这个动作，而对话框随手丢掉的返回 id 恰好就是它的钥匙——清单把它
    记成「无界面的路由」，差点让它以「删除冗余端点」的名义消失。

- **Epic 72 — 名单答得出第几页**（本段起）
  - 盘点结论（2026-11-07）：ROADMAP 的 `[ ]` 全关之后，70.3 记下的「给名单加分页是另一个问题」
    是唯一写明的产品债；信封读者普查门也直说 `useContacts` 的信封是客户端伪造的
    （`total = items.length`）。改它，等于让普查门从「记录一个假信封」变成「记录真窗口」。
  - **72.1 / 72.2（已完成 2026-11-07）**：后端 `findBoard` 收 `Pageable`，`countQuery` 复用同一段
    `BOARD_WHERE`，`total` 数的是匹配数；controller 走 `Paging.of`（50/100）；导出包仍读不筛的
    整份名单。前端 `useContacts` 换 `normalizePage`，`/networking` 加 URL 页码、换词回第一页、
    `lastPageOf` 纠正越界、真分页器。真 Postgres IT 验三页不重不漏与夹紧；屏幕测试验
    「1–50 of 120」。四道普查门随人口移动（11 真信封 / 13 pager / 第 14 个 hook / 58 个绑参），
    另补上同伴 71.3 新 E2E case 欠下的 65→66 计数。
  - 复用结论：**「先改产品，再让红门点名」比提前读普查门省事**；但文档里的反引号是契约，
    响应字段写成反引号会被参数门当成调用方要传的参数。并发会话正在改 i18n 文件时，
    pager label 复用页面自己的标题就能不碰它。

- **Epic 73 — 跨栈契约重新测量**（已完成 2026-11-08，以验证收口）
  - 两道跨平面闸门重新实跑：`test_browser_surface_audit.py` 3/3 绿（181 条公开路由、166 条有读者、
    15 条无读者各带理由、0 孤儿）；`test_the_clients_addresses_have_contract_rows.py` 2/2 绿
    （客户端能建的每个地址在 API.md 都有行；两条 walk 是下限而非钉死的 key 计数）。
  - 无缺口需要接线——71.3 的 `GET /jds/{}` 存储行读取器是唯一真缺口，已关。本段同时修复了
    同轮较早提交把 `plan_long_term.md` 截成一行状态的问题：全文从 b94aa56 还原后再追加本段。
  - 复用结论：**审计结论有保质期，必须重跑而不是沿用旧数字**；审计闸门通过所以本段以验证收口。
    顺手修正了 ROADMAP 里 Epic 73 条目被插入两次（一次夹在 Epic 32/33 之间、一次压在 Epic 72 之前）的问题，
    只留一份，放在 Epic 72 之后并标记关闭；给台账加了闸门 `tests/test_the_roadmap_names_each_epic_once.py`
    （每个 `## Epic N` 只能出现一次，双插入或丢前缀都会红），两个变异探针实测变红。

## 开发协议
（每个任务）

- 先跑相关测试，再改；改完跑三套件相关子集；提交前 `tsc` + lint。
- 实现 + 测试 + 真实 API/UI 接线（无 placeholder 端点）+ 文档/census 同步。
- 每个可交付单元立即 commit + push（遵循仓库现有提交风格）。
- Docker 依赖的 `*IT`、RAG eval、E2E 不在本机假装通过；记录为"需真实栈"。
- 新 AI 结论必须可追溯到证据；offline provider 在 `APP_ENV=prod` 一律拒绝。

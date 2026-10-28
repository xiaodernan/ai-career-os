# 长期开发计划 (Long-Term Development Plan)

## 终极目标

一个真正可运行、可交付的个人求职操作系统 (AI Career OS)：简历 → 知识库 →
岗位发现 → JD 情报 → 证据约束匹配 → 定制材料 → 模拟面试 → 申请管理 → 成长与
薪酬 → 数据可携带，全部闭环；并且从"问了才答"进化为"替你先做"——定时摄取、
主动提醒、通知中心、每周摘要、语音面试、移动端与生产级交付。

## 当前状态 (2026-10-28)

- **前端**: 724 个 vitest 通过（66 个文件）；`tsc --noEmit` 干净。
- **后端**: 617 个测试通过 (`mvn test`，含无需 Docker 的 MockMvc 切片)。
- **ai-service**: 1833 passed, 1 skipped (offline: mock/hash)。
- **E2E**: 24/24 golden journey（最近一次真实栈验证）。
- **分支**: main 与 origin 同步。
- **已完成**: Epic 0–18 全部勾选；13.2 的不变行跳过、导出序列化统一、
  i18n 表按段落重组并删除死代码；19.1 保存的搜索（后端 CRUD + `/jobs`
  侧栏面板）；19.2 定时摄取（`/ingestion` feeds/runs、03:20 调度、
  抓取安全边界、导入页订阅面板）；19.3 通知中心（无通知表，按来源实时合成，
  按 episode 存已读/忽略，四路由 + `/notifications` 页）。

## 主线队列（按顺序执行）

1. **13.1 收尾 — Markdown 导出面**
   `export_render.to_markdown` 已经写好且完整，但没有任何路由/按钮调用它。
   给 render 路由加 `format: "markdown"`，打通 backend 桥、`/data` 页面按钮、
   两种语言、路由级测试与 `API.md` / `EXPORT.md` 文档。

2. **13.2 收尾 — 恢复的删除语义**
   `currentState` 只覆盖 profile / applications / growth_plans / notes / contacts；
   resumes、knowledge、job_descriptions、interviews、memories 不在其中，所以
   这些 section 的"包内已无此行"永远无法计划成 delete。扩展 current state
   到全 section（并处理重新摄取 section 的 id 重映射），或者把 restore 明确
   记录为 upsert 并用测试钉住这个承诺。

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
   已完成（19.5，见上）。下一步：19.6 语音模拟面试。

6. **Epic 21 — 语音模拟面试**
   STT/TTS 的 provider 接缝 + 面试页的录音/播放；文本面试已有的评分与轨迹
   不重写，只把输入输出换成声音。

7. **Epic 22 — 移动端 / PWA**
   可安装外壳、离线壳、响应式审计（侧栏、看板拖拽、表格滚动）。

8. **Epic 23 — 真实板卡连接器**
   Greenhouse / Lever 公开 board API 接入既有 `Connector` 协议；
   RSS/JSON 粘贴路径保持为离线后备。

9. **Epic 24 — 交付硬化**
   夜间备份 + 恢复演练、指标与告警、运行手册更新；把 nightly 的
   eval/IT 结果变成可查的历史而不是日志。

## 开发协议（每个任务）

- 先跑相关测试，再改；改完跑三套件相关子集；提交前 `tsc` + lint。
- 实现 + 测试 + 真实 API/UI 接线（无 placeholder 端点）+ 文档/census 同步。
- 每个可交付单元立即 commit + push（遵循仓库现有提交风格）。
- Docker 依赖的 `*IT`、RAG eval、E2E 不在本机假装通过；记录为"需真实栈"。
- 新 AI 结论必须可追溯到证据；offline provider 在 `APP_ENV=prod` 一律拒绝。

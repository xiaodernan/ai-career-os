# 长期开发计划 (Long-Term Development Plan)

## 终极目标

一个真正可运行、可交付的个人求职操作系统 (AI Career OS)：简历 → 知识库 →
岗位发现 → JD 情报 → 证据约束匹配 → 定制材料 → 模拟面试 → 申请管理 → 成长与
薪酬 → 数据可携带，全部闭环；并且从"问了才答"进化为"替你先做"——定时摄取、
主动提醒、通知中心、每周摘要、语音面试、移动端与生产级交付。

## 当前状态 (2026-10-28)

- **前端**: 682 个 vitest 通过；`tsc --noEmit` 干净。
- **后端**: 468 个单元测试通过 (`mvn test -Dtest='*Test'`)；`*IT` 需 Docker。
- **ai-service**: 1833 passed, 1 skipped (offline: mock/hash)。
- **E2E**: 24/24 golden journey（最近一次真实栈验证）。
- **分支**: main 与 origin 同步；最近提交 `993c792`
  (`fix(portability): a re-import of unchanged rows writes nothing`)。
- **已完成**: Epic 0–18 全部勾选；13.2 的不变行跳过、导出序列化统一、
  i18n 表按段落重组并删除死代码。

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

3. **17.1b 收尾 — 41 条文案 census**
   `node scripts/regen-known.mjs` 报 41 条 / 7 文件。`/growth`、`/offers` 的
   placeholder 仍是中文页面上的英文（`e.g. Senior Backend Engineer (Java)`）。
   逐文件迁到 `translations.ts` 双语键，把 `KNOWN` 缩到 0 或只剩有理由的条目。

4. **Epic 19 — Proactive Career OS**
   19.1 保存的搜索与提醒规则 → 19.2 定时摄取（复用 plan-ingest）→
   19.3 通知中心 → 19.4 每周摘要投递。这是"OS 替你先做"的第一层。

5. **Epic 20 — 单版本打印**
   定制简历的独立打印视图（复用 export_render 的排版与语言机制），
   让"tailor → 下载 PDF"成为一条完整路径，而不是只打整个数据包。

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

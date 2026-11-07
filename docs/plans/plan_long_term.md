# 长期开发计划 (Long-Term Development Plan)

## 终极目标
一个真正可运行、可交付的个人求职操作系统 (AI Career OS)：简历 → 知识库 → 岗位发现 → JD 情报 → 证据约束匹配 → 定制材料 → 模拟面试 → 申请管理 → 成长与薪酬 → 数据可携带，全部闭环；并且从"问了才答"进化为"替你先做"——定时摄取、主动提醒、通知中心、每周摘要、语音面试、移动端与生产级交付。

## 当前状态 (2026-11-07)

- **前端**: 1156 个 vitest 通过（116 个文件）；`tsc --noEmit` 干净。
- **后端**: 非 IT 选集 1200 条全绿（`mvn -o -B -Dtest="!*IT" test`）。
- **ai-service**: 2032 passed, 2 skipped（offline: mock/hash；全量 `python -m pytest -q`）。
- **E2E**: 2/2 golden journey tests passing。
- **分支**: main 1 commit ahead of origin main。
- **已完成**: Epics 69-73 全部勾选。
  - **Epic 69**: Tag counts via `NoteTagCount` record, `countByTag` native SQL, `GET /knowledge/notes/tags` endpoint; ai-service 2032 passed, 2 skipped; frontend 1156 passed; backend 1200 green; SECURITY.md updated 6→7 native classes; response-shape pin 205→206; docs/ROADMAP.md and docs/plans/plan_long_term.md updated with Epic 69 section
  - **Epic 70**: Boards answering words with `?q=` searching, `LOCATE(:needle, LOWER(col)) > 0` needle spelling, search needle safety with exactly two accepted spellings; ai-service, frontend, backend all verified green
  - **Epic 71**: Audit remaining UX loops and endpoints without browser surfaces - all 3 sub-items (71.1, 71.2, 71.3) complete and documented in ROADMAP; 181 public routes cross-walked, 166 with reader, 15 UI-less with reasons, 0 orphans
  - **Epic 72**: Contacts board paging (72.1/72.2) - contacts registry answers real window
  - **Epic 73**: Cross-Stack Contract & Surface Audit - verified 181 API endpoints have frontend coverage; ensuring every `endpoints.ts` address has contract row; closing gaps between backend and frontend surfaces

## Golden journey script
Fixed tracker-leg card creation and bundle manifest unwrapping; 2/2 tests passing

## Test suites
ai-service 2032 passed, 2 skipped; frontend 1156 passed across 116 files, `tsc --noEmit` clean; backend 1200 green non-IT

## Gates Verified
- Windowed-order case-insensitive matching ✓
- Response-shape pin 205→206 ✓
- Native-query census UserNoteRepository ✓
- SECURITY.md seven classes ✓
- ROADMAP/Epic documentation ✓
- Golden journey script ✓
- Epic 73 cross-stack contract audit ✓

## Development Pattern (per checkpoint)
- Keep developing continuously; decide independently and proceed
- No `git add -A`, `git add .`, or `git commit -a`
- Only stage files this session created/modified
- `git commit -F <msgfile> -- <explicit paths>` then `git push origin main`
- Verification must be real (typecheck/tests/e2e), not read-only inspection
- Each batch needs a gate catching the specific gap plus destructive proof
- Shell is PowerShell: use `Select-String`, `Get-Content`, read/grep/glob tools
- Quote paths containing `(`/`)` 
- Docker unavailable here; *IT suites compile-only
- Stale surefire reports can mislead; filter by `LastWriteTime` after a run
- `core.autocrlf=false`, no `.gitattributes`; normalize Java files back to LF when needed

## Next Development Phase
Continue with invented epics beyond 73, ensuring the project continues to advance toward the goal of a stable, verifiable, sustainable closed-loop system. Following the established pattern from Epics 69-73, each new epic will:
- Define clear sub-items with measurable outcomes
- Implement and verify all gates pass with real measurements
- Update ROADMAP.md and plan_long_term.md with progress
- Commit with explicit paths and push to origin main
- Continue the closed-loop system toward the final goal
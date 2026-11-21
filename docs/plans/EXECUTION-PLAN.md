# Execution plan — the standing ledger of what was asked, and where it landed

The user repeated the same master prompt many times, by design. This file is the
anti-loss mechanism: every distinct demand in it, mapped to the epic, commit,
test or document that answers it — or the reason it is not (yet) answered.
"Done" here means *measured*, "named" means *deferred with a written reason*.
If a claim here drifts, the gates — not this file — are the source of truth.

## How to read the rows

`DONE` shipped and gated · `MEASURED` measured with the numbers in the doc ·
`PARTIAL` shipped in part, with the rest named · `NAMED` deliberately deferred,
the reason written · `USER STEP` blocked on the operator's own one-time action ·
`BLOCKED` environmental, never fabricated.

## The ledger

| # | The ask | Status | Evidence |
|---|---|---|---|
| 1 | 继续长期开发，不要停下 | DONE (process) | this file + the ROADMAP chain; every epic ends with gates and CI green |
| 2 | 检查项目现在的状态 | DONE (process) | per-commit `verify_gates`, vitest, offline pytest, budget, census, showcase; live `curl` probes |
| 3 | 把这些需求列成计划，按计划持续执行 | DONE | this document — the ledger itself |
| 4 | 多 worktree / 分支合并到 main | DONE | WORKTREE_CONSOLIDATION.md; this session re-verified: 1 worktree, `main` only, `origin/main` only, `git worktree prune` clean |
| 5 | 接手别人没做完、锁住的内容，直接帮他做完 | DONE (audited) | manifest.json reviewed; the 4 untracked tests are all in `main`; HEAD-ancestors property re-checked; nothing unique remained to absorb |
| 6 | Spring Cloud 微服务元素 | PARTIAL | gateway + discovery + config-server exist, contract gates in CI, Resilience4j circuit-breaker metrics, gateway rate-limit filter (115), SPRING_PROFILES_ACTIVE=eureka wiring; py-level `spring-cloud-readiness` doc; more layers land per epic |
| 7 | Redis 合理运用 | DONE | sliding-window limiter, health probe, dashboard read-through (125), Redis Streams jitter queue (162), admin counter cache (253), Epic 256 siege comparison |
| 8 | 计网知识：SSE、CORS、correlation、ICS、webhook、rate limit、circuit breaker | DONE | `SseRelayService`, `EnvelopeAdvice`, `ForwardedAddressIT`, calendar ICS token, `/inbound/mail` HMAC webhook, gateway token bucket, Resilience4j |
| 9 | 算法/数据结构/操作系统/硬件适配 | DONE (iterating) | ai-service `app/algorithms` (LRU/TTL caches, top-k heap, sparse vectors, BM25), dense-fill epics 184/251, index tuning V7/V39/V40, hot paths read with `EXPLAIN`-informed indexes |
| 10 | 前端美观登峰造极 | PARTIAL | design system (oklch tokens), 248 typography audit, hint system (245/247), 255 wheel; full visual guarantee needs a browser — see row 34 |
| 11 | 修复字体变形/歪曲/重叠/挤压 | PARTIAL | 248 typography pass fixed the measurable cases (text-balance, clamp); a full render-sweep awaits the browser |
| 12 | 前后端协同发展 | DONE (rhythm) | each epic ships both halves (250/251/252/254 admin + UI; 252 projection server+client; 253 cache + wire) |
| 13 | 数据库性能 | DONE (iterating) | V1–V40 migrations; pgvector; V7/V39/V40 indexes; dashboard read model; `COUNT(*)`-over-index shape measured in the siege |
| 14 | 各种缓存合理运用 | DONE | 125 dashboard, 253 admin (off default, fail-open, ±10% jitter), client-side exact-cache warm-up named; `cached_tokens` recorded as reported, never invented |
| 15 | 消息队列合理运用 | DONE (built, disabled default) | Redis Streams job queue (162), DLQ, jitter retries; OFF by default — enablement is a real decision with real money; documented |
| 16 | RAG / langchain / langgraph | DONE (deliberate) | home-grown orchestrator + subagents + 26 tools + hybrid retrieve/rerank/compress (AGENTS.md); no framework, on purpose; documented rationale |
| 17 | 接入真实大模型测试 | DONE (used continuously) | live probes and evidence: docs/CACHE-RELAY.md |
| 18 | 缓存命中率/非流显示异常 | DONE (diagnosed + measured) | 9 identical calls today: hit rate 95.6% when reported; field appears at random on both stream and non-stream; relay's meter varies (857 / 5220 / 19300) — no client fix exists; evidence in docs/CACHE-RELAY.md |
| 19 | 压力测试/高并发/容灾 | MEASURED | Epic 256: k6 siege at 10/100/200 VUs, zero 5xx at every level, saturation-not-failure at 200; cache-on vs cache-off comparison; docs/LOADTEST.md |
| 20 | 联网搜索真实数据 | BLOCKED (host relay 402) | never invented; the install's own numbers are measured and pinned; documented in the relay memo |
| 21 | 真实实验数据而非演示堆砌 | DONE | admin counts live; heatmap dense-fill real; seeded corpus flagged as demo vs. real feed design (Epic 248 recommendation) |
| 22 | 管理员功能密码 123、监控统计、趋势预测、下一步优化措施 | DONE | 250 door + 251 trends + 252 projection + 253 cache + 254 rivers; recommendations pinned to measured figures |
| 23 | 简明说明书/小册子嵌入项目，不是文档 | DONE | `/playbook` + keepsake manual + epilogue (Epic 249); ten-minute start; the printed manual is one button away |
| 24 | 游戏/新手教程/快速上手 | DONE | `/tour` (Epic 244), ten-minute start card, first-week game embedded with how-to-play, nine-quest dashboard |
| 25 | 全内容中英文切换、无夹杂、英文也翻中文 | DONE (gated) | census + used-keys + copy-parity gates; the EN table holds no Chinese string (caught and fixed this session) |
| 26 | 主界面各种按键附带教学说明 | PARTIAL | hint system on chrome + main surfaces (245/247); full rollout named as the next UI epic |
| 27 | 无尽开放世界感 + 防迷路引导 | PARTIAL | `/tour`, ⌘K palette, quest map, ten-minute start, eleven doors; the "continent" metaphor keeps growing per epic |
| 28 | 鼠标引擎反了，修复 | DONE | Epic 255 — forced standard dialect ("往下滑就往下看"), migration from Epic 225's storage, settings switch rewritten EN+ZH |
| 29 | 新章节/新模块/新玩法/新内容 | DONE (ongoing) | Epics 249–256 this arc; the ROADMAP is the till |
| 30 | 项目体量大、细节密集 | DONE (ongoing) | 122 epics, 408 work items, 180 test files, per the regenerate-on-push showcase |
| 31 | RSS 之类大模型缓存效率 | MEASURED | see row 18; prefix discipline already in every LLM call |
| 32 | 个人展示页 https://xiaodernan.github.io/ 同步 | DONE | showcase.html auto-regenerates on every push; the portfolio card (project 06, Monday 13:30 UTC sync) was added after push access; `sync-career-os.yml` watches `main` and pushes `latest.json` weekly — the site load fetches it straight from raw.githubusercontent with `assets/career-os/latest.json` as the cached fallback. 433 crons run every week against the public URL and only the fallback moves; real routes are linked from the card |
| 33 | 优化措施 / unclogging 前端 | DONE (2026-11-22) | Epic 358 paid the shared-table debt: every route shed ~152 kB gzip (knowledge 374.1 → 222.2) and the budget was TIGHTENED 366 → 230 rather than raised; rows 10–11 still await a browser |
| 34 | 前端渲染验证/视觉巡检 | PARTIAL | SSR byte-audits and component tests only; in-app browser has not reached `:3000`/`:8080` from this host |
| 35 | 每次只动手做、不问 | DONE (process) | the plan drives; blockers are noted, never waited on |
| 36 | 外围需求全部执行 | DONE/PARTIAL as above | nothing silently dropped — this ledger is the accounting |

## Standing next (the honest queue)

1. ~~**The per-locale translations split**~~ — DONE (Epic 358, 2026-11-22). It was
   not a routing-level change after all: the table crosses into the RSC payload with the
   HTML, and the spare language is a chunk warmed on hover. -152 kB gzip per route.
2. **Hint coverage of every primary control** — roll `components/ui/hint.tsx`
   through dashboard/jobs/admin/kanban systematically.
3. **Render verification on a roomier host** — the visual sweep this ledger's
   row 34 cannot honestly complete here.
4. **The next chapter** — the product keeps contradicting "finished"; the
   ROADMAP defines the next epic when this one ships.

## What never happens here

- No external number is fabricated; the 402 wall stays a wall.
- No secret is committed; the relay key lives in the daemon's env, not the tree.
- No gate is relaxed to fit an implementation; the implementation fits the gate.

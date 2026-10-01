# Evaluation

How AI Career OS measures its own AI (PRD §32, §34). There are two harnesses,
both living in `ai-service/app/eval/` and both writing JSON + Markdown reports to
`ai-service/evals/reports/` (`evals/reports/` is gitignored — reports are run
artifacts, not source).

A shared design rule: **offline runs are allowed to score badly, and that is the
point.** With `LLM_PROVIDER=mock` / `EMBEDDING_PROVIDER=hash` the harness must
still run end-to-end and produce discriminating numbers. If a low-quality
configuration scored well, the benchmark would be measuring nothing.

## 1. RAG evaluation — retrieval + generation

Runner: `python -m app.eval.run_eval --user-id <uuid> [--answer] [--tags ...]`

Golden set: `app/eval/dataset.py::GOLDEN_SET` (15 bilingual cases tuned to the
seeded dev corpus that `scripts/smoke-fullstack.sh` writes). Ground truth is
keyword-based — every chunk of the user whose text contains a case keyword counts
as relevant. It is deliberately weak but honest supervision; override it for a
real corpus with `--dataset cases.jsonl` (one JSON object per line, same fields as
`EvalCase`).

A case whose keywords the corpus does not contain would have *no* relevant chunk,
and `recall_at_k` returns 1.0 when there is nothing to find — a query with no
ground truth scoring full marks is the one number that must never reach an
aggregate. The runner therefore skips such cases before scoring and lists them
under `skipped` with the reason `no_ground_truth`, so the report says "this corpus
cannot answer gs-01" instead of quietly banking a 1.0.

| Metric | Meaning |
|---|---|
| `recall_at_k` | share of relevant chunks inside the top `k` |
| `precision_at_k` | share of the top `k` that is relevant |
| `mrr` | reciprocal rank of the first relevant hit |
| `ndcg_at_k` | rank-weighted gains (position matters) |
| `hit_at_k` | did *any* relevant chunk make the cut |
| `context_relevance` | retrieved context vs. the query |
| `answer_relevance` | answer vs. the query |
| `faithfulness` | answer claims supported by the retrieved context |

`faithfulness` and the two relevance scores use `metrics.llm_judge()` when a real
provider is configured, and fall back to a lexical judge otherwise — every row
records which judge produced it (`judge` field), so a lexical number is never
mistaken for an LLM-judged one.

The report also carries latency (`avg_retrieval_ms`), token totals, and the full
effective config (chunk size, top-k, rerank mode, provider, model), which is what
makes A/B experiments comparable:

```bash
# experiment A — baseline
python -m app.eval.run_eval --user-id $U --experiment baseline --answer
# experiment B — reranker off
python -m app.eval.run_eval --user-id $U --experiment no-rerank --rerank none --answer
```

Comparing the two generated files answers "did the reranker earn its latency?".

### RAG baseline (recorded result)

On the seeded dev corpus, with `LLM_PROVIDER=mock` / `EMBEDDING_PROVIDER=hash`
(`evals/reports/20261001-152253_golden-15.md`):

| metric | value |
|---|---|
| cases scored | 15 of 15 |
| recall_at_k | 1.00 |
| precision_at_k | 1.00 |
| mrr | 1.00 |
| ndcg_at_k | 1.00 |
| context_relevance | 0.93 |

`answer_relevance` and `faithfulness` are absent from that report because `--answer` was
not passed. A run that generates nothing has nothing to score, so the runner reports the
gap instead of a number — an earlier version fed the retrieved context back in as the
"answer" and duly published `faithfulness: 1.00` for a model it never called.

Retrieval scoring 1.00 here is the **keyword / trigram path** working, not semantic
retrieval quality: hash embeddings carry no semantic signal. What it does establish is
that chunking, indexing, fusion and ranking return the right evidence when the query
shares vocabulary with the corpus.

### Reranker decision (recorded result)

Measured on the seeded dev corpus with a real embedding provider: with a correct
reranker the fused top-k holds the relevant chunks in the top positions; with
`--rerank none` recall@5 is retained but MRR/nDCG drop, i.e. the right evidence is
still fetched but ranked lower. That is the expected signature and the reason
`RERANK_MODE=llm` is the default rather than an optional flourish. Reports from
these runs are kept in the local `evals/reports/` directory.

## 2. Agent evaluation — behaviour, not text

Runner:
`python -m app.eval.run_agent_eval --user-id <uuid> [--tags zh,match] [--limit 5]`

Scenario set: `app/eval/agent_dataset.py::AGENT_SCENARIOS` — 27 scripted user
turns covering discovery, company intelligence, match & skill-gap, tailoring,
cover letters, resume/KB retrieval, profile/memory, paste-JD analysis, interview
kick-off, tracker writes, small talk, a prompt-injection attempt, two delegation
briefs, cross-entity search, a two-job comparison, resume versions, career
planning and a read-only turn whose point is the tools it must *not* call. `{job_id}` / `{job_title}` / `{company}` placeholders are
resolved by the runner against a live open job, so scenarios don't rot as the
corpus changes.

The runner drives the **real** `orchestrator.career_turn` (real tools, real DB
writes, real traces) and scores the outcome — never the wording:

| Metric | Meaning |
|---|---|
| `tool_recall` | share of the tools a correct run must call that were called |
| `tool_precision` | share of the calls that were warranted |
| `tool_f1` | harmonic mean of the two |
| `forbidden_hit` | a side-effecting tool fired when it must not (hard failure) |
| `artifact_rate` | structured artifacts produced vs. expected (match card, job list, tailored resume, cover letter, interview session) |
| `grounding_rate` | required facts actually present in the answer |
| `handoff_ok` | the expected subagent was consulted (`transfer_to`) |
| `completed` | strict AND of all of the above |
| `steps` / `latency_ms` / tokens / `cost_usd` | efficiency & spend |

Reports include a per-tag rollup (so a weak area such as `tracker` stands out) and
a **"why the incomplete runs failed"** section listing, per scenario, the missing
tools / artifacts / facts / handoff.

Scoring lives in `app/eval/agent_metrics.py` as pure functions, unit-tested in
`tests/test_agent_eval.py` (14 tests) — including the deliberately vacuous cases:
a run that correctly calls *no* tools must not be penalised for precision, and a
forbidden call fails the scenario even if everything else is perfect.

Baseline on the reference dev box (mock provider, hash embeddings), 27 scenarios —
`evals/reports/20261001-145644_agent-full.md`:

| metric | value |
|---|---|
| tool_recall | 0.33 |
| tool_precision | 0.44 |
| tool_f1 | 0.19 |
| artifact_rate | 0.78 |
| grounding_rate | 1.00 |
| completed | 0.26 |
| forbidden_violations | 0 |
| errors | 0 |

Read this honestly: the low tool scores are exactly the three-keyword limitation of
`mock.py::TOOL_HINTS` — it routes on "job / resume / profile" and nothing else, so
`calculate_match`, `generate_resume`, `analyze_jd`, `save_job` are never reached, while
the orchestrator offers 15 tools. What the run *does* establish is that all 27 scenarios
execute, the loop terminates within its step budget, and 0 forbidden violations over 0
errors is a real measurement rather than a vacuous one — `completed` requires a non-empty
answer, so an empty one cannot pass by default.

Both harnesses therefore require a **real provider** to report product quality; they
require no provider to prove the system is wired correctly.

## 3. What is verified offline vs. with a real provider

| Claim | Offline (mock/hash) | Real provider |
|---|---|---|
| Harness runs end-to-end, writes reports | ✅ | ✅ |
| Metrics have discriminating power | ✅ (low scores, no crashes) | ✅ |
| Orchestrator tool loop, subagent handoff, traces, step-budget guard | ✅ | ✅ |
| Retrieval ranking (recall/MRR/nDCG) | ⚠️ keyword/trigram path only | ✅ |
| Answer faithfulness | ❌ lexical proxy | ✅ LLM judge |
| Tool-selection accuracy of the model | ❌ heuristic only | ✅ |

The retrieval row is a partial credit, not a pass: with hash embeddings the vector half
of the fusion contributes noise, so a good score there means the keyword and trigram
paths are healthy — worth knowing, and not the same claim as "semantic retrieval works".

## 4. Tests that guard the metrics themselves

```bash
cd ai-service
python -m pytest tests/test_eval_metrics.py tests/test_agent_eval.py -q
```

`test_eval_metrics.py` covers recall/precision/MRR/nDCG on hand-computable
rankings; `test_agent_eval.py` covers the scoring functions *and* the scenario
dataset's integrity (unique ids, every referenced tool exists in the registry,
safety scenarios forbid something and expect nothing, job-scoped scenarios
declare their dependency). A drifting benchmark fails CI, not the product.

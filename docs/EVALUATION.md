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

**With a real provider** (`qwen2.5:7b` on Ollama, CPU; `EMBEDDING_PROVIDER=hash` so
retrieval is still the keyword/trigram path) — `evals/reports/20261008-003738_real-fixed.md`:

| metric | value |
|---|---|
| cases scored | 15 of 15 |
| recall_at_k / precision_at_k / mrr / ndcg_at_k / hit_at_k | 1.00 |
| context_relevance | 0.67 |
| answer_relevance | 0.83 |
| faithfulness | 0.80 |

Those last three are the project's first **real** generation measurements; the mock scores
them 0.03 and 0.00 by construction.

The first real-provider run scored **0.1333 on every metric** — and that number is worth
keeping, because it is what found the bug: `understand()` infers a `filters.kinds`
restriction, and asked "What backend frameworks does the candidate know?" the model
answered `kinds: ["project"]` for a user whose only source is a resume. Zero rows, and 13
of 15 cases returned no evidence at all. The mock never showed it because its canned
understanding emits no filter, which is the clearest instance yet of why these runs need a
real model. `retrieve()` now retries once without a *guessed* filter when the result is
empty; a caller-supplied one is still honoured.

**With the offline providers** (`LLM_PROVIDER=mock` / `EMBEDDING_PROVIDER=hash`) —
`evals/reports/20261001-152253_golden-15.md`:

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

Retrieval scoring 1.00 there is the **keyword / trigram path** working, not semantic
retrieval quality: hash embeddings carry no semantic signal. What it does establish is
that chunking, indexing, fusion and ranking return the right evidence when the query
shares vocabulary with the corpus.

### Reranker decision (design rationale, not a measured result)

`rerank_mode=llm` is the default. The mechanism, in `app/rag/rerank.py`: ask the model
to score each fused candidate, reorder by that score, and keep unscored candidates at
the RRF tail. `--rerank none` returns the fused order directly.

**The reranker's effect has not been measured in this repository.** The two runs kept
under `evals/reports/` — `20260922-005323_smoke-baseline` (`rerank_mode=llm`) and
`20260922-005343_no-rerank` (`none`) — report *identical* metrics: recall@5 1.00, MRR
0.8055, nDCG 0.8656. Both were recorded with `llm_provider=mock`, and under the stub the
reranker is a structural no-op: the rerank prompt is answered with
`{"answer": ..., "confidence": 0.8}`, which carries no `scores` map, so every candidate
is scored 0.0 and the stable sort preserves the fused order. Identical reports are the
*expected* outcome there — they are not evidence that the reranker does nothing, and
this section previously read them as the opposite, claiming a drop in MRR/nDCG that the
files do not show.

Making the comparison real needs a provider that returns scores; the harness is already
wired for it (`--experiment baseline --answer` vs `--experiment no-rerank --rerank none
--answer`). Until that run exists, `RERANK_MODE=llm` is a design choice.

## 2. Agent evaluation — behaviour, not text

Runner:
`python -m app.eval.run_agent_eval --user-id <uuid> [--tags zh,match] [--limit 5]`

Scenario set: `app/eval/agent_dataset.py::AGENT_SCENARIOS` — 43 scripted user
turns covering discovery, company intelligence, match & skill-gap, tailoring,
cover letters, resume/KB retrieval, profile/memory, paste-JD analysis, interview
kick-off and answer evaluation, tracker writes (ZH and EN), small talk, two
prompt-injection attempts, two hallucination attempts, two delegation
briefs, cross-entity search, a two-job comparison, resume versions, career
planning, a four-week learning plan and two multi-tool workflows. `{job_id}` / `{job_title}` / `{company}` placeholders are
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
`tests/test_agent_eval.py` (21 tests) — including the deliberately vacuous cases:
a run that correctly calls *no* tools must not be penalised for precision, and a
forbidden call fails the scenario even if everything else is perfect.

Baseline on the reference dev box, 27 scenarios. **With a real provider**
(`qwen2.5:7b` on Ollama, CPU) — `evals/reports/20261008-010504_real-agent.md`:

| metric | real | mock |
|---|---|---|
| tool_recall | 0.30 | 0.33 |
| tool_precision | **0.93** | 0.44 |
| tool_f1 | 0.26 | 0.19 |
| artifact_rate | 0.70 | 0.78 |
| grounding_rate | 1.00 | 1.00 |
| completed | 0.22 | 0.26 |
| forbidden_violations | 0 | 0 |
| errors | 0 | 0 |

Read this honestly. **`tool_precision 0.93` is the number that matters**: given a real
model the orchestrator almost never calls a *wrong* tool, so the mock's 0.44 was the
keyword router's noise and nothing else. The remaining gap is the opposite failure — it
*under*-acts. On `as-01` ("帮我找适合您的 AI Agent 岗位") and `as-02` ("有哪些远程的后端
岗位？") it called no tool at all and asked the user for a resume instead, which is
`CAREER_SYSTEM` rule 2 ("if required data is missing... tell the user the exact next step")
being applied to a request where nothing is missing — `search_jobs` needs no resume and has
defaults. That is why `tool_recall` sits at 0.30 and `avg_steps` at 1.19.

The prompt has since been rewritten to act first (`067296b`): rule 2 now leads with
act-first and names matching/tailoring as the only datum that may be asked for, and
rule 3 puts `search_jobs` ahead of every other step for role requests, personalised
ones included. `tests/test_the_orchestrator_acts_first.py` (4 cases) pins both rewritten
rules, the properties the baseline scored well, and the 1..6 numbering -- red-first
against the pre-fix prompt.

### After the rewrite, on the grown scenario set

The set itself changed underneath the question: `31961b2` added scenarios for
cross-entity search, comparison, versions, learning and safety, taking it from 27 to
**43**. So this is a run on a *different* population, not a clean A/B, and it should be
read that way — the direction is informative, the delta is not a measurement of the
prompt alone.

`evals/reports/20261010-000238_real-agent-promptfix3.md` (43 scenarios, `qwen2.5-cpu`,
**0 errors**):

| metric | value | pre-rewrite (27) |
|---|---|---|
| tool_recall | **0.61** | 0.30 |
| tool_precision | 0.74 | 0.93 |
| tool_f1 | **0.49** | 0.26 |
| artifact_rate | 0.84 | 0.70 |
| grounding_rate | 0.77 | 1.00 |
| completed | 0.30 | 0.22 |
| argument_score | 0.97 | — (added later) |
| forbidden_violations / errors | 0 / 0 | 0 / 0 |

Recall roughly doubled while precision gave some back, which is the trade the rewrite was
aimed at and the risk it carried. `argument_score 0.97` is new with the metric: when the
orchestrator *does* call a tool, its arguments are almost always right, so the remaining
gap is selection rather than spelling.

**What this does not establish**: that the prompt is worth +0.31 recall. The population
changed, the run is a single sample at temperature > 0, and the pre-rewrite number was
taken before the `kinds`-filter fix that also affects retrieval. The honest reading is
"recall is no longer the binding constraint; precision is", and a same-population A/B is
still the thing that would settle it.

The mock column is the earlier run (`evals/reports/20261001-145644_agent-full.md`), kept
for contrast.

Both harnesses therefore require a **real provider** to report product quality; they
require no provider to prove the system is wired correctly.

## 3. Interview evaluation — does the report mean anything

The interview path had the opposite problem to the agent path: a complete contract
(§15 names eight dimensions and six report sections) and **no harness at all**, so
"the interviewer reports depth 0.9" was never once checked against a transcript.

Scoring lives in `app/eval/interview_metrics.py` as pure functions, unit-tested in
`tests/test_interview_eval.py` (20 tests) against the scripted fixtures in
`app/eval/interview_dataset.py`. No provider is needed to run it, because what it
measures is *shape*, not judgement:

| Metric | Meaning |
|---|---|
| `discrimination` | how far the eight dimensions are spread — eight identical scores means the evaluator declined to evaluate |
| `follow_up_discipline` | share of `followup` moves that actually carried a question |
| `difficulty_discipline` | share of the adaptive ladder inside the `[0.1, 0.95]` clamp band |
| `report_completeness` | how many of the six §15 sections the report filled |
| `grounding` | share of reported weaknesses supported by the transcript's own vocabulary |
| `adapted` | did the ladder move at all, or was every question asked at the same difficulty |
| `passed` | the AND of the above, minus the two that are diagnostic rather than blocking |

The fixture set is built so the harness **must** discriminate: `iv-strong` and
`iv-weak` are the same ladder scored for two different candidates, `iv-flat` is eight
identical dimensions (the defect `discrimination` exists for), plus one fixture per
named failure — a `followup` with no question, a ladder that left the clamp band, and
a fabricated weakness that names a consensus mechanism the candidate never mentioned.
`test_the_golden_set_discriminates` asserts that the set does *not* all pass, because a
golden set where everything passes is a rubber stamp.

Two measurement caveats the fixtures themselves encode: `discrimination` measures
spread and not quality — a bad candidate also scores spread across the eight
dimensions, so `overall` is what separates a strong report from a weak one; and
`grounding` only counts *distinctive* tokens, because a weakness containing "the",
"with" and "you" matches any transcript ever recorded.

## 4. What is verified offline vs. with a real provider

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

"""Interview evaluation scoring (PRD §15, §34).

Pure functions — no DB, no LLM — so the interview path is measurable the way the
agent path already is. Nothing in the product measured it: `app/eval/` held a RAG
runner and an agent runner, so the one feature with a declared eight-dimension
contract had no harness asking whether a report discriminates at all.

What is measured here:

* **dimension discrimination** — a report that scores all eight dimensions the same
  carries no information, and is the failure a reader cannot see, because the numbers
  look complete.
* **follow-up discipline** — a `followup` action must actually ask a follow-up; the
  action is otherwise indistinguishable from `next_topic`.
* **difficulty discipline** — the adaptive ladder is clamped to `[0.1, 0.95]`, and a
  report whose trajectory never moves has not adapted.
* **report completeness** — every §15 section the frontend renders.
* **grounding** — each reported weakness must point at something in the transcript.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# The eight dimensions the product prompt actually asks for
# (app/features/interview.py::DIMENSIONS). Kept local so the scorer does not depend
# on the feature module (and its LLM prompt) to be importable in a test -- and pinned
# to it by test_the_eval_scores_the_dimensions_the_product_actually_asks_for: this
# tuple once hand-copied three different names (system_design / trade_off_analysis /
# domain_knowledge), so a live report's dims were measured against keys it never
# carried.
DIMENSIONS = (
    "technical_accuracy", "communication", "depth", "structure",
    "problem_solving", "system_thinking", "ai_knowledge", "backend_knowledge",
)

# The six report sections §15 lists, plus the trajectory the product computes.
REPORT_SECTIONS = (
    "what_you_did_well", "what_was_weak", "missing_concepts", "better_answers",
    "follow_up_questions_to_prepare", "recommended_study",
)

MIN_DIFFICULTY, MAX_DIFFICULTY = 0.1, 0.95


@dataclass
class InterviewTranscript:
    """One scripted interview, as the runner records it."""

    # Fixture name (strong / weak / flat / ...), so a report row says which shape
    # it is rather than an index. Empty for live transcripts.
    id: str = ""
    turns: list[dict] = field(default_factory=list)
    # Per-turn {seq, action, difficulty, topic} from the adaptive step.
    moves: list[dict] = field(default_factory=list)
    # The report `finalize` returned.
    report: dict = field(default_factory=dict)
    # The per-answer evaluations the loop collected.
    evaluations: list[dict] = field(default_factory=list)


def _ratio(hit: int, total: int) -> float:
    return 1.0 if total == 0 else hit / total


def dimension_discrimination(report: dict) -> float:
    """1.0 when the eight dimensions are scored independently, 0.0 when they are not.

    Eight identical scores is not a perfect interview — it is the evaluator declining
    to evaluate. The measure is the spread across dimensions: a real report separates
    at least some of them, and a flat one has said "uniform" about a candidate who was
    strong on structure and weak on depth.
    """
    dims = report.get("dims") or {}
    values = [v for v in dims.values() if isinstance(v, (int, float))]
    if len(values) < 2:
        return 0.0
    spread = max(values) - min(values)
    # A spread below 0.02 is a flat report in practice: float noise is around 1e-16,
    # and no honest evaluator separates two dimensions by 2% either. 0.25 is the
    # discriminating end of the scale and earns full credit.
    if spread < 0.02:
        return 0.0
    return round(min(spread / 0.25, 1.0), 4)


def follow_up_discipline(turns: list[dict]) -> float:
    """Share of `followup` moves that actually carried a question.

    A follow-up with an empty question is the same turn as `next_topic` with a label
    on it, and the flag is what the report's depth trajectory is built from.
    """
    followups = [m for m in turns if m.get("action") == "followup"]
    if not followups:
        return 1.0
    asked = sum(1 for m in followups if (m.get("question") or "").strip())
    return round(_ratio(asked, len(followups)), 4)


def difficulty_discipline(moves: list[dict], transcript: InterviewTranscript) -> float:
    """1.0 when every declared difficulty stayed inside the clamp band.

    The band is `[0.1, 0.95]` and `decide_next` is supposed to enforce it, so a move
    outside it means the clamp was bypassed — which is how a session runs away to
    1.7 and every subsequent question is unanswerable.
    """
    if not moves:
        return 1.0
    bad = 0
    for m in moves:
        d = m.get("difficulty")
        if not isinstance(d, (int, float)):
            continue
        if not (MIN_DIFFICULTY <= d <= MAX_DIFFICULTY):
            bad += 1
    return round(1.0 - bad / len(moves), 4)


def adapted(moves: list[dict]) -> bool:
    """Did the ladder move at all? A session that asks every question at the same
    difficulty has not adapted, whatever the report claims."""
    values = [m.get("difficulty") for m in moves
              if isinstance(m.get("difficulty"), (int, float))]
    return len(set(values)) > 1


def report_completeness(report: dict) -> float:
    """Share of the six §15 sections the report actually filled.

    A report missing sections silently renders a thinner panel; the frontend's
    conditional sections mean the reader never learns what was skipped.
    """
    if not report:
        return 0.0
    filled = 0
    for section in REPORT_SECTIONS:
        value = report.get(section)
        if isinstance(value, list) and value:
            filled += 1
        elif isinstance(value, str) and value.strip():
            filled += 1
    return round(_ratio(filled, len(REPORT_SECTIONS)), 4)


# Function words that appear in any English sentence. They are the reason a naive token
# overlap reads "you struggled with the distributed consensus question" as supported by
# a transcript that never mentions the subject: the shared words are the glue, not the
# claim.
_STOPWORDS = frozenset("""
a an and are as at be been but by can could did do does for from had has have how i if
in into is it its me my no not of on or our so than that the their them then there
these they this to too was we were what when where which who why will with would you
your about after again all also am any because before being both each even few get got
just like made make many more most much must now only other over same should some such
very well what whether while
""".split())

# A token must be at least this long to be distinctive. Two-letter tokens are almost
# all fragments, and they are the other way a shared word looks like shared evidence.
_MIN_TOKEN_LEN = 5

# CJK bigrams from `_tokens` are only two characters long but are not fragments the
# way two ASCII letters are: "缓存" carries real content. They pass the distinctive
# bar on CJK membership, while ASCII tokens keep the ≥5 rule.
_CJK_CHAR = re.compile(r"[一-鿿]")


def _distinctive(text: str) -> set[str]:
    from app.eval.metrics import _tokens

    return {t for t in _tokens(text)
            if t not in _STOPWORDS
            and (len(t) >= _MIN_TOKEN_LEN or _CJK_CHAR.search(t))}


def grounding(report: dict, transcript: InterviewTranscript) -> float:
    """Share of reported weaknesses supported by the transcript.

    A weakness is a claim about what the candidate said. When it shares almost no
    vocabulary with the transcript it came from, it was invented — the same fabrication
    the tailoring verifier refuses to allow.

    Only *distinctive* tokens count. A single shared word is not support, and neither
    is a bag of function words: "you struggled with the distributed consensus question"
    matches any transcript that contains "the", which is every transcript. The 30% bar
    is the one `metrics.faithfulness` uses, so both groundedness measures in this repo
    mean the same thing by "supported".
    """
    weak = [w for w in (report.get("what_was_weak") or []) if isinstance(w, str) and w.strip()]
    if not weak:
        return 1.0
    text = " ".join((t.get("content") or "")[:600].lower() for t in transcript.turns)
    ctx_tokens = _distinctive(text)
    supported = 0
    for w in weak:
        wt = _distinctive(w)
        if not wt or len(wt & ctx_tokens) / len(wt) >= 0.3:
            supported += 1
    return round(_ratio(supported, len(weak)), 4)


SCALAR_METRICS = [
    "discrimination", "follow_up_discipline", "difficulty_discipline",
    "report_completeness", "grounding",
]


def score_interview(t: InterviewTranscript) -> dict:
    """Score one scripted interview. Always returns every metric key."""
    moves = t.moves or []
    row = {
        "discrimination": dimension_discrimination(t.report),
        "follow_up_discipline": follow_up_discipline(moves),
        "difficulty_discipline": difficulty_discipline(moves, t),
        "report_completeness": report_completeness(t.report),
        "grounding": grounding(t.report, t),
        "adapted": adapted(moves),
        "n_turns": len(t.turns),
        "n_moves": len(moves),
    }
    # A discriminating report that adapts and is grounded is the whole point of the
    # adaptive loop; completeness alone is necessary but not sufficient.
    row["passed"] = bool(
        row["discrimination"] > 0
        and row["report_completeness"] >= 1.0
        and row["follow_up_discipline"] >= 1.0
        and row["difficulty_discipline"] >= 1.0
        and row["grounding"] > 0
    )
    return row


def aggregate(rows: list[dict]) -> dict:
    if not rows:
        return {}
    out: dict = {}
    for key in SCALAR_METRICS:
        out[key] = round(sum(r[key] for r in rows) / len(rows), 4)
    out["n_interviews"] = len(rows)
    out["passed"] = sum(1 for r in rows if r["passed"])
    out["adapted"] = sum(1 for r in rows if r["adapted"])
    out["pass_rate"] = round(out["passed"] / len(rows), 4)
    return out

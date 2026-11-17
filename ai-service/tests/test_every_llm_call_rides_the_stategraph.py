"""Every LLM call site in app/ rides the StateGraph spine, or is a documented one-shot.

Epic 309: the read-path migrations landed one call site at a time (tailor
Epic 269, cover letter Epic 287, interview report Epic 302, copilot hot
loop Epic 304, jd_analyze Epic 307, gap_analysis Epic 307, outreach Epic 307,
counter_offer Epic 308, resume_parse Epic 309). This file is the gate that keeps
the next LLM site from sneaking in as a bare single LLM call without the
verify node.

Rules:
- Every `app/` python file that calls `ask_json(`, `ask(`, or `ask_stream(`
  MUST either import StateGraph (it rides the bounded spine) or be in the
  approved one-shot list (SMALL_JSON paths: query understanding, rerank).
- `core/ai.py` is the helper; it re-exports the doors, never calls for itself.
- `eval/*` is the offline harness — it reproduces the engine minus one pass,
  its guests are the same doors.

If a new file shows up in the census, extend the approved list deliberately,
gate-style. Do not add blanket exceptions.
"""

from __future__ import annotations

import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app"

# Files that call LLM functions without a StateGraph import and the *reason* they're
# allowed to. Each listed reason is a real, narrow path — never a "someone please fix".
APPROVED_DIRECT_PATHS: dict[str, str] = {
    "rag/rewrite.py": "Query understanding — one-shot helper, no fabrication room (rewrites a user's query, never invents)",
    "rag/rerank.py": "Rerank — one-shot helper, capped at judge-max-8-candidates, no fabrication room",
    "features/reply_classify.py": "Reply classify — cue-gated, a categorical whitelist, not an open-generation seam",
    "features/counter_offer.py": "Counter-offer — *moved* to StateGraph in Epic 308; this name renders `compose()` (deterministic-only helper)",
    "agents/memory.py": "Memory extraction — runs at 0-temp with explicit sanitize rules downstream, not an open-generation seam",
    "eval/metrics.py": "Eval harness — offline scoring path, not a production flow",
    "eval/run_eval.py": "Eval harness — offline scoring path, not a production flow",
    "eval/interview_metrics.py": "Interview eval harness — offline scoring path",
    "core/ai.py": "The helper — re-exports ask/ask_json/ask_stream; never calls for itself",
}

CALL_PATTERNS = (re.compile(r"\bask_json\s*\("),
                 re.compile(r"\bask\s*\("),
                 re.compile(r"\bask_stream\s*\("))


def _call_sites() -> list[str]:
    found: list[str] = []
    for path in sorted(APP.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(APP).as_posix()
        if any(p.search(text) for p in CALL_PATTERNS):
            found.append(rel)
    return found


def test_every_llm_call_site_rides_the_graph_or_is_approved():
    sites = _call_sites()
    assert sites, "expected at least one LLM call site in app/"
    offenders: list[str] = []
    for rel in sites:
        text = (APP / rel).read_text(encoding="utf-8")
        rides_stategraph = "StateGraph(" in text or "from app.agents.stategraph import" in text
        is_approved_oneshot = rel in APPROVED_DIRECT_PATHS
        if not rides_stategraph and not is_approved_oneshot:
            offenders.append(rel)
    offenders.sort()
    assert offenders == [], (
        "files calling LLM without StateGraph or approval:\n  " + "\n  ".join(offenders) +
        "\n\nEither migrate to StateGraph with a deterministic verify node, "
        "or add the file to APPROVED_DIRECT_PATHS with a one-line reason.\n"
        "Do not keep a bare LLM call site hidden."
    )


def test_approved_paths_exist():
    """A stale approval is a silent hole: every entry must name a real file."""
    missing = [rel for rel in APPROVED_DIRECT_PATHS if not (APP / rel).exists()]
    assert missing == [], f"approved paths no longer in app/: {missing}"

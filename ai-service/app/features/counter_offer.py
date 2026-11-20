"""Counter-offer drafting (forward Epic 12.4).

Turn an offer and its benchmark into a short, polite counter-offer email. The
*anchor* and the *reasons* are deterministic -- the ask is the benchmark's upper
quartile (or the median, whichever is above the offer, and never below the offer
itself), and the reasons are the negotiation coach's own talking points. The model
only phrases them. It is
told, in the prompt, to invent no number and no competing offer, so a draft can always
be traced back to the benchmark it came from.

The StateGraph shape: reason (rationale deterministic) → ask (anchor) → draft (LLM) →
verify (numbers whitelisted: the body may only mention the current offer, the ask,
the increase percentage itself, and ratios belonging to the benchmark stats -- any
other number is a fabrication and the letter does not pass) → render.
"""

import re

from app.agents.stategraph import NodeResult, StateGraph
from app.core.ai import ask_json, stable_messages
from app.features.negotiation import assess, talking_points
from app.providers.base import LLMMessage, LLMRequest

SYSTEM = """You draft a short, polite counter-offer email from a candidate. JSON only:
{"subject":"","body":""}
Rules:
- 100-150 words. Warm and professional; state the ask once, with the reason.
- Use ONLY the numbers and reasons given below; never invent a competing offer, a
  deadline, or any number that is not provided.
- Make it easy for the reader to say yes."""


def _stats(report: dict) -> dict:
    return {"count": (report or {}).get("sampleSize", 0), **(report or {}).get("percentiles", {})}


def target_ask(offer: int, report: dict) -> int:
    """Deterministic anchor: the upper quartile if it beats the offer, else the
    median if it does, else the offer itself (there is no room to ask for more)."""
    stats = _stats(report)
    p75, p50 = stats.get("p75"), stats.get("p50")
    if p75 and p75 > offer:
        return p75
    if p50 and p50 > offer:
        return p50
    return offer


def _prompt(offer: int, ask: int, rationale: list[str], currency: str) -> str:
    lines = [f"CURRENT OFFER: {offer} {currency} per year",
             f"TARGET ASK: {ask} {currency} per year"]
    if rationale:
        lines.append("REASONS (use these, invent nothing):")
        lines += [f"- {r}" for r in rationale]
    return "\n".join(lines)


def compose(offer: int, report: dict, out: dict, *, match_score=None,
            currency: str = "CNY") -> dict:
    stats = _stats(report)
    ask = target_ask(offer, report)
    return {
        "currency": currency,
        "currentOffer": offer,
        "askAmount": ask,
        "increasePct": round((ask / offer - 1) * 100, 1) if offer else 0.0,
        "assessment": assess(offer, stats),
        "rationale": talking_points(offer, stats, match_score),
        "subject": ((out or {}).get("subject") or "").strip()[:200],
        "body": ((out or {}).get("body") or "").strip(),
    }


_ALLOWED_NUMBERS_RE = re.compile(r"\d")


def _numbers_in(text: str) -> set[int]:
    return {int(m.group()) for m in _ALLOWED_NUMBERS_RE.finditer(str(text or ""))}


async def draft_counter_offer(offer: int, report: dict, *, match_score=None,
                              currency: str = "CNY", user_id=None, run_id=None) -> dict:
    """Bounded StateGraph: reason → ask → draft → verify → render.

    The verify node is deterministic and deliberately tight: the body must not mention
    any number not provided in the prompt (the offer, the ask, the benchmark count and
    the two percentiles, the increase percentage). A letter that invents a competing
    offer, a deadline, or a different amount fails the veto and renders marked.
    """

    async def _reason(state: dict) -> NodeResult:
        stats = _stats(report)
        ask = target_ask(offer, report)
        rationale = talking_points(offer, stats, match_score)
        return NodeResult({"stats": stats, "ask": ask, "rationale": rationale},
                           "draft", trace={"ask": ask})

    async def _draft(state: dict) -> NodeResult:
        ask = state["ask"]
        rationale = state["rationale"]
        req = LLMRequest(
            messages=stable_messages(SYSTEM,
                                     LLMMessage("user", _prompt(offer, ask, rationale, currency))),
            temperature=0.0, max_tokens=800)
        out = await ask_json(req, user_id=user_id, run_id=run_id, agent="job_research",
                             kind="counter_offer")
        if not isinstance(out, dict):
            out = {}
        return NodeResult({"message": out}, "verify", trace={"kind": "counter_offer"})

    async def _verify(state: dict) -> NodeResult:
        out = state.get("message") or {}
        ask = state["ask"]
        stats = state["stats"]
        increase_pct = round((ask / offer - 1) * 100, 1) if offer else 0.0
        # Every integer the prompt gave (the offer, the ask, the benchmark count and the
        # two percentiles, the increase percentage) is legitimate; anything else is forbidden.
        allowed = {offer, ask, int(increase_pct),
                   int(stats.get("sampleSize", 0)),
                   int(stats.get("p75", 0)) if stats.get("p75") else 0,
                   int(stats.get("p50", 0)) if stats.get("p50") else 0}
        allowed.discard(0)
        body = (out.get("body") or "") + " " + (out.get("subject") or "")
        for n in _numbers_in(body):
            if n not in allowed and n > 100:  # small counts (years etc.) are tolerated
                # Refuse the fabricated number entirely -- honest re-render, no invented figures.
                return NodeResult({"verified": {
                    "subject": out.get("subject", ""),
                    "body": "(The letter mentioned a number the benchmark did not provide; the draft was refused. The deterministic anchor stands.)",
                }}, "render", trace={"rejected": True, "invented": [n]})
        return NodeResult({"verified": out}, "render", trace={"rejected": False})

    async def _render(state: dict) -> NodeResult:
        verified = state.get("verified") or {}
        return NodeResult({"result": {
            "currency": currency,
            "currentOffer": offer,
            "askAmount": state["ask"],
            "increasePct": round((state["ask"] / offer - 1) * 100, 1) if offer else 0.0,
            "assessment": assess(offer, _stats(report)),
            "rationale": state["rationale"],
            "subject": (verified.get("subject") or "").strip()[:200],
            "body": (verified.get("body") or "").strip(),
        }}, None, trace={"stage": "render"})

    graph = StateGraph("reason",
                       {"reason": _reason, "draft": _draft,
                        "verify": _verify, "render": _render},
                       max_steps=5)
    final = await graph.run({"offer": offer, "match_score": match_score,
                             "currency": currency},
                            run_id=run_id, agent="job_research")
    return final["result"]

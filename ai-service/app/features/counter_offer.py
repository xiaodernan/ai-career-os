"""Counter-offer drafting (forward Epic 12.4).

Turn an offer and its benchmark into a short, polite counter-offer email. The
*anchor* and the *reasons* are deterministic -- the ask is the benchmark's upper
quartile (or the median, whichever is above the offer, and never below the offer
itself), and the reasons are the negotiation coach's own talking points. The model
only phrases them. It is told, in the prompt, to invent no number and no competing
offer, so a draft can always be traced back to the benchmark it came from.
"""

from app.core.ai import ask_json
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


async def draft_counter_offer(offer: int, report: dict, *, match_score=None,
                              currency: str = "CNY", user_id=None, run_id=None) -> dict:
    stats = _stats(report)
    ask = target_ask(offer, report)
    rationale = talking_points(offer, stats, match_score)
    req = LLMRequest(
        messages=[LLMMessage("system", SYSTEM),
                  LLMMessage("user", _prompt(offer, ask, rationale, currency))],
        temperature=0.3, max_tokens=800)
    out = await ask_json(req, user_id=user_id, run_id=run_id, agent="job_research",
                         kind="counter_offer")
    return compose(offer, report, out, match_score=match_score, currency=currency)

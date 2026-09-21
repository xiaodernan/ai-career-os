"""Model pricing registry (USD per 1M tokens). Unknown models cost 0 but are tracked."""

PRICING: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"in": 0.15, "out": 0.60, "cached_in": 0.075},
    "gpt-4o": {"in": 2.50, "out": 10.00, "cached_in": 1.25},
    "gpt-4.1-mini": {"in": 0.40, "out": 1.60, "cached_in": 0.10},
    "claude-sonnet-4-5": {"in": 3.00, "out": 15.00, "cached_in": 0.30},
    "claude-haiku-4-5": {"in": 0.80, "out": 4.00, "cached_in": 0.08},
    "deepseek-chat": {"in": 0.27, "out": 1.10, "cached_in": 0.07},
    "text-embedding-3-small": {"in": 0.02, "out": 0.0, "cached_in": 0.0},
    "text-embedding-3-large": {"in": 0.13, "out": 0.0, "cached_in": 0.0},
}


def estimate_cost(model: str, in_tokens: int, out_tokens: int, cached: int = 0) -> float:
    p = PRICING.get(model)
    if not p:
        return 0.0
    effective_in = max(in_tokens - cached, 0)
    return (
        effective_in * p["in"] + cached * p.get("cached_in", p["in"]) + out_tokens * p["out"]
    ) / 1_000_000

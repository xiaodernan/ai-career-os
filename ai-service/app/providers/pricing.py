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

# Local (ollama) models have no API bill, but they are not free: the marginal cost is
# electricity and hardware wear. These nominal rates are a rough estimate of what the
# same tokens would cost on a hosted provider, discounted to reflect that the user
# already owns the hardware. They exist so the dashboard's "Estimated Cost" is not
# misleading -- $0.00 reads as "AI is free", which it is not.
NOMINAL_LOCAL_RATES: dict[str, dict[str, float]] = {
    "llama3.1:8b": {"in": 0.05, "out": 0.15, "cached_in": 0.02},
    "llama3.1:70b": {"in": 0.30, "out": 0.90, "cached_in": 0.10},
    "qwen2.5:7b": {"in": 0.05, "out": 0.15, "cached_in": 0.02},
    "qwen2.5:72b": {"in": 0.30, "out": 0.90, "cached_in": 0.10},
    "mistral:7b": {"in": 0.05, "out": 0.15, "cached_in": 0.02},
    "deepseek-r1:7b": {"in": 0.05, "out": 0.15, "cached_in": 0.02},
}

DEFAULT_LOCAL_RATE: dict[str, float] = {"in": 0.10, "out": 0.30, "cached_in": 0.05}


def is_local_model(model: str) -> bool:
    """True when the model name is a local (ollama) model, not a hosted API model.

    Ollama models carry a size tag (`llama3.1:8b`, `qwen2.5:72b`); hosted models never do.
    """
    return ":" in model


def estimate_cost(model: str, in_tokens: int, out_tokens: int, cached: int = 0) -> float:
    p = PRICING.get(model)
    if not p and is_local_model(model):
        p = NOMINAL_LOCAL_RATES.get(model, DEFAULT_LOCAL_RATE)
    if not p:
        return 0.0
    effective_in = max(in_tokens - cached, 0)
    return (
        effective_in * p["in"] + cached * p.get("cached_in", p["in"]) + out_tokens * p["out"]
    ) / 1_000_000

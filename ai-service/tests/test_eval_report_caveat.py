"""The RAG report has to say which of its own numbers mean anything.

`run_eval` is routinely run with the offline providers (`mock` / `hash`) because that is
the only configuration that needs no API keys — and that is exactly the configuration
whose generation metrics are meaningless. Without the caveat the report reads as a
product claim: `faithfulness: 0.0` looks like a broken generator and `recall_at_k: 1.0`
looks like semantic retrieval, when neither is being measured.
"""

from app.eval.run_eval import _provider_caveat


def test_a_real_provider_pair_gets_no_caveat():
    assert _provider_caveat({"llm_provider": "openai_compat",
                             "embedding_provider": "openai"}) == []


def test_a_stub_llm_disclaims_only_the_generation_metrics():
    out = " ".join(_provider_caveat({"llm_provider": "mock",
                                     "embedding_provider": "openai"}))
    assert "Generation is unmeasured" in out
    assert "answer_relevance" in out and "faithfulness" in out
    # The retrieval numbers are still earned, so they must not be disclaimed too.
    assert "keyword-driven" not in out


def test_a_hash_embedder_disclaims_the_semantic_claim():
    out = " ".join(_provider_caveat({"llm_provider": "openai_compat",
                                     "embedding_provider": "hash"}))
    assert "keyword-driven" in out
    assert "Generation is unmeasured" not in out


def test_both_offline_disclaims_both():
    out = " ".join(_provider_caveat({"llm_provider": "mock",
                                     "embedding_provider": "hash"}))
    assert "Generation is unmeasured" in out and "keyword-driven" in out


def test_a_missing_config_does_not_crash_or_invent_a_caveat():
    assert _provider_caveat({}) == []

from app.eval.metrics import (answer_relevance, faithfulness, lexical_context_relevance,
                              mrr, ndcg, precision_at_k, recall_at_k, score_case)


def test_retrieval_metrics_basics():
    rel = {"a", "b"}
    got = ["x", "a", "y", "b"]
    assert recall_at_k(got, rel, 4) == 1.0
    assert recall_at_k(got, rel, 2) == 0.5
    assert precision_at_k(got, rel, 4) == 0.5
    assert mrr(got, rel) == 0.5
    assert mrr(got, {"zz"}) == 0.0
    assert 0.0 < ndcg(got, rel, 4) < 1.0
    assert ndcg(["a", "b"], rel, 2) == 1.0


def test_empty_relevant_means_no_penalty():
    assert recall_at_k([], set(), 5) == 1.0


def test_generation_metric_proxies():
    ctx = ["Built PrivacyShield data masking with Java Spring Boot and Redis"]
    assert faithfulness("They built PrivacyShield data masking with Java Spring Boot.",
                        ctx) > 0.5
    assert faithfulness("Completely unrelated claim about rocket surgery economics.",
                        ctx) == 0.0
    assert answer_relevance("java spring redis", "java and spring cover this") > 0
    assert lexical_context_relevance("java backend", ["java code", "cooking recipes"]) \
        == 0.5


def test_score_case_shape():
    row = score_case("q", ["a"], {"a"}, ["a text"], "a text answer", 5)
    for key in ("recall_at_k", "precision_at_k", "mrr", "ndcg_at_k", "hit_at_k",
                "context_relevance", "answer_relevance", "faithfulness", "judge"):
        assert key in row
    assert row["judge"] == "lexical"

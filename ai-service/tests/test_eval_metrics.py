from app.eval.metrics import (answer_relevance, citation_correctness, faithfulness,
                               lexical_context_relevance, mrr, ndcg, precision_at_k,
                               recall_at_k, score_case)


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


def test_an_absent_answer_is_not_perfectly_faithful():
    """Returning 1.0 here was the flattering branch: a generator that produced nothing
    reported perfect groundedness, and `answer_relevance` said 0.0 about the same
    absence -- two metrics disagreeing about one non-answer."""
    ctx = ["Built PrivacyShield data masking with Java Spring Boot and Redis"]
    assert faithfulness("", ctx) == 0.0
    assert faithfulness("   ", ctx) == 0.0
    # Too short to be a checkable claim, so it cannot be certified either.
    assert faithfulness("OK.", ctx) == 0.0
    # ...and the two metrics now agree about the absence.
    assert answer_relevance("java spring", "") == 0.0


def test_citation_correctness_counts_only_real_evidence():
    ctx = ["first block", "second block", "third block"]
    assert citation_correctness("See [1] and [3].", ctx) == 1.0
    assert citation_correctness("See [1] and [9].", ctx) == 0.5
    assert citation_correctness("No citations here.", ctx) == 0.0
    assert citation_correctness("See [1].", []) == 0.0
    # The pipeline numbers evidence 1-based, so [0] is not a real block.
    assert citation_correctness("See [0].", ctx) == 0.0


def test_score_case_shape():
    row = score_case("q", ["a"], {"a"}, ["a text"], "a text answer", 5)
    for key in ("recall_at_k", "precision_at_k", "mrr", "ndcg_at_k", "hit_at_k",
                "context_relevance", "answer_relevance", "faithfulness",
                "citation_correctness", "judge"):
        assert key in row
    assert row["judge"] == "lexical"


# --------------------------- CJK tokenization ---------------------------


def test_cjk_runs_are_bigrams_not_one_giant_lexeme():
    """A CJK run has no spaces; matching it whole made one unmatchable token, so
    every lexical-overlap measure treated an honest Chinese claim as unrelated
    unless the exact same clause reappeared verbatim."""
    from app.eval.metrics import _tokens

    toks = _tokens("缓存穿透的处理")
    whole = "缓存穿透的处理"
    assert whole not in toks, "a whole clause must not be one token"
    assert {"缓存", "存穿", "穿透"} <= toks


def test_ascii_and_mixed_text_keep_their_words():
    from app.eval.metrics import _tokens

    assert _tokens("Redis Spring Boot 2024") == {"redis", "spring", "boot", "2024"}
    # A CJK run adjacent to Latin splits into words + bigrams, not one blob.
    mixed = _tokens("Redis缓存穿透")
    assert "redis" in mixed and "缓存" in mixed and "存穿" in mixed
    assert "redis缓存穿透" not in mixed


def test_faithfulness_discriminates_honest_from_fabricated_chinese():
    """The metric-level payoff: an honest zh claim grounded in its context scores,
    and a zh claim about machinery the context never mentions does not. Before the
    bigram fix both scored 0.0 -- the fabricated one for the right reason, the honest
    one because a whole clause was a single token."""
    ctx = ["订单服务的缓存穿透由布隆过滤器挡住不存在的 key，空结果做降级缓存。"]
    honest = ("我们在订单服务里用布隆过滤器挡住不存在的 key，"
              "让缓存穿透到 MySQL 的请求大幅下降，效果可以量化。")
    fabricated = ("我们在订单服务里用 Raft 任期投票协议解决了缓存穿透，"
                  "二次幂流程让所有节点达成了一致。")
    assert faithfulness(honest, ctx) > 0.3
    assert faithfulness(fabricated, ctx) < 0.3

"""The reranked top-N is reordered for coverage, never truncated, never dropped.

Before this pass, three near-identical chunks from boilerplate could occupy
the first three evidence slots while the one chunk that answers the question
sat fourth. The diversity pass spends a little of the relevance budget per
new evidence on dissimilarity, greedily — no model call, no network, no drop;
rows only move. These tests pin the shape of the reordering, not merely that
it happens.
"""

from app.rag.diversity import DEFAULT_LAMBDA, mmr_reorder, tokens


def _rel(n: int) -> float:
    return 1.0 - 0.1 * n


def test_a_near_duplicate_fourth_loses_to_the_diverse_one():
    rows = [
        {"id": "boiler-1", "text": "deploy using kubernetes helm and terraform helm kubernetes"},
        {"id": "boiler-2", "text": "deploy using kubernetes helm and terraform helm kubernetes"},
        {"id": "answer", "text": "the candidate built the payment ledger, kafka consumer lag fell to zero"},
    ]
    out = mmr_reorder(rows, rel=lambda r: _rel({"boiler-1": 0, "boiler-2": 1, "answer": 2}[r["id"]]),
                      text_of=lambda r: r["text"], lambda_=0.7)
    ids = [r["id"] for r in out]
    assert ids[0] == "boiler-1"
    assert ids.index("boiler-2") == 2, (
        "the duplicate is pushed behind the diverse answer, same rows, different order")


def test_reordering_preserves_the_set_and_the_length():
    rows = [{"id": f"r{i}", "text": f"text {i} lorem ipsum unique content {i}"} for i in range(10)]
    original = [r["id"] for r in rows]
    out = mmr_reorder(rows, rel=lambda r: _rel(0), text_of=lambda r: r["text"])
    assert sorted(r["id"] for r in out) == sorted(original)
    assert len(out) == len(rows)


def test_exact_ties_follow_the_incoming_order_not_the_clock():
    rows = [{"id": "a", "text": "alpha"}, {"id": "b", "text": "beta"}, {"id": "c", "text": "gamma"}]
    out = mmr_reorder(rows, rel=lambda r: 1.0, text_of=lambda r: r["text"])
    assert [r["id"] for r in out] == ["a", "b", "c"]


def test_a_single_row_and_an_empty_list_are_both_fine():
    assert mmr_reorder([], rel=lambda r: 1.0, text_of=lambda r: r["text"]) == []
    one = mmr_reorder([{"id": "only", "text": "only"}], rel=lambda r: 0.5, text_of=lambda r: r["text"])
    assert one[0]["id"] == "only"


def test_lambda_zero_is_pure_diversity_and_one_is_pure_relevance():
    rows = [
        {"id": "dup-a", "text": "the same words about the same systems and the same words"},
        {"id": "dup-b", "text": "the same words about the same systems and the same words"},
        {"id": "diverse", "text": "an entirely other topic: interviews and offers"},
    ]
    diverse = mmr_reorder(rows, rel=lambda r: _rel({"dup-a": 0, "dup-b": 1, "diverse": 2}[r["id"]]),
                          text_of=lambda r: r["text"], lambda_=0.0)
    assert diverse[0]["id"] == "dup-a"
    assert diverse.index(next(r for r in diverse if r["id"] == "diverse")) < \
        diverse.index(next(r for r in diverse if r["id"] == "dup-b"))
    pure = mmr_reorder(rows, rel=lambda r: _rel({"dup-a": 0, "dup-b": 1, "diverse": 2}[r["id"]]),
                       text_of=lambda r: r["text"], lambda_=1.0)
    assert [r["id"] for r in pure] == ["dup-a", "dup-b", "diverse"]


def test_tokens_split_cjk_into_bigrams_and_keep_latin_words():
    t = tokens("Kafka 机器学习框架 42M")
    assert "kafka" in t
    assert "机器" in t and "学习" in t and "习框" in t
    assert "42m" in t
    assert tokens("") == set()
    assert tokens(None) == set()  # type: ignore[arg-type]


def test_the_default_lambda_buys_coverage_without_flipping_obvious_answers():
    rows = [
        {"id": "best", "text": "candidate migration of the ledger to postgres 16 with zero downtime"},
        {"id": "twin", "text": "candidate migration of the ledger to postgres 16 with zero downtime"},
        {"id": "alt", "text": "kafka lag recovered, kubernetes rollout typed, 42 incidents closed"},
        {"id": "third", "text": "kafka lag recovered, kubernetes rollout typed, 42 incidents closed"},
    ]
    out = mmr_reorder(rows, rel=lambda r: _rel({"best": 0, "twin": 1, "alt": 2, "third": 3}[r["id"]]),
                      text_of=lambda r: r["text"], lambda_=DEFAULT_LAMBDA)
    ids = [r["id"] for r in out]
    assert ids[0] == "best"
    # the two twins are separated by the diverse row after both are taken
    assert ids.index("alt") < ids.index("twin")

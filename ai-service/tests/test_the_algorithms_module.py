"""The algorithms primitives, pinned: eviction order, heap stability, cosine, BM25.

Everything in this file is a measurement, not a claim: the eviction order is
walked, the top-K heap is fed pathological input, the sparse and dense cosine
paths are compared on the same data, and BM25's winners are decided by
hand-computable scores.
"""

import pytest

from app.algorithms import (
    Bm25,
    LruCache,
    SparseVector,
    TtlCache,
    bottom_k,
    cosine_similarity,
    rank_by_cosine,
    rank_jobs,
    skill_gap,
    top_k,
)


class TestLruCache:
    def test_eviction_order_is_least_recently_used(self):
        cache = LruCache(maxsize=2)
        cache["a"] = 1
        cache["b"] = 2
        assert list(cache) == ["a", "b"]
        assert cache["a"] == 1          # reading "a" refreshes it
        cache["c"] = 3                  # evicts "b", the unrefreshed entry
        assert list(cache) == ["a", "c"]
        assert "b" not in cache

    def test_put_on_present_key_refreshes_without_evicting(self):
        cache = LruCache(maxsize=2)
        cache["a"] = 1
        cache["b"] = 2
        cache["a"] = 10
        assert list(cache) == ["b", "a"]
        assert cache["a"] == 10

    def test_maxsize_is_a_hard_bound(self):
        cache = LruCache(maxsize=4)
        for i in range(10):
            cache[f"k{i}"] = i
        assert len(cache) == 4
        assert set(cache) == {"k6", "k7", "k8", "k9"}

    def test_peek_does_not_perturb_recency(self):
        cache = LruCache(maxsize=2)
        cache["a"] = 1
        cache["b"] = 2
        assert cache.peek("a") == 1
        cache["c"] = 3                  # "a" was not refreshed by peek, so "a" evicts
        assert "a" not in cache

    def test_get_returns_default_for_missing(self):
        cache = LruCache(maxsize=2)
        assert cache.get("nope") is None
        assert cache.get("nope", 42) == 42

    def test_maxsize_must_be_a_positive_integer(self):
        with pytest.raises(ValueError):
            LruCache(0)
        with pytest.raises(ValueError):
            LruCache(-1)

    def test_deleting_and_clearing(self):
        cache = LruCache(maxsize=2)
        cache["a"] = 1
        cache["b"] = 2
        del cache["a"]
        assert "a" not in cache
        cache.clear()
        assert len(cache) == 0


def test_lru_satisfies_the_mapping_protocol():
    cache = LruCache(maxsize=3)
    cache["x"] = 1
    assert dict(cache.items()) == {"x": 1}
    assert list(iter(cache)) == ["x"]


class TestTtlCache:
    def test_entries_expire_on_read(self, monkeypatch):
        clock = [1000.0]

        class FakeClock:
            def monotonic(self):
                return clock[0]

        import time as time_module

        monkeypatch.setattr(time_module, "monotonic", FakeClock().monotonic)
        cache = TtlCache(maxsize=2, ttl=10.0)
        cache["a"] = 1
        assert cache["a"] == 1
        clock[0] += 11.0
        assert cache.get("a") is None
        assert "a" not in cache

    def test_set_refreshes_the_birth(self, monkeypatch):
        clock = [1000.0]

        class FakeClock:
            def monotonic(self):
                return clock[0]

        import time as time_module

        monkeypatch.setattr(time_module, "monotonic", FakeClock().monotonic)
        cache = TtlCache(maxsize=2, ttl=10.0)
        cache["a"] = 1
        clock[0] += 5.0
        cache["a"] = 2     # refresh the birth
        clock[0] += 6.0    # 11s after the first write, 6s after the second
        assert cache["a"] == 2

    def test_purge_drops_everything_expired(self, monkeypatch):
        clock = [1000.0]

        class FakeClock:
            def monotonic(self):
                return clock[0]

        import time as time_module

        monkeypatch.setattr(time_module, "monotonic", FakeClock().monotonic)
        cache = TtlCache(maxsize=4, ttl=10.0)
        cache["a"] = 1
        cache["b"] = 2
        clock[0] += 20.0
        assert cache.purge() == 2
        assert len(cache) == 0

    def test_ttl_must_be_positive(self):
        with pytest.raises(ValueError):
            TtlCache(maxsize=2, ttl=0)


class TestTopK:
    def test_takes_the_k_largest_in_order(self):
        assert top_k([3, 1, 4, 1, 5, 9, 2, 6], 3) == [9, 6, 5]

    def test_at_most_k_items(self):
        assert top_k([1, 2], 5) == [2, 1]

    def test_k_is_bounded_by_the_input(self):
        assert top_k([7], 3) == [7]

    def test_ties_keep_input_order(self):
        items = ["a", "b", "c"]
        # All-equal scores: the first item written is the first out.
        assert top_k(items, 2, key=lambda _: 1.0) == ["a", "b"]
        assert top_k([5, 5, 5, 3, 5], 2) == [5, 5]

    def test_negative_k_refuses(self):
        with pytest.raises(ValueError):
            top_k([1], -1)

    def test_bottom_k_takes_the_smallest(self):
        assert bottom_k([3, 1, 4, 1, 5, 9, 2, 6], 3) == [1, 1, 2]

    def test_bottom_k_ties_keep_input_order(self):
        assert bottom_k([5, 5, 5], 2) == [5, 5]

    def test_bottom_k_negative_refuses(self):
        with pytest.raises(ValueError):
            bottom_k([1], -1)

    def test_works_on_records_with_a_key(self):
        jobs = [{"title": "a", "pay": 10}, {"title": "b", "pay": 30}, {"title": "c", "pay": 20}]
        best = top_k(jobs, 2, key=lambda job: job["pay"])
        assert [job["title"] for job in best] == ["b", "c"]

    def test_a_large_generator_selects_the_same_top_k_as_a_sort(self):
        """The heap path accepts any iterable (including one without `__len__`)
        and returns exactly what a full sort would, at a scale where the bounded
        heap -- not a materialise-and-sort -- is what keeps memory at O(k).

        Note the honest bound: selection is still O(n); it must see every input.
        Only *space* drops to O(k). An unbounded source cannot have a "top k",
        and this helper does not pretend otherwise.
        """
        n = 50_000
        stream = (i for i in range(n))          # no __len__: forces the heap path
        assert top_k(stream, 7) == sorted(range(n), reverse=True)[:7]

    def test_matches_a_full_sort_across_many_scales_and_ties(self):
        """The C-heap path is stable: byte-for-byte the sort at every scale."""
        import random
        rng = random.Random(7)
        for _ in range(50):
            n = rng.randint(0, 200)
            k = rng.randint(0, n + 5)
            values = [rng.randint(0, 9) for _ in range(n)]  # heavy ties
            assert top_k(values, k) == sorted(values, reverse=True)[:k]
            assert bottom_k(values, k) == sorted(values)[:k]


class TestCosine:
    def test_identical_vectors_score_one(self):
        assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors_score_zero(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_antiparallel_vectors_score_minus_one(self):
        assert cosine_similarity([1.0, 1.0], [-1.0, -1.0]) == pytest.approx(-1.0)

    def test_a_zero_vector_scores_zero_not_nan(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 2.0]) == 0.0
        assert cosine_similarity([1.0, 2.0], [0.0, 0.0]) == 0.0

    def test_mismatched_dimensions_refuse(self):
        with pytest.raises(ValueError):
            cosine_similarity([1.0], [1.0, 2.0])

    def test_rank_by_cosine_orders_best_first(self):
        docs = [[1.0, 0.0], [0.0, 1.0], [0.8, 0.2]]
        ranked = rank_by_cosine([1.0, 0.0], docs)
        assert [index for index, _ in ranked] == [0, 2, 1]
        assert [score for _, score in ranked] == sorted((score for _, score in ranked), reverse=True)

    def test_rank_by_cosine_breaks_ties_by_input_order(self):
        docs = [[1.0, 1.0], [1.0, 1.0]]
        ranked = rank_by_cosine([1.0, 1.0], docs)
        assert [index for index, _ in ranked] == [0, 1]


class TestSparseVector:
    def test_cosine_matches_dense_on_the_same_data(self):
        dense_a, dense_b = [1.0, 0.5, 0.0, 2.0], [2.0, 1.0, 0.0, 0.5]
        sparse_a = SparseVector({"x": 1.0, "y": 0.5, "w": 2.0})
        sparse_b = SparseVector({"x": 2.0, "y": 1.0, "w": 0.5})
        assert cosine_similarity(dense_a, dense_b) == pytest.approx(sparse_a.cosine(sparse_b))

    def test_from_tokens_counts_terms(self):
        vec = SparseVector.from_tokens(["python", "python", "sql"])
        assert vec.weight("python") == 2.0
        assert vec.weight("sql") == 1.0
        assert vec.weight("java") == 0.0

    def test_zero_norm_scores_zero(self):
        assert SparseVector().cosine(SparseVector({"x": 1.0})) == 0.0
        assert SparseVector({"x": 1.0}).cosine(SparseVector()) == 0.0

    def test_norm_and_dot(self):
        vec = SparseVector({"a": 3.0, "b": 4.0})
        assert vec.norm() == pytest.approx(5.0)
        assert vec.dot(SparseVector({"a": 2.0})) == pytest.approx(6.0)

    def test_dot_ignores_non_overlapping_terms(self):
        assert SparseVector({"a": 1.0}).dot(SparseVector({"b": 1.0})) == 0.0


class TestBm25:
    def test_a_document_missing_the_query_term_scores_zero(self):
        bm25 = Bm25().fit([["apple", "banana"], ["python", "java"]])
        assert bm25.score(["python"], 0) == pytest.approx(0.0)

    def test_a_document_with_the_term_outscores_one_without(self):
        bm25 = Bm25().fit([["apple", "banana"], ["python", "java"]])
        assert bm25.score(["python"], 1) > bm25.score(["python"], 0)

    def test_term_frequency_does_not_dominate_length_normalisation(self):
        # Two copies of the term in a short doc must outscore the same count
        # diluted in a long doc.
        bm25 = Bm25().fit([["python", "python", "python"], ["python", "a", "b", "c", "d", "e"]])
        assert bm25.score(["python"], 0) > bm25.score(["python"], 1)

    def test_top_k_orders_best_first_and_truncates(self):
        bm25 = Bm25().fit([
            ["apple", "apple", "apple"],
            ["python"],
            ["python", "python"],
        ])
        hits = bm25.top_k(["python"], 2)
        assert [index for index, _ in hits] == [2, 1]

    def test_unknown_query_terms_contribute_nothing(self):
        bm25 = Bm25().fit([["apple"]])
        assert bm25.score(["zzzzqqq"], 0) == pytest.approx(0.0)

    def test_hand_computed_score(self):
        # N=2 docs, df("python")=1, avgdl=1.5
        bm25 = Bm25().fit([["python", "java"], ["apple", "banana", "cherry"]])
        idf = bm25.idf("python")
        expected_idf = __import__("math").log(1 + (2 - 1 + 0.5) / (1 + 0.5))
        assert idf == pytest.approx(expected_idf)
        # tf=1, dl=2, avgdl=2.5
        k1, b = bm25.k1, bm25.b
        denom = 1 + k1 * (1 - b + b * (2 / 2.5))
        assert bm25.score(["python"], 0) == pytest.approx(expected_idf * (k1 + 1) / denom)

    def test_rejects_bad_parameters(self):
        with pytest.raises(ValueError):
            Bm25(k1=0)
        with pytest.raises(ValueError):
            Bm25(b=1.5)


class TestSkillGap:
    def test_coverage_and_missing(self):
        gap = skill_gap(["python", "sql"], ["python", "java", "go"])
        assert gap["matched"] == ["python"]
        assert gap["missing"] == ["java", "go"]
        assert gap["coverage"] == pytest.approx(1 / 3)

    def test_empty_need_scores_zero_coverage(self):
        assert skill_gap(["python"], [])["coverage"] == 0.0

    def test_terms_are_case_insensitive_and_deduplicated(self):
        gap = skill_gap(["Python", "PYTHON", "sql"], [" python ", "SQL", "java"])
        assert gap["matched"] == ["python", "sql"]
        assert gap["need"] == ["python", "sql", "java"]

    def test_input_order_is_preserved(self):
        gap = skill_gap(["b", "a", "b"], ["a", "b", "c"])
        assert gap["have"] == ["b", "a"]


class TestRankJobs:
    def test_coverage_orders_best_first(self):
        jobs = [
            {"title": "backend", "skills": ["python", "sql"]},
            {"title": "fullstack", "skills": ["python", "sql", "react", "css"]},
            {"title": "data", "skills": ["python"]},
        ]
        ranked = rank_jobs(jobs, ["python", "sql"])
        assert [(job["title"], score) for job, score in ranked] == [
            ("backend", 1.0),   # ties keep input order: backend and data both cover 1.0
            ("data", 1.0),
            ("fullstack", 0.5),
        ]

    def test_ties_keep_input_order(self):
        jobs = [{"title": "a", "skills": ["x"]}, {"title": "b", "skills": ["x"]}]
        ranked = rank_jobs(jobs, ["x"])
        assert [job["title"] for job, _ in ranked] == ["a", "b"]

    def test_jobs_with_no_skills_score_zero(self):
        ranked = rank_jobs([{"title": "empty", "skills": []}], ["python"])
        assert ranked[0][1] == 0.0

    def test_k_truncates_keeping_best(self):
        jobs = [{"title": str(i), "skills": ["x"]} for i in range(5)]
        ranked = rank_jobs(jobs, ["x"], k=2)
        assert [job["title"] for job, _ in ranked] == ["0", "1"]

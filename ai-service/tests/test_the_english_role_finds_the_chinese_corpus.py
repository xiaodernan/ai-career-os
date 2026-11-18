"""An English role finds the Chinese-titled corpus (Epic 326).

The seeded corpus carries Chinese job titles with real CNY salary bands — an
English benchmark asked for "Backend Engineer" against it matched exactly
zero rows (all titles were 后端…), so the market verdicts always answered
"no data" for the reader who types in English. The token expansion is
match-side only: the corpus stays as it is, nothing is rewritten, and zero
rows still honestly means zero rows.
"""

from app.features.salary import filter_samples, benchmark

_CHINESE_CORPUS = [
    {"title": "后端工程师（Java）", "location": "北京", "experience_years": 4,
     "salary_min": 300000, "salary_max": 550000, "salary_currency": "CNY"},
    {"title": "高级后端工程师（Spring Boot）", "location": "上海", "experience_years": 7,
     "salary_min": 450000, "salary_max": 800000, "salary_currency": "CNY"},
    {"title": "数据平台后端工程师", "location": "杭州", "experience_years": 3,
     "salary_min": 350000, "salary_max": 620000, "salary_currency": "CNY"},
    {"title": "大模型推理优化工程师", "location": "深圳", "experience_years": 5,
     "salary_min": 500000, "salary_max": 900000, "salary_currency": "CNY"},
    {"title": "AI 算法工程师", "location": "北京", "experience_years": 4,
     "salary_min": 480000, "salary_max": 750000, "salary_currency": "CNY"},
    {"title": "前端工程师（React）", "location": "北京", "experience_years": 3,
     "salary_min": 320000, "salary_max": 500000, "salary_currency": "CNY"},
]


def test_the_english_backend_role_matches_chinese_backend_rows():
    out = filter_samples(_CHINESE_CORPUS, role="Backend Engineer", currency="CNY")
    assert len(out) >= 3
    assert all("后端" in r["title"] or "大模型" in r["title"] for r in out)


def test_the_chinese_role_still_matches_the_same_rows():
    out = filter_samples(_CHINESE_CORPUS, role="后端工程师", currency="CNY")
    assert len(out) >= 3


def test_the_ml_phrase_finds_the_algorithm_corpus():
    # The phrase, not the shredded words: "machine learning" -> 算法
    out = filter_samples(_CHINESE_CORPUS, role="machine learning engineer", currency="CNY")
    assert any("算法" in r["title"] for r in out)


def test_the_english_frontend_role_does_not_leak_backend_rows():
    out = filter_samples(_CHINESE_CORPUS, role="Frontend Engineer", currency="CNY")
    assert out and all("前端" in r["title"] for r in out)


def test_the_benchmark_answers_for_an_english_role_against_the_chinese_corpus():
    report = benchmark(_CHINESE_CORPUS, role="Backend Engineer", currency="CNY")
    assert report["sampleSize"] >= 3
    assert report["percentiles"]["p50"] is not None


def test_an_unknown_english_family_still_answers_zero_rows():
    # Honesty check: an English family no synonym covers must answer with zero rows,
    # not with an inflated match from overzealous expansion.
    out = filter_samples(_CHINESE_CORPUS, role="blockchain architect", currency="CNY")
    assert out == []

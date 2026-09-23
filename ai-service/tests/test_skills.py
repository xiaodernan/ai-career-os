"""Unit tests for the skill vocabulary / normalization layer."""

from app.core.skills import CATEGORY, category, extract_skills, normalize


def test_normalize_aliases_to_canonical():
    assert normalize("springboot") == "Spring Boot"
    assert normalize("k8s") == "Kubernetes"
    assert normalize("大模型") == "LLM"
    assert normalize("psql") == "PostgreSQL"
    assert normalize("  REDIS ") == "Redis"


def test_normalize_passes_through_unknown_and_empty():
    assert normalize("Foobarium") == "Foobarium"
    assert normalize("") == ""
    assert normalize(None) == ""


def test_category_lookup():
    assert category("mysql") == "data"
    assert category("LangChain") == "framework"
    assert category("Foobarium") == "other"


def test_extract_skills_mixed_language():
    text = ("Built services in Java and Spring Boot with MySQL and Redis; "
            "experimenting with RAG and 大模型 applications.")
    found = set(extract_skills(text))
    assert {"Java", "Spring Boot", "MySQL", "Redis", "RAG", "LLM"} <= found


def test_extract_skills_bounded_aliases_no_substring_false_positives():
    # "es" inside "resources" must NOT match Elasticsearch; "use" must not match "ts"
    assert extract_skills("managed cloud resources and reused dashboards") == []
    assert "Elasticsearch" in extract_skills("search powered by ES clusters")


def test_extract_skills_dedupes_and_sorts():
    found = extract_skills("Redis, redis and REDIS caching")
    assert found.count("Redis") == 1
    assert found == sorted(found, key=str.lower)


def test_extract_skills_sentence_final_period_not_swallowed():
    # "Kafka." at end of sentence must still match (boundary excludes '.')
    assert "Kafka" in extract_skills("Streamed orders with Kafka.")
    assert "Redis" in extract_skills("Cache with Redis. Warm-up via dumps.")
    assert "Next.js" in extract_skills("Rewrote the portal in Next.js.")


def test_every_category_value_is_known_shape():
    assert set(CATEGORY.values()) <= {
        "language", "framework", "library", "data", "cloud", "devops", "ai",
        "tool", "method", "cs_fundamentals", "soft", "other"}


def test_extract_skills_rejects_interior_substring_false_positives():
    # Regression: aliases used to match by plain substring, so English words whose
    # interior contained a short alias produced spurious skill tags.
    assert extract_skills("reduced storage costs by 30%") == []      # sto[rag]e
    assert extract_skills("highly interested in backend design") == []  # inte[rest]ed
    assert extract_skills("below average performance") == []          # ave[rag]e
    assert extract_skills("a strategic paragraph about caching") == []  # st[rag]egic
    assert extract_skills("the forest restore harvest") == []         # fo[rest]


def test_extract_skills_still_matches_whole_token_aliases():
    # same substrings DO count when they are standalone tokens
    assert "REST API" in extract_skills("used REST APIs daily")
    assert "RAG" in extract_skills("built a RAG pipeline")
    assert "Elasticsearch" in extract_skills("search powered by ES clusters")
    assert "Kubernetes" in extract_skills("deployed on k8s")


def test_extract_skills_cjk_aliases_match_without_surrounding_spaces():
    # boundary classes are ASCII-only, so CJK aliases glue to neighbouring Chinese
    assert "LLM" in extract_skills("熟悉大模型技术")
    assert "RAG" in extract_skills("检索增强生成方案")


def test_extract_skills_alias_dotted_names_respect_word_boundaries():
    assert "React" in extract_skills("rewrote in react.js")
    # jso[n] must not trigger the "js"→JavaScript alias
    assert "JavaScript" not in extract_skills("serialize to json only")


def test_extract_skills_outputs_only_normalize_fixed_points():
    # every returned skill must already be canonical: normalize(x) == x
    text = ("Java, Spring Boot, k8s, Docker, PostgreSQL, react.js, ES, "
            "大模型, Kafka and Redis")
    for skill in extract_skills(text):
        assert normalize(skill) == skill, skill
    # "K8s" is a CATEGORY key but folds to "Kubernetes"; a single mention must not
    # surface two entries for one concept
    assert extract_skills("deployed on k8s") == ["Kubernetes"]
    assert extract_skills("K8s and Kubernetes together") == ["Kubernetes"]

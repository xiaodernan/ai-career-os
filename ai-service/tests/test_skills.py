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

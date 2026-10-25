"""Query understanding must not hand the channels a shape they cannot use.

`understand` is the one place every retrieval channel reads from. The model is
asked for arrays and booleans; JSON sometimes answers with a bare string. Two
consequences were invisible rather than loud:

- `for e in "Kafka Spring"` yields its *characters*, so a string where an array
  was expected became `['K', 'a', 'f']` and the keyword channel went hunting for
  single letters -- retrieval quietly got worse, with no error anywhere;
- `bool("false")` is True, so a flag the model answered as a string read as the
  opposite of what it said.

These tests pin the coercion, because neither failure raises.
"""

import pytest

from app.rag import rewrite


def _patch(monkeypatch, payload):
    async def fake_ask_json(*a, **k):
        return payload

    monkeypatch.setattr(rewrite, "ask_json", fake_ask_json)


@pytest.mark.asyncio
async def test_a_bare_string_keyword_list_is_not_split_into_characters(monkeypatch):
    _patch(monkeypatch, {"rewritten": "kafka", "keywords": "Kafka Spring Boot"})
    u = await rewrite.understand("kafka experience")
    assert u["keywords"] == ["Kafka Spring Boot"], \
        "a string read character-by-character sends the keyword channel after letters"
    assert "K" not in u["keywords"]


@pytest.mark.asyncio
async def test_a_comma_separated_keyword_string_becomes_its_terms(monkeypatch):
    _patch(monkeypatch, {"rewritten": "kafka", "keywords": "Kafka, Spring Boot, RAG"})
    u = await rewrite.understand("kafka experience")
    assert u["keywords"] == ["Kafka", "Spring Boot", "RAG"]


@pytest.mark.asyncio
async def test_a_bare_string_expansion_is_one_phrase(monkeypatch):
    _patch(monkeypatch, {"rewritten": "kafka", "expansions": "streaming pipelines"})
    u = await rewrite.understand("kafka experience")
    assert u["expansions"] == ["streaming pipelines"]


@pytest.mark.asyncio
async def test_non_string_entries_are_dropped_and_the_limit_is_kept(monkeypatch):
    _patch(monkeypatch, {"rewritten": "kafka",
                         "keywords": ["Kafka", None, 7, "RAG", "Flink", "Go", "Java",
                                      "Redis", "K8s", "extra"]})
    u = await rewrite.understand("kafka experience")
    assert u["keywords"] == ["Kafka", "RAG", "Flink", "Go", "Java", "Redis", "K8s", "extra"]
    assert len(u["keywords"]) == 8


@pytest.mark.asyncio
async def test_a_non_string_rewritten_falls_back_to_the_raw_query(monkeypatch):
    # `rewritten` is the field every channel consumes; a list or number here used to
    # flow straight into the embedder and the trigram query.
    _patch(monkeypatch, {"rewritten": ["not", "a", "string"]})
    u = await rewrite.understand("kafka experience")
    assert u["rewritten"] == "kafka experience"


@pytest.mark.asyncio
async def test_a_blank_rewritten_falls_back_to_the_raw_query(monkeypatch):
    _patch(monkeypatch, {"rewritten": "   "})
    u = await rewrite.understand("kafka experience")
    assert u["rewritten"] == "kafka experience"


@pytest.mark.asyncio
async def test_the_string_false_flag_does_not_read_as_true(monkeypatch):
    _patch(monkeypatch, {"rewritten": "kafka", "needs_personal_evidence": "false"})
    u = await rewrite.understand("kafka experience")
    assert u["needs_personal_evidence"] is False


@pytest.mark.asyncio
async def test_a_real_false_stays_false_and_an_absent_flag_defaults_true(monkeypatch):
    _patch(monkeypatch, {"rewritten": "kafka", "needs_personal_evidence": False})
    assert (await rewrite.understand("q"))["needs_personal_evidence"] is False

    _patch(monkeypatch, {"rewritten": "kafka"})
    assert (await rewrite.understand("q"))["needs_personal_evidence"] is True


@pytest.mark.asyncio
async def test_a_failed_understanding_call_still_returns_the_raw_query(monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("provider down")

    monkeypatch.setattr(rewrite, "ask_json", boom)
    u = await rewrite.understand("kafka experience")
    assert u["rewritten"] == "kafka experience"
    assert u["keywords"] == [] and u["expansions"] == []
    assert u["intent"] == "other"

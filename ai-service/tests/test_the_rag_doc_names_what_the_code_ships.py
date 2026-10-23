"""docs/RAG.md's numbers and names are the code's, and its test pointers resolve.

RAG.md is the only document that explains the retrieval pipeline stage by stage, so it is
the one a reader trusts for the numbers: how many candidates each channel pulls, how long
a quote may be, which providers can embed, which modes the reranker runs in. Those are the
claims that rot quietly -- a `k=` moves and the prose still says 25, a provider is dropped
from the registry and the doc still offers it, a test is renamed and the pointer dangles.
None of it fails at runtime.

So the claims are read back out of the sources they describe: the per-channel `k` from
`rag/pipeline.py`, the quote cap from `to_evidence`, the embedding providers from
`providers/registry.py`, the rerank modes from `core/config.py`, the cover-letter kinds
from `features/cover_letter.py`, the published status steps from the `taskbus.publish`
calls, and every `tests/...::test_*` pointer from the test files it names. Two behaviours
are held as prose because they are decisions rather than constants: the keyword fanout
bound, and the retry that drops a guessed `kinds` filter which the code names
`kinds_filter_dropped`.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
AI = TESTS.parent
ROOT = AI.parent
DOC = ROOT / "docs" / "RAG.md"
PIPELINE = AI / "app" / "rag" / "pipeline.py"
REGISTRY = AI / "app" / "providers" / "registry.py"
CONFIG = AI / "app" / "core" / "config.py"
COVER_LETTER = AI / "app" / "features" / "cover_letter.py"


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def channel_ks() -> dict[str, int]:
    """channel -> the `k` pipeline.py asks it for."""
    out = {}
    for match in re.finditer(r"store\.(\w+_search)\([^)]*?k=(\d+)", read(PIPELINE), re.S):
        out[match.group(1)] = int(match.group(2))
    return out


def doc_bullets() -> list[str]:
    """RAG.md's bullets, with their wrapped continuation lines folded back in."""
    out: list[str] = []
    for line in read(DOC).split("\n"):
        if re.match(r"\s*-\s", line):
            out.append(line)
        elif re.match(r"\s{3,}\S", line) and out:
            out[-1] += " " + line.strip()
    return out


def documented_channels() -> dict[str, int]:
    """channel -> the `top N` the doc claims, read off its own channel bullets."""
    out = {}
    for bullet in doc_bullets():
        match = re.match(r"\s*-\s*`(\w+_search)`.*\(top (\d+)", bullet)
        if match:
            out[match.group(1)] = int(match.group(2))
    return out


def published_steps() -> set[str]:
    """Every status step the pipeline publishes over the task bus."""
    return set(re.findall(r'"step": "([a-z_]+)"', read(PIPELINE)))


def documented_steps() -> set[str]:
    text = read(DOC)
    match = re.search(r"`(understanding_query.*?reranking)`", text, re.S)
    assert match, "RAG.md no longer lists the streaming status steps it claims"
    return {step.strip() for step in match.group(1).split("→")}


def embedding_providers() -> set[str]:
    """The providers `get_embeddings` has a branch for."""
    return set(re.findall(r's\.embedding_provider == "(\w+)"', read(REGISTRY)))


def documented_providers() -> set[str]:
    text = read(DOC)
    match = re.search(r"get_embeddings`\):(.*?)(?:\n\n|$)", text, re.S)
    assert match, "RAG.md no longer names the embedding providers"
    return set(re.findall(r"`(\w+)`", match.group(1)))


def rerank_modes() -> set[str]:
    comment = re.search(r'rerank_mode: str = "\w+"\s*# ([^\n]+)', read(CONFIG))
    assert comment, "config.py no longer declares rerank_mode with its modes in a comment"
    return {mode.strip() for mode in comment.group(1).split("|")}


def documented_rerank_modes() -> set[str]:
    text = read(DOC)
    named = re.search(r"`RERANK_MODE=(\w+)`", text)
    skipped = re.search(r"`(\w+)` skips it", text)
    assert named and skipped, "RAG.md no longer names the rerank modes"
    return {named.group(1), skipped.group(1)}


def cover_letter_kinds() -> set[str]:
    match = re.search(r'kinds=\[([^\]]*)\]', read(COVER_LETTER))
    assert match, "cover_letter.py no longer asks for kinds"
    return {kind.strip().strip('"') for kind in match.group(1).split(",")}


def documented_cover_letter_kinds() -> set[str]:
    text = read(DOC)
    match = re.search(r"cover-letter generation retrieves `\[([^\]]*)\]`", text)
    assert match, "RAG.md no longer says which kinds cover-letter generation retrieves"
    return {kind.strip().strip('"') for kind in match.group(1).split(",")}


def doc_test_refs() -> list[tuple[str, str]]:
    """(test file or "", name prefix) for every test pointer the doc writes."""
    out = []
    for span in re.findall(r"`([^`]*test_[^`]*)`", read(DOC)):
        named = re.search(r"(test_\w+\.py)", span)
        where = named.group(1) if named else ""
        rest = span.replace(where, " ") if where else span
        out.extend((where, name) for name in re.findall(r"test_\w+", rest))
    return out


def test_every_channel_pulls_the_number_the_doc_claims():
    asked, claimed = channel_ks(), documented_channels()
    assert claimed, "RAG.md no longer states a top-N per channel"
    assert claimed == asked, (
        f"RAG.md claims {claimed} but pipeline.py asks {asked}")


def test_the_streaming_steps_the_doc_lists_are_the_ones_published():
    assert documented_steps() == published_steps(), (
        f"RAG.md lists {sorted(documented_steps())} but pipeline.py publishes "
        f"{sorted(published_steps())}")


def test_the_quote_cap_the_doc_claims_is_the_one_to_evidence_applies():
    body = read(PIPELINE)
    assert '"quote": (text if isinstance(text, str) else "")[:600],' in body, (
        "to_evidence no longer caps its quote at 600 characters")
    assert "600-char" in read(DOC), "RAG.md no longer claims a 600-char quote"


def test_the_embedding_providers_the_doc_offers_are_the_registrys():
    assert documented_providers() == embedding_providers(), (
        f"RAG.md offers {sorted(documented_providers())} but the registry branches on "
        f"{sorted(embedding_providers())}")


def test_the_rerank_modes_the_doc_names_are_the_ones_config_declares():
    assert documented_rerank_modes() == rerank_modes(), (
        f"RAG.md names {sorted(documented_rerank_modes())} but config declares "
        f"{sorted(rerank_modes())}")


def test_the_kinds_the_doc_attributes_to_cover_letters_are_the_ones_asked_for():
    assert documented_cover_letter_kinds() == cover_letter_kinds(), (
        f"RAG.md says cover-letter generation retrieves "
        f"{sorted(documented_cover_letter_kinds())} but cover_letter.py asks for "
        f"{sorted(cover_letter_kinds())}")


def test_every_test_the_doc_points_at_exists():
    problems = []
    for where, name in doc_test_refs():
        files = [TESTS / where] if where else sorted(TESTS.glob("test_*.py"))
        found = any(re.search(rf"^\s*(async )?def {name}", read(path), re.M)
                    for path in files if path.exists())
        if not found:
            problems.append(f"`{where}::{name}`" if where else f"`{name}`")
    assert problems == [], f"RAG.md points at tests that do not exist: {problems}"
    assert len(doc_test_refs()) >= 2, (
        f"only {len(doc_test_refs())} test pointers found; the doc has stopped citing its tests")


def test_the_doc_names_the_keyword_fanout_bound():
    """A bounded fan-out is a decision with a measured reason, not a constant to rediscover."""
    assert re.search(r"KEYWORD_FANOUT = \d+", read(PIPELINE)), (
        "pipeline.py no longer bounds its keyword fan-out")
    assert "KEYWORD_FANOUT" in read(DOC), (
        "RAG.md no longer names the fan-out bound, so the number of round trips the "
        "keyword channel costs is invisible to a reader of the pipeline")


def test_the_doc_names_the_retry_that_drops_a_guessed_kinds_filter():
    """The guess-and-retry is the difference between 13 of 15 golden cases and all of them."""
    assert "kinds_filter_dropped" in read(PIPELINE), (
        "pipeline.py no longer traces the dropped-kinds recovery")
    assert "kinds_filter_dropped" in read(DOC), (
        "RAG.md no longer names the `kinds_filter_dropped` recovery, so a reader believes "
        "the rewrite step's `filters.kinds` is authoritative")

"""The eval's ground truth must describe the corpus retrieval is actually allowed to return.

A retrieval metric is a ratio between two readings of one corpus: the chunks the system
returned, and the chunks that were worth returning. The runner built the second reading
out of a different set of rules than the product builds the first. `rag/store.py` gives
every channel the same two restrictions -- `d.status = 'ready'`, and a source-kind filter
when the request names kinds (`_apply_scoping`, whose own docstring says an unfiltered
channel "injects out-of-scope chunks") -- while `run_eval._relevant_ids` read
`document_chunks` bare: no document join, no status, no kind. A chunk of a document that
failed or is still indexing was therefore counted as a miss the run could never recover,
and one of the two claims the golden set makes went further:

* `EvalCase.kinds` is documented as "the metadata filter under test" and gs-03 and gs-05
  set it, but no code read the field. `run()` called `retrieve()` without `kinds`, so the
  filter was tested by nothing, and the ground truth ignored it too -- those two cases
  scored against the whole corpus, which is what gs-04 already does. Their declared
  difference was decoration.

This gate pins the two sides to each other, in the direction that cannot be satisfied by
deleting a claim: every restriction production's scoping applies must appear in the
ground-truth query, and the query must be the one spelling the scoping writes (read out
of `store._apply_scoping`, not copied). Two more clauses came from the same reading:
joining `documents` puts a second `user_id` in scope, so a predicate that stops
qualifying the column is a Postgres ambiguity error rather than a filter -- the fact is
derived from the migration that declares both columns; and the keywords still have to
hang together as one OR group, because an extra restriction is the easiest way to turn
"matches any keyword" into "matches every keyword" and quietly shrink the denominator.

Two directions are pinned because one alone passes on a runner that scopes everything or
nothing: a case without `kinds` must still get the status restriction and must NOT get a
kind filter, and a case with `kinds` must get the filter on both sides of the metric.
"""

import re
from pathlib import Path

import pytest

from app.core import db
from app.eval import run_eval as ev
from app.eval.dataset import GOLDEN_SET, EvalCase
from app.rag import store

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
MIGRATION = ROOT / "backend" / "src" / "main" / "resources" / "db" / "migration" / "V1__init_schema.sql"
RUN_EVAL = ROOT / "ai-service" / "app" / "eval" / "run_eval.py"
REWRITE = ROOT / "ai-service" / "app" / "rag" / "rewrite.py"

MIN_GOLDEN_CASES = 10
MIN_CASES_WITH_KINDS = 1


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


@pytest.fixture
def queries(monkeypatch):
    """Capture every (sql, args) the ground-truth reader sends, without a database."""
    calls: list[tuple[str, tuple]] = []

    async def fetch(sql, *args):
        calls.append((sql, args))
        return []

    monkeypatch.setattr(db, "fetch", fetch)
    return calls


async def capture(case: EvalCase, queries) -> tuple[str, tuple]:
    queries.clear()
    await ev._relevant_ids("11111111-1111-1111-1111-111111111111", case)
    assert len(queries) == 1, f"one case, {len(queries)} ground-truth queries"
    sql, args = queries[0]
    return re.sub(r"\s+", " ", sql).strip(), args


def production_kind_term() -> str:
    """The kind restriction `store._apply_scoping` writes, read from the function itself."""
    where: list[str] = []
    args: list[object] = []
    store._apply_scoping(where, args, ["resume"], None)
    return bindless(next(term for term in where if "ANY" in term))


def bindless(term: str) -> str:
    """Drop the placeholder number: both sides renumber as terms are appended."""
    return re.sub(r"\$\d+", "$N", term)


def where_terms(sql: str) -> list[str]:
    """Top-level restriction terms. Safe to split on AND because the keyword group,
    the only parenthesised part, holds nothing but ORs."""
    return [term.strip() for term in sql.split(" WHERE ", 1)[1].split(" AND ")]


def test_a_case_that_declares_a_kind_filter_passes_it_to_the_retrieval():
    src = read(RUN_EVAL)
    start = re.search(r"await retrieve\(", src)
    assert start, "run_eval no longer calls retrieve(); this gate's claim needs a re-read"
    depth, end = 0, src.index("(", start.start() + len("await retrieve") - 1)
    for i in range(end, len(src)):
        depth += src[i] == "("
        depth -= src[i] == ")"
        if depth == 0:
            break
    call = src[end:i + 1]
    assert re.search(r"kinds\s*=\s*case\.kinds", call), (
        f"`EvalCase.kinds` is declared as a filter under test but the runner calls "
        f"retrieve() with {call} -- no retrieval in the eval is scoped by it, so gs-03 "
        f"and gs-05 measure the same unfiltered corpus as gs-04"
    )


async def test_the_scoped_case_is_scored_with_productions_own_kind_term(queries):
    sql, args = await capture(
        EvalCase(id="c", query="q", keywords=["kafka"], kinds=["resume"]), queries)
    scoped = [term for term in where_terms(sql) if "ANY" in term]
    assert len(scoped) == 1, f"expected one kind restriction, got {scoped} in {sql}"
    assert bindless(scoped[0]) == production_kind_term(), (
        f"the ground truth restricts {scoped[0]!r} while production's scoping writes "
        f"{production_kind_term()!r} -- two spellings of one filter are two filters, and "
        "the one that drifts makes the metric compare different corpora"
    )
    assert args[-1] == ["resume"], f"the declared kinds never reach the query: {args}"


async def test_every_ground_truth_query_is_limited_to_ready_documents(queries):
    for case in (EvalCase(id="a", query="q", keywords=["kafka"]),
                 EvalCase(id="b", query="q", keywords=["kafka"], kinds=["resume"])):
        sql, _ = await capture(case, queries)
        assert "d.status = 'ready'" in sql, (
            f"{case.id}: ground truth counts chunks of documents the channels will not "
            f"serve ({sql}) -- a pending or failed document makes its chunks permanent "
            "misses, and recall can never reach the value the corpus supports"
        )
        assert re.search(r"JOIN documents d ON d\.id = c\.document_id", sql), (
            f"{case.id}: a status restriction needs the document; the query reads {sql}"
        )


async def test_a_case_without_a_declared_filter_stays_unfiltered(queries):
    sql, args = await capture(EvalCase(id="c", query="q", keywords=["kafka"]), queries)
    assert "ANY" not in sql, f"an unconditional case became scoped: {sql}"
    assert list(args) == ["11111111-1111-1111-1111-111111111111", "%kafka%"], (
        f"the kind term is bound for a case that declares none: {args}"
    )


async def test_the_join_leaves_no_ambiguous_column(queries):
    schema = read(MIGRATION)
    tables = {}
    for name in ("documents", "document_chunks"):
        body = re.search(rf"CREATE TABLE {name} \((.*?)\n\);", schema, re.S)
        assert body, f"V1 migration no longer declares {name}"
        tables[name] = {line.split()[0] for line in body.group(1).splitlines()
                        if line.strip() and not line.strip().startswith("--")}
    shared = tables["documents"] & tables["document_chunks"]
    assert "user_id" in shared, (
        f"the clause below was written for a schema where {shared} are shared; if the "
        "migration changed, re-derive which columns need qualifying"
    )
    sql, _ = await capture(
        EvalCase(id="c", query="q", keywords=["kafka"], kinds=["resume"]), queries)
    bare = [term for term in where_terms(sql)
            if re.match(r"(?:%s)\s*=" % "|".join(sorted(shared, key=len, reverse=True)), term)]
    assert bare == [], (
        f"{bare} are predicates with no table qualifier on a query that joins documents -- "
        "Postgres fails them with 'column reference is ambiguous', so the eval would "
        "report an empty corpus for every case"
    )


async def test_the_keywords_stay_one_or_group(queries):
    keywords = ["kafka", "redis", "索引"]
    sql, args = await capture(
        EvalCase(id="c", query="q", keywords=keywords, kinds=["resume"]), queries)
    group = re.search(r"\(([^()]*(?:ILIKE[^()]*)+)\)", sql)
    assert group, f"the keyword terms are not one parenthesised group: {sql}"
    assert sql.count("ILIKE") == len(keywords), (
        f"{len(keywords)} keywords, {sql.count('ILIKE')} matchers bound: {sql}"
    )
    assert group.group(1).count(" OR ") == group.group(1).count("ILIKE") - 1, (
        f"a case matches ANY keyword; inside {group.group(1)!r} they are combined "
        "otherwise, which shrinks the ground truth to chunks carrying every term and "
        "reports that as a better recall"
    )
    assert " AND " not in group.group(1), f"the group escaped its parentheses: {sql}"
    assert sql.count("ILIKE") == sql.count("ESCAPE '!'"), (
        f"a LIKE matcher without its escape hands the keyword's own '%' or '_' to the "
        f"database as an operator: {sql}"
    )


def test_every_declared_kind_is_a_spelling_the_filter_can_match():
    declared = [kind for case in GOLDEN_SET for kind in (case.kinds or [])]
    assert len(declared) >= MIN_CASES_WITH_KINDS, (
        "no golden case declares `kinds` any more -- the field's reader above is then "
        "vacuous, and so is the two cases' claim to test a metadata filter"
    )
    vocabulary = re.search(r"<subset of ([a-z_|]+),", read(REWRITE))
    assert vocabulary, "rewrite.py no longer declares the source-kind vocabulary"
    legal = set(vocabulary.group(1).split("|"))
    unknown = sorted(set(declared) - legal)
    assert unknown == [], (
        f"gs- cases filter on {unknown}, which no `knowledge_sources.kind` row can "
        f"carry (the vocabulary is {sorted(legal)}): the scoped ground truth comes back "
        "empty, the case skips as `no_ground_truth`, and a typo reads as a corpus gap"
    )


def test_the_golden_set_is_big_enough_for_the_scoring_to_mean_something():
    with_kinds = [case.id for case in GOLDEN_SET if case.kinds]
    assert len(GOLDEN_SET) >= MIN_GOLDEN_CASES, (
        f"only {len(GOLDEN_SET)} cases: the ratios above are read off a set too small "
        "for one case's scoping to be distinguishable from an accident"
    )
    assert len(with_kinds) >= MIN_CASES_WITH_KINDS, f"none of {with_kinds}"
    assert len({case.id for case in GOLDEN_SET}) == len(GOLDEN_SET), "duplicate case ids"

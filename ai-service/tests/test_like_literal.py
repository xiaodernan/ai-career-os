"""User text is data, never a LIKE pattern — the ai-service half of the same defect.

Every one of these queries builds a matcher as `'%'||<term>||'%'` or `f"%{term}%"`, which
hands the term's own metacharacters to LIKE as *operators*:
  * `%`  -> the filter stops filtering ("100%" matches every job)
  * `_`  -> matches any single char ("a_b" also matches "axb", and a skill named
            "ci_cd" matches "ci/cd")
  * `\\` -> is LIKE's implicit escape char, so a term containing one can no longer
            match its own text ("back\\slash" degrades to '%backslash%' -> 0 rows)

The fix is a single escaper (escape char `!`, chosen because it is not special under
`standard_conforming_strings`) plus `ESCAPE '!'` at every call site. These tests pin the
invariant per channel so a new search path cannot reintroduce the raw form.
"""

import re

import app.core.db as db
from app.agents.tools import _search_params, get_company
from app.eval.run_eval import EvalCase, _relevant_ids
from app.rag import store

LIKE_ESCAPES = ("%", "_")   # the chars a term may never pass through as operators

# ---------------- the escaper itself ----------------


def test_like_contains_neutralises_every_wildcard():
    assert db.like_contains("java") == "%java%"
    assert db.like_contains("100% remote") == "%100!% remote%"
    assert db.like_contains("a_b") == "%a!_b%"
    assert db.like_contains("x!y") == "%x!!y%"
    # backslash must survive untouched: '!' is the escape char now, so it carries no power
    assert db.like_contains("back\\slash") == "%back\\slash%"
    assert db.like_contains("") == "%%"


def test_like_contains_escapes_the_escape_char_first():
    # Doubling '!' last would re-escape the escapes just inserted for % and _.
    assert db.like_contains("!%") == "%!!!%%"
    assert db.like_contains("%!") == "%!%!!%"


def test_no_operator_survives_the_escaping_of_any_term():
    # Property check over the pattern body: every remaining metacharacter must be
    # introduced by '!', which is what makes the pattern match the term itself.
    for term in ["100%", "a_b", "!x", "back\\slash", "%_%", "plain", ""]:
        body = db.like_contains(term)[1:-1]
        i = 0
        while i < len(body):
            ch = body[i]
            if ch == "!":
                assert i + 1 < len(body), f"dangling escape char for {term!r}"
                assert body[i + 1] in "!%_", f"escape char wastes on {body[i + 1]!r}"
                i += 2
                continue
            assert ch not in ("%", "_"), f"{ch!r} left as an operator for {term!r}"
            i += 1


# ---------------- agents/tools._search_params ----------------


def _indices(sql: str) -> list[int]:
    return [int(n) for n in re.findall(r"\$(\d+)", sql)]


def test_search_params_binds_escaped_patterns_for_every_text_filter():
    where, args = _search_params(query="a_b", location="50%", company="x!y",
                                 remote="remote", skills=["Go"], min_salary=10, limit=5)
    sql = " AND ".join(where)
    assert "'%'||$" not in sql, "raw term still used as a LIKE pattern"
    assert sql.count("ILIKE") == sql.count("ESCAPE '!'"), "an ILIKE is missing its ESCAPE"
    assert "%a!_b%" in args
    assert "%50!%%" in args
    assert "%x!!y%" in args


def test_search_params_keeps_the_raw_term_for_the_tsquery_side():
    where, args = _search_params(query="100%", limit=5)
    sql = " AND ".join(where)
    assert "plainto_tsquery('simple', $1)" in sql
    assert args[0] == "100%", "tsquery wants the text, not an escaped pattern"
    assert args.count("100%") == 1, "the pattern arg must be a separate bind"


def test_search_params_keeps_every_placeholder_inside_the_bound_args():
    # Each text filter now costs its own bind, so an index shift here would silently
    # compare a clause against the wrong value (or collide with the LIMIT arg).
    for kwargs in ({"query": "q", "skills": ["s"], "location": "l", "remote": "r",
                    "company": "c", "min_salary": 1, "limit": 2},
                  {"query": "q"},
                  {"location": "l", "company": "c"},
                  {"skills": ["s"], "min_salary": 5},
                  {"limit": 3}):
        where, args = _search_params(**kwargs)
        used = sorted(set(_indices(" AND ".join(where))))
        assert used == list(range(min(used), max(used) + 1)) if used else True, \
            f"gap in placeholder numbering: {used}"
        assert all(1 <= i <= len(args) - 1 for i in used), \
            f"{used} points outside the {len(args) - 1} filter args (last is LIMIT)"


def test_search_params_every_referenced_index_is_bound_and_last_arg_is_the_limit():
    where, args = _search_params(query="q", skills=["s"], location="l", remote="r",
                                 company="c", min_salary=1, limit=2)
    sql = " AND ".join(where)
    used = sorted(set(_indices(sql)))
    assert used == list(range(1, len(args))), f"{used} must be exactly the non-LIMIT binds"
    assert args[-1] == 2


async def test_get_company_matches_the_name_as_a_literal(monkeypatch):
    calls = []

    async def fetchrow(sql, *args):
        calls.append((sql, args))
        return None

    monkeypatch.setattr(db, "fetchrow", fetchrow)
    out = await get_company("u1", name="Acme_Corp")
    sql, args = calls[0]
    assert out == {"error": "company not found"}
    assert "ESCAPE '!'" in sql
    assert list(args) == ["%Acme!_Corp%"], (
        "an unescaped '_' here lets a lookup for Acme_Corp bind the wrong company")


async def test_get_company_without_a_name_asks_the_database_nothing(monkeypatch):
    # `ILIKE '%%'` is not a lookup, it is "any row": an argument-free tool call would
    # return some unrelated company as if it were the one the user asked about.
    async def fetchrow(sql, *args):  # pragma: no cover - must not run
        raise AssertionError(f"unscoped company lookup reached the DB: {sql}")

    monkeypatch.setattr(db, "fetchrow", fetchrow)
    assert await get_company("u1") == {"error": "company lookup needs company_id or name"}
    assert await get_company("u1", name="   ") == {
        "error": "company lookup needs company_id or name"}


# ---------------- rag/store skill metadata filter ----------------


async def test_vector_search_escapes_the_skill_in_its_json_array_probe(monkeypatch):
    calls = []

    async def fetch(sql, *args):
        calls.append((sql, args))
        return []

    monkeypatch.setattr(db, "fetch", fetch)
    await store.vector_search("u1", [0.0, 0.0], skill="ci_cd")
    sql, args = calls[0]
    assert "ESCAPE '!'" in sql
    # the JSON quotes stay structural; only the skill's own '_' is neutralised
    assert '%"ci!_cd"%' in args, f"skill wildcard not neutralised: {args}"


# ---------------- eval ground truth ----------------


async def test_relevant_ids_does_not_let_one_keyword_match_every_chunk(monkeypatch):
    calls = []

    async def fetch(sql, *args):
        calls.append((sql, args))
        return []

    monkeypatch.setattr(db, "fetch", fetch)
    case = EvalCase(id="c", query="q", keywords=["kafka", "100%", "a_b"])
    await _relevant_ids("u1", case)
    sql, args = calls[0]
    assert sql.count("ILIKE") == sql.count("ESCAPE '!'")
    assert list(args[1:]) == ["%kafka%", "%100!%%", "%a!_b%"], (
        "a bare '%' keyword would label every chunk relevant and collapse the "
        "recall denominator this metric is measured against")


async def test_relevant_ids_without_keywords_binds_nothing(monkeypatch):
    async def fetch(sql, *args):  # pragma: no cover - must not run
        raise AssertionError("no keywords -> no ground-truth query")

    monkeypatch.setattr(db, "fetch", fetch)
    assert await _relevant_ids("u1", EvalCase(id="c", query="q", keywords=[])) == set()

"""The additive import plan matches content in one pass, not a quadratic rescan (Epic 161).

`_plan_additive` pairs a bundle's re-ingested rows (resumes / knowledge / memories)
against the rows already in the workspace **by content**, one-to-one: a bundle
carrying two copies of a resume restores both, and a restored row is found again
despite the ingestion pipeline minting it a new id. The original implementation
kept the unmatched targets in a list and, for every incoming row, walked that list
recomputing `_content_key(section, ex)` -- a tuple that embeds the row's *entire
plaintext* -- and `pop(index)`-ed on a hit. That is O(n·m) key constructions plus
list shifting over the reader's whole accumulated data (resumes and knowledge have
no row cap), so a full restore of a long-used workspace redoes the same expensive
hashing again and again.

This file pins the fix as a **differential contract**: a reference copy of the old
quadratic matcher lives here, and for varied inputs (duplicates, misses, memories
that switch update) the shipped `_plan_additive` must emit *exactly* the same ops.
A second assertion counts `_content_key` calls and requires the shipped matcher to
stay linear in the two list lengths -- the complexity improvement, measured at the
seam rather than guessed from a benchmark. No production behaviour is widened; the
one-to-one promise the restore panel already makes is unchanged.

Pure and offline: `_plan_additive` does no I/O, so these need no provider, key or
fixture.
"""

from __future__ import annotations

import pytest

from app.features import import_plan as pl


def _reference_additive(section: str, items: list[dict],
                        existing_items: list[dict]) -> list[dict]:
    """The pre-indexing matcher, kept verbatim as the behavioural oracle.

    Not shipped: it exists so a future edit to the real matcher is checked against
    the exact semantics it replaced, one-to-one consumption included.
    """
    remaining = list(existing_items)
    ops: list[dict] = []
    for it in items:
        key = pl._content_key(section, it)
        known = None
        for index, ex in enumerate(remaining):
            if pl._content_key(section, ex) == key:
                known = remaining.pop(index)
                break
        if known is None:
            kind = "create"
        elif section == "memories" and \
                pl._identity_hash(it, section) != pl._identity_hash(known, section):
            kind = "update"
        else:
            kind = "skip"
        ops.append(pl._op(kind, it))
    return ops


def _resume(title: str, plain: str | None = None, iid: str = "x") -> dict:
    return {"id": iid, "resume_title": title, "plaintext": plain if plain is not None else title}


def _memory(key: str, content: str, iid: str = "m") -> dict:
    return {"id": iid, "kind": "preference", "key": key, "content": content}


# Each case is (section, items, existing_items). They cover: empty target, exact
# re-import, duplicates that must restore twice, misses, order reversal, and a
# memory whose content changed (the one section where a match can be an update).
_CASES = [
    ("resumes", [], []),
    ("resumes", [_resume("A")], []),
    ("resumes", [], [_resume("A")]),
    ("resumes", [_resume("A")], [_resume("A")]),
    ("resumes", [_resume("A"), _resume("A", iid="copy")], [_resume("A")]),
    ("resumes", [_resume("A"), _resume("B"), _resume("C")],
     [_resume("C"), _resume("A"), _resume("D")]),
    ("resumes", [_resume("A", plain="v2"), _resume("A", iid="copy")],
     [_resume("A", plain="v1")]),
    ("knowledge", [{"id": "k", "title": "Doc", "text_excerpt": "body"}],
     [{"id": "old", "title": "Doc", "text_excerpt": "body"}]),
    ("memories", [_memory("k1", "prefers remote")], [_memory("k1", "prefers remote")]),
    ("memories", [_memory("k1", "prefers on-site")], [_memory("k1", "prefers remote")]),
    ("memories", [_memory("k1", "a"), _memory("k2", "b")],
     [_memory("k2", "b"), _memory("k3", "c")]),
]


@pytest.mark.parametrize("section,items,existing", _CASES)
def test_the_indexed_matcher_is_the_quadratic_matchers_exact_answer(section, items, existing):
    """Zero behavioural drift: the new matcher emits the old one's ops, in order."""
    assert pl._plan_additive(section, items, existing) == \
        _reference_additive(section, items, existing)


def test_the_matcher_constructs_content_keys_linearly_not_quadratically(monkeypatch):
    """The real improvement: key construction is O(n+m), not O(n·m).

    A spy counts `_content_key` calls. The indexed matcher builds one key per
    existing row (its index) and one per incoming row; it never rebuilds an
    existing row's key while scanning. With 40 incoming and 40 existing rows the
    old matcher would build up to 40·40 existing-side keys; the bound below admits
    only n+m, and the differential test above proves the answers are identical.
    """
    n = m = 40
    # Reverse order on purpose: with the old list matcher every incoming row
    # finds its match only at the *tail* of `remaining`, so it rebuilds m keys
    # per incoming row. A same-order input would hit on the first comparison and
    # hide the quadratic cost -- which is exactly why the inputs are reversed.
    items = [_resume(f"r{i}", iid=f"b{i}") for i in range(n)]
    existing = [_resume(f"r{i}", iid=f"e{i}") for i in reversed(range(m))]

    real_key = pl._content_key
    calls = {"n": 0}

    def spy(section, item):
        calls["n"] += 1
        return real_key(section, item)

    monkeypatch.setattr(pl, "_content_key", spy)
    ops = pl._plan_additive("resumes", items, existing)

    # Sanity: the matcher actually ran over the whole input and matched all rows.
    assert len(ops) == n
    assert [o["op"] for o in ops] == ["skip"] * n
    # Linear bound: one key per incoming + one per existing row, not a product.
    # The old matcher builds ~n·m/2 keys here (~820); the indexed one builds n+m (80).
    assert calls["n"] <= n + m, (
        f"_content_key was called {calls['n']} times for {n} incoming / {m} existing rows; "
        "the indexed matcher must not rebuild an existing row's key per incoming row")


def test_duplicate_existing_rows_are_consumed_once_each_in_order():
    """One-to-one on the target side too: two identical existing resumes satisfy
    two identical incoming ones, then a third incoming is a create. The index is a
    queue, not a set -- collapsing it to a set would silently skip the second copy.
    """
    items = [_resume("A", iid=f"b{i}") for i in range(3)]
    existing = [_resume("A", iid=f"e{i}") for i in range(2)]
    ops = pl._plan_additive("resumes", items, existing)
    assert [o["op"] for o in ops] == ["skip", "skip", "create"]

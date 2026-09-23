"""Every read of document_chunks must be tenant-scoped, and un-skippable.

document_chunks holds one user's uploaded resumes, projects and JD text side by side in
one table. The retrieval endpoints take ids and filters straight from the request body,
so the `user_id` predicate is the only thing between an enumerating caller and another
tenant's documents — which makes a scope filter that an omitted argument turns off the
most dangerous shape in the service: it works, it returns rows, and it leaks.
"""

import pytest

import app.core.db as db
from app.rag import store

USER = "11111111-1111-1111-1111-111111111111"
OTHER = "22222222-2222-2222-2222-222222222222"


class SqlCapture:
    def __init__(self):
        self.calls = []

    async def __call__(self, sql, *args):
        self.calls.append((sql, args))
        return []


async def test_get_chunks_scopes_by_tenant_without_a_bypass(monkeypatch):
    cap = SqlCapture()
    monkeypatch.setattr(db, "fetch", cap)
    await store.get_chunks([OTHER], user_id=USER)

    sql, args = cap.calls[0]
    assert "c.user_id = $2::uuid" in sql
    assert "IS NULL OR" not in sql.upper(), (
        "a nullable argument that removes the tenant filter is a cross-tenant read "
        "one forgotten keyword argument away"
    )
    assert args[1] == USER, "the tenant must be bound, not interpolated into the SQL"


async def test_omitting_the_tenant_is_a_type_error_not_an_unscoped_read(monkeypatch):
    cap = SqlCapture()
    monkeypatch.setattr(db, "fetch", cap)

    with pytest.raises(TypeError):
        await store.get_chunks([OTHER])

    assert cap.calls == [], "the query must never reach the database without a tenant"


async def test_every_retrieval_channel_binds_the_viewer(monkeypatch):
    """A new channel that forgets the scope must fail this, not review."""
    cap = SqlCapture()
    monkeypatch.setattr(db, "fetch", cap)

    await store.vector_search(USER, [0.1, 0.2], k=5)
    await store.keyword_search(USER, "kafka", k=5)
    await store.trigram_search(USER, "kafka", k=5)
    await store.get_chunks([OTHER], user_id=USER)

    assert len(cap.calls) == 4
    for sql, args in cap.calls:
        assert "user_id" in sql, "channel has no tenant predicate at all"
        assert USER in args, f"tenant never bound: {sql[:60]}"


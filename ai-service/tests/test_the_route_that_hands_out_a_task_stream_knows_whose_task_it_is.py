"""`GET /internal/stream/{task_id}` takes the task id out of the URL the browser typed.

Nothing in this product ever handed one user another user's task id, so the hole was quiet -- but
the backend relay (`SseRelayService.consume`) forwards `X-User-Id` from the JWT it verified, and
`require_internal` puts that id in `Ctx`, and then the route looked only at whether the task
*existed*. `docs/architecture.md` said otherwise: "auth verified at backend, task ownership
checked". The check did not exist. Probing the two task routes with a `Ctx` for a different user
returned the owner's state -- `state()["last"]` is the whole payload of the last frame, so a
copilot turn's text -- and an `EventSourceResponse` that replays every frame the task published.
A guessed UUID is the only thing that was standing in the way.

So this file runs the routes instead of reading them: three of them (the state read, the stream,
and the `/internal/stream/{task_id}` alias the relay actually calls -- `test_internal_contract.py`
pins that the Java client builds exactly that spelling, which is why the alias is the leg that
matters and not a duplicate), each asked twice: once as the owner, once as somebody else. The
refusal has to be indistinguishable from "no such task", because a 403 would confirm which UUIDs
are somebody's.

Two legs keep the fix from being a door that only locks for visitors. Every task the app makes has
to record the caller who made it -- read off the call sites, not assumed -- because a task with no
owner is refused here, and if the producers stopped recording ids that policy would silently
starve the product instead of protecting it. And the state route still answers with the four fields
it answered before: the fix belongs in a decision, not in a wider response body.
"""

import asyncio
import re
from pathlib import Path

from fastapi import HTTPException

from app.api import tasks
from app.core import taskbus
from app.core.deps import Ctx

APP = Path(__file__).resolve().parents[1] / "app"
RELAY = (Path(__file__).resolve().parents[2] / "backend" / "src" / "main" / "java"
         / "com" / "careeros" / "ai" / "SseRelayService.java")

OWNER = "11111111-1111-1111-1111-111111111111"
STRANGER = "22222222-2222-2222-2222-222222222222"
NO_SUCH_TASK = "33333333-3333-3333-3333-333333333333"

MINIMUM_TASK_SITES = 3


def make_task(user_id: str | None = OWNER) -> str:
    task_id = taskbus.new_task("agent_chat", user_id)
    taskbus.publish(task_id, "token", {"text": "the owner's answer"})
    taskbus.finish(task_id, True, {"answer": "the owner's result"})
    return task_id


def refused(callback, task_id: str, user_id: str):
    """Call a route as `user_id`; return the HTTPException it raises, or None when it answers."""
    try:
        asyncio.run(callback(task_id, Ctx(user_id=user_id)))
    except HTTPException as exc:
        return exc
    return None


def test_a_caller_who_did_not_make_the_task_gets_the_answer_a_task_never_made_gets():
    task_id = make_task()
    for route in (tasks.task_state, tasks.task_stream):
        foreign = refused(route, task_id, STRANGER)
        missing = refused(route, NO_SUCH_TASK, STRANGER)
        assert foreign is not None, (
            f"{route.__name__} answered {STRANGER} for a task owned by {OWNER}: the stream, "
            "including every frame already published, went out with no owner check")
        assert missing is not None and missing.status_code == 404
        assert foreign.status_code == missing.status_code and foreign.detail == missing.detail, (
            f"{route.__name__} distinguishes a foreign task ({foreign.status_code} "
            f"{foreign.detail!r}) from an absent one ({missing.status_code} "
            f"{missing.detail!r}): that difference tells a caller which UUIDs belong to somebody, "
            "which is the thing a guessing attack needs")


def frames_of(response) -> list[str]:
    async def collect():
        return [item["event"] async for item in response.body_iterator]

    return asyncio.run(collect())


def test_the_owner_still_reads_their_state_and_their_stream():
    task_id = make_task()
    assert refused(tasks.task_state, task_id, OWNER) is None, (
        "the owner was refused: a check that refuses everyone protects nothing and breaks the "
        "product at the same time")
    state = asyncio.run(tasks.task_state(task_id, Ctx(user_id=OWNER)))
    assert state["kind"] == "agent_chat" and state["done"] is True

    stream = asyncio.run(tasks.task_stream(task_id, Ctx(user_id=OWNER)))
    frames = frames_of(stream)
    assert frames == ["token", "done"], (
        f"{frames}: the owner's own stream has to replay the frames their task published -- the "
        "refusal above is only a guard if the honest read still reaches them")


def test_the_spelling_the_relay_actually_calls_has_the_same_door():
    """The alias is not a second copy of the route; it is the copy the product calls."""
    relay = RELAY.read_text(encoding="utf-8")
    built = re.search(r'"/internal/stream/"\s*\+\s*taskId', relay)
    assert built, (f"{RELAY.name} no longer builds `/internal/stream/<taskId>`, so this leg is "
                   "guarding a path nothing calls -- and the pin in test_internal_contract.py "
                   "needs re-reading, not this test")
    task_id = make_task()
    assert refused(tasks.task_stream_alias, task_id, STRANGER) is not None, (
        "the alias answers a stranger: the relay calls this spelling, so the check on the other "
        "route would be guarding a door nobody walks through")
    assert refused(tasks.task_stream_alias, task_id, OWNER) is None


def test_a_task_that_recorded_no_owner_is_nobodys():
    """Fail closed: an ownerless task is the shape a producer bug leaves behind."""
    task_id = make_task(user_id=None)
    assert refused(tasks.task_state, task_id, OWNER) is not None
    assert refused(tasks.task_stream, task_id, OWNER) is not None


def test_every_task_the_app_makes_records_the_caller_it_belongs_to():
    """The refusing policy is only safe while every producer passes a user id -- censused, not trusted.

    Reading the call sites is what makes the fail-closed leg above a guard rather than a time
    bomb: a `new_task(kind)` that forgets the second argument would create a stream no caller can
    ever open, and that is a bug this census names instead of a bug the browser finds.
    """
    sites = []
    for source in sorted(APP.rglob("*.py")):
        text = source.read_text(encoding="utf-8")
        for match in re.finditer(r"taskbus\.new_task\(", text):
            sites.append((source.name, text[:match.start()].count("\n") + 1,
                          _second_argument(text[match.end():])))
    assert len(sites) >= MINIMUM_TASK_SITES, (
        f"only {len(sites)} `taskbus.new_task(` call sites found under app/: the producers "
        "changed shape and this census is reading nothing")
    unowned = [f"{name}:{line}" for name, line, second in sites if second is None]
    assert unowned == [], (f"{unowned}: a task made without a user id can never be opened again, "
                           "because the routes refuse a task whose owner does not match -- pass "
                           "the caller at the call site")
    hardcoded = [f"{name}:{line} -> {second}" for name, line, second in sites
                 if not re.search(r"(ctx|user)[._]id", second or "")]
    assert hardcoded == [], (f"{hardcoded}: the owner recorded for a task is not read from the "
                             "caller in front of the endpoint -- a literal or a borrowed id makes "
                             "the refusal a lock that opens for the wrong person")


def test_the_refusal_does_not_widen_what_the_state_route_answers():
    task_id = make_task()
    answered = asyncio.run(tasks.task_state(task_id, Ctx(user_id=OWNER)))
    assert set(answered) == {"kind", "done", "events", "last"}, (
        f"{sorted(answered)}: `taskbus.state()` is the body this route answers with, and the "
        "owner belongs in a decision (`taskbus.owner`), not in the payload a caller receives")


def _second_argument(text: str) -> str | None:
    """The argument after the first comma at depth one, or None when the call has only one.

    A `[^)]*` scan goes blind the moment an argument holds a call, and an argument list is exactly
    where that happens, so this walks the parentheses.
    """
    depth, index = 1, 0
    while index < len(text):
        char = text[index]
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
            if depth == 0:
                break
        if depth == 1 and char == ",":
            rest = text[index + 1:]
            end = _first_top_level_split(rest)
            return rest[:end].strip() or None
        index += 1
    return None


def _first_top_level_split(text: str) -> int:
    depth = 0
    for index, char in enumerate(text):
        if char in "([{":
            depth += 1
        elif char in ")]}":
            if depth == 0:
                return index
            depth -= 1
        elif char == "," and depth == 0:
            return index
    return len(text)

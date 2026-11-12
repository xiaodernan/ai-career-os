"""A long-lived service cannot accumulate one task entry per task forever.

Epic 131 mirrored every task's frame feed into a Redis stream and kept an
in-process dictionary of tasks. Both grow by one entry per task and neither had
a reclamation path: `gc_old_tasks()` existed but no shipped code called it, and
a mirror stream key was never given an expiry. Over a long uptime that is an
unbounded growth in both Redis and process memory for a feed whose usefulness
ends minutes after its terminal frame.

Epic 152 closes both without inventing a clock or a knob. The Redis side renews
a bounded TTL on every write (a live task cannot lapse under a follower; a quiet
one is left to expire), and the memory side reuses the three loops that already
tick every 60 seconds. This file pins the *wiring* -- the runtime behaviour of
the TTL and of `gc_old_tasks()` itself is measured in
`test_the_task_bus_can_scale_out_through_redis_streams.py` and
`test_core_modules.py` respectively. What is measured here:

* the mirror's TTL window outlasts every consumer's maximum wait, so write-time
  renewal never drops a key a relay is still following;
* all three periodic loops actually call the reclaimer (a positive control --
  a function nobody calls is exactly the bug this Epic fixes);
* the loops share the existing cadence, so no second clock was introduced.
"""

import ast
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
TASKBUS = APP / "core" / "taskbus.py"
EMBED_JOBS = APP / "ops" / "embed_jobs.py"
EMBED_WORKERS = APP / "ops" / "embed_workers.py"
RELAY = (Path(__file__).resolve().parents[2] / "backend" / "src" / "main" / "java"
         / "com" / "careeros" / "ai" / "SseRelayService.java")


def _mirror_ttl_s() -> int:
    tree = ast.parse(TASKBUS.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "_MIRROR_TTL_S" for t in node.targets):
            return node.value.value
    raise AssertionError("_MIRROR_TTL_S is no longer a module constant in taskbus.py")


def _relay_timeout_minutes() -> int:
    text = RELAY.read_text(encoding="utf-8")
    match = re.search(r"RELAY_TIMEOUT\s*=\s*Duration\.ofMinutes\((\d+)\)", text)
    assert match, "the backend relay's read budget is no longer stated in minutes"
    return int(match.group(1))


def test_the_mirror_window_outlasts_the_longest_a_relay_will_wait():
    """Write-time renewal is only safe if the window exceeds every follower's budget."""
    ttl_s = _mirror_ttl_s()
    relay_s = _relay_timeout_minutes() * 60
    assert ttl_s > relay_s, (
        f"the mirror expires in {ttl_s}s but a relay will follow for up to {relay_s}s: "
        "a quiet stretch inside a live task could drop its key mid-follow"
    )
    # The stream's own wait is far shorter still; keep a margin over it too.
    tree = ast.parse(TASKBUS.read_text(encoding="utf-8"))
    wait = [
        n.args.defaults[0].value for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name == "subscribe" and any(a.arg == "heartbeat_s" for a in n.args.args)
        and n.args.defaults and isinstance(n.args.defaults[0], ast.Constant)
    ]
    assert wait == [15.0], f"{wait}: the stream wait changed, re-check the TTL margin"
    assert ttl_s > wait[0], "the window must outlast a single stream wait"


def _calls_gc(path: Path, loop_name: str) -> bool:
    """Whether `loop_name`'s function body contains a `taskbus.gc_old_tasks()` call."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == loop_name:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) \
                        and sub.func.attr == "gc_old_tasks":
                    return True
    return False


def test_every_periodic_loop_reclaims_the_in_memory_dictionary():
    """The reclaimer is wired into all three cadences, including the Redis-down one.

    A `gc_old_tasks` definition no shipped loop calls is the exact dead code this
    Epic removes, so this is a positive control over the wiring, not a restatement
    of the gc predicate (which test_core_modules.py measures).
    """
    wired = {
        "embed_loop": _calls_gc(EMBED_JOBS, "embed_loop"),
        "embed_loop_distributed": _calls_gc(EMBED_WORKERS, "embed_loop_distributed"),
        "_fallback_loop": _calls_gc(EMBED_WORKERS, "_fallback_loop"),
    }
    assert all(wired.values()), (
        f"{wired}: every loop that ticks must reclaim the in-memory dictionary, or the "
        "path with the missing call keeps growing without bound"
    )


def test_the_reclamation_rides_existing_cadence_not_a_new_clock():
    """No new create_task or sleep was added to start a second reclamation clock."""
    for path, name in ((EMBED_JOBS, "embed_jobs.py"), (EMBED_WORKERS, "embed_workers.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        loops = [n for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name in ("embed_loop", "embed_loop_distributed", "_fallback_loop")]
        sleeps = [s for loop in loops for s in ast.walk(loop)
                  if isinstance(s, ast.Call) and isinstance(s.func, ast.Attribute)
                  and s.func.attr in ("sleep", "create_task")]
        # One sleep per loop, none of them newly introduced for gc: the count is
        # pinned so a future "just add a sweeper task" cannot slip in unseen.
        assert len(sleeps) == len(loops), (
            f"{name}: {len(sleeps)} sleeps across {len(loops)} loops -- reclamation should "
            "ride the existing cadence, not start another clock"
        )


def test_the_mirror_write_renews_the_window_in_one_round_trip():
    """XADD and PEXPIRE are issued together, so a written key always has an expiry."""
    text = TASKBUS.read_text(encoding="utf-8")
    # Read the write method's source and assert the pipeline pairs the two commands.
    start = text.index("    async def write(self, task_id: str, payload: dict) -> None:")
    body = text[start:text.index("\n    async def ", start + 10)]
    assert "pipeline(" in body, "the mirror write must batch its commands into one round trip"
    assert '"XADD"' in body and '"PEXPIRE"' in body, (
        "the mirror write must both append the event and renew the key's window"
    )
    assert "_MIRROR_TTL_S" in body, "the expiry must come from the declared window constant"

"""Orchestrator unit tests: tool loop, subagent handoff, artifacts/sources/actions.

No DB / no LLM: ai.ask is scripted and observability.trace is recorded in-memory.
"""

import json
import re

import pytest

from app.agents import orchestrator
from app.agents.orchestrator import Outcome, _collect_artifacts, _derive_actions
from app.agents.tools import TOOL_INDEX, Tool, _search_params
from app.providers.base import LLMMessage, LLMResponse, ToolCall, Usage


def _tool(name: str, artifact: str | None = None) -> Tool:
    async def _unused(*a, **k):  # _collect_artifacts never calls the handler
        return {}
    return Tool(name, "", {}, _unused, artifact=artifact)


def _resp(tool_calls=None, text=""):
    return LLMResponse(text=text, tool_calls=tool_calls or [],
                       usage=Usage(10, 5), model="mock-model")


@pytest.fixture
def env(monkeypatch):
    traces: list[tuple[str, str, dict]] = []
    calls: list[dict] = []

    async def fake_trace(run_id, kind, agent, payload):
        traces.append((kind, agent, payload))

    monkeypatch.setattr(orchestrator.observability, "trace", fake_trace)

    async def fake_memory(user_id):
        return ""

    monkeypatch.setattr(orchestrator.memory, "build_memory_context", fake_memory)
    return traces, calls


async def test_tool_loop_produces_artifacts_and_actions(env, monkeypatch):
    traces, _ = env
    script = iter([
        _resp(tool_calls=[ToolCall(id="c1", name="search_jobs",
                                   arguments={"query": "backend"})]),
        _resp(text="Found 1 matching role for you."),
    ])
    seen_msgs: list[list[LLMMessage]] = []

    async def fake_ask(req, **kw):
        seen_msgs.append(req.messages)
        return next(script)

    async def fake_handler(user_id, **kw):
        return {"jobs": [{"id": "j1", "title": "BE", "company": "X", "location": "SH",
                          "remote": "remote", "salary": [1, 2], "skills": ["Java"]}]}

    monkeypatch.setattr(orchestrator.ai, "ask", fake_ask)
    monkeypatch.setattr(TOOL_INDEX["search_jobs"], "handler", fake_handler)

    out = await orchestrator.career_turn(user_id="u1", message="find jobs", run_id="r1")

    assert out.answer == "Found 1 matching role for you."
    assert out.tools_used == ["search_jobs"]
    assert out.artifacts[0]["type"] == "job_list"
    assert out.actions[0]["kind"] == "open_job" and out.actions[0]["job_id"] == "j1"
    kinds = [t[0] for t in traces]
    assert "tool_call" in kinds and "tool_result" in kinds and "final" in kinds
    # tool result must be replayed back to the model as a tool message
    tool_msgs = [m for m in seen_msgs[-1] if m.role == "tool"]
    assert tool_msgs and json.loads(tool_msgs[0].content)["jobs"]


async def test_subagent_handoff(env, monkeypatch):
    traces, _ = env
    # career -> transfer_to(job_research) -> sub search_jobs -> sub report -> career final
    script = iter([
        _resp(tool_calls=[ToolCall(id="t1", name="transfer_to",
                                   arguments={"agent": "job_research",
                                              "task": "find remote Java jobs"})]),
        _resp(tool_calls=[ToolCall(id="c1", name="search_jobs",
                                   arguments={"query": "java"})]),
        _resp(text="SUBREPORT: 3 remote Java roles found"),
        _resp(text="I searched remote Java roles via the job research agent."),
    ])
    tool_names_seen: list[list[str]] = []

    async def fake_ask(req, **kw):
        tool_names_seen.append([t.name for t in (req.tools or [])])
        return next(script)

    async def fake_handler(user_id, **kw):
        return {"jobs": [{"id": "j9", "title": "Java Dev", "company": "Y",
                          "location": "Remote", "remote": "remote",
                          "salary": None, "skills": ["Java"]}]}

    monkeypatch.setattr(orchestrator.ai, "ask", fake_ask)
    monkeypatch.setattr(TOOL_INDEX["search_jobs"], "handler", fake_handler)

    out = await orchestrator.career_turn(user_id="u1", message="找远程 Java 岗位",
                                         run_id="r2")

    assert "job research agent" in out.answer
    handoffs = [t for t in traces if t[0] == "handoff"]
    assert handoffs and handoffs[0][2]["to"] == "job_research"
    # subagent must NOT see transfer_to (no recursive handoff) and gets a
    # restricted tool surface
    sub_call = tool_names_seen[1]
    assert "transfer_to" not in sub_call
    assert set(sub_call) <= set(orchestrator.SUBAGENT_TOOLS["job_research"])
    assert out.tools_used == ["search_jobs"]  # only from the sub run


async def test_step_budget_guard(env, monkeypatch):
    traces, _ = env

    async def endless(req, **kw):
        return _resp(tool_calls=[ToolCall(id="x", name="save_job",
                                          arguments={"job_id": "j1"})])

    async def fake_save(user_id, **kw):
        return {"saved": True}

    async def final_ish(req, **kw):  # finalize call after budget
        return _resp(text="Summary after budget.")

    state = {"n": 0}

    async def router(req, **kw):
        state["n"] += 1
        return await (endless(req) if "Step budget reached" not in
                      req.messages[-1].content else final_ish(req))

    monkeypatch.setattr(orchestrator.ai, "ask", router)
    monkeypatch.setattr(TOOL_INDEX["save_job"], "handler", fake_save)
    monkeypatch.setattr(orchestrator, "MAX_STEPS", 3)

    out = await orchestrator.career_turn(user_id="u1", message="save it", run_id="r3")
    assert out.answer == "Summary after budget."
    assert out.steps == 3


async def test_tool_error_is_reported_not_raised(env, monkeypatch):
    traces, _ = env

    async def boom(req, **kw):
        if any(m.role == "tool" for m in req.messages):
            err = json.loads(req.messages[-1].content)
            return _resp(text=f"recovered: {err['error']}")
        return _resp(tool_calls=[ToolCall(id="c1", name="get_job",
                                         arguments={"job_id": "nope"})])

    async def bad_handler(user_id, **kw):
        raise RuntimeError("db exploded")

    monkeypatch.setattr(orchestrator.ai, "ask", boom)
    monkeypatch.setattr(TOOL_INDEX["get_job"], "handler", bad_handler)

    out = await orchestrator.career_turn(user_id="u1", message="job?", run_id="r4")
    assert "db exploded" in out.answer
    result = [t for t in traces if t[0] == "tool_result"][0]
    assert result[2]["ok"] is False


async def test_a_call_missing_a_required_property_never_reaches_the_handler(env, monkeypatch):
    traces, _ = env
    reached: list[dict] = []

    async def script(req, **kw):
        if any(m.role == "tool" for m in req.messages):
            return _resp(text=f"noted: {req.messages[-1].content}")
        return _resp(tool_calls=[ToolCall(id="c1", name="get_job", arguments={})])

    async def fake_get(user_id, **kw):
        reached.append(kw)
        return {"job": {}}

    monkeypatch.setattr(orchestrator.ai, "ask", script)
    monkeypatch.setattr(TOOL_INDEX["get_job"], "handler", fake_get)

    out = await orchestrator.career_turn(user_id="u1", message="show me the job", run_id="r9")
    assert reached == []  # schema check fired first -- no DB round trip wasted
    assert "missing required property 'job_id'" in out.answer


async def test_a_call_with_an_unknown_property_names_the_allowed_set(env, monkeypatch):
    traces, _ = env

    async def script(req, **kw):
        if any(m.role == "tool" for m in req.messages):
            return _resp(text=req.messages[-1].content)
        return _resp(tool_calls=[ToolCall(id="c1", name="get_job",
                                          arguments={"job_id": "j1", "verbose": True})])

    async def must_not_run(user_id, **kw):
        raise AssertionError("an invalid call reached the handler")

    monkeypatch.setattr(orchestrator.ai, "ask", script)
    monkeypatch.setattr(TOOL_INDEX["get_job"], "handler", must_not_run)

    out = await orchestrator.career_turn(user_id="u1", message="job?", run_id="r10")
    assert "unexpected property 'verbose'" in out.answer
    assert "allowed: job_id" in out.answer


async def test_a_model_failure_after_tools_ran_answers_from_what_they_returned(env, monkeypatch):
    """The tool work is already done and collected; losing it because the next
    composition call failed would discard a job list the user can still act on."""
    traces, _ = env
    state = {"n": 0}

    async def script(req, **kw):
        state["n"] += 1
        if state["n"] == 1:
            return _resp(tool_calls=[ToolCall(id="c1", name="search_jobs",
                                              arguments={"query": "java"})])
        raise ConnectionError("provider down")

    async def fake_search(user_id, **kw):
        return {"jobs": [{"id": "j1", "title": "Java dev", "company": "Acme"}]}

    monkeypatch.setattr(orchestrator.ai, "ask", script)
    monkeypatch.setattr(TOOL_INDEX["search_jobs"], "handler", fake_search)

    out = await orchestrator.career_turn(user_id="u1", message="find java jobs", run_id="r11")
    assert "search_jobs" in out.answer          # says what did complete
    assert "ConnectionError" in out.answer      # says why it stopped, plainly
    assert out.tools_used == ["search_jobs"]
    assert any(a["type"] == "job_list" for a in out.artifacts), \
        "the collected card must survive the failed call"
    assert any(k == "degraded" for k, _a, _p in traces), \
        "a degraded turn must be distinguishable from a normal one on the run record"


async def test_a_degraded_reply_follows_the_language_the_user_wrote_in(env, monkeypatch):
    """No model is left to mirror the user's language, so the one assembled reply
    has to pick it. The step-budget instruction the finalize path appends is
    English, which is why the fallback reads the *first* user message: taking the
    last one would answer a Chinese request in English."""
    state = {"n": 0}

    async def script(req, **kw):
        state["n"] += 1
        if state["n"] == 1:
            return _resp(tool_calls=[ToolCall(id="c1", name="search_jobs",
                                              arguments={"query": "java"})])
        raise TimeoutError("finalize timed out")

    async def fake_search(user_id, **kw):
        return {"jobs": []}

    monkeypatch.setattr(orchestrator.ai, "ask", script)
    monkeypatch.setattr(TOOL_INDEX["search_jobs"], "handler", fake_search)
    monkeypatch.setattr(orchestrator, "MAX_STEPS", 1)

    out = await orchestrator.career_turn(
        user_id="u1",
        message="帮我找 Java 岗位",
        # A previous English turn: reading the list forwards would answer this
        # Chinese request in English.
        history=[{"role": "user", "content": "find me english jobs"},
                 {"role": "assistant", "content": "Here are three."}],
        run_id="r14")

    assert "助手" in out.answer and "请稍后重试" in out.answer
    assert "The assistant could not finish" not in out.answer
    assert "search_jobs" in out.answer, "the completed steps still have to be named"


async def test_a_model_failure_before_any_tool_still_raises(env, monkeypatch):
    """With nothing gathered there is no answer to fall back on, and a silent
    'please retry' would hide a provider that is down for every turn."""
    async def script(req, **kw):
        raise ConnectionError("provider down")

    monkeypatch.setattr(orchestrator.ai, "ask", script)

    with pytest.raises(ConnectionError):
        await orchestrator.career_turn(user_id="u1", message="hi", run_id="r12")


async def test_a_failed_finalize_answers_from_the_tool_results(env, monkeypatch):
    traces, _ = env
    state = {"n": 0}

    async def script(req, **kw):
        state["n"] += 1
        if state["n"] <= 2:
            return _resp(tool_calls=[ToolCall(id=f"c{state['n']}", name="search_jobs",
                                              arguments={"query": "java"})])
        raise TimeoutError("finalize timed out")

    async def fake_search(user_id, **kw):
        return {"jobs": []}

    monkeypatch.setattr(orchestrator.ai, "ask", script)
    monkeypatch.setattr(TOOL_INDEX["search_jobs"], "handler", fake_search)
    monkeypatch.setattr(orchestrator, "MAX_STEPS", 2)

    out = await orchestrator.career_turn(user_id="u1", message="find java jobs", run_id="r13")
    assert "TimeoutError" in out.answer
    assert out.steps == 2
    assert any(p.get("stage") == "finalize_failed"
               for k, _a, p in traces if k == "degraded")


async def test_run_loop_survives_non_dict_tool_arguments(env, monkeypatch):
    # A malformed JSON parse can hand the loop arguments that are a list/string/None
    # rather than a dict. The loop must coerce to {} and let the tool's own argument
    # checks (or the executor's TypeError handler) emit a clean tool error -- NOT
    # raise AttributeError on `arguments.get(...)` and abort the whole turn.

    async def script(req, **kw):
        if not any(m.role == "tool" for m in req.messages):
            return _resp(tool_calls=[ToolCall(id="c1", name="get_job",
                                             arguments=["not", "a", "dict"])])
        return _resp(text="recovered from bad arguments")

    async def fake_get(user_id, **kw):
        return {"job": {"id": "j1"}}

    monkeypatch.setattr(orchestrator.ai, "ask", script)
    monkeypatch.setattr(TOOL_INDEX["get_job"], "handler", fake_get)

    out = await orchestrator.career_turn(user_id="u1", message="job?", run_id="r5")
    assert isinstance(out.answer, str)
    # The tool was attempted; with no usable args it fails as a tool error, not a crash.
    assert out.tools_used == ["get_job"]


async def test_run_loop_survives_non_dict_transfer_arguments(env, monkeypatch):
    # Same malformed-arguments hazard on the transfer_to branch.

    async def script(req, **kw):
        if not any(m.role == "tool" for m in req.messages):
            return _resp(tool_calls=[ToolCall(id="t1", name="transfer_to",
                                             arguments=None)])
        return _resp(text="recovered from bad handoff")

    monkeypatch.setattr(orchestrator.ai, "ask", script)

    out = await orchestrator.career_turn(user_id="u1", message="delegate", run_id="r6")
    assert isinstance(out.answer, str)  # no AttributeError, turn still produces an answer


# ---------------- search_jobs positional-binding symmetry + injection safety ----------------


def _ph(sql: str) -> list[int]:
    return sorted(int(n) for n in re.findall(r"\$(\d+)", sql))


def test_search_params_all_filters_align_placeholder_to_bound_value():
    where, args = _search_params(query="go", skills=["Go", ""], location="Berlin",
                                 remote="remote", company="ACME", min_salary=100, limit=99)
    joined = " AND ".join(where)
    # $1 is the raw tsquery term, $2 its escaped LIKE twin; every filter after them
    # shifts by one, which is exactly what this alignment check protects.
    assert _ph(joined) == [1, 2, 3, 4, 5, 6, 7]
    assert max(_ph(joined)) == len(args) - 1
    # positional symmetry: the value each clause points at is exactly right
    assert args[0] == "go"
    assert args[1] == "%go%"
    assert args[2] == ["Go"]                     # falsy skill entries dropped
    assert args[3] == "%Berlin%"
    assert args[4] == "remote"                   # remote_type is compared, not matched
    assert args[5] == "%ACME%"
    assert args[6] == 100
    assert args[7] == 25                         # limit clamped to the 25 ceiling


def test_search_params_never_interpolates_user_text_into_sql():
    where, _ = _search_params(query="'; DROP TABLE jobs;--", location="x--MARK--",
                              company="RobertDELETE", min_salary=5)
    joined = " AND ".join(where)
    for literal in ("DROP TABLE", "RobertDELETE", "x--MARK--"):
        assert literal not in joined             # only $N placeholders, no user literals


def test_search_params_empty_query_still_binds_limit_and_skips_fts():
    where, args = _search_params(query="", limit=5)
    assert where == ["j.status = 'open'"]        # no tsquery clause
    assert args == ["", 5]                        # $1 always bound (empty), limit last


def test_search_params_limit_clamped_to_bounds():
    assert _search_params(query="x", limit=0)[1][-1] == 1
    assert _search_params(query="x", limit=-8)[1][-1] == 1
    assert _search_params(query="x", limit=1000)[1][-1] == 25
    assert _search_params(query="x", limit=12)[1][-1] == 12


# ---------------- _collect_artifacts / _derive_actions (pure UI-shapers) ----------------
# These build the copilot's suggestion buttons and citation source chips. Reached via
# career_turn only on the job_list path; every other branch had zero coverage.


def test_collect_match_artifact_carries_job_id_and_payload():
    out = Outcome()
    _collect_artifacts(_tool("match_job", artifact="match"),
                       {"match": {"overall": 0.8}, "job": {"id": "j7"}}, out)
    assert out.artifacts == [{"type": "match", "job_id": "j7",
                              "payload": {"overall": 0.8}}]


def test_collect_skips_artifact_on_error_or_missing_payload():
    out = Outcome()
    _collect_artifacts(_tool("match_job", artifact="match"), {"error": "boom"}, out)
    _collect_artifacts(_tool("match_job", artifact="match"), {"job": {"id": "j1"}}, out)
    assert out.artifacts == []


def test_collect_tailored_cover_and_interview_artifacts_map_payload():
    out = Outcome()
    _collect_artifacts(_tool("tailor", artifact="tailored_resume"),
                       {"tailored": {"x": 1}, "diff": "d", "notes": "n",
                        "stats": {"s": 2}, "irrelevant": "drop-me"}, out)
    _collect_artifacts(_tool("cover", artifact="cover_letter"), {"body": "hi"}, out)
    _collect_artifacts(_tool("interview", artifact="interview_session"),
                       {"session_id": "s1"}, out)
    _collect_artifacts(_tool("interview", artifact="interview_session"),
                       {"no_session": True}, out)  # missing session_id -> skipped
    assert [a["type"] for a in out.artifacts] == [
        "tailored_resume", "cover_letter", "interview_session"]
    # tailored payload whitelists exactly the four known keys
    assert set(out.artifacts[0]["payload"]) == {"tailored", "diff", "notes", "stats"}
    assert out.artifacts[2]["payload"] == {"session_id": "s1"}


def test_collect_sources_dedups_by_chunk_id_and_drops_missing():
    out = Outcome()
    _collect_artifacts(_tool("search_resume", artifact=None),
                       {"evidence": [
                           {"chunk_id": "c1", "doc_title": "Resume", "section": "Exp",
                            "quote": "did X" * 200},
                           {"chunk_id": "c1", "quote": "dup"},        # same cid -> skipped
                           {"quote": "no chunk id"},                  # no cid -> skipped
                           {"chunk_id": "c2", "source_kind": "JD"}]}, out)
    assert [s["chunk_id"] for s in out.sources] == ["c1", "c2"]
    assert len(out.sources[0]["quote"]) == 300  # quote truncated to 300
    # c1 label uses doc_title › section; c2 falls back to source_kind with empty section
    assert out.sources[0]["label"] == "Resume › Exp"
    assert out.sources[1]["label"] == "JD"


def test_derive_actions_from_match_expands_to_three_ctas_deduped():
    out = Outcome(artifacts=[{"type": "match", "job_id": "j5", "payload": {}},
                             {"type": "match", "job_id": "j5", "payload": {}}])
    _derive_actions(out)
    kinds = [(a["kind"], a["job_id"]) for a in out.actions]
    assert kinds == [("tailor", "j5"), ("interview", "j5"), ("cover_letter", "j5")]


def test_derive_actions_job_list_and_interview_session():
    out = Outcome(artifacts=[
        {"type": "job_list", "payload": {"jobs": [{"id": f"j{i}", "title": f"T{i}",
                                                   "company": f"C{i}"} for i in range(7)]}},
        {"type": "interview_session", "payload": {"session_id": "s9"}}])
    _derive_actions(out)
    opens = [a for a in out.actions if a["kind"] == "open_job"]
    assert len(opens) == 5  # capped at 5 of the 7 jobs
    assert opens[0]["label"] == "Open T0 @ C0"
    assert {"kind": "open_interview", "label": "Continue interview",
            "session_id": "s9"} in out.actions


def test_derive_actions_match_without_job_id_yields_nothing():
    out = Outcome(artifacts=[{"type": "match", "job_id": None, "payload": {}}])
    _derive_actions(out)
    assert out.actions == []


# ---------------- _tool_result_text / _emit (LLM-facing chokepoints) ----------------


def test_tool_result_text_roundtrips_json_and_keeps_cjk_literal():
    out = orchestrator._tool_result_text({"note": "简历经验", "n": 3, "ok": True})
    assert json.loads(out) == {"note": "简历经验", "n": 3, "ok": True}
    # ensure_ascii=False must survive — CJK may not be escaped to \uXXXX (token bloat,
    # and this product's resumes/JDs are largely Chinese).
    assert "简历" in out
    assert "\\u" not in out


def test_tool_result_text_stringifies_non_json_types_via_default():
    from uuid import UUID
    u = UUID("11111111-2222-3333-4444-555555555555")
    out = orchestrator._tool_result_text({"id": u})  # UUID is not JSON-serialisable
    assert str(u) in out  # default=str handled it, no TypeError escaping


def test_tool_result_text_falls_back_to_str_on_unserialisable_structure():
    circular: dict = {}
    circular["self"] = circular  # json.dumps raises ValueError on a reference cycle
    out = orchestrator._tool_result_text(circular)
    assert isinstance(out, str) and out  # fell through to str(result), non-empty


def test_a_large_tool_result_is_shrunk_not_cut_mid_json():
    """A truncated JSON document is not JSON.

    `search_knowledge_base` returns a context block capped at 6000 chars, so its
    result routinely exceeded RESULT_CHARS and was cut mid-token -- the model then
    read a broken document instead of data. The result must stay parseable.
    """
    big = {"evidence": [{"chunk_id": f"c{i}", "quote": "q" * 200} for i in range(40)],
           "context": "x" * (orchestrator.RESULT_CHARS + 500)}
    out = orchestrator._tool_result_text(big)
    assert len(out) <= orchestrator.RESULT_CHARS
    parsed = json.loads(out)                       # the whole point
    assert "evidence" in parsed and "context" in parsed
    assert parsed["context"].endswith(f"({len(big['context'])} chars total)")


def test_shrinking_keeps_the_small_keys_exactly_as_they_were():
    big = {"total": 3, "note": "ok", "blob": "y" * (orchestrator.RESULT_CHARS + 200)}
    parsed = json.loads(orchestrator._tool_result_text(big))
    assert parsed["total"] == 3 and parsed["note"] == "ok"
    assert parsed["blob"].startswith("y" * 300)


def test_a_long_list_keeps_a_head_and_says_how_many_were_dropped():
    big = {"jobs": [{"id": f"j{i}", "title": "t" * 100} for i in range(60)]}
    parsed = json.loads(orchestrator._tool_result_text(big))
    assert len(parsed["jobs"]) == 4                       # three rows plus the marker
    assert parsed["jobs"][-1] == "...(60 items total)"


def test_a_result_that_already_fits_is_returned_untouched():
    small = {"jobs": [{"id": "j1"}]}
    assert json.loads(orchestrator._tool_result_text(small)) == small


async def test_an_optional_null_argument_is_treated_as_absent(env):
    """`{"name": null}` means "I have no name", which is the handler's own default.

    Before this it reached `name.strip()` and raised AttributeError, which surfaced to
    the model as a tool error it could not act on.
    """
    seen: dict = {}

    async def handler(user_id, *, name=""):
        seen["name"] = name
        return {"ok": True}

    tool = Tool("get_company", "",
                {"type": "object", "properties": {"name": {"type": "string"}},
                 "additionalProperties": False}, handler)
    result = await orchestrator._exec_tool(tool, "u1", {"name": None}, run_id=None,
                                           agent="career", task_id=None, out=Outcome())
    assert result == {"ok": True}
    assert seen["name"] == ""


async def test_a_required_null_argument_is_named_by_the_validator(env):
    called: list = []

    async def handler(user_id, *, text):
        called.append(text)
        return {}

    tool = Tool("parse_resume", "",
                {"type": "object", "properties": {"text": {"type": "string"}},
                 "required": ["text"], "additionalProperties": False}, handler)
    result = await orchestrator._exec_tool(tool, "u1", {"text": None}, run_id=None,
                                           agent="career", task_id=None, out=Outcome())
    assert "property 'text' must be a string" in result["error"]
    assert called == []


async def test_get_company_with_a_null_name_answers_instead_of_raising(env):
    """The real handler, with the payload the model actually sends.

    `{"name": null}` used to reach `name.strip()`; the turn then reported
    "'NoneType' object has no attribute 'strip'" instead of the one thing the model
    could act on: it needs an id or a name.
    """
    result = await orchestrator._exec_tool(
        TOOL_INDEX["get_company"], "u1", {"name": None}, run_id=None,
        agent="career", task_id=None, out=Outcome())
    assert result == {"error": "company lookup needs company_id or name"}


async def test_an_identical_repeated_call_runs_once_and_says_so(env, monkeypatch):
    """A model that loses the thread re-issues the call it just made.

    Running it again costs a database round trip and, for the write tools, performs
    the write twice; the artifact would also be collected twice, so the UI would draw
    two cards for one search.
    """
    traces, _ = env
    calls: list = []
    state = {"n": 0}
    tool_messages: list[str] = []

    async def script(req, **kw):
        state["n"] += 1
        if state["n"] <= 2:
            return _resp(tool_calls=[ToolCall(id=f"c{state['n']}", name="search_jobs",
                                              arguments={"query": "java"})])
        tool_messages.extend(m.content for m in req.messages if m.role == "tool")
        return _resp(text="done")

    async def fake_search(user_id, **kw):
        calls.append(kw)
        return {"jobs": [{"id": "j1", "title": "Java dev", "company": "Acme"}]}

    monkeypatch.setattr(orchestrator.ai, "ask", script)
    monkeypatch.setattr(TOOL_INDEX["search_jobs"], "handler", fake_search)

    out = await orchestrator.career_turn(user_id="u1", message="find java", run_id="r16")

    assert len(calls) == 1, "the identical second call must not reach the handler"
    assert out.tools_used == ["search_jobs"], "it ran once, so it is recorded once"
    assert sum(1 for a in out.artifacts if a["type"] == "job_list") == 1
    assert "_note" in tool_messages[1], "the model must be told why the result repeated"


async def test_a_repeated_failing_call_is_retried_not_cached(env, monkeypatch):
    """A failure is not an answer: a transient one deserves the retry."""
    calls: list = []
    state = {"n": 0}

    async def script(req, **kw):
        state["n"] += 1
        if state["n"] <= 2:
            return _resp(tool_calls=[ToolCall(id=f"c{state['n']}", name="get_job",
                                              arguments={"job_id": "j1"})])
        return _resp(text="done")

    async def flaky(user_id, **kw):
        calls.append(kw)
        raise RuntimeError("transient")

    monkeypatch.setattr(orchestrator.ai, "ask", script)
    monkeypatch.setattr(TOOL_INDEX["get_job"], "handler", flaky)

    await orchestrator.career_turn(user_id="u1", message="job", run_id="r17")
    assert len(calls) == 2


async def test_a_read_reissued_after_a_write_runs_again_and_sees_the_new_world(env, monkeypatch):
    """The answered-cache is only valid while the world stands still.

    A model that lists the pipeline, saves a role, and lists again is not losing the
    thread -- the second list is the point. Serving it from the cache would answer
    from the pre-write world while the write's own success message sits right above
    it, so the user is told the save happened and shown a list that says it didn't.
    """
    traces, _ = env
    seen: list[str] = []
    state = {"step": 0, "rows": 0}

    async def script(req, **kw):
        state["step"] += 1
        if state["step"] == 4:
            seen.extend(m.content for m in req.messages if m.role == "tool")
            return _resp(text="done")
        if state["step"] == 1:
            return _resp(tool_calls=[ToolCall(id="c1", name="search_jobs",
                                              arguments={"query": "java"})])
        if state["step"] == 2:
            return _resp(tool_calls=[ToolCall(id="c2", name="save_job",
                                              arguments={"job_id": "j1"})])
        if state["step"] == 3:
            return _resp(tool_calls=[ToolCall(id="c3", name="search_jobs",
                                              arguments={"query": "java"})])
        return _resp(text="done")

    async def fake_search(user_id, **kw):
        state["rows"] += 1
        return {"jobs": [{"id": f"j{state['rows']}", "title": "Java dev"}]}

    async def fake_save(user_id, **kw):
        return {"saved": True, "job_id": kw.get("job_id")}

    monkeypatch.setattr(orchestrator.ai, "ask", script)
    monkeypatch.setattr(TOOL_INDEX["search_jobs"], "handler", fake_search)
    monkeypatch.setattr(TOOL_INDEX["save_job"], "handler", fake_save)

    out = await orchestrator.career_turn(user_id="u1", message="save and recheck",
                                         run_id="r18")

    assert out.tools_used == ["search_jobs", "save_job", "search_jobs"], \
        "all three calls executed: the write ran, and the read after it ran again"
    search_msgs = [m for m in seen if "jobs" in m]
    assert len(search_msgs) == 2
    assert json.loads(search_msgs[0])["jobs"][0]["id"] == "j1", \
        "the first read answers with the pre-write rows"
    assert json.loads(search_msgs[1])["jobs"][0]["id"] == "j2", \
        "the re-issued read must run again and see the world the write changed"
    assert "_note" not in search_msgs[1], "fresh data needs no repetition note"


async def test_a_reissued_write_still_runs_once_after_the_cache_clears(env, monkeypatch):
    """The clear must not resurrect the double-write the cache exists to prevent.

    save_job inserts on every run; the write's own result stays cached (the clear
    happens before the cache write), so losing the thread right after saving still
    cannot insert twice.
    """
    traces, _ = env
    seen: list[str] = []
    state = {"step": 0}

    async def script(req, **kw):
        state["step"] += 1
        if state["step"] == 3:
            seen.extend(m.content for m in req.messages if m.role == "tool")
            return _resp(text="done")
        if state["step"] <= 2:
            return _resp(tool_calls=[ToolCall(id=f"c{state['step']}", name="save_job",
                                              arguments={"job_id": "j1"})])
        return _resp(text="done")

    writes: list = []

    async def fake_save(user_id, **kw):
        writes.append(kw)
        return {"saved": True, "job_id": kw.get("job_id")}

    monkeypatch.setattr(orchestrator.ai, "ask", script)
    monkeypatch.setattr(TOOL_INDEX["save_job"], "handler", fake_save)

    await orchestrator.career_turn(user_id="u1", message="save it", run_id="r19")

    assert len(writes) == 1, "the re-issued write must not insert twice"
    assert "_note" in seen[1], "the model is told the save already happened"


def test_trace_args_shorten_a_long_document_but_keep_short_values():
    out = orchestrator._trace_args({"text": "r" * 5000, "job_id": "j1", "n": 3})
    assert out["job_id"] == "j1" and out["n"] == 3
    assert out["text"].endswith("(5000 chars)")
    assert len(out["text"]) < 500


async def test_the_handler_receives_the_full_argument_even_though_the_trace_does_not(
        env, monkeypatch):
    """Shortening the record must not shorten the call.

    A resume is personal content that should not be duplicated into `agent_traces`,
    but the parser needs every character of it -- so the cut belongs to the trace only.
    """
    traces, _ = env
    full = "resume line\n" * 800
    seen: list[str] = []

    async def script(req, **kw):
        if any(m.role == "tool" for m in req.messages):
            return _resp(text="done")
        return _resp(tool_calls=[ToolCall(id="c1", name="parse_resume",
                                          arguments={"text": full})])

    async def fake_parse(user_id, *, text):
        seen.append(text)
        return {"parsed": {}, "score": {}}

    monkeypatch.setattr(orchestrator.ai, "ask", script)
    monkeypatch.setattr(TOOL_INDEX["parse_resume"], "handler", fake_parse)

    await orchestrator.career_turn(user_id="u1", message="parse this", run_id="r15")

    assert seen == [full], "the handler must get every character"
    traced = [p for k, _a, p in traces if k == "tool_call"][0]
    assert traced["args"]["text"].endswith(f"({len(full)} chars)")
    assert len(traced["args"]["text"]) < 500


def test_emit_publishes_only_when_task_id_present(monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(orchestrator.taskbus, "publish", lambda *a: calls.append(a))
    orchestrator._emit(None, "status", {"step": "x"})
    assert calls == []  # no task → nothing to fan out to
    orchestrator._emit("t1", "status", {"step": "y"})
    assert calls == [("t1", "status", {"step": "y"})]


def test_collect_artifacts_skips_malformed_evidence_rows():
    """A non-dict evidence element (buggy engine / stale cached row) must not
    raise -- `_collect_artifacts` runs outside `_exec_tool`'s try block, so an
    unguarded `.get` there would abort the whole turn."""
    out = Outcome()
    tool = _tool("search_knowledge_base")
    result = {"evidence": [
        "a stray string",                 # non-dict → skipped
        42,                               # non-dict → skipped
        {"no_chunk_id": "x"},             # dict but no id → skipped
        {"chunk_id": "c1", "doc_title": "D", "section": "S", "quote": "q"},
    ]}
    _collect_artifacts(tool, result, out)
    assert len(out.sources) == 1
    assert out.sources[0]["chunk_id"] == "c1"


def test_collect_artifacts_missing_evidence_key_is_safe():
    out = Outcome()
    tool = _tool("search_knowledge_base")
    _collect_artifacts(tool, {"jobs": []}, out)  # no "evidence" key at all
    assert out.sources == []


def test_collect_artifacts_match_branch_tolerates_non_dict_job():
    out = Outcome()
    tool = _tool("calculate_match", artifact="match")
    # `job` present but not a dict: `result.get("job", {}).get("id")` must not raise.
    _collect_artifacts(tool, {"match": {"score": 0.5}, "job": "not-a-dict"}, out)
    assert out.artifacts == [{"type": "match", "job_id": None, "payload": {"score": 0.5}}]


# ---------------- derived actions are bookkeeping, never the answer ----------------


def test_derive_actions_skips_artifacts_that_are_not_dicts():
    out = Outcome()
    out.artifacts = ["not an artifact", None, 7]
    _derive_actions(out)  # must not raise
    assert out.actions == []


def test_derive_actions_tolerates_a_non_dict_payload():
    out = Outcome()
    out.artifacts = [{"type": "job_list", "payload": "oops"},
                     {"type": "interview_session", "payload": ["not", "a", "dict"]},
                     {"type": "match", "payload": "oops"}]
    _derive_actions(out)  # `.get` on a string would have raised
    assert out.actions == []


def test_derive_actions_skips_job_rows_it_cannot_open():
    out = Outcome()
    out.artifacts = [{"type": "job_list", "payload": {"jobs": [
        "not a job",
        {"title": "No id"},                 # cannot be opened without an id
        {"id": "j1"},                        # no title/company, still openable
        {"id": "j2", "title": "Backend", "company": "Acme"},
    ]}}]
    _derive_actions(out)
    opens = [a for a in out.actions if a["kind"] == "open_job"]
    assert [a["job_id"] for a in opens] == ["j1", "j2"]
    assert opens[0]["label"] == "Open role"
    assert opens[1]["label"] == "Open Backend @ Acme", \
        "the shipped label format must not change for a well-formed row"


def test_derive_actions_does_not_raise_on_a_non_string_session_id():
    # A UUID here is plausible (a peer returning the raw column); json.dumps on the
    # de-duplication key used to raise TypeError and take the whole turn with it.
    import uuid

    out = Outcome()
    out.artifacts = [{"type": "interview_session",
                      "payload": {"session_id": uuid.uuid4()}}]
    _derive_actions(out)
    assert out.actions[0]["kind"] == "open_interview"


async def test_a_failure_deriving_actions_does_not_lose_the_answer(env, monkeypatch):
    async def script(req, **kw):
        return _resp(text="Here is your answer.")

    monkeypatch.setattr(orchestrator.ai, "ask", script)

    def boom(_out):
        raise RuntimeError("derivation bug")

    monkeypatch.setattr(orchestrator, "_derive_actions", boom)

    out = await orchestrator.career_turn(user_id="u1", message="hi", run_id="r14")
    assert out.answer == "Here is your answer."   # the reply survives
    assert out.actions == []                      # the affordances do not

"""The SSE event names ai-service publishes are the ones the browser knows what to do with.

Ingest progress, copilot turns and interview runs all stream over one channel:
`taskbus.publish(task_id, <name>, data)` -> `/internal/stream/{id}` -> the Java relay, which
forwards names verbatim (`SseRelayService.relayEvents`) -> `dispatchEvent` in
`frontend/src/lib/sse/use-sse.ts`.

Two of those three hops are typed by hand and nothing connects them. A renamed event breaks
quietly: the client's `default:` branch drops the frame without a word, so the checklist stops
moving while the copy promises "results appear as soon as it does" -- `status` is exactly that
frame. The step ids behind the ingest checklist are the same seam one level down, with a worse
failure: `applyStatusEvent` *appends* an unknown step as a new row labelled with its raw id.

ai-service is the producer and the client is TypeScript, so this reads `use-sse.ts` as data the
way the request-side gates read the Java client, and separates two channels that share the word
"event": the taskbus stream, and `core/ai.py`'s per-call `emit(...)` callback that no endpoint
wires to the stream yet.
"""

import re
from pathlib import Path

from tests.test_internal_contract import _argument_list, _top_level

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "src"
USE_SSE = FRONTEND / "lib" / "sse" / "use-sse.ts"
UPLOAD_DROPZONE = FRONTEND / "components" / "resumes" / "upload-dropzone.tsx"

# names reach the client only through taskbus: publish/_emit call sites and literal yields


def _sources() -> list[tuple[Path, str]]:
    return [(p, p.read_text(encoding="utf-8")) for p in sorted(APP_ROOT.rglob("*.py"))]


def _stream_emitters() -> set[str]:
    """Files defining `_emit(task_id, event, data)`: the stream's own forwarding helper.

    A local helper of the same name exists in ingestion/chunking.py for something else
    entirely, so the signature -- not the name -- decides which call sites are stream sites.
    """
    return {path.relative_to(APP_ROOT).as_posix() for path, source in _sources()
            if re.search(r"\ndef _emit\(task_id[^)]*\)", source)}


def _stream_sites() -> list[tuple[str, str]]:
    """(file, text of the event-name argument) for every call that can put a frame on the stream.

    `api/tasks.py` re-sends whatever taskbus already holds, so a name can only *originate* at a
    publish/_emit call site or a literal yield -- the forwarding sites are reported separately by
    `dynamic_stream_sites` rather than being mistaken for names.
    """
    out: list[tuple[str, str]] = []
    emitters = _stream_emitters()
    for path, source in _sources():
        rel = path.relative_to(APP_ROOT).as_posix()
        openers = ["publish"] + (["_emit"] if rel in emitters else [])
        for opener in openers:
            # `(?<!def )` keeps a definition of publish/_emit from reading as a call to it
            for match in re.finditer(r"(?<!\w)(?<!def )" + opener + r"\(", source):
                inner, _ = _argument_list(source, match.end() - 1)
                args = _top_level(inner, ",")
                if len(args) == 3:
                    out.append((rel, args[1]))
        for match in re.finditer(r'yield \{"event": ', source):
            head = source[match.end():match.end() + 40].split(",")[0]
            out.append((rel, head))
    return out


def _split_names(sites: list[tuple[str, str]]) -> tuple[set[str], list[str]]:
    """A leading string literal is a name (ternaries list several); anything else is a forwarder."""
    names, dynamic = set(), []
    for rel, text in sites:
        if text.startswith('"'):
            names.update(re.findall(r'"([a-z_]+)"', text))
        else:
            dynamic.append(f"{rel}: {text.strip()[:40]}")
    return names, sorted(set(dynamic))


def stream_names() -> set[str]:
    """Event names that can reach the browser."""
    return _split_names(_stream_sites())[0]


def dynamic_stream_sites() -> list[str]:
    """Publish sites whose name is a parameter -- each one is a forwarder this reader follows
    only through its callers, so the set of them has to stay in the open."""
    return _split_names(_stream_sites())[1]


def callback_names() -> set[str]:
    """Names `core/ai.py` hands to its caller's `emit` -- a producer with no consumer wired."""
    found = set()
    for _path, source in _sources():
        found.update(re.findall(r'(?<![\w.])emit\(\s*\{"event":\s*"([a-z_]+)"', source))
    return found


def _dispatcher_body() -> str:
    source = USE_SSE.read_text(encoding="utf-8")
    start = source.index("export function dispatchEvent")
    return source[start:source.index("\n}\n", start)]


def handled_names() -> set[str]:
    return set(re.findall(r'case "([a-z_]+)":', _dispatcher_body()))


def inert_channels() -> set[str]:
    """Routed by the client, unreachable through the stream today."""
    return handled_names() - stream_names()


def pipeline_steps() -> list[str]:
    """Step ids the ingestion pipeline publishes, in the order it runs them."""
    source = (APP_ROOT / "ingestion" / "pipeline.py").read_text(encoding="utf-8")
    seen: list[str] = []
    for step in re.findall(r'"step":\s*"([a-z_]+)"', source):
        if step not in seen:
            seen.append(step)
    return seen


def seed_rows() -> list[tuple[str, str]]:
    """(id, label) of the checklist rows the upload panel seeds."""
    source = UPLOAD_DROPZONE.read_text(encoding="utf-8")
    block = re.search(r"INGEST_SEED = \[(.*?)\n\];", source, re.S)
    assert block, "the upload panel no longer seeds its checklist from a literal list"
    return [(m.group(1), m.group(2)) for m in re.finditer(
        r'\{\s*id:\s*"([a-z_]+)",\s*label:\s*"([^"]+)"', block.group(1))]


# ---------------------------------------------------------------------- the reconciliations

def test_every_event_the_stream_carries_is_one_the_client_routes():
    unhandled = sorted(stream_names() - handled_names())
    assert unhandled == [], f"the client would drop these frames without a word: {unhandled}"


def test_the_channels_with_no_producer_stay_a_declared_list():
    """`token` is produced only for a caller-supplied callback (`core/ai.py`), and `trace` /
    `artifact` have no producer at all: three handlers waiting for a publisher. Declaring them
    is what makes the fourth one arriving -- or a name losing its handler -- an explicit change."""
    assert inert_channels() == {"artifact", "token", "trace"}
    assert callback_names() == {"token"}


def test_the_forwarders_that_pass_a_name_through_stay_declared():
    """Two sites hand a name along instead of naming one, and both are safe only because of
    where the name came from before: `_emit`'s callers are scanned above, and the SSE endpoint
    re-sends payloads taskbus already stored. A third one means a frame this gate never saw."""
    assert dynamic_stream_sites() == [
        "agents/orchestrator.py: event",
        "api/tasks.py: ev[\"event\"]",
    ]


def test_the_ingest_checklist_rows_are_the_steps_the_pipeline_publishes():
    assert [row[0] for row in seed_rows()] == pipeline_steps()
    labels = dict(seed_rows())
    assert all(" " in labels[step] for step in labels), \
        "a row whose label is its own id is what an unseeded step falls back to"


def test_both_sides_are_actually_read():
    """Positive control: every gate above would stay green on an empty reading of either file."""
    assert stream_names() == {"done", "error", "message", "ping", "progress", "status"}
    assert {"message", "status", "done", "error", "ping", "progress"} <= handled_names()
    assert len(handled_names()) >= 9, f"the dispatcher lost its cases: {sorted(handled_names())}"
    assert pipeline_steps() == ["extracting", "cleaning", "chunking", "embedding", "indexing"]
    assert len(seed_rows()) == 5
    assert seed_rows()[0][1].startswith("Extracting")

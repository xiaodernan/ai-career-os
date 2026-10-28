"""The backend's service-to-service surface is documented as fully as the ai-service one.

`docs/API.md` section 3 lists every route the ai-service serves under `/internal/*`, because
that is the surface the backend calls. The traffic runs the other way too: ai-service
ingestion downloads a stored upload's bytes from `GET /api/internal/files/{fileKey}`, guarded
by `InternalApiFilter` and `X-Internal-Token` rather than by a user JWT. A reader of section 3
alone would conclude the backend exposes no internal surface at all -- and the routes it does
expose are the one that hands out stored document bytes and the one the nightly job writes its
verdict to, so "who can call this, and what key do they need" is exactly the fact that must not
live only in a filter class.

This gate walks every `*Controller.java` under `backend/src/main/java` for mappings rooted at
`/api/internal` and requires each to appear in the doc; it also walks the doc the other way,
so a path the doc advertises with no controller behind it fails here too. Both directions,
because either alone passes on a doc that documents nothing.

Path parameters are normalised (`{fileKey}` and the Spring `/**` wildcard both read `{}`),
so a rename of the parameter is not a doc break -- the row is about the route, not the name.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
JAVA = ROOT / "backend" / "src" / "main" / "java"
DOC = ROOT / "docs" / "API.md"

PREFIX = "/api/internal"

MINIMUM = 1


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def norm(path: str) -> str:
    """One spelling for a path parameter or a trailing wildcard."""
    return re.sub(r"\{[^}]*\}|\*\*", "{}", path)


def backend_routes() -> set[str]:
    """Every route a backend controller mounts under the service-to-service prefix."""
    out = set()
    for path in sorted(JAVA.rglob("*Controller.java")):
        text = read(path)
        base = re.search(r'@RequestMapping\("([^"]+)"\)', text)
        base = base.group(1) if base else ""
        if not base.startswith(PREFIX):
            continue
        for match in re.finditer(
                r'@(Get|Post|Put|Patch|Delete)Mapping'
                r'(?:\(\s*(?:value\s*=\s*)?"([^"]*)"\s*[,)])?', text):
            sub = match.group(2) or ""
            out.add(norm((base + sub).replace("//", "/")))
    return out


def documented() -> set[str]:
    """Every `/api/internal/...` literal the doc writes in backticks."""
    text = read(DOC)
    return {norm(m) for m in re.findall(r"`(/api/internal/[^`\s]*)`", text)}


def test_every_backend_internal_route_is_documented():
    routes = backend_routes()
    assert len(routes) >= MINIMUM, f"{len(routes)} internal routes walked, pinned at least {MINIMUM}"
    undocumented = sorted(routes - documented())
    assert undocumented == [], (
        f"the backend serves internal routes the doc never names: {undocumented} -- a reader "
        f"of docs/API.md section 3 would not know these exist")


def test_no_documented_internal_route_is_a_phantom():
    phantom = sorted(documented() - backend_routes())
    assert phantom == [], f"API.md advertises internal routes no controller serves: {phantom}"


def test_the_internal_surface_is_the_files_route_and_the_nights_record():
    """Positive control: the population is the one guarded download plus the nightly record.

    The nightly route (roadmap 20.1) is the first internal route whose caller is not the
    ai-service: the scheduled workflow posts its own verdict through the same filter. The
    pin is the whole surface, so a third route has to be documented here as well as in the
    doc -- the two directions above would both stay green on a doc that grew with it.
    """
    assert backend_routes() == {f"{PREFIX}/files/{{}}", f"{PREFIX}/nightly-reports"}
    assert documented() == {f"{PREFIX}/files/{{}}", f"{PREFIX}/nightly-reports"}

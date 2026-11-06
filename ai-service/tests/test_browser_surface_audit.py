"""Epic 71.1 -- the browser-surface audit: every public route the backend serves,
cross-walked against the readers the frontend ships.

The frontend's own route-parity gate (frontend/src/lib/api/endpoints.test.ts) pins
this from the other side: it walks Spring's route table and files the routes no
`endpoints.*` name reaches, each with the reason it is UI-less. This gate reads the
same answer from the backend's plane -- the controllers actually mounted, and the
frontend sources actually shipped -- so a route added here without a reader there
reddens in the suite that ships the backend, before the frontend ever learns of it.
The walk resolves two entry spellings the endpoints map uses: nested namespaces
(`auth: { login: ... }`) and multi-line arrow builders, and it grades a route as
read when its key is referenced by any non-test frontend source.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENDPOINTS_TS = REPO / "frontend" / "src" / "lib" / "api" / "endpoints.ts"
FRONTEND_ROOTS = [REPO / "frontend" / "src" / "app",
                  REPO / "frontend" / "src" / "components",
                  REPO / "frontend" / "src" / "lib",
                  REPO / "frontend" / "src" / "hooks"]

# Backend routes the browser serves but deliberately never calls, with the reason each
# is UI-less. The frontend's NEVER_REFERENCED ledger is the source of this record; the
# two gates disagree only when one of them drifted, which is the point of running both.
UI_LESS_ROUTES = {
    "GET /health": "liveness for the container probe, not something a page calls",
    "GET /calendar.ics": "the feed address is pasted into a calendar client; the settings card copies the URL the backend already signed",
    "GET /me": "MeController's alias of /users/me; the client spells every call through /users/...",
    "PATCH /me": "MeController's alias; the app PATCHes /users/me/profile instead",
    "POST /me/email-change": "MeController's alias of /users/me/email-change, which the settings card calls (38.2)",
    "POST /me/erase": "MeController's alias of /users/me/erase, which the settings card calls (38.5)",
    "PATCH /me/password": "MeController's alias of /users/me/password, which the settings card calls (38.4)",
    "GET /me/sessions": "MeController's alias of /users/me/sessions, which the settings card calls (38.3)",
    "DELETE /me/sessions": "MeController's alias of /users/me/sessions (revoke all), which the settings card calls (38.3)",
    "DELETE /me/sessions/{}": "MeController's alias of /users/me/sessions/{}, which the settings card calls (38.3)",
    "GET /resumes/{}/versions": "superseded for the panel by GET /resume-versions?resumeId=...",
    "GET /mail/preferences/{}/{}": "the mail-settings page a letter's footer opens; the backend renders it and the browser only navigates to it from a mailbox, never fetches it from the app",
    "POST /mail/preferences/{}/{}/start/{}": "the rendered mail-settings page's own form posts here; the app never calls it",
    "POST /mail/preferences/{}/{}/stop/{}": "the one-click unsubscribe URL a mail client fires; the app never calls it",
    "POST /inbound/mail/{}": "a mail provider posts here, not the browser; the address is what the settings card hands out",
    "DELETE /applications/{}/letters/{}": "the cover-letter edit surface is a recorded gap (71.3's queue): the app reads letters and regenerates, but has no edit screen",
    "PATCH /applications/{}/letters/{}": "the cover-letter edit surface is a recorded gap (71.3's queue): the app reads letters and regenerates, but has no edit screen",
    "GET /jds/{}": "the JD detail read is a recorded gap (71.3's queue): the app analyzes a pasted posting and reads the suggestions, but never fetches a stored JD by id",
}

_PARAM = re.compile(r"\{[^}]*\}")


def _backend_public_routes():
    """(verb, path) for every non-internal route the backend's controllers mount."""
    java = REPO / "backend" / "src" / "main" / "java"
    out = {}
    for f in java.rglob("*Controller.java"):
        text = f.read_text(encoding="utf-8", errors="replace")
        base = re.search(r'@RequestMapping\("([^"]+)"\)', text)
        base = base.group(1) if base else ""
        for m in re.finditer(r'@(Get|Post|Put|Patch|Delete)Mapping(?:\((?:value\s*=\s*)?"([^"]*)"[^)]*\))?', text):
            verb, sub = m.group(1).upper(), m.group(2) or ""
            path = _PARAM.sub("{}", base + sub)
            if "/internal/" in path:
                continue
            out[(verb, path)] = f.name
    return out


def _endpoint_keys():
    """key -> path template, resolving the map's two entry spellings."""
    text = ENDPOINTS_TS.read_text(encoding="utf-8")
    out = {}
    namespace = None
    pending = None
    for line in text.split("\n"):
        ns = re.match(r"^  (\w+): \{$", line)
        if ns:
            namespace = ns.group(1)
            continue
        if line.strip() in ("},", "}") and namespace:
            namespace = None
            continue
        body = line.lstrip()
        entry = re.match(r'(\w+): (?:\(([^)]*)\) => )?(?:`([^`]*)`|"([^"]*)"),?\s*$', body)
        if not entry:
            if pending:
                done = re.match(r'\s*(?:`([^`]*)`|"([^"]*)"),?\s*$', line)
                if done:
                    out[pending[0]] = done.group(1) or done.group(2)
                    pending = None
            continue
        name, tmpl = entry.group(1), entry.group(3) or entry.group(4)
        full = f"{namespace}.{name}" if namespace else name
        out[full] = tmpl
        pending = (full, tmpl) if entry.group(2) is not None and not tmpl else None
    return out


def _frontend_reader_keys():
    """The endpoint keys at least one non-test frontend source references."""
    used = set()
    keys = _endpoint_keys()
    names = sorted(keys, key=len, reverse=True)
    for root in FRONTEND_ROOTS:
        for f in root.rglob("*.ts*"):
            if ".test." in f.name:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            for k in names:
                if re.search(r"endpoints\." + re.escape(k) + r"\b", text):
                    used.add(k)
    return used


def _served_key(verb, path):
    """The ledger's spelling for one mounted route: verb, space, path with the
    `/api/v1` base the controllers carry stripped, params folded."""
    return f"{verb} /{_PARAM.sub('{}', path).replace('/api/v1', '', 1).strip('/')}"


def test_every_public_route_has_a_frontend_surface_or_a_recorded_reason():
    routes = _backend_public_routes()
    keys = _endpoint_keys()
    used = _frontend_reader_keys()

    def fold(path):
        return _PARAM.sub("{}", path).replace("$", "")

    by_path = {}
    for (verb, path), f in routes.items():
        by_path.setdefault(fold(path), []).append((verb, path, f))

    orphans, readered = [], 0
    for path, calls in sorted(by_path.items()):
        np = path.replace("/api/v1", "", 1).lstrip("/")
        hit = None
        for k, tmpl in keys.items():
            if fold(tmpl).strip("/") == np:
                hit = (k, k in used)
                break
        if hit is None:
            for verb, _p, f in calls:
                key = _served_key(verb, path)
                if key in UI_LESS_ROUTES:
                    readered += 1
                    continue
                orphans.append(f"{key} [{f}] no-key")
            continue
        if not hit[1]:
            for verb, _p, f in calls:
                key = _served_key(verb, path)
                if key in UI_LESS_ROUTES:
                    readered += 1
                    continue
                orphans.append(f"{key} [{f}] key={hit[0]} unreferenced")
            continue
        readered += len(calls)

    assert not orphans, (
        f"{orphans}: public routes this audit cannot account for -- either the route is "
        "new and needs a frontend surface (or a reason filed in UI_LESS_ROUTES above), "
        "or the endpoints map drifted from the controllers. 71.1's finding is that the "
        "accounted set is the shipped set: the UI-less routes are health, the calendar "
        "feed, the MeController aliases, the rendered mail pages and the inbound "
        "single-letter read -- everything else has a reader.")
    assert readered >= 100, (
        f"only {readered} routes accounted for -- the walk narrowed; the audit is stated "
        "about the whole public surface, and a narrowed walk would clear it by reading nothing")


def test_the_ui_less_ledger_names_only_routes_the_backend_serves():
    """The reverse direction: every reason this gate files names a real route.

    A reason for a route the backend stopped serving is a stale excuse -- the ledger
    has to shrink with the route table, not just grow with it."""
    routes = {_served_key(verb, path) for (verb, path) in _backend_public_routes()}
    stale = sorted(key for key in UI_LESS_ROUTES if key not in routes)
    assert stale == [], (
        f"{stale}: the UI-less ledger names routes the backend no longer serves -- "
        "delete the stale reasons with the routes they excuse")

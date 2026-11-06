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

The ledger is graded in both directions -- a readerless route needs a reason, and
a reason needs a readerless route. 71.1 graded only the first, and the parser lost
`applicationLetter`, the map's only two-argument multi-line builder: PATCH/DELETE
of a cover letter were filed as "no edit screen" while the editor and the delete
dialog had shipped in 50.2/50.4. A lost key does not merely miss a route -- it
invents a gap, and 71.3 would have rebuilt a surface that already existed.
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
    # 71.3's one real remaining gap. PATCH/DELETE of a letter used to be filed
    # here too, with the reason "no edit screen" -- that was this walk losing the
    # `applicationLetter` key, not a missing product surface: 50.2/50.4 shipped
    # the in-place editor and the delete dialog. The reverse assertion below is
    # what stops a reason like that from being filed again.
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
        # A builder whose template sits on the *next* line. endpoints.ts has exactly
        # one: `applicationLetter: (id, letterId) =>` followed by its backtick string.
        # The single-line pattern below cannot see it, so the key used to vanish from
        # the map and every route it serves looked key-less -- which is how 71.1 filed
        # PATCH/DELETE of a cover letter as "no edit screen" while the in-place editor
        # and the delete dialog had shipped in 50.2/50.4. A walk that loses a key does
        # not merely miss a route: it invents a gap the product already closed.
        arrow_only = re.match(r"^(\w+): \([^)]*\) =>\s*$", body)
        if arrow_only:
            name = arrow_only.group(1)
            pending = (f"{namespace}.{name}" if namespace else name, "")
            continue
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


def _walk():
    """(orphans, accounted, readerless) over the whole public route table.

    `readerless` is the measured set of served routes no frontend source reads --
    the exact population UI_LESS_ROUTES is allowed to name. Returning it (rather
    than recomputing it in each test) is what lets the ledger be graded in both
    directions: a route without a reader needs a reason, *and* a reason needs a
    route without a reader. 71.1 gated only the first, so a key the parser lost
    could be filed as a product gap that did not exist.
    """
    routes = _backend_public_routes()
    keys = _endpoint_keys()
    used = _frontend_reader_keys()

    def fold(path):
        return _PARAM.sub("{}", path).replace("$", "")

    by_path = {}
    for (verb, path), f in routes.items():
        by_path.setdefault(fold(path), []).append((verb, path, f))

    orphans, accounted, readerless = [], 0, set()
    for path, calls in sorted(by_path.items()):
        np = path.replace("/api/v1", "", 1).lstrip("/")
        hit = None
        for k, tmpl in keys.items():
            if fold(tmpl).strip("/") == np:
                hit = (k, k in used)
                break
        for verb, _p, f in calls:
            key = _served_key(verb, path)
            if hit is not None and hit[1]:
                accounted += 1
                continue
            readerless.add(key)
            if key in UI_LESS_ROUTES:
                accounted += 1
            else:
                detail = "no-key" if hit is None else f"key={hit[0]} unreferenced"
                orphans.append(f"{key} [{f}] {detail}")
    return orphans, accounted, readerless


def test_every_public_route_has_a_frontend_surface_or_a_recorded_reason():
    orphans, accounted, _ = _walk()
    assert not orphans, (
        f"{orphans}: public routes this audit cannot account for -- either the route is "
        "new and needs a frontend surface (or a reason filed in UI_LESS_ROUTES above), "
        "or the endpoints map drifted from the controllers. 71.1's finding is that the "
        "accounted set is the shipped set: the UI-less routes are health, the calendar "
        "feed, the MeController aliases, the rendered mail pages, the inbound "
        "single-letter read and the stored-JD detail -- everything else has a reader.")
    assert accounted >= 100, (
        f"only {accounted} routes accounted for -- the walk narrowed; the audit is stated "
        "about the whole public surface, and a narrowed walk would clear it by reading nothing")


def test_the_ui_less_ledger_is_exactly_the_routes_without_a_reader():
    """Both directions of the ledger, measured from the same walk.

    A reason for a route the backend stopped serving is a stale excuse; a reason
    for a route the browser *does* read is a lie about the product. 71.1 filed
    PATCH/DELETE /applications/{}/letters/{} as "no edit screen" because this
    parser lost their two-argument endpoint, while the editor had shipped in
    50.2/50.4. Only the first direction was gated, so the lie passed. Both are
    gated now.
    """
    routes = {_served_key(verb, path) for (verb, path) in _backend_public_routes()}
    stale = sorted(key for key in UI_LESS_ROUTES if key not in routes)
    assert stale == [], (
        f"{stale}: the UI-less ledger names routes the backend no longer serves -- "
        "delete the stale reasons with the routes they excuse")

    _orphans, _accounted, readerless = _walk()
    invented = sorted(key for key in UI_LESS_ROUTES if key not in readerless)
    assert invented == [], (
        f"{invented}: the ledger files routes the frontend already reads -- a reason "
        "is a claim that a surface is missing, so delete it (or fix the parser that "
        "lost the endpoint key)")
    unfiled = sorted(readerless - set(UI_LESS_ROUTES))
    assert unfiled == [], (
        f"{unfiled}: readerless routes with no recorded reason -- give each one a "
        "reason in UI_LESS_ROUTES or wire the browser surface")


def test_the_two_argument_builder_stays_in_the_endpoint_map():
    """Pin the one entry spelling that made the ledger lie.

    `applicationLetter` is endpoints.ts's only multi-line, two-argument builder;
    losing it turns two served, read routes into key-less orphans. Assert the key,
    its shape and its reader so a future parser change reddens here first.
    """
    keys = _endpoint_keys()
    assert keys.get("applicationLetter") == "/applications/${seg(id)}/letters/${seg(letterId)}", (
        "the two-argument builder was not resolved -- check _endpoint_keys' pending line handling")
    assert "applicationLetter" in _frontend_reader_keys(), (
        "the letter editor/delete hooks stopped naming this endpoint")
    orphans, _, readerless = _walk()
    assert [o for o in orphans if "/letters/{}" in o] == [], (
        "the letter routes became orphans -- the walk can no longer see their reader")
    assert not any("/letters/{}" in k for k in readerless), (
        "the letter routes were filed as UI-less again -- their surface exists")

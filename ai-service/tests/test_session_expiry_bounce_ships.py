"""The signed-out bounce says why: the reason travels in the /login URL.

`onSessionExpired` takes the browser to /login with a full navigation, so the `ApiError` thrown
beside it fires a toast the navigation kills -- the user landed on the sign-in screen with no
explanation. The reason now rides the bounce URL instead: ``client.ts`` appends
``reason=<SESSION_EXPIRED_REASON>`` reading the value from ``lib/session-expiry.ts``, the login
page destructures it out of ``searchParams`` and hands it to ``sessionNotice``, and the form
renders the sentence in a ``role="alert"`` banner. Both spellings -- the reason value and the
sentence -- live in that one module, which is what lets the census below count carriers and
mean it.

Each link is pinned where it is written: the writer's import and bounce line (plus the ban on
a re-spelled literal), the login page's three lines (the register page must stay silent), the
module's declarations and its unit cases, the form's prop and single banner, and the app-wide
census of programmatic /login bounces -- four sites today, so a fifth bounce, or any bounce
that stops carrying the reason, has to cost an edit here.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests._repo_walk import walk_files

ROOT = Path(__file__).resolve().parents[2]
FRONT_SRC = ROOT / "frontend" / "src"

MODULE = "frontend/src/lib/session-expiry.ts"
MODULE_TEST = "frontend/src/lib/session-expiry.test.ts"
CLIENT = "frontend/src/lib/api/client.ts"
LOGIN_PAGE = "frontend/src/app/(auth)/login/page.tsx"
REGISTER_PAGE = "frontend/src/app/(auth)/register/page.tsx"
CRED_FORM = "frontend/src/components/auth/credentials-form.tsx"

SENTENCE = "Your session has expired \u2014 sign in again."
IMPORT_LINE = 'import { SESSION_EXPIRED_REASON } from "../session-expiry";'
BOUNCE_LINE = "window.location.href = `/login?next=${next}&reason=${SESSION_EXPIRED_REASON}`;"

BOUNCE = re.compile(r'\.(?:replace|push)\("/login|href = `/login')

EXPECTED_BOUNCES = [
    ("frontend/src/app/(app)/layout.tsx",
     'if (!session) router.replace("/login");'),
    ("frontend/src/app/(app)/layout.tsx",
     'if (isError && tokenStore.hasSession() === false) router.replace("/login");'),
    (CLIENT, BOUNCE_LINE),
    ("frontend/src/lib/hooks/auth.ts",
     'router.replace("/login");'),
]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def app_sources() -> tuple[str, ...]:
    """The app's own TypeScript sources, tests excluded -- a test naming a line is not the screen."""
    found = []
    for path in walk_files(FRONT_SRC):
        if path.suffix not in {".ts", ".tsx"} or ".test." in path.name:
            continue
        found.append(path.relative_to(ROOT).as_posix())
    assert len(found) >= 80, "the client walk read only %d files" % len(found)
    return tuple(sorted(found))


def test_the_bounce_writes_the_reason_it_imports():
    client = read(CLIENT)
    assert IMPORT_LINE in client, (
        "client.ts no longer imports the reason from the one module that declares it; the "
        "bounce below would be a re-spelled literal")
    assert BOUNCE_LINE in client, (
        "the session-expiry bounce no longer carries `reason=<SESSION_EXPIRED_REASON>`, so "
        "the login screen cannot say why the user is there")
    for literal in ('"expired"', "'expired'"):
        assert literal not in client, (
            "client.ts re-spells the reason as %s instead of importing SESSION_EXPIRED_REASON; "
            "a second spelling is a drift candidate" % literal)


def test_the_login_page_reads_the_reason_through_the_shared_helper():
    page = read(LOGIN_PAGE)
    assert 'import { sessionNotice } from "@/lib/session-expiry";' in page, (
        "the login page stopped importing the shared resolver")
    assert "const { reason } = await searchParams;" in page, (
        "the login page no longer destructures `reason` out of searchParams; Next 15 hands "
        "the page a Promise, and this pins the awaited form")
    assert "notice={sessionNotice(reason)}" in page, (
        "the login page stopped passing the resolved notice to the form; the reason would "
        "travel the whole way and die at the last step")
    assert "notice" not in read(REGISTER_PAGE), (
        "the register page grew a notice -- only the session-expiry bounce writes a reason, "
        "and it only ever targets /login")


def test_the_reason_module_declares_the_pinned_spellings():
    module = read(MODULE)
    for line in (
        'export const SESSION_EXPIRED_REASON = "expired";',
        'export const SESSION_EXPIRED_MESSAGE = "Your session has expired \u2014 sign in again.";',
        "export function sessionNotice(reason: unknown): string | undefined {",
        "return reason === SESSION_EXPIRED_REASON ? SESSION_EXPIRED_MESSAGE : undefined;",
    ):
        assert line in module, "session-expiry.ts lost %r" % line
    cases = read(MODULE_TEST)
    assert 'from "./session-expiry"' in cases and "toBeUndefined();" in cases and '"expired "' in cases, (
        "session-expiry.test.ts no longer holds the resolver both ways: the bounce's spelling "
        "resolves, and near misses (including a trailing space) stay silent")


def test_the_sentence_has_exactly_one_carrier_in_app_sources():
    carriers = [rel for rel in app_sources() if SENTENCE in read(rel)]
    assert carriers == [MODULE], (
        "the announcement sentence is carried by %s; it must live only in %s, or a copy can "
        "drift from the one the login screen renders" % (carriers or ["nothing"], MODULE))


def test_the_form_owns_the_notice_prop_and_renders_it_once():
    form = read(CRED_FORM)
    assert "notice?: string" in form, (
        "CredentialsForm lost the optional notice prop the login page passes")
    assert "{notice ? (" in form, (
        "the form no longer guards the banner on the prop; an undefined notice would render "
        "an empty alert")
    assert form.count('role="alert"') == 1, (
        'the form carries %d role="alert" elements; pinned at one (the notice banner)'
        % form.count('role="alert"'))
    assert form.count("{notice}") == 1, (
        "the form renders `{notice}` %d times; pinned at one" % form.count("{notice}"))


def test_every_programmatic_login_bounce_is_the_pinned_one():
    found = []
    for rel in app_sources():
        for line in read(rel).splitlines():
            if BOUNCE.search(line):
                found.append((rel, line.strip()))
    found = sorted(set(found))
    assert found == EXPECTED_BOUNCES, (
        "the programmatic /login bounces changed:\nfound:    %r\nexpected: %r\n"
        "each bounce is either benign (no session -> sign in; user-initiated sign-out) or "
        "carries the reason; changing one means deciding which it is" % (found, EXPECTED_BOUNCES))

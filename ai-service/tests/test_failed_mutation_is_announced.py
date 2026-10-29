"""Every mutation the app declares must have somebody who says so when it fails.

react-query gives a mutation two places to put an error handler, and the second one is invisible to a
reader of the hook file alone: the options object ``useMutation({...})`` accepts ``onError``, and so
does each *call* -- ``mutate(vars, { onError })`` -- with the call-level handlers running alongside the
hook's. A gate that reads only hooks therefore cannot answer the user-visible question, which is "when
this request fails, does anyone say so?". This file answers it per mutation site, app-wide, and follows
the caller's options through the one indirection the app actually uses: a named object handed to two
different mutations.

What the shipped code says, measured rather than assumed: 80 mutation sites in ten files
(the hook libraries, plus the knowledge uploader's own actions). 75 declare their failure at
the hook; the five that do not are all in ``auth.ts``. Four of those five are announced by
their caller -- the password forms pass inline call options, and the credentials form passes
one shared ``handlers`` object to both ``login.mutate`` and ``register.mutate``, whose
``onError`` maps the failure through the recovery module's describer. The fifth,
``useLogout``, is announced by nobody, and its ``mutationFn`` swallows the rejection
(``.catch(() => undefined)``), so the mutation cannot even enter an error state for a screen
to read; its ``onSettled`` clears the token, clears the cache and redirects regardless of what
the server said. That is a design choice -- a local sign-out always happens -- so this file
characterises it rather than changing it: it is the one place in the app where "you are signed
out" is not a claim about the server.

The same walk covers the failure helper: ``fail(...)`` has a single author and 73 uses, and
every use names a key the browser's table answers -- the sentence is resolved when the toast
is raised, in the reader's language. All but three name a different key: the inbox's read,
mark-all-read and dismiss share ``notifications.actionFailed`` because they are one sentence
about one screen, and the case below pins that exception by name. When this file first walked
a helper that took sentences, 28 were distinct, because two different deletes shared
"Delete failed." and the toast never said which record survived. Each delete now names its
own key, and the case below pins the spent state so a quietly reused sentence goes red.

Both populations used to be pinned as totals copied into four assertions. Two feature
commits (be6eea0's ``useImportApply``, c8d0a4b's ``useRenderBundle``) each added a site and
a sentence without this census, and one honest change reddened five cases while telling the
reader nothing about which file moved. The counts now come from the per-file roster below --
so a move names its file -- and the paragraph above is graded against the walk too, in the
last case, because prose that quotes a census is a claim about the app like any other.
"""

import collections
import re
from functools import lru_cache

from tests.test_cache_writes_ship_what_the_key_owner_produces import balanced_end
from tests.test_invalidated_keys_are_queries_screens_mount import (  # noqa: F401
    ACTIONS,
    AUTH_HOOKS,
    hook_body,
    sources,
    strip_comments,
)

SOURCE_ACTIONS = "frontend/src/components/knowledge/source-actions.tsx"
# The shared failure handler: one implementation of "what a failed write says",
# imported by every mutation hook. See `lib/hooks/failure.ts`.
FAILURE = "frontend/src/lib/hooks/failure.ts"
# The forward bridges' own mutation hooks (11.2-11.3, 12.x, 13.x, 14.x, 10.x).
# Each announces its failure through the shared handler, so a write that fails
# says which write failed rather than failing silently.
BRIDGE_HOOKS = {
    "frontend/src/lib/hooks/analytics.ts",
    "frontend/src/lib/hooks/data-portability.ts",
    "frontend/src/lib/hooks/growth.ts",
    "frontend/src/lib/hooks/ingestion.ts",
    "frontend/src/lib/hooks/notifications.ts",
    "frontend/src/lib/hooks/offers.ts",
    # 19.6's voice seam: the transcribe and speak writes announce their failure at the hook.
    "frontend/src/lib/hooks/voice.ts",
}
CLIENT = "frontend/src/lib/api/client.ts"
CREDENTIALS = "frontend/src/components/auth/credentials-form.tsx"
FORGOT = "frontend/src/components/auth/forgot-password-form.tsx"
RESET = "frontend/src/components/auth/reset-password-form.tsx"
TOPBAR = "frontend/src/components/layout/topbar.tsx"

DECL = re.compile(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\s+(\w+)|const\s+(\w+)\s*=)", re.M)

#: Every file that declares a mutation, and how many sites it declares, as measured off the
#: shipped bytes. The totals the cases claim are derived from this roster, so a new write is a
#: one-line edit that names the file that moved, instead of redening four cases that each
#: hand-copied the same sum. Two feature commits did exactly that and left the sums behind --
#: be6eea0 added ``useImportApply`` and c8d0a4b added ``useRenderBundle``, each announcing its
#: failure at the hook with its own ``fail()`` sentence, so what went stale was the census, not
#: the app. A mutation in a file outside this roster is still a red, and the red names that file.
ROSTER = {
    ACTIONS: 39,
    AUTH_HOOKS: 5,
    "frontend/src/lib/hooks/analytics.ts": 1,
    "frontend/src/lib/hooks/data-portability.ts": 5,
    "frontend/src/lib/hooks/growth.ts": 12,
    "frontend/src/lib/hooks/ingestion.ts": 8,
    "frontend/src/lib/hooks/notifications.ts": 3,
    "frontend/src/lib/hooks/offers.ts": 4,
    "frontend/src/lib/hooks/voice.ts": 2,
    SOURCE_ACTIONS: 1,
}
SITES = sum(ROSTER.values())

#: The hooks that state no ``onError`` of their own. They are the five auth signs, and the set
#: being closed is the claim: a sixth quiet site is a write whose failure nobody says out loud,
#: wherever it lives.
QUIET_AUTH = ["useForgotPassword", "useLogin", "useLogout", "useRegister", "useResetPassword"]

#: ``fail("...")`` calls per file -- the copy keys a failed write is announced with. Pinned per
#: file because the useful failure is "actions.ts spent one more key", not a total that
#: moves whenever any hook is touched.
SENTENCES = {
    ACTIONS: 38,
    "frontend/src/lib/hooks/analytics.ts": 1,
    "frontend/src/lib/hooks/data-portability.ts": 5,
    "frontend/src/lib/hooks/growth.ts": 12,
    "frontend/src/lib/hooks/ingestion.ts": 8,
    "frontend/src/lib/hooks/notifications.ts": 3,
    "frontend/src/lib/hooks/offers.ts": 4,
    "frontend/src/lib/hooks/voice.ts": 2,
}
FAIL_USES = sum(SENTENCES.values())

#: The one key more than one write spends, pinned by name and count. The inbox's three writes
#: -- read, mark-all-read and dismiss -- are one sentence about one screen ("Couldn't update
#: the inbox."), so they share a key on purpose. Every other write names its own, because a
#: toast that hides which record failed was the collision this file was written to stop.
SHARED_KEYS = {"notifications.actionFailed": 3}

#: The auth form's shared call options, declared inside the submit handler and passed to both
#: ``login.mutate`` and ``register.mutate``. The failure is mapped through the recovery module's
#: describer, which the form imports by name -- the describer's own name has moved once already
#: (``describeError`` -> ``authFormErrorMessage``), so the claim below binds the mechanism
#: (import + export + call) instead of a hand-copied line of another file's prose.
RECOVERY = "frontend/src/lib/auth-recovery.ts"

#: The docstring writes its census in words as well as digits; the last case re-reads the
#: walk and looks for the sentence it would have to have written today.
NUM_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
             8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def object_literal(text: str, pos: int) -> str:
    """The ``{...}`` that opens at or after ``pos``, read to its own matching close."""
    brace = text.index("{", pos)
    return text[brace : balanced_end(text, brace, "{", "}")]


def object_keys(lit: str) -> list[str]:
    """Top-level keys of an object literal; keys nested in another object are not this one's."""
    out: list[str] = []
    depth = 0
    i = 0
    while i < len(lit):
        char = lit[i]
        if char in "{[(":
            depth += 1
        elif char in "}])":
            depth -= 1
        elif depth == 1:
            m = re.match(r"(\w+):", lit[i:])
            if m and (i == 1 or lit[i - 1] in ",{[ \n\t"):
                out.append(m.group(1))
                i += m.end()
                continue
        i += 1
    return out


def split_top(args: str) -> list[str]:
    """An argument list split at top-level commas only."""
    out, depth, current = [], 0, ""
    for char in args:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        if char == "," and depth == 0:
            out.append(current)
            current = ""
        else:
            current += char
    return out + [current]


def owner_of(text: str, pos: int) -> str:
    """The nearest preceding declared function or component the site sits inside."""
    names = [m.group(1) or m.group(2) for m in DECL.finditer(text[:pos])]
    assert names, "a mutation site at line %d sits in no declaration this walk can name" % (
        text[:pos].count("\n") + 1
    )
    return names[-1]


@lru_cache(maxsize=None)
def sites() -> list:
    """Every ``useMutation(`` site, with its own options object's keys and its owner."""

    class Site:
        def __init__(self, rel, name, line, keys, body):
            self.rel, self.name, self.line = rel, name, line
            self.keys, self.body = keys, body

        @property
        def hook_level(self) -> bool:
            return "onError" in self.keys

        @property
        def where(self) -> str:
            return "%s:%d %s" % (self.rel.split("/")[-1], self.line, self.name)

    out = []
    for rel, text in sources().items():
        for m in re.finditer(r"\buseMutation\(", text):
            lit = object_literal(text, text.index("(", m.start()))
            keys = object_keys(lit)
            assert keys, "%s holds a useMutation with an options object that states no keys" % rel
            out.append(Site(rel, owner_of(text, m.start()), text[: m.start()].count("\n") + 1, keys, lit))
    return out


@lru_cache(maxsize=None)
def callers(hook: str) -> list:
    """Each ``X.mutate(...)`` where ``X`` is bound from ``hook()``, with the call-level options' keys."""

    class Caller:
        def __init__(self, rel, var, line, keys, named):
            self.rel, self.var, self.line, self.keys, self.named = rel, var, line, keys, named

        @property
        def where(self) -> str:
            return "%s:%d %s.mutate" % (self.rel.split("/")[-1], self.line, self.var)

    out = []
    for rel, text in sources().items():
        for b in re.finditer(r"const (\w+) = %s\(\)" % re.escape(hook), text):
            var = b.group(1)
            for c in re.finditer(r"\b%s\.(?:mutate|mutateAsync)\(" % re.escape(var), text):
                open_paren = text.index("(", c.start())
                args = text[open_paren + 1 : balanced_end(text, open_paren, "(", ")") - 1]
                parts = split_top(args)
                tail = parts[1].strip() if len(parts) > 1 else ""
                named, keys = "", []
                if tail.startswith("{"):
                    keys = object_keys(object_literal(tail, 0))
                elif re.fullmatch(r"\w+", tail):
                    named = tail
                    decl = re.search(r"const %s(:\s*[^=]*)?\s*=\s*" % re.escape(tail), text)
                    assert decl, "%s passes %s as call options, which nothing in that file binds" % (rel, tail)
                    keys = object_keys(object_literal(text, decl.end()))
                out.append(Caller(rel, var, text[: c.start()].count("\n") + 1, keys, named))
    assert out, "no screen calls %s, so this file has nothing to measure about its failure path" % hook
    return out


FAIL_CALL = re.compile(r'fail\("([^"]*)"\)')


def fail_messages() -> collections.Counter:
    """Every ``fail("...")`` message the app builds a handler from."""
    out: collections.Counter = collections.Counter()
    for text in sources().values():
        out.update(FAIL_CALL.findall(text))
    return out


def fail_uses() -> collections.Counter:
    """The same calls counted per file that makes them, so a move names its file."""
    out: collections.Counter = collections.Counter()
    for rel, text in sources().items():
        if hits := len(FAIL_CALL.findall(text)):
            out[rel] = hits
    return out


def stmt(body: str, needle: str) -> str:
    """The one line of a body that holds ``needle``, stripped."""
    hits = [line.strip() for line in body.splitlines() if needle in line]
    assert len(hits) == 1, "%r matches %d lines, so the claim does not name one statement" % (needle, len(hits))
    return hits[0]


# ------------------------------------------------------------------ cases


def test_every_mutation_the_app_declares_sits_in_a_function_the_walk_can_name():
    pop = sites()
    per_file = collections.Counter(s.rel for s in pop)
    # The census is read as a roster, not as a number: a write added or removed anywhere in
    # the app has to say which file it belongs to, because that file is where the next reader
    # of this failure will look.
    moved = {rel.split("/")[-1]: (want, per_file.get(rel, 0))
             for rel, want in sorted(ROSTER.items(), key=lambda kv: kv[0])
             if per_file.get(rel, 0) != want}
    outside = sorted(rel.split("/")[-1] for rel in set(per_file) - set(ROSTER))
    assert not moved and not outside, (
        "the mutation roster moved (file: pinned, walked) %s; files outside the roster: %s" % (
            moved, outside))
    assert len(pop) == SITES, "the roster sums to %d but the walk found %d" % (SITES, len(pop))
    # The component-level population is the part a concurrent screen edit can move, so it is read as a
    # claim about every site found rather than as a pinned count.
    component = [s for s in pop if s.rel == SOURCE_ACTIONS]
    assert len(component) >= 1, "%s declares no mutation, so the forall below proves nothing" % SOURCE_ACTIONS
    assert all(s.hook_level for s in component), "%s declares a mutation with no hook-level onError: %s" % (
        SOURCE_ACTIONS.split("/")[-1], [s.where for s in component if not s.hook_level]
    )
    assert {"useLogin", "useLogout", "useRegister"} <= {s.name for s in pop}, (
        "the walk lost one of the three auth mutations it sets out to read: %s" % sorted(s.name for s in pop)
    )


def test_the_five_quiet_hooks_are_the_auth_signs_and_every_other_site_announces_at_its_hook():
    quiet = [s for s in sites() if not s.hook_level]
    assert len(quiet) == len(QUIET_AUTH), "%d mutations announce nothing at the hook: %s" % (
        len(quiet), [s.where for s in quiet]
    )
    assert sorted(s.name for s in quiet) == QUIET_AUTH, "the hook-level silent set moved: %s" % sorted(
        s.name for s in quiet)
    assert {s.rel for s in quiet} == {AUTH_HOOKS}, "the silent set left %s" % AUTH_HOOKS.split("/")[-1]
    untyped = [s.where for s in sites() if "mutationFn" not in s.keys]
    assert not untyped, "a mutation with no mutationFn is not a request: %s" % untyped


def test_every_quiet_hook_is_announced_by_the_code_that_calls_it_except_the_signout():
    announced, silent = {}, {}
    for site in [s for s in sites() if not s.hook_level]:
        calls = callers(site.name)
        if all("onError" in c.keys for c in calls):
            announced[site.name] = sorted({c.where.split(":")[0] for c in calls})
        else:
            silent[site.name] = [(c.where, c.keys) for c in calls]
    assert sorted(announced) == ["useForgotPassword", "useLogin", "useRegister", "useResetPassword"], (
        "the caller-announced set is %s, still silent %s" % (sorted(announced), sorted(silent))
    )
    assert list(silent) == ["useLogout"], "more than one mutation is announced by neither hook nor caller: %s" % silent
    assert len(silent["useLogout"]) == 2, "useLogout is called %d times, not the two this file reads" % len(silent["useLogout"])
    assert all("onError" not in keys for _, keys in silent["useLogout"]), (
        "a sign-out call now passes an onError %s, so the silent sign-out has an announcer" % silent["useLogout"]
    )
    assert sorted(tuple(keys) for _, keys in silent["useLogout"]) == [(), ("onSettled",)], (
        "the two sign-out calls pass %s: this file reads one with no options at all and one that only "
        "repeats the local sign-out, neither of which can say that the server refused" % silent["useLogout"]
    )


def test_the_credentials_form_announces_two_different_mutations_with_one_shared_object():
    text = sources()[CREDENTIALS]
    assert sorted(re.findall(r"const (\w+) = (?:useLogin|useRegister)\(\)", text)) == ["login", "register"], (
        "the form binds %s" % re.findall(r"const (\w+) = (?:useLogin|useRegister)\(\)", text)
    )
    named = {c.named for c in callers("useLogin")} | {c.named for c in callers("useRegister")}
    assert len(named) == 1 and "" not in named, "the two calls pass %s, so they do not share one object" % named
    name = next(iter(named))
    decl = re.search(r"const %s(:\s*[^=]*)?\s*=\s*" % re.escape(name), text)
    assert decl, "%s is passed as call options but declared nowhere in the form" % name
    keys = object_keys(object_literal(text, decl.end()))
    assert "onError" in keys, "the shared handlers object states %s" % keys
    # The announcer is read out of the object both calls pass, and the describer it hands the
    # failure to is graded where it is authored. The form's own copy of this claim pinned one
    # line of the form's prose, so a commit that moved the sign-in error copy into the recovery
    # module -- the better change, with unit tests of its own -- read as a vanished announcer.
    statement = stmt(object_literal(text, decl.end()), "onError:")
    handler = re.fullmatch(r"onError: \((\w+): unknown\) => toast\.error\((\w+)\(\1\)\),", statement)
    assert handler, (
        "the shared onError is %s, which does not toast the failure it was handed through one "
        "describer call: the sign-in form's announcer changed shape and the two mutations that "
        "share it have to be re-read" % repr(statement))
    _, describer = handler.groups()
    assert describer not in re.findall(r"\bfunction (\w+)\(", text), (
        "%s is called by the shared onError and declared in the form too, so the sign-in failure "
        "copy has two authors" % describer)
    # Read as a statement rather than a line: prettier wrapped this import across six lines,
    # and a per-line scan then reported a describer that is right there in the header.
    imports = re.findall(
        r"import \{[^}]*\b%s\b[^}]*\} from \"(@/[^\"]+)\"" % re.escape(describer), text)
    assert len(imports) == 1, "%s is imported by %d statements, so the shared onError reads it " \
        "from somewhere this gate cannot name" % (describer, len(imports))
    module = imports[0]
    base = module.replace("@/", "frontend/src/")
    rel = next((p for p in (base + ".ts", base + ".tsx") if p in sources()), None)
    assert rel, "the form imports %s, which the source walk never reads" % module
    authors = [r for r, body in sources().items()
               if re.search(r"^export function %s\(" % re.escape(describer), body, re.M)]
    assert authors == [RECOVERY], "the sign-in describer %s is authored in %s" % (describer, authors)


def test_logout_is_the_one_mutation_in_the_app_that_cannot_reach_an_error_state():
    body = hook_body(AUTH_HOOKS, "useLogout")
    swallowed = [s for s in sites() if ".catch(() => undefined)" in s.body]
    assert len(swallowed) == 1 and swallowed[0].name == "useLogout", (
        "%d mutations swallow their rejection inside mutationFn: %s" % (
            len(swallowed), [s.where for s in swallowed])
    )
    assert stmt(body, "mutationFn:") == "mutationFn: () => authApi.logout().catch(() => undefined),", (
        "the sign-out request's own statement changed, so the claim about who can see its failure needs "
        "re-measuring"
    )
    settled = body[body.index("onSettled:") :]
    assert settled.index("tokenStore.clear();") < settled.index("qc.clear();") < settled.index('router.replace("/login");'), (
        "the local sign-out no longer runs in that order, which is the mechanism that makes a failed "
        "server logout indistinguishable from a successful one"
    )
    assert "onError" not in body, "useLogout announces a failure now, so this file's finding is stale"


def test_the_password_forms_announce_inline_while_the_signout_sites_announce_nothing():
    for hook, form in (("useForgotPassword", FORGOT), ("useResetPassword", RESET)):
        calls = callers(hook)
        assert all(c.keys and "onError" in c.keys for c in calls), "%s's calls pass %s" % (
            hook, [c.keys for c in calls]
        )
        assert not any(c.named for c in calls), "%s passes a named object, not inline call options" % hook
        assert {c.rel for c in calls} == {form}, "%s is called from %s, not only its own form" % (
            hook, sorted(c.rel for c in calls)
        )
    logout = callers("useLogout")
    assert sorted(c.rel.split("/")[-1] for c in logout) == ["page.tsx", "topbar.tsx"], (
        "the two sign-out sites are %s" % sorted(c.where for c in logout)
    )
    assert TOPBAR in {c.rel for c in logout}, "the topbar no longer signs out"
    assert sorted(tuple(c.keys) for c in logout) == [(), ("onSettled",)], (
        "a sign-out site now passes call options %s, so the local sign-out is spelled in more places "
        "than this file read" % [(c.where, c.keys) for c in logout]
    )
    for rel in sorted({c.rel for c in logout}):
        assert ".error" not in strip_comments(sources()[rel]), (
            "%s reads a mutation error, so the silent sign-out does have a reader after all" % rel.split("/")[-1]
        )


def test_the_failure_helper_has_one_author_and_every_message_is_spent_once():
    # The helper lives in `lib/hooks/actions.ts` and every mutation hook imports it
    # from there — one implementation of "what a failed write says to the user",
    # so the message cannot drift between two files that each wrote their own.
    authors = [
        rel
        for rel, text in sources().items()
        if re.search(r"^(?:export\s+)?function fail\(", text, re.M)
    ]
    assert authors == [FAILURE], "fail() is authored in %s" % authors
    text = sources()[FAILURE]
    assert "return (err: unknown) => toast.error(describe(err, fallbackKey));" in text, (
        "fail() no longer builds a toast from the caller's own fallback key"
    )
    messages = fail_messages()
    shared = {m: n for m, n in messages.items() if n > 1}
    # Where the keys are spent, per file, and the one-per-file sums. The count that used
    # to sit here -- a hand-copied total, refreshed each time a bridge grew a write -- could
    # only ever say "some number moved"; this says which file spent or unspent a key.
    uses = fail_uses()
    moved = {rel.split("/")[-1]: (want, uses.get(rel, 0)) for rel, want in sorted(SENTENCES.items())
             if uses.get(rel, 0) != want}
    outside = sorted(rel.split("/")[-1] for rel in set(uses) - set(SENTENCES))
    assert not moved and not outside, (
        "fail() keys per file moved (file: pinned, counted) %s; files outside the roster: %s"
        % (moved, outside))
    assert sum(uses.values()) == sum(messages.values()) == FAIL_USES, (
        "fail() keys: %d uses, %d distinct, pinned %d" % (
            sum(messages.values()), len(messages), FAIL_USES
        )
    )
    assert shared == SHARED_KEYS, (
        "the only key more than one write may spend is the inbox's own; shared: %s, pinned: %s"
        % (shared, SHARED_KEYS))
    assert "Delete failed." not in text, (
        "the collision this file spent is back: a toast again hides which record failed"
    )
    # The two deletes that used to share one sentence now each name their own record; each key
    # is pinned beside its holder's request verb so neither can drift alone.
    deletes = {
        "useDeleteResume": 'fail("failures.resumeDelete")',
        "useDeleteApplication": 'fail("failures.applicationDelete")',
    }
    for name, sentence in deletes.items():
        body = hook_body(ACTIONS, name)
        assert sentence in body, (
            "%s no longer names its own delete; an operation-blind toast hides what failed: %s" % (
                name, [line.strip() for line in body.splitlines() if "onError" in line])
        )
        assert "api.remove(" in body, (
            "%s announces a delete failure but its request is not the client's remove verb: %s" % (
                name, [line.strip() for line in body.splitlines() if "mutationFn" in line])
        )
    client = sources()[CLIENT]
    start = next(i for i, line in enumerate(client.splitlines()) if line.strip().startswith("remove:"))
    window = client.splitlines()[start : start + 3]
    assert any('method: "DELETE"' in line for line in window), (
        "the client's remove verb no longer sends DELETE, so the two mutations above announce a delete "
        "by calling something else: %s" % [line.strip() for line in window]
    )


def test_this_gate_reads_the_same_shipped_sources_as_the_gates_it_borrows():
    assert len(sources()) >= 100, "the shared source walk read %d files" % len(sources())
    assert len(sites()) == SITES, "the walk found %d sites against a roster of %d" % (len(sites()), SITES)
    assert len([s for s in sites() if s.hook_level]) == SITES - len(QUIET_AUTH), (
        "the hook-level count is not the roster less the named quiet set, so a site changed "
        "announcer without changing the quiet set this file reads")
    assert set(ROSTER) == {ACTIONS, AUTH_HOOKS, SOURCE_ACTIONS} | BRIDGE_HOOKS, (
        "the roster and the files this gate set out to read are different sets: %s"
        % sorted(set(ROSTER) ^ ({ACTIONS, AUTH_HOOKS, SOURCE_ACTIONS} | BRIDGE_HOOKS)))
    assert callers("useLogout") and callers("useLogin") and callers("useForgotPassword")
    for rel in (ACTIONS, AUTH_HOOKS, SOURCE_ACTIONS, CREDENTIALS, FORGOT, RESET, TOPBAR):
        assert rel in sources(), "%s is not in the population this gate reads" % rel
    assert TOPBAR in {c.rel for c in callers("useLogout")}, (
        "the topbar no longer signs out, so this file's two sign-out sites are a different pair"
    )


def test_the_headline_of_this_file_states_the_census_the_walk_measures():
    # The opening paragraph reads as a report on the app, so it is graded as one: every figure
    # it prints is re-measured here, in the same words the prose uses. A census that moves will
    # red this case beside the roster, which is the difference between a comment that rots and
    # a claim that has an author.
    prose = " ".join((__doc__ or "").split()).lower()
    pop = sites()
    quiet = [s for s in pop if not s.hook_level]
    files, announced = len({s.rel for s in pop}), len([s for s in pop if s.hook_level])
    spelled = {n: NUM_WORDS.get(n) for n in (files, len(quiet), len(quiet) - 1)}
    assert all(spelled.values()), (
        "the census grew past the words this case can read (%s): re-word the headline rather "
        "than let it go silently stale" % spelled)
    assert f"{len(pop)} mutation sites in {spelled[files]} files" in prose, (
        "the walk sees %d sites in %d files, which the opening paragraph no longer says" % (len(pop), files))
    assert f"{announced} declare their failure at the hook; the {spelled[len(quiet)]} that do " \
        f"not are all in ``auth.ts``" in prose, (
        "the announced/quiet split moved: %d hook-level, %d quiet at %s" % (
            announced, len(quiet), sorted({s.rel.split("/")[-1] for s in quiet})))
    assert f"{spelled[len(quiet) - 1]} of those {spelled[len(quiet)]} are announced by their caller" in prose, (
        "the caller-announced count moved: %d of the %d quiet hooks have an announcer at the call" % (
            len(quiet) - 1, len(quiet)))
    assert f"has a single author and {sum(fail_uses().values())} uses" in prose, (
        "fail() is now spent %d times, which the prose does not say" % sum(fail_uses().values()))

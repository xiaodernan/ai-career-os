"""Every mutation the app declares must have somebody who says so when it fails.

react-query gives a mutation two places to put an error handler, and the second one is invisible to a
reader of the hook file alone: the options object ``useMutation({...})`` accepts ``onError``, and so
does each *call* -- ``mutate(vars, { onError })`` -- with the call-level handlers running alongside the
hook's. A gate that reads only hooks therefore cannot answer the user-visible question, which is "when
this request fails, does anyone say so?". This file answers it per mutation site, app-wide, and follows
the caller's options through the one indirection the app actually uses: a named object handed to two
different mutations.

What the shipped code says, measured rather than assumed: 37 mutation sites in three files. 32 declare
their failure at the hook; the five that do not are all in ``auth.ts``. Four of those five are announced
by their caller -- the password forms pass inline call options, and the credentials form passes one
shared ``handlers`` object to both ``login.mutate`` and ``register.mutate``. The fifth, ``useLogout``, is
announced by nobody, and its ``mutationFn`` swallows the rejection (``.catch(() => undefined)``), so the
mutation cannot even enter an error state for a screen to read; its ``onSettled`` clears the token,
clears the cache and redirects regardless of what the server said. That is a design choice -- a local
sign-out always happens -- so this file characterises it rather than changing it: it is the one place in
the app where "you are signed out" is not a claim about the server.

The same walk covers the failure helper: ``fail(...)`` has a single author and 29 uses, and every use
spends a distinct sentence -- when this file first walked it, 28 were distinct, because two different
deletes shared "Delete failed." and the toast never said which record survived the failure. Each delete
now names its own record, and the case below pins the spent state so a reused sentence goes red rather
than quietly shipping.
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
CLIENT = "frontend/src/lib/api/client.ts"
CREDENTIALS = "frontend/src/components/auth/credentials-form.tsx"
FORGOT = "frontend/src/components/auth/forgot-password-form.tsx"
RESET = "frontend/src/components/auth/reset-password-form.tsx"
TOPBAR = "frontend/src/components/layout/topbar.tsx"

DECL = re.compile(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\s+(\w+)|const\s+(\w+)\s*=)", re.M)


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


def fail_messages() -> collections.Counter:
    """Every ``fail("...")`` message the app builds a handler from."""
    out: collections.Counter = collections.Counter()
    for text in sources().values():
        out.update(m.group(1) for m in re.finditer(r'fail\("([^"]*)"\)', text))
    return out


def stmt(body: str, needle: str) -> str:
    """The one line of a body that holds ``needle``, stripped."""
    hits = [line.strip() for line in body.splitlines() if needle in line]
    assert len(hits) == 1, "%r matches %d lines, so the claim does not name one statement" % (needle, len(hits))
    return hits[0]


# ------------------------------------------------------------------ cases


def test_every_mutation_the_app_declares_sits_in_a_function_the_walk_can_name():
    pop = sites()
    # 39 rather than 38 since `useGrowthReport` (10.3) joined, announcing its failure at the
    # hook like the memory card's pair before it (38's own history is below). Before them,
    # `useRenameConversation`, `useDeleteConversation` (6a1c620) and `useImportJob` (bf2d91b)
    # were the last to join. Those commits changed the population without this census, which
    # is what this assertion is for -- it went red rather than quietly covering fewer sites.
    assert len(pop) == 39, "the app declares %d mutations" % len(pop)
    per_file = collections.Counter(s.rel for s in pop)
    assert per_file[AUTH_HOOKS] == 5 and per_file[ACTIONS] >= 25, "sites per hook file: %s" % dict(
        (k.split("/")[-1], v) for k, v in per_file.items()
    )
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


def test_the_hook_announces_thirty_four_failures_and_the_five_that_stay_quiet_are_all_auth():
    quiet = [s for s in sites() if not s.hook_level]
    assert len(quiet) == 5, "%d mutations announce nothing at the hook: %s" % (
        len(quiet), [s.where for s in quiet]
    )
    assert sorted(s.name for s in quiet) == [
        "useForgotPassword", "useLogin", "useLogout", "useRegister", "useResetPassword",
    ], "the hook-level silent set moved: %s" % sorted(s.name for s in quiet)
    assert {s.rel for s in quiet} == {AUTH_HOOKS}
    assert len([s for s in sites() if s.hook_level]) == 34
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
    assert stmt(text, "onError: (err: unknown) => toast.error(describeError(err)),") == (
        'onError: (err: unknown) => toast.error(describeError(err)),'
    )
    assert re.search(r"function describeError\(", text), (
        "the shared onError no longer maps the failure through the form's own describer"
    )


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
    authors = [rel for rel, text in sources().items() if re.search(r"^function fail\(", text, re.M)]
    assert authors == [ACTIONS], "fail() is authored in %s" % authors
    text = sources()[ACTIONS]
    assert "return (err: unknown) => toast.error(describe(err, fallback));" in text, (
        "fail() no longer builds a toast from the caller's own fallback sentence"
    )
    messages = fail_messages()
    reused = sorted(m for m, n in messages.items() if n > 1)
    # 32 rather than 31: the growth page's report spent its own sentence
    # ("Couldn't build the growth report.") on top of the memory card's pair.
    assert sum(messages.values()) == 32 and not reused, (
        "fail() messages: %d uses, %d distinct, reused: %s" % (
            sum(messages.values()), len(messages), reused
        )
    )
    assert "Delete failed." not in text, (
        "the collision this file spent is back: a toast again hides which record failed"
    )
    # The two deletes that used to share one sentence now each name their own record; each sentence
    # is pinned beside its holder's request verb so neither can drift alone.
    deletes = {
        "useDeleteResume": 'fail("Couldn\'t delete the resume.")',
        "useDeleteApplication": 'fail("Couldn\'t delete that application.")',
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
    assert len(sites()) == 39 and len([s for s in sites() if s.hook_level]) == 34
    assert callers("useLogout") and callers("useLogin") and callers("useForgotPassword")
    for rel in (ACTIONS, AUTH_HOOKS, SOURCE_ACTIONS, CREDENTIALS, FORGOT, RESET, TOPBAR):
        assert rel in sources(), "%s is not in the population this gate reads" % rel
    assert TOPBAR in {c.rel for c in callers("useLogout")}, (
        "the topbar no longer signs out, so this file's two sign-out sites are a different pair"
    )
    outside = sorted({s.rel for s in sites()} - {ACTIONS, AUTH_HOOKS, SOURCE_ACTIONS})
    assert not outside, "a mutation appeared in a file this gate does not account for: %s" % outside

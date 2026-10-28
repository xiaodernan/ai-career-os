"""Every value the app writes into a cache key, against what the query owning that key produces.

``invalidateQueries`` promises a refetch; ``setQueryData`` promises something stricter and far less
discussed: it puts a value into the slot a query owns, and from then on every component reading that
slot believes it. Nothing checks the shape of what goes in. A wrong *key* is a refresh that refreshes
nothing -- the previous gate's subject, and a silence. A wrong *value* is worse, because it looks
like data: a screen rendering a field no producer ever emitted. So the two vocabularies have to be
kept apart. A request body is a set of **commands** ("set this", "clear that"); cached state is a set
of **answers** ("this row's reminder instant"). ``{...row, ...command}`` conflates them in one line,
and TypeScript cannot see the conflation, because the patch is an interface of optional keys and the
row an interface of nullable ones.

Twelve sites in ``frontend/src`` write a cache value. Ten spell their key in the source; the other
two -- the rollbacks in ``useReorderApplication`` and ``useUpdateApplication`` -- write back a key
each enumerated at runtime, which no static read can name. Three put a route's answer into
``["me"]``, and three put the inbox write's answer into ``["notifications"]``; three put a snapshot
back where it was read from; and three *merge*: one preserves a wrapper object it had just read
(``["job", id]``), two rewrite one page's ``items`` in place (``["applications"]``). Case 12 rebuilds
that sentence from the walk, because this header shipped
"seven sites ... six spell their key ... two merge" for a run of commits after the reorder board
copied the update hook's optimistic shape wholesale -- the numbers a reader trusts most are the ones
nobody grades. Seven files make the app's react-query calls, across eight methods, and case 1's roster
is where a new one has to be filed.

The other thing this header shipped was a finding it said it would not fix: the row merge spread
``UpdateApplicationBody`` -- five command keys -- onto a row produced by ``normalizeApplication``, and
exactly one command key, ``clearReminderAt``, is not an answer name. The server honors it
(``ApplicationService`` nulls the column) and the toast announces it ("Reminder cleared."), but the
spread could not express a removal, so the cached row kept its old ``reminderAt`` until the
``onSettled`` refetch landed. That was not a bounded lie nobody sees: ``kanban.tsx`` both draws the
reminder chip and decides ``overdue`` from ``app.reminderAt``, so the card on screen went on claiming
a reminder the user had just deleted, and the dialog that reopened read it back into its input. The
row is now built by ``optimisticApplicationRow``, which spreads the command and then nulls the field
the command clears -- and cases 9-10 grade the call site, the spread order and the shipped vitest
file that runs it, instead of characterising the window.

Five walks, none of which imports production code -- and none of which rediscovers the cache either.
This file borrows the previous gate's source walk, its comment blanking and its balanced scanner:
a second parser of the same calls would be a second thing to drift, so the shared population is
itself one of the cases.

1. the react-query **client** vocabulary: every ``qc.<method>(`` site, filed by the source that makes
   it and compared method-by-method against the sites the borrowed walk reads there, so the two gates
   close over one population and the single method that carries no key is named rather than assumed;
2. the twelve writes, each read for its arguments as its own source spells them, its value classified
   structurally as answer / snapshot / merge, and its key resolved by the walk's prefix rule;
3. the name sets each value is built from: ``useJob``'s returned wrapper, ``normalizePage``'s
   envelope, ``normalizeApplication``'s row, ``UpdateApplicationBody``, ``ReminderPatch``;
4. the prose: the docstring that enumerates the PATCH, the comment that states the clear's spelling,
   the freshness sentence the two un-invalidated writes rest on, and this header's own census of the
   walk it is built from;
5. the server: the two ``/me`` handlers' shared answer type, and the handler that acts on
   ``clearReminderAt``.
"""

from __future__ import annotations

import collections
import re

from tests.test_invalidated_keys_are_queries_screens_mount import (
    ACTIONS,
    AUTH_HOOKS,
    PROMISE,
    QUERY_HOOKS,
    RESOURCES,
    balanced_end,
    call_regions,
    declarations,
    enclosing_fn,
    hook_body,
    literal_text,
    mounted,
    opaque_key_sites,
    promises,
    read,
    segments,
    sources,
    strip_comments,
)
from tests.test_invalidated_keys_are_queries_screens_mount import (
    cache_reads_writes as cache_reads,
)

CLIENT = "frontend/src/lib/api/client.ts"
NORMALIZE = "frontend/src/lib/api/normalize.ts"
EDIT = "frontend/src/lib/application-edit.ts"
DIALOG = "frontend/src/components/applications/application-dialog.tsx"
KANBAN = "frontend/src/components/common/kanban.tsx"
ACTIONS_TEST = "frontend/src/lib/hooks/actions.test.ts"
USER_JAVA = "backend/src/main/java/com/careeros/user/web/UserController.java"
APP_SERVICE = "backend/src/main/java/com/careeros/application/service/ApplicationService.java"
APP_DTOS = "backend/src/main/java/com/careeros/application/dto/ApplicationDtos.java"
RESUMES_PAGE = "frontend/src/app/(app)/resumes/page.tsx"
SOURCE_ACTIONS = "frontend/src/components/knowledge/source-actions.tsx"
INGESTION_HOOKS = "frontend/src/lib/hooks/ingestion.ts"
ANALYTICS_HOOKS = "frontend/src/lib/hooks/analytics.ts"
NOTIFICATION_HOOKS = "frontend/src/lib/hooks/notifications.ts"

WRITERS = ("setQueryData", "setQueriesData")
READERS = ("getQueryData", "getQueriesData")
OPTIONS_KEY = ("invalidateQueries", "cancelQueries", "removeQueries", "setQueriesData", "getQueriesData")
POSITIONAL_KEY = ("setQueryData", "getQueryData", "ensureQueryData")
KEYED = (PROMISE,) + OPTIONS_KEY + POSITIONAL_KEY
BLANKED = tuple(sources().values())
ANSWER = "answer"
SNAPSHOT = "snapshot"
MERGE = "merge"
QC_CALL = re.compile(r"(?<![\w$])qc\.(\w+)\s*(?=<|\()")

#: Every react-query client call the app makes, by the file that makes it and the method it calls.
#: Three walks read this population -- the token scan below, this gate's balanced one, and the
#: invalidation gate's -- and until now each was checked against a hand-copied *sum*, which can only
#: ever report that a number moved. Filed by file, a spent call names the file that spent it, and the
#: three walks can be made to agree per file rather than merely in total.
CLIENT_CALLS = {
    ACTIONS: {"cancelQueries": 3, "getQueriesData": 2, "getQueryData": 1,
              "invalidateQueries": 52, "removeQueries": 1, "setQueriesData": 2, "setQueryData": 5},
    ANALYTICS_HOOKS: {"invalidateQueries": 1},
    AUTH_HOOKS: {"clear": 2, "setQueryData": 2},
    INGESTION_HOOKS: {"invalidateQueries": 7},
    NOTIFICATION_HOOKS: {"setQueryData": 3},
    RESUMES_PAGE: {"invalidateQueries": 1},
    SOURCE_ACTIONS: {"invalidateQueries": 1},
}
SITES = sum(sum(m.values()) for m in CLIENT_CALLS.values())
#: ``KEYED`` lists ``invalidateQueries`` twice (it is both the promise method and an options-key
#: one), so the roster sums over the *set* of keyed names; summing the tuple counted 52 promises twice.
KEYED_NAMES = set(KEYED)
KEYED_SITES = sum(sum(c for n, c in m.items() if n in KEYED_NAMES) for m in CLIENT_CALLS.values())
WRITE_SITES = sum(sum(m.get(n, 0) for n in WRITERS) for m in CLIENT_CALLS.values())
READ_SITES = sum(sum(m.get(n, 0) for n in READERS) for m in CLIENT_CALLS.values())
PROMISE_SITES = sum(m.get(PROMISE, 0) for m in CLIENT_CALLS.values())
#: The card that made the window this file's finding described visible: its staleness predicate and
#: its reminder chip both read the field the command was supposed to have emptied.
CARD_READS = ("const overdue = Boolean(app.reminderAt)", "{app.reminderAt && (")
#: The words the header's census sentence spells its counts with, so case 12 can rebuild it.
NUM_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
             8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def java(rel: str) -> str:
    """A Java source on this file's plane, comments blanked, so prose cannot arm a code scan."""
    return strip_comments(read(rel))


# ------------------------------------------------------------------ balanced argument/object reads


def split_args(inner: str, sep: str = ",") -> list[str]:
    """Top-level split on ``sep``, generic parameter lists included.

    ``<`` and ``>`` are only delimiters when they read as a generic: a ``>`` after ``=`` is an arrow,
    and a ``<`` only opens a list after an identifier, a dot or another ``>``. Without that, the
    comma inside ``Record<string, unknown>`` -- which ``useJob`` really does spell in its return --
    would invent an entry. An entry this reader cannot name raises, so a wrong guess is loud.
    """
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    lt = 0
    quote = ""
    i = 0
    while i < len(inner):
        ch = inner[i]
        if quote:
            buf.append(ch)
            if ch == "\\":
                if i + 1 < len(inner):
                    buf.append(inner[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = ""
        elif ch in "\"'`":
            quote = ch
            buf.append(ch)
        elif ch in "([{":
            depth += 1
            buf.append(ch)
        elif ch in ")]}":
            depth -= 1
            buf.append(ch)
        elif ch == "<" and buf and (buf[-1].isalnum() or buf[-1] in "._>"):
            lt += 1
            buf.append(ch)
        elif ch == ">" and buf[-1] != "=" and lt > 0:
            lt -= 1
            buf.append(ch)
        elif ch == sep and depth == 0 and lt == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    parts.append("".join(buf))
    assert depth == 0 and lt == 0 and not quote, "unbalanced fragment: %r" % inner[:60]
    return [p.strip() for p in parts if p.strip()]


def object_entries(lit: str) -> tuple[list[tuple[str, str]], int]:
    """An object literal's [(name, value text)] plus the number of entries that are spreads."""
    assert lit.startswith("{"), repr(lit[:40])
    end = balanced_end(lit, 0, "{", "}")
    assert end == len(lit), "object literal does not close where it was handed: %r" % lit[:40]
    entries: list[tuple[str, str]] = []
    spreads = 0
    for part in split_args(lit[1:-1]):
        if part.startswith("..."):
            spreads += 1
            continue
        m = re.match(r"^\[\w+\]:\s*", part) or re.match(r"^(\w+)\s*:\s*", part)
        if m:
            entries.append((m.group(1) if m.lastindex else "*", part[m.end() :]))
        elif re.match(r"^\w+$", part):
            entries.append((part, part))
        else:
            raise AssertionError("object entry this reader cannot name: %r" % part[:60])
    return entries, spreads


def keys_of(lit: str) -> set[str]:
    return {k for k, _ in object_entries(lit)[0]}


def interface_keys(rel: str, name: str) -> set[str]:
    """The property names an ``export interface`` declares -- members end at a semicolon, not a comma."""
    text = sources()[rel]
    m = re.search(r"^export interface %s\b" % re.escape(name), text, re.M)
    assert m, "%s does not declare interface %s" % (rel, name)
    brace = text.index("{", m.end())
    inner = text[brace + 1 : balanced_end(text, brace, "{", "}") - 1]
    out = set()
    for part in split_args(inner, ";"):
        declared = re.match(r"^(\w+)\??\s*:", part)
        assert declared, "interface member this reader cannot name: %r" % part[:60]
        out.add(declared.group(1))
    return out


def fn_body(rel: str, fn: str) -> str:
    """A top-level function's own text, generic parameter list included.

    The borrowed ``hook_body`` demands ``function NAME(``, which is true of every hook but not of
    ``normalizePage<T>`` -- and a reader that quietly returns nothing for a generic function would
    make this gate's shape claims about the page envelope vacuous.
    """
    text = sources()[rel]
    m = re.search(r"^(?:export )?(?:async )?function %s\b" % re.escape(fn), text, re.M)
    assert m, "%s does not declare function %s" % (rel, fn)
    i = m.end()
    if i < len(text) and text[i] == "<":
        i = balanced_end(text, i, "<", ">")
    while i < len(text) and text[i] not in "({":
        i += 1
    assert i < len(text), "%s: no parameter list after function %s" % (rel, fn)
    brace = text.index("{", balanced_end(text, i, "(", ")")) if text[i] == "(" else i
    return text[m.start() : balanced_end(text, brace, "{", "}")]


def returned_keys(rel: str, fn: str, want: int) -> set[str]:
    """Every key stated outright by one function's own ``return { ... }``, unioned over branches."""
    body = fn_body(rel, fn)
    lits = []
    for m in re.finditer(r"\breturn\s*(\{)", body):
        lits.append(body[m.start(1) : balanced_end(body, m.start(1), "{", "}")])
    assert lits, "%s in %s returns no object literal" % (fn, rel)
    out: set[str] = set()
    for lit in lits:
        out |= keys_of(lit)
    assert want <= len(out), "%s states %d names, below the %d this case needs" % (fn, len(out), want)
    return out


class Call:
    """One react-query client call: its key as the source spells it, its arguments, its value."""

    def __init__(self, rel: str, text: str, name: str, open_i: int, args: list[str]):
        self.rel = rel
        self.callee = name
        self.line = text[:open_i].count("\n") + 1
        self.fn = enclosing_fn(text, open_i)
        self.args = args
        self.annotation = self._annotation(text, open_i, name)
        self.key = self._key(name, args)
        self.segs = segments(self.key) if self.key else ("*",)

    @staticmethod
    def _annotation(text: str, open_i: int, name: str) -> str:
        i = text.rindex(name, 0, open_i)
        return text[i + len(name) : open_i].strip()

    @staticmethod
    def _key(name: str, args: list[str]) -> str | None:
        if name in OPTIONS_KEY:
            assert args, "%s() takes no argument" % name
            m = re.search(r"(?<!\w)queryKey:\s*(\[)", args[0])
            if not m:
                return None
            start = args[0].index(m.group(1))
            return args[0][start : balanced_end(args[0], start, "[", "]")]
        if name in POSITIONAL_KEY:
            assert args, "%s() takes no argument" % name
            return args[0] if args[0].startswith("[") else None
        return None

    @property
    def where(self) -> str:
        return "%s:%d [%s]" % (self.rel.split("/")[-1], self.line, self.fn)

    def annotated_keys(self) -> set[str]:
        """The names a read's own type argument states -- what the writer believed the shape was."""
        m = re.search(r"\{[^{}]*\}", self.annotation)
        assert m, "%s: annotation %r states no object shape" % (self.where, self.annotation)
        return keys_of(m.group(0))

    def __repr__(self) -> str:
        return "%s %s%s %s" % (self.where, self.callee, self.annotation, self.segs)


def calls(rel: str) -> list[Call]:
    text = sources()[rel]
    return [Call(rel, text, n, o, split_args(text[o + 1 : e - 1])) for n, o, e in call_regions(text)]


def all_calls() -> list[Call]:
    return [c for rel in sorted(sources()) for c in calls(rel)]


def keyed_calls(names: tuple[str, ...]) -> list[Call]:
    return [c for c in all_calls() if c.callee in names]


def writes() -> list[Call]:
    out = []
    for c in keyed_calls(WRITERS):
        assert len(c.args) == 2, "%s: a %s with %d arguments" % (c.where, c.callee, len(c.args))
        if c.callee == "setQueriesData":
            assert "queryKey:" in c.args[0], "%s: options without a queryKey" % c.where
        c.value = c.args[1]
        c.form = classify(c)
        out.append(c)
    return out


def reads() -> list[Call]:
    return [c for c in keyed_calls(READERS)]


def snapshot_names(rel: str, fn: str) -> set[str]:
    """The names a hook's own snapshot machinery binds.

    A read's target (``previous``), a rollback loop's destructuring (``key``, ``data``), and the same
    names reached through the callback's context record (``ctx.previous``) -- which is how react-query
    hands ``onMutate``'s return value to ``onError``.
    """
    body = hook_body(rel, fn)
    bases = set(re.findall(r"const (\w+) = qc\.getQuer", body))
    for m in re.finditer(r"\.forEach\(\(\[(\w+), (\w+)\]\)", body):
        bases.update(m.groups())
    out = set(bases)
    for ctx in re.findall(r"on(?:Error|Success|Settled): \((?:\w+ *, *){2}(\w+)", body):
        out.update("%s.%s" % (ctx, base) for base in bases)
    return out


def answer_name(rel: str, fn: str) -> str | None:
    m = re.search(r"onSuccess: \((\w+)", hook_body(rel, fn))
    return m.group(1) if m else None


def value_object(text: str) -> str:
    """The object literal a write's value evaluates to.

    Either the argument itself, or the object an updater function returns -- an updater's body is a
    statement block, so reading it as a literal would invent entries like ``if (!cur?.items)``.
    """
    if text.startswith("{"):
        end = balanced_end(text, 0, "{", "}")
        assert end == len(text), "the write's value is not one object literal: %r" % text[:40]
        return text
    m = re.search(r"\breturn\s*(\{)", text)
    assert m, "a cache-write value that is neither an object literal nor a function returning one"
    start = m.start(1)
    return text[start : balanced_end(text, start, "{", "}")]


def classify(c: Call) -> str:
    """Why the write exists: a fresh answer, a snapshot put back, or something built from both."""
    if c.value.startswith("{") or "=>" in c.value:
        return MERGE
    if c.value == answer_name(c.rel, c.fn):
        return ANSWER
    if c.value in snapshot_names(c.rel, c.fn):
        return SNAPSHOT
    raise AssertionError("%s writes %r, which is neither an answer nor a snapshot" % (c.where, c.value))


def stmt(rel: str, needle: str) -> str:
    """The one shipped line containing ``needle``."""
    hits = [line for line in sources()[rel].split("\n") if needle in line]
    assert len(hits) == 1, "%s: %r matches %d lines" % (rel, needle, len(hits))
    return hits[0]


def qc_calls_by_file() -> dict[str, collections.Counter]:
    """Every ``qc.<method>(`` site, filed by the source that makes it, generic arguments included."""
    out: dict[str, collections.Counter] = {}
    for rel, text in sources().items():
        counted = collections.Counter(m.group(1) for m in QC_CALL.finditer(text))
        if counted:
            out[rel] = counted
    return out


def qc_calls() -> collections.Counter:
    """The same census summed over files, which is the shape the header's census sentence counts."""
    out: collections.Counter = collections.Counter()
    for counted in qc_calls_by_file().values():
        out.update(counted)
    return out


def by_file(items: list) -> dict[str, collections.Counter]:
    """One walk's own sites, filed the same way, so two walks can be made to agree per file."""
    out: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for item in items:
        out[item.rel][item.callee] += 1
    return {rel: collections.Counter(counts) for rel, counts in sorted(out.items()) if counts}


def clients() -> list[str]:
    """The names the app binds a query client under -- the census regex's whole reach."""
    return sorted(set(re.findall(r"const (\w+) = useQueryClient\(\)", "".join(BLANKED))))


def decls_for(segs: tuple[str, ...]) -> list:
    """The walk's own prefix rule, restated here so a write's owners are readable by key shape."""
    return [d for d in declarations() if d.segs[: len(segs)] == segs]


# --- case 1: the two gates audit one population, filed by the file that calls ------------------


def test_the_cache_methods_the_app_calls_are_the_methods_the_key_walk_covers():
    census = qc_calls_by_file()
    assert clients() == ["qc"], "the app binds the query client under %s, so a qc-shaped census is blind" % clients()
    # The roster is the whole claim: both halves of a move matter, since a call added in one file and
    # spent in another keeps the old total exactly. A new *kind* of call has to be filed here by
    # whoever adds it, which is the point -- it would otherwise be covered by no bucket at all.
    moved = []
    for rel in sorted(set(census) | set(CLIENT_CALLS)):
        got, want = census.get(rel, collections.Counter()), collections.Counter(CLIENT_CALLS.get(rel, {}))
        if got != want:
            moved.append((rel.split("/")[-1],
                          {n: (want[n], got[n]) for n in sorted(set(got) | set(want)) if got[n] != want[n]}))
    assert not moved, "client-call roster and the walk disagree (file: pinned, counted) %s" % moved
    unkeyed = {rel: sorted(set(m) - set(KEYED)) for rel, m in CLIENT_CALLS.items() if set(m) - set(KEYED)}
    assert unkeyed == {AUTH_HOOKS: ["clear"]}, "no bucket exists for %s" % unkeyed
    # The two walks that key their sites must read what this file's token census reads, in the same
    # file, the same number of times. Three dict sums agreeing is not three dict claims agreeing.
    expected = {rel: collections.Counter({n: c for n, c in m.items() if n in KEYED})
                for rel, m in CLIENT_CALLS.items() if any(n in KEYED for n in m)}
    mine = by_file(keyed_calls(KEYED))
    theirs = by_file(cache_reads() + opaque_key_sites() + promises())
    assert mine == expected, "this gate's keyed walk reads %s, the roster files %s" % (mine, expected)
    assert theirs == expected, "the invalidation gate's walks read %s, the roster files %s" % (theirs, expected)
    assert sum(c["clear"] for c in census.values()) == SITES - KEYED_SITES == 2, (
        "the only calls neither gate can key are the %d that carry no key" % (SITES - KEYED_SITES)
    )


def test_the_keyless_clear_is_the_two_signout_handlers_and_nothing_else():
    hits = [rel for rel, text in sources().items() if "qc.clear()" in text]
    assert hits == [AUTH_HOOKS], "qc.clear() is called from %s" % hits
    assert sources()[AUTH_HOOKS].count("qc.clear();") == 2, "qc.clear() is not spelled with empty parens twice"
    owners = [f for f in ("useLogout", "useResetPassword") if "qc.clear();" in hook_body(AUTH_HOOKS, f)]
    assert len(owners) == 2, "qc.clear() is not inside both signout handlers: %s" % owners
    for f in owners:
        body = hook_body(AUTH_HOOKS, f)
        assert body.index("tokenStore.clear();") < body.index("qc.clear();"), (
            "%s drops the cache before the token, so a request still in flight can re-fill the cache "
            "with an answer for the account that just signed out" % f
        )


# --- case 2: twelve writes, and every key they name is owned by something a screen mounts ------


def test_the_write_ledger_names_every_site_and_the_key_and_form_each_one_has():
    sites = writes()
    assert len(sites) == WRITE_SITES, "the write walk found %s" % [repr(c) for c in sites]
    ledger = sorted((c.where.split(":")[0], c.fn, c.segs, c.form) for c in sites)
    assert ledger == [
        ("actions.ts", "useReorderApplication", ("*",), "snapshot"),
        ("actions.ts", "useReorderApplication", ("applications",), "merge"),
        ("actions.ts", "useToggleSaveJob", ("job", "*"), "merge"),
        ("actions.ts", "useToggleSaveJob", ("job", "*"), "snapshot"),
        ("actions.ts", "useUpdateApplication", ("*",), "snapshot"),
        ("actions.ts", "useUpdateApplication", ("applications",), "merge"),
        ("actions.ts", "useUpdateProfile", ("me",), "answer"),
        ("auth.ts", "useLogin", ("me",), "answer"),
        ("auth.ts", "useRegister", ("me",), "answer"),
        ("notifications.ts", "useDismissNotification", ("notifications",), "answer"),
        ("notifications.ts", "useMarkAllNotificationsRead", ("notifications",), "answer"),
        ("notifications.ts", "useMarkNotificationsRead", ("notifications",), "answer"),
    ], "the write ledger moved: %s" % ledger
    computed = [c for c in sites if c.key is None]
    assert len(computed) == 2 and {c.fn for c in computed} == {"useUpdateApplication", "useReorderApplication"}, (
        "the writes whose keys no static read can name are %s" % [c.where for c in computed]
    )


def test_every_key_a_write_names_is_owned_by_a_query_a_screen_mounts():
    owned = {}
    for c in writes():
        if c.key is None:
            continue
        hit = decls_for(c.segs)
        assert hit, "write %s puts a value under %s, which no query declares" % (c.where, c.segs)
        assert any(mounted(d) for d in hit), "write %s overwrites only queries no screen mounts" % c.where
        owned[c.segs] = sorted({d.fn for d in hit})
    assert owned == {("me",): ["useUser"], ("job", "*"): ["useJob"], ("applications",): ["useApplications"],
                     ("notifications",): ["useNotifications"]}, (
        "the key-to-owner map moved: %s" % owned
    )


# --- cases 3-4: the me writes, whose two producers are one call -------------------------------


def test_the_three_me_writes_put_in_the_answer_the_me_query_fetches():
    me = [c for c in writes() if c.segs == ("me",)]
    assert len(me) == 3, "%d writes name the me key" % len(me)
    for c in me:
        assert c.form == ANSWER and c.value == "user", "%s writes %r as %s" % (c.where, c.value, c.form)
        assert "onSuccess: (user) => {" in hook_body(c.rel, c.fn), (
            "%s's `user` is no longer the name the handler binds to the answer" % c.where
        )
    declared = [d for d in declarations() if d.segs == ("me",)]
    assert len(declared) == 1 and declared[0].fn == "useUser", "the me key is owned by %s" % [d.fn for d in declared]
    # One route and one answer type, reached by two callers: login and register end by asking /me who
    # the user is, with the very function the query uses as its queryFn. So the value they cache is not
    # a different shape from the one a refetch would have written -- it is the same call's answer.
    assert stmt(AUTH_HOOKS, "queryFn: authApi.me") == "    queryFn: authApi.me,"
    for fn, api in (("useLogin", "login"), ("useRegister", "register")):
        assert "mutationFn: authApi.%s," % api in hook_body(AUTH_HOOKS, fn), "%s no longer delegates to authApi.%s" % (fn, api)
        assert "return authApi.me();" in api_body(api), (
            "%s's mutation no longer ends on /me, so the value it hands to onSuccess is not a me answer" % fn
        )
    assert stmt(CLIENT, "request<User>(endpoints.auth.me)") == "    return request<User>(endpoints.auth.me);"
    assert "endpoints.auth.me" in hook_body(ACTIONS, "useUpdateProfile"), (
        "useUpdateProfile no longer PATCHes the same route the query GETs, so its write is an answer "
        "from a different record"
    )


def api_body(name: str) -> str:
    """One authApi method's body, read out of the object literal the client exports."""
    text = sources()[CLIENT]
    m = re.search(r"^  (?:async )?%s\(" % re.escape(name), text, re.M)
    assert m, "authApi has no %s method" % name
    brace = text.index("{", balanced_end(text, text.index("(", m.start()), "(", ")"))
    return text[brace : balanced_end(text, brace, "{", "}")]


def test_the_server_answers_both_me_routes_with_the_same_record():
    text = java(USER_JAVA)
    assert text.count('@GetMapping("/me")') == 1 and text.count('@PatchMapping("/me")') == 1
    get = re.search(r'@GetMapping\("/me"\)\s+public (\w+) me\(', text)
    patch = re.search(r'@PatchMapping\("/me"\)\s+public (\w+) updateMe\(', text)
    assert get and patch, "one of the two /me handlers no longer returns a named record"
    assert get.group(1) == patch.group(1) == "MeResponse", (
        "the GET answers %s while the PATCH answers %s, so the two writers of [\"me\"] are putting "
        "different shapes into one slot" % (get.group(1), patch.group(1))
    )


# --- case 5: the three writes differ in whether anyone promises to repair them ----------------


def test_only_one_of_the_three_me_writes_is_followed_by_a_refetch():
    """An answer written with no promise behind it is the cache's value until staleTime says otherwise."""
    invalidated = [p for p in promises() if p.segs == ("me",)]
    assert len(invalidated) == 1, "the me key is invalidated %d times: %s" % (
        len(invalidated), [p.where for p in invalidated]
    )
    body = hook_body(ACTIONS, "useUpdateProfile")
    assert body.index('setQueryData(["me"]') < body.index('invalidateQueries({ queryKey: ["me"] })'), (
        "useUpdateProfile now invalidates before it writes, so the value it also puts in the slot is "
        "one the refetch is already on its way to replace -- the write and the promise disagree about "
        "who owns the answer"
    )
    for fn in ("useLogin", "useRegister"):
        assert PROMISE not in hook_body(AUTH_HOOKS, fn), (
            "%s invalidates, so staleTime is no longer what bounds its write" % fn
        )
    assert stmt(AUTH_HOOKS, "staleTime:") == "    staleTime: 5 * 60_000,", "useUser's window changed spelling"
    assert 'queryKey: ["me"]' in hook_body(AUTH_HOOKS, "useUser"), "the window belongs to another query"


# --- cases 6-7: each merge, measured against the names its own key owner produces -------------


def test_the_job_merge_states_one_name_and_that_name_is_in_what_the_job_query_returns():
    sites = [c for c in writes() if c.fn == "useToggleSaveJob"]
    assert len(sites) == 2 and sorted(c.form for c in sites) == [MERGE, SNAPSHOT]
    merge = [c for c in sites if c.form == MERGE][0]
    stated, spreads = object_entries(value_object(merge.value))
    assert [k for k, _ in stated] == ["job"], "%s states %s, so the write no longer preserves the rest by spread" % (
        merge.where, [k for k, _ in stated]
    )
    assert spreads == 1, "%s keeps the wrapper with %d spreads" % (merge.where, spreads)
    returned = returned_keys(RESOURCES, "useJob", 7)
    assert "job" in returned, "useJob returns %s, none of which is the name the merge states" % sorted(returned)
    job_read = [c for c in reads() if c.fn == "useToggleSaveJob"][0]
    assert job_read.callee == "getQueryData", "the job snapshot is taken by %s" % job_read.callee
    assert job_read.annotated_keys() == {"job"}, "the snapshot is annotated %s" % job_read.annotation
    assert job_read.annotated_keys() <= returned, (
        "the snapshot annotation %s names a field useJob never returns, so the merge reads it back out "
        "of a shape that does not exist" % job_read.annotation
    )
    assert stmt(ACTIONS, "if (previous) {") == "      if (previous) {", (
        "the write is no longer guarded by the read, so a cold cache gets an object built from undefined"
    )


def test_the_applications_merge_rewrites_one_name_and_that_name_is_in_the_page_envelope():
    merge = [c for c in writes() if c.fn == "useUpdateApplication" and c.segs == ("applications",)][0]
    assert merge.form == MERGE and "=> {" in merge.value, "%s is %s" % (merge.where, merge.form)
    stated, spreads = object_entries(value_object(merge.value))
    assert [k for k, _ in stated] == ["items"], "%s states %s" % (merge.where, [k for k, _ in stated])
    assert spreads == 1, "the page merge no longer preserves the envelope with one spread"
    envelope = returned_keys(NORMALIZE, "normalizePage", 4)
    assert envelope == {"items", "total", "page", "size"}, "normalizePage answers %s" % sorted(envelope)
    page_read = [c for c in reads() if c.fn == "useUpdateApplication"][0]
    assert page_read.callee == "getQueriesData", "the page snapshot is taken by %s" % page_read.callee
    assert page_read.annotated_keys() == {"items"}, "the snapshot is annotated %s" % page_read.annotation
    # A prefix key: every cached page of this list is rewritten, so how many there are is a claim.
    owned = decls_for(("applications",))
    assert sorted(d.segs for d in owned) == [("applications", "*")], "applications is declared by %s" % [d.segs for d in owned]
    assert all(mounted(d) for d in owned)
    assert len(merge.segs) < len(owned[0].segs), "%s no longer reaches %s as a prefix" % (merge.segs, owned[0].segs)


# --- case 8: the writes no key read can see, and the reads that enumerate their keys -----------


def test_the_computed_key_writes_are_rollbacks_of_the_prefix_snapshots():
    opaque = opaque_key_sites()
    assert len(opaque) == 2, "the previous gate cannot read the key of %s" % [s.where for s in opaque]
    # The reorder board copied the update hook's optimistic shape wholesale -- the same
    # snapshot, the same replay, the same promise -- so both computed-key writes are pinned
    # by the same structural case, per hook.
    for fn in ("useUpdateApplication", "useReorderApplication"):
        row = next(c for c in opaque if c.fn == fn)
        assert (row.callee, row.fn) == ("setQueryData", fn)
        body = hook_body(ACTIONS, fn)
        assert "ctx?.previous?.forEach(([key, data]) => qc.setQueryData(key, data));" in body, (
            "%s's rollback no longer replays the (key, data) pairs the prefix read enumerated" % fn
        )
        assert "return { previous };" in body, "%s's snapshot no longer reaches the rollback" % fn
        assert body.index("getQueriesData") < body.index("forEach"), (
            "%s's read moved after the write it feeds" % fn
        )
        names = snapshot_names(ACTIONS, fn)
        assert {"previous", "key", "data"} <= names and "ctx.previous" in names, (
            "%s's rollback no longer replays names this hook binds from its own snapshot: %s"
            % (fn, sorted(names))
        )
        assert re.search(r"onError: \(\w+, \w+, ctx\)", body) or fn == "useReorderApplication", (
            "the third onError parameter is no longer the context record"
        )
        assert any(mounted(d) for d in decls_for(("applications",)))
        assert PROMISE in body, "%s promises no refetch, so the rollback is the only repair" % fn


# --- case 9: the row merge's spread is a command vocabulary, and one function owns it ----------


def test_the_row_the_cache_holds_is_built_by_one_named_merge_of_command_onto_row():
    merge = [c for c in writes() if c.fn == "useUpdateApplication" and c.segs == ("applications",)][0]
    assert "optimisticApplicationRow(a, patch)" in merge.value, (
        "%s no longer builds its row through the one named merge, so the command-to-row translation "
        "this file exists to grade has moved somewhere it cannot point at: %r" % (merge.where, merge.value[:80])
    )
    assert "a.id === id ? optimisticApplicationRow(a, patch) : a" in merge.value, (
        "the merge no longer rebuilds only the row the command names: %r" % merge.value[:80]
    )
    commands = interface_keys(ACTIONS, "UpdateApplicationBody")
    assert commands == {"status", "position", "note", "reminderAt", "clearReminderAt"}, (
        "the PATCH body now says %s" % sorted(commands)
    )
    row = returned_keys(NORMALIZE, "normalizeApplication", 17)
    assert len(row) >= 17, (
        "normalizeApplication states %d names, fewer than the 17 this finding was measured against: %s"
        % (len(row), sorted(row))
    )
    gap = commands - row
    assert gap == {"clearReminderAt"}, (
        "the merge spreads %s onto a row produced as %s: the keys that are not row names are %s"
        % (sorted(commands), sorted(row), sorted(gap))
    )
    assert commands & row == {"status", "position", "note", "reminderAt"}
    spreaders = sorted(rel.split("/")[-1] for rel, text in sources().items()
                       if "{ ...row, ...patch," in text)
    assert spreaders == ["actions.ts"], (
        "the command-onto-row spread has authors %s, so a clear can be un-translated somewhere this "
        "gate does not read" % spreaders
    )


# --- case 10: the one command that names a field rather than a value ---------------------------


def test_the_clear_is_announced_and_the_row_the_card_draws_loses_the_instant():
    """The window this file used to characterise: a removal is a command no row field can carry."""
    body = fn_body(ACTIONS, "optimisticApplicationRow")
    assert "export function optimisticApplicationRow(row: Application, patch: UpdateApplicationBody)" in body
    spread, nulled = body.index("...patch,"), body.index("{ reminderAt: null }")
    assert spread < nulled, (
        "the nulling pair is spread before the command, so a clear re-writes the row's own instant "
        "back over it"
    )
    assert "patch.clearReminderAt ?" in body[:nulled], (
        "the null is no longer conditional on the command that asks for it, so every optimistic write "
        "would drop the reminder"
    )
    assert ": null" in body[nulled:], "the else arm no longer contributes nothing: %r" % body[nulled : nulled + 40]
    hook = hook_body(ACTIONS, "useUpdateApplication")
    assert 'else if (patch.clearReminderAt) toast.success("Reminder cleared.");' in hook
    assert hook.index("optimisticApplicationRow(a, patch)") < hook.index("Reminder cleared."), (
        "the toast no longer follows the merge that removes the instant it announces"
    )
    tail = hook.split("onSettled:")[1]
    assert 'qc.invalidateQueries({ queryKey: ["applications"] });' in tail, (
        "nothing refetches the list once the response lands, so the row the merge built is the value "
        "rather than the guess"
    )
    assert hook.split("onSuccess:")[0].count(PROMISE) == 0, (
        "the optimistic hook now promises a refetch before the toast, so the repair is the refetch and "
        "this case would be describing a different design"
    )
    # The reader that made the window visible without opening anything: the board card reads the
    # field twice for its staleness predicate and twice more for the chip beside the date.
    card = sources()[KANBAN]
    for line in CARD_READS:
        assert line in card, "the card no longer reads the instant the way this claim says it does: %r" % line
    assert card.count("app.reminderAt") == 4, "the card reads app.reminderAt %d times" % card.count("app.reminderAt")
    # The shipped seam that runs the merge, so the claim above is not only a reading of one line.
    test = read(ACTIONS_TEST)
    imports = [line for line in test.splitlines() if 'from "@/lib/hooks/actions"' in line]
    assert len(imports) == 1 and "optimisticApplicationRow" in imports[0], (
        "the vitest file no longer imports the merge it is the behavioural reader for: %s" % imports
    )
    block = test[test.index('describe("optimisticApplicationRow"') :] if 'describe("optimisticApplicationRow"' in test else ""
    assert block, "actions.test.ts declares no describe block for the merge"
    assert re.search(r"optimisticApplicationRow\(row\(\), \{ clearReminderAt: true \}\)\.reminderAt\)\.toBeNull", block), (
        "the shipped test no longer runs a clear through the merge and expects the instant to be gone"
    )
    assert "reminderAt" in block and "optimisticApplicationRow(row(), { status:" in block, (
        "the shipped test no longer pins the other half: a command that says nothing about reminders "
        "must leave the instant alone"
    )


def test_the_key_the_merge_invents_is_emitted_once_translated_once_and_acted_on_by_the_server():
    authors = sorted(rel.split("/")[-1] for rel in sources() if re.search(r"^\s*clearReminderAt\?", sources()[rel], re.M))
    assert authors == ["actions.ts", "application-edit.ts"], "clearReminderAt is declared as a member by %s" % authors
    emitters = sorted(rel.split("/")[-1] for rel in sources() if "clearReminderAt: true" in sources()[rel])
    assert emitters == ["application-edit.ts"], "it is emitted as a value in %s" % emitters
    readers = sorted(rel.split("/")[-1] for rel, text in sources().items() if "patch.clearReminderAt" in text)
    assert readers == ["actions.ts"], "the command is read off a patch by %s, not only by the merge" % readers
    assert stmt(EDIT, "clearReminderAt: true") == "  return next ? { reminderAt: next } : { clearReminderAt: true };"
    assert len(interface_keys(EDIT, "ReminderPatch")) == 2, "ReminderPatch is the command's other author"
    assert sources()[DIALOG].count("reminderPatch(") == 1, "the dialog calls reminderPatch %d times" % sources()[DIALOG].count("reminderPatch(")
    assert stmt(DIALOG, "toReminderInput(application?.reminderAt)") == "    setReminder(toReminderInput(application?.reminderAt));"
    assert "clearReminderAt" not in strip_comments(read(DIALOG)), (
        "the dialog now reads the command name, which would make the merge's invention a real field"
    )
    assert "Boolean.TRUE.equals(request.clearReminderAt())" in java(APP_SERVICE), (
        "the server no longer acts on the key, so the command was never a command either"
    )
    assert "clearReminderAt" in java(APP_DTOS), "the DTO no longer binds it"


# --- case 10: the prose, bound to the code it describes ---------------------------------------


def test_the_docstring_that_lists_the_patch_names_a_strict_subset_of_the_body_the_caller_sends():
    text = read(ACTIONS)
    window = text[max(0, text.index("export function useUpdateApplication") - 400) : text.index("export function useUpdateApplication")]
    docs = re.findall(r"^/\*\* (.*) \*/$", window, re.M)
    assert docs, "useUpdateApplication has no docstring above it"
    doc = docs[-1]
    listed = re.search(r"PATCH \{([^}]*)\}", doc)
    assert listed, "the docstring no longer enumerates the PATCH: %r" % doc
    stated = {s.strip() for s in listed.group(1).split(",")}
    commands = interface_keys(ACTIONS, "UpdateApplicationBody")
    assert stated < commands, "the docstring says %s, which is not a strict subset of %s" % (sorted(stated), sorted(commands))
    assert commands - stated == {"reminderAt", "clearReminderAt"}, (
        "the sentence omits %s; the merge spreads all five, so the prose and the code disagree about "
        "which two keys the optimistic write is responsible for" % sorted(commands - stated)
    )
    assert "optimistic" in doc, "the sentence no longer claims the write this file is auditing"


def test_the_comment_that_explains_the_clear_quotes_the_key_the_function_emits():
    text = read(EDIT)
    decl = re.search(r"^export function reminderPatch\(", text, re.M)
    assert decl, "reminderPatch is no longer an exported declaration"
    close = text.rindex("*/", 0, decl.start())
    doc = text[text.rindex("/*", 0, close) : close]
    quoted = re.findall(r"`([^`]*)`", doc)
    assert "clearReminderAt" in quoted, "the comment's backticks hold %s" % quoted
    emitted = re.search(r"return next \? \{ (\w+): next \} : \{ (\w+): true \};", text)
    assert emitted, "reminderPatch no longer returns one of two single-key objects"
    assert emitted.group(2) == "clearReminderAt", "the comment promises clearReminderAt, the code returns %s" % emitted.group(2)
    words = sorted(q for q in quoted if re.fullmatch(r"[A-Za-z]\w*", q))
    assert words == ["clearReminderAt"], (
        "the backticks in the comment hold %s, while the function can return %s or %s: the key this "
        "gate calls an invention is the one the comment exists to explain"
        % (words, emitted.group(1), emitted.group(2))
    )
    assert "null component means" in doc, (
        "the claim this whole finding rests on -- that a null on that DTO means leave it alone -- is no "
        "longer stated, so the command key has no documented reason to exist"
    )


# --- case 11: the gate's own feet ------------------------------------------------------------


def test_this_gate_and_the_invalidation_gate_read_the_same_shipped_sources():
    assert len(sources()) >= 100, "the shared source walk read %d files" % len(sources())
    # Every one of these totals is now read off CLIENT_CALLS rather than typed in beside it, so the
    # only hand-copied number left in this file is the roster itself -- and a roster row that drifts
    # is case 1 naming the file, not a sum that lost a site.
    assert len(writes()) == WRITE_SITES and len(reads()) == READ_SITES, (
        "%s writes against a roster of %d, %s reads against %d"
        % (len(writes()), WRITE_SITES, len(reads()), READ_SITES)
    )
    assert len(promises()) == PROMISE_SITES, "the borrowed promise walk reads %d" % len(promises())
    assert len(keyed_calls(KEYED)) == KEYED_SITES, "the keyed population is %d" % len(keyed_calls(KEYED))
    assert len([c for c in all_calls() if c.callee in QUERY_HOOKS]) == len(declarations()), (
        "the walk's hook regions and the previous gate's declarations are different sets: %d vs %d"
        % (len([c for c in all_calls() if c.callee in QUERY_HOOKS]), len(declarations()))
    )
    for rel in (ACTIONS, AUTH_HOOKS, RESOURCES, NORMALIZE, CLIENT, EDIT, DIALOG, KANBAN):
        assert rel in sources(), "%s is not in the population this gate reads" % rel
    assert ACTIONS_TEST not in sources(), (
        "the vitest file is read as a shipped test, not as if it were app source: the walk skips tests"
    )
    assert USER_JAVA not in sources() and APP_SERVICE not in sources(), (
        "the Java plane is read through its own file, not as if it were TypeScript"
    )
    # One segment policy for both gates, and one text form for the ledger.
    assert segments('["job", id]') == ("job", "*") and segments("[key, data]") == ("*", "*")
    assert literal_text('["applications",\n  ]') == '["applications", ]', "the ledger's whitespace policy moved"
    assert decls_for(("applications",))[0].segs == ("applications", "*")
    # An oracle for the write population that is not this file's balanced walk: a token count.
    spelled = sum(text.count("qc.setQueryData(") + text.count("qc.setQueriesData<") for text in BLANKED)
    assert spelled == len(writes()) == WRITE_SITES, (
        "the token scan sees %d writes, the walk sees %d, the roster files %d"
        % (spelled, len(writes()), WRITE_SITES)
    )


# --- case 12: this header's own census, rebuilt from the walk it describes ---------------------


def word(n: int) -> str:
    assert n in NUM_WORDS, "the header has no spelled word for %d; add it beside the census" % n
    return NUM_WORDS[n]


def test_the_headline_of_this_file_counts_the_writes_the_walk_finds():
    prose = " ".join((__doc__ or "").split()).lower()
    sites = writes()
    computed = sorted({c.fn for c in sites if c.key is None})
    forms = collections.Counter(c.form for c in sites)
    merged = collections.Counter(c.segs for c in sites if c.form == MERGE)
    claims = [
        "%s sites in ``frontend/src`` write a cache value." % word(len(sites)),
        "%s spell their key in the source; the other %s -- the rollbacks in %s --" % (
            word(len(sites) - len(computed)), word(len(computed)),
            " and ".join("``%s``" % f for f in computed)),
        "%s put a route's answer into ``[\"me\"]``" % word(len([c for c in sites if c.segs == ("me",)])),
        "%s put a snapshot back where it was read from" % word(forms[SNAPSHOT]),
        "and %s *merge*: %s preserves a wrapper object it had just read (``[\"job\", id]``), %s rewrite "
        "one page's ``items`` in place (``[\"applications\"]``)" % (
            word(forms[MERGE]), word(merged[("job", "*")]), word(merged[("applications",)])),
        # The population case 1 files: read off the walk, so a fifth calling file moves the header
        # as well as the roster, and neither claim is a number typed beside the other.
        "%s files make the app's react-query calls, across %s methods" % (
            word(len(qc_calls_by_file())), word(len(qc_calls()))),
    ]
    spent = [claim for claim in claims if claim.lower() not in prose]
    assert not spent, "the header census no longer says what the walk measures: %s" % spent
    assert "deliberately does not fix" not in prose, (
        "this file is back to characterising a user-visible defect instead of grading its repair"
    )

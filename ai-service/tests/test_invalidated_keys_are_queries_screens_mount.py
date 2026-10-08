"""The cache keys the app promises to refresh, against the queries a screen actually mounts.

``invalidateQueries({queryKey: K})`` is a one-directional promise: it refetches every *mounted*
query whose key starts with ``K``. Nothing in TypeScript, and nothing in this repository until now,
notices when ``K`` stops matching. The call still returns, the mutation's toast still fires, and the
list the user is looking at keeps showing the row the server just deleted -- a refresh that refreshes
an empty set is silent in a way a 500 is not. So the promise is worth gating on two axes at once:
does ``K`` match a query the app declares, and is that declared query owned by a hook a screen
mounts? Both are answered from shipped text, because both are properties of how the source spells
the key.

Four walks, none of which imports production code:

1. every react-query cache call and query hook in ``frontend/src`` (comments blanked first, so a
   docstring that quotes a key cannot arm a scan), each read for the key array it passes -- the
   ``queryKey:`` property or the positional array -- which yields a promise from
   ``invalidateQueries``, a declaration from ``useQuery``, and an optimistic read or write from the
   rest. A call whose key the walk cannot read is not skipped but counted, and the last case pins
   that census to the one site that ships;
2. which declarations a screen mounts: a hook in ``lib/hooks`` is mounted iff its own name occurs
   somewhere else in the non-test sources; a key declared inside a page or component file is mounted
   by the file that renders it;
3. the resume detail screen, for the one chain where the prefix relation is the entire design;
4. the users controller, for the fact that the profile surface is real on the server and now has a
   screen to answer.

What the walk records, and does not fix: 46 promises, every one of them naming a declared key --
and since the settings page grew its account and career-profile editors, and the jobs page its
paste-a-posting importer, every promise's matches include a query a screen mounts, so the
dead-promise ledger this file used to pin is empty. Three declared
queries are still unmounted (`useResumeScore`, `useSourceStatus`, `useGlobalSearch`), each a
duplicate or a window onto data another hook already fetches, and every one of the three is bound
to the screen that answers the same routes without it (cases 8, 8b and 8c). Closing any of them
is an owner's choice
(mount a screen or delete the data layer), and the first cases make either move cost a ledger edit.
What is *not* a choice is the live chain: the Versions
panel on the resume detail screen refreshes after a parse only because the two mutations and the
query share a key prefix and a route parameter on one screen, and the last cases bind that claim to
the comment that states it.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = "frontend/src"

ACTIONS = "frontend/src/lib/hooks/actions.ts"
RESOURCES = "frontend/src/lib/hooks/resources.ts"
AUTH_HOOKS = "frontend/src/lib/hooks/auth.ts"
HOOK_FILES = (ACTIONS, RESOURCES, AUTH_HOOKS)
DETAIL = "frontend/src/app/(app)/resumes/[id]/page.tsx"
SETTINGS = "frontend/src/app/(app)/settings/page.tsx"
PALETTE = "frontend/src/components/common/command-palette.tsx"
ENDPOINTS = "frontend/src/lib/api/endpoints.ts"
CONTROLLER = "backend/src/main/java/com/careeros/user/web/UserController.java"
KNOWLEDGE_CONTROLLER = "backend/src/main/java/com/careeros/knowledge/web/KnowledgeController.java"
KNOWLEDGE_PAGE = "frontend/src/app/(app)/knowledge/page.tsx"

PROMISE = "invalidateQueries"
QUERY_HOOKS = ("useQuery", "useInfiniteQuery", "useSuspenseQuery")
OTHER_CACHE_CALLS = (
    "cancelQueries",
    "removeQueries",
    "setQueriesData",
    "setQueryData",
    "getQueriesData",
    "getQueryData",
    "ensureQueryData",
)
CALLABLES = (PROMISE,) + QUERY_HOOKS + OTHER_CACHE_CALLS


def read(rel: str) -> str:
    """A shipped file, on this file's own plane, with one line-ending policy."""
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def strip_comments(text: str) -> str:
    """Blank every comment, keeping offsets, so prose cannot arm a code scan.

    Quote-aware, because ``https://`` and ``//`` inside a string literal are not comments.
    """
    out = list(text)
    i, n = 0, len(text)
    quote = ""
    while i < n:
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch in "\"'`":
            quote = ch
            i += 1
            continue
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        i += 1
    return "".join(out)


def balanced_end(text: str, i: int, o: str, c: str) -> int:
    """Index just past the delimiter that closes the one at ``i``."""
    assert text[i] == o, (i, repr(text[i : i + 12]), o)
    depth = 0
    quote = ""
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch in "\"'`":
            quote = ch
        elif ch == o:
            depth += 1
        elif ch == c:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise AssertionError("unbalanced %s from %s" % (o, text[i - 60 : i + 12]))


@lru_cache(maxsize=1)
def sources() -> dict[str, str]:
    """Every non-test TypeScript source in the client, comments already blanked."""
    root = ROOT / SRC
    out = {}
    for p in sorted(root.rglob("*")):
        if p.suffix not in (".ts", ".tsx") or ".test." in p.name:
            continue
        out[SRC + "/" + p.relative_to(root).as_posix()] = strip_comments(read(p.relative_to(ROOT).as_posix()))
    assert len(out) >= 100, "the client walk read only %d files" % len(out)
    return out


def call_regions(text: str) -> list[tuple[str, int, int]]:
    """(callee, span) for every react-query cache call and query hook in one file."""
    rx = re.compile(r"(?<![\w$])(%s)\s*(?=<|\()" % "|".join(map(re.escape, sorted(CALLABLES, key=len, reverse=True))))
    out = []
    for m in rx.finditer(text):
        i = m.end()
        if text[i] == "<":
            i = balanced_end(text, i, "<", ">")
            while i < len(text) and text[i].isspace():
                i += 1
            if i >= len(text) or text[i] != "(":
                continue
        out.append((m.group(1), i, balanced_end(text, i, "(", ")")))
    return out


def segments(arr: str) -> tuple[str, ...]:
    """The key's shape: each quoted segment verbatim, each computed segment as ``*``.

    ``*`` is what react-query compares by value at runtime, so a static walk may only ever treat two
    keys as agreeing when their *literal* segments agree and the computed ones line up positionally.
    """
    inner = arr[1:-1]
    segs: list[str] = []
    i = 0
    while True:
        while i < len(inner) and inner[i] in " \t\n":
            i += 1
        if i >= len(inner):
            break
        if inner[i] == '"':
            j = inner.index('"', i + 1)
            segs.append(inner[i + 1 : j])
            i = j + 1
        else:
            k = balanced_end(inner, i, "[", "]") - 1 if inner[i] == "[" else i
            ds = db = 0
            while k < len(inner):
                ch = inner[k]
                if ch in "[{":
                    ds += ch == "["
                    db += ch == "{"
                elif ch in "]}":
                    ds -= ch == "]"
                    db -= ch == "}"
                elif ch == "," and ds == 0 and db == 0:
                    break
                k += 1
            segs.append("*")
            i = k
        if i < len(inner) and inner[i] == ",":
            i += 1
            continue
        break
    return tuple(segs)


def literal_text(arr: str) -> str:
    """The array's own source text, whitespace collapsed, for comparing prose against code."""
    return re.sub(r"\s+", " ", arr)


def enclosing_fn(text: str, pos: int) -> str:
    """The nearest preceding function declaration, which owns the key at ``pos``."""
    decls = [m.group(1) for m in re.finditer(r"^(?:export )?(?:async )?function (\w+)", text, re.M) if m.start() < pos]
    return decls[-1] if decls else "<module>"


class Site:
    def __init__(self, rel: str, text: str, start: int, arr: str, callee: str):
        self.rel = rel
        self.line = text[:start].count("\n") + 1
        self.arr = arr
        self.segs = segments(arr)
        self.callee = callee
        self.fn = enclosing_fn(text, start)

    @property
    def where(self) -> str:
        return "%s:%d [%s]" % (self.rel.split("/")[-1], self.line, self.fn)

    def __repr__(self) -> str:
        return "%s %s" % (self.where, self.segs)


def walk(rel: str, text: str) -> tuple[list[Site], list[Site], list[Site], list[Site]]:
    """Every cache call and query hook in one file, with the key array it passes.

    The key is the ``queryKey:`` property when the call takes an options object, and the first
    positional array when it does not -- ``setQueryData(["me"], user)`` is the same kind of promise
    as ``invalidateQueries({queryKey: ["me"]})`` and must not be invisible to the walk. A call that
    passes a key the walk cannot read is recorded rather than skipped, so the fourth bucket is the
    census of what this gate cannot see.
    """
    regions = call_regions(text)
    decls, promises, others, opaque = [], [], [], []
    for index, (name, open_i, end) in enumerate(regions):
        for other, (_, o2, e2) in enumerate(regions):
            if other != index and o2 < e2 and o2 > open_i and e2 < end:
                raise AssertionError("%s nests a cache call inside %s()" % (rel, name))
        window = text[open_i + 1 : end - 1]
        q = re.search(r"(?<!\w)queryKey:\s*(\[)", window)
        if q:
            a = open_i + 1 + q.start(1)
        else:
            b = window.find("[")
            if b < 0:
                assert name != PROMISE, "%s: an invalidate with no queryKey property" % rel
                opaque.append(Site(rel, text, open_i + 1, "[?]", name))
                continue
            a = open_i + 1 + b
        arr_end = balanced_end(text, a, "[", "]")
        assert arr_end <= end, "%s: a queryKey array at %d runs past its %s() call" % (rel, a, name)
        site = Site(rel, text, a, text[a:arr_end], name)
        if name == PROMISE:
            promises.append(site)
        elif name in QUERY_HOOKS:
            decls.append(site)
        else:
            others.append(site)
    return decls, promises, others, opaque


def _bucket(which: int) -> list[Site]:
    out: list[list[Site]] = [[], [], [], []]
    for rel in sorted(sources()):
        for i, part in enumerate(walk(rel, sources()[rel])):
            out[i].extend(part)
    decls, promises, others, opaque = out
    assert len(decls) >= 25 and len(promises) >= 40, "the key walk read %d declarations" % len(decls)
    assert decls or promises, "the key walk read nothing"
    return out[which]


@lru_cache(maxsize=1)
def declarations() -> list[Site]:
    return _bucket(0)


@lru_cache(maxsize=1)
def promises() -> list[Site]:
    return _bucket(1)


@lru_cache(maxsize=1)
def cache_reads_writes() -> list[Site]:
    return _bucket(2)


@lru_cache(maxsize=1)
def opaque_key_sites() -> list[Site]:
    """Cache calls whose key is not a literal array: what the walk cannot read."""
    return _bucket(3)


@lru_cache(maxsize=1)
def mentions(hook: str) -> list[str]:
    """Files that name a function outside its own declaration: who mounts it."""
    rx = re.compile(r"(?<![\w$.])%s(?![\w$])" % re.escape(hook))
    out = []
    for rel, text in sources().items():
        used = len(rx.findall(text)) - len(
            re.findall(r"^(?:export )?(?:async )?function %s\(" % re.escape(hook), text, re.M)
        )
        if used > 0:
            out.append("%s x%d" % (rel.split("/")[-1], used))
    return out


def mounted(site: Site) -> bool:
    """Is this declared key fetched by a query a screen runs?"""
    if site.rel not in HOOK_FILES:
        # Declared inside a page or component file: the file that renders it mounts it.
        return True
    assert site.fn.startswith("use"), "%s declares a query key but is not a hook" % site.where
    return bool(mentions(site.fn))


def matches(site: Site) -> list[Site]:
    return [d for d in declarations() if d.segs[: len(site.segs)] == site.segs]


def dead_promises() -> list[tuple[Site, Site]]:
    """Promises whose every matching declaration is unmounted, paired with each such declaration."""
    out = []
    for p in promises():
        hit = matches(p)
        if hit and not any(mounted(d) for d in hit):
            out.extend((p, d) for d in hit)
    return out


def unmounted_declarations() -> list[Site]:
    return [d for d in declarations() if not mounted(d)]


# --- case 1: the invariant that holds, and that a rename would break -------------------------


def test_every_invalidation_promise_names_a_key_some_query_declares():
    decls, sites = declarations(), promises()
    assert len(sites) >= 40, "only %d invalidation sites walked" % len(sites)
    assert len(decls) >= 25, "only %d query declarations walked" % len(decls)
    unmatched = [p for p in sites if not matches(p)]
    assert not unmatched, "promises naming no declared key: %s" % [repr(p) for p in unmatched]
    # The walk that produced the verdict must be the one that could have failed it.
    assert ("resumes", "*") in [d.segs for d in decls], "the walk lost the resumes list key"


# --- cases 2-4: the promises that refresh nothing a user can see ------------------------------


def test_no_promise_refreshes_only_queries_no_screen_mounts():
    pairs = dead_promises()
    # Empty since the settings page's account + career-profile editors mounted `useProfile`: the
    # ["profile"] promises left the ledger the same way the notes one did, screen first.
    assert pairs == [], "dead promises appeared: %s (lines %s)" % (
        [(repr(p), repr(d)) for p, d in pairs], sorted(p.where for p, _ in pairs))


def test_three_queries_are_declared_by_hooks_no_screen_mounts():
    dead = unmounted_declarations()
    assert len(dead) >= 3, "only %d unmounted declarations walked" % len(dead)
    by_name = {d.fn: d.segs for d in dead}
    # `useAIUsage` left this ledger when the dashboard's spend card started mounting it,
    # `useKnowledgeNotes` when the knowledge page grew its notes panel, `useProfile` when the
    # settings page grew its account + career-profile editors.
    assert by_name == {
        "useResumeScore": ("resume", "*", "score"),
        "useSourceStatus": ("knowledge", "source", "*", "status"),
        "useGlobalSearch": ("search", "*"),
    }, "unmounted queries moved: %s" % sorted(by_name)
    for d in dead:
        assert mentions(d.fn) == [], "%s is named outside its own declaration: %s" % (d.where, mentions(d.fn))


def test_every_promise_pairs_with_a_query_a_screen_mounts():
    owners = {(p.fn, p.segs): sorted({d.fn for d in matches(p)}) for p in promises()}
    # The inverse of the dead ledger above: every promise's matches include at least one mounted
    # declaration, so a regression prints which promise went dark instead of which screen starved.
    unmounted = {d.fn for d in unmounted_declarations()}
    for (fn, segs), names in sorted(owners.items()):
        mounted = [n for n in names if n not in unmounted]
        assert mounted, "the promise (%s, %s) only feeds unmounted queries: %s" % (fn, segs, names)


# --- cases 5-6: the live chain, and the comment that states why it works ----------------------


def hook_body(rel: str, hook: str) -> str:
    text = sources()[rel]
    m = re.search(r"^(?:export )?(?:async )?function %s\(" % re.escape(hook), text, re.M)
    assert m, "%s does not declare %s" % (rel, hook)
    params = text.index("(", m.start())
    brace = text.index("{", balanced_end(text, params, "(", ")"))
    return text[m.start() : balanced_end(text, brace, "{", "}")]


def test_the_versions_panel_is_refreshed_by_a_prefix_the_screen_keeps_shared():
    versions = [d for d in declarations() if d.fn == "useResumeVersions"]
    assert len(versions) == 1, "useResumeVersions declares %d keys" % len(versions)
    declared = versions[0].segs
    assert declared == ("resume", "*", "versions"), repr(declared)
    parsers = [p for p in promises() if p.fn in ("useParseResume", "useSetCurrentResume")]
    assert parsers, "neither resume mutation invalidates anything"
    for fn in ("useParseResume", "useSetCurrentResume"):
        sites = [p for p in promises() if p.fn == fn]
        shared = [
            p
            for p in sites
            if declared[: len(p.segs)] == p.segs and len(declared) > len(p.segs)
        ]
        assert shared, "%s never invalidates a strict prefix of the versions key; it invalidates %s" % (
            fn, [s.segs for s in sites]
        )
    # ... and the three of them are only the same value because one screen passes one parameter.
    # Contained, not matched: a pattern's ``??`` is a lazy quantifier, not the two shipped characters.
    page = sources()[DETAIL]
    assert "const id = params?.id ?? null;" in page, "the detail screen no longer binds id once"
    for hook, arg in (
        ("useResume", "id"),
        ("useResumeVersions", "id"),
        ("useParseResume", 'id ?? ""'),
        ("useSetCurrentResume", 'id ?? ""'),
    ):
        calls = re.findall(r"const \w+ = %s\(([^)]*)\);" % re.escape(hook), page)
        assert calls == [arg], "%s is called on the detail screen as %s, not %s(%s)" % (
            hook, calls, hook, arg)


def test_the_comment_that_explains_that_refresh_quotes_keys_the_code_ships():
    # The prose is read from the shipped file, not from the comment-blanked walk: this case is about
    # a sentence, and the sentence is the thing being checked.
    text = read(RESOURCES)
    decl = re.search(r"^export function useResumeVersions\(", text, re.M)
    assert decl, "useResumeVersions is no longer an exported declaration"
    close = text.rindex("*/", 0, decl.start())
    doc = text[text.rindex("/*", 0, close) : close]
    quoted = [literal_text(m.group(0)) for m in re.finditer(r'\["[^\]]*\]', doc)]
    assert sorted(quoted) == sorted(['["resume", id]', '["resume", resumeId]']), (
        "the comment quotes %s, and each quoted key has to be a key the code ships" % quoted
    )
    quoted_two = '["resume", resumeId]'
    sites_for_quote = [
        p
        for p in promises()
        if p.fn in ("useParseResume", "useSetCurrentResume") and literal_text(p.arr) == quoted_two
    ]
    assert sorted({p.fn for p in sites_for_quote}) == ["useParseResume", "useSetCurrentResume"], (
        "the comment quotes %s, which stands in for %s" % (
            quoted_two, sorted({p.fn for p in sites_for_quote}) or "no shipped promise")
    )
    for p in sites_for_quote:
        assert p.segs == ("resume", "*"), "%s is not keyed on the resume id alone" % p.where
    remaining = [q for q in quoted if q != quoted_two]
    assert len(remaining) == 1, "the comment quotes %s" % quoted
    versions = [d for d in declarations() if d.fn == "useResumeVersions"]
    assert len(versions) == 1, "useResumeVersions declares %d keys" % len(versions)
    assert versions[0].segs[: 2] == segments(remaining[0]), (
        "the comment's other key, %s, is no longer the prefix of the versions query %s"
        % (remaining[0], versions[0].segs)
    )


# --- case 7: one handler, and both of its keys are live ---------------------------------------


def test_the_profile_handler_writes_and_invalidates_live_keys_in_the_same_callback():
    live = [s for s in cache_reads_writes() if s.fn == "useUpdateProfile" and s.callee == "setQueryData"]
    assert [s.segs for s in live] == [("me",)], "the optimistic write is %s" % [repr(s) for s in live]
    assert any(mounted(d) for d in matches(live[0])), (
        "the optimistic write no longer lands on a mounted query: %s" % repr(live[0])
    )
    sites = [p for p in promises() if p.fn == "useUpdateProfile"]
    keys = [p.segs for p in sites]
    assert keys == [("me",), ("profile",)], "onSuccess now invalidates %s" % (keys,)
    # Both halves are live since the settings page mounted its editors: the optimistic write lands
    # on ["me"] and the invalidation hits ["profile"] through `useProfile`. The live/dead split this
    # file used to pin inside one handler is gone; the case stays to notice it coming back.
    live_keys = [p.segs for p in sites if any(mounted(d) for d in matches(p))]
    dead_keys = [p.segs for p in sites if not any(mounted(d) for d in matches(p))]
    assert live_keys == [("me",), ("profile",)], "which half of the handler is live moved: %s" % (live_keys,)
    assert dead_keys == [], (
        "a dead half appeared inside the handler; the handler is %s" % [repr(p) for p in sites]
    )


# --- case 8: an unmounted query can be a duplicate rather than a gap --------------------------


def test_the_score_the_screen_shows_comes_from_use_resume_while_use_resume_score_asks_again():
    score_body = hook_body(RESOURCES, "useResumeScore")
    resume_body = hook_body(RESOURCES, "useResume")
    fetched = r"api\.get<unknown>\(([^)]*\)?[^)]*)\)"
    asked_score = re.search(fetched, score_body)
    asked_resume = re.search(fetched, resume_body)
    assert asked_score and asked_resume, "neither hook's request is readable"
    assert asked_score.group(1) == asked_resume.group(1) == "endpoints.resume(id!)", (
        "the duplicate no longer asks the same route: %s vs %s"
        % (asked_score.group(1), asked_resume.group(1))
    )
    assert "normalizeResumeScore" in score_body and "normalizeResumeScore" in resume_body
    page = sources()[DETAIL]
    assert "const resume = useResume(id);" in page, "the screen no longer reads useResume"
    assert "const r = resume.data;" in page, "the screen no longer unwraps it as r"
    assert "score={r.score ?? null}" in page, "the panel no longer renders r.score"
    assert "useResumeScore" not in page, "the screen now mounts the duplicate as well"


# --- case 8b: the same duplicate shape, for the palette's search -------------------------------


def test_the_search_results_the_palette_shows_come_from_its_own_query_while_use_global_search_asks_again():
    search_body = hook_body(RESOURCES, "useGlobalSearch")
    asked = re.search(r"api\.get<unknown>\(([^)]*\)?[^)]*)\)", search_body)
    assert asked, "the duplicate's request is not readable"
    assert asked.group(1).startswith("endpoints.search"), (
        "the duplicate no longer asks the route the palette asks: %s" % asked.group(1)
    )
    palette = sources()[PALETTE]
    assert "endpoints.search" in palette, "the palette stopped naming the route its results come from"
    assert "useGlobalSearch" not in palette, "the screen now mounts the duplicate as well"
    # The two stay disjoint in the cache as well: the palette's query is its own, keyed
    # ["command-search", q], so nothing that ever refreshes ["search", ...] refetches the rows
    # on screen -- the duplicate serves nobody through invalidation either.
    keys = {d.segs for d in declarations() if d.rel == PALETTE}
    assert ("command-search", "*") in keys, "the palette's own key moved: %s" % (sorted(keys),)
    assert not any(k[:1] == ("search",) for k in keys), (
        "the palette declares a key in the duplicate's space: %s" % (sorted(keys),)
    )


# --- case 8c: the remaining unmounted query is a window onto rows the list already carries -----


def test_the_source_status_the_list_polls_covers_what_use_source_status_asks_again():
    status_body = hook_body(RESOURCES, "useSourceStatus")
    asked = re.search(r"api\.get<unknown>\(([^)]*\)?[^)]*)\)", status_body)
    assert asked, "the window's request is not readable"
    assert asked.group(1) == "endpoints.knowledgeSourceStatus(id!)", (
        "the single-source window no longer asks the status route: %s" % asked.group(1)
    )
    # The controller still answers it, so the window is onto a live route, not a ghost.
    controller = read(KNOWLEDGE_CONTROLLER)
    assert '@GetMapping("/sources/{id}/status")' in controller, "the status route is gone"
    # Every field the window returns, the list's mapper already carries per row, and the
    # knowledge page polls that list while anything ingests -- which is how an upload visibly
    # moves today, with no screen needing the single-source query.
    list_body = hook_body(RESOURCES, "useKnowledgeSources")
    assert "refetchInterval" in list_body and '"ingesting"' in list_body, \
        "the list stopped polling while a row ingests"
    mapper_body = hook_body(RESOURCES, "mapSource")
    for field in ("status", "error", "chunkCount", "taskId"):
        assert field in mapper_body, "the list row lost %s, so the window is no longer redundant" % field
    page = sources()[KNOWLEDGE_PAGE]
    assert "useKnowledgeSources(" in page, "the knowledge screen stopped mounting the list"
    assert "useSourceStatus" not in page, "the screen now mounts the window as well"


# --- cases 9-10: what the profile surface says now that a screen says it ----------------------


def test_the_profile_surface_is_real_on_the_server_and_mounted_by_a_screen():
    controller = read(CONTROLLER)
    assert '@RequestMapping("/api/v1/users")' in controller
    for verb in ("GetMapping", "PatchMapping"):
        assert "@%s(\"/me/profile\")" % verb in controller, "%s /users/me/profile is gone" % verb
    assert 'profile: "/users/me/profile",' in read(ENDPOINTS), "the client stopped naming the route"
    # The surface has a screen now: each hook is named outside its own declaration, so a rename
    # breaks the settings page instead of silently orphaning a real route.
    for hook in ("useProfile", "useUpdateProfile", "useUpdateProfileDetails"):
        assert mentions(hook) != [], "%s is named nowhere outside its own declaration" % hook


def test_the_profile_toasts_are_copy_no_user_can_hear():
    sentences = re.findall(r'toast\.(?:success|error)\("([^"]+)"\)', hook_body(ACTIONS, "useUpdateProfile"))
    sentences += re.findall(
        r'toast\.(?:success|error)\("([^"]+)"\)', hook_body(ACTIONS, "useUpdateProfileDetails")
    )
    assert "Profile saved." in sentences and "Career profile saved." in sentences, sentences
    for line in sentences:
        heard = [rel for rel, text in sources().items() if line in text]
        assert heard == [ACTIONS], "%r is rendered in %s, so it is no longer unreachable copy" % (line, heard)
    assert "Profile saved" not in sources()[SETTINGS], "the settings screen now says it"


# --- case 11: the one key the walk cannot read, and where its keys come from ------------------


def test_the_walk_has_exactly_one_key_blind_spot_and_it_replays_a_mounted_snapshot():
    opaque = opaque_key_sites()
    derived = sorted((s.rel.split("/")[-1], s.callee, s.fn) for s in opaque)
    assert derived == [("actions.ts", "setQueryData", "useUpdateApplication")], (
        "cache calls with a key the walk cannot read moved: %s (lines %s)"
        % (derived, [s.where for s in opaque])
    )
    site = opaque[0]
    body = hook_body(ACTIONS, site.fn)
    # The blind spot is the rollback: it writes back the keys of the snapshot, so the only way to
    # know what it touches is to read what the snapshot was taken over.
    assert "ctx?.previous?.forEach(([key, data]) => qc.setQueryData(key, data));" in body, (
        "%s is no longer that rollback: %s" % (site.where, body)
    )
    reads = [s for s in cache_reads_writes() if s.fn == site.fn and s.callee == "getQueriesData"]
    assert [s.segs for s in reads] == [("applications",)], (
        "the rollback replays %s snapshots, taken over %s"
        % (len(opaque), [repr(r) for r in reads])
    )
    assert "return { previous };" in body, "the snapshot read no longer reaches the rollback"
    assert any(mounted(d) for d in matches(reads[0])), (
        "the snapshot is taken over %s, which prefixes no mounted query, so the rollback restores "
        "cache entries no screen shows" % repr(reads[0])
    )

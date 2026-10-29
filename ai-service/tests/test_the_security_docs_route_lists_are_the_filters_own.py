"""SECURITY.md's two route lists are the filter's own, and both had gone stale.

The document states two security-critical populations as prose: which routes are public
(unauthenticated) and which routes the rate limiter treats as AI-costing. Both are
decided in Java, in two places a reader of the doc would have to go and find --
`SecurityConfig`'s `permitAll` chain and `RateLimitFilter.isAiCost` -- and both had
drifted.

The public list omitted `/api-docs/**` and `/swagger-ui.html`, which the filter admits
alongside the `/v3/api-docs/**` and `/swagger-ui/**` spellings the doc named. That is
the harmless half.

The AI-cost list was the dangerous half. `isAiCost` gained three routes that spend
provider money without living under an "AI-looking" path -- `/jobs/import` (importing a
JD runs the analyst) and `/knowledge/documents` and `/resumes/upload` (both embed every
chunk of a document into pgvector) -- and the doc never followed. A reader auditing
rate-limit coverage from SECURITY.md would have concluded those three were unthrottled,
which is the exact hole the list exists to close.

So both lists are read out of the Java that decides them and reconciled with the doc in
both directions: a route the filter admits that the doc omits, and a route the doc claims
that no filter mentions, both fail. `isAiCost`'s regexes are folded to path templates
(`^/api/v1/resumes/[^/]+/parse/?$` reads as `/resumes/{id}/parse`) so the comparison is
about coverage, not spelling, and the `/api/v1` prefix is dropped from both sides because
the doc writes the short form.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
DOC = ROOT / "docs" / "SECURITY.md"
SECURITY_CONFIG = (
    ROOT
    / "backend"
    / "src"
    / "main"
    / "java"
    / "com"
    / "careeros"
    / "config"
    / "SecurityConfig.java"
)
RATE_LIMIT = (
    ROOT
    / "backend"
    / "src"
    / "main"
    / "java"
    / "com"
    / "careeros"
    / "ratelimit"
    / "RateLimitFilter.java"
)

PREFIX = "/api/v1"


def read(path: Path) -> str:
    """Shipped text with LF endings; `git archive` hands out CRLF on this host."""
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def split_args(text: str, open_at: int) -> list[str]:
    """Top-level comma-separated arguments of the call whose `(` sits at `open_at`."""
    depth, out, buf = 0, [], ""
    for char in text[open_at:]:
        if char in "([":
            depth += 1
            if depth > 1:
                buf += char
            continue
        if char in ")]":
            depth -= 1
            if depth == 0:
                out.append(buf)
                return out
            buf += char
            continue
        if char == "," and depth == 1:
            out.append(buf)
            buf = ""
        else:
            buf += char
    return out


def public_routes() -> set[str]:
    """Every route `SecurityConfig` admits without authentication, as the doc spells them."""
    text = read(SECURITY_CONFIG)
    out = set()
    for match in re.finditer(r"\.requestMatchers\(", text):
        args = [a.strip() for a in split_args(text, match.end() - 1)]
        method = next((a for a in args if a.startswith("HttpMethod.")), None)
        paths = [a for a in args if a.startswith('"')]
        for path in paths:
            literal = path.strip('"')
            out.add(f"{method.split('.')[-1]} {literal}" if method else literal)
    return out


def ai_cost_routes() -> set[str]:
    """Every path `isAiCost` throttles, as the doc spells them (no `/api/v1` prefix)."""
    body = read(RATE_LIMIT)
    start = body.index("static boolean isAiCost(")
    stop = body.index("private String userOrIp(")
    window = body[start:stop]
    out = {path[len(PREFIX) :] for path in re.findall(r'"(/api/v1[^"]*)"', window)}
    for pattern in re.findall(r'"(\^/api/v1[^"]*)"', window):
        template = pattern.lstrip("^")[len(PREFIX) :]
        template = re.sub(r"\[\^/\]\+", "{id}", template)
        out.add(re.sub(r"/\?\$?$", "", template))
    return out


def doc_bullet(anchor: str) -> str:
    """The SECURITY.md bullet that starts with `anchor`, continuations folded in.

    A continuation is a line indented deeper than the bullet and not itself a
    bullet: the rate-limit list nests sub-bullets (`/api/v1/auth/**` 10/min,
    **Fails open**) whose contents belong to other claims, and folding those in
    would make the AI-cost list claim routes the filter never matches.
    """
    lines = read(DOC).split("\n")
    for index, line in enumerate(lines):
        if line.strip().startswith(anchor):
            indent = len(line) - len(line.lstrip())
            out = [line]
            for follow in lines[index + 1 :]:
                if not follow.strip():
                    break
                follow_indent = len(follow) - len(follow.lstrip())
                if follow_indent <= indent or follow.lstrip().startswith("- "):
                    break
                out.append(follow)
            return " ".join(part.strip() for part in out)
    raise AssertionError(f"SECURITY.md no longer has a bullet starting {anchor!r}")


def documented_routes(bullet: str) -> set[str]:
    """The backticked route spellings in a bullet, `/api/v1` prefix dropped."""
    out = set()
    for token in re.findall(r"`([^`]+)`", bullet):
        if not token.startswith("/") and not token.startswith("OPTIONS /"):
            continue
        out.add(token[len(PREFIX) :] if token.startswith(PREFIX) else token)
    return out


def admitted_covers(token: str, admitted: set[str]) -> bool:
    """Is this doc-named route one the filter actually admits?

    A route is covered by an exact matcher, or by a `/**` matcher whose prefix it sits under:
    `/api-docs` and `/api-docs/ui` are admitted by `/api-docs/**`, and the doc names them
    because that is the path `application.yml` serves.
    """
    if token in admitted:
        return True
    return any(
        route.endswith("/**")
        and (token == route[:-3] or token.startswith(route[:-3] + "/"))
        for route in admitted
    )


def test_a_wildcard_matcher_covers_the_paths_under_it_and_nothing_else():
    """Pins the wildcard arithmetic, which is one character wide and easy to get wrong.

    `/**` is three characters. Stripping two of them leaves `/api-docs/`, under which
    `/api-docs` and `/api-docs/ui` do not sit, so the doc's own spellings would read as
    unadmitted -- exactly the failure the wildcard check exists to prevent.
    """
    admitted = {"/api-docs/**", "/auth/**", "/swagger-ui.html", "/health"}
    assert admitted_covers("/api-docs", admitted)
    assert admitted_covers("/api-docs/ui", admitted)
    assert admitted_covers("/api-docs/deeply/nested", admitted)
    assert admitted_covers("/api-docs/**", admitted)
    assert not admitted_covers("/api-docsious", admitted)
    assert not admitted_covers("/healthz", admitted)


def test_every_route_the_security_config_admits_is_named_in_the_doc():
    bullet = doc_bullet("- Public (unauthenticated) routes:")
    claimed = documented_routes(bullet)
    admitted = {
        path[len(PREFIX) :] if path.startswith(PREFIX) else path
        for path in public_routes()
    }
    undocumented = sorted(admitted - claimed)
    unadmitted = sorted(t for t in claimed if not admitted_covers(t, admitted))
    assert undocumented == [] and unadmitted == [], (
        f"SecurityConfig admits {sorted(admitted)} and SECURITY.md names {sorted(claimed)}; "
        f"admitted but undocumented: {undocumented}, claimed but not admitted: {unadmitted}"
    )


def test_every_route_the_rate_limiter_costs_is_named_in_the_doc():
    bullet = doc_bullet("- AI-costing paths")
    claimed = documented_routes(bullet)
    costed = ai_cost_routes()
    missing = sorted(costed - claimed)
    assert missing == [], (
        f"RateLimitFilter.isAiCost throttles {missing} and SECURITY.md never names them, so a "
        f"reader auditing coverage from the doc concludes they are unthrottled -- which is the "
        f"hole the explicit list exists to close"
    )
    assert sorted(claimed - costed) == [], (
        f"SECURITY.md claims {sorted(claimed - costed)} are throttled but isAiCost does not "
        f"match them"
    )


def test_the_two_lists_are_populations_rather_than_a_short_list():
    """Positive control: enough routes on each side that a match cannot be an accident."""
    assert len(public_routes()) >= 9, (
        f"only {len(public_routes())} public routes parsed"
    )
    assert len(ai_cost_routes()) >= 9, (
        f"only {len(ai_cost_routes())} AI-cost routes parsed"
    )
    assert len(documented_routes(doc_bullet("- Public (unauthenticated) routes:"))) >= 9
    assert len(documented_routes(doc_bullet("- AI-costing paths"))) >= 9

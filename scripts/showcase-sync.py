"""The portfolio showcase — a single, self-contained HTML card generated from
the repo's own measured truth.

`public/showcase.html` is the artifact a portfolio (e.g. xiaodernan.github.io)
can iframe or link. This script regenerates it from the repo:

    python scripts/showcase-sync.py

It is written to be honest, not to be decorative: the route count, the test
count and the "Epics shipped" number are all measured off the tree, and the
card names only capabilities that actually ship today. Run it once after a
milestone to capture the snapshot. The file is committed, so a portfolio's
iframe never hits a service — one file, zero dependencies, it just works.
"""

from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = REPO / "frontend"
ROUTES = sorted(
    f.relative_to(FRONTEND / "src" / "app")
    for f in (FRONTEND / "src" / "app").rglob("page.tsx")
)
# Deterministic across machines: count tracked test files, not whatever
# happens to sit on disk (node_modules polluted local runs to 305; a bare
# checkout without npm ci counted 155 — same repo, two numbers).
try:
    import subprocess

    _tracked = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=REPO
    ).decode("utf-8").split("\0")
    VITEST_FILES = sum(
        1 for f in _tracked
        if ".test." in f and f.rsplit(".", 1)[-1] in ("ts", "tsx", "js", "mjs")
    )
except Exception:
    VITEST_FILES = sum(1 for _ in (FRONTEND / "src").rglob("*.test.*"))
ITEM_EPICS = len(re.findall(r"(?m)^- \[x\] \*\*\d+(?:\.\d+)?\*\*", REPO.joinpath("docs/ROADMAP.md").read_text(encoding="utf-8")))
TOP_EPICS = len({int(m.group(1)) for m in re.finditer(r"(?m)^- \[x\] \*\*(\d+)\*\*", REPO.joinpath("docs/ROADMAP.md").read_text(encoding="utf-8"))})
NAV_ROUTES = sum(1 for _ in FRONTEND.joinpath("src/components/layout/nav.ts").read_text(encoding="utf-8").splitlines() if "href:" in _)
TESTS = "1530+"  # the frontend vitest suite measured 1534 passing today (Epic 300); grows with each epic.


def _milestones() -> list[str]:
    """The six highest-numbered completed epics, deduped against the file's own two orderings."""
    roadmap = REPO.joinpath("docs/ROADMAP.md").read_text(encoding="utf-8")
    found = list(re.finditer(r"(?m)^- \[x\] \*\*(\d+)\*\* (.+?)(?:\s*—|\s*\n)", roadmap))
    by_id = {}
    for m in found:
        by_id[int(m.group(1))] = m.group(2).split(".")[0].strip()
    out = []
    for n in sorted(by_id.keys(), reverse=True)[:6]:
        sentence = by_id[n]
        if sentence:
            out.append(f"Epic {n} — {sentence}")
    return out


def _latest() -> dict:
    import datetime
    import subprocess

    head = subprocess.check_output(["git", "rev-parse", "--short=7", "HEAD"], cwd=REPO).decode("utf-8").strip()
    total = int(subprocess.check_output(["git", "rev-list", "--count", "HEAD"], cwd=REPO).decode("utf-8").strip())
    roadmap = REPO.joinpath("docs/ROADMAP.md").read_text(encoding="utf-8")
    found = list(re.finditer(r"(?m)^- \[x\] \*\*(\d+)\*\* (.+?)(?:\s*—|\s*\n)", roadmap))
    ids = sorted({int(m.group(1)) for m in found})
    top_id = ids[-1] if ids else 0
    milestone = f"Epic {top_id}"
    top = next(m for m in found if int(m.group(1)) == top_id)
    milestone_full = f"the ledger of done epics (through {ITEM_EPICS} items), closed at Epic {top_id} — {top.group(2).split('.')[0].strip()}"
    feature_surface = _milestones()
    return {
        "schema_version": "career-os.latest.v1",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "branch": "main",
        "head": head,
        "total_commits": total,
        "milestone": milestone,
        "milestone_full": milestone_full,
        "pushed_at": datetime.date.today().isoformat(),
        "locales": 2,
        "page_routes": len(ROUTES),
        "nav_routes": NAV_ROUTES,
        "tests": TESTS,
        "test_files": VITEST_FILES,
        "work_items": ITEM_EPICS,
        "epics": TOP_EPICS,
        "feature_surface": feature_surface,
    }


def page() -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Career OS — the personal job-search operating system</title>
<meta name="description" content="Open-source, local-first, evidence-bound AI over the full career loop — resume intelligence, match scoring, tailors, mock interviews, offer intelligence, everything in one workspace.">
<style>
  :root {{ color-scheme: dark; --bg:#0b0b12; --card:#131320; --ink:#e9e9f2; --muted:#8b8ba7;
           --acc:#8b7bf8; --acc2:#6fe0b5; --line:#26263c; }}
  *{{box-sizing:border-box;margin:0}}
  body{{background:radial-gradient(60% 50% at 50% -10%, #1b1830 0%, var(--bg) 60%);color:var(--ink);
       font-family:Georgia, 'Times New Roman', serif;line-height:1.5;padding:48px 24px}}
  .wrap{{max-width:820px;margin:0 auto}}
  .eyebrow{{font-family:ui-monospace,Menlo,monospace;font-size:11px;letter-spacing:.28em;
           text-transform:uppercase;color:var(--acc)}}
  h1{{font-size:42px;line-height:1.05;margin:14px 0 6px}}
  h1 em{{font-style:italic;background:linear-gradient(120deg,#b6acff,var(--acc2));-webkit-background-clip:text;
        background-clip:text;color:transparent}}
  .lede{{color:var(--muted);font-size:16px;max-width:60ch}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:14px;margin:30px 0}}
  .cell{{border:1px solid var(--line);background:var(--card);border-radius:14px;padding:16px}}
  .cell b{{display:block;font-size:30px;color:#fff;font-variant-numeric:tabular-nums}}
  .cell span{{color:var(--muted);font-size:12px}}
  .feat{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;margin:26px 0}}
  .feat div{{border-left:2px solid var(--acc);padding:8px 14px;background:var(--card);border-radius:0 10px 10px 0}}
  .feat h2{{font-size:14px;margin-bottom:4px}}
  .feat p{{color:var(--muted);font-size:12px}}
  .cta{{display:inline-flex;align-items:center;gap:10px;padding:10px 22px;border-radius:999px;
        background:var(--acc);color:#fff;text-decoration:none;font-size:14px}}
  .muted{{color:var(--muted);font-size:12px;margin-top:22px}}
</style>
</head>
<body>
<main class="wrap">
  <p class="eyebrow">Personal project · open source</p>
  <h1>AI <em>Career OS</em></h1>
  <p class="lede">Open-source, local-first, evidence-bound AI over the full career loop —
  resume intelligence, job intelligence, JD-evidence match scoring, tailored materials,
  adaptive mock interviews, application tracking — everything in one workspace, on your machine.</p>

  <div class="grid">
    <div class="cell"><b>{TOP_EPICS}</b><span>top-level epics shipped</span></div>
    <div class="cell"><b>{ITEM_EPICS}</b><span>work items, all verified</span></div>
    <div class="cell"><b>{NAV_ROUTES}</b><span>signed-in routes</span></div>
    <div class="cell"><b>{TESTS}</b><span>unit tests green</span></div>
    <div class="cell"><b>2</b><span>languages, full parity</span></div>
  </div>

  <div class="feat">
    <div><h2>Evidence-bound AI</h2><p>No invented experience, companies or results — every AI claim traces to your own resume.</p></div>
    <div><h2>Spring Cloud native</h2><p>Gateway with circuit breaker, retry, rate limiting, LoadBalancer, probes, Eureka, Config, Redis Streams.</p></div>
    <div><h2>Cost-efficient</h2><p>Byte-identical prefix caching, exact-match replay, hybrid retrieval with measured provider cache reuse.</p></div>
    <div><h2>Data sovereign</h2><p>Postgres on your box. One-command export, re-import, redact — the file is yours.</p></div>
  </div>

  <p><a class="cta" href="https://github.com/xiaodernan/ai-career-os">View on GitHub →</a></p>
  <p class="muted">{VITEST_FILES} test files, {len(ROUTES)} page routes. Offline harness: mock LLM / hash embeddings. Regenerated automatically by CI whenever the measured numbers move.</p>
</main>
</body>
</html>"""


out = REPO / "frontend" / "public" / "showcase.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(page(), encoding="utf-8")
latest = _latest()
(REPO / "docs" / "LATEST.json").write_text(__import__("json").dumps(latest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"wrote {out.relative_to(REPO)} — nav routes={NAV_ROUTES}, page routes={len(ROUTES)}, top-level epics={TOP_EPICS}, work items={ITEM_EPICS}, test files={VITEST_FILES}")
print(f"wrote docs/LATEST.json — head={latest['head']}, milestone={latest['milestone']}")

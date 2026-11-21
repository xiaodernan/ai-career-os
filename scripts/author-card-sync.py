"""The author card — a single, self-contained HTML card for the portfolio.

Brief X asks for two things this repo can actually deliver: "把所有项目都列入我的 github io
页面" and "极致装修和宣传我的 io 页面和 GitHub 个人主页". The io page is a separate
repository, so what this file provides is the artifact that page can embed: one file, zero
dependencies, no runtime, no fetch — an iframe that renders on any origin.

It is written to be honest about the one thing that has been got wrong before. The personal
facts below are the ones the reader of this repository was given directly and explicitly, and
the brief names them as load-bearing ("之前出现过严重幻觉，务必以下面为准，不许搞错"). So the
card carries no derived claim, no inferred employer, no guessed score: every line is a fact
that was stated. Where a fact has a number it is the number given. The project name is a single
constant and it is spelled the one way it is spelled; a previous pass wrote it the other way,
which is the failure this file exists to stop repeating — and the gate beside it refuses the
wrong spelling anywhere in this source, comment included, so it cannot come back by accident.

The project figures are measured off the tree by the same walk showcase-sync.py uses, so the
card cannot disagree with the repository it is generated from.

    python scripts/author-card-sync.py
"""

from __future__ import annotations

import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[1]
FRONTEND = REPO / "frontend"

# The facts, exactly as given. Not derived, not inferred, not "approximately".
NAME = "赵欣曈"
NAME_EN = "Zhao Xintong"
UNDERGRAD = "南方科技大学"
UNDERGRAD_EN = "Southern University of Science and Technology"
GRADUATE = "香港中文大学"
GRADUATE_EN = "The Chinese University of Hong Kong"
MAJOR = "计算机科学与技术"
MAJOR_EN = "Computer Science and Technology"
INTERNSHIP = "法狗狗"
INTERNSHIP_EN = "Fagougou"
IELTS = "IELTS 6.5"
CET = "CET-6 546"
PHYSICS = "全国中学生物理竞赛 铜牌"
PHYSICS_EN = "National High School Physics Olympiad — Bronze"
PROVINCE_AWARDS = "江西省一等奖、二等奖"
PROVINCE_AWARDS_EN = "Jiangxi Province — First Prize, Second Prize"
# The project name, spelled the one way it is spelled.
PROJECT = "隐盾"
PROJECT_EN = "Yindun"
GITHUB = "https://github.com/xiaodernan"
PROJECT_REPO = "https://github.com/xiaodernan/ai-career-os"


def _count(pattern: str) -> int:
    roadmap = REPO.joinpath("docs/ROADMAP.md").read_text(encoding="utf-8")
    return len(re.findall(pattern, roadmap))


def _nav_routes() -> int:
    text = FRONTEND.joinpath("src/components/layout/nav.ts").read_text(encoding="utf-8")
    return sum(1 for _ in text.splitlines() if "href:" in _)


def _test_files() -> int:
    try:
        files = subprocess.check_output(["git", "ls-files", "-z"], cwd=REPO).decode("utf-8").split("\0")
    except Exception:
        return 0
    return sum(1 for f in files if ".test." in f and f.rsplit(".", 1)[-1] in ("ts", "tsx", "js", "mjs"))


def _head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short=7", "HEAD"], cwd=REPO).decode("utf-8").strip()
    except Exception:
        return ""


TOP_EPICS = _count(r"(?m)^- \[x\] \*\*(\d+)\*\*")
WORK_ITEMS = _count(r"(?m)^- \[x\] \*\*\d+(?:\.\d+)?\*\*")


def page() -> str:
    """The card. Dark, self-contained, one screen — the portfolio's own theme."""
    facts = [
        (f"{UNDERGRAD} · {MAJOR}", f"{UNDERGRAD_EN} · {MAJOR_EN}", "本科"),
        (f"{GRADUATE} · {MAJOR}", f"{GRADUATE_EN} · {MAJOR_EN}", "硕士"),
        (f"实习 · {INTERNSHIP}", f"Internship · {INTERNSHIP_EN}", "经历"),
        (IELTS, "IELTS", "语言"),
        (CET, "CET-6", "语言"),
        (PHYSICS, PHYSICS_EN, "竞赛"),
        (PROVINCE_AWARDS, PROVINCE_AWARDS_EN, "竞赛"),
    ]
    rows = "".join(
        f'<li><span class="k">{zh}</span><span class="v">{en}</span></li>'
        for zh, en, _kind in facts
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{NAME} · {PROJECT}</title>
<meta name="description" content="{NAME} — {MAJOR}，{UNDERGRAD}本科、{GRADUATE}硕士。开源项目「{PROJECT}」作者。">
<style>
  :root{{--bg:#0b0c0f;--card:#12141a;--line:#232733;--fg:#e8eaf0;--muted:#9aa3b2;--acc:#6366f1;--acc2:#22d3ee}}
  *{{box-sizing:border-box;margin:0}}
  body{{background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
        display:flex;align-items:center;justify-content:center;min-height:100vh;padding:28px}}
  .card{{width:100%;max-width:640px;background:var(--card);border:1px solid var(--line);border-radius:20px;padding:30px 32px;
        box-shadow:0 24px 60px -30px rgba(0,0,0,.8)}}
  .eyebrow{{font-size:11px;letter-spacing:.28em;text-transform:uppercase;color:var(--acc2);font-weight:600}}
  h1{{font-size:34px;line-height:1.15;margin:10px 0 2px;letter-spacing:-.01em}}
  .en{{color:var(--muted);font-size:14px;letter-spacing:.02em}}
  .proj{{margin:18px 0 22px;padding:12px 16px;border:1px solid var(--line);border-radius:12px;background:rgba(99,102,241,.07)}}
  .proj b{{color:var(--acc2);font-size:17px}}
  .proj span{{color:var(--muted);font-size:13px;display:block;margin-top:2px}}
  ul{{list-style:none;padding:0;display:grid;gap:9px}}
  li{{display:flex;align-items:baseline;gap:12px;padding-bottom:9px;border-bottom:1px solid var(--line)}}
  li:last-child{{border-bottom:0;padding-bottom:0}}
  .k{{color:var(--muted);font-size:11px;letter-spacing:.14em;min-width:44px;text-transform:uppercase}}
  .v{{font-size:15px}}
  .nums{{display:flex;gap:22px;margin-top:22px;padding-top:20px;border-top:1px solid var(--line)}}
  .nums div{{flex:1}}
  .nums b{{display:block;font-size:24px;font-variant-numeric:tabular-nums;color:var(--acc2)}}
  .nums span{{font-size:11px;color:var(--muted);letter-spacing:.1em}}
  .links{{display:flex;gap:10px;margin-top:22px}}
  a{{flex:1;text-align:center;text-decoration:none;font-size:13px;font-weight:600;padding:10px 14px;border-radius:10px;
     border:1px solid var(--line);color:var(--fg);transition:border-color .15s,background .15s}}
  a:hover{{border-color:var(--acc);background:rgba(99,102,241,.12)}}
  a.p{{background:var(--acc);border-color:var(--acc);color:#fff}}
  a.p:hover{{background:#4f46e5}}
  .foot{{margin-top:18px;font-size:11px;color:var(--muted);font-family:ui-monospace,SFMono-Regular,Menlo,monospace}}
</style>
</head>
<body>
<main class="card">
  <p class="eyebrow">Author · 作者</p>
  <h1>{NAME}</h1>
  <p class="en">{NAME_EN} · {MAJOR_EN}</p>
  <div class="proj">
    <b>「{PROJECT}」</b>
    <span>{PROJECT_EN} — an open-source, local-first, evidence-bound AI job-search operating system. 开源、本地优先、证据约束的个人求职操作系统。</span>
  </div>
  <ul>{rows}</ul>
  <div class="nums">
    <div><b>{TOP_EPICS}</b><span>EPICS</span></div>
    <div><b>{WORK_ITEMS}</b><span>WORK ITEMS</span></div>
    <div><b>{_nav_routes()}</b><span>ROUTES</span></div>
    <div><b>{_test_files()}</b><span>TEST FILES</span></div>
  </div>
  <div class="links">
    <a class="p" href="{PROJECT_REPO}">项目仓库 · {PROJECT}</a>
    <a href="{GITHUB}">GitHub 主页</a>
  </div>
  <p class="foot">measured off the tree at {_head()} — the figures move only when the work does.</p>
</main>
</body>
</html>"""


out = FRONTEND / "public" / "author.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(page(), encoding="utf-8")
print(f"wrote {out.relative_to(REPO)} — {NAME} · {PROJECT} · {TOP_EPICS} epics / {WORK_ITEMS} work items")

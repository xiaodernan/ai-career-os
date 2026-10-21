"""Build a patch that carries only this session's hunks for a shared file.

The repository is developed concurrently, and `app/api/features.py` carries
another session's in-flight work. A commit that took the whole file would
take that work with it, so this builds a patch from the committed version
plus only the hunks that belong here, and stages that.

Run: python scripts/stage_only_mine.py <path> <marker>
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = Path(__file__).resolve().parents[2]


def main() -> int:
    rel = sys.argv[1]
    # Git's paths are relative to the repository root, not to this package.
    repo_rel = f"ai-service/{rel}"
    target = ROOT / repo_rel
    base = subprocess.run(
        ["git", "show", f"HEAD:{repo_rel}"], cwd=REPO, capture_output=True, check=True,
    ).stdout.decode("utf-8")
    if not base:
        print(f"the committed text of {repo_rel} is empty", file=sys.stderr)
        return 1

    # The committed text, with this session's change applied to it.
    mine = base.replace(
        'class PipelineFunnelReq(BaseModel):\n'
        '    applications: list[ApplicationInput] = Field(min_length=1)\n',
        'class PipelineFunnelReq(BaseModel):\n'
        '    """The funnel\'s input. `applications` is optional because an account with no\n'
        '    applications is a real state, not an error: the engine then answers with an\n'
        '    empty funnel, which is the honest answer for a workspace that has not\n'
        '    started. A required list would make the first run a 422 -- the same\n'
        '    reasoning the digest\'s request already carries."""\n'
        '\n'
        '    applications: list[ApplicationInput] = Field(default_factory=list)\n',
    ).replace(
        'class ResponseRateReq(BaseModel):\n'
        '    applications: list[ApplicationInput] = Field(min_length=1)\n',
        'class ResponseRateReq(BaseModel):\n'
        '    """The response rate\'s input, optional for the same reason as the funnel\'s:\n'
        '    a workspace with no applications answers with zeroes, not with a 422."""\n'
        '\n'
        '    applications: list[ApplicationInput] = Field(default_factory=list)\n',
    )
    if mine == base:
        print("the base text does not carry the shape this patch expects", file=sys.stderr)
        return 1

    work = REPO / ".stage-tmp" / repo_rel
    base_file = work.parent / "a" / repo_rel
    mine_file = work.parent / "b" / repo_rel
    base_file.parent.mkdir(parents=True, exist_ok=True)
    mine_file.parent.mkdir(parents=True, exist_ok=True)
    base_file.write_text(base, encoding="utf-8", newline="")
    mine_file.write_text(mine, encoding="utf-8", newline="")

    patch = subprocess.run(
        ["git", "diff", "--no-index", "--binary", str(base_file), str(mine_file)],
        cwd=work.parent, capture_output=True, check=False,
    ).stdout.decode("utf-8", errors="replace")
    # `git diff --no-index` writes the paths it was given; the patch has to
    # name the repository's own path.
    patch = re.sub(r"(?m)^--- .*$", f"--- a/{repo_rel}", patch, count=1)
    patch = re.sub(r"(?m)^\+\+\+ .*$", f"+++ b/{repo_rel}", patch, count=1)
    patch = re.sub(r"(?m)^diff --git .*$", f"diff --git a/{repo_rel} b/{repo_rel}", patch, count=1)

    _debug(repo_rel, patch)
    # The patch is bytes, not text: the locale's codec would mangle the
    # em-dashes in the docstrings, and `git apply` would refuse the file.
    subprocess.run(["git", "apply", "--cached", "-"], cwd=REPO,
                   input=patch.encode("utf-8"), check=True)
    print(f"staged only this session's hunks for {repo_rel}")
    return 0


def _debug(repo_rel: str, patch: str) -> None:
    out = REPO / ".stage-tmp" / "patch.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(patch, encoding="utf-8", newline="")
    print(f"patch written to {out}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())

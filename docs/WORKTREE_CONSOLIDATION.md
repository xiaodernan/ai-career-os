# Worktree consolidation — 2026-11-09

Besides the main checkout (`D:/求职平台`) the repository had **ten registered linked
worktrees**, all at detached HEADs left by historical sessions:

```
D:/careeros-baseline-f25f6db
D:/careerosu244/wt-head
D:/careerosu245/u11/wt
D:/careerosu245/u12/post-8ff337c
D:/careerosu245/u12/post-c522546
D:/careerosu245/u12/wt
D:/careerosu245/u12/wt-head
D:/careerosu245/u13/wt
D:/careerosu245/u13/wt-head
D:/careerosu256/wt
```

This note records what was measured *before* they were retired, so "everything is
consolidated into `main`" is a claim with evidence rather than a directory deletion.

## What the measurement found

| Check | Result |
| --- | --- |
| Local branches | one: `main`, tracking `origin/main` |
| Remote branches | one: `origin/main` |
| Linked worktrees | 10, all **detached** (no branch to merge) |
| Worktree HEADs that are ancestors of `main` | **10 / 10** |
| Commits reachable from a worktree but not from `main` | **0** |
| Untracked files in a worktree that are absent from `main`'s HEAD | **0** |
| Stashes | none |

Every worktree was dirty (1–667 changed files). The bulk of that is the CRLF/LF
churn this host produces when different tools rewrite a file: five worktrees had
**no** untracked files and **no** asymmetric (add ≠ delete) diff at all. The other
five carried asymmetric diffs and four untracked test files, which were checked
one by one:

- All four untracked tests already exist in `main`'s HEAD. Two are byte-identical;
  the other two are *shorter* than the version in `main`, which has since grown —
  neither contains a line `main` lacks.
- The asymmetric diffs are **older snapshots**, not abandoned implementations.
  `ai-service/app/features/analytics.py` is 12.7K / 16.0K characters in the
  worktrees versus 17.4K in `main` (0.79–0.94 similarity, worktree-only text is
  superseded copy). `docs/ROADMAP.md` is 116K versus 352K. `main` is strictly the
  newer, larger body of work.

So there was nothing to `merge` or `cherry-pick`: no branch, no unique commit, no
unique file. The content had already been consolidated by the ordinary commit
history. What remained was ten stale registrations and their disk copies.

## The recoverable backup

Before any removal, every worktree's complete `git diff --binary`, its
`git status --porcelain` listing, and full copies of its untracked files were
written to `backups/worktree-consolidation/` (gitignored, kept locally):

- `<name>.patch` — 27,254,570 bytes in total;
- `<name>.status.txt` — the exact dirty-file population;
- `<name>__<basename>.py.txt` — the four untracked tests, **flattened**;
- `manifest.json` — path, HEAD, dirty-file count and patch size per worktree.

The untracked copies were first written preserving their `ai-service/tests/`
paths, which made the repository's offline-Python census see a second `tests`
tree under `backups/` and redden (`test_response_shape_contract.py`:
"a `tests` directory in another tree is a directory this census would start
excusing files in"). They were renamed to flat `.txt` archives in the same
backup directory. **A backup inside the repository is still part of the tree
the gates walk** — keep it out of any path shape a census recognises.

Because each HEAD is an ancestor of `main`, any patch can be replayed from the
commit it names. Nothing was discarded that cannot be reconstructed.

## Retirement

The ten registrations were removed with `git worktree remove --force` (force was
required because every worktree was dirty) and the stale administrative files
were cleared with `git worktree prune`. `git worktree list` then names only the
main checkout. No branch was rewritten, no force-push, no history edit.

## What this does **not** mean

`docs/ROADMAP.md` remains the single backlog, `docs/plans/plan_long_term.md` the
long-term plan, and `main`/`origin/main` the only line of development. A future
session that needs a scratch tree should register it deliberately and remove it
the same way; a detached snapshot is not a branch and should not be mistaken for
one.

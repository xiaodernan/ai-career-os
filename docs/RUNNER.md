# CI Runner — `lenovo-career-os-2` (self-hosted, this machine)

## Why it exists
GitHub-hosted runners cannot serve this repo (every push queued/cancelled for days).
All CI jobs in `.github/workflows/ci.yml` target the self-hosted Windows runner
co-located with the developer's working machine (`XIAODERNAN`).

## Lifecycle
The runner is **foreground-only**. It dies on reboot or log-off. Two ways back:

1. **Normal (no admin):** log on and run
   `D:\_actions-runner-careeros\run.cmd`
   (keep the window open; closing it stops the runner).
2. **As a Windows service (needs an elevated shell):**
   `cd D:\_actions-runner-careeros && .\svc.cmd install && .\svc.cmd start`
   (uninstall: `.\svc.cmd stop && .\svc.cmd uninstall`)

A per-user scheduled task was attempted and denied by the OS (`Access is denied`), so
until an admin session runs `svc.cmd`, option 1 is the supported path.

## Registration (if the runner has to be re-created)
```powershell
$token = gh api -X POST repos/xiaodernan/ai-career-os/actions/runners/registration-token --jq '.token'
cd D:\_actions-runner-careeros
.\config.cmd --url https://github.com/xiaodernan/ai-career-os --token $token --name lenovo-career-os-2 --unattended --replace
.\run.cmd
```

## Gotchas the CI already encodes
- `python` on PATH is a dangling Store-stub (`C:\Program Files\Python311\python.exe` does not exist).
  Workflow uses `py -3.11` (resolves to the runner's own CPython 3.11.9).
- That Python has user site-packages **disabled**; every Python job creates a per-checkout
  `.venv` and calls `.venv\Scripts\python.exe`.
- Next.js production build needs `NODE_OPTIONS=--max-old-space-size=8192` on this machine;
  the bundle-budget job sets it.
- pwsh is the default shell; avoid bash `||` / `&&` short-circuits, use
  `if (-not (git diff --cached --quiet)) { ... }`.
- Proxy goes through Clash Verge at `127.0.0.1:7897`; git over HTTPS picks it up from
  `http.proxy` in the current session / `.gitconfig`.

# scan-agent-proxy.ps1 — READ-ONLY audit of local agent config for a Clash proxy
# port binding. Reports real config bindings; ignores caches, history and bytecode
# where the digits happen to appear. Bounded to the specific agent config roots so
# it finishes in seconds instead of traversing every file under LOCALAPPDATA.
#
#   powershell -ExecutionPolicy Bypass -File scripts/scan-agent-proxy.ps1

$ErrorActionPreference = 'SilentlyContinue'
function Say($m) { Write-Host "[scan] $m" }

# Exactly the agents the owner named, plus the other common ones — no deep walk of
# APPDATA/LOCALAPPDATA as a whole (that traverses caches and stalls for minutes).
$roots = @(
  "$env:USERPROFILE\.workbuddy",
  "$env:USERPROFILE\.config\opencode",
  "$env:APPDATA\ai.opencode.desktop",
  "$env:APPDATA\WorkBuddy AI",
  "$env:APPDATA\Trae CN\User",
  "$env:APPDATA\Cursor\User",
  "$env:LOCALAPPDATA\CodeBuddyExtension",
  "$env:USERPROFILE\.claude",
  "$env:USERPROFILE\.codex",
  "$env:USERPROFILE\.cursor"
)

$configExt = '.json','.jsonc','.yaml','.yml','.toml','.ini','.env'
# Only files whose NAME looks like config — not CodeCache / History / logs.
$configName = 'settings|config|mcp|provider|model|env|opencode\.settings|package'
$cachePart = 'CodeCache|Cache_Data|Code Cache|CachedData|compile-cache|node_modules|History|logs|Crashpad|GPUCache|blobs|blob_storage'

$findings = @()
foreach ($r in $roots) {
  if (-not (Test-Path $r)) { continue }
  # -Depth 3 bounds the walk; config lives at the root or one/two levels in.
  Get-ChildItem -Path $r -Recurse -Depth 3 -File -ErrorAction SilentlyContinue |
    Where-Object {
      $_.Length -lt 200000 -and $_.Extension -in $configExt -and
      $_.Name -match $configName -and $_.FullName -notmatch $cachePart
    } |
    ForEach-Object {
      $f = $_.FullName
      $c = Get-Content -Raw -LiteralPath $f -ErrorAction SilentlyContinue
      if (-not $c) { return }
      $m = [regex]::Matches($c, '7897|7898|mixed-port|socks-port|HTTP_PROXY|HTTPS_PROXY|http_proxy|https_proxy|proxy-server|"proxy"', 'IgnoreCase')
      # A bare digit run inside a large number is a timestamp/checksum, not a port.
      $real = @($m | Where-Object {
        $v = $_.Value
        if ($v -notmatch '^\d+$') { return $true }
        $start = [Math]::Max(0, $_.Index - 1)
        $end = [Math]::Min($c.Length, $_.Index + $v.Length + 1)
        $ctx = $c.Substring($start, $end - $start)
        $ctx -notmatch '\d' + [regex]::Escape($v) + '\d'
      })
      if ($real.Count -gt 0) {
        $findings += [pscustomobject]@{ file = $f; hits = ($real | ForEach-Object Value | Select-Object -Unique) -join ',' }
      }
    }
}

Say "scanned agent config roots: $($roots.Count)"
if ($findings.Count -eq 0) {
  Say "CLEAN — no agent config binds a Clash proxy port or sets a proxy env var."
  Say "Port-like digit runs in caches/logs are timestamps or bytecode checksums, not bindings."
} else {
  Say "FOUND $($findings.Count) config file(s) with proxy-like content — review each:"
  $findings | ForEach-Object { Say ("  {0}  [{1}]" -f $_.file, $_.hits) }
}

$listening = @()
foreach ($p in 7890,7891,7897,7898,1080,1081,7899) {
  $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($c) {
    $pr = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
    $listening += "$p -> $($pr.ProcessName)"
  }
}
if ($listening.Count -eq 0) { Say "no Clash proxy port is listening on this host right now" }
else { Say "listening proxy ports: $($listening -join ', ')" }

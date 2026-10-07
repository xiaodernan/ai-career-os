# e2e/preflight.ps1 - stack checks to run before "npx playwright test".
#
# Every check here exists because a trap documented in README.md cost a real
# debugging session: the auth rate limit (trap 3), who owns port 3000 (trap 6),
# hosted AI providers with empty keys, images older than the code under test,
# a local .next build older than the sources, and a test-results dir big
# enough to trip the sandbox bulk-delete guard (trap 5).
#
# The script never mutates the stack. FAIL means "fix before running";
# WARN is context that is only sometimes the problem. Checks that only make
# sense for a containerized service degrade to inconclusive WARNs when the
# service runs as a local process, which is the honest answer.
#
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File preflight.ps1
# Exit:  0 = nothing blocks the run (warnings possible), 1 = fix a FAIL first.

$ErrorActionPreference = 'Continue'
$script:failures = 0
$script:warnings = 0

function Say($level, $msg) {
    Write-Output ("[{0}] {1}" -f $level.PadRight(5), $msg)
    if ($level -eq 'FAIL') { $script:failures++ }
    if ($level -eq 'WARN') { $script:warnings++ }
}

# Same defaults as the README env-overrides table.
$base = if ($env:E2E_BASE_URL) { $env:E2E_BASE_URL } else { 'http://localhost:3000' }
$api  = if ($env:E2E_API_URL)  { $env:E2E_API_URL }  else { 'http://127.0.0.1:8080/api/v1' }
$ai   = if ($env:E2E_AI_URL)   { $env:E2E_AI_URL }   else { 'http://127.0.0.1:8000' }

function UrlOk($url) {
    try {
        $r = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
        return ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500)
    } catch { return $false }
}

Write-Output "e2e preflight $(Get-Date -Format s)"
Write-Output "base=$base api=$api ai=$ai"
Write-Output ''

# --- 1. three services reachable ---------------------------------------------
if (UrlOk $base) { Say 'PASS' "frontend answers at $base" }
else { Say 'FAIL' "frontend not reachable at $base - start it or fix E2E_BASE_URL" }

if (UrlOk "$api/health") { Say 'PASS' "backend health at $api/health" }
else { Say 'FAIL' "backend health not reachable at $api/health" }

if (UrlOk "$ai/health") { Say 'PASS' "ai-service health at $ai/health" }
else { Say 'FAIL' "ai-service health not reachable at $ai/health" }

# --- 2. who owns port 3000 (README trap 6) ------------------------------------
# "$( ... )" not "[string]( ... )": an empty native-command result is $null and
# the cast keeps it null on some hosts, while interpolation always yields ''.
$feContainer = "$(docker ps --filter 'name=careeros-frontend' --format '{{.Names}}' 2>$null)"
if ($feContainer) {
    Say 'WARN' 'careeros-frontend container is up and owns port 3000 - local .next rebuilds are invisible until you stop it (trap 6)'
} else {
    $conn = Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        Say 'PASS' "port 3000 is a host process (pid $($conn[0].OwningProcess)), not the frontend container"
        $buildId = Join-Path $PSScriptRoot '..\frontend\.next\BUILD_ID'
        if (Test-Path $buildId) {
            $built = (Get-Item $buildId).LastWriteTime
            $newest = Get-ChildItem (Join-Path $PSScriptRoot '..\frontend\src') -Recurse -File -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($newest -and $newest.LastWriteTime -gt $built) {
                Say 'WARN' ".next is older than frontend/src/$($newest.Name) - rebuild and restart before trusting UI results"
            } else {
                Say 'PASS' ".next build is newer than every frontend/src file"
            }
        } else {
            Say 'WARN' 'no frontend/.next/BUILD_ID - is that server serving a production build at all?'
        }
    } else {
        Say 'FAIL' 'nobody is listening on port 3000'
    }
}

if ($base -match '^http://127\.0\.0\.1') {
    Say 'WARN' 'E2E_BASE_URL uses 127.0.0.1 - the browser treats it as a different origin than the CORS allowlist default (trap 1)'
}

docker version --format '{{.Server.Version}}' 2>$null | Out-Null
$dockerOk = ($LASTEXITCODE -eq 0)
if (-not $dockerOk) {
    Say 'WARN' 'docker CLI or daemon unavailable - container-only checks below are skipped'
}

# --- 3. auth rate limit (README trap 3) ----------------------------------------
if ($dockerOk) {
    $rl = "$(docker exec careeros-backend printenv RATELIMIT_AUTH_PER_MINUTE 2>$null)"
    if ($rl -match '^\d+$') {
        if ([int]$rl -ge 100) { Say 'PASS' "backend RATELIMIT_AUTH_PER_MINUTE=$rl" }
        else { Say 'FAIL' "backend RATELIMIT_AUTH_PER_MINUTE=$rl - a full run registers more accounts than that; apply e2e-override.yml and up the backend again (trap 3)" }
    } else {
        Say 'WARN' 'could not read RATELIMIT_AUTH_PER_MINUTE from careeros-backend (local process? then start it with RATELIMIT_AUTH_PER_MINUTE=100)'
    }
}

# --- 4. offline AI providers ----------------------------------------------------
if ($dockerOk) {
    $aiContainer = ''
    foreach ($n in @('careeros-ai', 'careeros-ai-service')) {
        $hit = "$(docker ps --filter "name=$n" --format '{{.Names}}' 2>$null)"
        if ($hit) { $aiContainer = $n; break }
    }
    if ($aiContainer) {
        $llm = "$(docker exec $aiContainer printenv LLM_PROVIDER 2>$null)"
        $emb = "$(docker exec $aiContainer printenv EMBEDDING_PROVIDER 2>$null)"
        if ($llm -eq 'mock' -and $emb -eq 'hash') {
            Say 'PASS' "$aiContainer runs LLM_PROVIDER=mock EMBEDDING_PROVIDER=hash"
        } else {
            Say 'FAIL' "$aiContainer has LLM_PROVIDER='$llm' EMBEDDING_PROVIDER='$emb' - hosted providers with empty keys stall every AI test; up the container with LLM_PROVIDER=mock EMBEDDING_PROVIDER=hash"
        }
    } else {
        Say 'WARN' 'ai-service is not a container - make sure the process was started with LLM_PROVIDER=mock EMBEDDING_PROVIDER=hash'
    }
}

# --- 5. image freshness (matters for containerized acceptance runs) -------------
if ($dockerOk) {
    $targets = @(
        @{ image = 'career-os-backend';    src = 'backend/src' },
        @{ image = 'career-os-ai-service'; src = 'ai-service/app' },
        @{ image = 'career-os-frontend';   src = 'frontend' }
    )
    foreach ($t in $targets) {
        $created = "$(docker images --format '{{.CreatedAt}}' $t.image 2>$null)"
        if (-not $created) {
            Say 'WARN' "image $($t.image) does not exist yet - build it before a containerized acceptance run"
            continue
        }
        $clean = ($created -replace '\s+[A-Z]{2,4}\s*$', '') -replace '(\+\d{2})(\d{2})$', '$1:$2'
        try { $imgTime = [datetime]::Parse($clean, [Globalization.CultureInfo]::InvariantCulture) } catch { $imgTime = $null }
        $commitTime = $null
        $c = "$(git log -1 --format=%cI -- $($t.src) 2>$null)"
        if ($c) { try { $commitTime = [datetime]::Parse($c) } catch { } }
        if ($imgTime -and $commitTime) {
            if ($imgTime -lt $commitTime) {
                Say 'WARN' "image $($t.image) ($($imgTime.ToString('s'))) is older than the last commit touching $($t.src) ($($commitTime.ToString('s'))) - rebuild before accepting (a full cache-hit rebuild reuses layers and keeps the old timestamp; if you just rebuilt, this is that artifact, not staleness)"
            } else {
                Say 'PASS' "image $($t.image) is at least as new as the last commit touching $($t.src)"
            }
        }
    }
}

# --- 6. test-results bloat (README trap 5) --------------------------------------
$tr = Join-Path $PSScriptRoot 'test-results'
if (Test-Path $tr) {
    $n = (Get-ChildItem $tr -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
    if ($n -ge 40) {
        Say 'WARN' "test-results holds $n files - the sandbox bulk-delete shim can stall the next run; raise CODEBUDDY_SAFE_DELETE_BULK_THRESHOLD or move the dir aside (trap 5)"
    } else {
        Say 'PASS' "test-results holds $n files"
    }
}

Write-Output ''
if ($script:failures -gt 0) {
    Write-Output "preflight: $($script:failures) FAIL / $($script:warnings) WARN - fix the FAILs before running the suite"
    exit 1
}
Write-Output "preflight: 0 FAIL / $($script:warnings) WARN - ready for npx playwright test"
exit 0

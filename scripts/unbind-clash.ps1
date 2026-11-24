# unbind-clash.ps1 — permanently remove every Clash Verge proxy binding on this host.
#
# Run once, in ANY PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts/unbind-clash.ps1
#
# What it does: clears the ambient proxy variables at User/Machine scope, resets
# Windows (WinHTTP + IE) proxy to direct, strips git/npm proxy config, turns off
# Clash Verge's own system-proxy/TUN switches, and verifies a direct connection.
# It is idempotent: safe to run any number of times. It never touches the project
# source; that unbind already shipped in Epic 433.

$ErrorActionPreference = "Continue"
function Say($m) { Write-Host "[unbind] $m" }

$proxyNames = @('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy')

# 1. Process scope (this shell)
foreach ($n in $proxyNames) { [Environment]::SetEnvironmentVariable($n, $null, 'Process'); Remove-Item "Env:$n" -ErrorAction SilentlyContinue }
Say "cleared proxy vars in current process"

# 2. User scope (persisted for your future shells/apps)
foreach ($n in $proxyNames) { [Environment]::SetEnvironmentVariable($n, $null, 'User') }
Say "cleared proxy vars at User scope"

# 3. Machine scope (needs admin; skip quietly if not elevated)
try {
    foreach ($n in $proxyNames) { [Environment]::SetEnvironmentVariable($n, $null, 'Machine') }
    Say "cleared proxy vars at Machine scope"
} catch { Say "Machine scope needs admin — skipped (re-run as admin to clear it)" }

# 4. Windows proxy: WinHTTP + IE/WININET to direct
netsh winhttp reset proxy | Out-Null
Say "WinHTTP proxy reset to direct"
Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -Value 0 -ErrorAction SilentlyContinue
Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyServer -Value '' -ErrorAction SilentlyContinue
Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name AutoConfigURL -Value '' -ErrorAction SilentlyContinue
Say "IE/WININET proxy disabled"

# 5. git / npm global proxy
foreach ($k in @('http.proxy','https.proxy','http.proxyAuthMethod')) { git config --global --unset-all $k 2>$null }
npm config delete proxy 2>$null; npm config delete https-proxy 2>$null
Say "git/npm proxy config cleared"

# 6. Clash Verge's own system-proxy / TUN switches -> off (if config present)
$cv = "$env:USERPROFILE\.config\clash-verge\verge.yaml"
if (Test-Path $cv) {
    $txt = Get-Content -Raw -LiteralPath $cv
    $txt = $txt -replace '(?m)^enable_system_proxy:\s*.*$', 'enable_system_proxy: false'
    $txt = $txt -replace '(?m)^enable_tun_mode:\s*.*$', 'enable_tun_mode: false'
    Set-Content -LiteralPath $cv -Value $txt -NoNewline
    Say "Clash Verge system-proxy + TUN set to false"
} else { Say "no Clash Verge verge.yaml found — nothing to change there" }

# 7. Verify direct network
Say "verifying DIRECT connection (no proxy)..."
$ok = $true
foreach ($u in @('https://github.com','https://api.github.com','https://registry.npmjs.org')) {
    $code = curl.exe -s -o NUL -w '%{http_code}' --noproxy '*' --max-time 12 $u 2>&1
    Say "$code  $u"
    if ($code -ne '200') { $ok = $false }
}
if ($ok) { Say "SUCCESS — the host reaches the internet directly. You no longer need Clash." }
else { Say "Some hosts failed — check your router/ISP. This is no longer a Clash-proxy issue." }

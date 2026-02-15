# ONE-TIME ADMIN SETUP — Run this once as Administrator
# Enables WSL2 to connect to Chrome CDP instances on ports 9222-9225
#
# What it does:
# 1. Adds firewall rule allowing inbound TCP on 9222-9225
# 2. Sets up port proxy: forwards 0.0.0.0:922x -> 127.0.0.1:922x
#    (Chrome binds to localhost only; WSL2 is on a separate network)

Write-Host "Chrome CDP Setup for WSL2" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
Write-Host ""

# 1. Firewall rule
Write-Host "[1/2] Firewall rule..." -ForegroundColor Yellow
$rule = Get-NetFirewallRule -DisplayName "Chrome CDP for WSL" -ErrorAction SilentlyContinue
if ($rule) {
    Write-Host "  Already exists." -ForegroundColor Green
} else {
    New-NetFirewallRule -DisplayName "Chrome CDP for WSL" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 9222-9225 -Profile Any | Out-Null
    Write-Host "  Created firewall rule for ports 9222-9225." -ForegroundColor Green
}

# 2. Port proxy
Write-Host "[2/2] Port proxy (0.0.0.0 -> 127.0.0.1)..." -ForegroundColor Yellow
foreach ($port in 9222..9225) {
    netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null
    netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=127.0.0.1 | Out-Null
    Write-Host "  Port $port proxied." -ForegroundColor Green
}

Write-Host ""
Write-Host "Done! WSL can now reach Chrome CDP at:" -ForegroundColor Cyan
$wslIp = (Get-NetIPAddress -InterfaceAlias "vEthernet (WSL*)" -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress
if ($wslIp) {
    foreach ($port in 9222..9225) {
        Write-Host "  http://${wslIp}:$port" -ForegroundColor White
    }
} else {
    Write-Host "  http://<windows-host-ip>:9222-9225" -ForegroundColor White
}
Write-Host ""
Write-Host "Verify from WSL with: cdp status" -ForegroundColor Gray

# Keep window open briefly
Start-Sleep -Seconds 3

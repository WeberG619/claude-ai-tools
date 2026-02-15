# Launch Chrome CDP instances for Playwright automation
# Usage: .\launch_cdp.ps1           # Launch all 4
#        .\launch_cdp.ps1 -Port 1   # Launch just instance 1 (port 9222)
#        .\launch_cdp.ps1 -Port 2   # Launch just instance 2 (port 9223)
#        .\launch_cdp.ps1 -Kill      # Kill all CDP Chrome instances

param(
    [int]$Port = 0,
    [switch]$Kill
)

$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$BaseDataDir = "$env:LOCALAPPDATA\Temp\chrome-cdp"

$instances = @(
    @{ Port = 9222; Dir = "$BaseDataDir\session-1"; Name = "CDP-1" },
    @{ Port = 9223; Dir = "$BaseDataDir\session-2"; Name = "CDP-2" },
    @{ Port = 9224; Dir = "$BaseDataDir\session-3"; Name = "CDP-3" },
    @{ Port = 9225; Dir = "$BaseDataDir\session-4"; Name = "CDP-4" }
)

# Kill mode
if ($Kill) {
    Write-Host "Killing all CDP Chrome instances..." -ForegroundColor Yellow
    foreach ($inst in $instances) {
        $procs = Get-Process chrome -ErrorAction SilentlyContinue | Where-Object {
            try {
                $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
                $cmd -match "remote-debugging-port=$($inst.Port)"
            } catch { $false }
        }
        if ($procs) {
            $procs | Stop-Process -Force
            Write-Host "  Killed $($inst.Name) (port $($inst.Port))" -ForegroundColor Red
        }
    }
    Write-Host "Done." -ForegroundColor Green
    exit
}

# Filter to specific port if requested
if ($Port -ge 1 -and $Port -le 4) {
    $instances = @($instances[$Port - 1])
}

# Add firewall rules for WSL access (one-time, requires admin)
$ruleName = "Chrome CDP for WSL"
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $existing) {
    Write-Host "Adding firewall rule for WSL access to ports 9222-9225..." -ForegroundColor Yellow
    try {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort 9222-9225 -Profile Private -ErrorAction Stop | Out-Null
        Write-Host "  Firewall rule added." -ForegroundColor Green
    } catch {
        Write-Host "  Could not add firewall rule (need admin). Run once as admin:" -ForegroundColor Red
        Write-Host "  New-NetFirewallRule -DisplayName '$ruleName' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 9222-9225" -ForegroundColor Cyan
    }
}

# Launch instances
foreach ($inst in $instances) {
    # Check if already running
    $already = $false
    $procs = Get-Process chrome -ErrorAction SilentlyContinue
    foreach ($p in $procs) {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)" -ErrorAction SilentlyContinue).CommandLine
            if ($cmd -match "remote-debugging-port=$($inst.Port)") {
                $already = $true
                break
            }
        } catch {}
    }

    if ($already) {
        Write-Host "$($inst.Name) already running on port $($inst.Port)" -ForegroundColor Cyan
        continue
    }

    # Create data dir
    if (-not (Test-Path $inst.Dir)) {
        New-Item -ItemType Directory -Path $inst.Dir -Force | Out-Null
    }

    # Launch
    $args = @(
        "--remote-debugging-port=$($inst.Port)",
        "--user-data-dir=$($inst.Dir)",
        "--no-first-run",
        "--no-default-browser-check",
        "--remote-allow-origins=*"
    )

    Start-Process $ChromePath -ArgumentList $args
    Write-Host "$($inst.Name) launched on port $($inst.Port)" -ForegroundColor Green
}

Write-Host ""
Write-Host "CDP Endpoints:" -ForegroundColor White
foreach ($inst in $instances) {
    Write-Host "  $($inst.Name): http://localhost:$($inst.Port)" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "From WSL, connect via: http://$(hostname).local:<port> or check IP with: cat /etc/resolv.conf" -ForegroundColor Gray

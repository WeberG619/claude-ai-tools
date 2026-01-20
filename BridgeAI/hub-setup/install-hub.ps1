# BridgeAI Hub Installation Script
# Run this on your old computer that will become the hub

Write-Host "=============================================="
Write-Host "  BridgeAI Smart Hub Installer"
Write-Host "=============================================="
Write-Host ""

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Please run this script as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'"
    exit 1
}

# Step 1: Check Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Cyan
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "  Python not found. Installing..." -ForegroundColor Yellow
    winget install Python.Python.3.11 --silent
} else {
    Write-Host "  Python found!" -ForegroundColor Green
}

# Step 2: Install required packages
Write-Host ""
Write-Host "[2/5] Installing Python packages..." -ForegroundColor Cyan
pip install flask pywebostv websocket-client requests --quiet
Write-Host "  Packages installed!" -ForegroundColor Green

# Step 3: Check Tailscale
Write-Host ""
Write-Host "[3/5] Checking Tailscale..." -ForegroundColor Cyan
$tailscale = Get-Command tailscale -ErrorAction SilentlyContinue
if (-not $tailscale) {
    Write-Host "  Tailscale not found!" -ForegroundColor Yellow
    Write-Host "  Please install from: https://tailscale.com/download" -ForegroundColor Yellow
    Write-Host "  Then run this script again." -ForegroundColor Yellow
    Start-Process "https://tailscale.com/download"
    exit 1
} else {
    Write-Host "  Tailscale found!" -ForegroundColor Green
    $tsStatus = tailscale status 2>&1
    if ($tsStatus -match "stopped") {
        Write-Host "  Starting Tailscale..." -ForegroundColor Yellow
        tailscale up
    }
}

# Step 4: Create startup task
Write-Host ""
Write-Host "[4/5] Creating auto-start task..." -ForegroundColor Cyan

$hubPath = Split-Path -Parent $PSScriptRoot
$action = New-ScheduledTaskAction -Execute "pythonw.exe" -Argument "$hubPath\hub-setup\hub_server.py"
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Highest

Unregister-ScheduledTask -TaskName "BridgeAI Hub" -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName "BridgeAI Hub" -Action $action -Trigger $trigger -Settings $settings -Principal $principal
Write-Host "  Auto-start enabled!" -ForegroundColor Green

# Step 5: Configure firewall
Write-Host ""
Write-Host "[5/5] Configuring firewall..." -ForegroundColor Cyan
New-NetFirewallRule -DisplayName "BridgeAI Hub" -Direction Inbound -Port 5000 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
Write-Host "  Firewall configured!" -ForegroundColor Green

# Get Tailscale IP
Write-Host ""
Write-Host "=============================================="
Write-Host "  Installation Complete!"
Write-Host "=============================================="
Write-Host ""

$tsIP = (tailscale ip -4 2>&1)
Write-Host "Your BridgeAI Hub address:"
Write-Host "  Local:     http://localhost:5000" -ForegroundColor Green
Write-Host "  Tailscale: http://$tsIP:5000" -ForegroundColor Green
Write-Host ""
Write-Host "To start the hub now, run:"
Write-Host "  python `"$hubPath\hub-setup\hub_server.py`""
Write-Host ""
Write-Host "The hub will auto-start when this computer boots."
Write-Host ""

# Start the hub now
Write-Host "Starting BridgeAI Hub..."
Start-Process python -ArgumentList "$hubPath\hub-setup\hub_server.py" -WindowStyle Normal
Write-Host "Hub is running!" -ForegroundColor Green

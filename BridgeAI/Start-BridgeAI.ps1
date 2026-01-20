# BridgeAI Launcher
# Starts BridgeAI with all checks and configurations

param(
    [switch]$SetupOnly,
    [switch]$Verbose
)

$Host.UI.RawUI.WindowTitle = "BridgeAI"

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "       BridgeAI - Your AI Assistant" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

$BridgeAIPath = "D:\_CLAUDE-TOOLS\BridgeAI"

# Quick system check
Write-Host "  Checking system..." -ForegroundColor Gray

$checks = @{
    "Claude Code" = { claude --version 2>$null }
    "Python" = { python --version 2>$null }
    "Node.js" = { node --version 2>$null }
}

$allGood = $true
foreach ($check in $checks.GetEnumerator()) {
    $result = & $check.Value
    if ($result) {
        if ($Verbose) {
            Write-Host "  [OK] $($check.Key)" -ForegroundColor Green
        }
    } else {
        Write-Host "  [MISSING] $($check.Key)" -ForegroundColor Red
        $allGood = $false
    }
}

if (-not $allGood) {
    Write-Host ""
    Write-Host "  Some components are missing." -ForegroundColor Yellow
    Write-Host "  Run setup.ps1 to install them." -ForegroundColor Yellow
    Write-Host ""

    if (-not $SetupOnly) {
        $response = Read-Host "  Continue anyway? (y/n)"
        if ($response -ne 'y') {
            exit 1
        }
    } else {
        exit 1
    }
}

if ($SetupOnly) {
    Write-Host ""
    Write-Host "  All checks passed!" -ForegroundColor Green
    Write-Host ""
    exit 0
}

# Check system health
Write-Host ""
Write-Host "  Quick health check..." -ForegroundColor Gray
$health = & powershell.exe -ExecutionPolicy Bypass -File "$BridgeAIPath\scripts\system-diagnostics.ps1" -Check health 2>$null | ConvertFrom-Json

if ($health.memory.status -eq "high") {
    Write-Host "  [!] Memory is running high ($($health.memory.used_percent)%)" -ForegroundColor Yellow
}
if ($health.disk) {
    foreach ($drive in $health.disk) {
        if ($drive.status -eq "critical") {
            Write-Host "  [!] $($drive.drive) is almost full ($($drive.used_percent)%)" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "  Starting BridgeAI..." -ForegroundColor Green
Write-Host ""
Write-Host "  Just talk naturally. Ask for help anytime." -ForegroundColor Gray
Write-Host "  Type 'exit' or press Ctrl+C to quit." -ForegroundColor Gray
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""

# Change to BridgeAI directory and start
Set-Location $BridgeAIPath
claude

Write-Host ""
Write-Host "  BridgeAI session ended." -ForegroundColor Cyan
Write-Host ""

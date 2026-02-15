# Agent Command Center - Full Startup
# ====================================
# Starts: Dashboard + Autonomous Executor

Write-Host "=============================================="
Write-Host "   AGENT COMMAND CENTER - FULL STARTUP"
Write-Host "=============================================="
Write-Host ""

$dashboardPath = "D:\_CLAUDE-TOOLS\agent-dashboard"
Set-Location $dashboardPath

# Kill any existing processes
Write-Host "Cleaning up old processes..." -ForegroundColor Yellow
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -like "*agent*" -or $_.CommandLine -like "*agent-dashboard*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2

# Start Dashboard Server
Write-Host "Starting Dashboard Server..." -ForegroundColor Cyan
$dashboard = Start-Process -FilePath "wsl" -ArgumentList "bash -c 'cd /mnt/d/_CLAUDE-TOOLS/agent-dashboard && python server.py'" -WindowStyle Hidden -PassThru
Write-Host "  Dashboard PID: $($dashboard.Id)" -ForegroundColor Green

Start-Sleep -Seconds 3

# Start Autonomous Executor
Write-Host "Starting Autonomous Executor..." -ForegroundColor Cyan
$executor = Start-Process -FilePath "wsl" -ArgumentList "bash -c 'cd /mnt/d/_CLAUDE-TOOLS/agent-dashboard && python cli_executor.py'" -WindowStyle Hidden -PassThru
Write-Host "  Executor PID: $($executor.Id)" -ForegroundColor Green

Start-Sleep -Seconds 2

# Open Dashboard in Chrome
Write-Host ""
Write-Host "Opening Dashboard in Chrome..." -ForegroundColor Cyan
Start-Process "chrome.exe" -ArgumentList "http://localhost:8888"

Write-Host ""
Write-Host "=============================================="
Write-Host "   ALL SYSTEMS RUNNING"
Write-Host "=============================================="
Write-Host ""
Write-Host "Dashboard: http://localhost:8888" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C in this window to stop all agents"
Write-Host ""

# Wait for user to stop
try {
    while ($true) {
        Start-Sleep -Seconds 10

        # Check if processes are still running
        $dashRunning = Get-Process -Id $dashboard.Id -ErrorAction SilentlyContinue
        $execRunning = Get-Process -Id $executor.Id -ErrorAction SilentlyContinue

        if (-not $dashRunning) {
            Write-Host "Dashboard stopped - restarting..." -ForegroundColor Yellow
            $dashboard = Start-Process -FilePath "wsl" -ArgumentList "bash -c 'cd /mnt/d/_CLAUDE-TOOLS/agent-dashboard && python server.py'" -WindowStyle Hidden -PassThru
        }

        if (-not $execRunning) {
            Write-Host "Executor stopped - restarting..." -ForegroundColor Yellow
            $executor = Start-Process -FilePath "wsl" -ArgumentList "bash -c 'cd /mnt/d/_CLAUDE-TOOLS/agent-dashboard && python cli_executor.py'" -WindowStyle Hidden -PassThru
        }
    }
} finally {
    Write-Host "`nShutting down..." -ForegroundColor Yellow
    Stop-Process -Id $dashboard.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $executor.Id -Force -ErrorAction SilentlyContinue
    Write-Host "All agents stopped." -ForegroundColor Green
}

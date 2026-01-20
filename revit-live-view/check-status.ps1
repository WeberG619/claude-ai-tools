# Quick status check for Revit Live View system
Write-Host "=== Revit Live View Status ===" -ForegroundColor Cyan

# Check daemon process
$daemon = Get-Process -Name "powershell" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*revit-capture-daemon*" }

if ($daemon) {
    Write-Host "[OK] Daemon is running (PID: $($daemon.Id))" -ForegroundColor Green
} else {
    Write-Host "[!!] Daemon is NOT running" -ForegroundColor Red
}

# Check scheduled tasks
Write-Host ""
Write-Host "Scheduled Tasks:" -ForegroundColor Yellow
Get-ScheduledTask -TaskName "RevitLiveView*" | ForEach-Object {
    $status = if ($_.State -eq "Ready") { "Green" } else { "Yellow" }
    Write-Host "  - $($_.TaskName): $($_.State)" -ForegroundColor $status
}

# Check status file
$statusFile = "D:\revit_live_status.json"
if (Test-Path $statusFile) {
    $status = Get-Content $statusFile | ConvertFrom-Json
    Write-Host ""
    Write-Host "Last Capture:" -ForegroundColor Yellow
    Write-Host "  - Time: $($status.timestamp)"
    Write-Host "  - Windows: $($status.captured_count)"
    Write-Host "  - Daemon Flag: $($status.daemon_running)"
} else {
    Write-Host ""
    Write-Host "[!!] No status file found" -ForegroundColor Red
}

# Check Revit
$revit = Get-Process -Name "Revit" -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "Revit Instances: $($revit.Count)" -ForegroundColor Yellow

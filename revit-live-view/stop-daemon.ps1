# Stop the Revit Live View Capture Daemon
$processes = Get-Process -Name "powershell" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*revit-capture-daemon*" }

if ($processes) {
    $processes | Stop-Process -Force
    Write-Host "Revit Live View Daemon stopped."
} else {
    Write-Host "No running daemon found."
}

# Update status file
$statusFile = "D:\revit_live_status.json"
if (Test-Path $statusFile) {
    $status = Get-Content $statusFile | ConvertFrom-Json
    $status.daemon_running = $false
    $status | ConvertTo-Json | Set-Content $statusFile
}

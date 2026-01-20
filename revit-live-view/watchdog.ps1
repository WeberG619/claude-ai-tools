# Revit Live View Watchdog
# Checks if daemon is running and restarts if needed
# Run this periodically via Task Scheduler

$daemonRunning = Get-Process -Name "powershell" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*revit-capture-daemon*" }

if (-not $daemonRunning) {
    # Check if Revit is running - only start daemon if Revit is open
    $revitRunning = Get-Process -Name "Revit" -ErrorAction SilentlyContinue

    if ($revitRunning) {
        # Start the daemon
        Start-Process wscript.exe -ArgumentList "`"D:\_CLAUDE-TOOLS\revit-live-view\start-background.vbs`"" -WindowStyle Hidden

        # Log restart
        $log = @{
            timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
            action = "daemon_restarted"
            reason = "watchdog_detected_not_running"
        }
        $logFile = "D:\_CLAUDE-TOOLS\revit-live-view\watchdog.log"
        $log | ConvertTo-Json | Add-Content $logFile
    }
}

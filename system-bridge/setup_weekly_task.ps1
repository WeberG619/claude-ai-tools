# Setup Weekly Review Task in Windows Task Scheduler
# Run as Administrator

$taskName = "Claude Brain Weekly Review"
$description = "Weekly maintenance for Claude memory system - pattern synthesis, correction decay, archiving"

# Python executable path
$pythonPath = "python"

# Script path
$scriptPath = "D:\_CLAUDE-TOOLS\system-bridge\weekly_review.py"

# Run every Sunday at 8 PM
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 8:00PM

# Action - run weekly review in apply mode
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "$scriptPath --apply" -WorkingDirectory "D:\_CLAUDE-TOOLS\system-bridge"

# Settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable

# Register the task
try {
    # Remove existing task if present
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

    # Create new task
    Register-ScheduledTask -TaskName $taskName -Description $description -Trigger $trigger -Action $action -Settings $settings -RunLevel Limited

    Write-Host "✓ Task '$taskName' created successfully!" -ForegroundColor Green
    Write-Host "  Schedule: Every Sunday at 8:00 PM" -ForegroundColor Cyan
    Write-Host "  Script: $scriptPath" -ForegroundColor Cyan

} catch {
    Write-Host "✗ Failed to create task: $_" -ForegroundColor Red
    Write-Host "  Make sure to run as Administrator" -ForegroundColor Yellow
}

# Show task status
Write-Host "`nCurrent scheduled tasks for Claude:" -ForegroundColor White
Get-ScheduledTask | Where-Object { $_.TaskName -like "*Claude*" } | Format-Table TaskName, State, LastRunTime

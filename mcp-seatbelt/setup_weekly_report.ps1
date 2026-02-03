# Set up weekly scheduled task for seatbelt report
# Run this script once as Administrator

$taskName = "MCP Seatbelt Weekly Report"
$taskPath = "D:\_CLAUDE-TOOLS\mcp-seatbelt\weekly_report.ps1"

# Remove existing task if present
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# Create trigger: Every Sunday at 10 AM
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 10:00AM

# Create action
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$taskPath`""

# Create settings
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

# Register task
Register-ScheduledTask -TaskName $taskName -Trigger $trigger -Action $action -Settings $settings -Description "Generate weekly MCP Seatbelt security report"

Write-Host "✅ Scheduled task '$taskName' created"
Write-Host "   Runs every Sunday at 10:00 AM"
Write-Host ""
Write-Host "To run manually: schtasks /run /tn `"$taskName`""

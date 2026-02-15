# Setup Windows Scheduled Task to auto-dismiss Revit dialogs on startup
# Run this script as Administrator to create the scheduled task
# Author: BIM Ops Studio

$taskName = "RevitDialogAutoDismiss"
$scriptPath = "$PSScriptRoot\click_close_button.py"

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "Task '$taskName' already exists. Removing..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create the action - run Python script
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "`"$scriptPath`" --initial-delay 5"

# Create trigger - when Revit.exe starts
# Note: Windows Task Scheduler doesn't have a native "on app start" trigger
# We'll use a workaround with Event Log monitoring

# Alternative: Create a trigger that runs every 5 minutes and checks if Revit is running
$trigger = New-ScheduledTaskTrigger -AtLogOn

# Run with highest privileges
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest

# Settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Create and register the task
$task = New-ScheduledTask -Action $action -Principal $principal -Settings $settings -Trigger $trigger

Register-ScheduledTask -TaskName $taskName -InputObject $task -Force

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host " Scheduled Task Created!" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Task: $taskName"
Write-Host "Action: Runs dialog auto-closer at user login"
Write-Host ""
Write-Host "For more control, you can also:" -ForegroundColor Yellow
Write-Host "1. Add a shortcut to your Revit shortcut that runs the script first"
Write-Host "2. Use Revit's journal file to add a delay startup"
Write-Host ""

# Create a helper batch file to launch Revit WITH dialog dismisser
$revitLauncherContent = @"
@echo off
:: Launch Revit with Dialog Auto-Dismisser
:: Double-click this instead of Revit directly

echo Starting Revit Dialog Auto-Dismisser...
start "" pythonw "%~dp0click_close_button.py" --initial-delay 3

echo Launching Revit...
start "" "C:\Program Files\Autodesk\Revit 2026\Revit.exe"

:: Also try 2025 if 2026 doesn't exist
if not exist "C:\Program Files\Autodesk\Revit 2026\Revit.exe" (
    start "" "C:\Program Files\Autodesk\Revit 2025\Revit.exe"
)
"@

$revitLauncherPath = "$PSScriptRoot\Launch_Revit_Clean.bat"
$revitLauncherContent | Out-File -FilePath $revitLauncherPath -Encoding ASCII

Write-Host "Also created: Launch_Revit_Clean.bat" -ForegroundColor Green
Write-Host "Use this batch file to start Revit with auto-dialog-dismisser" -ForegroundColor Gray

# Revit Startup Dialog Dismisser
# Automatically closes add-in startup dialogs by sending Enter key
# Run this after launching Revit to clear all popup dialogs

param(
    [int]$MaxAttempts = 15,      # Maximum dialogs to close
    [int]$DelayMs = 800,         # Delay between attempts
    [int]$InitialDelayMs = 3000  # Wait for Revit to show first dialog
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

Write-Host "Revit Dialog Dismisser Starting..." -ForegroundColor Cyan
Write-Host "Waiting $($InitialDelayMs/1000) seconds for Revit dialogs to appear..."
Start-Sleep -Milliseconds $InitialDelayMs

$dialogsClosed = 0

for ($i = 1; $i -le $MaxAttempts; $i++) {
    # Send Enter key to close any active dialog
    [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
    $dialogsClosed++

    Write-Host "  [$i] Sent Enter key" -ForegroundColor Gray
    Start-Sleep -Milliseconds $DelayMs
}

Write-Host ""
Write-Host "Dialog dismissal complete!" -ForegroundColor Green
Write-Host "Sent $dialogsClosed Enter key presses to Revit." -ForegroundColor Green
Write-Host ""
Write-Host "If dialogs remain, run again or increase -MaxAttempts" -ForegroundColor Yellow

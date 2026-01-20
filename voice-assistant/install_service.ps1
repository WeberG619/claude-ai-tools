# Install Claude Voice Service
# This adds the voice service to Windows startup (system tray version)

$servicePath = "D:\_CLAUDE-TOOLS\voice-assistant"

# First install dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow
pip show SpeechRecognition | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install SpeechRecognition pyaudio edge-tts pystray pillow
}

# Create startup shortcut
$WshShell = New-Object -ComObject WScript.Shell
$startupFolder = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupFolder "ClaudeVoiceService.lnk"

$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "pythonw.exe"
$shortcut.Arguments = "`"$servicePath\voice_tray.pyw`""
$shortcut.WorkingDirectory = $servicePath
$shortcut.WindowStyle = 7  # Minimized
$shortcut.Description = "Claude Voice Assistant - System Tray"
$shortcut.Save()

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Claude Voice Service Installed" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Startup shortcut created at:" -ForegroundColor Green
Write-Host "  $shortcutPath" -ForegroundColor White
Write-Host ""
Write-Host "The service will start automatically when Windows starts." -ForegroundColor Yellow
Write-Host "Look for the microphone icon in your system tray." -ForegroundColor Yellow
Write-Host ""
Write-Host "To start it now, run:" -ForegroundColor Green
Write-Host "  pythonw `"$servicePath\voice_tray.pyw`"" -ForegroundColor White
Write-Host ""
Write-Host "Or for console mode (with debug output):" -ForegroundColor Green
Write-Host "  python `"$servicePath\voice_service.py`"" -ForegroundColor White

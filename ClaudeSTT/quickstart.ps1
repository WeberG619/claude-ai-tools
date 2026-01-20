Write-Host "`nClaude STT Quick Start" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan
Write-Host "`nThis script will help you get started quickly without compilation issues." -ForegroundColor Yellow

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $scriptPath "python"

Push-Location $pythonPath

try {
    Write-Host "`nInstalling simplified requirements..." -ForegroundColor Yellow
    python -m pip install --upgrade pip --quiet
    python -m pip install -r requirements-simple.txt
    
    Write-Host "`nTesting installation..." -ForegroundColor Yellow
    $testCode = @"
import sounddevice as sd
print(f'Found {len(sd.query_devices())} audio devices')
print('Audio system working!')
"@
    
    python -c $testCode
    
    Write-Host "`nTesting audio system..." -ForegroundColor Yellow
    python test_audio.py
    
    Write-Host "`nPress any key to start the voice assistant..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    
    Write-Host "`nStarting Claude STT..." -ForegroundColor Green
    Write-Host "Say 'Claude' to activate, then speak your command" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
    
    python example_simple.py
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
finally {
    Pop-Location
}
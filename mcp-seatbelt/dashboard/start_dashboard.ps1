# MCP Seatbelt Dashboard Launcher
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host ""
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "  MCP Seatbelt Dashboard"                 -ForegroundColor Cyan
Write-Host "  http://localhost:5050"                  -ForegroundColor Yellow
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

# Check Flask is installed
$flaskCheck = python -c "import flask" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Flask..." -ForegroundColor Yellow
    pip install flask
}

# Open browser after short delay
Start-Job -ScriptBlock {
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:5050"
} | Out-Null

# Run dashboard
python app.py

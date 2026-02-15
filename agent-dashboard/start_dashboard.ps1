# Agent Dashboard Launcher
Write-Host "=========================================="
Write-Host "   Agent Command Center Dashboard"
Write-Host "=========================================="
Write-Host ""

$dashboardPath = "D:\_CLAUDE-TOOLS\agent-dashboard"
Set-Location $dashboardPath

# Check if dependencies are installed
$checkFastapi = python -c "import fastapi" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

Write-Host "Starting server on http://localhost:8080" -ForegroundColor Green
Write-Host "Opening browser..." -ForegroundColor Cyan
Start-Sleep -Seconds 2

# Open browser
Start-Process "chrome.exe" -ArgumentList "http://localhost:8080"

# Start server
python server.py

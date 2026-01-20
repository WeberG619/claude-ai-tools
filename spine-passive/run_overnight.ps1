# Spine Passive Learner - Overnight Extraction
# Run this from PowerShell (not WSL) to extract from Revit projects

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " SPINE PASSIVE LEARNER - OVERNIGHT TRAINING" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

Set-Location "D:\_CLAUDE-TOOLS\spine-passive"

# Check if Revit MCP Bridge is running
Write-Host "Checking Revit MCP Bridge connection..." -ForegroundColor Yellow

$pipeName = "RevitMCPBridge2026"
$pipeExists = [System.IO.Directory]::GetFiles("\\.\pipe\") | Where-Object { $_ -like "*$pipeName*" }

if (-not $pipeExists) {
    Write-Host "ERROR: RevitMCPBridge2026 not found!" -ForegroundColor Red
    Write-Host "Make sure Revit 2026 is running with MCP Bridge started." -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "RevitMCPBridge2026 is running!" -ForegroundColor Green
Write-Host ""

# Set Python path and run using Windows Python (not WSL)
$env:PYTHONPATH = "D:\_CLAUDE-TOOLS\spine-passive\src"
$windowsPython = "C:\Users\rick\miniconda3\python.exe"

Write-Host "Starting overnight extraction..." -ForegroundColor Yellow
Write-Host "This will process all pending Revit projects." -ForegroundColor White
Write-Host "Press Ctrl+C to stop at any time." -ForegroundColor White
Write-Host ""

# Run extraction using Windows Python
& $windowsPython -m spine_passive extract --overnight --revit-version 2026

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host " EXTRACTION COMPLETE" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Run 'python -m spine_passive stats' to see results."
Write-Host "Run 'python -m spine_passive analyze' to see patterns."
Write-Host ""
Read-Host "Press Enter to exit"

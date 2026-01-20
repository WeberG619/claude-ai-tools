# Revit Drop Zone Monitor Launcher

$ErrorActionPreference = "Stop"

Write-Host "`n===== REVIT DROP ZONE MONITOR =====" -ForegroundColor Cyan
Write-Host "Development Assistant for Revit" -ForegroundColor Cyan
Write-Host "==================================`n" -ForegroundColor Cyan

# Configuration
$monitorScript = "D:\claude-code-revit\dropzone_monitor.py"
$configFile = "D:\claude-code-revit\config\dropzone_config.json"

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.7+" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check files
if (-not (Test-Path $monitorScript)) {
    Write-Host "✗ Monitor script not found at: $monitorScript" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

if (-not (Test-Path $configFile)) {
    Write-Host "✗ Config file not found at: $configFile" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "`nDrop files into these zones:" -ForegroundColor Yellow
Write-Host "  📝 Code Generator: revit_zones\code_generator" -ForegroundColor Gray
Write-Host "  🐛 Error Debugger: revit_zones\error_debugger" -ForegroundColor Gray
Write-Host "  🧪 Test Generator: dev_zones	est_generator" -ForegroundColor Gray
Write-Host "  📚 Doc Builder: dev_zones\doc_builder" -ForegroundColor Gray

Write-Host "`nStarting monitor... (Ctrl+C to stop)`n" -ForegroundColor Green

# Start monitoring
python $monitorScript

Write-Host "`nMonitor stopped." -ForegroundColor Yellow
Read-Host "Press Enter to exit"

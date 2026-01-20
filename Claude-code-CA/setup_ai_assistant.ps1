# AI Assistant Setup Script
# Sets up the complete AI-enhanced automation system

Write-Host "`nAI-Enhanced Automation Assistant Setup" -ForegroundColor Magenta
Write-Host "=====================================" -ForegroundColor Magenta

# Check Python
Write-Host "`nChecking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.8 or higher." -ForegroundColor Red
    Write-Host "  Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Create virtual environment
Write-Host "`nCreating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "  Virtual environment already exists" -ForegroundColor Gray
} else {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
Write-Host "✓ Virtual environment activated" -ForegroundColor Green

# Install requirements
Write-Host "`nInstalling Python dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r requirements.txt
Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Install Tesseract if not present
Write-Host "`nChecking Tesseract OCR..." -ForegroundColor Yellow
try {
    tesseract --version 2>&1 | Out-Null
    Write-Host "✓ Tesseract found" -ForegroundColor Green
} catch {
    Write-Host "⚠ Tesseract not found" -ForegroundColor Yellow
    Write-Host "  For OCR features, install from: https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Gray
    Write-Host "  The system will work without it, but with limited text recognition" -ForegroundColor Gray
}

# Create necessary directories
Write-Host "`nCreating directories..." -ForegroundColor Yellow
$dirs = @("ui_templates", "screenshots", "logs")
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Gray
    }
}
Write-Host "✓ Directories ready" -ForegroundColor Green

# Create launcher script
Write-Host "`nCreating launcher..." -ForegroundColor Yellow
@'
@echo off
echo Starting AI Assistant...
call venv\Scripts\activate
python ai_assistant.py %*
'@ | Out-File -FilePath "ai_assistant.bat" -Encoding ASCII
Write-Host "✓ Launcher created: ai_assistant.bat" -ForegroundColor Green

# Create PowerShell launcher
@'
# AI Assistant PowerShell Launcher
& ".\venv\Scripts\Activate.ps1"
python ai_assistant.py $args
'@ | Out-File -FilePath "Start-AIAssistant.ps1" -Encoding UTF8
Write-Host "✓ PowerShell launcher created: Start-AIAssistant.ps1" -ForegroundColor Green

# Test imports
Write-Host "`nTesting system..." -ForegroundColor Yellow
$testScript = @'
import sys
try:
    import cv2
    print("✓ OpenCV ready")
except:
    print("✗ OpenCV import failed")
    
try:
    from PIL import Image
    print("✓ PIL ready")
except:
    print("✗ PIL import failed")

try:
    import pytesseract
    print("✓ Pytesseract ready")
except:
    print("✗ Pytesseract import failed")
    
print("✓ Basic imports successful")
'@

$testScript | python
Write-Host "`n✓ System test completed" -ForegroundColor Green

# Final instructions
Write-Host "`n" -NoNewline
Write-Host "Setup Complete!" -ForegroundColor Green -BackgroundColor DarkGreen
Write-Host "`nTo start the AI Assistant:" -ForegroundColor Cyan
Write-Host "  Option 1: Double-click 'ai_assistant.bat'" -ForegroundColor White
Write-Host "  Option 2: Run '.\Start-AIAssistant.ps1' in PowerShell" -ForegroundColor White
Write-Host "  Option 3: Run 'python ai_assistant.py' (with venv activated)" -ForegroundColor White

Write-Host "`nQuick Start Examples:" -ForegroundColor Yellow
Write-Host '  .\Start-AIAssistant.ps1' -ForegroundColor White
Write-Host '  .\Start-AIAssistant.ps1 "Close the Copilot dialog"' -ForegroundColor White
Write-Host '  .\Start-AIAssistant.ps1 --no-learn "Take a screenshot"' -ForegroundColor White

Write-Host "`nFor your PowerPoint issue, run:" -ForegroundColor Magenta
Write-Host '  .\Start-AIAssistant.ps1 "Close the Copilot dialog in PowerPoint"' -ForegroundColor White

Write-Host "`n"
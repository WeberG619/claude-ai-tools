param(
    [switch]$SkipVCCheck,
    [switch]$UseCPU
)

Write-Host "Claude STT Installation Script" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan

$ErrorActionPreference = "Stop"

# Check for Visual C++ Build Tools
if (-not $SkipVCCheck) {
    Write-Host "`nChecking for Visual C++ Build Tools..." -ForegroundColor Yellow
    
    $vcInstalled = $false
    $vsWhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    
    if (Test-Path $vsWhere) {
        $installations = & $vsWhere -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -format json | ConvertFrom-Json
        if ($installations.Count -gt 0) {
            $vcInstalled = $true
        }
    }
    
    if (-not $vcInstalled) {
        Write-Host "Visual C++ Build Tools not found!" -ForegroundColor Red
        Write-Host "`nYou have two options:" -ForegroundColor Yellow
        Write-Host "1. Install Microsoft C++ Build Tools from:" -ForegroundColor White
        Write-Host "   https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor Cyan
        Write-Host "2. Run this script with -SkipVCCheck to use pre-built wheels" -ForegroundColor White
        Write-Host "`nRecommended: Use option 2 for easier installation" -ForegroundColor Green
        exit 1
    }
}

# Check Python version
Write-Host "`nChecking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 8)) {
            throw "Python 3.8 or higher required. Found: $pythonVersion"
        }
        Write-Host "Found $pythonVersion" -ForegroundColor Green
    }
}
catch {
    Write-Host "Python not found or version too old!" -ForegroundColor Red
    Write-Host "Please install Python 3.8 or higher from https://python.org" -ForegroundColor Yellow
    exit 1
}

# Navigate to python directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $scriptPath "python"
Push-Location $pythonPath

try {
    # Upgrade pip
    Write-Host "`nUpgrading pip..." -ForegroundColor Yellow
    python -m pip install --upgrade pip --quiet
    
    # Install requirements
    Write-Host "`nInstalling Python packages..." -ForegroundColor Yellow
    Write-Host "This may take several minutes on first install..." -ForegroundColor Gray
    
    if ($UseCPU) {
        # Install CPU-only versions of PyTorch
        Write-Host "Installing CPU-only versions of PyTorch..." -ForegroundColor Yellow
        python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet
    }
    
    # Install other requirements
    python -m pip install -r requirements.txt --quiet
    
    # Test imports
    Write-Host "`nTesting package imports..." -ForegroundColor Yellow
    $testScript = @"
import sys
try:
    import numpy
    import pyaudio
    import faster_whisper
    import torch
    import colorama
    print('All imports successful!')
    sys.exit(0)
except ImportError as e:
    print(f'Import error: {e}')
    sys.exit(1)
"@
    
    $testResult = python -c $testScript 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Package import test failed: $testResult"
    }
    Write-Host $testResult -ForegroundColor Green
    
    # Download Whisper model
    Write-Host "`nPre-downloading Whisper model..." -ForegroundColor Yellow
    $downloadScript = @"
from faster_whisper import WhisperModel
print('Downloading base model...')
model = WhisperModel('base', device='cpu')
print('Model downloaded successfully!')
"@
    
    python -c $downloadScript
    
    Write-Host "`nPython installation completed successfully!" -ForegroundColor Green
    
    # Build C# components
    Write-Host "`nBuilding C# components..." -ForegroundColor Yellow
    $buildScript = Join-Path $scriptPath "build.ps1"
    if (Test-Path $buildScript) {
        & $buildScript
    }
    else {
        Write-Host "build.ps1 not found, skipping C# build" -ForegroundColor Yellow
    }
    
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "Installation completed successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "1. Test Python STT: python example.py" -ForegroundColor White
    Write-Host "2. Deploy to Revit: .\deploy.ps1" -ForegroundColor White
    Write-Host "3. Start Revit and look for 'Claude Voice' tab" -ForegroundColor White
    
}
catch {
    Write-Host "`nInstallation failed!" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
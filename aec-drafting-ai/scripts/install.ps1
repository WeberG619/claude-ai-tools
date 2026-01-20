# AEC Drafting AI - Windows Installer
# Run as: .\install.ps1

param(
    [string]$RevitVersion = "2026",
    [switch]$SkipDLL,
    [switch]$SkipClaude,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  AEC Drafting AI - Installer v0.1  " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Write-Host "[1/6] Checking prerequisites..." -ForegroundColor Yellow

# Check Revit
$RevitPath = "C:\Program Files\Autodesk\Revit $RevitVersion"
if (-not (Test-Path $RevitPath)) {
    Write-Host "  ERROR: Revit $RevitVersion not found at $RevitPath" -ForegroundColor Red
    Write-Host "  Please install Revit $RevitVersion first." -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Revit $RevitVersion found" -ForegroundColor Green

# Check Python
$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    Write-Host "  ERROR: Python not found in PATH" -ForegroundColor Red
    Write-Host "  Please install Python 3.10+ and add to PATH" -ForegroundColor Red
    exit 1
}
$PythonVersion = & python --version 2>&1
Write-Host "  ✓ $PythonVersion found" -ForegroundColor Green

# Check Claude Code
$Claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $Claude) {
    Write-Host "  WARNING: Claude Code CLI not found" -ForegroundColor Yellow
    Write-Host "  Install with: npm install -g @anthropic/claude-code" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ Claude Code CLI found" -ForegroundColor Green
}

# Install Revit Add-in
Write-Host ""
Write-Host "[2/6] Installing Revit add-in..." -ForegroundColor Yellow

$AddinsDir = "$env:APPDATA\Autodesk\Revit\Addins\$RevitVersion"
if (-not (Test-Path $AddinsDir)) {
    New-Item -ItemType Directory -Path $AddinsDir -Force | Out-Null
}

if (-not $SkipDLL) {
    $DLLSource = "$RootDir\revit-addin\RevitMCPBridge2026.dll"
    $AddinSource = "$RootDir\revit-addin\RevitMCPBridge2026.addin"

    if (Test-Path $DLLSource) {
        Copy-Item $DLLSource $AddinsDir -Force
        Copy-Item $AddinSource $AddinsDir -Force
        Write-Host "  ✓ Revit add-in installed to $AddinsDir" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: DLL not found at $DLLSource" -ForegroundColor Yellow
        Write-Host "  You'll need to build or copy the DLL manually" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Skipped (--SkipDLL)" -ForegroundColor Gray
}

# Install Python dependencies
Write-Host ""
Write-Host "[3/6] Installing Python dependencies..." -ForegroundColor Yellow

$RequirementsFile = "$RootDir\requirements.txt"
if (Test-Path $RequirementsFile) {
    & pip install -r $RequirementsFile --quiet
    Write-Host "  ✓ Python dependencies installed" -ForegroundColor Green
} else {
    # Install common dependencies
    & pip install pydantic mcp pymupdf edge-tts numpy --quiet 2>$null
    Write-Host "  ✓ Core dependencies installed" -ForegroundColor Green
}

# Configure Claude Code
Write-Host ""
Write-Host "[4/6] Configuring Claude Code..." -ForegroundColor Yellow

$ClaudeConfigDir = "$env:USERPROFILE\.claude"
if (-not (Test-Path $ClaudeConfigDir)) {
    New-Item -ItemType Directory -Path $ClaudeConfigDir -Force | Out-Null
}

$SettingsTemplate = "$RootDir\config\claude_settings.json"
$SettingsDest = "$ClaudeConfigDir\settings.json"

if (Test-Path $SettingsTemplate) {
    if (-not (Test-Path $SettingsDest)) {
        Copy-Item $SettingsTemplate $SettingsDest
        Write-Host "  ✓ Claude settings installed" -ForegroundColor Green
    } else {
        Write-Host "  ✓ Claude settings already exist (not overwritten)" -ForegroundColor Green
    }
} else {
    Write-Host "  Settings template not found, skipping" -ForegroundColor Gray
}

# Copy project registry
Write-Host ""
Write-Host "[5/6] Setting up project registry..." -ForegroundColor Yellow

$RegistrySource = "$RootDir\config\project_registry.json"
$RegistryDest = "$RootDir\project_registry.json"

if ((Test-Path $RegistrySource) -and -not (Test-Path $RegistryDest)) {
    Copy-Item $RegistrySource $RegistryDest
    Write-Host "  ✓ Project registry template copied" -ForegroundColor Green
    Write-Host "  Edit $RegistryDest to add your projects" -ForegroundColor Gray
}

# Verify installation
Write-Host ""
Write-Host "[6/6] Verifying installation..." -ForegroundColor Yellow

$Checks = @{
    "Revit add-in" = Test-Path "$AddinsDir\RevitMCPBridge2026.dll"
    "Python" = $null -ne (Get-Command python -ErrorAction SilentlyContinue)
    "Claude CLI" = $null -ne (Get-Command claude -ErrorAction SilentlyContinue)
}

$AllPassed = $true
foreach ($check in $Checks.GetEnumerator()) {
    if ($check.Value) {
        Write-Host "  ✓ $($check.Key)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $($check.Key)" -ForegroundColor Red
        $AllPassed = $false
    }
}

# Summary
Write-Host ""
Write-Host "=====================================" -ForegroundColor Cyan
if ($AllPassed) {
    Write-Host "  Installation Complete!            " -ForegroundColor Green
} else {
    Write-Host "  Installation Partial              " -ForegroundColor Yellow
}
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Restart Revit (if running)" -ForegroundColor Gray
Write-Host "  2. Open a project in Revit" -ForegroundColor Gray
Write-Host "  3. Run 'claude' in any terminal" -ForegroundColor Gray
Write-Host "  4. Try: 'Show me the project info'" -ForegroundColor Gray
Write-Host ""

if (-not $AllPassed) {
    Write-Host "To fix missing components:" -ForegroundColor Yellow
    if (-not $Checks["Claude CLI"]) {
        Write-Host "  npm install -g @anthropic/claude-code" -ForegroundColor Gray
    }
}

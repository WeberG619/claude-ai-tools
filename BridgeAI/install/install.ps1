# BridgeAI Installer
# Run this on a new computer to set up BridgeAI

param(
    [string]$InstallPath = "C:\BridgeAI",
    [switch]$SkipDependencies
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "     BridgeAI Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as admin (optional but helpful)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[INFO] Running without admin rights - some features may be limited" -ForegroundColor Yellow
    Write-Host ""
}

# Step 1: Check/Install Node.js
Write-Host "Step 1: Checking Node.js..." -ForegroundColor White
$nodeVersion = node --version 2>$null
if ($nodeVersion) {
    Write-Host "  [OK] Node.js $nodeVersion installed" -ForegroundColor Green
} else {
    if ($SkipDependencies) {
        Write-Host "  [SKIP] Node.js not installed" -ForegroundColor Yellow
    } else {
        Write-Host "  [INSTALLING] Node.js..." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  Please download and install Node.js from:" -ForegroundColor White
        Write-Host "  https://nodejs.org/en/download/" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  After installing, run this script again." -ForegroundColor White
        Start-Process "https://nodejs.org/en/download/"
        exit 1
    }
}

# Step 2: Check/Install Python
Write-Host "Step 2: Checking Python..." -ForegroundColor White
$pythonVersion = python --version 2>$null
if ($pythonVersion) {
    Write-Host "  [OK] $pythonVersion installed" -ForegroundColor Green
} else {
    if ($SkipDependencies) {
        Write-Host "  [SKIP] Python not installed" -ForegroundColor Yellow
    } else {
        Write-Host "  [INSTALLING] Python..." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  Please download and install Python from:" -ForegroundColor White
        Write-Host "  https://www.python.org/downloads/" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  IMPORTANT: Check 'Add Python to PATH' during installation!" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  After installing, run this script again." -ForegroundColor White
        Start-Process "https://www.python.org/downloads/"
        exit 1
    }
}

# Step 3: Install Claude Code CLI
Write-Host "Step 3: Checking Claude Code..." -ForegroundColor White
$claudeVersion = claude --version 2>$null
if ($claudeVersion) {
    Write-Host "  [OK] Claude Code installed" -ForegroundColor Green
} else {
    Write-Host "  [INSTALLING] Claude Code CLI..." -ForegroundColor Yellow
    npm install -g @anthropic-ai/claude-code
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Claude Code installed" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Failed to install Claude Code" -ForegroundColor Red
        exit 1
    }
}

# Step 4: Create installation directory
Write-Host "Step 4: Setting up BridgeAI..." -ForegroundColor White
if (-not (Test-Path $InstallPath)) {
    New-Item -Path $InstallPath -ItemType Directory -Force | Out-Null
    Write-Host "  [OK] Created $InstallPath" -ForegroundColor Green
} else {
    Write-Host "  [OK] $InstallPath already exists" -ForegroundColor Green
}

# Step 5: Copy BridgeAI files
Write-Host "Step 5: Copying files..." -ForegroundColor White
$sourcePath = Split-Path -Parent $PSScriptRoot
Copy-Item -Path "$sourcePath\*" -Destination $InstallPath -Recurse -Force -Exclude "install"
Write-Host "  [OK] Files copied" -ForegroundColor Green

# Step 6: Install Python dependencies
Write-Host "Step 6: Installing Python packages..." -ForegroundColor White
$reqFiles = Get-ChildItem -Path $InstallPath -Recurse -Filter "requirements.txt"
foreach ($req in $reqFiles) {
    pip install -r $req.FullName -q 2>$null
}
# Also install MCP SDK
pip install mcp fastmcp edge-tts -q 2>$null
Write-Host "  [OK] Python packages installed" -ForegroundColor Green

# Step 7: Create desktop shortcut
Write-Host "Step 7: Creating shortcut..." -ForegroundColor White
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "BridgeAI.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$InstallPath\Start-BridgeAI.ps1`""
$shortcut.WorkingDirectory = $InstallPath
$shortcut.Description = "BridgeAI - Your AI Assistant"
$shortcut.Save()

Write-Host "  [OK] Desktop shortcut created" -ForegroundColor Green

# Step 8: Configure Claude settings
Write-Host "Step 8: Configuring Claude..." -ForegroundColor White
$claudeConfigPath = Join-Path $env:USERPROFILE ".claude"
if (-not (Test-Path $claudeConfigPath)) {
    New-Item -Path $claudeConfigPath -ItemType Directory -Force | Out-Null
}

# Copy settings
$settingsSource = Join-Path $InstallPath ".claude\settings.json"
$settingsDest = Join-Path $claudeConfigPath "settings.local.json"

# Update paths in settings for this machine
$settings = Get-Content $settingsSource | ConvertFrom-Json
# Update paths to use install location
$settingsJson = $settings | ConvertTo-Json -Depth 10
$settingsJson = $settingsJson -replace "/mnt/d/_CLAUDE-TOOLS/BridgeAI", $InstallPath.Replace("\", "/")
$settingsJson = $settingsJson -replace "D:/_CLAUDE-TOOLS/BridgeAI", $InstallPath.Replace("\", "/")
$settingsJson | Set-Content $settingsDest

Write-Host "  [OK] Claude configured" -ForegroundColor Green

# Done!
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "     Installation Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "BridgeAI is ready to use!" -ForegroundColor White
Write-Host ""
Write-Host "To start:" -ForegroundColor Gray
Write-Host "  - Double-click 'BridgeAI' on your desktop" -ForegroundColor Cyan
Write-Host "  - Or run: $InstallPath\Start-BridgeAI.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "First time setup:" -ForegroundColor Gray
Write-Host "  - You'll need to log in to Claude (anthropic.com)" -ForegroundColor White
Write-Host "  - Just follow the prompts in the terminal" -ForegroundColor White
Write-Host ""

# Offer to start now
$response = Read-Host "Start BridgeAI now? (y/n)"
if ($response -eq 'y') {
    & "$InstallPath\Start-BridgeAI.ps1"
}

# BridgeAI Setup Script
# Run this to set up BridgeAI on a new computer

param(
    [switch]$Full,
    [switch]$CheckOnly
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  BridgeAI Setup" -ForegroundColor Cyan
Write-Host "  Your AI Assistant" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$errors = @()
$warnings = @()

# Check 1: PowerShell version
Write-Host "Checking PowerShell..." -NoNewline
$psVersion = $PSVersionTable.PSVersion.Major
if ($psVersion -ge 5) {
    Write-Host " OK (v$psVersion)" -ForegroundColor Green
} else {
    Write-Host " WARNING (v$psVersion - recommend v5+)" -ForegroundColor Yellow
    $warnings += "PowerShell version is old"
}

# Check 2: Node.js (required for Claude Code)
Write-Host "Checking Node.js..." -NoNewline
try {
    $nodeVersion = node --version 2>$null
    if ($nodeVersion) {
        Write-Host " OK ($nodeVersion)" -ForegroundColor Green
    } else {
        throw "Not found"
    }
} catch {
    Write-Host " MISSING" -ForegroundColor Red
    $errors += "Node.js is required - install from https://nodejs.org"
}

# Check 3: npm
Write-Host "Checking npm..." -NoNewline
try {
    $npmVersion = npm --version 2>$null
    if ($npmVersion) {
        Write-Host " OK (v$npmVersion)" -ForegroundColor Green
    } else {
        throw "Not found"
    }
} catch {
    Write-Host " MISSING" -ForegroundColor Red
    $errors += "npm is required (comes with Node.js)"
}

# Check 4: Python (for some MCP servers)
Write-Host "Checking Python..." -NoNewline
try {
    $pythonVersion = python --version 2>$null
    if ($pythonVersion) {
        Write-Host " OK ($pythonVersion)" -ForegroundColor Green
    } else {
        throw "Not found"
    }
} catch {
    Write-Host " OPTIONAL (some features need it)" -ForegroundColor Yellow
    $warnings += "Python not found - some features will be limited"
}

# Check 5: Claude Code CLI
Write-Host "Checking Claude Code..." -NoNewline
try {
    $claudeVersion = claude --version 2>$null
    if ($claudeVersion) {
        Write-Host " OK" -ForegroundColor Green
    } else {
        throw "Not found"
    }
} catch {
    Write-Host " MISSING" -ForegroundColor Red
    $errors += "Claude Code CLI required - install with: npm install -g @anthropic-ai/claude-code"
}

# Check 6: Internet connectivity
Write-Host "Checking internet..." -NoNewline
$internet = Test-NetConnection -ComputerName "api.anthropic.com" -Port 443 -WarningAction SilentlyContinue
if ($internet.TcpTestSucceeded) {
    Write-Host " OK" -ForegroundColor Green
} else {
    Write-Host " FAILED" -ForegroundColor Red
    $errors += "Cannot reach Anthropic API - check internet connection"
}

# Check 7: Disk space
Write-Host "Checking disk space..." -NoNewline
$disk = Get-CimInstance -ClassName Win32_LogicalDisk -Filter "DeviceID='C:'"
$freeGB = [math]::Round($disk.FreeSpace / 1GB, 1)
if ($freeGB -ge 5) {
    Write-Host " OK ($freeGB GB free)" -ForegroundColor Green
} else {
    Write-Host " LOW ($freeGB GB free)" -ForegroundColor Yellow
    $warnings += "Low disk space - recommend 5GB+ free"
}

# Check 8: Memory
Write-Host "Checking memory..." -NoNewline
$os = Get-CimInstance -ClassName Win32_OperatingSystem
$totalGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
if ($totalGB -ge 8) {
    Write-Host " OK ($totalGB GB)" -ForegroundColor Green
} else {
    Write-Host " LOW ($totalGB GB)" -ForegroundColor Yellow
    $warnings += "Low memory - BridgeAI works best with 8GB+"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

# Summary
if ($errors.Count -eq 0) {
    Write-Host "STATUS: Ready to use!" -ForegroundColor Green
    Write-Host ""
    Write-Host "To start BridgeAI, run:" -ForegroundColor White
    Write-Host "  claude" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "STATUS: Setup needed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please fix these issues:" -ForegroundColor White
    foreach ($error in $errors) {
        Write-Host "  - $error" -ForegroundColor Red
    }
    Write-Host ""
}

if ($warnings.Count -gt 0) {
    Write-Host "Warnings (optional fixes):" -ForegroundColor Yellow
    foreach ($warning in $warnings) {
        Write-Host "  - $warning" -ForegroundColor Yellow
    }
    Write-Host ""
}

# If -Full flag, attempt to install missing components
if ($Full -and $errors.Count -gt 0) {
    Write-Host "Attempting automatic setup..." -ForegroundColor Cyan
    Write-Host ""

    if ($errors -contains "Claude Code CLI required - install with: npm install -g @anthropic-ai/claude-code") {
        Write-Host "Installing Claude Code..." -ForegroundColor Yellow
        npm install -g @anthropic-ai/claude-code
    }

    Write-Host ""
    Write-Host "Re-run this script to verify setup." -ForegroundColor White
}

Write-Host "========================================" -ForegroundColor Cyan

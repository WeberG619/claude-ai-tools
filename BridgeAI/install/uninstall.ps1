# BridgeAI Uninstaller

param(
    [string]$InstallPath = "C:\BridgeAI",
    [switch]$KeepData
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "     BridgeAI Uninstaller" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

# Confirm
$response = Read-Host "Are you sure you want to uninstall BridgeAI? (y/n)"
if ($response -ne 'y') {
    Write-Host "Cancelled." -ForegroundColor Gray
    exit 0
}

# Remove desktop shortcut
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "BridgeAI.lnk"
if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath -Force
    Write-Host "[OK] Removed desktop shortcut" -ForegroundColor Green
}

# Remove installation folder
if (Test-Path $InstallPath) {
    if ($KeepData) {
        # Keep the data folder
        Get-ChildItem $InstallPath -Exclude "data" | Remove-Item -Recurse -Force
        Write-Host "[OK] Removed BridgeAI (kept data folder)" -ForegroundColor Green
    } else {
        Remove-Item $InstallPath -Recurse -Force
        Write-Host "[OK] Removed BridgeAI completely" -ForegroundColor Green
    }
}

# Note about Claude Code
Write-Host ""
Write-Host "Note: Claude Code CLI was not removed." -ForegroundColor Gray
Write-Host "To remove it: npm uninstall -g @anthropic-ai/claude-code" -ForegroundColor Gray
Write-Host ""

Write-Host "BridgeAI has been uninstalled." -ForegroundColor Yellow
Write-Host ""

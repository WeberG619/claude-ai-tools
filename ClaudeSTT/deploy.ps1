param(
    [string]$RevitVersion = "2024",
    [switch]$Force
)

Write-Host "Deploying Claude STT to Revit $RevitVersion" -ForegroundColor Cyan

$ErrorActionPreference = "Stop"

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildPath = Join-Path $scriptPath "build" $RevitVersion
$addinPath = Join-Path $env:APPDATA "Autodesk\Revit\Addins\$RevitVersion"

if (-not (Test-Path $buildPath)) {
    Write-Host "Build not found. Running build script..." -ForegroundColor Yellow
    & (Join-Path $scriptPath "build.ps1") -RevitVersion $RevitVersion
}

if (-not (Test-Path $addinPath)) {
    New-Item -ItemType Directory -Path $addinPath -Force | Out-Null
}

$targetPath = Join-Path $addinPath "ClaudeSTT"
if (Test-Path $targetPath) {
    if ($Force) {
        Write-Host "Removing existing installation..." -ForegroundColor Yellow
        Remove-Item -Path $targetPath -Recurse -Force
    }
    else {
        Write-Host "ClaudeSTT already installed. Use -Force to overwrite." -ForegroundColor Red
        exit 1
    }
}

Write-Host "`nCopying files to Revit addins folder..." -ForegroundColor Yellow

Copy-Item -Path $buildPath -Destination $targetPath -Recurse

Copy-Item -Path (Join-Path $buildPath "ClaudeSTT.addin") -Destination $addinPath -Force

$processes = Get-Process | Where-Object { $_.ProcessName -eq "Revit" }
if ($processes.Count -gt 0) {
    Write-Host "`nWARNING: Revit is currently running. Please restart Revit to load the addon." -ForegroundColor Yellow
}

Write-Host "`nDeployment completed successfully!" -ForegroundColor Green
Write-Host "`nClaudeSTT has been installed to:" -ForegroundColor Cyan
Write-Host $targetPath -ForegroundColor White
Write-Host "`nStart Revit and look for the 'Claude Voice' tab" -ForegroundColor Cyan
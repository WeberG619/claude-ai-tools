param(
    [string]$Configuration = "Release",
    [string]$RevitVersion = "2024"
)

Write-Host "Building Claude STT for Revit $RevitVersion" -ForegroundColor Cyan

$ErrorActionPreference = "Stop"

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $scriptPath "python"
$csharpPath = Join-Path $scriptPath "csharp"
$outputPath = Join-Path $scriptPath "build" $RevitVersion

if (Test-Path $outputPath) {
    Remove-Item -Path $outputPath -Recurse -Force
}

New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $outputPath "python") -Force | Out-Null

Write-Host "`nInstalling Python dependencies..." -ForegroundColor Yellow
Push-Location $pythonPath
try {
    & python -m pip install -r requirements.txt --quiet
    if ($LASTEXITCODE -ne 0) { throw "Failed to install Python dependencies" }
}
finally {
    Pop-Location
}

Write-Host "`nBuilding C# components..." -ForegroundColor Yellow
Push-Location $csharpPath
try {
    $revitApiPath = "C:\Program Files\Autodesk\Revit $RevitVersion"
    if (-not (Test-Path $revitApiPath)) {
        throw "Revit $RevitVersion not found at $revitApiPath"
    }
    
    & msbuild ClaudeSTT.sln /p:Configuration=$Configuration /p:ReferencePath="$revitApiPath" /p:Platform="Any CPU" /v:minimal
    if ($LASTEXITCODE -ne 0) { throw "Build failed" }
}
finally {
    Pop-Location
}

Write-Host "`nCopying files to output..." -ForegroundColor Yellow

Copy-Item -Path (Join-Path $csharpPath "src\ClaudeSTT.Revit\bin\$Configuration\ClaudeSTT.Revit.dll") -Destination $outputPath
Copy-Item -Path (Join-Path $csharpPath "src\ClaudeSTT.Core\bin\$Configuration\ClaudeSTT.Core.dll") -Destination $outputPath
Copy-Item -Path (Join-Path $csharpPath "src\ClaudeSTT.Revit\bin\$Configuration\Newtonsoft.Json.dll") -Destination $outputPath

$addinContent = Get-Content (Join-Path $csharpPath "src\ClaudeSTT.Revit\ClaudeSTT.addin")
$addinContent = $addinContent -replace '<Assembly>ClaudeSTT.Revit.dll</Assembly>', "<Assembly>$outputPath\ClaudeSTT.Revit.dll</Assembly>"
$addinContent | Set-Content (Join-Path $outputPath "ClaudeSTT.addin")

Copy-Item -Path (Join-Path $pythonPath "*") -Destination (Join-Path $outputPath "python") -Recurse -Exclude @("__pycache__", "*.pyc", ".git")

Write-Host "`nBuild completed successfully!" -ForegroundColor Green
Write-Host "`nOutput location: $outputPath" -ForegroundColor Cyan
Write-Host "`nTo install:" -ForegroundColor Yellow
Write-Host "1. Copy all files from $outputPath to %APPDATA%\Autodesk\Revit\Addins\$RevitVersion\" -ForegroundColor White
Write-Host "2. Restart Revit" -ForegroundColor White
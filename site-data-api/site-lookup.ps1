# Site Data Lookup - PowerShell Wrapper
# Usage: .\site-lookup.ps1 "123 Main St, Miami, FL 33130"

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Address
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "site_data.py"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   SITE DATA LOOKUP" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

python $pythonScript $Address

# Check if JSON was created
$jsonFile = Join-Path (Get-Location) "site_data_result.json"
if (Test-Path $jsonFile) {
    Write-Host "`nJSON output available at: $jsonFile" -ForegroundColor Green
}

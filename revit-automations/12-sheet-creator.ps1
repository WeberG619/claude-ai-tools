# Sheet Creator
# Creates new sheets with specified numbers and names
# Usage: .\12-sheet-creator.ps1 -Version 2026|2025 -SheetNumber "A1.0" -SheetName "FLOOR PLAN" [-DryRun]
# Or batch: .\12-sheet-creator.ps1 -Version 2026|2025 -JsonFile "sheets.json" [-DryRun]

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("2025", "2026")]
    [string]$Version,

    [string]$SheetNumber = "",
    [string]$SheetName = "",
    [string]$JsonFile = "",
    [switch]$DryRun
)

$pipeName = "RevitMCPBridge$Version"

function Invoke-RevitMCP {
    param([string]$Method, [hashtable]$Params = @{})

    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    $pipe.Connect(10000)
    $writer = New-Object System.IO.StreamWriter($pipe)
    $reader = New-Object System.IO.StreamReader($pipe)
    $writer.AutoFlush = $true

    $request = @{ method = $Method; params = $Params } | ConvertTo-Json -Compress
    $writer.WriteLine($request)
    $response = $reader.ReadLine() | ConvertFrom-Json
    $pipe.Close()

    return $response
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "SHEET CREATOR - Revit $Version" -ForegroundColor Cyan
if ($DryRun) { Write-Host "[DRY RUN MODE]" -ForegroundColor Yellow }
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Build list of sheets to create
$sheetsToCreate = @()

if ($JsonFile) {
    if (-not (Test-Path $JsonFile)) {
        Write-Host "ERROR: JSON file not found: $JsonFile" -ForegroundColor Red
        exit 1
    }
    $data = Get-Content $JsonFile | ConvertFrom-Json
    foreach ($sheet in $data.sheets) {
        $sheetsToCreate += @{
            number = $sheet.sheetNumber
            name = $sheet.sheetName
        }
    }
    Write-Host "Loaded $($sheetsToCreate.Count) sheets from JSON" -ForegroundColor Gray
} elseif ($SheetNumber -and $SheetName) {
    $sheetsToCreate += @{
        number = $SheetNumber
        name = $SheetName
    }
} else {
    Write-Host "ERROR: Provide either -SheetNumber/-SheetName or -JsonFile" -ForegroundColor Red
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Gray
    Write-Host '  .\12-sheet-creator.ps1 -Version 2026 -SheetNumber "A1.0" -SheetName "FLOOR PLAN"'
    Write-Host '  .\12-sheet-creator.ps1 -Version 2026 -JsonFile "new-sheets.json"'
    Write-Host ""
    Write-Host "JSON format:" -ForegroundColor Gray
    Write-Host '  { "sheets": [{ "sheetNumber": "A1.0", "sheetName": "FLOOR PLAN" }] }'
    exit 1
}

# Get existing sheets to check for conflicts
$existingResponse = Invoke-RevitMCP -Method "getSheets"
$existingNumbers = @{}
if ($existingResponse.success) {
    foreach ($s in $existingResponse.result.sheets) {
        $existingNumbers[$s.sheetNumber] = $true
    }
}

Write-Host "SHEETS TO CREATE" -ForegroundColor Yellow
Write-Host "-" * 50

$created = 0
$skipped = 0

foreach ($sheet in $sheetsToCreate) {
    $num = $sheet.number
    $name = $sheet.name

    if ($existingNumbers.ContainsKey($num)) {
        Write-Host "  SKIP: $num already exists" -ForegroundColor Yellow
        $skipped++
        continue
    }

    if ($DryRun) {
        Write-Host "  [DRY] Would create: $num - $name" -ForegroundColor Cyan
        $created++
    } else {
        $result = Invoke-RevitMCP -Method "createSheet" -Params @{
            sheetNumber = $num
            sheetName = $name
        }

        if ($result.success) {
            Write-Host "  OK: Created $num - $name" -ForegroundColor Green
            $created++
        } else {
            Write-Host "  FAIL: $num - $($result.error)" -ForegroundColor Red
        }
    }
}

Write-Host ""
Write-Host "-" * 50
Write-Host "SUMMARY" -ForegroundColor Yellow
Write-Host "  Created: $created" -ForegroundColor Green
Write-Host "  Skipped: $skipped" -ForegroundColor $(if ($skipped -gt 0) { "Yellow" } else { "Green" })

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan

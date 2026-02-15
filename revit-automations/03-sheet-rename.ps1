# Sheet Rename Batch Tool
# Rename multiple sheets from a JSON mapping file
# Usage: .\03-sheet-rename.ps1 -Version 2026|2025 -MappingFile path.json [-DryRun]

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("2025", "2026")]
    [string]$Version,

    [Parameter(Mandatory=$true)]
    [string]$MappingFile,

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
Write-Host "SHEET RENAME BATCH - Revit $Version" -ForegroundColor Cyan
if ($DryRun) { Write-Host "[DRY RUN MODE - No changes will be made]" -ForegroundColor Yellow }
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Load mapping file
if (-not (Test-Path $MappingFile)) {
    Write-Host "ERROR: Mapping file not found: $MappingFile" -ForegroundColor Red
    Write-Host ""
    Write-Host "Mapping file format (JSON):" -ForegroundColor Gray
    Write-Host '{
  "renames": [
    { "sheetNumber": "A1.0.1", "newName": "FLOOR PLAN - AREA A" },
    { "sheetNumber": "A1.0.2", "newName": "FLOOR PLAN - AREA B" }
  ]
}' -ForegroundColor Gray
    exit 1
}

$mapping = Get-Content $MappingFile -Raw | ConvertFrom-Json
$renames = $mapping.renames

Write-Host "Loaded $($renames.Count) rename operations from mapping file" -ForegroundColor White
Write-Host ""

# Get current sheets
$sheetsResponse = Invoke-RevitMCP -Method "getSheets"
if (-not $sheetsResponse.success) {
    Write-Host "ERROR: Failed to get sheets" -ForegroundColor Red
    exit 1
}

$sheets = $sheetsResponse.result.sheets
$sheetLookup = @{}
foreach ($sheet in $sheets) {
    $sheetLookup[$sheet.sheetNumber] = $sheet
}

# Process renames
$successCount = 0
$skipCount = 0
$errorCount = 0

foreach ($rename in $renames) {
    $sheetNum = $rename.sheetNumber
    $newName = $rename.newName

    if (-not $sheetLookup.ContainsKey($sheetNum)) {
        Write-Host "  SKIP: Sheet $sheetNum not found" -ForegroundColor Yellow
        $skipCount++
        continue
    }

    $sheet = $sheetLookup[$sheetNum]
    $currentName = $sheet.sheetName

    if ($currentName -eq $newName) {
        Write-Host "  SKIP: $sheetNum already named '$newName'" -ForegroundColor Gray
        $skipCount++
        continue
    }

    Write-Host "  $sheetNum : '$currentName' -> '$newName'" -ForegroundColor White

    if (-not $DryRun) {
        # Use setParameter to change sheet name
        $result = Invoke-RevitMCP -Method "setParameter" -Params @{
            elementId = $sheet.id
            parameterName = "Sheet Name"
            value = $newName
        }

        if ($result.success) {
            Write-Host "    OK" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "    FAILED: $($result.error)" -ForegroundColor Red
            $errorCount++
        }

        # Small delay between operations (from gotchas)
        Start-Sleep -Milliseconds 300
    } else {
        Write-Host "    [Would rename]" -ForegroundColor Cyan
        $successCount++
    }
}

Write-Host ""
Write-Host "-" * 40
Write-Host "SUMMARY" -ForegroundColor Yellow
Write-Host "  Renamed:  $successCount" -ForegroundColor Green
Write-Host "  Skipped:  $skipCount" -ForegroundColor Yellow
Write-Host "  Errors:   $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { "Red" } else { "Green" })

if ($DryRun) {
    Write-Host ""
    Write-Host "This was a dry run. Run without -DryRun to apply changes." -ForegroundColor Cyan
}

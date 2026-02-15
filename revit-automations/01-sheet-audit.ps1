# Sheet Audit Tool
# Analyzes sheets in a Revit project and generates a status report
# Usage: .\01-sheet-audit.ps1 -Version 2026|2025

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("2025", "2026")]
    [string]$Version
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

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "SHEET AUDIT REPORT - Revit $Version" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Get document info
$docInfo = Invoke-RevitMCP -Method "getDocumentInfo"
if ($docInfo.success) {
    Write-Host "Project: $($docInfo.result.title)" -ForegroundColor White
    Write-Host "Path: $($docInfo.result.pathName)" -ForegroundColor Gray
    Write-Host ""
}

# Get all sheets
$sheetsResponse = Invoke-RevitMCP -Method "getSheets"
if (-not $sheetsResponse.success) {
    Write-Host "ERROR: Failed to get sheets" -ForegroundColor Red
    exit 1
}

$sheets = $sheetsResponse.result.sheets
$totalSheets = $sheetsResponse.result.totalSheets

# Categorize sheets
$emptySheets = @()
$genericNameSheets = @()
$populatedSheets = @()
$mepSheets = @()

foreach ($sheet in $sheets) {
    $isEmpty = $sheet.viewCount -eq 0
    $isGenericName = $sheet.sheetName -eq "Sheet" -or $sheet.sheetName -match "^Sheet\s*\d*$"
    $isMEP = $sheet.sheetNumber -match "^[MEP]-"

    if ($isEmpty) {
        $emptySheets += $sheet
    } else {
        $populatedSheets += $sheet
    }

    if ($isGenericName) {
        $genericNameSheets += $sheet
    }

    if ($isMEP) {
        $mepSheets += $sheet
    }
}

# Summary
Write-Host "SUMMARY" -ForegroundColor Yellow
Write-Host "-" * 40
Write-Host "Total Sheets:        $totalSheets"
Write-Host "With Content:        $($populatedSheets.Count)" -ForegroundColor Green
Write-Host "Empty (no views):    $($emptySheets.Count)" -ForegroundColor $(if ($emptySheets.Count -gt 0) { "Yellow" } else { "Green" })
Write-Host "Generic Names:       $($genericNameSheets.Count)" -ForegroundColor $(if ($genericNameSheets.Count -gt 0) { "Yellow" } else { "Green" })
Write-Host "MEP Placeholder:     $($mepSheets.Count)" -ForegroundColor Gray
Write-Host ""

# Empty Sheets Detail
if ($emptySheets.Count -gt 0) {
    Write-Host "EMPTY SHEETS (No Viewports)" -ForegroundColor Yellow
    Write-Host "-" * 40
    foreach ($sheet in $emptySheets | Sort-Object sheetNumber) {
        $nameStatus = if ($sheet.sheetName -eq "Sheet") { "[GENERIC]" } else { "" }
        Write-Host "  $($sheet.sheetNumber.PadRight(10)) $($sheet.sheetName) $nameStatus" -ForegroundColor Gray
    }
    Write-Host ""
}

# Generic Name Sheets Detail
$genericNotEmpty = $genericNameSheets | Where-Object { $_.viewCount -gt 0 }
if ($genericNotEmpty.Count -gt 0) {
    Write-Host "SHEETS WITH GENERIC NAMES (Have Content)" -ForegroundColor Yellow
    Write-Host "-" * 40
    foreach ($sheet in $genericNotEmpty | Sort-Object sheetNumber) {
        Write-Host "  $($sheet.sheetNumber.PadRight(10)) $($sheet.sheetName) ($($sheet.viewCount) views)" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Populated Sheets
Write-Host "POPULATED SHEETS" -ForegroundColor Green
Write-Host "-" * 40
foreach ($sheet in $populatedSheets | Sort-Object sheetNumber) {
    Write-Host "  $($sheet.sheetNumber.PadRight(10)) $($sheet.sheetName) ($($sheet.viewCount) views)" -ForegroundColor White
}
Write-Host ""

# Output JSON for programmatic use
$report = @{
    version = $Version
    project = $docInfo.result.title
    timestamp = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    summary = @{
        total = $totalSheets
        populated = $populatedSheets.Count
        empty = $emptySheets.Count
        genericNames = $genericNameSheets.Count
    }
    emptySheets = $emptySheets | ForEach-Object { @{ number = $_.sheetNumber; name = $_.sheetName; id = $_.id } }
    genericNameSheets = $genericNameSheets | ForEach-Object { @{ number = $_.sheetNumber; name = $_.sheetName; id = $_.id; viewCount = $_.viewCount } }
}

$jsonPath = "D:\_CLAUDE-TOOLS\revit-automations\last-audit-$Version.json"
$report | ConvertTo-Json -Depth 5 | Out-File $jsonPath -Encoding UTF8
Write-Host "Report saved to: $jsonPath" -ForegroundColor Cyan

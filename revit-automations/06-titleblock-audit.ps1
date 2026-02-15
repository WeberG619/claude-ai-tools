# Titleblock Audit
# Shows which titleblocks are used and by how many sheets
# Usage: .\06-titleblock-audit.ps1 -Version 2026|2025

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

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "TITLEBLOCK AUDIT - Revit $Version" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Get sheets to find titleblock info
$sheetsResponse = Invoke-RevitMCP -Method "getSheets"
if (-not $sheetsResponse.success) {
    Write-Host "ERROR: Failed to get sheets" -ForegroundColor Red
    exit 1
}

$sheets = $sheetsResponse.result.sheets

# Get titleblock elements for count
$tbResponse = Invoke-RevitMCP -Method "getElements" -Params @{ category = "TitleBlocks" }
$titleblockCount = if ($tbResponse.success -and $tbResponse.result.elements) {
    $tbResponse.result.elements.Count
} else {
    $sheets.Count
}

# Group sheets by titleblock type if available
$byFamily = @{}
foreach ($sheet in $sheets) {
    # Try to get titleblock type from sheet - fall back to "Standard" if not available
    $family = if ($sheet.titleblockType) { $sheet.titleblockType } else { "Standard Titleblock" }
    if (-not $byFamily.ContainsKey($family)) {
        $byFamily[$family] = @{
            count = 0
            sheets = @()
        }
    }
    $byFamily[$family].count++
    $byFamily[$family].sheets += $sheet.sheetNumber
}

Write-Host "TITLEBLOCK FAMILIES" -ForegroundColor Yellow
Write-Host "-" * 50

foreach ($family in $byFamily.Keys | Sort-Object) {
    $info = $byFamily[$family]
    Write-Host ""
    Write-Host "$family" -ForegroundColor Cyan
    Write-Host "  Used on: $($info.count) sheets" -ForegroundColor White
}

Write-Host ""
Write-Host "-" * 50

# Recommend primary titleblock
$primary = $byFamily.GetEnumerator() | Sort-Object { $_.Value.count } -Descending | Select-Object -First 1
if ($primary) {
    Write-Host ""
    Write-Host "RECOMMENDATION" -ForegroundColor Yellow
    Write-Host "  Primary titleblock: $($primary.Key)" -ForegroundColor Green
    Write-Host "  Used on $($primary.Value.count) of $($sheets.Count) sheets" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan

# Unplaced Views Finder
# Lists views that are not placed on any sheet
# Usage: .\05-unplaced-views.ps1 -Version 2026|2025 [-ViewType FloorPlan|Legend|etc]

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("2025", "2026")]
    [string]$Version,

    [string]$ViewType = ""
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
Write-Host "UNPLACED VIEWS FINDER - Revit $Version" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Get all sheets and collect placed view IDs
$sheetsResponse = Invoke-RevitMCP -Method "getSheets"
if (-not $sheetsResponse.success) {
    Write-Host "ERROR: Failed to get sheets" -ForegroundColor Red
    exit 1
}

$placedViewIds = @{}
foreach ($sheet in $sheetsResponse.result.sheets) {
    foreach ($viewId in $sheet.placedViews) {
        $placedViewIds[$viewId] = $sheet.sheetNumber
    }
}

Write-Host "Found $($placedViewIds.Count) views placed on sheets" -ForegroundColor Gray
Write-Host ""

# Get all views
$viewsResponse = Invoke-RevitMCP -Method "getViews"
if (-not $viewsResponse.success) {
    Write-Host "ERROR: Failed to get views" -ForegroundColor Red
    exit 1
}

$views = $viewsResponse.result.views

# Filter views - exclude browser views and sheets themselves
$placeableTypes = @('FloorPlan', 'CeilingPlan', 'Elevation', 'Section', 'ThreeD', 'DraftingView', 'Legend', 'Detail', 'AreaPlan')
$excludeTypes = @('ProjectBrowser', 'SystemBrowser', 'DrawingSheet', 'Schedule', 'Internal')

$unplacedViews = @()
foreach ($view in $views) {
    # Skip if placed
    if ($placedViewIds.ContainsKey($view.id)) { continue }

    # Skip excluded types
    if ($view.viewType -in $excludeTypes) { continue }

    # Filter by type if specified
    if ($ViewType -and $view.viewType -ne $ViewType) { continue }

    $unplacedViews += $view
}

# Group by type
$byType = @{}
foreach ($view in $unplacedViews) {
    $type = if ($view.viewType) { $view.viewType } else { "Unknown" }
    if (-not $byType.ContainsKey($type)) { $byType[$type] = @() }
    $byType[$type] += $view
}

Write-Host "UNPLACED VIEWS ($($unplacedViews.Count) total)" -ForegroundColor Yellow
Write-Host "-" * 50

if ($ViewType) {
    Write-Host "Filtered by type: $ViewType" -ForegroundColor Gray
    Write-Host ""
}

foreach ($type in $byType.Keys | Sort-Object) {
    $typeViews = $byType[$type]
    Write-Host ""
    Write-Host "$type ($($typeViews.Count))" -ForegroundColor Cyan
    foreach ($v in $typeViews | Sort-Object name) {
        Write-Host "  ID: $($v.id.ToString().PadRight(10)) $($v.name)" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Placeable types: $($placeableTypes -join ', ')" -ForegroundColor Gray

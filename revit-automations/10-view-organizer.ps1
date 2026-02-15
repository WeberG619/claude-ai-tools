# View Organizer
# Lists views grouped by type with placement status
# Usage: .\10-view-organizer.ps1 -Version 2026|2025 [-Type FloorPlan|Section|etc]

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("2025", "2026")]
    [string]$Version,

    [string]$Type = ""
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
Write-Host "VIEW ORGANIZER - Revit $Version" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Get sheets to find placed views
$sheetsResponse = Invoke-RevitMCP -Method "getSheets"
$placedViewIds = @{}
if ($sheetsResponse.success) {
    foreach ($sheet in $sheetsResponse.result.sheets) {
        foreach ($viewId in $sheet.placedViews) {
            $placedViewIds[$viewId] = $sheet.sheetNumber
        }
    }
}
Write-Host "Found $($placedViewIds.Count) views placed on sheets" -ForegroundColor Gray

# Get all views
$viewsResponse = Invoke-RevitMCP -Method "getViews"
if (-not $viewsResponse.success) {
    Write-Host "ERROR: Failed to get views" -ForegroundColor Red
    exit 1
}

$views = $viewsResponse.result.views
if (-not $views) { $views = $viewsResponse.result }

# Filter and group
$excludeTypes = @('ProjectBrowser', 'SystemBrowser', 'DrawingSheet', 'Internal')
$byType = @{}

foreach ($view in $views) {
    $viewType = if ($view.viewType) { $view.viewType } else { "Unknown" }

    # Skip excluded types
    if ($viewType -in $excludeTypes) { continue }

    # Filter by type if specified
    if ($Type -and $viewType -ne $Type) { continue }

    if (-not $byType.ContainsKey($viewType)) {
        $byType[$viewType] = @{
            placed = @()
            unplaced = @()
        }
    }

    if ($placedViewIds.ContainsKey($view.id)) {
        $byType[$viewType].placed += @{
            view = $view
            sheet = $placedViewIds[$view.id]
        }
    } else {
        $byType[$viewType].unplaced += $view
    }
}

Write-Host ""
Write-Host "VIEW SUMMARY" -ForegroundColor Yellow
Write-Host "-" * 50

$totalPlaced = 0
$totalUnplaced = 0

foreach ($viewType in $byType.Keys | Sort-Object) {
    $data = $byType[$viewType]
    $placedCount = $data.placed.Count
    $unplacedCount = $data.unplaced.Count
    $total = $placedCount + $unplacedCount
    $totalPlaced += $placedCount
    $totalUnplaced += $unplacedCount

    $status = if ($unplacedCount -eq 0) { "Green" } elseif ($placedCount -eq 0) { "Red" } else { "Yellow" }

    Write-Host ""
    Write-Host "$viewType ($total total)" -ForegroundColor Cyan
    Write-Host "  Placed:   $placedCount" -ForegroundColor Green
    Write-Host "  Unplaced: $unplacedCount" -ForegroundColor $(if ($unplacedCount -gt 0) { "Yellow" } else { "Green" })

    # Show first few unplaced views
    if ($unplacedCount -gt 0 -and $unplacedCount -le 5) {
        foreach ($v in $data.unplaced) {
            Write-Host "    - $($v.name) (ID: $($v.id))" -ForegroundColor Gray
        }
    } elseif ($unplacedCount -gt 5) {
        foreach ($v in $data.unplaced | Select-Object -First 3) {
            Write-Host "    - $($v.name) (ID: $($v.id))" -ForegroundColor Gray
        }
        Write-Host "    ... and $($unplacedCount - 3) more" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "-" * 50
Write-Host "TOTAL VIEWS" -ForegroundColor Yellow
Write-Host "  Placed:   $totalPlaced" -ForegroundColor Green
Write-Host "  Unplaced: $totalUnplaced" -ForegroundColor $(if ($totalUnplaced -gt 0) { "Yellow" } else { "Green" })

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan

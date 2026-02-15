# Level Information
# Shows all levels with elevations and associated views
# Usage: .\13-level-info.ps1 -Version 2026|2025

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
Write-Host "LEVEL INFORMATION - Revit $Version" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Get levels
$levelsResponse = Invoke-RevitMCP -Method "getLevels"
if (-not $levelsResponse.success -and -not $levelsResponse.levels) {
    Write-Host "ERROR: Failed to get levels" -ForegroundColor Red
    exit 1
}

$levels = if ($levelsResponse.levels) { $levelsResponse.levels } else { $levelsResponse.result.levels }

# Get views to associate with levels
$viewsResponse = Invoke-RevitMCP -Method "getViews"
$viewsByLevel = @{}
if ($viewsResponse.success) {
    $views = if ($viewsResponse.result.views) { $viewsResponse.result.views } else { $viewsResponse.result }
    foreach ($view in $views) {
        if ($view.level) {
            if (-not $viewsByLevel.ContainsKey($view.level)) {
                $viewsByLevel[$view.level] = @()
            }
            $viewsByLevel[$view.level] += $view
        }
    }
}

Write-Host "PROJECT LEVELS" -ForegroundColor Yellow
Write-Host "-" * 50
Write-Host ""

# Sort by elevation
$sortedLevels = $levels | Sort-Object elevation -Descending

foreach ($level in $sortedLevels) {
    $name = $level.name
    $elev = if ($level.elevation -ne $null) { "{0:N2} ft" -f $level.elevation } else { "N/A" }
    $id = $level.id

    Write-Host "$name" -ForegroundColor Cyan
    Write-Host "  Elevation: $elev" -ForegroundColor White
    Write-Host "  ID: $id" -ForegroundColor Gray

    # Show associated views
    if ($viewsByLevel.ContainsKey($name)) {
        $levelViews = $viewsByLevel[$name]
        $floorPlans = $levelViews | Where-Object { $_.viewType -eq "FloorPlan" }
        $ceilingPlans = $levelViews | Where-Object { $_.viewType -eq "CeilingPlan" }

        if ($floorPlans.Count -gt 0) {
            Write-Host "  Floor Plans: $($floorPlans.Count)" -ForegroundColor Gray
        }
        if ($ceilingPlans.Count -gt 0) {
            Write-Host "  Ceiling Plans: $($ceilingPlans.Count)" -ForegroundColor Gray
        }
    }
    Write-Host ""
}

Write-Host "-" * 50
Write-Host "Total Levels: $($levels.Count)" -ForegroundColor Yellow

# Calculate floor-to-floor heights
if ($sortedLevels.Count -gt 1) {
    Write-Host ""
    Write-Host "FLOOR-TO-FLOOR HEIGHTS" -ForegroundColor Yellow
    Write-Host "-" * 50

    for ($i = 0; $i -lt $sortedLevels.Count - 1; $i++) {
        $upper = $sortedLevels[$i]
        $lower = $sortedLevels[$i + 1]
        if ($upper.elevation -ne $null -and $lower.elevation -ne $null) {
            $height = $upper.elevation - $lower.elevation
            Write-Host "  $($lower.name) to $($upper.name): $("{0:N2}" -f $height) ft ($("{0:N0}" -f ($height * 12)) in)" -ForegroundColor White
        }
    }
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan

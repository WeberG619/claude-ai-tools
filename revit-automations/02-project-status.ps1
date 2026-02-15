# Project Status Dashboard
# Quick health check showing sheets, views, and project metrics
# Usage: .\02-project-status.ps1 -Version 2026|2025

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
Write-Host "PROJECT STATUS DASHBOARD - Revit $Version" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Get document info
$docInfo = Invoke-RevitMCP -Method "getDocumentInfo"
if ($docInfo.success) {
    Write-Host "PROJECT INFO" -ForegroundColor Yellow
    Write-Host "-" * 40
    Write-Host "  Name:     $($docInfo.title)" -ForegroundColor White
    Write-Host "  Number:   $($docInfo.projectInfo.number)" -ForegroundColor White
    Write-Host "  Client:   $($docInfo.projectInfo.name)" -ForegroundColor White
    Write-Host "  Path:     $($docInfo.pathName)" -ForegroundColor Gray
    Write-Host ""
}

# Get levels
$levelsResponse = Invoke-RevitMCP -Method "getLevels"
if ($levelsResponse.success) {
    $levels = $levelsResponse.levels
    Write-Host "LEVELS ($($levelsResponse.levelCount))" -ForegroundColor Yellow
    Write-Host "-" * 40
    foreach ($level in $levels | Sort-Object elevation) {
        $elevStr = "{0:N2}" -f $level.elevation
        Write-Host "  $($level.name.PadRight(25)) Elev: $elevStr ft" -ForegroundColor White
    }
    Write-Host ""
}

# Get sheets
$sheetsResponse = Invoke-RevitMCP -Method "getSheets"
if ($sheetsResponse.success) {
    $sheets = $sheetsResponse.result.sheets
    $populated = ($sheets | Where-Object { $_.viewCount -gt 0 }).Count
    $empty = ($sheets | Where-Object { $_.viewCount -eq 0 }).Count

    Write-Host "SHEETS ($($sheets.Count) total)" -ForegroundColor Yellow
    Write-Host "-" * 40
    Write-Host "  Populated:  $populated" -ForegroundColor Green
    Write-Host "  Empty:      $empty" -ForegroundColor $(if ($empty -gt 0) { "Yellow" } else { "Green" })

    # Group by series
    $series = @{}
    foreach ($sheet in $sheets) {
        $prefix = if ($sheet.sheetNumber -match "^([A-Z]+)") { $matches[1] } else { "Other" }
        if (-not $series.ContainsKey($prefix)) { $series[$prefix] = 0 }
        $series[$prefix]++
    }

    Write-Host ""
    Write-Host "  By Series:" -ForegroundColor Gray
    foreach ($s in $series.GetEnumerator() | Sort-Object Name) {
        Write-Host "    $($s.Name): $($s.Value) sheets" -ForegroundColor White
    }
    Write-Host ""
}

# Get views summary
$viewsResponse = Invoke-RevitMCP -Method "getViews"
if ($viewsResponse.success) {
    $views = $viewsResponse.result

    # Categorize views
    $viewTypes = @{}
    foreach ($view in $views) {
        $type = if ($view.viewType) { $view.viewType } else { "Unknown" }
        if (-not $viewTypes.ContainsKey($type)) { $viewTypes[$type] = 0 }
        $viewTypes[$type]++
    }

    Write-Host "VIEWS ($($views.Count) total)" -ForegroundColor Yellow
    Write-Host "-" * 40
    foreach ($vt in $viewTypes.GetEnumerator() | Sort-Object Value -Descending) {
        Write-Host "  $($vt.Name.PadRight(20)) $($vt.Value)" -ForegroundColor White
    }
    Write-Host ""
}

# Get wall types
$wallTypesResponse = Invoke-RevitMCP -Method "getWallTypes"
if ($wallTypesResponse.success) {
    $wallTypes = $wallTypesResponse.wallTypes
    Write-Host "WALL TYPES ($($wallTypesResponse.wallTypeCount))" -ForegroundColor Yellow
    Write-Host "-" * 40
    $shown = 0
    foreach ($wt in $wallTypes | Select-Object -First 8) {
        Write-Host "  $($wt.name)" -ForegroundColor White
        $shown++
    }
    if ($wallTypes.Count -gt 8) {
        Write-Host "  ... and $($wallTypes.Count - 8) more" -ForegroundColor Gray
    }
    Write-Host ""
}

# Timestamp
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host "=" * 60 -ForegroundColor Cyan

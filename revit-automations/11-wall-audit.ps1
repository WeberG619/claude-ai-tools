# Wall Type Audit
# Lists all wall types with instance counts and usage
# Usage: .\11-wall-audit.ps1 -Version 2026|2025

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
Write-Host "WALL TYPE AUDIT - Revit $Version" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Get wall types
$typesResponse = Invoke-RevitMCP -Method "getWallTypes"
if (-not $typesResponse.success -and -not $typesResponse.wallTypes) {
    Write-Host "ERROR: Failed to get wall types" -ForegroundColor Red
    exit 1
}

$wallTypes = if ($typesResponse.wallTypes) { $typesResponse.wallTypes } else { $typesResponse.result.wallTypes }
Write-Host "Found $($wallTypes.Count) wall types" -ForegroundColor Gray

# Get wall instances
$wallsResponse = Invoke-RevitMCP -Method "getElements" -Params @{ category = "Walls" }
$walls = @()
if ($wallsResponse.success -and $wallsResponse.result.elements) {
    $walls = $wallsResponse.result.elements
}
Write-Host "Found $($walls.Count) wall instances" -ForegroundColor Gray
Write-Host ""

# Count instances per type
$typeUsage = @{}
foreach ($wall in $walls) {
    $typeName = if ($wall.typeName) { $wall.typeName } elseif ($wall.type) { $wall.type } else { "Unknown" }
    if (-not $typeUsage.ContainsKey($typeName)) {
        $typeUsage[$typeName] = 0
    }
    $typeUsage[$typeName]++
}

Write-Host "WALL TYPES BY USAGE" -ForegroundColor Yellow
Write-Host "-" * 50

# Sort by usage (most used first)
$sorted = $typeUsage.GetEnumerator() | Sort-Object Value -Descending

$usedTypes = @()
$unusedTypes = @()

foreach ($entry in $sorted) {
    if ($entry.Value -gt 0) {
        $usedTypes += $entry
    }
}

# Find unused types
foreach ($wt in $wallTypes) {
    $name = $wt.name
    if (-not $typeUsage.ContainsKey($name)) {
        $unusedTypes += $name
    }
}

Write-Host ""
Write-Host "USED WALL TYPES ($($usedTypes.Count))" -ForegroundColor Green
foreach ($entry in $usedTypes) {
    $count = $entry.Value.ToString().PadLeft(5)
    Write-Host "  $count x  $($entry.Key)" -ForegroundColor White
}

if ($unusedTypes.Count -gt 0) {
    Write-Host ""
    Write-Host "UNUSED WALL TYPES ($($unusedTypes.Count))" -ForegroundColor Yellow
    foreach ($name in $unusedTypes | Sort-Object) {
        Write-Host "      -  $name" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "-" * 50
Write-Host "SUMMARY" -ForegroundColor Yellow
Write-Host "  Total types:  $($wallTypes.Count)" -ForegroundColor White
Write-Host "  Used:         $($usedTypes.Count)" -ForegroundColor Green
Write-Host "  Unused:       $($unusedTypes.Count)" -ForegroundColor $(if ($unusedTypes.Count -gt 0) { "Yellow" } else { "Green" })
Write-Host "  Total walls:  $($walls.Count)" -ForegroundColor White

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan

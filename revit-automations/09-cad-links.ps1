# CAD Link Manager
# Lists all CAD links/imports in the project
# Usage: .\09-cad-links.ps1 -Version 2026|2025

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
Write-Host "CAD LINK MANAGER - Revit $Version" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Try multiple methods to get CAD imports
$cadImports = @()

# Method 1: getImportedCAD
$cadResponse = Invoke-RevitMCP -Method "getImportedCAD"
if ($cadResponse.success -or $cadResponse.cadImports) {
    if ($cadResponse.cadImports) {
        $cadImports = $cadResponse.cadImports
    } elseif ($cadResponse.result.cadImports) {
        $cadImports = $cadResponse.result.cadImports
    }
}

# Method 2: Try getCadLayers if first method returned nothing
if ($cadImports.Count -eq 0) {
    $layersResponse = Invoke-RevitMCP -Method "getCadLayers"
    if ($layersResponse.success -or $layersResponse.layers) {
        Write-Host "CAD LAYERS FOUND" -ForegroundColor Yellow
        Write-Host "-" * 50
        $layers = if ($layersResponse.layers) { $layersResponse.layers } else { $layersResponse.result.layers }
        if ($layers) {
            foreach ($layer in $layers | Select-Object -First 20) {
                Write-Host "  $layer" -ForegroundColor White
            }
            if ($layers.Count -gt 20) {
                Write-Host "  ... and $($layers.Count - 20) more layers" -ForegroundColor Gray
            }
        }
        Write-Host ""
    }
}

if ($cadImports.Count -gt 0) {
    Write-Host "CAD IMPORTS ($($cadImports.Count) found)" -ForegroundColor Yellow
    Write-Host "-" * 50

    foreach ($cad in $cadImports) {
        Write-Host ""
        $name = if ($cad.name) { $cad.name } else { "Unknown" }
        $id = if ($cad.id) { $cad.id } else { "N/A" }
        Write-Host "  $name" -ForegroundColor Cyan
        Write-Host "    ID: $id" -ForegroundColor Gray
        if ($cad.path) { Write-Host "    Path: $($cad.path)" -ForegroundColor Gray }
        if ($cad.viewId) { Write-Host "    View: $($cad.viewId)" -ForegroundColor Gray }
    }
} else {
    Write-Host "No CAD imports detected via API" -ForegroundColor Yellow
    Write-Host "Note: The project may have CAD links that require a different query method" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan

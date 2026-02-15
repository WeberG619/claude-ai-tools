# Family Instance Counter
# Counts family instances by category
# Usage: .\15-family-count.ps1 -Version 2026|2025

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
Write-Host "FAMILY INSTANCE COUNTER - Revit $Version" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Categories to count
$categories = @(
    "Walls",
    "Doors",
    "Windows",
    "Rooms",
    "Furniture",
    "Casework",
    "Plumbing Fixtures",
    "Lighting Fixtures",
    "Electrical Fixtures",
    "Generic Models",
    "Columns",
    "Floors",
    "Ceilings",
    "Roofs",
    "Stairs"
)

Write-Host "ELEMENT COUNTS BY CATEGORY" -ForegroundColor Yellow
Write-Host "-" * 50
Write-Host ""

$totalElements = 0
$results = @()

foreach ($category in $categories) {
    $response = Invoke-RevitMCP -Method "getElements" -Params @{ category = $category }

    $count = 0
    if ($response.success -and $response.result.elements) {
        $count = $response.result.elements.Count
    }

    if ($count -gt 0) {
        $totalElements += $count
        $results += @{
            Category = $category
            Count = $count
        }
    }
}

# Sort by count descending
$sorted = $results | Sort-Object { $_.Count } -Descending

foreach ($item in $sorted) {
    $countStr = $item.Count.ToString().PadLeft(6)
    Write-Host "  $countStr  $($item.Category)" -ForegroundColor White
}

# Show categories with zero elements
$zeroCategories = $categories | Where-Object {
    $cat = $_
    -not ($results | Where-Object { $_.Category -eq $cat })
}

if ($zeroCategories.Count -gt 0) {
    Write-Host ""
    Write-Host "Categories with no elements:" -ForegroundColor Gray
    Write-Host "  $($zeroCategories -join ', ')" -ForegroundColor Gray
}

Write-Host ""
Write-Host "-" * 50
Write-Host "TOTAL ELEMENTS: $totalElements" -ForegroundColor Green

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan

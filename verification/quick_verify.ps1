# Quick BIM Verification Script
# Usage: .\quick_verify.ps1 -Version 2025|2026 -Category "Walls"|"Doors"|"Windows"

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("2025", "2026")]
    [string]$Version = "2025",

    [Parameter(Mandatory=$false)]
    [string]$Category = "Walls",

    [Parameter(Mandatory=$false)]
    [int]$ExpectedCount = 0
)

$pipeName = "RevitMCPBridge$Version"

function Send-MCPRequest {
    param([string]$Json)

    try {
        $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
        $pipe.Connect(5000)

        $writer = New-Object System.IO.StreamWriter($pipe)
        $reader = New-Object System.IO.StreamReader($pipe)

        $writer.WriteLine($Json)
        $writer.Flush()

        $response = $reader.ReadLine()
        $pipe.Close()

        return $response | ConvertFrom-Json
    }
    catch {
        return @{ error = $_.Exception.Message }
    }
}

# Build query based on category
$method = switch ($Category) {
    "Walls" { "getWalls" }
    "Doors" { "getDoorTypes" }
    "Windows" { "getWindowTypes" }
    "Rooms" { "getRooms" }
    default { "getElements" }
}

$json = @{
    method = $method
    params = @{}
} | ConvertTo-Json -Compress

Write-Host "=== BIM Verification ===" -ForegroundColor Cyan
Write-Host "Revit Version: $Version"
Write-Host "Category: $Category"
Write-Host ""

$result = Send-MCPRequest -Json $json

if ($result.error) {
    Write-Host "ERROR: $($result.error)" -ForegroundColor Red
    exit 1
}

# Count elements
$count = 0
if ($result.$Category) {
    $count = $result.$Category.Count
} elseif ($result.walls) {
    $count = $result.walls.Count
} elseif ($result.rooms) {
    $count = $result.rooms.Count
}

Write-Host "Found: $count elements" -ForegroundColor Green

if ($ExpectedCount -gt 0) {
    if ($count -eq $ExpectedCount) {
        Write-Host "STATUS: PASSED (matches expected $ExpectedCount)" -ForegroundColor Green
    } else {
        $diff = $count - $ExpectedCount
        Write-Host "STATUS: WARNING (expected $ExpectedCount, diff: $diff)" -ForegroundColor Yellow
    }
}

# Output summary
@{
    status = if ($ExpectedCount -eq 0 -or $count -eq $ExpectedCount) { "PASSED" } else { "WARNING" }
    category = $Category
    found = $count
    expected = $ExpectedCount
    version = $Version
} | ConvertTo-Json

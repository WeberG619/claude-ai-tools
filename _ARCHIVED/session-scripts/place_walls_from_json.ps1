# Place Walls from JSON
# ====================
# Reads walls detected by dxf_to_revit_walls.py and places them in Revit
#
# Usage:
#   .\place_walls_from_json.ps1 -WallsJson "D:\detected_walls.json" -LevelId 368

param(
    [Parameter(Mandatory=$true)]
    [string]$WallsJson,

    [int]$LevelId = 368,

    [string]$PipeName = "RevitMCPBridge2025",

    [int]$Height = 10,

    [switch]$DryRun
)

# Wall Type Mapping
$WallTypeMap = @{
    4 = 26564      # Generic - 4"
    5 = 533588     # Generic - 5"
    6 = 1693       # Generic - 6"
    8 = 1698       # Generic - 8"
    9 = 790343     # Generic - 9"
    10 = 1214289   # Generic - 10"
    12 = 1219224   # Generic - 12"
}

function Get-WallTypeId {
    param([int]$ThicknessInches)

    if ($WallTypeMap.ContainsKey($ThicknessInches)) {
        return $WallTypeMap[$ThicknessInches]
    }

    # Find closest match
    $closest = $WallTypeMap.Keys | Sort-Object { [Math]::Abs($_ - $ThicknessInches) } | Select-Object -First 1
    return $WallTypeMap[$closest]
}

# Load walls from JSON
Write-Host "Loading walls from: $WallsJson" -ForegroundColor Cyan
$walls = Get-Content $WallsJson | ConvertFrom-Json

Write-Host "Loaded $($walls.Count) walls" -ForegroundColor Green

# Show summary
$thicknessDist = $walls | Group-Object thickness_in | Sort-Object Name
Write-Host "`nWall thickness distribution:"
foreach ($group in $thicknessDist) {
    Write-Host "  $($group.Name)`": $($group.Count) walls"
}

if ($DryRun) {
    Write-Host "`nDRY RUN - No walls will be placed" -ForegroundColor Yellow
    Write-Host "First 10 walls that would be placed:"
    foreach ($wall in $walls | Select-Object -First 10) {
        $typeId = Get-WallTypeId -ThicknessInches $wall.thickness_in
        Write-Host "  $($wall.type): ($($wall.start_point[0]), $($wall.start_point[1])) to ($($wall.end_point[0]), $($wall.end_point[1])) - $($wall.thickness_in)in (type $typeId)"
    }
    exit
}

# Connect to Revit
Write-Host "`nConnecting to Revit via $PipeName..." -ForegroundColor Cyan

try {
    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", $PipeName, [System.IO.Pipes.PipeDirection]::InOut)
    $pipe.Connect(5000)
    $reader = New-Object System.IO.StreamReader($pipe)
    $writer = New-Object System.IO.StreamWriter($pipe)
    $writer.AutoFlush = $true
    Write-Host "Connected!" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Could not connect to Revit. Is RevitMCPBridge running?" -ForegroundColor Red
    exit 1
}

# Place walls
$placed = 0
$failed = 0
$total = $walls.Count

Write-Host "`nPlacing $total walls..." -ForegroundColor Cyan

foreach ($wall in $walls) {
    $sx = $wall.start_point[0]
    $sy = $wall.start_point[1]
    $sz = 0
    $ex = $wall.end_point[0]
    $ey = $wall.end_point[1]
    $ez = 0

    $typeId = Get-WallTypeId -ThicknessInches $wall.thickness_in

    $json = @{
        method = "createWall"
        params = @{
            startPoint = @($sx, $sy, $sz)
            endPoint = @($ex, $ey, $ez)
            levelId = $LevelId
            wallTypeId = $typeId
            height = $Height
        }
    } | ConvertTo-Json -Compress

    try {
        $writer.WriteLine($json)
        Start-Sleep -Milliseconds 100
        $response = $reader.ReadLine()
        $result = $response | ConvertFrom-Json

        if ($result.success) {
            $placed++
            $pct = [math]::Round(($placed + $failed) / $total * 100)
            Write-Host "`r[$pct%] Placed: $placed, Failed: $failed" -NoNewline
        }
        else {
            $failed++
            # Uncomment to see errors:
            # Write-Host "Failed: $($result.error)" -ForegroundColor Red
        }
    }
    catch {
        $failed++
    }
}

$pipe.Close()

Write-Host "`n`n========================================" -ForegroundColor Cyan
Write-Host "COMPLETE" -ForegroundColor Green
Write-Host "  Placed: $placed walls"
Write-Host "  Failed: $failed walls"
Write-Host "  Total:  $total walls"
Write-Host "========================================" -ForegroundColor Cyan

# Avon Park Floor Plan - Designed for CORRECT Room Areas
# Working backwards from target areas to determine wall positions

function Send-MCPRequest {
    param([string]$method, [hashtable]$params)
    try {
        $pipeClient = New-Object System.IO.Pipes.NamedPipeClientStream(".", "RevitMCPBridge2026", [System.IO.Pipes.PipeDirection]::InOut)
        $pipeClient.Connect(5000)
        $reader = New-Object System.IO.StreamReader($pipeClient)
        $writer = New-Object System.IO.StreamWriter($pipeClient)
        $writer.AutoFlush = $true
        $request = @{ method = $method; params = $params } | ConvertTo-Json -Depth 10 -Compress
        $writer.WriteLine($request)
        $response = $reader.ReadLine()
        $pipeClient.Close()
        return $response | ConvertFrom-Json
    }
    catch { return @{ success = $false; error = $_.Exception.Message } }
}

Write-Host "======================================================="
Write-Host "AVON PARK FLOOR PLAN - AREA-CORRECT DESIGN"
Write-Host "======================================================="

# Clear existing walls
$walls = Send-MCPRequest -method "getWalls" -params @{}
if ($walls.wallCount -gt 0) {
    $ids = $walls.walls | ForEach-Object { $_.wallId }
    Send-MCPRequest -method "deleteElements" -params @{ elementIds = $ids } | Out-Null
    Write-Host "Cleared $($walls.wallCount) existing walls"
}

$levels = Send-MCPRequest -method "getLevels" -params @{}
$levelId = ($levels.levels | Where-Object { $_.elevation -eq 0 } | Select-Object -First 1).levelId

$ext = "Generic - 8`""
$int = "Generic - 4`""

# =====================================================
# DESIGN BASED ON REQUIRED AREAS
# =====================================================
# Target areas:
#   BEDROOM-3:      140 SF -> 11.67' x 12'
#   BEDROOM-2:      142 SF -> 11.83' x 12'
#   FAMILY/DINING:  244 SF -> 13' x 18.77'
#   LIVING:         210 SF -> 14' x 15'
#   MASTER BEDROOM: 221 SF -> 13' x 17'
#   MASTER BATH:    70 SF  -> 7' x 10'
#   BATH-2:         42 SF  -> 6' x 7'
#   BATH-3:         32 SF  -> 5' x 6.4'
#   KITCHEN:        200 SF -> 12.5' x 16'
#   LAUNDRY:        30 SF  -> 5' x 6'
#   HALL-1:         38 SF  -> 4' x 9.5'
#   CLOSET:         32 SF  -> 4' x 8'
#   2-CAR GARAGE:   543 SF -> 21' x 25.86'
#
# Total width: 55.79' (from PDF)
# Target under air: 1,991 SF (excluding garage)
#
# Layout calculation:
# If width = 55.79' and under air = 1,991 SF
# Average depth = 1991 / 55.79 = 35.7'
# Plus garage (543 SF) somewhere
# =====================================================

# ZONE WIDTHS (West to East):
$brWidth = 12          # Bedroom zone: 12' wide (bedrooms are ~12' deep stacked)
$centralWidth = 15     # Central zone: 15' wide (Family/Dining)
$livingWidth = 13      # Living/Master zone: 13' wide
$garageWidth = 15.79   # Garage zone: 15.79' wide (55.79 - 12 - 15 - 13)

# X coordinates
$x0 = 0
$x1 = $brWidth                                    # 12
$x2 = $brWidth + $centralWidth                    # 27
$x3 = $brWidth + $centralWidth + $livingWidth     # 40
$x4 = 55.79                                       # 55.79

# ZONE DEPTHS (South to North):
# Building depth to accommodate all rooms
# For bedrooms: 140+142 = 282 SF / 12' = 23.5' stacked
# For Family/Dining: 244 / 15 = 16.3' deep
# Need total depth of ~50' to fit everything

$totalDepth = 50

# Y coordinates for room divisions
$y0 = 0                # South exterior
$y_mbath = 7           # Master bath: 7' x 10' = 70 SF
$y_hall = 11           # Hall level (4' wide = 38 SF / 4' width * 9.5' length)
$y_br_div = 24         # Bedroom division (12' for each bedroom)
$y_family_n = 35       # Family/dining north edge
$y_garage_n = 26       # Garage north edge (543 / 15.79 = 34.4' deep... adjust)
$y_north = $totalDepth # North exterior (50')

Write-Host ""
Write-Host "Building: 55.79' x $totalDepth'"
Write-Host "Zones: BR=$brWidth' | Central=$centralWidth' | Living=$livingWidth' | Garage=$garageWidth'"
Write-Host ""

# =====================================================
# CREATE WALLS
# =====================================================

$wallList = @()

# EXTERIOR (8" CMU)
$wallList += @{ d = "South"; x1 = 0; y1 = 0; x2 = 55.79; y2 = 0; t = $ext }
$wallList += @{ d = "East"; x1 = 55.79; y1 = 0; x2 = 55.79; y2 = 50; t = $ext }
$wallList += @{ d = "North"; x1 = 55.79; y1 = 50; x2 = 0; y2 = 50; t = $ext }
$wallList += @{ d = "West"; x1 = 0; y1 = 50; x2 = 0; y2 = 0; t = $ext }

# INTERIOR ZONE DIVIDERS (4" partitions)
# Bedroom zone east (x=12)
$wallList += @{ d = "BR-Zone-E"; x1 = $x1; y1 = 0; x2 = $x1; y2 = $y_br_div; t = $int }

# Central zone east (x=27)
$wallList += @{ d = "Central-E"; x1 = $x2; y1 = 0; x2 = $x2; y2 = 50; t = $int }

# Living zone east (x=40)
$wallList += @{ d = "Living-E"; x1 = $x3; y1 = 0; x2 = $x3; y2 = 50; t = $int }

# BEDROOM DIVISIONS
# BR-2/BR-3 horizontal divider (each bedroom 12' deep)
$wallList += @{ d = "BR-2/BR-3"; x1 = 0; y1 = $y_br_div; x2 = $x1; y2 = $y_br_div; t = $int }

# Make bedrooms 11.83' wide (y direction) to match areas:
# BR-2: 12' x 11.83' = 142 SF
# BR-3: 12' x 11.67' = 140 SF
# But they're in the same zone, so we use the zone width

# CENTRAL ZONE DIVISIONS
# Hall at y=11 (width=4')
$wallList += @{ d = "Hall-S"; x1 = $x1; y1 = $y_hall; x2 = $x2; y2 = $y_hall; t = $int }

# Family/Dining north boundary (to separate from patio/upper)
$wallList += @{ d = "Family-N"; x1 = $x1; y1 = $y_family_n; x2 = $x2; y2 = $y_family_n; t = $int }

# Bath-2 (6' x 7' = 42 SF) in lower central
$b2_width = 6
$b2_depth = 7
$wallList += @{ d = "Bath2-E"; x1 = ($x1 + $b2_width); y1 = 0; x2 = ($x1 + $b2_width); y2 = $b2_depth; t = $int }
$wallList += @{ d = "Bath2-N"; x1 = $x1; y1 = $b2_depth; x2 = ($x1 + $b2_width); y2 = $b2_depth; t = $int }

# Bath-3 (5' x 6.4' = 32 SF) in upper central area near y=35
$b3_width = 5
$b3_depth = 6.5
$wallList += @{ d = "Bath3-S"; x1 = $x1; y1 = ($y_family_n - $b3_depth); x2 = ($x1 + $b3_width); y2 = ($y_family_n - $b3_depth); t = $int }
$wallList += @{ d = "Bath3-E"; x1 = ($x1 + $b3_width); y1 = ($y_family_n - $b3_depth); x2 = ($x1 + $b3_width); y2 = $y_family_n; t = $int }

# LIVING/MASTER ZONE DIVISIONS
# Living: 13' x 17' = 221 SF... wait that's master bedroom target
# Let me recalculate:
# LIVING: 210 SF / 13' width = 16.15' deep
# MASTER: 221 SF / 13' width = 17' deep
# MASTER BATH: 70 SF / 7' width = 10' deep

$master_depth = 17
$mbath_depth = 10

# Master/Living divider (y position)
$wallList += @{ d = "Master-Living"; x1 = $x2; y1 = ($mbath_depth + $master_depth); x2 = $x3; y2 = ($mbath_depth + $master_depth); t = $int }

# Master Bath north wall
$wallList += @{ d = "MBath-N"; x1 = $x2; y1 = $mbath_depth; x2 = ($x2 + 7); y2 = $mbath_depth; t = $int }
$wallList += @{ d = "MBath-E"; x1 = ($x2 + 7); y1 = 0; x2 = ($x2 + 7); y2 = $mbath_depth; t = $int }

# GARAGE ZONE
# Garage: 543 SF / 15.79' width = 34.4' deep
$garage_depth = 34.4
$wallList += @{ d = "Garage-N"; x1 = $x3; y1 = $garage_depth; x2 = 55.79; y2 = $garage_depth; t = $int }

# Kitchen (200 SF) above garage
# Kitchen: 200 / 15.79 = 12.7' deep (from y=34.4 to y=47.1)
$kitchen_depth = 12.7
$wallList += @{ d = "Kitchen-N"; x1 = $x3; y1 = ($garage_depth + $kitchen_depth); x2 = 55.79; y2 = ($garage_depth + $kitchen_depth); t = $int }

# Laundry (30 SF = 5' x 6') in upper right corner
$wallList += @{ d = "Laundry-W"; x1 = (55.79 - 5); y1 = ($garage_depth + $kitchen_depth); x2 = (55.79 - 5); y2 = 50; t = $int }

# CLOSETS IN BEDROOMS (4' x 8' = 32 SF each)
$cl_w = 4
$cl_d = 8
# BR-2 closet (lower left)
$wallList += @{ d = "BR2-Cl-N"; x1 = 0; y1 = $cl_d; x2 = $cl_w; y2 = $cl_d; t = $int }
$wallList += @{ d = "BR2-Cl-E"; x1 = $cl_w; y1 = 0; x2 = $cl_w; y2 = $cl_d; t = $int }

# BR-3 closet (upper left, below y=24)
$wallList += @{ d = "BR3-Cl-S"; x1 = 0; y1 = ($y_br_div - $cl_d); x2 = $cl_w; y2 = ($y_br_div - $cl_d); t = $int }
$wallList += @{ d = "BR3-Cl-E"; x1 = $cl_w; y1 = ($y_br_div - $cl_d); x2 = $cl_w; y2 = $y_br_div; t = $int }

Write-Host "--- Creating Walls ---"
$created = 0
foreach ($w in $wallList) {
    $params = @{
        startPoint = @($w.x1, $w.y1, 0)
        endPoint = @($w.x2, $w.y2, 0)
        levelId = $levelId
        height = 10
        wallType = $w.t
    }
    $result = Send-MCPRequest -method "createWall" -params $params
    if ($result.success) {
        $created++
        Write-Host "  OK: $($w.d)"
    } else {
        Write-Host "  FAIL: $($w.d) - $($result.error)"
    }
}

# =====================================================
# ROOM AREA CALCULATION
# =====================================================
Write-Host ""
Write-Host "======================================================="
Write-Host "ROOM AREA VERIFICATION"
Write-Host "======================================================="

# Calculate actual areas from wall positions
$br2_area = ($x1 - $cl_w) * $cl_d + $x1 * ($y_br_div - $cl_d)
$br2_simple = $x1 * $y_br_div - $cl_w * $cl_d
Write-Host "BEDROOM-2:      $([math]::Round($br2_simple)) SF (Target: 142)"

$br3_area = $x1 * (50 - $y_br_div) - $cl_w * $cl_d
Write-Host "BEDROOM-3:      $([math]::Round($br3_area)) SF (Target: 140)"

$family_area = ($x2 - $x1) * ($y_family_n - $y_hall) - $b3_width * $b3_depth
Write-Host "FAMILY/DINING:  $([math]::Round($family_area)) SF (Target: 244)"

$living_area = ($x3 - $x2) * (50 - ($mbath_depth + $master_depth))
Write-Host "LIVING:         $([math]::Round($living_area)) SF (Target: 210)"

$master_area = ($x3 - $x2) * $master_depth
Write-Host "MASTER BEDROOM: $([math]::Round($master_area)) SF (Target: 221)"

$mbath_area = 7 * $mbath_depth
Write-Host "MASTER BATH:    $([math]::Round($mbath_area)) SF (Target: 70)"

$bath2_area = $b2_width * $b2_depth
Write-Host "BATH-2:         $([math]::Round($bath2_area)) SF (Target: 42)"

$bath3_area = $b3_width * $b3_depth
Write-Host "BATH-3:         $([math]::Round($bath3_area)) SF (Target: 32)"

$garage_area = (55.79 - $x3) * $garage_depth
Write-Host "GARAGE:         $([math]::Round($garage_area)) SF (Target: 543)"

$kitchen_area = (55.79 - $x3) * $kitchen_depth
Write-Host "KITCHEN:        $([math]::Round($kitchen_area)) SF (Target: 200)"

Write-Host ""
Write-Host "Total walls created: $created"

$zoom = Send-MCPRequest -method "zoomToFit" -params @{}
Write-Host "Done!"

# Avon Park Floor Plan - TRACED from PDF
# Following the actual dimension strings and room layout

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

Write-Host "================================================"
Write-Host "AVON PARK - TRACED FROM PDF DIMENSIONS"
Write-Host "================================================"

# Get level
$levels = Send-MCPRequest -method "getLevels" -params @{}
$levelId = ($levels.levels | Where-Object { $_.elevation -eq 0 } | Select-Object -First 1).levelId
if (-not $levelId) { $levelId = $levels.levels[0].levelId }

$ext = "Generic - 8`""  # 8" CMU exterior
$int = "Generic - 4`""  # 4" interior

# ===================================================
# DIMENSIONS FROM PDF (traced carefully)
# ===================================================
# Total width: 55'-9 1/2" = 55.79'
# From dimension string: 11'-10" + wall + 41'-10" = ~54' + walls
#
# ROOM AREAS (must match these!):
# BEDROOM-3:      140 SF -> 11.67' x 12'
# BEDROOM-2:      142 SF -> 11.83' x 12'
# FAMILY/DINING:  244 SF -> 14' x 17.43'
# LIVING:         210 SF -> 14' x 15'
# MASTER BEDROOM: 221 SF -> 13' x 17'
# MASTER BATH:    70 SF  -> 7' x 10'
# BATH-2:         42 SF  -> 6' x 7'
# BATH-3:         32 SF  -> 5.33' x 6'
# HALL-1:         38 SF  -> 4' x 9.5'
# KITCHEN:        200 SF -> 12.5' x 16'
# LAUNDRY:        30 SF  -> 5' x 6'
# CLOSET:         32 SF  -> 4' x 8'
# 2-CAR GARAGE:   543 SF -> 20' x 27.15'
#
# Building footprint calculation:
# Under air: 1,991 SF
# If building is 55.79' wide: depth = 1991/55.79 = 35.7' (for main house)
# Plus garage: 543 SF / 20' wide = 27' deep
# ===================================================

# Building depth calculated from areas:
# Main living area needs to be ~36' deep to get 1991 SF at ~55' width
# BUT garage is separate, so let's calculate:
# Total under air (no garage): 1991 SF
# If width for living = 35', depth = 1991/35 = 57' - too deep
# So building must be wider for living, with garage on side

# From PDF visual: Main house ~35' wide, Garage ~21' wide
# Main house: 35' x 57' = nope, that's 1995 SF but 57' is too deep
#
# Let me use: Main house 35' wide, 28.5' deep = 997 SF
# That's only half! The building must have more area.

# ACTUAL CALCULATION:
# Looking at the floor plan, the building appears to be:
# - About 55.79' wide (E-W)
# - About 36-40' deep (N-S)
# - With the garage taking up part of that footprint

# Let's use 55.79' x 45' = 2510 SF total footprint
# Minus garage 543 SF = 1967 SF under air (close to 1991!)

# So: Building is 55.79' x 45' roughly
# Garage is in the SE corner, about 20' x 27' = 540 SF

# COORDINATE SYSTEM:
# Origin (0,0) at SW corner
# X increases to EAST
# Y increases to NORTH

# X coordinates (traced from PDF dimensions):
$x_west = 0             # West exterior wall
$x_br_east = 11.83      # East edge of bedrooms (11'-10")
$x_center = 25.83       # East edge of central zone (11.83 + 14 = 25.83)
$x_living = 38.83       # East edge of living/master zone (25.83 + 13 = 38.83)
$x_east = 55.79         # East exterior wall (total width)

# Garage starts at x = 35.79 (55.79 - 20 = 35.79 for 20' wide garage)
$x_garage = 35.79

# Y coordinates (based on room depths):
$y_south = 0            # South exterior wall
$y_masterbath = 10      # Master bath is 10' deep
$y_mid = 22             # Middle division (bedroom split, living/master split)
$y_kitchen = 32         # Kitchen north edge
$y_north = 45           # North exterior wall (approx)

# Garage north edge
$y_garage_north = 27    # Garage is 27' deep

Write-Host "Building dimensions: 55.79' x 45'"
Write-Host "Garage: 20' x 27' = 540 SF"
Write-Host ""

# ===================================================
# EXTERIOR WALLS (8" CMU)
# ===================================================

$exteriorWalls = @(
    # Main perimeter
    @{ desc = "South Wall"; start = @(0, 0); end = @(55.79, 0) },
    @{ desc = "East Wall - Lower"; start = @(55.79, 0); end = @(55.79, $y_garage_north) },
    @{ desc = "East-North Jog"; start = @(55.79, $y_garage_north); end = @($x_garage, $y_garage_north) },
    @{ desc = "East Wall - Upper"; start = @($x_garage, $y_garage_north); end = @($x_garage, $y_north) },
    @{ desc = "North Wall"; start = @($x_garage, $y_north); end = @(0, $y_north) },
    @{ desc = "West Wall"; start = @(0, $y_north); end = @(0, 0) }
)

Write-Host "--- Creating Exterior Walls (8`") ---"
$extCount = 0
foreach ($wall in $exteriorWalls) {
    $params = @{
        startPoint = @($wall.start[0], $wall.start[1], 0)
        endPoint = @($wall.end[0], $wall.end[1], 0)
        levelId = $levelId
        height = 10
        wallType = $ext
    }
    $result = Send-MCPRequest -method "createWall" -params $params
    if ($result.success) {
        $extCount++
        $len = [math]::Round([math]::Sqrt([math]::Pow($wall.end[0] - $wall.start[0], 2) + [math]::Pow($wall.end[1] - $wall.start[1], 2)), 2)
        Write-Host "  OK: $($wall.desc) ($len ft)"
    } else {
        Write-Host "  FAIL: $($wall.desc) - $($result.error)"
    }
}

# ===================================================
# INTERIOR WALLS (4" wood stud)
# ===================================================

$interiorWalls = @(
    # === MAIN VERTICAL DIVISIONS ===

    # Bedroom zone east wall (x = 11.83)
    @{ desc = "Bedrooms East Wall"; start = @($x_br_east, 0); end = @($x_br_east, $y_north) },

    # Living/Master zone east wall (x = 38.83) - separates from garage zone
    @{ desc = "Garage West Wall"; start = @($x_living, 0); end = @($x_living, $y_garage_north) },

    # Central/Living division (x = 25.83)
    @{ desc = "Central/Living Division"; start = @($x_center, 0); end = @($x_center, $y_north) },

    # === BEDROOM HORIZONTAL DIVISION ===
    # Bedroom-2 and Bedroom-3 split (y = 22)
    @{ desc = "BR-2/BR-3 Division"; start = @(0, $y_mid); end = @($x_br_east, $y_mid) },

    # === LIVING/MASTER HORIZONTAL DIVISION ===
    # y = 22 continues through living zone
    @{ desc = "Living/Master Division"; start = @($x_center, $y_mid); end = @($x_living, $y_mid) },

    # === MASTER BATH WALLS ===
    # Master bath north wall (y = 10)
    @{ desc = "Master Bath North"; start = @($x_center, $y_masterbath); end = @($x_living, $y_masterbath) },
    # Master bath west wall
    @{ desc = "Master Bath West"; start = @(30, 0); end = @(30, $y_masterbath) },

    # === CENTRAL ZONE DIVISIONS ===
    # Bath-2 area (lower left of central zone)
    @{ desc = "Bath-2 South"; start = @($x_br_east, 7); end = @(18, 7) },
    @{ desc = "Bath-2 East"; start = @(18, 0); end = @(18, 7) },

    # Bath-3 area (upper left of central zone)
    @{ desc = "Bath-3 South"; start = @($x_br_east, 38); end = @(17, 38) },
    @{ desc = "Bath-3 East"; start = @(17, 38); end = @(17, $y_north) },

    # Hall-1 walls
    @{ desc = "Hall North"; start = @($x_br_east, 12); end = @($x_center, 12) },

    # === CLOSET WALLS IN BEDROOMS ===
    @{ desc = "BR-3 Closet South"; start = @(0, 36); end = @(5, 36) },
    @{ desc = "BR-3 Closet East"; start = @(5, 36); end = @(5, $y_mid) },
    @{ desc = "BR-2 Closet North"; start = @(0, 8); end = @(5, 8) },
    @{ desc = "BR-2 Closet East"; start = @(5, 0); end = @(5, 8) },

    # === GARAGE ZONE DIVISIONS ===
    # Kitchen south wall
    @{ desc = "Kitchen South"; start = @($x_living, 16); end = @($x_garage, 16) },
    # Laundry walls
    @{ desc = "Laundry South"; start = @($x_garage, 21); end = @(50, 21) },
    @{ desc = "Laundry East"; start = @(50, 16); end = @(50, $y_garage_north) },
    # Kitchen/Garage separation
    @{ desc = "Kitchen East"; start = @($x_garage, 16); end = @($x_garage, $y_garage_north) }
)

Write-Host ""
Write-Host "--- Creating Interior Walls (4`") ---"
$intCount = 0
foreach ($wall in $interiorWalls) {
    $params = @{
        startPoint = @($wall.start[0], $wall.start[1], 0)
        endPoint = @($wall.end[0], $wall.end[1], 0)
        levelId = $levelId
        height = 10
        wallType = $int
    }
    $result = Send-MCPRequest -method "createWall" -params $params
    if ($result.success) {
        $intCount++
        $len = [math]::Round([math]::Sqrt([math]::Pow($wall.end[0] - $wall.start[0], 2) + [math]::Pow($wall.end[1] - $wall.start[1], 2)), 2)
        Write-Host "  OK: $($wall.desc) ($len ft)"
    } else {
        Write-Host "  FAIL: $($wall.desc) - $($result.error)"
    }
}

# ===================================================
# CALCULATE AND VERIFY ROOM AREAS
# ===================================================

Write-Host ""
Write-Host "================================================"
Write-Host "ROOM AREA VERIFICATION"
Write-Host "================================================"

# Calculate areas from coordinates
$br3_area = ($x_br_east - 5) * ($y_north - $y_mid) + 5 * ($y_north - 36)  # minus closet
$br3_area = $x_br_east * ($y_north - $y_mid) - 5 * ($y_north - 36)
Write-Host "BEDROOM-3:      $([math]::Round($br3_area)) SF (Target: 140)"

$br2_area = $x_br_east * $y_mid - 5 * 8  # minus closet
Write-Host "BEDROOM-2:      $([math]::Round($br2_area)) SF (Target: 142)"

$family_area = ($x_center - $x_br_east) * ($y_north - 12) - (17 - $x_br_east) * ($y_north - 38)  # minus bath-3
Write-Host "FAMILY/DINING:  $([math]::Round($family_area)) SF (Target: 244)"

$living_area = ($x_living - $x_center) * ($y_north - $y_mid)
Write-Host "LIVING:         $([math]::Round($living_area)) SF (Target: 210)"

$master_area = ($x_living - $x_center) * ($y_mid - $y_masterbath)
Write-Host "MASTER BEDROOM: $([math]::Round($master_area)) SF (Target: 221)"

$masterbath_area = ($x_living - 30) * $y_masterbath
Write-Host "MASTER BATH:    $([math]::Round($masterbath_area)) SF (Target: 70)"

$garage_area = ($x_east - $x_living) * $y_garage_north - (50 - $x_living) * ($y_garage_north - 16)
Write-Host "2-CAR GARAGE:   $([math]::Round($garage_area)) SF (Target: 543)"

$kitchen_area = ($x_garage - $x_living) * ($y_garage_north - 16)
Write-Host "KITCHEN:        $([math]::Round($kitchen_area)) SF (Target: 200)"

Write-Host ""
Write-Host "================================================"
Write-Host "Exterior Walls: $extCount"
Write-Host "Interior Walls: $intCount"
Write-Host "Total Walls: $($extCount + $intCount)"
Write-Host "================================================"

# Zoom to fit
$zoom = Send-MCPRequest -method "zoomToFit" -params @{}
Write-Host "View zoomed: $($zoom.success)"

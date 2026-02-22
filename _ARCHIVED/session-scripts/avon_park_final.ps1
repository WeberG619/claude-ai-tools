# Avon Park Floor Plan - Final Version
# Based on: Total 55.79' x 45' footprint, with garage inside

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
Write-Host "AVON PARK FLOOR PLAN - FINAL VERSION"
Write-Host "================================================"

$levels = Send-MCPRequest -method "getLevels" -params @{}
$levelId = ($levels.levels | Where-Object { $_.elevation -eq 0 } | Select-Object -First 1).levelId
if (-not $levelId) { $levelId = $levels.levels[0].levelId }

$ext = "Generic - 8`""
$int = "Generic - 4`""

# ================================================================
# BUILDING DIMENSIONS (from PDF analysis)
# ================================================================
# Width: 55'-9 1/2" = 55.79'
# From dimension: "11'-10" + 4.5" + 41'-10"" breakdown
#
# Room areas to achieve:
# BEDROOM-3: 140 SF -> 11.67' x 12'
# BEDROOM-2: 142 SF -> 11.83' x 12'
# FAMILY/DINING: 244 SF -> 14' x 17.43'
# LIVING: 210 SF -> 14' x 15'
# MASTER BEDROOM: 221 SF -> 13' x 17'
# MASTER BATH: 70 SF -> 7' x 10'
# KITCHEN: 200 SF -> 12.5' x 16'
# 2-CAR GARAGE: 543 SF -> 22' x 24.7'
#
# Layout strategy:
# - Bedrooms stacked on left (12' wide, 24' total depth)
# - Central zone with Family/Dining, baths, hall
# - Living/Master zone
# - Garage/Kitchen zone on right
# ================================================================

# COORDINATES based on room area calculations:

# X-coordinates (West to East):
$x0 = 0           # West exterior
$x1 = 11.83       # East of bedroom zone (11'-10")
$x2 = 25.83       # East of central zone (11.83 + 14 = ~26')
$x3 = 38.83       # East of living/master zone (25.83 + 13 = ~39')
$x4 = 55.79       # East exterior (total width)

# Y-coordinates (South to North):
# Building depth: ~45' total to accommodate all rooms
$y0 = 0           # South exterior
$y1 = 10          # Master bath north edge (10' from south)
$y2 = 12          # Lower room boundaries
$y3 = 24          # Mid-point (bedrooms split here)
$y4 = 27          # Upper section
$y5 = 38          # Kitchen/utility north edge
$y6 = 45          # North exterior

# Garage boundaries:
$gx1 = 38.83      # Garage west (same as x3)
$gx2 = 55.79      # Garage east (x4)
$gy1 = 0          # Garage south
$gy2 = 24.7       # Garage north (543 SF / 22' = 24.7')

Write-Host "Building: 55.79' x 45'"
Write-Host "Garage zone: 17' x 25'"

# ================================================================
# EXTERIOR WALLS (8" CMU)
# ================================================================

$exteriorWalls = @(
    # Perimeter
    @{ desc = "South"; start = @(0, 0); end = @(55.79, 0) },
    @{ desc = "East"; start = @(55.79, 0); end = @(55.79, 45) },
    @{ desc = "North"; start = @(55.79, 45); end = @(0, 45) },
    @{ desc = "West"; start = @(0, 45); end = @(0, 0) }
)

Write-Host "`n--- Exterior Walls (8`") ---"
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
        Write-Host "  OK: $($wall.desc)"
    } else {
        Write-Host "  FAIL: $($wall.desc)"
    }
}

# ================================================================
# INTERIOR WALLS (4" partitions)
# ================================================================

$interiorWalls = @(
    # === MAIN VERTICAL ZONES ===

    # Bedroom zone east wall (x=11.83)
    @{ desc = "Bedroom Zone East"; start = @(11.83, 0); end = @(11.83, 45) },

    # Central zone east wall (x=25.83)
    @{ desc = "Central Zone East"; start = @(25.83, 0); end = @(25.83, 45) },

    # Living/Garage zone divider (x=38.83)
    @{ desc = "Living/Garage Divider"; start = @(38.83, 0); end = @(38.83, 45) },

    # === BEDROOM ZONE DIVISIONS ===

    # BR-2/BR-3 horizontal divider (y=24 for 12' rooms)
    @{ desc = "BR-2/BR-3 Divider"; start = @(0, 24); end = @(11.83, 24) },

    # BR-2 closet (5'x6')
    @{ desc = "BR-2 Closet North"; start = @(0, 6); end = @(5, 6) },
    @{ desc = "BR-2 Closet East"; start = @(5, 0); end = @(5, 6) },

    # BR-3 closet (5'x6')
    @{ desc = "BR-3 Closet South"; start = @(0, 39); end = @(5, 39) },
    @{ desc = "BR-3 Closet East"; start = @(5, 39); end = @(5, 45) },

    # === CENTRAL ZONE DIVISIONS ===

    # Family/Dining is the main space (14' x 17.43' = 244 SF)
    # Hall and baths are in the lower portion

    # Hall south wall (y=10)
    @{ desc = "Hall South"; start = @(11.83, 10); end = @(25.83, 10) },

    # Bath-2 walls (6' x 7' = 42 SF)
    @{ desc = "Bath-2 East"; start = @(17.83, 0); end = @(17.83, 7) },
    @{ desc = "Bath-2 North"; start = @(11.83, 7); end = @(17.83, 7) },

    # Bath-3 in upper central (5.33' x 6' = 32 SF)
    @{ desc = "Bath-3 South"; start = @(11.83, 39); end = @(17.16, 39) },
    @{ desc = "Bath-3 East"; start = @(17.16, 39); end = @(17.16, 45) },

    # === LIVING/MASTER ZONE DIVISIONS ===

    # Living/Master horizontal divider (y=27 for proper areas)
    # Living: 13' x 18' = 234 SF (target 210)
    # Master: 13' x 17' = 221 SF (target 221)
    @{ desc = "Living/Master Divider"; start = @(25.83, 27); end = @(38.83, 27) },

    # Master Bath walls (7' x 10' = 70 SF)
    @{ desc = "Master Bath North"; start = @(25.83, 10); end = @(32.83, 10) },
    @{ desc = "Master Bath East"; start = @(32.83, 0); end = @(32.83, 10) },

    # === GARAGE/KITCHEN ZONE ===

    # Garage north wall (at y=24.7 for 543 SF with 17' width)
    # Actually: 543 / 17 = 31.9' deep - let's use 25'
    @{ desc = "Garage North"; start = @(38.83, 25); end = @(55.79, 25) },

    # Kitchen walls (12.5' x 16' = 200 SF)
    # Kitchen is between garage north and upper area
    @{ desc = "Kitchen South"; start = @(38.83, 32); end = @(51.33, 32) },

    # Laundry (5' x 6' = 30 SF)
    @{ desc = "Laundry East"; start = @(51.33, 32); end = @(51.33, 38) },
    @{ desc = "Laundry North"; start = @(38.83, 38); end = @(51.33, 38) },

    # Utility/Storage
    @{ desc = "Utility South"; start = @(38.83, 40); end = @(55.79, 40) }
)

Write-Host "`n--- Interior Walls (4`") ---"
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
        Write-Host "  OK: $($wall.desc)"
    } else {
        Write-Host "  FAIL: $($wall.desc)"
    }
}

# ================================================================
# ROOM AREA VERIFICATION
# ================================================================

Write-Host "`n================================================"
Write-Host "ROOM AREA VERIFICATION"
Write-Host "================================================"

# Calculate from coordinates
$br2 = (11.83 - 5) * 6 + 11.83 * (24 - 6)  # Main area minus closet
$br2_actual = 11.83 * 24 - 5 * 6
Write-Host "BEDROOM-2:      $([math]::Round($br2_actual)) SF (Target: 142)"

$br3 = 11.83 * (45 - 24) - 5 * 6
Write-Host "BEDROOM-3:      $([math]::Round($br3)) SF (Target: 140)"

$family = (25.83 - 11.83) * (45 - 10) - (17.16 - 11.83) * 6  # minus bath-3
Write-Host "FAMILY/DINING:  $([math]::Round($family)) SF (Target: 244)"

$living = (38.83 - 25.83) * (45 - 27)
Write-Host "LIVING:         $([math]::Round($living)) SF (Target: 210)"

$master = (38.83 - 25.83) * (27 - 10)
Write-Host "MASTER BEDROOM: $([math]::Round($master)) SF (Target: 221)"

$mbath = (32.83 - 25.83) * 10
Write-Host "MASTER BATH:    $([math]::Round($mbath)) SF (Target: 70)"

$bath2 = (17.83 - 11.83) * 7
Write-Host "BATH-2:         $([math]::Round($bath2)) SF (Target: 42)"

$garage = (55.79 - 38.83) * 25
Write-Host "GARAGE:         $([math]::Round($garage)) SF (Target: 543)"

$kitchen = (51.33 - 38.83) * (38 - 32)
Write-Host "KITCHEN:        $([math]::Round($kitchen)) SF (Target: 200)"

Write-Host "`n================================================"
Write-Host "Exterior: $extCount, Interior: $intCount"
Write-Host "Total Walls: $($extCount + $intCount)"
Write-Host "================================================"

$zoom = Send-MCPRequest -method "zoomToFit" -params @{}
Write-Host "View zoomed: $($zoom.success)"

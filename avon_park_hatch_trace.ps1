# Avon Park Floor Plan - TRACING THE WALL HATCH PATTERNS
# Following the shaded/hatched wall patterns exactly as shown in PDF

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
Write-Host "AVON PARK - TRACING WALL HATCH PATTERNS"
Write-Host "================================================"

$levels = Send-MCPRequest -method "getLevels" -params @{}
$levelId = ($levels.levels | Where-Object { $_.elevation -eq 0 } | Select-Object -First 1).levelId
if (-not $levelId) { $levelId = $levels.levels[0].levelId }

$ext = "Generic - 8`""  # Exterior CMU
$int = "Generic - 4`""  # Interior partition

# ================================================================
# TRACING WALL HATCH PATTERNS FROM PDF
# ================================================================
# Looking at the floor plan, I trace the CENTER LINE of each wall
# by following the hatched pattern
#
# PDF shows the floor plan with:
# - North arrow pointing upper-right
# - Scale: 1/4" = 1'-0"
# - Total width: 55'-9 1/2"
#
# I'm tracing each wall segment as I see it in the hatch pattern
# ================================================================

# COORDINATE REFERENCE:
# Setting origin at SOUTHWEST corner of building
# X = East (positive), Y = North (positive)
# All dimensions in FEET

# From PDF dimension strings, reading the segment markers:
# Top string shows points at: 0, 12'-4", then 14'-8" more, then 11'-3" more, etc.
# Total: 55'-9.5"

# ================================================================
# TRACING EXTERIOR PERIMETER (following outer hatch edge)
# ================================================================

# The building perimeter traced from the hatch pattern:
# Starting at SW corner, going clockwise...

# Looking at the PDF floor plan image:
# - The PATIO is at top (outdoor, not enclosed)
# - The PORCH is at bottom right (outdoor)
# - The main heated space includes bedrooms, living areas, and bathrooms
# - Garage is enclosed but not heated

# From visual inspection of hatch pattern:
# The exterior wall outline appears to be roughly:
# - 55.79' wide (E-W)
# - Main house: ~30-35' deep (N-S)
# - Garage section: steps in from the main house line

# Dimension string reading (top, left to right):
# 2" + 12'-4" + 14'-8" + 11'-3" + 3'-5" + 7'-4 1/2" = 49'-2" (not full width)
# Missing ~6.5' for remaining segments (garage east portion)

# Let me trace what I can clearly see in the hatch pattern:

# X-coordinate markers from dimension string:
$x0 = 0           # West wall (left edge)
$x1 = 12.33       # 12'-4" from west (first major division - bedroom zone east)
$x2 = 27          # 12.33 + 14.67 = 27' (central zone)
$x3 = 38.25       # 27 + 11.25 = 38.25' (living area)
$x4 = 41.67       # 38.25 + 3.42 = 41.67' (small jog)
$x5 = 49.04       # 41.67 + 7.375 = 49.04' (before garage end)
$x6 = 55.79       # East wall (full width)

# Y-coordinate markers from vertical dimension strings:
# Left side: 7'-0" + 12'-10" + ...
$y0 = 0           # South wall
$y1 = 7           # 7'-0" up (master bath height?)
$y2 = 12.83       # 7 + 5.83 (some room division)
$y3 = 19.83       # Another marker
$y4 = 27          # Upper section
$y5 = 32          # Near north edge
$y_north = 35     # North wall (approximate)

# ================================================================
# EXTERIOR WALLS - Tracing the outer hatch boundary
# ================================================================

Write-Host "`n--- Tracing Exterior Walls (8`" CMU) ---"

# The exterior hatch pattern shows a roughly rectangular building
# with some variation on the east side for garage/porch

$exteriorWalls = @(
    # SOUTH WALL - Full width along bottom
    @{ desc = "South Wall (full width)"; start = @(0, 0); end = @(55.79, 0) },

    # EAST WALL - From SE corner going north
    @{ desc = "East Wall (garage)"; start = @(55.79, 0); end = @(55.79, 24) },

    # EAST-NORTH TRANSITION - The building steps in here
    @{ desc = "Garage North Wall"; start = @(55.79, 24); end = @(41, 24) },

    # EAST WALL UPPER - Continues north from step-in
    @{ desc = "East Wall (upper)"; start = @(41, 24); end = @(41, $y_north) },

    # NORTH WALL - Back to west
    @{ desc = "North Wall"; start = @(41, $y_north); end = @(0, $y_north) },

    # WEST WALL - South back to start
    @{ desc = "West Wall"; start = @(0, $y_north); end = @(0, 0) }
)

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

# ================================================================
# INTERIOR WALLS - Tracing the interior hatch lines
# ================================================================

Write-Host "`n--- Tracing Interior Walls (4`" partitions) ---"

# From the PDF, I can see interior partition walls at:
# - x = 12.33' (separating bedrooms from central area)
# - Various horizontal walls dividing rooms
# - Bathroom walls
# - Closet walls

$interiorWalls = @(
    # BEDROOM ZONE EAST WALL (x ≈ 12')
    @{ desc = "Bedroom Zone East"; start = @(12, 0); end = @(12, $y_north) },

    # BEDROOM DIVIDER (horizontal, splitting BR-2 and BR-3)
    @{ desc = "BR-2/BR-3 Divider"; start = @(0, 17.5); end = @(12, 17.5) },

    # LIVING/MASTER ZONE (x ≈ 27')
    @{ desc = "Central/Living Division"; start = @(27, 0); end = @(27, $y_north) },

    # GARAGE ZONE WEST WALL (x ≈ 41')
    # Already part of exterior step-in

    # HORIZONTAL DIVISIONS IN LIVING/MASTER ZONE
    @{ desc = "Living/Master Division"; start = @(27, 17.5); end = @(41, 17.5) },

    # MASTER BATH WALLS
    @{ desc = "Master Bath North"; start = @(27, 8); end = @(41, 8) },
    @{ desc = "Master Bath East Division"; start = @(33, 0); end = @(33, 8) },

    # BATH-2 WALLS (in central zone, lower portion)
    @{ desc = "Bath-2 South"; start = @(12, 6); end = @(19, 6) },
    @{ desc = "Bath-2 East"; start = @(19, 0); end = @(19, 6) },

    # BATH-3 WALLS (in central zone, upper portion)
    @{ desc = "Bath-3 South"; start = @(12, 28); end = @(17, 28) },
    @{ desc = "Bath-3 East"; start = @(17, 28); end = @(17, $y_north) },

    # HALL WALLS
    @{ desc = "Hall South"; start = @(12, 11); end = @(27, 11) },

    # CLOSETS IN BEDROOMS
    @{ desc = "BR-3 Closet South"; start = @(0, 28); end = @(5, 28) },
    @{ desc = "BR-3 Closet East"; start = @(5, 28); end = @(5, 17.5) },
    @{ desc = "BR-2 Closet North"; start = @(0, 7); end = @(5, 7) },
    @{ desc = "BR-2 Closet East"; start = @(5, 0); end = @(5, 7) },

    # KITCHEN/LAUNDRY/UTILITY ZONE
    @{ desc = "Kitchen West"; start = @(35, 0); end = @(35, 24) },
    @{ desc = "Kitchen/Utility Divider"; start = @(35, 18); end = @(41, 18) },
    @{ desc = "Laundry East"; start = @(48, 18); end = @(48, 24) },
    @{ desc = "Laundry South"; start = @(41, 20); end = @(55.79, 20) }
)

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

# ================================================================
# SUMMARY
# ================================================================

Write-Host "`n================================================"
Write-Host "HATCH PATTERN TRACE COMPLETE"
Write-Host "================================================"
Write-Host "Exterior Walls: $extCount"
Write-Host "Interior Walls: $intCount"
Write-Host "Total: $($extCount + $intCount)"

# Calculate approximate areas
Write-Host "`n--- Approximate Room Areas ---"
Write-Host "BEDROOM-3:      $([math]::Round((12 - 5) * (35 - 28) + 12 * (28 - 17.5))) SF (Target: 140)"
Write-Host "BEDROOM-2:      $([math]::Round((12 - 5) * 7 + 12 * (17.5 - 7))) SF (Target: 142)"
Write-Host "FAMILY/DINING:  $([math]::Round((27 - 12) * (35 - 11) - (17 - 12) * (35 - 28))) SF (Target: 244)"
Write-Host "LIVING:         $([math]::Round((41 - 27) * (35 - 17.5))) SF (Target: 210)"
Write-Host "MASTER:         $([math]::Round((41 - 27) * (17.5 - 8))) SF (Target: 221)"
Write-Host "MASTER BATH:    $([math]::Round((33 - 27) * 8 + (41 - 33) * 8)) SF (Target: 70)"
Write-Host "GARAGE:         $([math]::Round((55.79 - 41) * 24 - (55.79 - 41) * 4)) SF (Target: 543)"

$zoom = Send-MCPRequest -method "zoomToFit" -params @{}
Write-Host "`nZoomed: $($zoom.success)"

$pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", "RevitMCPBridge2026", [System.IO.Pipes.PipeDirection]::InOut)
$pipe.Connect(5000)
$writer = New-Object System.IO.StreamWriter($pipe)
$reader = New-Object System.IO.StreamReader($pipe)
$writer.AutoFlush = $true

function Send-Revit($json) {
    $writer.WriteLine($json)
    return $reader.ReadLine()
}

$levelId = 368
$h = 10.0

# ============================================================
# REAL FLOOR PLAN - Based on Houseplans.com Plan #70-1207
# 1500 sf, 3 bed, 2 bath ranch with 3-car garage
#
# Coordinate system: origin at bottom-left corner of house
# Y=0 is south (front porch side), Y increases going north
# X=0 is west (left), X increases going east
#
# The plan has the garage on the left, living on the right,
# bedrooms tucked behind the garage.
# ============================================================

Write-Host "=== CREATING WALLS - Real Floor Plan ==="

# ---- OVERALL DIMENSIONS ----
# Total width: 56ft (32 garage + 24 living)
# Depth: 48ft
# Garage: x=0..32, y=26..48 (upper left)
# Bedrooms: x=0..32, y=0..26 (lower left)
# Living: x=32..56, y=0..48 (right side)

# ---- EXTERIOR WALLS ----

# South wall (front) - full width
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[0,0,0],"endPoint":[56,0,0],"levelId":368,"height":10}}')
Write-Host "South exterior: $r"

# East wall - full height
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[56,0,0],"endPoint":[56,48,0],"levelId":368,"height":10}}')
Write-Host "East exterior: $r"

# North wall - full width
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[56,48,0],"endPoint":[0,48,0],"levelId":368,"height":10}}')
Write-Host "North exterior: $r"

# West wall - full height
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[0,48,0],"endPoint":[0,0,0],"levelId":368,"height":10}}')
Write-Host "West exterior: $r"

# ---- GARAGE / HOUSE DIVIDER ----
# Garage wall separating garage from bedrooms/living (vertical at x=32)
# But only from y=26 to y=48 (garage area)
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[32,26,0],"endPoint":[32,48,0],"levelId":368,"height":10}}')
Write-Host "Garage east wall: $r"

# Garage south wall (separating garage from bedrooms)
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[0,26,0],"endPoint":[32,26,0],"levelId":368,"height":10}}')
Write-Host "Garage south wall: $r"

# ---- BEDROOM ZONE (x=0..32, y=0..26) ----

# Master bedroom: x=0..15, y=0..15 (southwest corner, front of house)
# Master bed east wall (x=15, y=0..15)
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[15,0,0],"endPoint":[15,15,0],"levelId":368,"height":10}}')
Write-Host "Master bed east wall: $r"

# Master bed north wall / master suite divider (y=15, x=0..15)
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[0,15,0],"endPoint":[15,15,0],"levelId":368,"height":10}}')
Write-Host "Master suite north: $r"

# Master bath area: x=0..11, y=15..21
# Master closet: x=11..15, y=15..21
# Master bath / closet divider (x=11, y=15..21)
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[11,15,0],"endPoint":[11,21,0],"levelId":368,"height":10}}')
Write-Host "MBath/Closet divider: $r"

# Master bath/closet north wall (y=21, x=0..15)
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[0,21,0],"endPoint":[15,21,0],"levelId":368,"height":10}}')
Write-Host "MBath north wall: $r"

# ---- HALLWAY (x=15..19, y=0..26) ----
# 3.5ft wide hall connecting bedrooms to living area
# Hall east wall (x=19, y=0..26) - but only bedroom section
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[19,0,0],"endPoint":[19,26,0],"levelId":368,"height":10}}')
Write-Host "Hall east wall: $r"

# ---- HALL BATHROOM (x=15..19, y=15..23) ----
# Hall bath south wall (y=15 already exists as master suite north)
# Hall bath north wall (y=23, x=15..19)
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[15,23,0],"endPoint":[19,23,0],"levelId":368,"height":10}}')
Write-Host "Hall bath north: $r"

# ---- BEDROOM 2 (x=19..30, y=15..26) ----
# Bed 2 south wall (y=15, x=19..30) - partial, connects to hall bath
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[19,15,0],"endPoint":[32,15,0],"levelId":368,"height":10}}')
Write-Host "Bed2 south wall: $r"

# Bed 2 / Bed 3 divider (y=15 is already the line)
# Actually Bed 2 is upper, Bed 3 is lower in the bedroom wing
# Let me reconsider the layout:
# Bed 2: x=19..30, y=15..26 (upper, 11x11)
# Bed 3: x=19..30, y=4..15 (lower, 11x11 approx - actually 11'4 x 10)
# Hall Bath: x=15..19, y=15..23

# Bed 3 south wall doesn't need separate - it shares with hall
# Bed 3 area: x=19..30, y=0..15
# But we already have the wall at y=15 from x=19 to x=32

# Need east wall for bedroom zone at x=30 (bedrooms don't go all the way to x=32)
# Actually let's make bedrooms go to x=30 with closets at x=30..32
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[30,0,0],"endPoint":[30,26,0],"levelId":368,"height":10}}')
Write-Host "Bedroom closet wall: $r"

# Closet divider between bed2 closet and bed3 closet (y=15 already exists from x=19..32)
# Linen closet area at x=30..32, y=0..26 (narrow strip for closets)

# ---- LIVING AREA (x=32..56, y=0..48) ----

# Great Room: x=32..56, y=26..48 (upper right, opens to garage area visually)
# Actually great room is the main living space - let me put it at top right
# Kitchen: x=44..56, y=0..13 (southeast corner area)
# Dining: x=32..44, y=0..13 (south center)
# Great Room: x=32..56, y=13..42 (large central space)
# Laundry: x=50..56, y=0..7 (bottom right corner)

# Dining/Kitchen south boundary is the exterior south wall (y=0)
# Great room / dining-kitchen divider (y=13, x=32..56)
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[32,13,0],"endPoint":[56,13,0],"levelId":368,"height":10}}')
Write-Host "Great room south wall: $r"

# Kitchen / Dining divider (x=44, y=0..13)
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[44,0,0],"endPoint":[44,13,0],"levelId":368,"height":10}}')
Write-Host "Kitchen/Dining divider: $r"

# Laundry room: x=50..56, y=0..7
# Laundry west wall (x=50, y=0..7)
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[50,0,0],"endPoint":[50,7,0],"levelId":368,"height":10}}')
Write-Host "Laundry west wall: $r"

# Laundry north wall (y=7, x=50..56)
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[50,7,0],"endPoint":[56,7,0],"levelId":368,"height":10}}')
Write-Host "Laundry north wall: $r"

# ---- FOYER / ENTRY ----
# Foyer at the connection point between bedroom hall and living area
# Entry wall segment: x=32, y=0..26 (divides bedrooms from living)
# But we want an opening for the foyer - let's make a partial wall
# Entry/foyer: x=30..35, y=0..5 area
# Wall from bedroom zone to living zone (x=32, y=5..13) - partial wall leaving foyer open
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[32,5,0],"endPoint":[32,13,0],"levelId":368,"height":10}}')
Write-Host "Foyer/living divider: $r"

# Foyer north wall (y=5, x=30..32) - small wall segment
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[30,5,0],"endPoint":[32,5,0],"levelId":368,"height":10}}')
Write-Host "Foyer north wall: $r"

# ---- ADDITIONAL INTERIOR DETAILS ----

# Hall closet wall (small closet off hallway)
# x=15..17.5, y=23..26 area
$r = Send-Revit('{"method":"createWall","params":{"startPoint":[15,23,0],"endPoint":[15,26,0],"levelId":368,"height":10}}')
Write-Host "Hall closet west: $r"

Write-Host ""
Write-Host "=== CREATING ROOMS ==="

# Room labels at center points
$rooms = @(
    @{name="Garage"; x=16; y=37},
    @{name="Master Bedroom"; x=7.5; y=7.5},
    @{name="Master Bath"; x=5.5; y=18},
    @{name="Master Closet"; x=13; y=18},
    @{name="Hallway"; x=17; y=10},
    @{name="Hall Bath"; x=17; y=19},
    @{name="Bedroom 2"; x=24.5; y=20.5},
    @{name="Bedroom 3"; x=24.5; y=7.5},
    @{name="Great Room"; x=44; y=30},
    @{name="Dining Room"; x=38; y=6.5},
    @{name="Kitchen"; x=47; y=10},
    @{name="Laundry"; x=53; y=3.5}
)

foreach ($rm in $rooms) {
    $json = '{"method":"createRoom","params":{"location":[' + $rm.x + ',' + $rm.y + ',0],"name":"' + $rm.name + '","levelId":' + $levelId + '}}'
    $r = Send-Revit($json)
    Write-Host "$($rm.name): $r"
}

Write-Host ""
Write-Host "=== ZOOM TO FIT ==="
$r = Send-Revit('{"method":"zoomToFit","params":{}}')
Write-Host "Zoom: $r"

$pipe.Close()
Write-Host "DONE"

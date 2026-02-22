$pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", "RevitMCPBridge2026", [System.IO.Pipes.PipeDirection]::InOut)
$pipe.Connect(5000)
$writer = New-Object System.IO.StreamWriter($pipe)
$reader = New-Object System.IO.StreamReader($pipe)
$writer.AutoFlush = $true

function Send-Revit($json) {
    $writer.WriteLine($json)
    $resp = $reader.ReadLine()
    return $resp
}

$levelId = 368
$wallHeight = 10.0

# Track wall IDs for door/window placement
$wallIds = @{}

Write-Host "=== CREATING WALLS ==="

# Floor plan walls from the generated plan (13 walls)
# All coordinates in feet, origin bottom-left

$walls = @(
    # Exterior walls (rectangle perimeter)
    @{name="south"; sx=0; sy=0; ex=44; ey=0},      # South
    @{name="east"; sx=44; sy=0; ex=44; ey=34},      # East
    @{name="north"; sx=44; sy=34; ex=0; ey=34},     # North
    @{name="west"; sx=0; sy=34; ex=0; ey=0},        # West

    # Column dividers (vertical interior walls)
    @{name="master_div"; sx=14; sy=0; ex=14; ey=34},   # Master column divider
    @{name="bed_div"; sx=33; sy=7; ex=33; ey=34},      # Bedroom column divider

    # Service row divider (horizontal)
    @{name="svc_div"; sx=0; sy=7; ex=44; ey=7},        # Service row top

    # Master column interior: master bed / master bath divider
    @{name="mb_div"; sx=0; sy=19; ex=14; ey=19},       # Master bed bottom

    # Bedroom column interiors
    @{name="bed23_div"; sx=33; sy=24; ex=44; ey=24},   # Bed2/Bed3 divider
    @{name="bed3bath_div"; sx=33; sy=14; ex=44; ey=14}, # Bed3/Bath divider

    # Great room interiors (open plan - no walls between L/K/D)
    # Kitchen/Dining divider - SKIP (open plan)
    # Dining/Living divider - SKIP (open plan)

    # Service row interiors
    @{name="svc_hall"; sx=34; sy=0; ex=34; ey=7},      # Hallway/HalfBath divider
    @{name="svc_hb_laundry"; sx=38; sy=0; ex=38; ey=7} # HalfBath/Laundry divider
)

foreach ($w in $walls) {
    $json = '{"method":"createWall","params":{"startPoint":[' + $w.sx + ',' + $w.sy + ',0],"endPoint":[' + $w.ex + ',' + $w.ey + ',0],"levelId":' + $levelId + ',"height":' + $wallHeight + '}}'
    $r = Send-Revit($json)
    Write-Host "$($w.name): $r"

    # Parse wall ID from response
    if ($r -match '"wallId"\s*:\s*(\d+)') {
        $wallIds[$w.name] = [int]$Matches[1]
        Write-Host "  -> Wall ID: $($wallIds[$w.name])"
    }
}

Write-Host ""
Write-Host "=== CREATING DOORS ==="

# Doors from the floor plan (key doors for circulation)
$doors = @(
    # Entry door on south wall
    @{wall="south"; x=7; y=0; z=0; w=3.0; h=6.67},

    # Zone transition: Hallway -> Kitchen (on svc_div wall)
    @{wall="svc_div"; x=24; y=7; z=0; w=2.5; h=6.67},

    # Master Bed -> Master Bath
    @{wall="mb_div"; x=2.25; y=19; z=0; w=2.5; h=6.67},

    # Master column -> Great room (Dining)
    @{wall="master_div"; x=14; y=22.75; z=0; w=2.5; h=6.67},

    # Master column -> Great room (Living)
    @{wall="master_div"; x=14; y=31.75; z=0; w=2.5; h=6.67},

    # Bedroom 2 -> Great room (Living)
    @{wall="bed_div"; x=33; y=31.75; z=0; w=2.5; h=6.67},

    # Bedroom 3 -> Great room (Dining)
    @{wall="bed_div"; x=33; y=21.75; z=0; w=2.5; h=6.67},

    # Bedroom 2 top entry
    @{wall="bed23_div"; x=41.75; y=24; z=0; w=2.5; h=6.67},

    # Bathroom door
    @{wall="bed3bath_div"; x=35.17; y=14; z=0; w=2.33; h=6.67},

    # Entry -> Hallway
    @{wall="master_div"; x=14; y=3.5; z=0; w=2.5; h=6.67},

    # Half Bath door
    @{wall="svc_hall"; x=34; y=2.17; z=0; w=2.33; h=6.67},

    # Laundry door
    @{wall="svc_hb_laundry"; x=38; y=2.17; z=0; w=2.33; h=6.67}
)

foreach ($d in $doors) {
    $wId = $wallIds[$d.wall]
    if ($wId) {
        $json = '{"method":"createDoor","params":{"wallId":' + $wId + ',"location":[' + $d.x + ',' + $d.y + ',' + $d.z + '],"width":' + $d.w + ',"height":' + $d.h + '}}'
        $r = Send-Revit($json)
        Write-Host "Door on $($d.wall): $r"
    } else {
        Write-Host "SKIP door on $($d.wall) - no wall ID"
    }
}

Write-Host ""
Write-Host "=== CREATING WINDOWS ==="

# Windows from the floor plan
$windows = @(
    # Master Bedroom - west wall (2 windows)
    @{wall="west"; x=0; y=29.25; z=0; w=3.0; h=4.5},
    @{wall="west"; x=0; y=23.75; z=0; w=3.0; h=4.5},

    # Master Bath - west wall
    @{wall="west"; x=0; y=14; z=0; w=2.0; h=3.0},

    # Bedroom 2 - east wall
    @{wall="east"; x=44; y=29; z=0; w=3.0; h=4.5},

    # Bedroom 3 - east wall
    @{wall="east"; x=44; y=19; z=0; w=3.0; h=4.5},

    # Bathroom - east wall
    @{wall="east"; x=44; y=10.5; z=0; w=2.0; h=3.0},

    # Living Room - north wall (2 windows)
    @{wall="north"; x=27.25; y=34; z=0; w=3.0; h=5.0},
    @{wall="north"; x=19.75; y=34; z=0; w=3.0; h=5.0}
)

foreach ($win in $windows) {
    $wId = $wallIds[$win.wall]
    if ($wId) {
        $json = '{"method":"createWindow","params":{"wallId":' + $wId + ',"location":[' + $win.x + ',' + $win.y + ',' + $win.z + '],"width":' + $win.w + ',"height":' + $win.h + '}}'
        $r = Send-Revit($json)
        Write-Host "Window on $($win.wall): $r"
    } else {
        Write-Host "SKIP window on $($win.wall) - no wall ID"
    }
}

Write-Host ""
Write-Host "=== CREATING ROOMS ==="

# Room labels at center points
$rooms = @(
    @{name="Master Bedroom"; x=7; y=26.5},
    @{name="Master Bath"; x=7; y=13},
    @{name="Bedroom 2"; x=38.5; y=29},
    @{name="Bedroom 3"; x=38.5; y=19},
    @{name="Bathroom"; x=38.5; y=10.5},
    @{name="Kitchen"; x=23.5; y=11.5},
    @{name="Dining Room"; x=23.5; y=20.5},
    @{name="Living Room"; x=23.5; y=29.5},
    @{name="Entry"; x=7; y=3.5},
    @{name="Hallway"; x=24; y=3.5},
    @{name="Half Bath"; x=36; y=3.5},
    @{name="Laundry"; x=41; y=3.5}
)

foreach ($rm in $rooms) {
    $json = '{"method":"createRoom","params":{"location":[' + $rm.x + ',' + $rm.y + ',0],"name":"' + $rm.name + '","levelId":' + $levelId + '}}'
    $r = Send-Revit($json)
    Write-Host "$($rm.name): $r"
}

Write-Host ""
Write-Host "=== CREATING FLOOR ==="

# Floor slab for the entire footprint
$json = '{"method":"createFloor","params":{"points":[[0,0],[44,0],[44,34],[0,34]],"levelId":' + $levelId + '}}'
$r = Send-Revit($json)
Write-Host "Floor: $r"

Write-Host ""
Write-Host "=== DONE ==="

$pipe.Close()

$pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", "RevitMCPBridge2026", [System.IO.Pipes.PipeDirection]::InOut)
$pipe.Connect(5000)
$writer = New-Object System.IO.StreamWriter($pipe)
$reader = New-Object System.IO.StreamReader($pipe)
$writer.AutoFlush = $true

function Send-Revit($json) {
    $writer.WriteLine($json)
    return $reader.ReadLine()
}

# Get all walls
$r = Send-Revit('{"method":"getWalls","params":{}}')
$walls = $r | ConvertFrom-Json
Write-Host "Found $($walls.wallCount) walls"

# Get all rooms
$r = Send-Revit('{"method":"getRooms","params":{}}')
$rooms = $r | ConvertFrom-Json
Write-Host "Found $($rooms.roomCount) rooms"

# Delete all walls
if ($walls.wallCount -gt 0) {
    $ids = ($walls.walls | ForEach-Object { $_.wallId }) -join ","
    $r = Send-Revit("{`"method`":`"deleteElements`",`"params`":{`"elementIds`":[$ids]}}")
    Write-Host "Delete walls: $r"
}

# Delete all rooms
if ($rooms.roomCount -gt 0) {
    $ids = ($rooms.rooms | ForEach-Object { $_.roomId }) -join ","
    $r = Send-Revit("{`"method`":`"deleteElements`",`"params`":{`"elementIds`":[$ids]}}")
    Write-Host "Delete rooms: $r"
}

$pipe.Close()

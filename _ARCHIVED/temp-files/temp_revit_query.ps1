$pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", "RevitMCPBridge2026", [System.IO.Pipes.PipeDirection]::InOut)
$pipe.Connect(5000)
$writer = New-Object System.IO.StreamWriter($pipe)
$reader = New-Object System.IO.StreamReader($pipe)
$writer.AutoFlush = $true

function Send-Revit($json) {
    $writer.WriteLine($json)
    return $reader.ReadLine()
}

# Get levels
$r = Send-Revit('{"method":"getLevels","params":{}}')
Write-Host "LEVELS: $r"

# Get existing walls
$r = Send-Revit('{"method":"getWalls","params":{}}')
Write-Host "WALLS: $r"

# Get existing doors
$r = Send-Revit('{"method":"getDoors","params":{}}')
Write-Host "DOORS: $r"

# Get existing windows
$r = Send-Revit('{"method":"getWindows","params":{}}')
Write-Host "WINDOWS: $r"

$pipe.Close()

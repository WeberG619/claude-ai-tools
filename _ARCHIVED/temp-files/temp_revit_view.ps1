$pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", "RevitMCPBridge2026", [System.IO.Pipes.PipeDirection]::InOut)
$pipe.Connect(5000)
$writer = New-Object System.IO.StreamWriter($pipe)
$reader = New-Object System.IO.StreamReader($pipe)
$writer.AutoFlush = $true

function Send-Revit($json) {
    $writer.WriteLine($json)
    return $reader.ReadLine()
}

# Try to zoom to fit
$r = Send-Revit('{"method":"zoomToFit","params":{}}')
Write-Host "ZoomToFit: $r"

# Get active view info
$r = Send-Revit('{"method":"getActiveView","params":{}}')
Write-Host "ActiveView: $r"

# Try floor with boundaryPoints
$r = Send-Revit('{"method":"createFloor","params":{"boundaryPoints":[[0,0],[44,0],[44,34],[0,34]],"levelId":368}}')
Write-Host "Floor: $r"

$pipe.Close()

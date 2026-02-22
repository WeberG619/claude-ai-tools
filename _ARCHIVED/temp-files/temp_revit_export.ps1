$pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", "RevitMCPBridge2026", [System.IO.Pipes.PipeDirection]::InOut)
$pipe.Connect(5000)
$writer = New-Object System.IO.StreamWriter($pipe)
$reader = New-Object System.IO.StreamReader($pipe)
$writer.AutoFlush = $true

function Send-Revit($json) {
    $writer.WriteLine($json)
    return $reader.ReadLine()
}

# Try export view image
$r = Send-Revit('{"method":"exportViewImage","params":{"filePath":"D:/_CLAUDE-TOOLS/temp_floorplan.png","width":2000,"height":1600}}')
Write-Host "ExportView: $r"

# Try captureView
$r = Send-Revit('{"method":"captureView","params":{"filePath":"D:/_CLAUDE-TOOLS/temp_floorplan2.png"}}')
Write-Host "CaptureView: $r"

# Try exportImage
$r = Send-Revit('{"method":"exportImage","params":{"filePath":"D:/_CLAUDE-TOOLS/temp_floorplan3.png"}}')
Write-Host "ExportImage: $r"

$pipe.Close()

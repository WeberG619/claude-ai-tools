$pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", "RevitMCPBridge2026", [System.IO.Pipes.PipeDirection]::InOut)
$pipe.Connect(5000)
$writer = New-Object System.IO.StreamWriter($pipe)
$reader = New-Object System.IO.StreamReader($pipe)
$writer.AutoFlush = $true

$writer.WriteLine('{"method":"zoomToFit","params":{}}')
$r = $reader.ReadLine()
Write-Host "ZoomToFit: $r"

$pipe.Close()

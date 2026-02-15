param([string]$cmd)
$pipeName = "RevitMCPBridge2026"
try {
    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    $pipe.Connect(10000)
    $writer = New-Object System.IO.StreamWriter($pipe)
    $reader = New-Object System.IO.StreamReader($pipe)
    $writer.AutoFlush = $true
    $writer.WriteLine($cmd)
    $response = $reader.ReadLine()
    $pipe.Close()
    Write-Output $response
} catch {
    Write-Error $_.Exception.Message
    exit 1
}

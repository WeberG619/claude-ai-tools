param(
    [string]$Method = "ping",
    [string]$Params = "{}"
)

$pipeName = "RevitMCPBridge2026"

try {
    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    $pipe.Connect(5000)

    $writer = New-Object System.IO.StreamWriter($pipe)
    $reader = New-Object System.IO.StreamReader($pipe)

    $json = '{"method": "' + $Method + '", "params": ' + $Params + '}'
    $writer.WriteLine($json)
    $writer.Flush()

    $response = $reader.ReadLine()
    Write-Output $response

    $pipe.Close()
} catch {
    Write-Output ('{"error": "' + $_.Exception.Message + '"}')
}

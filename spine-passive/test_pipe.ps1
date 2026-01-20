# Test Revit MCP Bridge Named Pipe Connection

$pipeName = "RevitMCPBridge2026"

Write-Host "Testing connection to $pipeName..." -ForegroundColor Yellow

try {
    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    $pipe.Connect(10000)  # 10 second timeout

    $writer = New-Object System.IO.StreamWriter($pipe)
    $writer.AutoFlush = $true
    $reader = New-Object System.IO.StreamReader($pipe)

    $request = '{"method":"ping"}'
    Write-Host "Sending: $request"
    $writer.WriteLine($request)

    $response = $reader.ReadLine()
    Write-Host "Received: $response" -ForegroundColor Green

    $pipe.Dispose()
    Write-Host "SUCCESS! Bridge is responding." -ForegroundColor Green

} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

# Test Revit MCP Bridge Connection
# Run this in PowerShell to check if the bridge is responding

Write-Host "Testing RevitMCPBridge2026..." -ForegroundColor Yellow

$pipeName = "RevitMCPBridge2026"
$pipe = $null

try {
    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream('.', $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    $pipe.Connect(5000)  # 5 second timeout

    $writer = New-Object System.IO.StreamWriter($pipe)
    $writer.AutoFlush = $true
    $reader = New-Object System.IO.StreamReader($pipe)

    # Send ping command
    $writer.WriteLine('{"method":"ping"}')
    $response = $reader.ReadLine()

    Write-Host "SUCCESS! Bridge is responding:" -ForegroundColor Green
    Write-Host $response

} catch {
    Write-Host "FAILED to connect to RevitMCPBridge2026" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Trying RevitMCPBridge2025..." -ForegroundColor Yellow

    try {
        $pipe2 = New-Object System.IO.Pipes.NamedPipeClientStream('.', 'RevitMCPBridge2025', [System.IO.Pipes.PipeDirection]::InOut)
        $pipe2.Connect(5000)

        $writer2 = New-Object System.IO.StreamWriter($pipe2)
        $writer2.AutoFlush = $true
        $reader2 = New-Object System.IO.StreamReader($pipe2)

        $writer2.WriteLine('{"method":"ping"}')
        $response2 = $reader2.ReadLine()

        Write-Host "SUCCESS! Revit 2025 Bridge is responding:" -ForegroundColor Green
        Write-Host $response2

        $pipe2.Dispose()

    } catch {
        Write-Host "FAILED to connect to RevitMCPBridge2025" -ForegroundColor Red
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Write-Host "TROUBLESHOOTING:" -ForegroundColor Cyan
        Write-Host "1. Open Revit 2025 or 2026"
        Write-Host "2. Look for 'MCP Bridge' ribbon tab"
        Write-Host "3. Click 'Start Bridge' button"
        Write-Host "4. Run this script again"
    }

} finally {
    if ($pipe) { $pipe.Dispose() }
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

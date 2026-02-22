$pipeName = "RevitMCPBridge2026"
$rooms = Get-Content "D:\_CLAUDE-TOOLS\l7_final.json" | ConvertFrom-Json

Write-Host "Updating $($rooms.Count) remaining rooms..." -ForegroundColor Cyan

foreach ($room in $rooms) {
    $newNumber = "7" + $room.number.PadLeft(2, "0")
    Write-Host "Room $($room.roomId): $($room.number) -> $newNumber" -NoNewline

    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream('.', $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    try {
        $pipe.Connect(5000)
        $writer = New-Object System.IO.StreamWriter($pipe)
        $reader = New-Object System.IO.StreamReader($pipe)

        $json = '{"method":"modifyRoomProperties","params":{"roomId":"' + $room.roomId + '","number":"' + $newNumber + '"}}'
        $writer.WriteLine($json)
        $writer.Flush()
        $response = $reader.ReadLine() | ConvertFrom-Json
        $pipe.Close()

        if ($response.success) {
            Write-Host " OK" -ForegroundColor Green
        } else {
            Write-Host " FAIL: $($response.error)" -ForegroundColor Red
        }
    } catch {
        Write-Host " ERROR: $($_.Exception.Message)" -ForegroundColor Red
    }
    Start-Sleep -Milliseconds 100
}

Write-Host "`nDone!" -ForegroundColor Cyan

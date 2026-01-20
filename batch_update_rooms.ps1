$pipeName = "RevitMCPBridge2026"
$rooms = Get-Content "D:\_CLAUDE-TOOLS\l7_retry.json" | ConvertFrom-Json

Write-Host "Updating $($rooms.Count) rooms on Level 7..." -ForegroundColor Cyan

$updated = 0
$failed = 0

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
            $updated++
        } else {
            Write-Host " FAIL: $($response.error)" -ForegroundColor Red
            $failed++
        }
    } catch {
        Write-Host " ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }

    Start-Sleep -Milliseconds 50
}

Write-Host "`n=== Complete ===" -ForegroundColor Cyan
Write-Host "Updated: $updated" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })

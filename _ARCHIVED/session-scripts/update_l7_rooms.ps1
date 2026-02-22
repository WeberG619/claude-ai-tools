$pipeName = "RevitMCPBridge2026"

function Send-RevitCommand {
    param([string]$json)
    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream('.', $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    try {
        $pipe.Connect(5000)
        $writer = New-Object System.IO.StreamWriter($pipe)
        $reader = New-Object System.IO.StreamReader($pipe)
        $writer.WriteLine($json)
        $writer.Flush()
        $response = $reader.ReadLine()
        $pipe.Close()
        return $response | ConvertFrom-Json
    } catch {
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

Write-Host "Getting rooms on Level 7..." -ForegroundColor Cyan
$roomsResponse = Send-RevitCommand '{"method":"getRooms","params":{}}'

$level7Rooms = $roomsResponse.rooms | Where-Object { $_.level -eq "L7" }
Write-Host "Found $($level7Rooms.Count) rooms on Level 7" -ForegroundColor Green

$updated = 0
$skipped = 0

foreach ($room in $level7Rooms) {
    $oldNumber = $room.number

    # Skip if already starts with 7 and is 3+ digits (like 701, 745)
    if ($oldNumber -match "^7\d{2}") {
        Write-Host "Skipping room $($room.roomId): $oldNumber (already correct)" -ForegroundColor Yellow
        $skipped++
        continue
    }

    # Create new number: prepend 7 to make it 7XX format
    $newNumber = "7" + $oldNumber.PadLeft(2, "0")

    Write-Host "Updating room $($room.roomId) [$($room.name)]: $oldNumber -> $newNumber" -ForegroundColor White

    $updateJson = '{"method":"modifyRoomProperties","params":{"roomId":"' + $room.roomId + '","number":"' + $newNumber + '"}}'

    $result = Send-RevitCommand $updateJson

    if ($result.success) {
        $updated++
        Write-Host "  Done" -ForegroundColor Green
    } else {
        Write-Host "  Failed: $($result.error)" -ForegroundColor Red
    }

    Start-Sleep -Milliseconds 50
}

Write-Host ""
Write-Host "=== Complete ===" -ForegroundColor Cyan
Write-Host "Updated: $updated rooms" -ForegroundColor Green
Write-Host "Skipped: $skipped rooms (already correct)" -ForegroundColor Yellow

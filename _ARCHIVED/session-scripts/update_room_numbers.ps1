# Update room numbers on Level 7 from XX to 7XX
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

# Get all rooms
Write-Host "Getting all rooms..." -ForegroundColor Cyan
$roomsResponse = Send-RevitCommand '{"method":"getRooms","params":{}}'

if (-not $roomsResponse.success) {
    Write-Host "Failed to get rooms: $($roomsResponse.error)" -ForegroundColor Red
    exit 1
}

# Filter for Level 7 (levelId: 1304034)
$level7Rooms = $roomsResponse.rooms | Where-Object { $_.levelId -eq 1304034 }
Write-Host "Found $($level7Rooms.Count) rooms on Level 7" -ForegroundColor Green

# Update each room number
$updated = 0
$failed = 0

foreach ($room in $level7Rooms) {
    $oldNumber = $room.number

    # Skip if already starts with 7
    if ($oldNumber -match "^7\d{2}") {
        Write-Host "Room $($room.roomId) already has correct number: $oldNumber" -ForegroundColor Yellow
        continue
    }

    # Create new number by prepending 7
    $newNumber = "7" + $oldNumber.PadLeft(2, '0')

    Write-Host "Updating room $($room.roomId): $oldNumber -> $newNumber" -ForegroundColor White

    $updateJson = @{
        method = "modifyRoomProperties"
        params = @{
            roomId = $room.roomId.ToString()
            number = $newNumber
        }
    } | ConvertTo-Json -Compress

    $result = Send-RevitCommand $updateJson

    if ($result.success) {
        $updated++
        Write-Host "  Success!" -ForegroundColor Green
    } else {
        $failed++
        Write-Host "  Failed: $($result.error)" -ForegroundColor Red
    }

    # Small delay to not overwhelm Revit
    Start-Sleep -Milliseconds 100
}

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Updated: $updated rooms" -ForegroundColor Green
Write-Host "Failed: $failed rooms" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })

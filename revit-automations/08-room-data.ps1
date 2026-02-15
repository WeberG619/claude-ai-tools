# Room Data Export
# Extracts room schedule data (name, number, area, level)
# Usage: .\08-room-data.ps1 -Version 2026|2025 [-ExportJson]

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("2025", "2026")]
    [string]$Version,

    [switch]$ExportJson
)

$pipeName = "RevitMCPBridge$Version"

function Invoke-RevitMCP {
    param([string]$Method, [hashtable]$Params = @{})

    $pipe = New-Object System.IO.Pipes.NamedPipeClientStream(".", $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    $pipe.Connect(10000)
    $writer = New-Object System.IO.StreamWriter($pipe)
    $reader = New-Object System.IO.StreamReader($pipe)
    $writer.AutoFlush = $true

    $request = @{ method = $Method; params = $Params } | ConvertTo-Json -Compress
    $writer.WriteLine($request)
    $response = $reader.ReadLine() | ConvertFrom-Json
    $pipe.Close()

    return $response
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "ROOM DATA EXPORT - Revit $Version" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Get rooms
$roomsResponse = Invoke-RevitMCP -Method "getElements" -Params @{ category = "Rooms" }
if (-not $roomsResponse.success) {
    Write-Host "ERROR: Failed to get rooms" -ForegroundColor Red
    exit 1
}

$rooms = $roomsResponse.result.elements
Write-Host "Found $($rooms.Count) rooms" -ForegroundColor Gray
Write-Host ""

# Group by level
$byLevel = @{}
$totalArea = 0
foreach ($room in $rooms) {
    $level = if ($room.level) { $room.level } else { "Unplaced" }
    if (-not $byLevel.ContainsKey($level)) {
        $byLevel[$level] = @()
    }
    $byLevel[$level] += $room
    if ($room.area) { $totalArea += $room.area }
}

Write-Host "ROOMS BY LEVEL" -ForegroundColor Yellow
Write-Host "-" * 50

foreach ($level in $byLevel.Keys | Sort-Object) {
    $levelRooms = $byLevel[$level]
    $levelArea = 0
    foreach ($r in $levelRooms) { if ($r.area) { $levelArea += $r.area } }
    $areaStr = if ($levelArea -gt 0) { "{0:N0} SF" -f $levelArea } else { "N/A" }

    Write-Host ""
    Write-Host "$level ($($levelRooms.Count) rooms, $areaStr)" -ForegroundColor Cyan

    foreach ($room in $levelRooms | Sort-Object name) {
        $roomNum = if ($room.number) { $room.number } else { "---" }
        $roomName = if ($room.name) { $room.name.Substring(0, [Math]::Min(35, $room.name.Length)) } else { "Unnamed" }
        $roomArea = if ($room.area -and $room.area -gt 0) { "{0:N0} SF" -f $room.area } else { "---" }
        Write-Host "  $($roomNum.PadRight(6)) $($roomName.PadRight(37)) $roomArea" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "-" * 50
Write-Host "TOTAL: $($rooms.Count) rooms, $("{0:N0}" -f $totalArea) SF" -ForegroundColor Green

# Export to JSON if requested
if ($ExportJson) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $jsonPath = "D:\_CLAUDE-TOOLS\revit-automations\rooms_$timestamp.json"

    $export = @{
        exportDate = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        revitVersion = $Version
        roomCount = $rooms.Count
        totalArea = $totalArea
        byLevel = $byLevel.Keys | ForEach-Object {
            @{
                level = $_
                rooms = $byLevel[$_]
            }
        }
    }

    $export | ConvertTo-Json -Depth 5 | Out-File -FilePath $jsonPath -Encoding UTF8
    Write-Host ""
    Write-Host "Exported to: $jsonPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan

# Verify room sizes and clean up

function Send-MCPRequest {
    param([string]$method, [hashtable]$params)
    try {
        $pipeClient = New-Object System.IO.Pipes.NamedPipeClientStream(".", "RevitMCPBridge2026", [System.IO.Pipes.PipeDirection]::InOut)
        $pipeClient.Connect(5000)
        $reader = New-Object System.IO.StreamReader($pipeClient)
        $writer = New-Object System.IO.StreamWriter($pipeClient)
        $writer.AutoFlush = $true
        $request = @{ method = $method; params = $params } | ConvertTo-Json -Depth 10 -Compress
        $writer.WriteLine($request)
        $response = $reader.ReadLine()
        $pipeClient.Close()
        return $response | ConvertFrom-Json
    }
    catch { return @{ success = $false; error = $_.Exception.Message } }
}

# Calculate approximate room areas from wall coordinates
Write-Host "ROOM SIZE VERIFICATION"
Write-Host "======================"
Write-Host ""

# Based on my wall coordinates:
$rooms = @(
    @{ Name = "BEDROOM-3"; Width = 14; Height = 14; Target = 140 },
    @{ Name = "BEDROOM-2"; Width = 14; Height = 14; Target = 142 },
    @{ Name = "FAMILY/DINING"; Width = 21.83; Height = 14; Target = 244 },
    @{ Name = "KITCHEN"; Width = 8.83; Height = 14; Target = 200 },
    @{ Name = "LIVING"; Width = 8.83; Height = 14; Target = 210 },
    @{ Name = "MASTER BEDROOM"; Width = 8.5; Height = 10; Target = 221 },
    @{ Name = "MASTER BATH"; Width = 8.5; Height = 7; Target = 70 },
    @{ Name = "BATH-3"; Width = 5.33; Height = 6; Target = 32 },
    @{ Name = "BATH-2"; Width = 8.67; Height = 8; Target = 42 },
    @{ Name = "HALL-1"; Width = 13; Height = 4; Target = 38 },
    @{ Name = "GARAGE"; Width = 12; Height = 24; Target = 543 }
)

Write-Host "Room               | Calculated | Target | Match"
Write-Host "-------------------+------------+--------+------"

$totalCalc = 0
$totalTarget = 0

foreach ($room in $rooms) {
    $area = [math]::Round($room.Width * $room.Height, 0)
    $totalCalc += $area
    $totalTarget += $room.Target
    $match = if ([math]::Abs($area - $room.Target) -le 30) { "OK" } else { "OFF" }
    Write-Host ("{0,-18} | {1,10} | {2,6} | {3}" -f $room.Name, "$area SF", "$($room.Target) SF", $match)
}

Write-Host "-------------------+------------+--------+------"
Write-Host ("{0,-18} | {1,10} | {2,6} |" -f "TOTAL (no garage)", "$($totalCalc - 288) SF", "$($totalTarget - 543) SF")

Write-Host ""
Write-Host "Note: Dimensions need adjustment to match target areas exactly."

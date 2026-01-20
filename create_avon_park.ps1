# Create Avon Park walls from Claude's floor plan analysis

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

# Get the correct level
$levels = Send-MCPRequest -method "getLevels" -params @{}
$levelId = 30
foreach ($lvl in $levels.levels) {
    if ($lvl.elevation -eq 0) {
        $levelId = $lvl.levelId
        Write-Host "Using level: $($lvl.name) (ID: $levelId)"
        break
    }
}

# First delete the previous test walls (optional - skip if you want to keep them)
# We'll just create the new walls offset from the old ones

# Load wall definitions
$walls = Get-Content "D:\_CLAUDE-TOOLS\avon_park_claude_walls.json" -Raw | ConvertFrom-Json

Write-Host "`nCreating $($walls.Count) walls from floor plan analysis..."
Write-Host "=================================================="

$created = 0
$failed = 0

foreach ($wall in $walls) {
    # Offset walls to avoid overlap with previous test (add 100' offset)
    $offsetX = 100
    $offsetY = 100
    
    $params = @{
        startPoint = @(($wall.start[0] + $offsetX), ($wall.start[1] + $offsetY), 0)
        endPoint = @(($wall.end[0] + $offsetX), ($wall.end[1] + $offsetY), 0)
        levelId = $levelId
        height = 10
    }
    
    $result = Send-MCPRequest -method "createWall" -params $params
    
    if ($result.success) {
        $created++
        $length = [math]::Sqrt([math]::Pow($wall.end[0] - $wall.start[0], 2) + [math]::Pow($wall.end[1] - $wall.start[1], 2))
        Write-Host "  OK: $($wall.desc) ($([math]::Round($length, 1)) ft)"
    } else {
        $failed++
        Write-Host "  FAIL: $($wall.desc) - $($result.error)"
    }
}

Write-Host "`n=================================================="
Write-Host "Created: $created walls"
Write-Host "Failed: $failed walls"
Write-Host "=================================================="

# Zoom to fit to see all walls
$zoom = Send-MCPRequest -method "zoomToFit" -params @{}
Write-Host "`nZoomed to fit: $($zoom.success)"

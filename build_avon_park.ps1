# Build Avon Park Floor Plan with correct wall thicknesses

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

Write-Host "=========================================="
Write-Host "AVON PARK SINGLE FAMILY RESIDENCE"
Write-Host "1700 W Sheffield Rd, Avon Park, FL 33825"
Write-Host "=========================================="

# Get level
$levels = Send-MCPRequest -method "getLevels" -params @{}
$levelId = ($levels.levels | Where-Object { $_.elevation -eq 0 } | Select-Object -First 1).levelId
if (-not $levelId) { $levelId = $levels.levels[0].levelId }
Write-Host "Using Level ID: $levelId"

# Get wall types
$types = Send-MCPRequest -method "getWallTypes" -params @{}
$exterior8in = ($types.wallTypes | Where-Object { $_.name -eq "Generic - 8`"" }).name
$interior4in = ($types.wallTypes | Where-Object { $_.name -eq "Generic - 4`"" }).name

if (-not $exterior8in) { $exterior8in = "Generic - 8`"" }
if (-not $interior4in) { $interior4in = "Generic - 4`"" }

Write-Host "Exterior Wall Type: $exterior8in"
Write-Host "Interior Wall Type: $interior4in"

# Load wall data
$data = Get-Content "D:\_CLAUDE-TOOLS\avon_park_accurate.json" -Raw | ConvertFrom-Json

Write-Host "`n--- Creating Exterior Walls (8 inch CMU) ---"
$extCreated = 0

foreach ($wall in $data.exterior_walls) {
    $params = @{
        startPoint = @($wall.start[0], $wall.start[1], 0)
        endPoint = @($wall.end[0], $wall.end[1], 0)
        levelId = $levelId
        height = 10
        wallType = $exterior8in
    }
    
    $result = Send-MCPRequest -method "createWall" -params $params
    
    if ($result.success) {
        $extCreated++
        $len = [math]::Round([math]::Sqrt([math]::Pow($wall.end[0] - $wall.start[0], 2) + [math]::Pow($wall.end[1] - $wall.start[1], 2)), 1)
        Write-Host "  OK: $($wall.desc) ($len ft)"
    } else {
        Write-Host "  FAIL: $($wall.desc) - $($result.error)"
    }
}

Write-Host "`n--- Creating Interior Walls (4 inch Stud) ---"
$intCreated = 0

foreach ($wall in $data.interior_walls) {
    $params = @{
        startPoint = @($wall.start[0], $wall.start[1], 0)
        endPoint = @($wall.end[0], $wall.end[1], 0)
        levelId = $levelId
        height = 10
        wallType = $interior4in
    }
    
    $result = Send-MCPRequest -method "createWall" -params $params
    
    if ($result.success) {
        $intCreated++
        $len = [math]::Round([math]::Sqrt([math]::Pow($wall.end[0] - $wall.start[0], 2) + [math]::Pow($wall.end[1] - $wall.start[1], 2)), 1)
        Write-Host "  OK: $($wall.desc) ($len ft)"
    } else {
        Write-Host "  FAIL: $($wall.desc) - $($result.error)"
    }
}

Write-Host "`n=========================================="
Write-Host "SUMMARY"
Write-Host "=========================================="
Write-Host "Exterior Walls Created: $extCreated / $($data.exterior_walls.Count)"
Write-Host "Interior Walls Created: $intCreated / $($data.interior_walls.Count)"
Write-Host "Total Walls: $($extCreated + $intCreated)"
Write-Host "=========================================="

# Zoom to fit
$zoom = Send-MCPRequest -method "zoomToFit" -params @{}
Write-Host "`nView zoomed to fit: $($zoom.success)"

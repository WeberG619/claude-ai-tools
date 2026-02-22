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

# Get all walls in the model
Write-Host "Getting all walls..."
$walls = Send-MCPRequest -method "getElements" -params @{ category = "Walls" }

if ($walls.success) {
    Write-Host "Found $($walls.elements.Count) walls"
    
    # Delete walls that are far from origin (our test walls)
    $deleted = 0
    foreach ($wall in $walls.elements) {
        # Get element location
        $loc = Send-MCPRequest -method "getElementLocation" -params @{ elementId = $wall.id }
        if ($loc.success) {
            # If wall is beyond 50 feet from origin, delete it (our test walls were at 100+ offset)
            $x = $loc.location.x
            $y = $loc.location.y
            if ($x -gt 50 -or $y -gt 50) {
                $del = Send-MCPRequest -method "deleteElements" -params @{ elementIds = @($wall.id) }
                if ($del.success) {
                    $deleted++
                }
            }
        }
    }
    Write-Host "Deleted $deleted test walls"
} else {
    Write-Host "Could not get walls: $($walls.error)"
}

# Get available wall types
Write-Host "`nGetting wall types..."
$types = Send-MCPRequest -method "getWallTypes" -params @{}

if ($types.success) {
    Write-Host "Available wall types:"
    foreach ($wt in $types.wallTypes) {
        Write-Host "  - $($wt.name) (ID: $($wt.id), Width: $($wt.width))"
    }
} else {
    Write-Host "Could not get wall types: $($types.error)"
}

# Create walls in Revit via MCP named pipe

function Send-MCPRequest {
    param([string]$method, [hashtable]$params)
    
    try {
        $pipeClient = New-Object System.IO.Pipes.NamedPipeClientStream(".", "RevitMCPBridge2026", [System.IO.Pipes.PipeDirection]::InOut)
        $pipeClient.Connect(5000)
        
        $reader = New-Object System.IO.StreamReader($pipeClient)
        $writer = New-Object System.IO.StreamWriter($pipeClient)
        $writer.AutoFlush = $true
        
        # Use "params" not "parameters"!
        $request = @{
            method = $method
            params = $params
        } | ConvertTo-Json -Depth 10 -Compress
        
        $writer.WriteLine($request)
        $response = $reader.ReadLine()
        
        $pipeClient.Close()
        return $response | ConvertFrom-Json
    }
    catch {
        return @{ success = $false; error = $_.Exception.Message }
    }
}

# Get levels first
Write-Host "Getting levels from Revit..."
$levels = Send-MCPRequest -method "getLevels" -params @{}

if (-not $levels.success) {
    Write-Host "ERROR: $($levels.error)"
    exit 1
}

$levelId = $levels.levels[0].levelId
foreach ($lvl in $levels.levels) {
    if ($lvl.elevation -eq 0) {
        $levelId = $lvl.levelId
        Write-Host "Using level: $($lvl.name) (ID: $levelId)"
        break
    }
}

# Test with one wall - startPoint as array
Write-Host "`nTesting createWall..."

$params = @{
    startPoint = @(0, 0, 0)
    endPoint = @(10, 0, 0)
    levelId = $levelId
    height = 10
}

$result = Send-MCPRequest -method "createWall" -params $params

if ($result.success) {
    Write-Host "SUCCESS: Wall created (ID: $($result.elementId))"
    
    # Now create all the extracted walls
    Write-Host "`nNow creating extracted walls..."
    $wallsJson = Get-Content "D:\_CLAUDE-TOOLS\avon_park_walls.json" -Raw | ConvertFrom-Json
    
    $created = 0
    $failed = 0
    
    foreach ($wall in $wallsJson) {
        $wp = @{
            startPoint = @($wall.params.startPoint[0], $wall.params.startPoint[1], 0)
            endPoint = @($wall.params.endPoint[0], $wall.params.endPoint[1], 0)
            levelId = $levelId
            height = $wall.params.height
        }
        
        $r = Send-MCPRequest -method "createWall" -params $wp
        
        if ($r.success) {
            $created++
            Write-Host "  Created: $($wall.length_feet) ft wall"
        } else {
            $failed++
            Write-Host "  FAILED: $($r.error)"
        }
    }
    
    Write-Host "`n=========================================="
    Write-Host "Summary: Created $($created + 1) walls, Failed $failed"
    Write-Host "=========================================="
    
} else {
    Write-Host "FAILED: $($result.error)"
}

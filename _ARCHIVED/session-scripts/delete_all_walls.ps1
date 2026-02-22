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

Write-Host "Getting all walls to delete..."
$walls = Send-MCPRequest -method "getElements" -params @{ category = "Walls" }

if ($walls.success -and $walls.elements.Count -gt 0) {
    Write-Host "Found $($walls.elements.Count) walls"
    
    # Get IDs of walls that are far from origin (our test walls)
    $wallIds = @()
    foreach ($w in $walls.elements) {
        $wallIds += $w.id
    }
    
    if ($wallIds.Count -gt 0) {
        Write-Host "Deleting $($wallIds.Count) walls..."
        $result = Send-MCPRequest -method "deleteElements" -params @{ elementIds = $wallIds }
        if ($result.success) {
            Write-Host "SUCCESS: Deleted $($result.deletedCount) walls"
        } else {
            Write-Host "FAILED: $($result.error)"
        }
    }
} else {
    Write-Host "No walls found or error: $($walls.error)"
}

# Zoom to fit
$zoom = Send-MCPRequest -method "zoomToFit" -params @{}

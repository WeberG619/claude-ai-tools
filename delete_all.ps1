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

# Get all walls
$walls = Send-MCPRequest -method "getWalls" -params @{}
Write-Host "Found $($walls.wallCount) walls to delete"

if ($walls.wallCount -gt 0) {
    $wallIds = $walls.walls | ForEach-Object { $_.wallId }
    Write-Host "Deleting all walls..."
    $result = Send-MCPRequest -method "deleteElements" -params @{ elementIds = $wallIds }
    Write-Host "Delete result: $($result | ConvertTo-Json -Compress)"
}

# Zoom to fit
Send-MCPRequest -method "zoomToFit" -params @{} | Out-Null
Write-Host "Done - view reset"

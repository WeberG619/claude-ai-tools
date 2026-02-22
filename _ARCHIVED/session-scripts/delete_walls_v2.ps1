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

# Try getElementsByCategory
Write-Host "Trying getElementsByCategory..."
$walls = Send-MCPRequest -method "getElementsByCategory" -params @{ categoryName = "Walls" }
Write-Host "Result: $($walls | ConvertTo-Json -Depth 2 -Compress)"

if (-not $walls.success) {
    # Try getAllWalls
    Write-Host "`nTrying getAllWalls..."
    $walls = Send-MCPRequest -method "getAllWalls" -params @{}
    Write-Host "Result: $($walls | ConvertTo-Json -Depth 2 -Compress)"
}

if (-not $walls.success) {
    # Try getWalls
    Write-Host "`nTrying getWalls..."
    $walls = Send-MCPRequest -method "getWalls" -params @{}
    Write-Host "Result: $($walls | ConvertTo-Json -Depth 2 -Compress)"
}

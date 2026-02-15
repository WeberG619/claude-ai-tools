param(
    [string]$TabId = "89B0415052310BA062E416C50B679C82",
    [string]$JavaScript = ""
)

$wsUrl = "ws://localhost:9222/devtools/page/$TabId"

Add-Type -AssemblyName System.Net.Http

$ws = New-Object System.Net.WebSockets.ClientWebSocket
$ct = [System.Threading.CancellationToken]::None

try {
    $connectTask = $ws.ConnectAsync([Uri]$wsUrl, $ct)
    $connectTask.GetAwaiter().GetResult()

    $cmd = @{
        id = 1
        method = "Runtime.evaluate"
        params = @{
            expression = $JavaScript
            returnByValue = $true
            awaitPromise = $true
        }
    } | ConvertTo-Json -Depth 5 -Compress

    $bytes = [System.Text.Encoding]::UTF8.GetBytes($cmd)
    $segment = [System.ArraySegment[byte]]::new($bytes)
    $sendTask = $ws.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $ct)
    $sendTask.GetAwaiter().GetResult()

    $buf = [byte[]]::new(65536)
    $seg = [System.ArraySegment[byte]]::new($buf)
    $recvTask = $ws.ReceiveAsync($seg, $ct)
    $recvTask.GetAwaiter().GetResult()
    $response = [System.Text.Encoding]::UTF8.GetString($buf, 0, $recvTask.Result.Count)
    Write-Output $response
}
catch {
    Write-Error $_.Exception.Message
}
finally {
    if ($ws.State -eq 'Open') {
        $closeTask = $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $ct)
        $closeTask.GetAwaiter().GetResult()
    }
    $ws.Dispose()
}

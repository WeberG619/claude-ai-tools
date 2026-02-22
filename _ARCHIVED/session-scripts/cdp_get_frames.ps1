param([string]$TabId)

$wsUrl = "ws://localhost:9222/devtools/page/$TabId"
$ws = New-Object System.Net.WebSockets.ClientWebSocket
$ct = [System.Threading.CancellationToken]::None
$ws.ConnectAsync([Uri]$wsUrl, $ct).Wait()

# Send Page.getFrameTree
$msg = '{"id":1,"method":"Page.getFrameTree","params":{}}'
$bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
$segment = New-Object System.ArraySegment[byte] -ArgumentList @(,$bytes)
$ws.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $ct).Wait()

# Receive
$buf = New-Object byte[] 65536
$result = ""
do {
    $recv = $ws.ReceiveAsync((New-Object System.ArraySegment[byte] -ArgumentList @(,$buf)), $ct).Result
    $result += [System.Text.Encoding]::UTF8.GetString($buf, 0, $recv.Count)
} while (-not $recv.EndOfMessage)

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $ct).Wait()
Write-Output $result
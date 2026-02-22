$tabId = "8461E928A850B6B41FEBCC18CE8B5E98"
$wsUrl = "ws://localhost:9222/devtools/page/$tabId"
$ws = New-Object System.Net.WebSockets.ClientWebSocket
$cts = New-Object System.Threading.CancellationTokenSource(20000)
$ws.ConnectAsync([Uri]$wsUrl, $cts.Token).Wait()

$script:id = 0

function Invoke-CDP($method, $params) {
    $script:id++
    $msg = @{ id = $script:id; method = $method; params = $params } | ConvertTo-Json -Depth 10 -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $seg = New-Object System.ArraySegment[byte] $bytes, 0, $bytes.Length
    $ws.SendAsync($seg, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $cts.Token).Wait()
    $buf = New-Object byte[] 65536
    $rseg = New-Object System.ArraySegment[byte] $buf, 0, $buf.Length
    $result = $ws.ReceiveAsync($rseg, $cts.Token).Result
    return [System.Text.Encoding]::UTF8.GetString($buf, 0, $result.Count) | ConvertFrom-Json
}

# Click "Create API key" button
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "var btn = Array.from(document.querySelectorAll('button')).find(function(b) { return b.textContent.includes('Create API key'); }); if(btn) { btn.click(); 'clicked'; } else { 'not found'; }" }
Write-Output "Create button: $($r.result.result.value)"

Start-Sleep -Seconds 2

# Check for modal/dialog
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "document.body.innerText.substring(0, 800)" }
Write-Output "Page text: $($r.result.result.value)"

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $cts.Token).Wait()

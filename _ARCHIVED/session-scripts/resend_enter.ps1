$tabId = "8461E928A850B6B41FEBCC18CE8B5E98"
$wsUrl = "ws://localhost:9222/devtools/page/$tabId"
$ws = New-Object System.Net.WebSockets.ClientWebSocket
$cts = New-Object System.Threading.CancellationTokenSource(15000)
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

# Check current email value
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "document.querySelector('#email') ? document.querySelector('#email').value : 'no email field'" }
Write-Output "Current email: $($r.result.result.value)"

# Focus the email field
Invoke-CDP "Runtime.evaluate" @{ expression = "document.querySelector('#email').focus()" } | Out-Null
Start-Sleep -Milliseconds 200

# Press Enter to submit
Invoke-CDP "Input.dispatchKeyEvent" @{ type = "rawKeyDown"; key = "Enter"; code = "Enter"; windowsVirtualKeyCode = 13 } | Out-Null
Invoke-CDP "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "Enter"; code = "Enter"; windowsVirtualKeyCode = 13 } | Out-Null

Start-Sleep -Seconds 5
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "document.title + ' | ' + window.location.href + ' | ' + document.body.innerText.substring(0,500)" }
Write-Output "After Enter: $($r.result.result.value)"

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $cts.Token).Wait()

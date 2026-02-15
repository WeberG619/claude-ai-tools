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

function Type-InField($selector, $text) {
    Invoke-CDP "Runtime.evaluate" @{ expression = "document.querySelector(`"$selector`").focus()" } | Out-Null
    Start-Sleep -Milliseconds 200
    Invoke-CDP "Input.dispatchKeyEvent" @{ type = "rawKeyDown"; key = "a"; code = "KeyA"; windowsVirtualKeyCode = 65; modifiers = 2 } | Out-Null
    Invoke-CDP "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "a"; code = "KeyA"; windowsVirtualKeyCode = 65 } | Out-Null
    Start-Sleep -Milliseconds 50
    Invoke-CDP "Input.dispatchKeyEvent" @{ type = "rawKeyDown"; key = "Delete"; code = "Delete"; windowsVirtualKeyCode = 46 } | Out-Null
    Invoke-CDP "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "Delete"; code = "Delete"; windowsVirtualKeyCode = 46 } | Out-Null
    Start-Sleep -Milliseconds 50
    Invoke-CDP "Input.insertText" @{ text = $text } | Out-Null
    Start-Sleep -Milliseconds 200
    $r = Invoke-CDP "Runtime.evaluate" @{ expression = "document.querySelector(`"$selector`").value.length" }
    return $r.result.result.value
}

# Type password (17 chars, well above 12 minimum)
$pwd = "B1m0ps!Resend2026"
$len1 = Type-InField "#password" $pwd
Write-Output "Password field: $len1 chars"

$len2 = Type-InField "#confirm-password" $pwd
Write-Output "Confirm field: $len2 chars"

Start-Sleep -Milliseconds 500

# Submit via requestSubmit
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "var f=document.querySelector('form');if(f){f.requestSubmit();'submitted'}else{'no form'}" }
Write-Output "Submit: $($r.result.result.value)"

Start-Sleep -Seconds 8
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "document.title + ' | ' + window.location.href + ' | ' + document.body.innerText.substring(0,500)" }
Write-Output "After: $($r.result.result.value)"

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $cts.Token).Wait()

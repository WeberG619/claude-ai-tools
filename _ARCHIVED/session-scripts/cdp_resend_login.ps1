param([string]$TabId)

$wsUrl = "ws://localhost:9222/devtools/page/$TabId"

function Send-CDPCommand($ws, $id, $method, $params) {
    $msg = @{ id = $id; method = $method; params = $params } | ConvertTo-Json -Depth 5 -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $segment = New-Object System.ArraySegment[byte] -ArgumentList @(,$bytes)
    $ct = [System.Threading.CancellationToken]::None
    $ws.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $ct).Wait()

    $buf = New-Object byte[] 65536
    $result = ""
    do {
        $recv = $ws.ReceiveAsync((New-Object System.ArraySegment[byte] -ArgumentList @(,$buf)), $ct).Result
        $result += [System.Text.Encoding]::UTF8.GetString($buf, 0, $recv.Count)
    } while (-not $recv.EndOfMessage)
    return $result
}

$ws = New-Object System.Net.WebSockets.ClientWebSocket
$ct = [System.Threading.CancellationToken]::None
$ws.ConnectAsync([Uri]$wsUrl, $ct).Wait()

$id = 1

# Focus and fill email
$r = Send-CDPCommand $ws $id "Runtime.evaluate" @{ expression = "document.getElementById('email').focus(); document.getElementById('email').select(); 'ok'" }
$id++
Start-Sleep -Milliseconds 300
$r = Send-CDPCommand $ws $id "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "a"; code = "KeyA"; modifiers = 2 }
$id++
$r = Send-CDPCommand $ws $id "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "a"; code = "KeyA"; modifiers = 2 }
$id++
$r = Send-CDPCommand $ws $id "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "Delete"; code = "Delete" }
$id++
$r = Send-CDPCommand $ws $id "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "Delete"; code = "Delete" }
$id++
Start-Sleep -Milliseconds 200
$r = Send-CDPCommand $ws $id "Input.insertText" @{ text = "weberg619@gmail.com" }
$id++
Start-Sleep -Milliseconds 300

# Focus and fill password
$r = Send-CDPCommand $ws $id "Runtime.evaluate" @{ expression = "document.getElementById('password').focus(); document.getElementById('password').select(); 'ok'" }
$id++
Start-Sleep -Milliseconds 300
$r = Send-CDPCommand $ws $id "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "a"; code = "KeyA"; modifiers = 2 }
$id++
$r = Send-CDPCommand $ws $id "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "a"; code = "KeyA"; modifiers = 2 }
$id++
$r = Send-CDPCommand $ws $id "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "Delete"; code = "Delete" }
$id++
$r = Send-CDPCommand $ws $id "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "Delete"; code = "Delete" }
$id++
Start-Sleep -Milliseconds 200
$r = Send-CDPCommand $ws $id "Input.insertText" @{ text = "B1m0ps!Resend2026" }
$id++
Start-Sleep -Milliseconds 300

# Verify
$r = Send-CDPCommand $ws $id "Runtime.evaluate" @{ expression = "'email=' + document.getElementById('email').value + ' pass_len=' + document.getElementById('password').value.length" }
Write-Output "Verify: $r"
$id++

# Click Log In button
$r = Send-CDPCommand $ws $id "Runtime.evaluate" @{ expression = "var btns = Array.from(document.querySelectorAll('button')); var loginBtn = btns.find(function(b) { return b.textContent.trim() === 'Log In'; }); if (loginBtn) { loginBtn.click(); 'clicked Log In'; } else { 'Log In not found: ' + btns.map(function(b){return b.textContent.trim()}).join(', '); }" }
Write-Output "Login: $r"
$id++

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $ct).Wait()
Write-Output "Done"
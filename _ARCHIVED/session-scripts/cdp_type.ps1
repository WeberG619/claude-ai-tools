param(
    [string]$TabId,
    [string]$Selector,
    [string]$Text
)

$wsUrl = "ws://localhost:9222/devtools/page/$TabId"
$ws = New-Object System.Net.WebSockets.ClientWebSocket
$cts = New-Object System.Threading.CancellationTokenSource(10000)
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
    $json = [System.Text.Encoding]::UTF8.GetString($buf, 0, $result.Count)
    return $json | ConvertFrom-Json
}

# Focus the element
Invoke-CDP "Runtime.evaluate" @{ expression = "document.querySelector('$Selector').focus()" } | Out-Null
Start-Sleep -Milliseconds 100

# Select all existing text
Invoke-CDP "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "a"; code = "KeyA"; windowsVirtualKeyCode = 65; nativeVirtualKeyCode = 65; modifiers = 2 } | Out-Null
Invoke-CDP "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "a"; code = "KeyA"; windowsVirtualKeyCode = 65; nativeVirtualKeyCode = 65 } | Out-Null
Start-Sleep -Milliseconds 50

# Delete selected text
Invoke-CDP "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "Backspace"; code = "Backspace"; windowsVirtualKeyCode = 8; nativeVirtualKeyCode = 8 } | Out-Null
Invoke-CDP "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "Backspace"; code = "Backspace"; windowsVirtualKeyCode = 8; nativeVirtualKeyCode = 8 } | Out-Null
Start-Sleep -Milliseconds 50

# Insert text all at once
Invoke-CDP "Input.insertText" @{ text = $Text } | Out-Null
Start-Sleep -Milliseconds 100

# Verify
$result = Invoke-CDP "Runtime.evaluate" @{ expression = "document.querySelector('$Selector').value" }
Write-Output $result.result.result.value

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $cts.Token).Wait()

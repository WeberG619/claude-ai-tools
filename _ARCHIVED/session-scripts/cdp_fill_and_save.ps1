param(
    [string]$TabId,
    [string]$HostValue,
    [string]$DataValue,
    [string]$RecordType = "TXT",
    [string]$PriorityValue = ""
)

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

$cmdId = 1

# Focus the Host field and clear it
$js = "document.getElementById(':r5:').focus(); document.getElementById(':r5:').select(); 'focused host'"
$r = Send-CDPCommand $ws $cmdId "Runtime.evaluate" @{ expression = $js }
Write-Output "Focus host: $r"
$cmdId++
Start-Sleep -Milliseconds 300

# Clear existing value
$r = Send-CDPCommand $ws $cmdId "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "a"; code = "KeyA"; modifiers = 2 }
$cmdId++
Start-Sleep -Milliseconds 100
$r = Send-CDPCommand $ws $cmdId "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "a"; code = "KeyA"; modifiers = 2 }
$cmdId++
Start-Sleep -Milliseconds 100
$r = Send-CDPCommand $ws $cmdId "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "Delete"; code = "Delete" }
$cmdId++
Start-Sleep -Milliseconds 100
$r = Send-CDPCommand $ws $cmdId "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "Delete"; code = "Delete" }
$cmdId++
Start-Sleep -Milliseconds 300

# Type the host value
$r = Send-CDPCommand $ws $cmdId "Input.insertText" @{ text = $HostValue }
Write-Output "Typed host: $r"
$cmdId++
Start-Sleep -Milliseconds 500

# If priority is needed, fill it
if ($PriorityValue -ne "") {
    $js = "document.getElementById(':r7:').focus(); document.getElementById(':r7:').select(); 'focused priority'"
    $r = Send-CDPCommand $ws $cmdId "Runtime.evaluate" @{ expression = $js }
    Write-Output "Focus priority: $r"
    $cmdId++
    Start-Sleep -Milliseconds 300

    $r = Send-CDPCommand $ws $cmdId "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "a"; code = "KeyA"; modifiers = 2 }
    $cmdId++
    Start-Sleep -Milliseconds 100
    $r = Send-CDPCommand $ws $cmdId "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "a"; code = "KeyA"; modifiers = 2 }
    $cmdId++
    Start-Sleep -Milliseconds 100
    $r = Send-CDPCommand $ws $cmdId "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "Delete"; code = "Delete" }
    $cmdId++
    Start-Sleep -Milliseconds 100
    $r = Send-CDPCommand $ws $cmdId "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "Delete"; code = "Delete" }
    $cmdId++
    Start-Sleep -Milliseconds 300

    $r = Send-CDPCommand $ws $cmdId "Input.insertText" @{ text = $PriorityValue }
    Write-Output "Typed priority: $r"
    $cmdId++
    Start-Sleep -Milliseconds 500
}

# Focus the Data field and clear it
$js = "document.getElementById(':r9:').focus(); document.getElementById(':r9:').select(); 'focused data'"
$r = Send-CDPCommand $ws $cmdId "Runtime.evaluate" @{ expression = $js }
Write-Output "Focus data: $r"
$cmdId++
Start-Sleep -Milliseconds 300

$r = Send-CDPCommand $ws $cmdId "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "a"; code = "KeyA"; modifiers = 2 }
$cmdId++
Start-Sleep -Milliseconds 100
$r = Send-CDPCommand $ws $cmdId "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "a"; code = "KeyA"; modifiers = 2 }
$cmdId++
Start-Sleep -Milliseconds 100
$r = Send-CDPCommand $ws $cmdId "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "Delete"; code = "Delete" }
$cmdId++
Start-Sleep -Milliseconds 100
$r = Send-CDPCommand $ws $cmdId "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "Delete"; code = "Delete" }
$cmdId++
Start-Sleep -Milliseconds 300

# Type the data value
$r = Send-CDPCommand $ws $cmdId "Input.insertText" @{ text = $DataValue }
Write-Output "Typed data: $r"
$cmdId++
Start-Sleep -Milliseconds 500

# Verify values
$js = "var h = document.getElementById(':r5:'); var d = document.getElementById(':r9:'); 'Host=' + h.value + ' Data=' + d.value.substring(0,50)"
$r = Send-CDPCommand $ws $cmdId "Runtime.evaluate" @{ expression = $js }
Write-Output "Verify: $r"
$cmdId++

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $ct).Wait()
Write-Output "Done"
param(
    [string]$TabId,
    [string]$HostId,
    [string]$HostValue,
    [string]$PriorityId = "",
    [string]$PriorityValue = "",
    [string]$DataId,
    [string]$DataValue
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

function Fill-Field($ws, [ref]$cmdId, $fieldId, $value) {
    $js = "document.getElementById('$fieldId').focus(); document.getElementById('$fieldId').select(); 'focused $fieldId'"
    $r = Send-CDPCommand $ws $cmdId.Value "Runtime.evaluate" @{ expression = $js }
    $cmdId.Value++
    Start-Sleep -Milliseconds 300

    $r = Send-CDPCommand $ws $cmdId.Value "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "a"; code = "KeyA"; modifiers = 2 }
    $cmdId.Value++
    $r = Send-CDPCommand $ws $cmdId.Value "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "a"; code = "KeyA"; modifiers = 2 }
    $cmdId.Value++
    Start-Sleep -Milliseconds 100
    $r = Send-CDPCommand $ws $cmdId.Value "Input.dispatchKeyEvent" @{ type = "keyDown"; key = "Delete"; code = "Delete" }
    $cmdId.Value++
    $r = Send-CDPCommand $ws $cmdId.Value "Input.dispatchKeyEvent" @{ type = "keyUp"; key = "Delete"; code = "Delete" }
    $cmdId.Value++
    Start-Sleep -Milliseconds 200

    $r = Send-CDPCommand $ws $cmdId.Value "Input.insertText" @{ text = $value }
    $cmdId.Value++
    Start-Sleep -Milliseconds 300
    Write-Output "Filled $fieldId = $value"
}

$ws = New-Object System.Net.WebSockets.ClientWebSocket
$ct = [System.Threading.CancellationToken]::None
$ws.ConnectAsync([Uri]$wsUrl, $ct).Wait()

$cmdId = [ref]1

# Fill Host
Fill-Field $ws $cmdId $HostId $HostValue

# Fill Priority if provided
if ($PriorityId -ne "" -and $PriorityValue -ne "") {
    Fill-Field $ws $cmdId $PriorityId $PriorityValue
}

# Fill Data
Fill-Field $ws $cmdId $DataId $DataValue

# Verify
$js = "var h = document.getElementById('$HostId'); var d = document.getElementById('$DataId'); 'Host=' + h.value + ' Data=' + d.value.substring(0,60)"
$r = Send-CDPCommand $ws $cmdId.Value "Runtime.evaluate" @{ expression = $js }
Write-Output "Verify: $r"

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $ct).Wait()
Write-Output "Done"
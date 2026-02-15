param(
    [string]$TabId,
    [string]$JsFile
)

$js = (Get-Content $JsFile -Raw) -replace "`r`n", " " -replace "`n", " " -replace "  +", " "
$wsUrl = "ws://localhost:9222/devtools/page/$TabId"
$ws = New-Object System.Net.WebSockets.ClientWebSocket
$cts = New-Object System.Threading.CancellationTokenSource(10000)
$ws.ConnectAsync([Uri]$wsUrl, $cts.Token).Wait()

$msg = @{
    id = 1
    method = "Runtime.evaluate"
    params = @{
        expression = $js
        returnByValue = $true
    }
} | ConvertTo-Json -Depth 5 -Compress

$bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
$seg = New-Object System.ArraySegment[byte] $bytes, 0, $bytes.Length
$ws.SendAsync($seg, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $cts.Token).Wait()

$buf = New-Object byte[] 131072
$rseg = New-Object System.ArraySegment[byte] $buf, 0, $buf.Length
$result = $ws.ReceiveAsync($rseg, $cts.Token).Result
$json = [System.Text.Encoding]::UTF8.GetString($buf, 0, $result.Count) | ConvertFrom-Json

if ($json.result.result.value) {
    Write-Output $json.result.result.value
} elseif ($json.result.exceptionDetails) {
    Write-Output ("ERROR: " + $json.result.exceptionDetails.exception.description)
} else {
    Write-Output ($json | ConvertTo-Json -Depth 5)
}

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $cts.Token).Wait()

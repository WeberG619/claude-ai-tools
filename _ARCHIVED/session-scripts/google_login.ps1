$tabId = "BAA9D7DBAA57CE8EE19F7BA5FA806A84"
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

# Find the email input
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "var input = document.querySelector('input[type=email]') || document.querySelector('#identifierId'); if(input) { input.focus(); 'focused ' + input.id; } else { 'no input found'; }" }
Write-Output "Input: $($r.result.result.value)"

Start-Sleep -Milliseconds 200
Invoke-CDP "Input.insertText" @{ text = "weber@bimopsstudio.com" } | Out-Null
Start-Sleep -Milliseconds 300

# Click Next
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "var btn = document.querySelector('#identifierNext button') || Array.from(document.querySelectorAll('button')).find(function(b){return b.textContent.includes('Next')}); if(btn){btn.click();'clicked Next'}else{'no Next button'}" }
Write-Output "Next: $($r.result.result.value)"

Start-Sleep -Seconds 5
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "document.title + ' | ' + window.location.href.substring(0,80) + ' | ' + document.body.innerText.substring(0,400)" }
Write-Output "After: $($r.result.result.value)"

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $cts.Token).Wait()

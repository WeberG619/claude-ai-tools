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

# Focus the name input
Invoke-CDP "Runtime.evaluate" @{ expression = "document.querySelector('#name').focus()" } | Out-Null
Start-Sleep -Milliseconds 200
Invoke-CDP "Input.insertText" @{ text = "bim-ops-studio" } | Out-Null
Start-Sleep -Milliseconds 300

# Verify
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "document.querySelector('#name').value" }
Write-Output "Name value: $($r.result.result.value)"

# Find the Add button in the dialog/modal - use startsWith match
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "var btns = Array.from(document.querySelectorAll('button')); var addBtn = btns.find(function(b) { return b.textContent.trim().indexOf('Add') === 0 && b.textContent.trim().indexOf('Create') === -1; }); if(addBtn) { addBtn.click(); 'clicked'; } else { 'not found'; }" }
Write-Output "Add: $($r.result.result.value)"

Start-Sleep -Seconds 5
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "document.body.innerText.substring(0, 1500)" }
Write-Output "After: $($r.result.result.value)"

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $cts.Token).Wait()

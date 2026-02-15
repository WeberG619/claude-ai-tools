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

# Click "Add domain" button
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "var btn = Array.from(document.querySelectorAll('button')).find(function(b) { return b.textContent.trim().indexOf('Add domain') === 0; }); if(btn) { btn.click(); 'clicked'; } else { 'not found'; }" }
Write-Output "Add domain button: $($r.result.result.value)"

Start-Sleep -Seconds 2

# Check modal
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "var inputs = Array.from(document.querySelectorAll('input')); inputs.map(function(e,i){return i+':'+e.id+':'+e.type+':'+e.placeholder}).join('|')" }
Write-Output "Inputs: $($r.result.result.value)"

# Find domain input and fill it
Invoke-CDP "Runtime.evaluate" @{ expression = "var input = document.querySelector('input[placeholder*=domain],input[placeholder*=example],input#domain'); if(input) input.focus(); else { var inputs = Array.from(document.querySelectorAll('input')); var empty = inputs.find(function(i){return !i.value && i.type !== 'hidden'}); if(empty) empty.focus(); }" } | Out-Null
Start-Sleep -Milliseconds 200
Invoke-CDP "Input.insertText" @{ text = "bimopsstudio.com" } | Out-Null
Start-Sleep -Milliseconds 300

# Check modal text for buttons
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "document.body.innerText.substring(document.body.innerText.indexOf('Add domain'), document.body.innerText.indexOf('Add domain') + 500)" }
Write-Output "Modal: $($r.result.result.value)"

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $cts.Token).Wait()

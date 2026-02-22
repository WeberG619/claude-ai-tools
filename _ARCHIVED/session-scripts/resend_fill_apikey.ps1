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

# Find the name input in the modal - look for the input that's empty and in a dialog
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "var inputs = Array.from(document.querySelectorAll('input')); inputs.map(function(e,i){return i+':'+e.id+':'+e.type+':'+e.name+':'+e.placeholder+':'+e.value}).join('|')" }
Write-Output "Inputs: $($r.result.result.value)"

# Focus and type in the name field (likely the first empty text input)
Invoke-CDP "Runtime.evaluate" @{ expression = "var inputs = Array.from(document.querySelectorAll('input[type=text],input:not([type])')); var nameInput = inputs.find(function(i){return !i.value}); if(nameInput) nameInput.focus();" } | Out-Null
Start-Sleep -Milliseconds 200
Invoke-CDP "Input.insertText" @{ text = "bim-ops-studio" } | Out-Null
Start-Sleep -Milliseconds 300

# Click Add button
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "var btns = Array.from(document.querySelectorAll('button')); var addBtn = btns.find(function(b) { return b.textContent.trim() === 'Add'; }); if(addBtn) { addBtn.click(); 'clicked Add'; } else { 'not found: ' + btns.map(function(b){return b.textContent.trim()}).join('|'); }" }
Write-Output "Add button: $($r.result.result.value)"

Start-Sleep -Seconds 4
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "document.body.innerText.substring(0, 1000)" }
Write-Output "After: $($r.result.result.value)"

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $cts.Token).Wait()

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

# List inputs
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "Array.from(document.querySelectorAll('input')).map(function(e,i){return i+':id='+e.id+',name='+e.name+',type='+e.type+',placeholder='+e.placeholder+',value='+e.value}).join('|')" }
Write-Output "Inputs: $($r.result.result.value)"

# Focus the domain name input
Invoke-CDP "Runtime.evaluate" @{ expression = "var input = document.querySelector('input#name') || document.querySelector('input[name=name]') || document.querySelectorAll('input')[1]; if(input) input.focus();" } | Out-Null
Start-Sleep -Milliseconds 200
Invoke-CDP "Input.insertText" @{ text = "bimopsstudio.com" } | Out-Null
Start-Sleep -Milliseconds 300

# Check value
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "Array.from(document.querySelectorAll('input')).map(function(e){return e.id+':'+e.value}).join('|')" }
Write-Output "Values: $($r.result.result.value)"

# Click Add Domain submit button
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "var form = document.querySelector('form'); if(form) { form.requestSubmit(); 'submitted'; } else { var btn = Array.from(document.querySelectorAll('button')).find(function(b){return b.textContent.trim().indexOf('Add Domain')===0}); if(btn){btn.click();'clicked'}else{'no form or button'} }" }
Write-Output "Submit: $($r.result.result.value)"

Start-Sleep -Seconds 5
$r = Invoke-CDP "Runtime.evaluate" @{ expression = "document.title + ' | ' + window.location.href + ' | ' + document.body.innerText.substring(0, 1200)" }
Write-Output "After: $($r.result.result.value)"

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "", $cts.Token).Wait()

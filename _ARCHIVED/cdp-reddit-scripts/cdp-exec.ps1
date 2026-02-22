# CDP JavaScript Executor - runs JS in the active Edge/Chrome tab via CDP
# Usage: powershell -File cdp-exec.ps1 -js "document.title"
# Usage: powershell -File cdp-exec.ps1 -js "document.title" -port 9222
param(
    [Parameter(Mandatory=$true)][string]$js,
    [int]$port = 9222,
    [string]$url = ""
)

# If URL specified, navigate first
if ($url) {
    $targets = (Invoke-WebRequest -Uri "http://127.0.0.1:$port/json" -UseBasicParsing).Content | ConvertFrom-Json
    $page = $targets | Where-Object { $_.type -eq "page" } | Select-Object -First 1
    if ($page) {
        $wsUrl = $page.webSocketDebuggerUrl
        # Navigate via CDP
        $navPayload = @{id=1; method="Page.navigate"; params=@{url=$url}} | ConvertTo-Json -Compress
        # Use Python for WebSocket since PS doesn't have native support
        $pyScript = @"
import asyncio, websockets, json, sys
async def main():
    async with websockets.connect('$wsUrl') as ws:
        await ws.send('$navPayload')
        r = await ws.recv()
        print(r)
asyncio.run(main())
"@
        python -c $pyScript 2>$null
        Start-Sleep -Seconds 2
    }
}

# Get page target
$targets = (Invoke-WebRequest -Uri "http://127.0.0.1:$port/json" -UseBasicParsing).Content | ConvertFrom-Json
$page = $targets | Where-Object { $_.type -eq "page" } | Select-Object -First 1

if (-not $page) {
    Write-Error "No page target found"
    exit 1
}

$wsUrl = $page.webSocketDebuggerUrl

# Escape the JS for JSON
$escapedJs = $js.Replace('\', '\\').Replace('"', '\"').Replace("`n", '\n').Replace("`r", '')

$payload = "{`"id`":1,`"method`":`"Runtime.evaluate`",`"params`":{`"expression`":`"$escapedJs`",`"returnByValue`":true}}"

# Use Python for WebSocket communication
$pyScript = @"
import asyncio, websockets, json, sys
async def main():
    try:
        async with websockets.connect('$wsUrl') as ws:
            await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": """$($js.Replace('"', '\"'))""", "returnByValue": True}}))
            result = json.loads(await ws.recv())
            if 'result' in result and 'result' in result['result']:
                val = result['result']['result'].get('value', result['result']['result'].get('description', ''))
                print(val)
            else:
                print(json.dumps(result))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
asyncio.run(main())
"@

python -c $pyScript

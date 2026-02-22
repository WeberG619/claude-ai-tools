"""CDP JavaScript Executor - runs JS in Edge/Chrome via WebSocket"""
import asyncio
import json
import sys
import urllib.request

def get_ws_url(port=9222):
    """Get WebSocket URL for the first page target"""
    url = f"http://127.0.0.1:{port}/json"
    with urllib.request.urlopen(url, timeout=5) as resp:
        targets = json.loads(resp.read().decode())
    for t in targets:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("No page target found")

async def run_js(js_code, port=9222):
    """Execute JavaScript and return the result"""
    import websockets
    ws_url = get_ws_url(port)
    async with websockets.connect(ws_url) as ws:
        msg = json.dumps({
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {"expression": js_code, "returnByValue": True}
        })
        await ws.send(msg)
        result = json.loads(await ws.recv())
        if "result" in result and "result" in result["result"]:
            val = result["result"]["result"]
            if "value" in val:
                return val["value"]
            return val.get("description", str(val))
        return json.dumps(result)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cdp-run.py <javascript>")
        sys.exit(1)

    js = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9222

    result = asyncio.run(run_js(js, port))
    print(result)

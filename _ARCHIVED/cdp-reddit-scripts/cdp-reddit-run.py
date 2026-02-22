"""CDP Runner targeting the Reddit tab specifically"""
import asyncio
import json
import sys
import urllib.request

def get_reddit_ws_url(port=9222):
    url = f"http://127.0.0.1:{port}/json"
    with urllib.request.urlopen(url, timeout=5) as resp:
        targets = json.loads(resp.read().decode())
    for t in targets:
        if t.get("type") == "page" and "reddit" in t.get("url", "").lower():
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("No Reddit page target found")

async def run_js(js_code, port=9222):
    import websockets
    ws_url = get_reddit_ws_url(port)
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
        print("Usage: python cdp-reddit-run.py <js_file> [port]")
        sys.exit(1)

    js_file = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9222

    with open(js_file, 'r', encoding='utf-8') as f:
        js_code = f.read()

    result = asyncio.run(run_js(js_code, port))
    print(result)

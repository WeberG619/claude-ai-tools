"""Take screenshot of Reddit page via CDP"""
import asyncio
import json
import urllib.request
import base64

def get_reddit_ws_url(port=9222):
    url = f"http://127.0.0.1:{port}/json"
    with urllib.request.urlopen(url, timeout=5) as resp:
        targets = json.loads(resp.read().decode())
    for t in targets:
        if t.get("type") == "page" and "reddit" in t.get("url", "").lower():
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("No Reddit page target found")

async def main():
    import websockets
    ws_url = get_reddit_ws_url()
    msg_id = 1

    async with websockets.connect(ws_url, max_size=10*1024*1024) as ws:
        async def send_cdp(method, params=None):
            nonlocal msg_id
            msg = {"id": msg_id, "method": method}
            if params:
                msg["params"] = params
            msg_id += 1
            await ws.send(json.dumps(msg))
            while True:
                result = json.loads(await ws.recv())
                if "id" in result and result["id"] == msg_id - 1:
                    return result

        await send_cdp("Page.bringToFront")
        await send_cdp("Runtime.evaluate", {"expression": "window.scrollTo(0, 0); 'ok';"})
        await asyncio.sleep(0.3)

        result = await send_cdp("Page.captureScreenshot", {"format": "png"})
        img_data = base64.b64decode(result["result"]["data"])
        with open(r"D:\_CLAUDE-TOOLS\reddit-screenshot.png", "wb") as f:
            f.write(img_data)
        print("Screenshot saved")

asyncio.run(main())

"""Focus page and take screenshot via CDP"""
import asyncio
import json
import sys
import urllib.request
import base64

def get_ws_url(port=9222):
    url = f"http://127.0.0.1:{port}/json"
    with urllib.request.urlopen(url, timeout=5) as resp:
        targets = json.loads(resp.read().decode())
    for t in targets:
        if t.get("type") == "page" and "reddit" in t.get("url", "").lower():
            return t["webSocketDebuggerUrl"]
    # Fallback to first page
    for t in targets:
        if t.get("type") == "page":
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("No page target found")

async def main():
    import websockets
    ws_url = get_ws_url()
    msg_id = 1

    async with websockets.connect(ws_url) as ws:
        async def send_cdp(method, params=None):
            nonlocal msg_id
            msg = {"id": msg_id, "method": method}
            if params:
                msg["params"] = params
            msg_id += 1
            await ws.send(json.dumps(msg))
            result = json.loads(await ws.recv())
            return result

        # Bring to front
        await send_cdp("Page.bringToFront")
        await asyncio.sleep(0.5)

        # Scroll title into view
        scroll_js = """
        var titleComp = document.querySelector('faceplate-textarea-input[name="title"]');
        if (titleComp) titleComp.scrollIntoView({block: 'start'});
        'scrolled';
        """
        await send_cdp("Runtime.evaluate", {"expression": scroll_js})
        await asyncio.sleep(0.3)

        # Take screenshot
        result = await send_cdp("Page.captureScreenshot", {"format": "png"})
        img_data = base64.b64decode(result["result"]["data"])

        output = sys.argv[1] if len(sys.argv) > 1 else r"D:\_CLAUDE-TOOLS\reddit-screenshot.png"
        with open(output, "wb") as f:
            f.write(img_data)
        print(f"Screenshot saved to {output}")

asyncio.run(main())

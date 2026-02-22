"""Click the 'Add flair and tags' button via CDP mouse event"""
import asyncio
import json
import urllib.request

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

        # Get the position of "Add flair and tags" button
        pos_js = """
        (function() {
            // Find by text content
            var allEls = document.querySelectorAll('*');
            for (var i = 0; i < allEls.length; i++) {
                var text = allEls[i].textContent.trim();
                if (text === 'Add flair and tags*' || text === 'Add flair and tags') {
                    // Make sure it's a leaf-level element (not a parent containing many children)
                    if (allEls[i].children.length <= 3) {
                        var rect = allEls[i].getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            return JSON.stringify({
                                x: rect.x + rect.width/2,
                                y: rect.y + rect.height/2,
                                w: rect.width,
                                h: rect.height,
                                tag: allEls[i].tagName,
                                text: text
                            });
                        }
                    }
                }
            }
            return JSON.stringify({error: 'not found'});
        })()
        """
        r = await send_cdp("Runtime.evaluate", {"expression": pos_js, "returnByValue": True})
        pos = json.loads(r["result"]["result"]["value"])
        print(f"Flair button: {pos}")

        if "error" in pos:
            print("Error: element not found")
            return

        # Click using CDP mouse events
        x, y = int(pos["x"]), int(pos["y"])
        await send_cdp("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x, "y": y,
            "button": "left", "clickCount": 1
        })
        await send_cdp("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x, "y": y,
            "button": "left", "clickCount": 1
        })

        await asyncio.sleep(1)

        # Check what appeared
        check_js = """
        (function() {
            // Check for dialog/modal
            var dialogs = document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="Modal"]');
            var visible = [];
            dialogs.forEach(function(d) {
                if (d.offsetHeight > 0) {
                    visible.push({tag: d.tagName, text: d.textContent.trim().substring(0, 200)});
                }
            });

            // Check shadow roots for dialogs
            var customs = document.querySelectorAll('*');
            customs.forEach(function(c) {
                if (c.shadowRoot) {
                    var dlg = c.shadowRoot.querySelectorAll('[role="dialog"], [class*="modal"]');
                    dlg.forEach(function(d) {
                        if (d.offsetHeight > 0) {
                            visible.push({parent: c.tagName, tag: d.tagName, text: d.textContent.trim().substring(0, 200)});
                        }
                    });
                }
            });

            // Check for flair options
            var flairModal = document.querySelector('r-post-flairs-modal');
            if (flairModal && flairModal.shadowRoot) {
                var items = flairModal.shadowRoot.querySelectorAll('button, [role="radio"], [role="option"], label, li');
                var flairOptions = [];
                items.forEach(function(item) {
                    if (item.textContent.trim().length > 0 && item.textContent.trim().length < 60) {
                        flairOptions.push(item.textContent.trim());
                    }
                });
                return JSON.stringify({dialogs: visible, flairOptions: flairOptions});
            }

            return JSON.stringify({dialogs: visible, flairModal: !!flairModal});
        })()
        """
        r = await send_cdp("Runtime.evaluate", {"expression": check_js, "returnByValue": True})
        print(f"After click: {r['result']['result']['value']}")

asyncio.run(main())

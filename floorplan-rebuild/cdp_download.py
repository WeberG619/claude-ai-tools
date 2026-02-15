"""Download a floor plan image via Chrome DevTools Protocol."""
import json
import time
import base64
import sys
import os

# Try websocket-client first, fallback to websockets
try:
    import websocket
    HAS_WS = True
except ImportError:
    HAS_WS = False

if not HAS_WS:
    print("Installing websocket-client...")
    os.system(f"{sys.executable} -m pip install websocket-client -q")
    import websocket

CDP_HOST = "127.0.0.1"
CDP_PORT = 9222
SAVE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_tabs():
    import urllib.request
    url = f"http://{CDP_HOST}:{CDP_PORT}/json/list"
    resp = urllib.request.urlopen(url, timeout=5)
    return json.loads(resp.read())

def create_tab():
    import urllib.request
    url = f"http://{CDP_HOST}:{CDP_PORT}/json/new?about:blank"
    req = urllib.request.Request(url, method="PUT")
    resp = urllib.request.urlopen(req, timeout=5)
    return json.loads(resp.read())

msg_id = 0
def send_cmd(ws, method, params=None):
    global msg_id
    msg_id += 1
    msg = {"id": msg_id, "method": method}
    if params:
        msg["params"] = params
    ws.send(json.dumps(msg))
    while True:
        resp = json.loads(ws.recv())
        if resp.get("id") == msg_id:
            return resp

def main():
    # Create a new tab
    print("Creating CDP tab...")
    tab = create_tab()
    ws_url = tab["webSocketDebuggerUrl"]
    print(f"Tab: {tab['id']}")

    # Connect
    ws = websocket.create_connection(ws_url, timeout=30)
    print("Connected to CDP")

    # Navigate to Google Images
    search_url = "https://www.google.com/search?q=simple+small+house+floor+plan+with+dimensions+architecture&tbm=isch"
    print(f"Navigating to Google Images...")
    send_cmd(ws, "Page.navigate", {"url": search_url})
    time.sleep(4)

    # Click on first substantial image to get full-size URL
    # First, get thumbnail info
    js = """
    (() => {
        const imgs = Array.from(document.querySelectorAll('img'));
        const good = imgs.filter(i => i.naturalWidth > 100 && i.naturalHeight > 100 && i.src.startsWith('http'));
        return JSON.stringify(good.slice(0, 5).map(i => ({
            src: i.src.substring(0, 300),
            alt: (i.alt || '').substring(0, 80),
            w: i.naturalWidth,
            h: i.naturalHeight
        })));
    })()
    """
    resp = send_cmd(ws, "Runtime.evaluate", {"expression": js, "returnByValue": True})
    images = json.loads(resp["result"]["result"]["value"])
    print(f"Found {len(images)} images on Google Images")

    if not images:
        print("No images found. Trying direct URL...")
        # Fallback: navigate directly to a known floor plan image
        target_url = "https://www.houseplans.net/uploads/plans/28702/elevations/28702-rendering.jpg"
    else:
        # Use the first good image
        target_url = images[0]["src"]
        print(f"Using: {images[0]['alt']} ({images[0]['w']}x{images[0]['h']})")

    # Use fetch API in browser to download image as base64
    print(f"Fetching image via browser fetch...")
    fetch_js = f"""
    (async () => {{
        try {{
            const resp = await fetch("{target_url}");
            const blob = await resp.blob();
            return new Promise((resolve) => {{
                const reader = new FileReader();
                reader.onloadend = () => resolve(reader.result);
                reader.readAsDataURL(blob);
            }});
        }} catch(e) {{
            return "ERROR: " + e.message;
        }}
    }})()
    """
    resp = send_cmd(ws, "Runtime.evaluate", {
        "expression": fetch_js,
        "returnByValue": True,
        "awaitPromise": True,
    })

    data_url = resp.get("result", {}).get("result", {}).get("value", "")

    if data_url.startswith("ERROR:"):
        print(f"Fetch failed: {data_url}")
        # Fallback: just screenshot the page
        print("Falling back to page screenshot...")
        send_cmd(ws, "Page.navigate", {"url": target_url})
        time.sleep(3)
        resp = send_cmd(ws, "Page.captureScreenshot", {"format": "png"})
        b64_data = resp["result"]["data"]
        img_bytes = base64.b64decode(b64_data)
        save_path = os.path.join(SAVE_DIR, "downloaded_floorplan.png")
        with open(save_path, "wb") as f:
            f.write(img_bytes)
        print(f"Screenshot saved: {save_path} ({len(img_bytes)} bytes)")
    elif data_url.startswith("data:"):
        # Extract base64 from data URL
        header, b64_data = data_url.split(",", 1)
        img_bytes = base64.b64decode(b64_data)

        # Determine extension
        ext = "jpg"
        if "png" in header:
            ext = "png"
        elif "webp" in header:
            ext = "webp"

        save_path = os.path.join(SAVE_DIR, f"downloaded_floorplan.{ext}")
        with open(save_path, "wb") as f:
            f.write(img_bytes)
        print(f"Image saved: {save_path} ({len(img_bytes)} bytes)")
    else:
        print(f"Unexpected response: {data_url[:200]}")

    # Close tab
    import urllib.request
    req = urllib.request.Request(
        f"http://{CDP_HOST}:{CDP_PORT}/json/close/{tab['id']}",
        method="GET"
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except:
        pass

    ws.close()
    print("Done!")

if __name__ == "__main__":
    main()

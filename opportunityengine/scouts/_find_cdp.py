"""Find active Chrome CDP port."""
import urllib.request
import json

for port in range(9222, 9230):
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=3)
        data = json.loads(r.read())
        print(f"CDP ACTIVE on port {port}")
        print(f"  Browser: {data.get('Browser', '?')}")
        print(f"  WS URL: {data.get('webSocketDebuggerUrl', '?')}")

        # List tabs
        r2 = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=3)
        tabs = json.loads(r2.read())
        print(f"  Tabs: {len(tabs)}")
        for t in tabs[:5]:
            print(f"    - {t.get('title', '?')[:60]} | {t.get('url', '?')[:60]}")
        break
    except Exception:
        pass
else:
    print("No CDP found on ports 9222-9229")

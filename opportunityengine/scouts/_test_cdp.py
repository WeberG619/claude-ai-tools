"""Test CDP connectivity on multiple ports."""
import urllib.request
import json

for port in [9222, 9223, 9224, 9225, 9226]:
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=3)
        data = json.loads(r.read())
        browser = data.get("Browser", "unknown")
        ws = data.get("webSocketDebuggerUrl", "none")
        print(f"Port {port}: {browser}")
        print(f"  WS: {ws}")
    except Exception as e:
        pass

# Also try Playwright direct
try:
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    for port in [9222, 9223]:
        try:
            browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}", timeout=5000)
            print(f"Playwright CDP on {port}: Connected! {len(browser.contexts)} contexts")
            for ctx in browser.contexts:
                for page in ctx.pages[:3]:
                    print(f"  Tab: {page.url[:80]}")
            break
        except Exception as e:
            print(f"Playwright CDP on {port}: {str(e)[:80]}")
    pw.stop()
except Exception as e:
    print(f"Playwright error: {e}")

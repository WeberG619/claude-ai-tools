"""Full integration test for CDP MCP - Chrome and Edge."""
import sys, os, asyncio, json, time
sys.path.insert(0, os.path.dirname(__file__))

from chrome_launcher import (
    ensure_chrome_cdp, ensure_edge_cdp, get_status,
    CDP_PORT, EDGE_CDP_PORT, CHROME_PATH, EDGE_PATH,
)
from cdp_client import get_client

PASS = 0
FAIL = 0

def report(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {name}" + (f" - {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  [FAIL] {name}" + (f" - {detail}" if detail else ""))


async def test_browser(browser_name, port, ensure_fn):
    """Test a browser: launch, navigate, interact, screenshot, cleanup."""
    global PASS, FAIL
    print(f"\n{'='*60}")
    print(f"Testing {browser_name} (port {port})")
    print(f"{'='*60}")

    # 1. Launch
    print(f"\n--- Launch ---")
    result = ensure_fn()
    launched = result.get("success") or result.get("ready")
    report(f"Launch {browser_name}", launched, result.get("message", ""))
    if not launched:
        print(f"  Skipping remaining {browser_name} tests")
        return False

    # 2. Status check
    print(f"\n--- Status ---")
    status = get_status()
    key = "chrome" if browser_name == "Chrome" else "edge"
    report(f"Status shows {browser_name} available", status[key]["available"])

    # 3. Connect
    print(f"\n--- Connection ---")
    client = get_client(port=port)
    try:
        title = await client.connect(0)
        report("Connect to tab", True, f"Title: {title}")
    except Exception as e:
        report("Connect to tab", False, str(e))
        return False

    # 4. List tabs
    print(f"\n--- Tabs ---")
    tabs = client.get_all_tabs()
    report("List tabs", len(tabs) > 0, f"{len(tabs)} tab(s)")

    # 5. Navigate - Site 1
    print(f"\n--- Navigation ---")
    sites = [
        ("https://news.ycombinator.com", "Hacker News"),
        ("https://en.wikipedia.org", "Wikipedia"),
        ("https://github.com", "GitHub"),
    ]

    for url, expected_name in sites:
        try:
            await client.navigate(url)
            await asyncio.sleep(2)
            title = await client.evaluate("document.title")
            ok = len(title) > 0
            report(f"Navigate to {expected_name}", ok, f"Title: {title[:60]}")
        except Exception as e:
            report(f"Navigate to {expected_name}", False, str(e))

    # 6. JavaScript evaluation
    print(f"\n--- JS Evaluation ---")
    try:
        result = await client.evaluate("1 + 1")
        report("Simple math (1+1)", result == 2, f"Result: {result}")
    except Exception as e:
        report("Simple math", False, str(e))

    try:
        result = await client.evaluate("navigator.userAgent")
        report("Get user agent", isinstance(result, str) and len(result) > 10, result[:80])
    except Exception as e:
        report("Get user agent", False, str(e))

    # 7. Get text
    print(f"\n--- Text Extraction ---")
    try:
        text = await client.get_text("body", max_length=200)
        report("Get page text", len(text) > 10, f"{len(text)} chars")
    except Exception as e:
        report("Get page text", False, str(e))

    # 8. Get HTML
    print(f"\n--- HTML ---")
    try:
        html = await client.get_html(selector="title")
        report("Get title HTML", "<title>" in html.lower(), html[:80])
    except Exception as e:
        report("Get title HTML", False, str(e))

    # 9. Screenshot
    print(f"\n--- Screenshot ---")
    try:
        png_bytes = await client.screenshot()
        ok = len(png_bytes) > 1000
        path = os.path.join(r"C:\Temp", f"{browser_name.lower()}-cdp-test.png")
        with open(path, "wb") as f:
            f.write(png_bytes)
        report("Take screenshot", ok, f"{len(png_bytes)} bytes -> {path}")
    except Exception as e:
        report("Take screenshot", False, str(e))

    # 10. Open new tab via CDP API
    print(f"\n--- New Tab ---")
    try:
        target = client.create_new_tab("https://example.com")
        await asyncio.sleep(2)
        tabs = client.get_all_tabs()
        report("Open new tab (CDP API)", len(tabs) >= 2, f"{len(tabs)} tab(s) now")
    except Exception as e:
        report("Open new tab (CDP API)", False, str(e))

    await client.disconnect()
    return True


async def main():
    global PASS, FAIL

    print("="*60)
    print("CDP MCP Server - Full Integration Test")
    print(f"Chrome port: {CDP_PORT}, Edge port: {EDGE_CDP_PORT}")
    print(f"Chrome path: {CHROME_PATH}")
    print(f"Edge path:   {EDGE_PATH}")
    print("="*60)

    # Test Chrome
    await test_browser("Chrome", CDP_PORT, ensure_chrome_cdp)

    # Kill Chrome before testing Edge
    import subprocess
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"],
                   capture_output=True, timeout=10)
    time.sleep(2)

    # Test Edge
    await test_browser("Edge", EDGE_CDP_PORT, ensure_edge_cdp)

    # Summary
    print("\n" + "="*60)
    print(f"RESULTS: {PASS} passed, {FAIL} failed")
    print("="*60)

    if FAIL > 0:
        sys.exit(1)


asyncio.run(main())

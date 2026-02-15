#!/usr/bin/env python3
"""Enable YouTube Data API v3 on bim-ops-youtube project via CDP browser."""
import asyncio
from playwright.async_api import async_playwright

async def enable_api():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=10000)
    ctx = browser.contexts[0]

    # Find the Google Cloud Console tab
    page = None
    for p in ctx.pages:
        if "console.cloud.google.com" in p.url:
            page = p
            break

    if not page:
        page = await ctx.new_page()
        url = "https://console.cloud.google.com/apis/library/youtube.googleapis.com?project=bim-ops-youtube"
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(10)

    print(f"URL: {page.url}")

    # Dismiss free trial banner if present
    try:
        dismiss = page.locator('button:has-text("Dismiss")').first
        if await dismiss.is_visible(timeout=3000):
            await dismiss.click()
            print("Dismissed trial banner")
            await asyncio.sleep(2)
    except:
        pass

    # Click Enable button - try multiple selectors
    clicked = False
    for selector in [
        'button:has-text("Enable")',
        '[aria-label="Enable"]',
        'button.mdc-button:has-text("Enable")',
    ]:
        try:
            btn = page.locator(selector).first
            await btn.scroll_into_view_if_needed(timeout=3000)
            await asyncio.sleep(1)
            await btn.click(timeout=5000, force=True)
            print(f"Clicked Enable via: {selector}")
            clicked = True
            break
        except Exception as e:
            print(f"  {selector}: {e}")

    if not clicked:
        # Last resort - use JavaScript
        result = await page.evaluate("""() => {
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {
                if (btn.textContent.trim() === 'Enable') {
                    btn.click();
                    return 'clicked via JS';
                }
            }
            return 'no Enable button found';
        }""")
        print(f"JS fallback: {result}")
        clicked = "clicked" in result

    if clicked:
        print("Waiting for API to enable...")
        await asyncio.sleep(15)
        body = await page.inner_text("body")
        if any(kw in body.lower() for kw in ["manage", "disable", "enabled", "api/dashboard"]):
            print("SUCCESS: YouTube Data API v3 is ENABLED!")
        else:
            print(f"Post-enable page: {body[:300]}")

    # Close extra tabs
    for p in list(ctx.pages):
        if any(kw in p.url for kw in ["newtab", "new-tab"]):
            await p.close()

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(enable_api())

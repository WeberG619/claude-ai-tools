#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def cleanup():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0]

    # Use JavaScript to find and click the Save button in the overlay
    result = await page.evaluate("""() => {
        // Find Save buttons in overlay/dialog
        const overlays = document.querySelectorAll('.cdk-overlay-pane, [role="dialog"]');
        for (const ov of overlays) {
            const btns = ov.querySelectorAll('button');
            for (const btn of btns) {
                if (btn.textContent.trim() === 'Save') {
                    btn.click();
                    return 'clicked Save in dialog';
                }
            }
        }
        // Fallback: any visible Save button
        const allBtns = document.querySelectorAll('button');
        for (const btn of allBtns) {
            if (btn.textContent.trim() === 'Save' && btn.offsetParent !== null) {
                btn.click();
                return 'clicked Save (fallback)';
            }
        }
        // Try X/close button
        const close = document.querySelector('[aria-label="Close"], .mat-dialog-close');
        if (close) { close.click(); return 'clicked close'; }
        return 'no button found';
    }""")
    print(f"Dialog: {result}")
    await asyncio.sleep(3)

    # Close extra tabs
    tabs = list(ctx.pages)
    for p in tabs:
        url = p.url
        if any(kw in url for kw in ["approval", "developers.google.com/terms", "newtab", "new-tab-page", "newtab-footer"]):
            try:
                await p.close()
                print(f"Closed: {url[:50]}")
            except:
                pass

    print(f"Tabs: {len(ctx.pages)}")
    for p in ctx.pages:
        print(f"  {p.url[:80]}")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(cleanup())

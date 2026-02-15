#!/usr/bin/env python3
"""Take screenshot of current browser state"""
import asyncio
from playwright.async_api import async_playwright

async def screenshot():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    print(f"Current URL: {page.url}")

    # Take screenshot
    await page.screenshot(path=r"D:\gcloud_screenshot.png", full_page=False)
    print("Screenshot saved to D:\\gcloud_screenshot.png")

    # Also dump body text
    body = await page.inner_text("body")
    with open(r"D:\gcloud_current_state.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:15000])

    # Check for any overlays/dialogs
    dialogs = await page.locator('[role="dialog"], .cdk-overlay-pane, .mat-mdc-dialog-container').all()
    for d in dialogs:
        try:
            vis = await d.is_visible()
            if vis:
                text = await d.inner_text()
                print(f"DIALOG: {text[:300]}")
        except:
            pass

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(screenshot())

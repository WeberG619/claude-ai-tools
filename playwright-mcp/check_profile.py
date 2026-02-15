#!/usr/bin/env python3
"""Check LinkedIn profile content"""
import asyncio
import traceback
from playwright.async_api import async_playwright

async def check_profile():
    try:
        pw = await async_playwright().start()
        browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
        ctx = browser.contexts[0]
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        await page.goto("https://www.linkedin.com/in/me/", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(4)

        # Scroll down to load more content
        for _ in range(3):
            await page.mouse.wheel(0, 800)
            await asyncio.sleep(1)

        # Scroll back to top
        await page.mouse.wheel(0, -3000)
        await asyncio.sleep(1)

        # Get all visible text
        body_text = await page.inner_text("body")

        # Write to file (utf-8, no encoding issues)
        with open(r"D:\linkedin_profile_text.txt", "w", encoding="utf-8") as f:
            f.write(f"Profile URL: {page.url}\n\n")
            f.write(body_text[:8000])

        print("DONE - wrote to D:\\linkedin_profile_text.txt")

        browser = None
        await pw.stop()
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_profile())

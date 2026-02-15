#!/usr/bin/env python3
"""Check Twitter/X status - logged in? profile exists?"""
import asyncio
from playwright.async_api import async_playwright

async def check():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(5)

    url = page.url
    print(f"URL after navigation: {url}")

    # Check if redirected to login
    if "login" in url or "flow" in url:
        print("STATUS: NOT LOGGED IN - redirected to login page")
    else:
        print("STATUS: LOGGED IN")
        # Try to get profile info
        try:
            # Click on profile or get username
            body_text = await page.inner_text("body")
            # Write first 3000 chars
            with open(r"D:\twitter_status.txt", "w", encoding="utf-8") as f:
                f.write(f"URL: {url}\n\n")
                f.write(body_text[:3000])
            print("Wrote page text to D:\\twitter_status.txt")
        except Exception as e:
            print(f"Error getting page text: {e}")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(check())

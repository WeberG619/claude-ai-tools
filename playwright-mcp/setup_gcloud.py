#!/usr/bin/env python3
"""Set up Google Cloud project for YouTube API via browser automation"""
import asyncio
from playwright.async_api import async_playwright

async def setup():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Step 1: Go to Google Cloud Console
    print("=== Step 1: Navigate to Google Cloud Console ===")
    await page.goto("https://console.cloud.google.com/", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)
    print(f"On: {page.url}")

    # Check what we see
    body = await page.inner_text("body")
    with open(r"D:\gcloud_page.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:5000])
    print("Wrote page state to D:\\gcloud_page.txt")

    # Check if we need to accept terms or select a project
    if "terms" in body.lower() or "agree" in body.lower():
        print("Need to accept terms first")
        try:
            agree_btn = page.locator('button:has-text("Agree"), button:has-text("AGREE"), input[type="checkbox"]').first
            await agree_btn.click(timeout=5000)
            await asyncio.sleep(2)
            # Look for continue/agree button
            continue_btn = page.locator('button:has-text("Agree and Continue"), button:has-text("AGREE AND CONTINUE")').first
            await continue_btn.click(timeout=5000)
            await asyncio.sleep(3)
            print("Accepted terms")
        except Exception as e:
            print(f"Terms handling: {e}")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(setup())

#!/usr/bin/env python3
"""Check all open browser tabs"""
import asyncio
from playwright.async_api import async_playwright

async def check():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    print(f"Open tabs: {len(ctx.pages)}")
    for i, page in enumerate(ctx.pages):
        print(f"  [{i}] {page.url[:100]}")
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(check())

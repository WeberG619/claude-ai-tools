#!/usr/bin/env python3
"""Post next LinkedIn content"""
import asyncio
from playwright.async_api import async_playwright

POST_FILE = r"D:\_CLAUDE-TOOLS\playwright-mcp\posts\post2_jarvis.txt"

async def post():
    with open(POST_FILE, "r", encoding="utf-8") as f:
        post_text = f.read().strip()

    print(f"Post length: {len(post_text)} chars")

    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Open LinkedIn with composer
    await page.goto("https://www.linkedin.com/feed/?shareActive=true", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(4)
    print(f"On: {page.url}")

    # Find the editor textbox
    editor = page.locator('[role="textbox"]').first
    await editor.wait_for(state="visible", timeout=10000)
    print("Found editor textbox")

    # Click and fill
    await editor.click()
    await asyncio.sleep(0.5)
    await editor.fill(post_text)
    await asyncio.sleep(1)
    print("Filled post text")

    # Verify text was entered
    entered = await editor.inner_text()
    print(f"Verified: {len(entered)} chars in editor")

    # Click Post button
    try:
        post_btn = page.get_by_role("button", name="Post", exact=True)
        await post_btn.click(timeout=5000)
        print("Clicked Post button!")
        await asyncio.sleep(3)
        print("POST PUBLISHED SUCCESSFULLY")
    except Exception as e:
        print(f"Could not click Post: {e}")
        # Try alternative
        try:
            post_btn = page.locator('button.share-actions__primary-action').first
            await post_btn.click(timeout=5000)
            print("Posted via alternative selector")
        except Exception as e2:
            print(f"Alternative also failed: {e2}")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(post())

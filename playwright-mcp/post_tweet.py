#!/usr/bin/env python3
"""Post a tweet within 280 char limit"""
import asyncio
from playwright.async_api import async_playwright

TWEET = """I built a voice assistant that talks to Revit.

"Create a floor plan with 3 bedrooms and a central hallway."

Voice → Claude → RevitMCPBridge → walls, doors, rooms placed in seconds.

No menus. No clicking. Just intent → model.

Open source: github.com/bimopsstudio"""

print(f"Tweet length: {len(TWEET)} chars")
assert len(TWEET) <= 280, f"Tweet too long: {len(TWEET)}"

async def post():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    await page.goto("https://x.com/compose/post", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(3)

    editor = page.locator('[data-testid="tweetTextarea_0"], [role="textbox"]').first
    await editor.wait_for(state="visible", timeout=10000)
    await editor.click()
    await asyncio.sleep(0.5)
    await editor.fill(TWEET)
    await asyncio.sleep(1)

    entered = await editor.inner_text()
    print(f"Entered {len(entered)} chars")

    # Wait for button to become enabled
    await asyncio.sleep(2)
    post_btn = page.locator('[data-testid="tweetButton"]').first
    is_disabled = await post_btn.get_attribute("aria-disabled")
    print(f"Post button disabled: {is_disabled}")

    if is_disabled == "true":
        print("Button still disabled - checking char count display")
        # Maybe fill didn't work right, try keyboard
        await editor.click()
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Delete")
        await asyncio.sleep(0.5)
        await page.keyboard.type(TWEET, delay=5)
        await asyncio.sleep(2)
        is_disabled = await post_btn.get_attribute("aria-disabled")
        print(f"After retype, button disabled: {is_disabled}")

    try:
        await post_btn.click(timeout=10000)
        print("TWEET POSTED!")
        await asyncio.sleep(3)
    except Exception as e:
        print(f"Post failed: {e}")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(post())

#!/usr/bin/env python3
"""Update just the LinkedIn headline"""
import asyncio
from playwright.async_api import async_playwright

NEW_HEADLINE = "Founder at BIM Ops Studio | Building AI agents that control Revit | Open Source RevitMCPBridge | ADN Member"

async def update_headline():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    await page.goto("https://www.linkedin.com/in/me/", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(4)
    print(f"On profile: {page.url}")

    # Click Edit profile button
    edit_btn = page.locator('button[aria-label="Edit profile"]').first
    await edit_btn.click(timeout=5000)
    print("Clicked 'Edit profile' button")
    await asyncio.sleep(3)

    # The headline is a div[role="textbox"] containing the current headline text
    textboxes = await page.locator('div[role="textbox"]').all()
    headline_box = None
    for tb in textboxes:
        try:
            if await tb.is_visible():
                text = await tb.inner_text()
                if "Founder" in text or "BIM" in text or "Revit" in text:
                    headline_box = tb
                    print(f"Found headline textbox: '{text[:60]}...'")
                    break
        except:
            pass

    if headline_box:
        # Clear and type the new headline
        await headline_box.click()
        await asyncio.sleep(0.5)
        # Select all and delete
        await page.keyboard.press("Control+a")
        await asyncio.sleep(0.3)
        await page.keyboard.press("Delete")
        await asyncio.sleep(0.3)
        # Type new headline
        await page.keyboard.type(NEW_HEADLINE, delay=10)
        print(f"Typed new headline: {NEW_HEADLINE[:60]}...")
        await asyncio.sleep(1)
    else:
        print("Could not find headline textbox!")

    # Save
    try:
        save_btn = page.get_by_role("button", name="Save")
        await save_btn.click(timeout=5000)
        print("Saved!")
        await asyncio.sleep(3)
    except Exception as e:
        print(f"Save failed: {e}")

    print("Done.")
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(update_headline())

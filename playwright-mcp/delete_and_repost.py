#!/usr/bin/env python3
"""Delete most recent LinkedIn post, then repost with updated text"""
import asyncio
from playwright.async_api import async_playwright

async def delete_and_repost():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Go to profile to find the post
    await page.goto("https://www.linkedin.com/in/me/recent-activity/all/", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(4)
    print(f"On activity page: {page.url}")

    # Find the three-dot menu on the first post
    try:
        # LinkedIn uses "Open control menu" or similar for the ... button
        menu_btn = page.locator('button[aria-label*="control menu"], button[aria-label*="more actions"], button[aria-label*="More actions"]').first
        await menu_btn.click(timeout=5000)
        print("Clicked post menu")
        await asyncio.sleep(1)
    except Exception as e:
        print(f"Could not find menu button: {e}")
        # List buttons to find it
        buttons = await page.locator("button").all()
        for i, btn in enumerate(buttons[:40]):
            try:
                label = await btn.get_attribute("aria-label") or ""
                if "menu" in label.lower() or "more" in label.lower() or "option" in label.lower() or "control" in label.lower():
                    print(f"  btn {i}: aria-label='{label}'")
            except:
                pass
        await pw.stop()
        return

    # Click "Delete post"
    try:
        delete_opt = page.get_by_text("Delete post", exact=False).first
        await delete_opt.click(timeout=5000)
        print("Clicked 'Delete post'")
        await asyncio.sleep(2)
    except Exception as e:
        print(f"Could not find Delete post option: {e}")
        # List menu items
        items = await page.locator('[role="menuitem"], [role="option"], li').all()
        for i, item in enumerate(items[:15]):
            try:
                text = (await item.inner_text())[:60]
                if text.strip():
                    print(f"  menu item {i}: '{text}'")
            except:
                pass
        await pw.stop()
        return

    # Confirm deletion
    try:
        confirm_btn = page.get_by_role("button", name="Delete")
        await confirm_btn.click(timeout=5000)
        print("Confirmed deletion")
        await asyncio.sleep(3)
    except Exception as e:
        print(f"Could not confirm delete: {e}")
        await pw.stop()
        return

    print("Post deleted. Now reposting...")

    # Read the updated post text
    with open(r"D:\_CLAUDE-TOOLS\playwright-mcp\posts\post2_jarvis.txt", "r", encoding="utf-8") as f:
        post_text = f.read().strip()

    print(f"Repost length: {len(post_text)} chars")

    # Open composer
    await page.goto("https://www.linkedin.com/feed/?shareActive=true", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(4)

    # Find editor and fill
    editor = page.locator('[role="textbox"]').first
    await editor.wait_for(state="visible", timeout=10000)
    await editor.click()
    await asyncio.sleep(0.5)
    await editor.fill(post_text)
    await asyncio.sleep(1)
    print("Filled updated post text")

    # Click Post
    try:
        post_btn = page.get_by_role("button", name="Post", exact=True)
        await post_btn.click(timeout=5000)
        print("Clicked Post button!")
        await asyncio.sleep(3)
        print("REPOST PUBLISHED SUCCESSFULLY")
    except Exception as e:
        print(f"Could not click Post: {e}")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(delete_and_repost())

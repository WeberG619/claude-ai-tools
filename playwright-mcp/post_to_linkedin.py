#!/usr/bin/env python3
"""Post to LinkedIn using Playwright + CDP"""

import asyncio
import sys
import os

async def create_post():
    from playwright.async_api import async_playwright

    # Read post text from file
    post_file = r"D:\linkedin_post.txt"
    with open(post_file, "r", encoding="utf-8") as f:
        post_text = f.read().strip()

    print(f"Post text loaded: {len(post_text)} chars")

    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    print("Connected to Chrome CDP")

    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Make sure we're on the feed
    if "feed" not in page.url:
        await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(2)

    print(f"On page: {page.url}")

    # Open post composer via shareActive URL
    await page.goto("https://www.linkedin.com/feed/?shareActive=true", wait_until="domcontentloaded", timeout=15000)
    await asyncio.sleep(3)
    print("Composer should be open")

    # Find the text editor
    # LinkedIn uses a contenteditable div with role="textbox" or class containing "editor"
    editor = None

    # Try role=textbox first
    try:
        editor = page.locator('[role="textbox"]').first
        await editor.wait_for(state="visible", timeout=5000)
        print("Found editor via role=textbox")
    except Exception:
        pass

    # Try contenteditable
    if editor is None:
        try:
            editor = page.locator('[contenteditable="true"]').first
            await editor.wait_for(state="visible", timeout=5000)
            print("Found editor via contenteditable")
        except Exception:
            pass

    # Try the placeholder text
    if editor is None:
        try:
            editor = page.get_by_placeholder("What do you want to talk about?")
            await editor.wait_for(state="visible", timeout=5000)
            print("Found editor via placeholder")
        except Exception:
            pass

    if editor is None:
        print("ERROR: Could not find editor element")
        # List what's on the page
        elements = await page.query_selector_all('[contenteditable], [role="textbox"], textarea')
        print(f"Found {len(elements)} potential editors")
        for i, el in enumerate(elements):
            tag = await el.evaluate("el => el.tagName")
            role = await el.get_attribute("role") or ""
            ce = await el.get_attribute("contenteditable") or ""
            print(f"  {i}: <{tag}> role={role} contenteditable={ce}")
        await browser.close()
        await pw.stop()
        return False

    # Click to focus
    await editor.click()
    await asyncio.sleep(0.5)
    print("Editor focused")

    # Try fill first (works for input/textarea)
    try:
        await editor.fill(post_text)
        print("Used fill() successfully")
    except Exception:
        # For contenteditable, use keyboard.type or clipboard paste
        print("fill() failed, using clipboard paste...")
        # Set clipboard via JS and paste
        await page.evaluate("""
            async (text) => {
                // Use execCommand as fallback for contenteditable
                document.execCommand('insertText', false, text);
            }
        """, post_text)
        print("Used execCommand insertText")

    await asyncio.sleep(1)

    # Verify text was entered
    editor_text = await editor.inner_text()
    if len(editor_text) > 50:
        print(f"SUCCESS: Post text entered ({len(editor_text)} chars)")
        print(f"Preview: {editor_text[:100]}...")
    else:
        print(f"WARNING: Editor text is short ({len(editor_text)} chars): {editor_text}")
        # Last resort: type it character by character
        print("Trying keyboard type as last resort...")
        await editor.click()
        await asyncio.sleep(0.3)
        # Select all and delete first
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Delete")
        await asyncio.sleep(0.2)
        await page.keyboard.type(post_text, delay=2)
        print("Typed via keyboard")

    print("\n=== POST IS READY FOR REVIEW ===")
    print("The post is in the LinkedIn composer. Review it and click 'Post' when ready.")

    await browser.close()
    await pw.stop()
    return True

if __name__ == "__main__":
    result = asyncio.run(create_post())
    sys.exit(0 if result else 1)

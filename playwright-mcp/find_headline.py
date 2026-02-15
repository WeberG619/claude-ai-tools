#!/usr/bin/env python3
"""Find the headline field in LinkedIn's Edit Profile dialog"""
import asyncio
from playwright.async_api import async_playwright

async def find_headline():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    await page.goto("https://www.linkedin.com/in/me/", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(4)

    # Click Edit profile
    edit_btn = page.locator('button[aria-label="Edit profile"]').first
    await edit_btn.click(timeout=5000)
    print("Opened Edit profile dialog")
    await asyncio.sleep(3)

    # Find the modal/dialog
    modal = page.locator('[role="dialog"], .artdeco-modal, [class*="modal"]').first
    try:
        await modal.wait_for(state="visible", timeout=3000)
        print("Found modal dialog")
    except:
        print("No modal found, searching whole page")
        modal = page

    # Scroll within modal to reveal more fields
    try:
        modal_body = page.locator('.artdeco-modal__content, [class*="modal__content"]').first
        await modal_body.evaluate("el => el.scrollTop = 200")
        await asyncio.sleep(1)
        print("Scrolled modal")
    except:
        print("Could not scroll modal body")

    # List ALL form elements in the dialog - inputs, textareas, contenteditable, selects
    print("\n=== ALL FORM ELEMENTS ===")
    for tag in ["input", "textarea", "select", "[contenteditable='true']", "div[role='textbox']"]:
        elements = await page.locator(tag).all()
        for i, el in enumerate(elements[:40]):
            try:
                vis = await el.is_visible()
                if not vis:
                    continue
                label = await el.get_attribute("aria-label") or ""
                el_id = await el.get_attribute("id") or ""
                name = await el.get_attribute("name") or ""
                ph = await el.get_attribute("placeholder") or ""
                role = await el.get_attribute("role") or ""
                tag_name = await el.evaluate("el => el.tagName")
                try:
                    val = await el.input_value()
                    val = val[:80]
                except:
                    val = (await el.inner_text())[:80] if await el.is_visible() else ""
                print(f"  {tag_name} id='{el_id}' label='{label}' name='{name}' ph='{ph}' role='{role}' val='{val}'")
            except:
                pass

    # Also look for labels that say "Headline"
    print("\n=== LABELS CONTAINING 'HEADLINE' ===")
    labels = await page.locator("label").all()
    for i, lbl in enumerate(labels[:30]):
        try:
            text = await lbl.inner_text()
            if "headline" in text.lower() or "title" in text.lower():
                for_attr = await lbl.get_attribute("for") or ""
                print(f"  label: '{text}' for='{for_attr}'")
                # Try to find the associated input
                if for_attr:
                    assoc = page.locator(f"#{for_attr}")
                    tag_name = await assoc.evaluate("el => el.tagName")
                    print(f"    -> associated element: {tag_name}")
        except:
            pass

    # Look for any element with "headline" in its attributes
    print("\n=== ELEMENTS WITH 'HEADLINE' IN ATTRIBUTES ===")
    headline_els = await page.locator('[id*="headline" i], [name*="headline" i], [aria-label*="headline" i], [class*="headline" i]').all()
    for i, el in enumerate(headline_els[:10]):
        try:
            tag_name = await el.evaluate("el => el.tagName")
            el_id = await el.get_attribute("id") or ""
            cls = await el.get_attribute("class") or ""
            vis = await el.is_visible()
            print(f"  {tag_name} id='{el_id}' class='{cls[:80]}' visible={vis}")
        except:
            pass

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(find_headline())

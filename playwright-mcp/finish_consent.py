#!/usr/bin/env python3
"""Check the agreement checkbox and click Create to finish consent screen"""
import asyncio
from playwright.async_api import async_playwright

PROJECT = "bim-ops-youtube"

async def finish():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Should already be on the consent screen creation page at step 4
    print(f"On: {page.url}")

    # If not on the create page, navigate there
    if "auth/overview/create" not in page.url:
        await page.goto(f"https://console.cloud.google.com/auth/overview/create?project={PROJECT}",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(8)

    # Check the agreement checkbox
    print("Looking for agreement checkbox...")

    # Strategy 1: mat-checkbox
    try:
        checkbox = page.locator('mat-checkbox').first
        if await checkbox.is_visible(timeout=3000):
            checked = await checkbox.get_attribute("aria-checked") or ""
            text = (await checkbox.inner_text())[:60]
            print(f"  mat-checkbox: text='{text}' checked={checked}")
            if checked != "true":
                await checkbox.click()
                print("  Checked the checkbox!")
                await asyncio.sleep(1)
    except Exception as e:
        print(f"  mat-checkbox: {e}")

    # Strategy 2: input[type=checkbox]
    try:
        cb_input = page.locator('input[type="checkbox"]').first
        if await cb_input.is_visible(timeout=2000):
            is_checked = await cb_input.is_checked()
            if not is_checked:
                await cb_input.click(force=True)
                print("  Checked checkbox input!")
        elif not await cb_input.is_visible():
            # Try clicking via JS
            result = await page.evaluate("""() => {
                const cbs = document.querySelectorAll('mat-checkbox, input[type="checkbox"]');
                for (const cb of cbs) {
                    cb.click();
                    return 'clicked: ' + cb.tagName;
                }
                return 'none found';
            }""")
            print(f"  JS checkbox click: {result}")
    except Exception as e:
        print(f"  checkbox input: {e}")

    # Strategy 3: Click text "I agree"
    try:
        agree = page.locator(':text("I agree")').first
        if await agree.is_visible(timeout=2000):
            await agree.click()
            print("  Clicked 'I agree' text")
    except:
        pass

    await asyncio.sleep(1)

    # Verify checkbox state
    try:
        cbs = await page.locator('mat-checkbox').all()
        for cb in cbs:
            try:
                vis = await cb.is_visible()
                if vis:
                    checked = await cb.get_attribute("aria-checked") or ""
                    text = (await cb.inner_text())[:50]
                    print(f"  Checkbox: checked={checked} text='{text}'")
            except:
                pass
    except:
        pass

    # Now click Create
    print("\nClicking Create...")
    try:
        create_btn = page.locator('button:has-text("Create")').first
        disabled = await create_btn.get_attribute("disabled")
        aria_disabled = await create_btn.get_attribute("aria-disabled")
        print(f"  Create button: disabled={disabled} aria-disabled={aria_disabled}")
        await create_btn.click(timeout=5000)
        print("  Clicked Create!")
        await asyncio.sleep(10)
    except Exception as e:
        print(f"  Create failed: {e}")

    # Also try Continue button
    try:
        cont_btn = page.locator('button:has-text("Continue")').first
        if await cont_btn.is_visible(timeout=2000):
            await cont_btn.click(timeout=3000)
            print("  Also clicked Continue!")
            await asyncio.sleep(5)
    except:
        pass

    # Check result
    print(f"\nFinal URL: {page.url}")
    body = await page.inner_text("body")
    with open(r"D:\gcloud_consent_done2.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:12000])

    if "overview/create" not in page.url:
        print("SUCCESS! Navigated away from creation page!")
    else:
        # Check step indicators
        steps = await page.locator('[aria-label*="step"]').all()
        for s in steps[:5]:
            try:
                label = await s.get_attribute("aria-label") or ""
                print(f"  {label}")
            except:
                pass

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(finish())

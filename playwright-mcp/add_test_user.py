#!/usr/bin/env python3
"""Add test users to OAuth audience - fill chip input + Enter + Save"""
import asyncio
from playwright.async_api import async_playwright

PROJECT = "bim-ops-youtube"

async def add_user():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Go to audience page
    print("=== Adding Test Users ===")
    await page.goto(f"https://console.cloud.google.com/auth/audience?project={PROJECT}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(8)
    print(f"On: {page.url}")

    body = await page.inner_text("body")

    # Check current test users
    print("Current test users:")
    if "weber@bimopsstudio.com" in body:
        print("  weber@bimopsstudio.com already present")
    if "weberg619@gmail.com" in body:
        print("  weberg619@gmail.com already present")

    # Click "Add users"
    try:
        add_btn = page.locator('button:has-text("Add users")').first
        await add_btn.click(timeout=5000)
        print("Clicked 'Add users'")
        await asyncio.sleep(3)
    except Exception as e:
        print(f"Add users button: {e}")

    # Find the email chip input
    try:
        email_input = page.locator('#_0rif_mat-mdc-chip-list-input-0, [aria-label*="email"], input[aria-label="Text field for emails"]').first
        await email_input.wait_for(state="visible", timeout=5000)

        # Add first email
        await email_input.fill("weber@bimopsstudio.com")
        await asyncio.sleep(0.5)
        await page.keyboard.press("Enter")
        print("  Added: weber@bimopsstudio.com")
        await asyncio.sleep(1)

        # Add second email
        await email_input.fill("weberg619@gmail.com")
        await asyncio.sleep(0.5)
        await page.keyboard.press("Enter")
        print("  Added: weberg619@gmail.com")
        await asyncio.sleep(1)
    except Exception as e:
        print(f"Email input: {e}")

    # Click Add/Save button in the dialog
    try:
        # Look for a dialog-specific Add button
        dialog_btns = await page.locator('[role="dialog"] button, .cdk-overlay-pane button').all()
        for btn in dialog_btns:
            try:
                if await btn.is_visible():
                    text = (await btn.inner_text())[:20].strip()
                    if text.lower() in ["add", "save", "confirm"]:
                        await btn.click()
                        print(f"  Clicked dialog '{text}' button")
                        await asyncio.sleep(3)
                        break
            except:
                pass
        else:
            # Fallback: look for any visible "Add" button
            add_btn = page.locator('button:has-text("Add")').last
            if await add_btn.is_visible(timeout=2000):
                await add_btn.click()
                print("  Clicked last 'Add' button")
                await asyncio.sleep(3)
    except Exception as e:
        print(f"Save: {e}")

    # Verify
    await asyncio.sleep(2)
    body = await page.inner_text("body")
    print(f"\nFinal state:")
    for email in ["weber@bimopsstudio.com", "weberg619@gmail.com"]:
        if email in body:
            print(f"  Present: {email}")
        else:
            print(f"  NOT found: {email}")

    with open(r"D:\gcloud_audience_done.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:10000])

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(add_user())

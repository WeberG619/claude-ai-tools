#!/usr/bin/env python3
"""Configure OAuth consent screen then create credentials"""
import asyncio
from playwright.async_api import async_playwright

PROJECT = "bim-ops-youtube"

async def configure():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Step 1: Click "Configure consent screen" link
    print("=== Configuring Consent Screen ===")
    # Go to the branding page which is the new consent screen config
    await page.goto(f"https://console.cloud.google.com/auth/branding?project={PROJECT}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)
    print(f"On: {page.url}")

    body = await page.inner_text("body")
    with open(r"D:\gcloud_branding.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:8000])

    # List all form elements on this page
    print("Form elements:")
    inputs = await page.locator("input, textarea, select").all()
    for i, inp in enumerate(inputs[:25]):
        try:
            if not await inp.is_visible():
                continue
            tag = await inp.evaluate("el => el.tagName")
            label = await inp.get_attribute("aria-label") or ""
            el_id = await inp.get_attribute("id") or ""
            placeholder = await inp.get_attribute("placeholder") or ""
            try:
                val = await inp.input_value()
            except:
                val = ""
            print(f"  {tag} id='{el_id}' label='{label}' ph='{placeholder}' val='{val[:50]}'")
        except:
            pass

    # Look for buttons
    print("\nButtons:")
    buttons = await page.locator("button, a[role='button']").all()
    for i, btn in enumerate(buttons[:25]):
        try:
            if not await btn.is_visible():
                continue
            text = (await btn.inner_text())[:40]
            label = await btn.get_attribute("aria-label") or ""
            if text.strip() or label:
                print(f"  btn: text='{text}' label='{label}'")
        except:
            pass

    # Check if there's a "Get Started" button or if we need to fill a form
    if "get started" in body.lower():
        print("\nClicking Get Started...")
        try:
            btn = page.locator('button:has-text("Get started"), a:has-text("Get started")').first
            await btn.click(timeout=5000)
            await asyncio.sleep(5)
            print(f"After Get Started: {page.url}")
            body = await page.inner_text("body")
            with open(r"D:\gcloud_after_start.txt", "w", encoding="utf-8") as f:
                f.write(f"URL: {page.url}\n\n")
                f.write(body[:8000])
        except Exception as e:
            print(f"Get Started failed: {e}")

    # Fill the branding/consent form
    # App name
    try:
        app_name_input = page.locator('input[formcontrolname="displayName"], input[aria-label*="App name"], input[aria-label*="app name"]').first
        if await app_name_input.is_visible(timeout=3000):
            await app_name_input.fill("BIM Ops Studio Uploader")
            print("Filled app name")
    except:
        # Try by placeholder or just first non-search input
        try:
            inputs = await page.locator("input").all()
            for inp in inputs:
                try:
                    if not await inp.is_visible():
                        continue
                    val = await inp.input_value()
                    label = await inp.get_attribute("aria-label") or ""
                    if "search" in label.lower() or "query" in label.lower():
                        continue
                    if not val:
                        await inp.fill("BIM Ops Studio Uploader")
                        print(f"Filled first empty input (label='{label}')")
                        break
                except:
                    pass
        except:
            pass

    # User support email
    try:
        email_inputs = await page.locator('input[type="email"]').all()
        for inp in email_inputs:
            if await inp.is_visible():
                await inp.fill("weber@bimopsstudio.com")
                print("Filled support email")
                break
    except:
        pass

    # Developer contact email
    try:
        textareas = await page.locator("textarea").all()
        for ta in textareas:
            if await ta.is_visible():
                await ta.fill("weber@bimopsstudio.com")
                print("Filled developer email textarea")
                break
    except:
        pass

    # Save / Continue
    for text in ["Save and Continue", "Save", "Continue", "Next", "Create"]:
        try:
            btn = page.locator(f'button:has-text("{text}")').first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                print(f"Clicked '{text}'")
                await asyncio.sleep(3)
                break
        except:
            continue

    # After consent screen is configured, go create the OAuth client
    print("\n=== Creating OAuth Client ===")
    await page.goto(f"https://console.cloud.google.com/auth/clients/create?project={PROJECT}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)
    print(f"On: {page.url}")

    body = await page.inner_text("body")
    with open(r"D:\gcloud_create_client.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:8000])

    # List form elements
    print("Client creation form elements:")
    all_els = await page.locator("input, select, textarea, mat-select, [role='combobox'], [role='listbox'], cfc-select").all()
    for i, el in enumerate(all_els[:20]):
        try:
            if not await el.is_visible():
                continue
            tag = await el.evaluate("el => el.tagName")
            label = await el.get_attribute("aria-label") or ""
            el_id = await el.get_attribute("id") or ""
            try:
                val = await el.input_value()
            except:
                val = (await el.inner_text())[:50]
            print(f"  {tag} id='{el_id}' label='{label}' val='{val[:50]}'")
        except:
            pass

    # Also check for dropdowns/selects specifically
    print("\nLooking for app type dropdown:")
    dropdowns = await page.locator("mat-select, cfc-select, [role='combobox'], [role='listbox'], select").all()
    for i, dd in enumerate(dropdowns):
        try:
            vis = await dd.is_visible()
            text = (await dd.inner_text())[:50]
            label = await dd.get_attribute("aria-label") or ""
            print(f"  dropdown {i}: visible={vis} text='{text}' label='{label}'")
        except:
            pass

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(configure())

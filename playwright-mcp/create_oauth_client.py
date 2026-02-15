#!/usr/bin/env python3
"""Create OAuth Desktop client - target the correct dropdown"""
import asyncio
from playwright.async_api import async_playwright

PROJECT = "bim-ops-youtube"

async def create_client():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Navigate to OAuth client creation page
    print("=== Creating OAuth Desktop Client ===")
    await page.goto(f"https://console.cloud.google.com/auth/clients/create?project={PROJECT}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(8)
    print(f"On: {page.url}")

    # Select "Desktop app" from Application type dropdown
    # The correct dropdown is _0rif_cfc-select-0
    print("\n--- Selecting Application Type ---")
    try:
        app_type_dd = page.locator('#_0rif_cfc-select-0')
        await app_type_dd.wait_for(state="visible", timeout=8000)
        await app_type_dd.click()
        print("  Clicked app type dropdown")
        await asyncio.sleep(2)

        # Look for Desktop app option
        options = await page.locator('[role="option"], cfc-option, mat-option').all()
        print(f"  Found {len(options)} options")
        for opt in options:
            try:
                text = (await opt.inner_text())[:50]
                print(f"    Option: '{text}'")
                if "desktop" in text.lower():
                    await opt.click()
                    print(f"    Selected: {text}")
                    break
            except:
                pass
        await asyncio.sleep(3)
    except Exception as e:
        print(f"  App type dropdown: {e}")

    # After selecting Desktop app, more form fields should appear
    print("\n--- Form after type selection ---")
    body = await page.inner_text("body")
    with open(r"D:\gcloud_after_type.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:12000])

    # List visible inputs
    inputs = await page.locator("input").all()
    for inp in inputs:
        try:
            if not await inp.is_visible():
                continue
            el_type = await inp.get_attribute("type") or ""
            el_id = await inp.get_attribute("id") or ""
            if el_type == "search" or "search" in el_id:
                continue
            label = await inp.get_attribute("aria-label") or ""
            val = await inp.input_value()
            print(f"  Input: id='{el_id}' type='{el_type}' label='{label[:30]}' val='{val[:30]}'")
        except:
            pass

    # Fill client name if there's an input for it
    try:
        name_inputs = await page.locator("input:not([type='search']):not([type='hidden'])").all()
        for inp in name_inputs:
            if await inp.is_visible():
                el_id = await inp.get_attribute("id") or ""
                if "search" in el_id or "mat-input-0" == el_id:
                    continue
                val = await inp.input_value()
                if "Desktop client" in val or not val:
                    await inp.fill("BIM Ops YouTube Uploader")
                    print(f"  Filled client name in {el_id}")
                    break
    except Exception as e:
        print(f"  Client name: {e}")

    # List buttons
    print("\nButtons:")
    buttons = await page.locator("button").all()
    for btn in buttons[:20]:
        try:
            if not await btn.is_visible():
                continue
            text = (await btn.inner_text())[:40].strip()
            if text and text not in ["Dismiss", "Start free", "Keyboard shortcuts"]:
                disabled = await btn.get_attribute("disabled")
                print(f"  btn: '{text}' disabled={disabled}")
        except:
            pass

    # Click Create
    print("\n--- Creating Client ---")
    try:
        create_btn = page.locator('button:has-text("Create")').first
        await create_btn.wait_for(state="visible", timeout=5000)
        await create_btn.click(timeout=5000)
        print("  Clicked Create!")
        await asyncio.sleep(10)
    except Exception as e:
        print(f"  Create failed: {e}")
        # Try scrolling and looking again
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)
        try:
            create_btn = page.locator('button:has-text("Create")').first
            await create_btn.click(timeout=5000)
            print("  Clicked Create (after scroll)!")
            await asyncio.sleep(10)
        except:
            pass

    # Check the result page
    print(f"\nResult URL: {page.url}")
    body = await page.inner_text("body")
    with open(r"D:\gcloud_client_done.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:15000])

    # Look for dialog with client ID/secret
    print("\nLooking for credentials dialog...")
    try:
        # Check for modal/dialog
        dialogs = await page.locator('[role="dialog"], .mat-mdc-dialog-container, .cdk-overlay-pane').all()
        for d in dialogs:
            try:
                if await d.is_visible():
                    text = (await d.inner_text())[:500]
                    print(f"  Dialog content: {text[:200]}")
            except:
                pass
    except:
        pass

    # Look for download JSON button
    try:
        for sel in ['button:has-text("Download")', 'a:has-text("Download")',
                     'button:has-text("download JSON")', 'a:has-text("JSON")',
                     '[aria-label*="Download"]', '[aria-label*="download"]']:
            dl_btn = page.locator(sel).first
            try:
                if await dl_btn.is_visible(timeout=2000):
                    print(f"  Found download with selector: {sel}")
                    async with page.expect_download(timeout=10000) as dl_info:
                        await dl_btn.click()
                        download = await dl_info.value
                        save_path = r"D:\_CLAUDE-TOOLS\youtube-uploader\client_secret.json"
                        await download.save_as(save_path)
                        print(f"  DOWNLOADED to: {save_path}")
                    break
            except:
                pass
    except:
        pass

    # If no dialog, check if we're on the client detail page
    if "clients" in page.url and "create" not in page.url:
        print("\nOn client detail page!")
        # Look for client ID text
        for kw in ["Client ID", "Client secret", ".apps.googleusercontent.com"]:
            if kw in body:
                # Find the line with this keyword
                for line in body.split("\n"):
                    if kw in line:
                        print(f"  {line.strip()[:100]}")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(create_client())

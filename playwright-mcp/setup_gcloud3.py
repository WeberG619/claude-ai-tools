#!/usr/bin/env python3
"""Set up YouTube API on existing Google Cloud project"""
import asyncio
from playwright.async_api import async_playwright

PROJECT_ID = "bridge-ai-484302"

async def setup():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Step 1: Enable YouTube Data API v3 on existing project
    print("=== Step 1: Enable YouTube Data API v3 ===")
    await page.goto(f"https://console.cloud.google.com/apis/library/youtube.googleapis.com?project={PROJECT_ID}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(6)
    print(f"On: {page.url}")

    body = await page.inner_text("body")
    if "manage" in body.lower() or "enabled" in body.lower() or "disable" in body.lower():
        print("YouTube API already enabled!")
    else:
        try:
            enable_btn = page.locator('button:has-text("Enable"), button:has-text("ENABLE")').first
            await enable_btn.click(timeout=10000)
            print("Clicked Enable")
            await asyncio.sleep(8)
        except Exception as e:
            print(f"Enable: {e}")

    # Step 2: Go to OAuth consent screen (old-style URL)
    print("\n=== Step 2: OAuth Consent Screen ===")
    await page.goto(f"https://console.cloud.google.com/apis/credentials/consent?project={PROJECT_ID}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)
    print(f"On: {page.url}")

    body = await page.inner_text("body")
    with open(r"D:\gcloud_consent2.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:6000])
    print("Saved consent page state")

    # Check if consent screen already configured
    if "edit app" in body.lower() or "publishing status" in body.lower():
        print("OAuth consent screen already configured!")
    else:
        # Need to select user type and create
        # Try to select External
        try:
            external = page.locator('[value="EXTERNAL"], :text("External")').first
            await external.click(timeout=5000)
            print("Selected External")
            await asyncio.sleep(1)
        except:
            pass

        try:
            create_btn = page.locator('button:has-text("Create"), button:has-text("CREATE")').first
            await create_btn.click(timeout=5000)
            print("Clicked Create")
            await asyncio.sleep(5)
        except:
            pass

        # Fill the form
        try:
            # App name
            inputs = await page.locator("input").all()
            for inp in inputs:
                try:
                    if not await inp.is_visible():
                        continue
                    label = await inp.get_attribute("aria-label") or ""
                    val = await inp.input_value()
                    placeholder = await inp.get_attribute("placeholder") or ""
                    if "app name" in label.lower() or (not val and not placeholder):
                        await inp.fill("BIM Ops Studio Uploader")
                        print(f"Filled app name (label='{label}')")
                        break
                except:
                    pass

            # Developer email
            email_inputs = await page.locator('input[type="email"], input[id*="email"]').all()
            for inp in email_inputs:
                try:
                    if await inp.is_visible():
                        await inp.fill("weber@bimopsstudio.com")
                        print("Filled developer email")
                except:
                    pass

            # Save
            save_btn = page.locator('button:has-text("Save and Continue"), button:has-text("SAVE AND CONTINUE"), button:has-text("Save")').first
            await save_btn.click(timeout=5000)
            print("Saved consent screen")
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Consent form: {e}")

    # Step 3: Create OAuth credentials
    print("\n=== Step 3: Create OAuth 2.0 Client ID ===")
    await page.goto(f"https://console.cloud.google.com/apis/credentials/oauthclient?project={PROJECT_ID}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)
    print(f"On: {page.url}")

    body = await page.inner_text("body")
    with open(r"D:\gcloud_oauth.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:6000])

    # List all visible form elements
    print("Listing form elements:")
    for tag in ["select", "input", "button", '[role="listbox"]', '[role="combobox"]']:
        elements = await page.locator(tag).all()
        for i, el in enumerate(elements[:20]):
            try:
                if not await el.is_visible():
                    continue
                label = await el.get_attribute("aria-label") or ""
                text = (await el.inner_text())[:60] if tag in ["select", "button"] else ""
                el_id = await el.get_attribute("id") or ""
                try:
                    val = await el.input_value()
                except:
                    val = ""
                if label or text or val:
                    tag_name = await el.evaluate("el => el.tagName")
                    print(f"  {tag_name} id='{el_id}' label='{label}' text='{text[:40]}' val='{val[:40]}'")
            except:
                pass

    # Try to select "Desktop app" from application type dropdown
    try:
        # The dropdown might be a mat-select or regular select
        dropdowns = await page.locator('select, [role="listbox"], mat-select, [role="combobox"]').all()
        for dd in dropdowns:
            try:
                if await dd.is_visible():
                    await dd.click()
                    print("Clicked a dropdown")
                    await asyncio.sleep(1)
                    # Look for Desktop app option
                    desktop = page.locator('[role="option"]:has-text("Desktop"), option:has-text("Desktop"), mat-option:has-text("Desktop")').first
                    await desktop.click(timeout=3000)
                    print("Selected Desktop app!")
                    await asyncio.sleep(1)
                    break
            except:
                continue
    except:
        pass

    # Fill name
    try:
        name_input = page.locator('input[aria-label*="Name"], input#name, input[formcontrolname="name"]').first
        if await name_input.is_visible(timeout=3000):
            await name_input.fill("BIM Ops YouTube Uploader")
            print("Filled credential name")
    except:
        pass

    # Click Create
    try:
        create_btn = page.locator('button:has-text("Create"), button:has-text("CREATE")').first
        await create_btn.click(timeout=5000)
        print("Clicked Create!")
        await asyncio.sleep(5)
    except Exception as e:
        print(f"Create: {e}")

    # Check for download / client ID
    body = await page.inner_text("body")
    with open(r"D:\gcloud_result.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:6000])
    print(f"\nResult URL: {page.url}")

    # Try to click download JSON
    try:
        download = page.locator('button:has-text("Download JSON"), button:has-text("DOWNLOAD JSON"), a:has-text("download")').first
        if await download.is_visible(timeout=3000):
            await download.click()
            print("Downloading client_secret.json!")
            await asyncio.sleep(5)
    except:
        print("No download button found on this page")

    # Go to credentials list to find the download link
    print("\n=== Checking credentials list ===")
    await page.goto(f"https://console.cloud.google.com/apis/credentials?project={PROJECT_ID}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)

    body = await page.inner_text("body")
    with open(r"D:\gcloud_credlist.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:6000])
    print(f"Credentials list URL: {page.url}")

    # Look for download icons on credentials
    download_btns = await page.locator('[aria-label*="Download"], [aria-label*="download"], button[aria-label*="JSON"]').all()
    for i, btn in enumerate(download_btns):
        try:
            label = await btn.get_attribute("aria-label") or ""
            vis = await btn.is_visible()
            print(f"  download btn {i}: label='{label}' visible={vis}")
            if vis:
                await btn.click()
                print(f"  Clicked download button!")
                await asyncio.sleep(5)
                break
        except:
            pass

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(setup())

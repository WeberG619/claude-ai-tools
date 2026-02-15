#!/usr/bin/env python3
"""Set up Google Cloud project for YouTube API - after login"""
import asyncio
from playwright.async_api import async_playwright

async def setup():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Navigate to Cloud Console
    print("=== Navigating to Google Cloud Console ===")
    await page.goto("https://console.cloud.google.com/", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(6)
    print(f"On: {page.url}")

    # Check if we're on the console
    body = await page.inner_text("body")
    with open(r"D:\gcloud_page2.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:6000])
    print("Wrote page state")

    # Check for terms of service
    if "terms of service" in body.lower() or "agree" in body.lower():
        print("Handling Terms of Service...")
        try:
            checkboxes = await page.locator('input[type="checkbox"], mat-checkbox, [role="checkbox"]').all()
            for cb in checkboxes:
                try:
                    if await cb.is_visible():
                        await cb.click()
                        print("  Checked a checkbox")
                        await asyncio.sleep(0.5)
                except:
                    pass

            for text in ["Agree and Continue", "AGREE AND CONTINUE", "Agree", "Accept", "Continue"]:
                try:
                    btn = page.get_by_role("button", name=text)
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        print(f"  Clicked '{text}'")
                        await asyncio.sleep(3)
                        break
                except:
                    continue
        except Exception as e:
            print(f"Terms handling error: {e}")

    # Now create a new project
    print("\n=== Step 2: Create New Project ===")
    await page.goto("https://console.cloud.google.com/projectcreate", wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)
    print(f"On: {page.url}")

    # Fill project name
    try:
        name_input = page.locator('input[aria-label*="Project name"], input[formcontrolname="projectName"], input#project-name, input[type="text"]').first
        await name_input.wait_for(state="visible", timeout=10000)
        await name_input.fill("")
        await name_input.fill("bimops-youtube")
        print("Filled project name: bimops-youtube")
        await asyncio.sleep(1)
    except Exception as e:
        print(f"Could not fill project name: {e}")
        # Debug: list all inputs
        inputs = await page.locator("input").all()
        for i, inp in enumerate(inputs[:15]):
            try:
                if await inp.is_visible():
                    label = await inp.get_attribute("aria-label") or ""
                    val = await inp.input_value()
                    print(f"  input {i}: label='{label}' val='{val[:50]}'")
            except:
                pass

    # Click Create
    try:
        create_btn = page.get_by_role("button", name="Create")
        await create_btn.click(timeout=5000)
        print("Clicked Create")
        await asyncio.sleep(8)
    except Exception as e:
        print(f"Create button: {e}")
        # Try alternative
        try:
            create_btn = page.locator('button:has-text("CREATE"), button:has-text("Create")').first
            await create_btn.click(timeout=5000)
            print("Clicked Create (alt)")
            await asyncio.sleep(8)
        except:
            pass

    print(f"After create: {page.url}")

    # Step 3: Enable YouTube Data API v3
    print("\n=== Step 3: Enable YouTube Data API v3 ===")
    await page.goto("https://console.cloud.google.com/apis/library/youtube.googleapis.com?project=bimops-youtube",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)
    print(f"On: {page.url}")

    try:
        enable_btn = page.get_by_role("button", name="Enable")
        await enable_btn.click(timeout=10000)
        print("Clicked Enable")
        await asyncio.sleep(8)
    except Exception as e:
        print(f"Enable button: {e}")
        # Maybe already enabled
        body = await page.inner_text("body")
        if "manage" in body.lower() or "enabled" in body.lower():
            print("API may already be enabled")
        else:
            try:
                enable_btn = page.locator('button:has-text("ENABLE"), button:has-text("Enable")').first
                await enable_btn.click(timeout=5000)
                print("Clicked Enable (alt)")
                await asyncio.sleep(8)
            except:
                pass

    # Step 4: Set up OAuth consent screen
    print("\n=== Step 4: OAuth Consent Screen ===")
    await page.goto("https://console.cloud.google.com/apis/credentials/consent?project=bimops-youtube",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)

    body = await page.inner_text("body")
    with open(r"D:\gcloud_consent.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:5000])
    print(f"On: {page.url}")

    # Select External user type
    try:
        external_radio = page.locator('input[value="external"], [data-value="external"], :text("External")').first
        await external_radio.click(timeout=5000)
        print("Selected External")
        await asyncio.sleep(1)
    except:
        print("External selection may not be needed or already selected")

    # Click Create on consent screen
    try:
        create_btn = page.get_by_role("button", name="Create")
        await create_btn.click(timeout=5000)
        print("Clicked Create for consent")
        await asyncio.sleep(5)
    except:
        pass

    # Fill consent screen form
    try:
        # App name
        app_name = page.locator('input[formcontrolname="displayName"], input[aria-label*="App name"], input#appName').first
        if await app_name.is_visible(timeout=5000):
            await app_name.fill("BIM Ops Studio Uploader")
            print("Filled app name")

        # User support email
        email_inputs = await page.locator('input[type="email"]').all()
        for inp in email_inputs:
            try:
                if await inp.is_visible():
                    await inp.fill("weber@bimopsstudio.com")
                    print("Filled email")
            except:
                pass

        # Save
        save_btn = page.get_by_role("button", name="Save and Continue")
        await save_btn.click(timeout=5000)
        print("Saved consent screen")
        await asyncio.sleep(3)
    except Exception as e:
        print(f"Consent form: {e}")

    # Step 5: Create OAuth credentials
    print("\n=== Step 5: Create OAuth 2.0 Credentials ===")
    await page.goto("https://console.cloud.google.com/apis/credentials/oauthclient?project=bimops-youtube",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)
    print(f"On: {page.url}")

    body = await page.inner_text("body")
    with open(r"D:\gcloud_creds.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:5000])

    # Select application type: Desktop app
    try:
        # Click the dropdown for application type
        type_dropdown = page.locator('[aria-label*="Application type"], select, [role="listbox"]').first
        await type_dropdown.click(timeout=5000)
        await asyncio.sleep(1)

        # Select Desktop app
        desktop_option = page.locator('mat-option:has-text("Desktop app"), [role="option"]:has-text("Desktop"), option:has-text("Desktop")').first
        await desktop_option.click(timeout=5000)
        print("Selected Desktop app")
        await asyncio.sleep(1)
    except Exception as e:
        print(f"App type dropdown: {e}")

    # Fill name
    try:
        name_input = page.locator('input[formcontrolname="name"], input[aria-label*="Name"]').first
        if await name_input.is_visible(timeout=3000):
            await name_input.fill("BIM Ops YouTube Uploader")
            print("Filled credential name")
    except:
        pass

    # Click Create
    try:
        create_btn = page.get_by_role("button", name="Create")
        await create_btn.click(timeout=5000)
        print("Clicked Create credentials")
        await asyncio.sleep(5)
    except Exception as e:
        print(f"Create credentials: {e}")

    # Check final state
    body = await page.inner_text("body")
    with open(r"D:\gcloud_final.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:5000])
    print(f"\nFinal URL: {page.url}")
    print("Wrote final state to D:\\gcloud_final.txt")

    # Try to find download button for client secret
    try:
        download_btn = page.locator('button:has-text("Download JSON"), button:has-text("DOWNLOAD JSON"), a:has-text("Download")').first
        if await download_btn.is_visible(timeout=3000):
            await download_btn.click()
            print("Clicked Download JSON!")
            await asyncio.sleep(3)
    except:
        print("Download button not found yet - may need to go to credentials list")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(setup())

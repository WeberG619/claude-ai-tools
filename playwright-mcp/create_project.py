#!/usr/bin/env python3
"""Create Google Cloud project for BIM Ops Studio YouTube"""
import asyncio
from playwright.async_api import async_playwright

async def create():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Step 1: Create project
    print("=== Creating Project ===")
    await page.goto("https://console.cloud.google.com/projectcreate",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)

    # Fill project name
    name_input = page.locator('#p6ntest-name-input')
    await name_input.wait_for(state="visible", timeout=10000)
    await name_input.click()
    await name_input.fill("")
    await name_input.fill("BIM Ops YouTube")
    print("Set project name: BIM Ops YouTube")
    await asyncio.sleep(1)

    # Check what project ID was auto-generated
    try:
        # Try to read the project ID text
        body = await page.inner_text("body")
        for line in body.split("\n"):
            if "project id" in line.lower() or "bim-ops" in line.lower():
                print(f"  {line.strip()[:80]}")
    except:
        pass

    # Click Create
    create_btn = page.locator('button:has-text("Create")').last
    await create_btn.click(timeout=5000)
    print("Clicked Create")
    await asyncio.sleep(10)

    # Wait for redirect to new project
    print(f"After create: {page.url}")

    # Get the project ID from the URL
    import re
    project_match = re.search(r'project=([^&]+)', page.url)
    if project_match:
        project_id = project_match.group(1)
        print(f"Project ID: {project_id}")
    else:
        # Check notifications for the new project
        print("Checking for project creation notification...")
        await asyncio.sleep(5)
        # Try to navigate using the project selector
        await page.goto("https://console.cloud.google.com/cloud-resource-manager",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)
        body = await page.inner_text("body")
        # Look for "BIM Ops" in project list
        for line in body.split("\n"):
            if "bim" in line.lower() and "ops" in line.lower():
                print(f"  Found: {line.strip()[:80]}")

        # Try the most likely project ID
        project_id = "bim-ops-youtube"

    # Step 2: Enable YouTube Data API
    print(f"\n=== Enabling YouTube API on {project_id} ===")
    await page.goto(f"https://console.cloud.google.com/apis/library/youtube.googleapis.com?project={project_id}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(6)

    body = await page.inner_text("body")
    if "manage" in body.lower() or "disable" in body.lower():
        print("Already enabled!")
    else:
        try:
            enable_btn = page.locator('button:has-text("Enable")').first
            await enable_btn.click(timeout=10000)
            print("Enabled YouTube API")
            await asyncio.sleep(8)
        except Exception as e:
            print(f"Enable failed: {e}")

    # Step 3: Configure OAuth consent screen
    print(f"\n=== OAuth Consent Screen ===")
    # Use the old-style API credentials consent URL
    await page.goto(f"https://console.cloud.google.com/apis/credentials/consent?project={project_id}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)

    body = await page.inner_text("body")
    with open(r"D:\gcloud_consent3.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\nProject: {project_id}\n\n")
        f.write(body[:8000])
    print(f"On: {page.url}")

    # Check if we need to configure or if it's already done
    if "need additional access" in body.lower():
        print("PERMISSION ERROR on this project too!")
        print("Your Google Workspace org (bimopsstudio.com) may have restrictions.")
        print("\nTRY THIS: Use a personal Gmail account instead of bimopsstudio.com")
        print("Or: Go to admin.google.com > Security > API Controls to enable access")
    elif "external" in body.lower() and "internal" in body.lower():
        # Need to select user type
        print("Need to configure consent screen")
        try:
            external = page.locator(':text("External")').first
            await external.click(timeout=3000)
            await asyncio.sleep(0.5)
            create = page.locator('button:has-text("Create")').first
            await create.click(timeout=3000)
            print("Selected External and clicked Create")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Consent type selection: {e}")
    elif "get started" in body.lower():
        print("New consent screen UI - clicking Get Started")
        try:
            get_started = page.locator('button:has-text("Get Started"), button:has-text("GET STARTED")').first
            await get_started.click(timeout=5000)
            print("Clicked Get Started")
            await asyncio.sleep(5)
        except:
            pass
    else:
        print("Consent screen may already be configured")

    # Save final state
    body = await page.inner_text("body")
    with open(r"D:\gcloud_state.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\nProject: {project_id}\n\n")
        f.write(body[:8000])
    print(f"\nFinal state saved. URL: {page.url}")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(create())

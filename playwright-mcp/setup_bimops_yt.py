#!/usr/bin/env python3
"""Set up BIM Ops YouTube project - enable API, OAuth consent, credentials"""
import asyncio
from playwright.async_api import async_playwright

PROJECT = "bim-ops-youtube"

async def setup():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Switch to the project first
    print(f"=== Switching to project: {PROJECT} ===")
    await page.goto(f"https://console.cloud.google.com/home/dashboard?project={PROJECT}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)
    print(f"On: {page.url}")

    body = await page.inner_text("body")
    if "need additional access" in body.lower() or "permission" in body.lower():
        print("PERMISSION ISSUE on bim-ops-youtube!")
        with open(r"D:\gcloud_perm_issue.txt", "w", encoding="utf-8") as f:
            f.write(body[:6000])

        # This is likely an org policy issue with bimopsstudio.com
        # Let's check what projects we DO have access to
        print("\nChecking accessible projects...")
        await page.goto("https://console.cloud.google.com/cloud-resource-manager",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)
        body = await page.inner_text("body")
        with open(r"D:\gcloud_accessible.txt", "w", encoding="utf-8") as f:
            f.write(f"URL: {page.url}\n\n")
            f.write(body[:8000])
        print("Saved accessible projects list")

        # List the projects we can see
        for line in body.split("\n"):
            line = line.strip()
            if line and len(line) > 3 and len(line) < 100:
                if any(kw in line.lower() for kw in ["project", "bim", "bridge", "youtube", "ops"]):
                    print(f"  {line}")
    else:
        print("Project accessible! Continuing setup...")

        # Enable YouTube API
        print(f"\n=== Enabling YouTube Data API v3 ===")
        await page.goto(f"https://console.cloud.google.com/apis/library/youtube.googleapis.com?project={PROJECT}",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(6)

        body = await page.inner_text("body")
        if "manage" in body.lower() or "disable" in body.lower():
            print("Already enabled!")
        else:
            try:
                enable_btn = page.locator('button:has-text("Enable")').first
                await enable_btn.click(timeout=10000)
                print("Enabled!")
                await asyncio.sleep(8)
            except:
                print("Could not find Enable button")

        # OAuth consent screen
        print(f"\n=== OAuth Consent Screen ===")
        await page.goto(f"https://console.cloud.google.com/apis/credentials/consent/edit?project={PROJECT}",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)
        body = await page.inner_text("body")
        with open(r"D:\gcloud_consent_final.txt", "w", encoding="utf-8") as f:
            f.write(f"URL: {page.url}\n\n")
            f.write(body[:8000])

        # Create OAuth credentials
        print(f"\n=== Create OAuth Client ===")
        await page.goto(f"https://console.cloud.google.com/apis/credentials?project={PROJECT}",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)

        # Click "Create Credentials" button
        try:
            create_cred = page.locator('button:has-text("Create credentials"), button:has-text("CREATE CREDENTIALS")').first
            await create_cred.click(timeout=5000)
            print("Clicked Create Credentials")
            await asyncio.sleep(2)

            # Select OAuth client ID
            oauth_option = page.locator(':text("OAuth client ID")').first
            await oauth_option.click(timeout=3000)
            print("Selected OAuth client ID")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Create credentials: {e}")

        body = await page.inner_text("body")
        with open(r"D:\gcloud_cred_final.txt", "w", encoding="utf-8") as f:
            f.write(f"URL: {page.url}\n\n")
            f.write(body[:8000])

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(setup())

#!/usr/bin/env python3
"""Fix Google Cloud project - check bimops-youtube or create under right org"""
import asyncio
from playwright.async_api import async_playwright

async def fix():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Step 1: Check the project list
    print("=== Checking project list ===")
    await page.goto("https://console.cloud.google.com/cloud-resource-manager",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(6)

    body = await page.inner_text("body")
    with open(r"D:\gcloud_projects.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:8000])
    print(f"On: {page.url}")
    print("Wrote project list")

    # Step 2: Try to select/switch to bimops-youtube project
    print("\n=== Trying bimops-youtube project ===")
    await page.goto("https://console.cloud.google.com/home/dashboard?project=bimops-youtube",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)

    body = await page.inner_text("body")
    with open(r"D:\gcloud_bimops.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:6000])

    if "need additional access" in body.lower() or "permission" in body.lower():
        print("Permission issue on bimops-youtube project")
        print("Trying to go to IAM to fix permissions...")

        # Try IAM page
        await page.goto(f"https://console.cloud.google.com/iam-admin/iam?project=bimops-youtube",
                        wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(5)
        body = await page.inner_text("body")
        with open(r"D:\gcloud_iam.txt", "w", encoding="utf-8") as f:
            f.write(f"URL: {page.url}\n\n")
            f.write(body[:6000])
        print(f"IAM page: {page.url}")

        if "need additional access" in body.lower():
            print("Also no IAM access. Project may need org admin to fix.")
            print("Let's try creating a new project with a different name...")

            # Create a new project
            await page.goto("https://console.cloud.google.com/projectcreate",
                            wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(5)

            # Dump the create page to understand the form
            body = await page.inner_text("body")
            with open(r"D:\gcloud_create.txt", "w", encoding="utf-8") as f:
                f.write(f"URL: {page.url}\n\n")
                f.write(body[:6000])

            # List ALL form elements
            print("\nCreate project form elements:")
            all_elements = await page.locator("input, select, textarea, button, [role='combobox'], [role='listbox']").all()
            for i, el in enumerate(all_elements[:30]):
                try:
                    if not await el.is_visible():
                        continue
                    tag = await el.evaluate("el => el.tagName")
                    label = await el.get_attribute("aria-label") or ""
                    el_id = await el.get_attribute("id") or ""
                    name = await el.get_attribute("name") or ""
                    try:
                        val = await el.input_value()
                    except:
                        val = (await el.inner_text())[:50]
                    print(f"  {tag} id='{el_id}' label='{label}' name='{name}' val='{val[:50]}'")
                except:
                    pass
    else:
        print("bimops-youtube project is accessible!")
        # Continue with OAuth setup on this project
        print("Proceeding with API setup...")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(fix())

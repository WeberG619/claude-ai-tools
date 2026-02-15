#!/usr/bin/env python3
"""Navigate to client detail page and extract credentials"""
import asyncio
import os
import json
from playwright.async_api import async_playwright

PROJECT = "bim-ops-youtube"
CLIENT_ID = "596602069942-kl9ad3gejjvv68gbjlcaqu61mbg7j4mc.apps.googleusercontent.com"

async def download():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Try navigating directly to the client detail page
    print("=== Navigating to Client Detail ===")
    detail_url = f"https://console.cloud.google.com/auth/clients/{CLIENT_ID}?project={PROJECT}"
    await page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(8)
    print(f"On: {page.url}")

    body = await page.inner_text("body")
    with open(r"D:\gcloud_client_detail2.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:15000])

    # Look for client secret on the page
    client_secret = ""
    print("\nSearching for credentials on page...")
    for line in body.split("\n"):
        line = line.strip()
        if ".apps.googleusercontent.com" in line:
            print(f"  Client ID: {line[:80]}")
        if line.startswith("GOCSPX-"):
            client_secret = line
            print(f"  Client Secret: {client_secret[:20]}...")
        if "client secret" in line.lower():
            print(f"  Secret label: {line[:60]}")

    # Check for download button
    print("\nDownload buttons:")
    for sel in ['button:has-text("Download")', 'a:has-text("Download")',
                 '[aria-label*="Download"]', '[aria-label*="download"]',
                 'button:has-text("JSON")']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=2000):
                text = (await btn.inner_text())[:40]
                print(f"  Found: '{text}'")
        except:
            pass

    # Look for "show secret" or copy buttons
    print("\nAction buttons:")
    buttons = await page.locator("button, [role='button']").all()
    for btn in buttons[:25]:
        try:
            if not await btn.is_visible():
                continue
            text = (await btn.inner_text())[:40].strip()
            label = await btn.get_attribute("aria-label") or ""
            if text and text not in ["Dismiss", "Start free", "Keyboard shortcuts", "Search"]:
                info = f"  btn: text='{text}'"
                if label:
                    info += f" label='{label[:30]}'"
                print(info)
        except:
            pass

    # Try to set download behavior and click download
    print("\nAttempting download...")
    try:
        cdp = await page.context.new_cdp_session(page)
        await cdp.send("Browser.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": r"D:\_CLAUDE-TOOLS\youtube-uploader",
            "eventsEnabled": True
        })

        for sel in ['button:has-text("Download")', 'a:has-text("Download")',
                     '[aria-label*="Download"]']:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    print(f"  Clicked: {sel}")
                    await asyncio.sleep(5)
                    break
            except:
                pass
    except Exception as e:
        print(f"  Download error: {e}")

    # Check if file appeared
    target_dir = r"D:\_CLAUDE-TOOLS\youtube-uploader"
    for f_name in os.listdir(target_dir):
        if f_name.endswith(".json"):
            fpath = os.path.join(target_dir, f_name)
            print(f"  Found JSON: {fpath}")

    # If we still don't have the secret, check if it's visible now
    if not client_secret:
        body = await page.inner_text("body")
        for line in body.split("\n"):
            line = line.strip()
            if line.startswith("GOCSPX-"):
                client_secret = line
                print(f"  Found secret after actions: {client_secret[:20]}...")

    # If we have the secret, construct the JSON
    if client_secret:
        print(f"\n=== Constructing client_secret.json ===")
        client_json = {
            "installed": {
                "client_id": CLIENT_ID,
                "project_id": PROJECT,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": client_secret,
                "redirect_uris": ["http://localhost"]
            }
        }
        save_path = r"D:\_CLAUDE-TOOLS\youtube-uploader\client_secret.json"
        with open(save_path, "w") as f:
            json.dump(client_json, f, indent=2)
        print(f"  Saved to: {save_path}")
    else:
        print("\nClient secret not found on page.")
        print("Full body scan for potential secrets...")
        # Look for any string that looks like a client secret
        import re
        for line in body.split("\n"):
            line = line.strip()
            # Client secrets are usually 24+ chars alphanumeric
            if re.match(r'^[A-Za-z0-9_-]{24,}$', line) and not ".apps." in line:
                print(f"  Potential secret: {line[:20]}...")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(download())

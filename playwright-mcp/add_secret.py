#!/usr/bin/env python3
"""Try old-style credentials page or add secret with confirmation"""
import asyncio
import json
import time
from playwright.async_api import async_playwright

PROJECT = "bim-ops-youtube"
CLIENT_ID = "596602069942-kl9ad3gejjvv68gbjlcaqu61mbg7j4mc.apps.googleusercontent.com"

async def get_secret():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Try the old-style API credentials page
    print("=== Trying old-style credentials page ===")
    await page.goto(f"https://console.cloud.google.com/apis/credentials?project={PROJECT}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(8)
    print(f"On: {page.url}")

    body = await page.inner_text("body")
    with open(r"D:\gcloud_old_creds.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:15000])

    # Look for download icon/button
    print("\nSearching for download options on old page...")
    for line in body.split("\n"):
        line = line.strip()
        if any(kw in line.lower() for kw in ["download", "json", "bim ops", "596"]):
            print(f"  {line[:100]}")

    # Look for download icons (the old page has download arrow icons)
    print("\nAction buttons/icons:")
    actions = await page.locator("button, [role='button'], a").all()
    for act in actions[:30]:
        try:
            if not await act.is_visible():
                continue
            label = await act.get_attribute("aria-label") or ""
            text = (await act.inner_text())[:40].strip()
            title = await act.get_attribute("title") or ""
            if any(kw in label.lower() + text.lower() + title.lower()
                   for kw in ["download", "json", "secret"]):
                print(f"  text='{text}' label='{label}' title='{title}'")
        except:
            pass

    # Try the old edit page for this client
    print("\n=== Trying old edit page ===")
    edit_url = f"https://console.cloud.google.com/apis/credentials/oauthclient/{CLIENT_ID}?project={PROJECT}"
    await page.goto(edit_url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(8)
    print(f"On: {page.url}")

    body = await page.inner_text("body")
    with open(r"D:\gcloud_old_edit.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:15000])

    # Search for secret
    client_secret = ""
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("GOCSPX-"):
            client_secret = line
            print(f"  FOUND SECRET: {client_secret}")
            break
        if "secret" in line.lower():
            print(f"  {line[:100]}")

    # Look for download JSON on this page
    print("\nDownload options:")
    for sel in ['button:has-text("Download")', 'a:has-text("Download JSON")',
                 '[aria-label*="Download"]', 'a[href*="download"]']:
        try:
            btn = page.locator(sel).first
            if await btn.is_visible(timeout=2000):
                text = (await btn.inner_text())[:40]
                label = await btn.get_attribute("aria-label") or ""
                print(f"  Found: text='{text}' label='{label}'")
        except:
            pass

    if not client_secret:
        # Go back to new page and try Add secret with careful monitoring
        print("\n=== Adding new secret with monitoring ===")
        detail_url = f"https://console.cloud.google.com/auth/clients/{CLIENT_ID}?project={PROJECT}"
        await page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(8)

        # Intercept network responses to capture the secret
        secrets_found = []

        def on_response(response):
            if "secret" in response.url.lower() or "client" in response.url.lower():
                try:
                    # Don't await - just log
                    print(f"  Network: {response.status} {response.url[:80]}")
                except:
                    pass

        page.on("response", on_response)

        # Click Add secret
        try:
            add_btn = page.locator('button:has-text("Add secret")').first
            await add_btn.click(timeout=5000)
            print("Clicked Add secret")
            await asyncio.sleep(3)

            # Check for confirmation dialog
            body = await page.inner_text("body")
            if "confirm" in body.lower() or "are you sure" in body.lower():
                print("Confirmation dialog found!")
                # Click confirm/yes/ok
                for sel in ['button:has-text("Confirm")', 'button:has-text("Yes")',
                             'button:has-text("OK")', 'button:has-text("Add")']:
                    try:
                        btn = page.locator(sel).first
                        if await btn.is_visible(timeout=2000):
                            await btn.click()
                            print(f"  Clicked {sel}")
                            await asyncio.sleep(5)
                            break
                    except:
                        pass

            # Now check for the new secret
            await asyncio.sleep(3)
            body = await page.inner_text("body")
            with open(r"D:\gcloud_after_add.txt", "w", encoding="utf-8") as f:
                f.write(f"URL: {page.url}\n\n")
                f.write(body[:15000])

            for line in body.split("\n"):
                line = line.strip()
                if line.startswith("GOCSPX-"):
                    client_secret = line
                    print(f"  FOUND NEW SECRET: {client_secret}")
                    break

            # Check for any popup/dialog/toast
            overlays = await page.locator('[role="dialog"], .cdk-overlay-pane, [class*="snack"], [class*="toast"]').all()
            for ov in overlays:
                try:
                    if await ov.is_visible():
                        text = await ov.inner_text()
                        print(f"  Overlay: {text[:200]}")
                        for line in text.split("\n"):
                            if line.strip().startswith("GOCSPX-"):
                                client_secret = line.strip()
                                print(f"  FOUND SECRET IN OVERLAY: {client_secret}")
                except:
                    pass

        except Exception as e:
            print(f"  Add secret error: {e}")

    # If we have the secret, save it
    if client_secret:
        print(f"\n=== Saving client_secret.json ===")
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
        print(f"  SAVED: {save_path}")
    else:
        print("\nCould not capture secret via UI.")
        print("Trying gcloud CLI approach...")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(get_secret())

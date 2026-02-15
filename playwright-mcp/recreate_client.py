#!/usr/bin/env python3
"""Delete and recreate OAuth client, intercepting API response to capture secret"""
import asyncio
import json
from playwright.async_api import async_playwright

PROJECT = "bim-ops-youtube"
CLIENT_ID = "596602069942-kl9ad3gejjvv68gbjlcaqu61mbg7j4mc.apps.googleusercontent.com"

captured_secret = None

async def recreate():
    global captured_secret
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Step 1: Delete the existing client
    print("=== Deleting existing client ===")
    detail_url = f"https://console.cloud.google.com/auth/clients/{CLIENT_ID}?project={PROJECT}"
    await page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(6)

    try:
        delete_btn = page.locator('button:has-text("Delete"), a:has-text("Delete")').first
        await delete_btn.click(timeout=5000)
        print("  Clicked Delete")
        await asyncio.sleep(3)

        # Confirm deletion
        body = await page.inner_text("body")
        if "confirm" in body.lower() or "delete" in body.lower():
            for sel in ['button:has-text("Delete")', 'button:has-text("Confirm")',
                         'button:has-text("OK")', 'button:has-text("Yes")']:
                try:
                    btn = page.locator(sel).last  # Use last to get the confirm dialog button
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        print(f"  Confirmed deletion: {sel}")
                        await asyncio.sleep(5)
                        break
                except:
                    pass
        print(f"  After delete: {page.url}")
    except Exception as e:
        print(f"  Delete error: {e}")

    # Step 2: Create a new client with network interception
    print("\n=== Creating new OAuth client with interception ===")
    await page.goto(f"https://console.cloud.google.com/auth/clients/create?project={PROJECT}",
                    wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(8)

    # Set up network response interception
    async def handle_response(response):
        global captured_secret
        url = response.url
        if any(kw in url.lower() for kw in ["oauthclient", "clients", "credential", "oauth2"]):
            try:
                body = await response.text()
                if "GOCSPX-" in body or "client_secret" in body:
                    print(f"  INTERCEPTED secret in response: {url[:80]}")
                    # Parse the JSON response
                    try:
                        data = json.loads(body)
                        if "clientSecret" in str(data):
                            print(f"  Response data keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                            # Save raw response
                            with open(r"D:\gcloud_api_response.json", "w") as f:
                                json.dump(data, f, indent=2)
                    except:
                        pass
                    # Also save raw text
                    with open(r"D:\gcloud_api_raw.txt", "w") as f:
                        f.write(body[:5000])
            except:
                pass

    page.on("response", handle_response)

    # Select Desktop app
    print("Selecting Desktop app...")
    try:
        app_type_dd = page.locator('#_0rif_cfc-select-0')
        await app_type_dd.wait_for(state="visible", timeout=8000)
        await app_type_dd.click()
        await asyncio.sleep(2)

        opt = page.locator('[role="option"]:has-text("Desktop app")').first
        await opt.click(timeout=3000)
        print("  Selected Desktop app")
        await asyncio.sleep(3)
    except Exception as e:
        print(f"  App type: {e}")

    # Fill name
    try:
        inputs = await page.locator("input").all()
        for inp in inputs:
            if await inp.is_visible():
                el_id = await inp.get_attribute("id") or ""
                el_type = await inp.get_attribute("type") or ""
                if el_type == "search" or "search" in el_id:
                    continue
                val = await inp.input_value()
                if "Desktop client" in val or not val:
                    await inp.fill("BIM Ops YouTube Uploader")
                    print("  Filled name")
                    break
    except:
        pass

    # Click Create
    try:
        create_btn = page.locator('button:has-text("Create")').first
        await create_btn.click(timeout=5000)
        print("  Clicked Create")
        await asyncio.sleep(10)
    except Exception as e:
        print(f"  Create: {e}")

    # Check for dialog with secret
    print("\nChecking for creation dialog...")
    body = await page.inner_text("body")

    # Look for secret in page text
    new_client_id = ""
    new_secret = ""
    for line in body.split("\n"):
        line = line.strip()
        if ".apps.googleusercontent.com" in line and "Client:" not in line:
            new_client_id = line
        if line.startswith("GOCSPX-"):
            new_secret = line

    # Check dialog content specifically
    dialogs = await page.locator('[role="dialog"], .cdk-overlay-pane, .mat-mdc-dialog-container').all()
    for d in dialogs:
        try:
            if await d.is_visible():
                d_text = await d.inner_text()
                print(f"  Dialog: {d_text[:300]}")

                # Also check for copy-able elements inside dialog
                copy_els = await d.locator('[class*="copy"], [class*="value"], code, pre, input, [class*="secret"]').all()
                for cel in copy_els:
                    try:
                        cel_text = ""
                        try:
                            cel_text = await cel.input_value()
                        except:
                            cel_text = (await cel.inner_text())[:100]
                        if cel_text:
                            print(f"    Copy element: '{cel_text[:60]}'")
                            if cel_text.startswith("GOCSPX-"):
                                new_secret = cel_text
                    except:
                        pass

                # Look for the secret by checking all spans/divs in dialog
                spans = await d.locator("span, div").all()
                for s in spans:
                    try:
                        if not await s.is_visible():
                            continue
                        t = (await s.inner_text())[:100]
                        # Check for secret-like string
                        if t.startswith("GOCSPX-"):
                            new_secret = t.strip()
                            print(f"    SECRET FOUND: {new_secret}")
                    except:
                        pass
        except:
            pass

    # Also try clipboard approach - copy client ID, then copy secret
    if not new_secret:
        print("\nTrying to copy from dialog elements...")
        # There might be a "Copy" icon/button next to the secret
        copy_btns = await page.locator('[aria-label*="Copy"], [aria-label*="copy"], [title*="Copy"], button:has-text("copy")').all()
        for i, btn in enumerate(copy_btns):
            try:
                if await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(0.5)
                    # Try to read clipboard via JS
                    try:
                        clip = await page.evaluate("navigator.clipboard.readText()")
                        print(f"  Copy btn {i} clipboard: {clip[:40]}")
                        if clip.startswith("GOCSPX-"):
                            new_secret = clip
                            break
                    except:
                        pass
            except:
                pass

    # Try reading from intercepted API response file
    if not new_secret:
        try:
            with open(r"D:\gcloud_api_response.json", "r") as f:
                data = json.load(f)
                print(f"\nIntercepted API response: {json.dumps(data, indent=2)[:500]}")
        except FileNotFoundError:
            pass
        try:
            with open(r"D:\gcloud_api_raw.txt", "r") as f:
                raw = f.read()
                print(f"\nRaw API response: {raw[:500]}")
        except FileNotFoundError:
            pass

    # Save the result
    with open(r"D:\gcloud_recreate_result.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(f"Client ID: {new_client_id}\n")
        f.write(f"Client Secret: {new_secret}\n\n")
        f.write(body[:15000])

    if new_client_id and new_secret:
        print(f"\n=== SUCCESS ===")
        print(f"  Client ID: {new_client_id}")
        print(f"  Client Secret: {new_secret[:15]}...")
        client_json = {
            "installed": {
                "client_id": new_client_id,
                "project_id": PROJECT,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret": new_secret,
                "redirect_uris": ["http://localhost"]
            }
        }
        save_path = r"D:\_CLAUDE-TOOLS\youtube-uploader\client_secret.json"
        with open(save_path, "w") as f:
            json.dump(client_json, f, indent=2)
        print(f"  SAVED: {save_path}")
    elif new_client_id:
        print(f"\n  Got Client ID: {new_client_id}")
        print("  But secret not captured. Check the dialog on screen!")
        # DON'T click OK yet - leave dialog open for user
        print("  LEAVING DIALOG OPEN - check screen for secret!")
    else:
        print("\nClient creation may have failed or dialog not captured.")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(recreate())

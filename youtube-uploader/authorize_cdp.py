#!/usr/bin/env python3
"""
YouTube OAuth authorization via Chrome CDP browser.
Instead of opening a new browser, uses the existing Chrome CDP session
where the user is already logged into Google.
"""
import asyncio
import json
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from playwright.async_api import async_playwright

SCRIPT_DIR = Path(__file__).parent
CLIENT_SECRET_FILE = SCRIPT_DIR / "client_secret.json"
TOKEN_FILE = SCRIPT_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.readonly",
]

REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"  # Manual copy/paste flow

async def authorize():
    # Load client secret
    with open(CLIENT_SECRET_FILE) as f:
        client_data = json.load(f)
    installed = client_data["installed"]
    client_id = installed["client_id"]
    client_secret = installed["client_secret"]

    # Construct OAuth URL
    auth_url = "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    })

    print(f"Auth URL: {auth_url[:80]}...")

    # Connect to CDP browser
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = await ctx.new_page()

    # Navigate to auth URL
    print("\nNavigating to Google OAuth consent...")
    await page.goto(auth_url, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(5)
    print(f"On: {page.url}")

    body = await page.inner_text("body")

    # Handle account selection if needed
    if "choose an account" in body.lower() or "select an account" in body.lower():
        print("Account selection page - choosing weber@bimopsstudio.com...")
        try:
            account = page.locator(':text("weber@bimopsstudio.com")').first
            await account.click(timeout=5000)
            await asyncio.sleep(5)
            body = await page.inner_text("body")
        except:
            # Try clicking the first account
            try:
                account = page.locator('[data-email]').first
                await account.click(timeout=5000)
                await asyncio.sleep(5)
                body = await page.inner_text("body")
            except:
                pass

    print(f"After account selection: {page.url}")

    # Handle "Google hasn't verified this app" warning
    if "hasn't verified" in body.lower() or "unverified" in body.lower() or "unsafe" in body.lower():
        print("Unverified app warning - clicking 'Advanced' then 'Go to...'")
        try:
            # Click "Advanced" or "Show Advanced"
            advanced = page.locator(':text("Advanced"), :text("Show Advanced")').first
            await advanced.click(timeout=5000)
            await asyncio.sleep(2)

            # Click "Go to BIM Ops Studio Uploader (unsafe)"
            go_to = page.locator('a:has-text("Go to"), a:has-text("unsafe")').first
            await go_to.click(timeout=5000)
            await asyncio.sleep(5)
            body = await page.inner_text("body")
        except Exception as e:
            print(f"  Warning bypass: {e}")

    print(f"Consent page: {page.url}")

    # Handle consent - click "Allow" or "Continue"
    if "allow" in body.lower() or "grant" in body.lower() or "access" in body.lower():
        print("Granting permissions...")

        # Click Allow/Continue/Grant
        for text in ["Continue", "Allow", "Grant"]:
            try:
                btn = page.locator(f'button:has-text("{text}")').first
                if await btn.is_visible(timeout=3000):
                    await btn.click()
                    print(f"  Clicked '{text}'")
                    await asyncio.sleep(5)
                    break
            except:
                pass

    # After consent, we should be redirected to the OOB page with the auth code
    # OR we might need to handle more consent steps
    print(f"After consent: {page.url}")
    body = await page.inner_text("body")

    # Check for another "Allow" step
    if "allow" in body.lower():
        for text in ["Allow", "Continue", "Grant", "Confirm"]:
            try:
                btn = page.locator(f'button:has-text("{text}")').first
                if await btn.is_visible(timeout=3000):
                    await btn.click()
                    print(f"  Clicked '{text}'")
                    await asyncio.sleep(5)
                    break
            except:
                pass

    # Check for auth code in URL or page
    print(f"Final URL: {page.url}")
    body = await page.inner_text("body")

    auth_code = None

    # Check URL for code parameter
    if "code=" in page.url:
        parsed = urllib.parse.urlparse(page.url)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            auth_code = params["code"][0]
            print(f"  Auth code from URL: {auth_code[:20]}...")
    # Check if code is shown on page (OOB flow)
    elif "authorization code" in body.lower() or "4/" in body:
        for line in body.split("\n"):
            line = line.strip()
            if line.startswith("4/"):
                auth_code = line
                print(f"  Auth code from page: {auth_code[:20]}...")
                break

    # Also check for code in input/textarea elements
    if not auth_code:
        inputs = await page.locator("input, textarea, code, pre").all()
        for inp in inputs:
            try:
                if await inp.is_visible():
                    try:
                        val = await inp.input_value()
                    except:
                        val = (await inp.inner_text())[:200]
                    if val and ("4/" in val or len(val) > 20):
                        auth_code = val.strip()
                        print(f"  Auth code from element: {auth_code[:20]}...")
                        break
            except:
                pass

    # Save page state for debugging
    with open(r"D:\gcloud_oauth_result.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:10000])

    if auth_code:
        print(f"\n=== Exchanging auth code for token ===")
        # Exchange auth code for tokens
        token_data = urllib.parse.urlencode({
            "code": auth_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }).encode()

        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=token_data,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        try:
            with urllib.request.urlopen(req) as resp:
                token_response = json.loads(resp.read())
                print(f"  Access token: {token_response.get('access_token', '')[:20]}...")
                print(f"  Refresh token: {'present' if token_response.get('refresh_token') else 'MISSING'}")
                print(f"  Scope: {token_response.get('scope', '')[:60]}")

                # Save token in google-auth format
                token_json = {
                    "token": token_response["access_token"],
                    "refresh_token": token_response.get("refresh_token", ""),
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scopes": SCOPES,
                }

                with open(TOKEN_FILE, "w") as f:
                    json.dump(token_json, f, indent=2)
                print(f"\n  Token saved to: {TOKEN_FILE}")
                print("  YouTube API is ready for uploads!")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            print(f"  Token exchange failed: {e.code}")
            print(f"  Error: {error_body[:200]}")
    else:
        print("\nAuth code not captured. Check the browser - you may need to:")
        print("  1. Select your Google account")
        print("  2. Click 'Advanced' > 'Go to BIM Ops Studio Uploader (unsafe)'")
        print("  3. Grant all permissions")
        print("Check D:\\gcloud_oauth_result.txt for current page state")

    # Close the auth tab
    await page.close()
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(authorize())

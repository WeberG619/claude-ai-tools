#!/usr/bin/env python3
"""Update Twitter/X profile and post first tweet"""
import asyncio
from playwright.async_api import async_playwright

NEW_BIO = """Founder, BIM Ops Studio. Building AI agents that control Autodesk Revit through natural language.

Open source: RevitMCPBridge
Voice-to-BIM | Floor Plan ML | 15+ MCP servers

#BIM #AI #Revit #AEC"""

NEW_LOCATION = "Seattle, WA"
NEW_WEBSITE = "bimopsstudio.com"
NEW_NAME = "Weber Gouin"

# Adapted from LinkedIn post for Twitter format (concise)
TWEET = """I built a voice assistant that talks to Revit.

I say: "Create a floor plan with three bedrooms and a central hallway."

What happens:
→ Voice transcribed in real time
→ Claude interprets intent → BIM operations
→ Commands flow through RevitMCPBridge via named pipes
→ Revit executes: walls go up, doors placed, rooms tagged

Natural language to BIM geometry in seconds. No menus. No clicking.

The design intent goes straight from your voice to Revit's API.

Built solo at BIM Ops Studio. Open source.

github.com/bimopsstudio/RevitMCPBridge2026

#BIM #AI #Revit #AEC #Architecture #VoiceAI #RevitAPI"""


async def setup():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # ===== UPDATE PROFILE =====
    print("--- Updating Profile ---")
    await page.goto("https://x.com/settings/profile", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(4)

    # Find and fill fields
    # Name field
    try:
        name_input = page.locator('input[name="displayName"]').first
        await name_input.wait_for(state="visible", timeout=5000)
        await name_input.fill("")
        await name_input.fill(NEW_NAME)
        print(f"Set name: {NEW_NAME}")
    except Exception as e:
        print(f"Name field not found by name attr, trying alternatives: {e}")
        # List all inputs
        inputs = await page.locator("input").all()
        for i, inp in enumerate(inputs[:15]):
            try:
                if not await inp.is_visible():
                    continue
                name = await inp.get_attribute("name") or ""
                placeholder = await inp.get_attribute("placeholder") or ""
                val = await inp.input_value()
                data_testid = await inp.get_attribute("data-testid") or ""
                print(f"  input {i}: name='{name}' ph='{placeholder}' testid='{data_testid}' val='{val[:50]}'")
            except:
                pass

    # Bio field
    try:
        bio_textarea = page.locator('textarea[name="description"]').first
        await bio_textarea.wait_for(state="visible", timeout=5000)
        await bio_textarea.fill("")
        await bio_textarea.fill(NEW_BIO)
        print(f"Set bio ({len(NEW_BIO)} chars)")
    except Exception as e:
        print(f"Bio textarea not found by name, trying alternatives: {e}")
        textareas = await page.locator("textarea").all()
        for i, ta in enumerate(textareas[:10]):
            try:
                if not await ta.is_visible():
                    continue
                name = await ta.get_attribute("name") or ""
                placeholder = await ta.get_attribute("placeholder") or ""
                val = await ta.input_value()
                print(f"  textarea {i}: name='{name}' ph='{placeholder}' val='{val[:50]}'")
            except:
                pass

    # Location field
    try:
        location_input = page.locator('input[name="location"]').first
        await location_input.wait_for(state="visible", timeout=5000)
        await location_input.fill("")
        await location_input.fill(NEW_LOCATION)
        print(f"Set location: {NEW_LOCATION}")
    except Exception as e:
        print(f"Location not found: {e}")

    # Website field
    try:
        website_input = page.locator('input[name="url"]').first
        await website_input.wait_for(state="visible", timeout=5000)
        await website_input.fill("")
        await website_input.fill(NEW_WEBSITE)
        print(f"Set website: {NEW_WEBSITE}")
    except Exception as e:
        print(f"Website not found: {e}")

    # Save profile
    try:
        save_btn = page.locator('[data-testid="Profile_Save_Button"], button:has-text("Save")').first
        await save_btn.click(timeout=5000)
        print("Saved profile!")
        await asyncio.sleep(3)
    except Exception as e:
        print(f"Save failed: {e}")

    # ===== POST TWEET =====
    print("\n--- Posting Tweet ---")
    await page.goto("https://x.com/compose/post", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(3)

    # Find the tweet composer
    try:
        editor = page.locator('[data-testid="tweetTextarea_0"], [role="textbox"]').first
        await editor.wait_for(state="visible", timeout=10000)
        await editor.click()
        await asyncio.sleep(0.5)

        # Type the tweet (fill doesn't always work on Twitter's editor)
        await editor.fill(TWEET)
        await asyncio.sleep(1)

        # Verify
        entered = await editor.inner_text()
        print(f"Entered {len(entered)} chars in composer")

        if len(entered) < 50:
            # fill() didn't work, try keyboard typing
            print("fill() may not have worked, trying keyboard.type()")
            await editor.click()
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Delete")
            await asyncio.sleep(0.3)
            await page.keyboard.type(TWEET, delay=5)
            await asyncio.sleep(1)
            entered = await editor.inner_text()
            print(f"After keyboard.type: {len(entered)} chars")

    except Exception as e:
        print(f"Could not find tweet composer: {e}")

    # Click Post button
    try:
        post_btn = page.locator('[data-testid="tweetButton"]').first
        await post_btn.click(timeout=5000)
        print("Clicked Post button!")
        await asyncio.sleep(3)
        print("TWEET POSTED SUCCESSFULLY")
    except Exception as e:
        print(f"Could not post: {e}")

    # ===== FOLLOW KEY ACCOUNTS =====
    print("\n--- Following Key Accounts ---")
    accounts_to_follow = [
        "AnthropicAI",      # Anthropic (Claude maker)
        "ClaudeAI",         # Claude AI
        "AutodeskRevit",    # Autodesk Revit
        "Autodesk",         # Autodesk
        "AaborneJay",       # Jay Aabornee - Revit community
        "DynamoBIM",        # Dynamo for Revit
    ]

    for account in accounts_to_follow:
        try:
            await page.goto(f"https://x.com/{account}", wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)

            # Check if already following
            body = await page.inner_text("body")
            if "Following" in body[:500]:
                print(f"  Already following @{account}")
                continue

            follow_btn = page.locator('[data-testid*="follow"]').first
            btn_text = await follow_btn.inner_text()
            if btn_text == "Follow":
                await follow_btn.click(timeout=3000)
                print(f"  Followed @{account}")
                await asyncio.sleep(1)
            else:
                print(f"  @{account}: button says '{btn_text}', skipping")
        except Exception as e:
            print(f"  Could not follow @{account}: {e}")

    print("\n=== TWITTER SETUP COMPLETE ===")
    await pw.stop()

if __name__ == "__main__":
    asyncio.run(setup())

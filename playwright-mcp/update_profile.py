#!/usr/bin/env python3
"""Update LinkedIn profile headline and About section"""
import asyncio
import traceback
from playwright.async_api import async_playwright

NEW_HEADLINE = "Founder at BIM Ops Studio | Building AI agents that control Revit | Open Source RevitMCPBridge | ADN Member"

NEW_ABOUT = """After 15 years in architecture and BIM, I started building the tools I wished existed.

I'm the founder of BIM Ops Studio, where I develop AI-driven automation for Revit and the AEC industry.

What I've built:
\u2192 RevitMCPBridge \u2014 An open source AI agent that controls Autodesk Revit through natural language. No plugins, no Dynamo. Just intent \u2192 model.
\u2192 Voice-to-BIM \u2014 A Jarvis-style voice assistant that talks directly to Revit's API.
\u2192 Floor Plan ML Pipeline \u2014 Teaching AI to read architectural drawings and convert them into Revit models.
\u2192 15+ MCP servers running in parallel \u2014 Email, calendar, code reviews, browser automation, and Revit all managed by a single AI agent.

The tech stack: Claude (Anthropic), Model Context Protocol, C#/.NET, Python, Named Pipes.

I believe the future of AEC is conversational \u2014 architects describing intent, AI executing in the model. I'm building that future right now, in production, every day.

Open source: github.com/bimopsstudio
Website: bimopsstudio.com
Contact: weber@bimopsstudio.com"""


async def update_profile():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Navigate to profile
    await page.goto("https://www.linkedin.com/in/me/", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(4)
    print(f"On profile: {page.url}")

    # ===== UPDATE HEADLINE =====
    print("\n--- Updating Headline ---")

    # Click the "Edit profile" button (pencil icon near name)
    try:
        edit_btn = page.locator('button[aria-label="Edit profile"]').first
        await edit_btn.click(timeout=5000)
        print("Clicked 'Edit profile' button")
        await asyncio.sleep(3)
    except Exception as e:
        print(f"Could not find Edit profile button: {e}")
        # List all buttons to debug
        buttons = await page.locator("button").all()
        for i, btn in enumerate(buttons[:30]):
            label = await btn.get_attribute("aria-label") or ""
            text = (await btn.inner_text())[:50] if await btn.is_visible() else ""
            if label or text:
                print(f"  btn {i}: aria-label='{label}' text='{text}'")

    # Find and update the headline field - first list all inputs to find it
    try:
        # Try multiple selectors for headline
        headline_input = None
        for selector in [
            'input[id*="headline"]',
            'input[aria-label*="Headline"]',
            'textarea[aria-label*="Headline"]',
            'input[name*="headline"]',
        ]:
            try:
                el = page.locator(selector).first
                if await el.is_visible(timeout=1000):
                    headline_input = el
                    print(f"Found headline via: {selector}")
                    break
            except:
                continue

        if not headline_input:
            # List all visible inputs/textareas to find headline
            print("Listing all inputs to find headline field:")
            inputs = await page.locator("input, textarea").all()
            for i, inp in enumerate(inputs[:30]):
                try:
                    if not await inp.is_visible():
                        continue
                    label = await inp.get_attribute("aria-label") or ""
                    name = await inp.get_attribute("name") or ""
                    placeholder = await inp.get_attribute("placeholder") or ""
                    inp_id = await inp.get_attribute("id") or ""
                    val = (await inp.input_value())[:80]
                    print(f"  input {i}: id='{inp_id}' label='{label}' name='{name}' ph='{placeholder}' val='{val}'")
                except:
                    pass

        if headline_input:
            await headline_input.fill("")
            await headline_input.fill(NEW_HEADLINE)
            print(f"Filled headline: {NEW_HEADLINE[:60]}...")
        else:
            print("Could not locate headline input")
    except Exception as e:
        print(f"Headline update error: {e}")

    # Save the intro changes
    try:
        save_btn = page.get_by_role("button", name="Save")
        await save_btn.click(timeout=5000)
        print("Saved intro changes")
        await asyncio.sleep(3)
    except Exception as e:
        print(f"Could not click Save: {e}")

    # ===== UPDATE ABOUT SECTION =====
    print("\n--- Updating About Section ---")

    # Navigate back to profile if needed
    if "edit" in page.url.lower():
        await page.goto("https://www.linkedin.com/in/me/", wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(3)

    # Scroll down to About section
    await page.mouse.wheel(0, 500)
    await asyncio.sleep(1)

    # Find and click the edit button for the About section
    try:
        about_edit = page.locator('button[aria-label="Edit about"]').first
        await about_edit.click(timeout=5000)
        print("Clicked 'Edit about' button")
        await asyncio.sleep(2)
    except Exception as e:
        print(f"Could not find Edit about button: {e}")
        # Try finding the section and its edit button
        try:
            # Look for pencil icon near "About" heading
            about_section = page.locator('#about').first
            edit_btn = about_section.locator('xpath=..').locator('button').first
            await edit_btn.click(timeout=5000)
            print("Clicked About edit via section locator")
            await asyncio.sleep(2)
        except Exception as e2:
            print(f"Section approach also failed: {e2}")

    # Find the About text area and update it
    try:
        about_textarea = None
        for selector in [
            'textarea[aria-label*="About"]',
            'textarea[aria-label*="about"]',
            'textarea[aria-label*="Summary"]',
            'textarea[aria-label*="summary"]',
            'div[role="textbox"]',
            '[contenteditable="true"]',
            'textarea',
        ]:
            try:
                el = page.locator(selector).first
                if await el.is_visible(timeout=1000):
                    about_textarea = el
                    print(f"Found About textarea via: {selector}")
                    break
            except:
                continue

        if not about_textarea:
            print("Listing all textareas and editable elements:")
            for sel in ["textarea", "[contenteditable]", "div[role='textbox']", "input"]:
                elements = await page.locator(sel).all()
                for i, el in enumerate(elements[:10]):
                    try:
                        vis = await el.is_visible()
                        label = await el.get_attribute("aria-label") or ""
                        el_id = await el.get_attribute("id") or ""
                        role = await el.get_attribute("role") or ""
                        print(f"  {sel}[{i}]: visible={vis} id='{el_id}' label='{label}' role='{role}'")
                    except:
                        pass

        if about_textarea:
            await about_textarea.fill("")
            await about_textarea.fill(NEW_ABOUT)
            print(f"Filled About section ({len(NEW_ABOUT)} chars)")
        else:
            print("Could not locate About textarea")
    except Exception as e:
        print(f"About update error: {e}")

    # Save About changes
    try:
        save_btn = page.get_by_role("button", name="Save")
        await save_btn.click(timeout=5000)
        print("Saved About section")
        await asyncio.sleep(3)
    except Exception as e:
        print(f"Could not click Save for About: {e}")

    print("\n=== PROFILE UPDATE COMPLETE ===")
    print("Check your profile to verify the changes look good.")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(update_profile())

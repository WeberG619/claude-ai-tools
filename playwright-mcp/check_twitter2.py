#!/usr/bin/env python3
"""Check Twitter/X profile after login"""
import asyncio
from playwright.async_api import async_playwright

async def check():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Go to home first to confirm logged in
    await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(4)
    print(f"Home URL: {page.url}")

    # Now go to profile
    await page.goto("https://x.com/settings/profile", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(4)

    body = await page.inner_text("body")
    with open(r"D:\twitter_settings.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {page.url}\n\n")
        f.write(body[:4000])
    print("Wrote settings page to D:\\twitter_settings.txt")

    # Go to actual profile page
    await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(3)

    # Try to find username from the sidebar
    try:
        # Look for the profile link in the sidebar
        profile_link = page.locator('a[data-testid="AppTabBar_Profile_Link"]').first
        href = await profile_link.get_attribute("href")
        print(f"Profile link: {href}")
        username = href.strip("/") if href else "unknown"

        # Navigate to profile
        await page.goto(f"https://x.com/{username}", wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(4)

        body = await page.inner_text("body")
        with open(r"D:\twitter_profile.txt", "w", encoding="utf-8") as f:
            f.write(f"URL: {page.url}\n")
            f.write(f"Username: {username}\n\n")
            f.write(body[:5000])
        print(f"Wrote profile page to D:\\twitter_profile.txt")
    except Exception as e:
        print(f"Could not find profile link: {e}")
        # Fallback: just grab the home page content
        body = await page.inner_text("body")
        with open(r"D:\twitter_profile.txt", "w", encoding="utf-8") as f:
            f.write(f"URL: {page.url}\n\n")
            f.write(body[:5000])
        print("Wrote home page text as fallback")

    # Also check notifications
    await page.goto("https://x.com/notifications", wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(3)
    notif_text = await page.inner_text("body")
    with open(r"D:\twitter_notifications.txt", "w", encoding="utf-8") as f:
        f.write(notif_text[:3000])
    print("Wrote notifications to D:\\twitter_notifications.txt")

    await pw.stop()

if __name__ == "__main__":
    asyncio.run(check())

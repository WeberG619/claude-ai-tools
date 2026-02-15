#!/usr/bin/env python3
"""
Check engagement across LinkedIn and Twitter/X.
Reports: notifications, comments, mentions, new followers.
"""

import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

OUTPUT_FILE = r"D:\social_engagement.json"


async def check_linkedin(page):
    """Check LinkedIn notifications and engagement."""
    print("--- LinkedIn ---")

    # Check notifications
    await page.goto("https://www.linkedin.com/notifications/",
                    wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(3)

    notifs = []
    try:
        items = await page.locator('.nt-card').all()
        for item in items[:10]:
            try:
                text = (await item.inner_text()).strip()
                if text:
                    notifs.append(text[:200])
            except:
                pass
    except:
        # Fallback: get all text
        body = await page.inner_text("body")
        notifs = [body[:1000]]

    print(f"  Notifications: {len(notifs)} items")

    # Check post analytics
    await page.goto("https://www.linkedin.com/in/me/recent-activity/all/",
                    wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(3)

    posts = []
    try:
        body = await page.inner_text("body")
        # Look for reaction counts
        for line in body.split("\n"):
            line = line.strip()
            if "reaction" in line.lower() or "comment" in line.lower() or "repost" in line.lower():
                posts.append(line[:100])
    except:
        pass

    print(f"  Post engagement signals: {len(posts)}")

    return {"notifications": notifs, "engagement": posts}


async def check_twitter(page):
    """Check Twitter/X notifications and mentions."""
    print("--- Twitter/X ---")

    # Check notifications
    await page.goto("https://x.com/notifications",
                    wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(3)

    notif_text = await page.inner_text("body")
    notifs = [line.strip() for line in notif_text.split("\n")
              if line.strip() and len(line.strip()) > 10][:20]

    print(f"  Notifications: {len(notifs)} items")

    # Check mentions
    await page.goto("https://x.com/notifications/mentions",
                    wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(3)

    mentions_text = await page.inner_text("body")
    mentions = [line.strip() for line in mentions_text.split("\n")
                if line.strip() and len(line.strip()) > 10
                and "@" in line][:10]

    print(f"  Mentions: {len(mentions)}")

    return {"notifications": notifs[:10], "mentions": mentions}


async def check_all():
    """Check all platforms."""
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    report = {
        "timestamp": datetime.now().isoformat(),
        "platforms": {}
    }

    try:
        report["platforms"]["linkedin"] = await check_linkedin(page)
    except Exception as e:
        print(f"LinkedIn check failed: {e}")
        report["platforms"]["linkedin"] = {"error": str(e)}

    try:
        report["platforms"]["twitter"] = await check_twitter(page)
    except Exception as e:
        print(f"Twitter check failed: {e}")
        report["platforms"]["twitter"] = {"error": str(e)}

    # Save report
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nReport saved to {OUTPUT_FILE}")

    await pw.stop()
    return report


if __name__ == "__main__":
    asyncio.run(check_all())

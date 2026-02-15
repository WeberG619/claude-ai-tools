#!/usr/bin/env python3
"""
Cross-post content to LinkedIn and Twitter/X simultaneously.
Adapts content for each platform's format and character limits.

Usage:
    python cross_post.py --file post.txt                    # Post to both
    python cross_post.py --file post.txt --platform linkedin  # LinkedIn only
    python cross_post.py --file post.txt --platform twitter   # Twitter only
    python cross_post.py --text "Quick update" --platform twitter
"""

import asyncio
import argparse
import sys
from playwright.async_api import async_playwright

TWITTER_CHAR_LIMIT = 280


def truncate_for_twitter(text):
    """Intelligently truncate long-form content to fit Twitter's 280 char limit."""
    if len(text) <= TWITTER_CHAR_LIMIT:
        return text

    # Try to find a natural break point
    # Remove hashtag block at the end first
    lines = text.strip().split("\n")
    content_lines = []
    hashtag_lines = []
    for line in reversed(lines):
        if line.strip().startswith("#") and not content_lines:
            hashtag_lines.insert(0, line)
        else:
            content_lines.insert(0, line)

    trimmed = "\n".join(content_lines).strip()

    if len(trimmed) <= TWITTER_CHAR_LIMIT:
        return trimmed

    # Take first paragraph + ellipsis
    paragraphs = trimmed.split("\n\n")
    result = paragraphs[0]
    if len(result) > TWITTER_CHAR_LIMIT - 3:
        result = result[:TWITTER_CHAR_LIMIT - 3] + "..."
    return result


async def post_linkedin(page, text):
    """Post to LinkedIn."""
    await page.goto("https://www.linkedin.com/feed/?shareActive=true",
                    wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(4)

    editor = page.locator('[role="textbox"]').first
    await editor.wait_for(state="visible", timeout=10000)
    await editor.click()
    await asyncio.sleep(0.5)
    await editor.fill(text)
    await asyncio.sleep(1)

    entered = await editor.inner_text()
    print(f"LinkedIn: {len(entered)} chars entered")

    post_btn = page.get_by_role("button", name="Post", exact=True)
    await post_btn.click(timeout=5000)
    await asyncio.sleep(3)
    print("LinkedIn: POSTED")
    return True


async def post_twitter(page, text):
    """Post to Twitter/X."""
    tweet_text = truncate_for_twitter(text)
    print(f"Twitter: {len(tweet_text)} chars (from {len(text)} original)")

    await page.goto("https://x.com/compose/post",
                    wait_until="domcontentloaded", timeout=20000)
    await asyncio.sleep(3)

    editor = page.locator('[data-testid="tweetTextarea_0"], [role="textbox"]').first
    await editor.wait_for(state="visible", timeout=10000)
    await editor.click()
    await asyncio.sleep(0.5)
    await editor.fill(tweet_text)
    await asyncio.sleep(2)

    post_btn = page.locator('[data-testid="tweetButton"]').first
    is_disabled = await post_btn.get_attribute("aria-disabled")

    if is_disabled == "true":
        # Retry with keyboard typing
        await editor.click()
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Delete")
        await asyncio.sleep(0.3)
        await page.keyboard.type(tweet_text, delay=5)
        await asyncio.sleep(2)

    await post_btn.click(timeout=10000)
    await asyncio.sleep(3)
    print("Twitter: POSTED")
    return True


async def cross_post(text, platforms=None):
    """Post content to specified platforms."""
    if platforms is None:
        platforms = ["linkedin", "twitter"]

    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222", timeout=5000)
    ctx = browser.contexts[0]
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    results = {}

    for platform in platforms:
        try:
            if platform == "linkedin":
                results["linkedin"] = await post_linkedin(page, text)
            elif platform == "twitter":
                results["twitter"] = await post_twitter(page, text)
        except Exception as e:
            print(f"{platform}: FAILED - {e}")
            results[platform] = False

    await pw.stop()
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cross-post to LinkedIn and Twitter")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to text file with post content")
    group.add_argument("--text", help="Post text directly")
    parser.add_argument("--platform", choices=["linkedin", "twitter", "both"],
                        default="both", help="Target platform(s)")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read().strip()
    else:
        content = args.text

    platforms = ["linkedin", "twitter"] if args.platform == "both" else [args.platform]

    print(f"Content: {len(content)} chars")
    print(f"Platforms: {', '.join(platforms)}")
    print("---")

    results = asyncio.run(cross_post(content, platforms))

    print("\n=== RESULTS ===")
    for p, ok in results.items():
        print(f"  {p}: {'OK' if ok else 'FAILED'}")

#!/usr/bin/env python3
"""Debug script to see what Upwork page looks like via CDP."""
import asyncio
import sys
from playwright.async_api import async_playwright

CDP_PORTS = [9222, 9224, 9225, 9223, 9229]


async def debug():
    pw = await async_playwright().start()
    browser = None

    for port in CDP_PORTS:
        for host in ["localhost", "127.0.0.1", "[::1]"]:
            try:
                browser = await pw.chromium.connect_over_cdp(
                    f"http://{host}:{port}", timeout=5000
                )
                print(f"Connected via {host}:{port}")
                break
            except Exception:
                continue
        if browser:
            break

    if not browser:
        print("Could not connect to any CDP port")
        await pw.stop()
        return

    ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = await ctx.new_page()

    print("Navigating to Upwork...")
    await page.goto(
        "https://www.upwork.com/nx/search/jobs/?q=Revit+API&sort=recency",
        wait_until="domcontentloaded",
        timeout=30000,
    )
    await page.wait_for_timeout(8000)

    url = page.url
    title = await page.title()
    html = await page.content()

    print(f"URL: {url}")
    print(f"Title: {title}")
    print(f"HTML length: {len(html)}")

    has_cf = "cloudflare" in html.lower()
    has_login = "login" in url.lower()
    print(f"Cloudflare: {has_cf}")
    print(f"Login redirect: {has_login}")

    articles = await page.query_selector_all("article")
    sections = await page.query_selector_all("section")
    h2s = await page.query_selector_all("h2")
    print(f"articles: {len(articles)}, sections: {len(sections)}, h2s: {len(h2s)}")

    body_text = await page.inner_text("body")
    print(f"\n--- Body text (first 1000 chars) ---")
    print(body_text[:1000])

    await page.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(debug())

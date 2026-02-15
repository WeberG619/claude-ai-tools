"""Check Freelancer tab state and find options for bidding."""

import time
from playwright.sync_api import sync_playwright


def safe_screenshot(page, path):
    try:
        page.screenshot(path=path, timeout=8000)
        print(f"Screenshot: {path}")
    except:
        print("Screenshot timed out")


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9222")
    print("Connected")

    context = browser.contexts[0]

    # Find Freelancer tab
    page = None
    for p in context.pages:
        if "freelancer.com" in p.url:
            page = p
            print(f"Found Freelancer tab: {p.url}")
            break

    if not page:
        print("No Freelancer tab found")
        pw.stop()
        return

    print(f"Current URL: {page.url}")

    # Refresh to get current state
    page.reload(wait_until="domcontentloaded", timeout=30000)
    time.sleep(4)

    body = page.inner_text("body")[:1500]
    print(f"\nPage text:\n{body[:1000]}")

    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_now.png")

    # Look for bid-related elements
    print("\n=== Bid-related elements ===")
    for text in ["Place Bid", "Bid on this", "bid", "Bid", "Award", "Buy", "purchase", "upgrade", "membership"]:
        try:
            els = page.query_selector_all(f'button:has-text("{text}"), a:has-text("{text}")')
            for el in els:
                if el.is_visible():
                    tag = el.evaluate("e => e.tagName")
                    href = el.get_attribute("href") or ""
                    inner = el.inner_text().strip()[:60]
                    print(f"  <{tag}> '{inner}' href={href[:80]}")
        except:
            pass

    # Check for any bid form or bid pack info
    print("\n=== Links with 'bid' or 'membership' ===")
    links = page.query_selector_all("a")
    for link in links:
        try:
            if link.is_visible():
                href = link.get_attribute("href") or ""
                text = link.inner_text().strip()[:60]
                if any(kw in (href + text).lower() for kw in ["bid", "membership", "upgrade", "plan", "pricing"]):
                    print(f"  '{text}' -> {href[:100]}")
        except:
            pass

    # Scroll down to see more
    page.evaluate("window.scrollBy(0, 500)")
    time.sleep(1)
    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_scroll.png")

    # Look for the warning about bids
    print("\n=== Warnings/alerts ===")
    alerts = page.query_selector_all('[class*="alert"], [class*="warning"], [class*="notice"], [class*="Banner"]')
    for a in alerts:
        try:
            if a.is_visible():
                text = a.inner_text().strip()[:200]
                print(f"  '{text}'")
        except:
            pass

    pw.stop()


if __name__ == "__main__":
    main()

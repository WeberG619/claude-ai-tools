"""Fill Upwork proposal after verification is complete."""

import json
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

    # Find Upwork tab
    page = None
    for p in context.pages:
        if "upwork.com" in p.url:
            page = p
            print(f"Found Upwork tab: {p.url}")
            break

    if not page:
        print("No Upwork tab found")
        pw.stop()
        return

    url = page.url
    print(f"Current URL: {url}")
    body = page.inner_text("body")[:500]
    print(f"Page text: {body[:300]}")
    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_post_verify.png")

    # If we're still on verification page or a different page, navigate to the job
    job_url = "https://www.upwork.com/jobs/Full-Stack-Python-Developer-FastAPI-HTMX-for-B2B-MVP-Supabase-VPS_~022017323436049499959/"

    if "jobs" not in url.lower() or "verification" in url.lower():
        print("Navigating to job page...")
        page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)
        print(f"Now on: {page.url}")
        safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_job.png")

    # Look for Apply Now button
    body = page.inner_text("body")[:800]
    print(f"\nPage text: {body[:400]}")

    apply_clicked = False
    for sel in [
        'button:has-text("Apply Now")',
        'a:has-text("Apply Now")',
        'button:has-text("Submit a Proposal")',
        'a:has-text("Submit a Proposal")',
        '[data-test="apply-button"]',
        'a[href*="apply"]',
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                print(f"Found: {sel}")
                el.click()
                time.sleep(5)
                print(f"Clicked apply, now on: {page.url}")
                safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_apply2.png")
                apply_clicked = True
                break
        except Exception as e:
            pass

    if not apply_clicked:
        print("No Apply button found - may already be on proposal page or need to scroll")
        # Try scrolling down to find it
        page.evaluate("window.scrollBy(0, 500)")
        time.sleep(1)
        for sel in ['button:has-text("Apply Now")', 'a:has-text("Apply Now")']:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    time.sleep(5)
                    apply_clicked = True
                    print(f"Found after scroll: {sel}")
                    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_apply2.png")
                    break
            except:
                pass

    # Now we should be on the proposal form
    # Load proposal text
    with open(r"D:\_CLAUDE-TOOLS\opportunityengine\.tmp_proposals.json", "r") as f:
        data = json.load(f)

    proposal_text = data["upwork"]["text"]
    bid_amount = data["upwork"]["bid"]

    # Clean up proposal text
    clean = proposal_text.replace("**", "")
    if "---" in clean:
        parts = clean.split("---")
        # Find the part that starts with "Hi,"
        for part in parts:
            stripped = part.strip()
            if stripped.startswith("Hi,") or stripped.startswith("Hi "):
                clean = stripped
                break
    if not clean.startswith("Hi"):
        # Try to find "Hi," in the text
        idx = clean.find("Hi,")
        if idx >= 0:
            clean = clean[idx:]

    print(f"\nProposal ({len(clean)} chars): {clean[:150]}...")

    # Check current page for textareas and inputs
    print("\n=== Page elements ===")

    # All visible textareas
    textareas = page.query_selector_all("textarea")
    for i, ta in enumerate(textareas):
        try:
            if ta.is_visible():
                name = ta.get_attribute("name") or ""
                placeholder = ta.get_attribute("placeholder") or ""
                testid = ta.get_attribute("data-test") or ""
                aria = ta.get_attribute("aria-label") or ""
                print(f"  Textarea [{i}]: name={name} ph={placeholder[:50]} testid={testid} aria={aria}")
        except:
            pass

    # All visible inputs
    inputs = page.query_selector_all("input")
    for i, inp in enumerate(inputs):
        try:
            if inp.is_visible():
                name = inp.get_attribute("name") or ""
                itype = inp.get_attribute("type") or ""
                placeholder = inp.get_attribute("placeholder") or ""
                testid = inp.get_attribute("data-test") or ""
                val = inp.input_value()[:30]
                print(f"  Input [{i}]: name={name} type={itype} ph={placeholder[:40]} testid={testid} val={val}")
        except:
            pass

    # Try to fill the cover letter
    proposal_filled = False
    for sel in [
        'textarea[data-test="cover-letter-area"]',
        'textarea[placeholder*="cover letter"]',
        'textarea[placeholder*="Cover"]',
        'textarea[aria-label*="cover"]',
        '#cover-letter-area',
        'textarea',
    ]:
        try:
            els = page.query_selector_all(sel)
            for el in els:
                if el.is_visible():
                    el.click()
                    time.sleep(0.3)
                    el.fill("")
                    el.fill(clean)
                    print(f"\nFilled proposal via {sel}")
                    proposal_filled = True
                    break
            if proposal_filled:
                break
        except Exception as e:
            print(f"  {sel}: {e}")

    # Try to fill bid/rate
    bid_filled = False
    for sel in [
        'input[data-test="bid-amount"]',
        'input[aria-label*="bid"]',
        'input[aria-label*="rate"]',
        'input[placeholder*="amount"]',
        'input[placeholder*="rate"]',
        'input[data-test="rate-input"]',
    ]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                el.fill("")
                el.fill(str(int(bid_amount)))
                print(f"Filled bid: ${bid_amount} via {sel}")
                bid_filled = True
                break
        except:
            continue

    time.sleep(1)
    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_filled2.png")
    print(f"\nProposal filled: {proposal_filled}, Bid filled: {bid_filled}")

    # Find and click submit
    if proposal_filled:
        for sel in [
            'button:has-text("Submit Proposal")',
            'button[data-test="submit-proposal-btn"]',
            'button:has-text("Submit")',
            'button:has-text("Send")',
        ]:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    print(f"\nSubmit button found: {sel}")
                    print(">>> CLICKING SUBMIT <<<")
                    btn.click()
                    time.sleep(5)
                    safe_screenshot(page, r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_done.png")
                    print(f"Done! URL: {page.url}")
                    body = page.inner_text("body")[:300]
                    print(f"Result: {body[:200]}")
                    break
            except:
                continue

    pw.stop()


if __name__ == "__main__":
    main()

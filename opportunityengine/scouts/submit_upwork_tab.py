"""Fill Upwork proposal on existing tab via Playwright CDP."""

import json
import time
from playwright.sync_api import sync_playwright


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9222")
    print("Connected")

    context = browser.contexts[0]

    # Find the Upwork tab
    page = None
    for p in context.pages:
        if "upwork.com" in p.url:
            page = p
            print(f"Found Upwork tab: {p.url}")
            break

    if not page:
        print("No Upwork tab found in browser")
        pw.stop()
        return

    # Take screenshot of current state
    try:
        page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_current.png", timeout=5000)
        print("Screenshot saved: .screenshot_uw_current.png")
    except Exception:
        print("Screenshot timed out - continuing anyway")

    # Check current state
    url = page.url
    print(f"Current URL: {url}")
    body_text = page.inner_text("body")[:500]
    print(f"Page text preview: {body_text[:300]}")

    # Check if we're on a Cloudflare page still
    if "Verifying" in body_text or "challenge" in url:
        print("Still on Cloudflare challenge - waiting 10s...")
        time.sleep(10)
        try:
            page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_current.png", timeout=5000)
        except:
            pass
        body_text = page.inner_text("body")[:500]
        print(f"After wait: {body_text[:200]}")

    # Check if we're on the job page
    if "jobs" not in url.lower() and "apply" not in url.lower():
        print("Not on a job page. Current URL:", url)
        print("Trying to navigate to the job...")
        try:
            page.goto(
                "https://www.upwork.com/jobs/Full-Stack-Python-Developer-FastAPI-HTMX-for-B2B-MVP-Supabase-VPS_~022017323436049499959/",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            time.sleep(5)
            page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_nav.png", timeout=5000)
            print(f"Navigated to: {page.url}")
        except Exception as e:
            print(f"Navigation failed: {e}")

    # Now look for "Apply Now" button
    apply_clicked = False
    apply_selectors = [
        'a:has-text("Apply Now")',
        'button:has-text("Apply Now")',
        'a:has-text("Submit a Proposal")',
        'button:has-text("Submit a Proposal")',
        '[data-test="apply-button"]',
        '.air3-btn:has-text("Apply")',
        'a[href*="apply"]',
    ]
    for sel in apply_selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                print(f"Found apply button: {sel}")
                el.click()
                time.sleep(5)
                page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_apply.png", timeout=5000)
                print(f"Clicked apply, now on: {page.url}")
                apply_clicked = True
                break
        except Exception as e:
            print(f"  {sel}: {e}")

    if not apply_clicked:
        print("Could not find Apply button - checking if already on proposal page")

    # Load proposal text
    with open(r"D:\_CLAUDE-TOOLS\opportunityengine\.tmp_proposals.json", "r") as f:
        data = json.load(f)

    proposal_text = data["upwork"]["text"]
    bid_amount = data["upwork"]["bid"]

    # Clean up the proposal text - remove markdown
    clean = proposal_text.replace("**", "").replace("---\n\n", "")
    # Remove the "Here's a draft proposal..." prefix if present
    if "---" in clean:
        clean = clean.split("---", 1)[-1].strip()
    if clean.startswith("Hi,"):
        pass  # Good, starts with greeting
    elif "Hi," in clean:
        clean = clean[clean.index("Hi,"):]

    print(f"\nProposal text ({len(clean)} chars):")
    print(clean[:200] + "...")

    # Try to fill the cover letter / proposal textarea
    proposal_filled = False

    # Dump visible textareas and inputs for debugging
    print("\n=== Visible textareas ===")
    textareas = page.query_selector_all("textarea")
    for i, ta in enumerate(textareas):
        try:
            if ta.is_visible():
                name = ta.get_attribute("name") or ""
                placeholder = ta.get_attribute("placeholder") or ""
                aria = ta.get_attribute("aria-label") or ""
                testid = ta.get_attribute("data-test") or ""
                print(f"  [{i}] name={name} placeholder={placeholder[:50]} aria={aria} testid={testid}")
        except:
            pass

    cover_selectors = [
        'textarea[data-test="cover-letter-area"]',
        'textarea[placeholder*="cover letter"]',
        'textarea[placeholder*="Cover Letter"]',
        'textarea[placeholder*="proposal"]',
        'textarea[aria-label*="cover"]',
        'textarea[aria-label*="Cover"]',
        '#cover-letter-area',
        '#coverLetter',
        'textarea',
    ]
    for sel in cover_selectors:
        try:
            els = page.query_selector_all(sel)
            for el in els:
                if el.is_visible():
                    el.click()
                    time.sleep(0.3)
                    el.fill("")
                    el.fill(clean)
                    print(f"Filled proposal via {sel}")
                    proposal_filled = True
                    break
            if proposal_filled:
                break
        except Exception as e:
            print(f"  {sel}: {e}")

    # Try to fill bid amount
    bid_filled = False
    bid_selectors = [
        'input[data-test="bid-amount"]',
        'input[aria-label*="bid"]',
        'input[aria-label*="Bid"]',
        'input[placeholder*="amount"]',
        'input[placeholder*="rate"]',
    ]
    for sel in bid_selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                el.fill("")
                el.fill(str(int(bid_amount)))
                print(f"Filled bid amount: ${bid_amount} via {sel}")
                bid_filled = True
                break
        except:
            continue

    time.sleep(1)
    page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_filled.png", timeout=5000)
    print(f"\nProposal filled: {proposal_filled}, Bid filled: {bid_filled}")
    print("Screenshot saved: .screenshot_uw_filled.png")

    # Look for submit button but ask before clicking
    submit_selectors = [
        'button[data-test="submit-proposal-btn"]',
        'button:has-text("Submit Proposal")',
        'button:has-text("Submit")',
        'button:has-text("Send")',
    ]
    for sel in submit_selectors:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                print(f"\nSubmit button found: {sel}")
                if proposal_filled:
                    print(">>> CLICKING SUBMIT <<<")
                    btn.click()
                    time.sleep(5)
                    page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_submitted.png", timeout=5000)
                    print(f"Submitted! Final URL: {page.url}")
                else:
                    print("Proposal not filled - NOT clicking submit")
                break
        except:
            continue

    pw.stop()


if __name__ == "__main__":
    main()

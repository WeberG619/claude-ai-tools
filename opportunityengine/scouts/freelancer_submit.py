"""Freelancer.com bid submission via Playwright CDP.

Run on Windows Python with Playwright installed.
Usage: python freelancer_submit.py '{"url": "...", "bid_amount": 100, "proposal_text": "..."}'
"""

import json
import sys
import time


def submit_bid(data: dict) -> dict:
    """Submit a bid on a Freelancer project page."""
    from playwright.sync_api import sync_playwright

    url = data["url"]
    bid_amount = data["bid_amount"]
    proposal_text = data["proposal_text"]

    # Try CDP ports
    cdp_ports = [9222, 9224, 9225, 9223, 9229]
    browser = None
    pw = None

    try:
        pw = sync_playwright().start()

        for port in cdp_ports:
            try:
                browser = pw.chromium.connect_over_cdp(f"http://localhost:{port}")
                break
            except Exception:
                continue

        if not browser:
            return {"success": False, "message": "No CDP browser available"}

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        # Navigate to the project page
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # Check if we're logged in
        if "login" in page.url.lower():
            page.close()
            return {"success": False, "message": "login_required"}

        # Look for the bid form
        # Freelancer has different layouts, try multiple selectors
        bid_input = None
        bid_selectors = [
            'input[name="bid_amount"]',
            'input[data-bid-amount]',
            'input[placeholder*="bid"]',
            'input[placeholder*="amount"]',
            '#bidAmount',
            '.bid-amount input',
        ]

        for sel in bid_selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    bid_input = el
                    break
            except Exception:
                continue

        if not bid_input:
            # Try to click "Place Bid" or "Bid on this project" button first
            bid_buttons = [
                'button:has-text("Place Bid")',
                'button:has-text("Bid on this")',
                'a:has-text("Place Bid")',
                'a:has-text("Bid on this")',
                '.PlaceBidBtn',
            ]
            for sel in bid_buttons:
                try:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click()
                        time.sleep(2)
                        break
                except Exception:
                    continue

            # Try bid selectors again
            for sel in bid_selectors:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        bid_input = el
                        break
                except Exception:
                    continue

        if not bid_input:
            page.close()
            return {"success": False, "message": "Could not find bid input field"}

        # Clear and fill bid amount
        bid_input.click()
        bid_input.fill("")
        bid_input.fill(str(int(bid_amount)))
        time.sleep(0.5)

        # Find and fill proposal text area
        proposal_input = None
        proposal_selectors = [
            'textarea[name="description"]',
            'textarea[name="proposal"]',
            'textarea[placeholder*="proposal"]',
            'textarea[placeholder*="describe"]',
            '.proposal-text textarea',
            'textarea.bid-description',
            'textarea',  # Last resort - first textarea on page
        ]

        for sel in proposal_selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    proposal_input = el
                    break
            except Exception:
                continue

        if proposal_input:
            proposal_input.click()
            proposal_input.fill("")
            proposal_input.fill(proposal_text[:5000])
            time.sleep(0.5)

        # Look for submit button
        submit_selectors = [
            'button[type="submit"]:has-text("Place Bid")',
            'button[type="submit"]:has-text("Submit")',
            'button:has-text("Place Bid")',
            'button:has-text("Submit Bid")',
            'button:has-text("Submit Proposal")',
            '.PlaceBidBtn',
        ]

        submitted = False
        for sel in submit_selectors:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    time.sleep(3)
                    submitted = True
                    break
            except Exception:
                continue

        if not submitted:
            page.close()
            return {"success": False, "message": "Could not find submit button"}

        # Check for success/error messages
        time.sleep(2)
        page_text = page.inner_text("body")[:2000].lower()

        if any(kw in page_text for kw in ["bid placed", "successfully", "bid submitted", "congratulations"]):
            page.close()
            return {"success": True, "message": "Bid submitted successfully", "reference": url}

        if any(kw in page_text for kw in ["error", "failed", "insufficient"]):
            page.close()
            return {"success": False, "message": f"Submission may have failed - check manually: {url}"}

        # Assume success if no error detected
        page.close()
        return {"success": True, "message": "Bid submitted (unconfirmed)", "reference": url}

    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
        if pw:
            try:
                pw.stop()
            except Exception:
                pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "message": "No data provided"}))
        sys.exit(1)

    arg = sys.argv[1]
    try:
        # Try as file path first, then as inline JSON
        import os
        if os.path.exists(arg):
            with open(arg, "r") as f:
                data = json.load(f)
        else:
            data = json.loads(arg)
    except (json.JSONDecodeError, IOError) as e:
        print(json.dumps({"success": False, "message": f"Invalid input: {e}"}))
        sys.exit(1)

    result = submit_bid(data)
    print(json.dumps(result))

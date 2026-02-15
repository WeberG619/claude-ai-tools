"""Submit proposals to Freelancer, Upwork, and Reddit via Playwright CDP."""

import json
import sys
import time


def connect_browser():
    """Connect to existing Chrome CDP session."""
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    cdp_ports = [9222, 9224, 9225, 9223, 9229]

    for port in cdp_ports:
        try:
            browser = pw.chromium.connect_over_cdp(f"http://localhost:{port}")
            print(f"Connected to CDP on port {port}")
            return pw, browser
        except Exception:
            continue

    print("ERROR: No CDP browser available")
    sys.exit(1)


def submit_freelancer(browser, url, bid_amount, proposal_text):
    """Submit a bid on Freelancer."""
    print(f"\n{'='*60}")
    print(f"FREELANCER: {url}")
    print(f"Bid: ${bid_amount}")
    print(f"{'='*60}")

    context = browser.contexts[0]
    page = context.new_page()

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(4)

        # Check if logged in
        if "login" in page.url.lower():
            print("NOT LOGGED IN - waiting for manual login...")
            page.wait_for_url("**/projects/**", timeout=120000)
            time.sleep(3)

        print(f"On page: {page.url}")

        # Screenshot current state
        page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl.png")
        print("Screenshot saved to .screenshot_fl.png")

        # Look for "Place Bid" or "Bid on this Project" button
        bid_btn = None
        for sel in [
            'button:has-text("Place Bid")',
            'button:has-text("Bid on this")',
            'a:has-text("Place Bid")',
            'a:has-text("Bid on this")',
            '[data-target="place-bid"]',
            '.PlaceBidBtn',
            'button:has-text("Place a Bid")',
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    bid_btn = el
                    print(f"Found bid button: {sel}")
                    break
            except:
                continue

        if bid_btn:
            bid_btn.click()
            time.sleep(3)
            page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl2.png")

        # Try to find and fill bid amount input
        bid_filled = False
        for sel in [
            'input[name="bid_amount"]',
            'input[data-bid-amount]',
            'input[placeholder*="bid"]',
            'input[placeholder*="amount"]',
            'input[placeholder*="Enter"]',
            '#bidAmount',
            '.bid-amount input',
            'input[type="number"]',
        ]:
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

        if not bid_filled:
            print("Could not find bid amount field - check screenshot")

        # Find and fill proposal textarea
        proposal_filled = False
        for sel in [
            'textarea[name="description"]',
            'textarea[name="proposal"]',
            'textarea[placeholder*="proposal"]',
            'textarea[placeholder*="describe"]',
            'textarea[placeholder*="Describe"]',
            '.proposal-text textarea',
            'textarea.bid-description',
            '#descriptionTextArea',
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    el.fill("")
                    # Strip markdown formatting for Freelancer
                    clean_text = proposal_text.replace("**", "").replace("- ", "• ")
                    el.fill(clean_text)
                    print(f"Filled proposal text via {sel}")
                    proposal_filled = True
                    break
            except:
                continue

        if not proposal_filled:
            # Try any visible textarea
            textareas = page.query_selector_all("textarea")
            for ta in textareas:
                if ta.is_visible():
                    ta.click()
                    clean_text = proposal_text.replace("**", "").replace("- ", "• ")
                    ta.fill(clean_text)
                    print("Filled proposal in first visible textarea")
                    proposal_filled = True
                    break

        if not proposal_filled:
            print("Could not find proposal text field - check screenshot")

        time.sleep(1)
        page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl3.png")
        print("Screenshot saved (after fill)")

        # Find submit button but DON'T click yet - let user review
        for sel in [
            'button[type="submit"]:has-text("Place Bid")',
            'button:has-text("Place Bid")',
            'button:has-text("Submit")',
        ]:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    print(f"Submit button found: {sel}")
                    print(">>> CLICKING SUBMIT <<<")
                    btn.click()
                    time.sleep(5)
                    page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl4.png")
                    print("Submitted! Screenshot saved.")
                    break
            except:
                continue

        return True

    except Exception as e:
        print(f"Freelancer error: {e}")
        page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_err.png")
        return False
    finally:
        # Don't close the page so user can review
        pass


def submit_upwork(browser, url, bid_amount, proposal_text):
    """Submit a proposal on Upwork."""
    print(f"\n{'='*60}")
    print(f"UPWORK: {url}")
    print(f"Bid: ${bid_amount}")
    print(f"{'='*60}")

    context = browser.contexts[0]
    page = context.new_page()

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(4)

        if "login" in page.url.lower():
            print("NOT LOGGED IN - waiting for manual login...")
            page.wait_for_url("**/jobs/**", timeout=120000)
            time.sleep(3)

        print(f"On page: {page.url}")
        page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw.png")

        # Look for "Apply Now" or "Submit a Proposal" button
        apply_btn = None
        for sel in [
            'a:has-text("Apply Now")',
            'button:has-text("Apply Now")',
            'a:has-text("Submit a Proposal")',
            'button:has-text("Submit a Proposal")',
            '[data-test="apply-button"]',
            '.air3-btn:has-text("Apply")',
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    apply_btn = el
                    print(f"Found apply button: {sel}")
                    break
            except:
                continue

        if apply_btn:
            apply_btn.click()
            time.sleep(5)
            page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw2.png")
            print("Clicked apply, on proposal page")

        # Fill in the cover letter / proposal
        proposal_filled = False
        for sel in [
            'textarea[placeholder*="cover letter"]',
            'textarea[placeholder*="proposal"]',
            'textarea[data-test="cover-letter"]',
            '#cover-letter',
            'textarea',
        ]:
            try:
                els = page.query_selector_all(sel)
                for el in els:
                    if el.is_visible():
                        el.click()
                        el.fill("")
                        el.fill(proposal_text.replace("**", ""))
                        print(f"Filled proposal via {sel}")
                        proposal_filled = True
                        break
                if proposal_filled:
                    break
            except:
                continue

        # Try to set the bid amount
        for sel in [
            'input[data-test="bid-amount"]',
            'input[placeholder*="amount"]',
            'input[placeholder*="bid"]',
            'input[aria-label*="bid"]',
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    el.fill("")
                    el.fill(str(int(bid_amount)))
                    print(f"Filled bid: ${bid_amount}")
                    break
            except:
                continue

        time.sleep(1)
        page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw3.png")

        # Submit
        for sel in [
            'button:has-text("Submit")',
            'button[data-test="submit-proposal"]',
            'button:has-text("Send")',
        ]:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    print(f"Submit button found: {sel}")
                    print(">>> CLICKING SUBMIT <<<")
                    btn.click()
                    time.sleep(5)
                    page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw4.png")
                    print("Submitted! Screenshot saved.")
                    break
            except:
                continue

        return True

    except Exception as e:
        print(f"Upwork error: {e}")
        page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_err.png")
        return False


def submit_reddit(browser, url, proposal_text):
    """Navigate to Reddit post and prepare DM."""
    print(f"\n{'='*60}")
    print(f"REDDIT: {url}")
    print(f"{'='*60}")

    context = browser.contexts[0]
    page = context.new_page()

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(4)

        print(f"On page: {page.url}")
        page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_rd.png")

        # Check if logged in - look for login button
        login_btn = page.query_selector('a[href*="login"]')
        if login_btn and login_btn.is_visible():
            print("NOT LOGGED IN to Reddit - user needs to log in")
            print("Waiting for login...")
            # Wait for the login to complete (URL won't have /login anymore)
            time.sleep(30)  # Give user time to log in

        # Try to find the post author to DM
        # Look for the author link
        author = None
        for sel in [
            'a[href*="/user/"]',
            '[data-testid="post_author_link"]',
            '.author',
        ]:
            try:
                els = page.query_selector_all(sel)
                for el in els:
                    href = el.get_attribute("href") or ""
                    if "/user/" in href and "AutoModerator" not in href:
                        author = href.split("/user/")[-1].strip("/")
                        if author:
                            break
                if author:
                    break
            except:
                continue

        if author:
            print(f"Found post author: u/{author}")
            # Navigate to DM compose page
            dm_url = f"https://www.reddit.com/message/compose/?to={author}"
            page.goto(dm_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(4)
            page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_rd2.png")

            # Fill subject
            for sel in ['input[name="subject"]', '#subject', 'input[placeholder*="Subject"]']:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.fill("Re: Python SWE - AI Research Support Role")
                        print("Filled subject")
                        break
                except:
                    continue

            # Fill message body
            for sel in ['textarea[name="message"]', '#message', 'textarea']:
                try:
                    els = page.query_selector_all(sel)
                    for el in els:
                        if el.is_visible():
                            clean_text = proposal_text.replace("**", "").replace("- ", "• ")
                            el.fill(clean_text)
                            print("Filled message body")
                            break
                except:
                    continue

            time.sleep(1)
            page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_rd3.png")
            print("Reddit DM ready - screenshot saved")
            print(">>> User should review and click Send <<<")
        else:
            print("Could not find post author for DM")
            print("Post the proposal as a comment instead")

        return True

    except Exception as e:
        print(f"Reddit error: {e}")
        return False


if __name__ == "__main__":
    # Load proposal data
    data_path = r"D:\_CLAUDE-TOOLS\opportunityengine\.tmp_proposals.json"
    with open(data_path, "r") as f:
        proposals = json.load(f)

    pw, browser = connect_browser()

    try:
        # 1. Freelancer
        if proposals.get("freelancer"):
            p = proposals["freelancer"]
            submit_freelancer(browser, p["url"], p["bid"], p["text"])

        # 2. Upwork
        if proposals.get("upwork"):
            p = proposals["upwork"]
            submit_upwork(browser, p["url"], p["bid"], p["text"])

        # 3. Reddit
        if proposals.get("reddit"):
            p = proposals["reddit"]
            submit_reddit(browser, p["url"], p["text"])

        print("\n" + "=" * 60)
        print("ALL DONE - Check screenshots and browser tabs")
        print("=" * 60)

    finally:
        # Don't close browser - leave tabs open for review
        pw.stop()

"""Log into Freelancer and Upwork via Google OAuth on Edge CDP."""

import time
from playwright.sync_api import sync_playwright


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    print("Connected to Edge CDP")

    context = browser.contexts[0]

    # --- UPWORK: Try Google OAuth ---
    print("\n=== UPWORK ===")
    uw_page = None
    for p in context.pages:
        if "upwork.com" in p.url and "login" in p.url:
            uw_page = p
            break

    if uw_page:
        print(f"Found Upwork login tab: {uw_page.url}")

        # First try: fill email and click Continue
        email_input = uw_page.query_selector('input[placeholder*="Username or Email"]')
        if email_input:
            email_input.fill("weberg619@gmail.com")
            print("Filled email on Upwork")
            time.sleep(1)

            # Click Continue
            continue_btn = uw_page.query_selector('button#login_control_continue')
            if not continue_btn:
                continue_btn = uw_page.query_selector('button:has-text("Continue")')
            if continue_btn:
                continue_btn.click()
                print("Clicked Continue")
                time.sleep(5)
                uw_page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_login2.png")
                print(f"URL after continue: {uw_page.url}")
                print("Screenshot saved: .screenshot_uw_login2.png")
    else:
        print("No Upwork login tab found")

    # --- FREELANCER: Try Google OAuth ---
    print("\n=== FREELANCER ===")
    fl_page = None
    for p in context.pages:
        if "freelancer.com" in p.url and "login" in p.url:
            fl_page = p
            break

    if fl_page:
        print(f"Found Freelancer login tab: {fl_page.url}")

        # Fill email field
        email_input = fl_page.query_selector('input[placeholder*="Email or Username"]')
        if email_input:
            email_input.fill("weberg619@gmail.com")
            print("Filled email on Freelancer")
        else:
            # Try other selectors
            for sel in ['input[name="emailOrUsername"]', 'input[type="email"]', 'input[id*="email"]']:
                el = fl_page.query_selector(sel)
                if el:
                    el.fill("weberg619@gmail.com")
                    print(f"Filled email via {sel}")
                    break

        time.sleep(1)
        fl_page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_login2.png")
        print("Screenshot saved: .screenshot_fl_login2.png")
        print("Need password to continue - or use 'Continue with Google'")
    else:
        print("No Freelancer login tab found")

    pw.stop()


if __name__ == "__main__":
    main()

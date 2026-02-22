"""Log into Freelancer and Upwork via Edge CDP."""

import time
from playwright.sync_api import sync_playwright

EMAIL = "weberg619@gmail.com"
PASSWORD = "Weber@619.1974"


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    print("Connected to Edge CDP")

    context = browser.contexts[0]

    # --- UPWORK ---
    print("\n=== UPWORK ===")
    uw_page = None
    for p in context.pages:
        if "upwork.com" in p.url:
            uw_page = p
            break

    if uw_page:
        print(f"Tab: {uw_page.url}")

        # Fill password
        pw_input = uw_page.query_selector('input[type="password"]')
        if pw_input:
            pw_input.fill(PASSWORD)
            print("Password filled")

            # Check "Keep me logged in"
            keep_logged = uw_page.query_selector('input[type="checkbox"]')
            if keep_logged:
                try:
                    keep_logged.check()
                    print("Checked 'Keep me logged in'")
                except:
                    pass

            time.sleep(1)

            # Click Log in
            login_btn = uw_page.query_selector('button#login_control_continue')
            if not login_btn:
                login_btn = uw_page.query_selector('button:has-text("Log in")')
            if login_btn:
                login_btn.click()
                print("Clicked Log in")
                time.sleep(8)
                print(f"URL after login: {uw_page.url}")
                uw_page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_after_login.png")
                if "login" not in uw_page.url.lower():
                    print("UPWORK: LOGGED IN!")
                else:
                    print("UPWORK: Still on login page - may need 2FA or CAPTCHA")
        else:
            # Might need to enter email first
            email_input = uw_page.query_selector('input[placeholder*="Username or Email"]')
            if email_input:
                email_input.fill(EMAIL)
                continue_btn = uw_page.query_selector('button:has-text("Continue")')
                if continue_btn:
                    continue_btn.click()
                    time.sleep(5)
                    pw_input = uw_page.query_selector('input[type="password"]')
                    if pw_input:
                        pw_input.fill(PASSWORD)
                        login_btn = uw_page.query_selector('button:has-text("Log in")')
                        if login_btn:
                            login_btn.click()
                            time.sleep(8)
                            print(f"URL: {uw_page.url}")
                            uw_page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_uw_after_login.png")
    else:
        print("No Upwork tab found")

    # --- FREELANCER ---
    print("\n=== FREELANCER ===")
    fl_page = None
    for p in context.pages:
        if "freelancer.com" in p.url:
            fl_page = p
            break

    if fl_page:
        print(f"Tab: {fl_page.url}")

        # Fill password
        pw_input = fl_page.query_selector('input[type="password"]')
        if pw_input:
            pw_input.fill(PASSWORD)
            print("Password filled")

            # Check "Remember me"
            remember = fl_page.query_selector('input[type="checkbox"]')
            if remember:
                try:
                    remember.check()
                    print("Checked 'Remember me'")
                except:
                    pass

            time.sleep(1)

            # Click Log in
            login_btn = fl_page.query_selector('button:has-text("Log in")')
            if not login_btn:
                login_btn = fl_page.query_selector('button[type="submit"]')
            if login_btn:
                login_btn.click()
                print("Clicked Log in")
                time.sleep(8)
                print(f"URL after login: {fl_page.url}")
                fl_page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_after_login.png")
                if "login" not in fl_page.url.lower():
                    print("FREELANCER: LOGGED IN!")
                else:
                    print("FREELANCER: Still on login page - may need CAPTCHA")
        else:
            print("No password field found")
    else:
        print("No Freelancer tab found")

    pw.stop()


if __name__ == "__main__":
    main()

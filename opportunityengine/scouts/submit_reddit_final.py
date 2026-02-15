"""Fill Reddit DM title and click Send."""

import time
from playwright.sync_api import sync_playwright


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9222")
    print("Connected")

    context = browser.contexts[0]

    # Find the existing Reddit DM tab
    page = None
    for p in context.pages:
        if "message/compose" in p.url:
            page = p
            print(f"Found DM tab: {p.url}")
            break

    if not page:
        print("No DM tab found")
        pw.stop()
        return

    # Clear the search bar that got junk in it
    try:
        search = page.query_selector('input[name="q"]:visible')
        if search:
            search.fill("")
    except:
        pass

    # Fill the Title field - it's name="message-title"
    title_input = page.query_selector('input[name="message-title"]')
    if title_input and title_input.is_visible():
        title_input.click()
        title_input.fill("AI Research Support - Python SWE Application")
        print("Filled title field!")
    else:
        print("ERROR: Could not find title input")
        pw.stop()
        return

    time.sleep(1)
    page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_rd_ready.png")
    print("Screenshot saved (ready to send)")

    # Click Send button
    send_btn = page.query_selector('button:has-text("Send")')
    if send_btn:
        print(f"Send button enabled: {send_btn.is_enabled()}")
        if send_btn.is_enabled():
            print(">>> CLICKING SEND <<<")
            send_btn.click()
            time.sleep(5)
            page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_rd_sent.png")
            print(f"SENT! Final URL: {page.url}")
            # Check for success
            body = page.inner_text("body")[:300]
            print(f"Page text: {body}")
        else:
            print("Send button is disabled - title may not have registered")
            # Try pressing Tab first to trigger validation
            title_input.press("Tab")
            time.sleep(1)
            if send_btn.is_enabled():
                print(">>> CLICKING SEND (after Tab) <<<")
                send_btn.click()
                time.sleep(5)
                page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_rd_sent.png")
                print(f"SENT! Final URL: {page.url}")
    else:
        print("Could not find Send button")

    pw.stop()


if __name__ == "__main__":
    main()

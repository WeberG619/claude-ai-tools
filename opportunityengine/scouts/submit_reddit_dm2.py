"""Fill Reddit DM title field and click Send - message already filled."""

import time
import sys
from playwright.sync_api import sync_playwright


def main():
    pw = sync_playwright().start()

    cdp_ports = [9222, 9224, 9225, 9223, 9229]
    browser = None
    for port in cdp_ports:
        try:
            browser = pw.chromium.connect_over_cdp(f"http://localhost:{port}")
            print(f"Connected to CDP on port {port}")
            break
        except Exception:
            continue

    if not browser:
        print("ERROR: No CDP browser available")
        sys.exit(1)

    context = browser.contexts[0]

    # Find the existing Reddit DM tab
    page = None
    for p in context.pages:
        if "message/compose" in p.url:
            page = p
            print(f"Found existing DM tab: {p.url}")
            break

    if not page:
        print("No Reddit DM tab found, opening new one...")
        page = context.new_page()
        page.goto(
            "https://www.reddit.com/message/compose/?to=Bradley_561",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        time.sleep(5)

    # The Title field on Reddit new UI - try multiple approaches
    title_filled = False

    # Try finding by placeholder text "Title"
    all_inputs = page.query_selector_all("input")
    for inp in all_inputs:
        try:
            placeholder = inp.get_attribute("placeholder") or ""
            aria_label = inp.get_attribute("aria-label") or ""
            name = inp.get_attribute("name") or ""
            inp_type = inp.get_attribute("type") or ""
            if inp.is_visible() and inp_type not in ("hidden", "submit"):
                val = inp.input_value()
                print(f"  Input: name={name} placeholder={placeholder} aria={aria_label} type={inp_type} val={val[:30]}")
                # Fill the Title field - it's the empty input (Send to already has Bradley_561)
                if not val and "Bradley" not in placeholder:
                    inp.click()
                    inp.fill("AI Research Support - Python SWE Application")
                    print(f"  >> Filled title!")
                    title_filled = True
                    break
        except Exception as e:
            continue

    if not title_filled:
        # Try by label text
        try:
            # Click on the "Title" label area
            title_label = page.get_by_text("Title", exact=False)
            if title_label:
                title_label.click()
                time.sleep(0.5)
                page.keyboard.type("AI Research Support - Python SWE Application")
                print("Filled title via label click + keyboard")
                title_filled = True
        except Exception as e:
            print(f"Label approach failed: {e}")

    time.sleep(1)
    page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_rd_dm_final.png")

    if title_filled:
        # Click Send
        send_btn = None
        for sel in [
            'button:has-text("Send")',
            'button[type="submit"]',
            'input[type="submit"]',
        ]:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    send_btn = btn
                    print(f"Found send button: {sel}")
                    break
            except:
                continue

        if send_btn:
            print(">>> CLICKING SEND <<<")
            send_btn.click()
            time.sleep(5)
            page.screenshot(
                path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_rd_sent.png"
            )
            print("SENT! Screenshot saved.")
            print(f"Final URL: {page.url}")
        else:
            print("Could not find Send button")
    else:
        print("Could not fill Title field - check screenshot")

    pw.stop()


if __name__ == "__main__":
    main()

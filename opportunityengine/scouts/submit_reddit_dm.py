"""Submit Reddit DM to Bradley_561 via Playwright CDP."""

import time
import sys
from playwright.sync_api import sync_playwright


def main():
    pw = sync_playwright().start()

    # Connect to existing Chrome
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
    page = context.new_page()

    try:
        # Navigate to DM compose page for Bradley_561
        dm_url = "https://www.reddit.com/message/compose/?to=Bradley_561"
        page.goto(dm_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)

        print(f"On page: {page.url}")
        page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_rd_dm.png")
        print("Screenshot saved: .screenshot_rd_dm.png")

        # Check if we're on the compose page
        body_text = page.inner_text("body")[:500]
        print(f"Page text: {body_text[:200]}")

        # Try to find subject input
        subject_filled = False
        subject_selectors = [
            'input[name="subject"]',
            '#subject',
            'input[placeholder*="Subject"]',
            'input[placeholder*="subject"]',
        ]
        for sel in subject_selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.fill("Re: AI Research Support - Python SWE")
                    print(f"Filled subject via {sel}")
                    subject_filled = True
                    break
            except Exception as e:
                print(f"Subject {sel}: {e}")

        # Proposal text
        proposal = (
            "Hi Bradley,\n\n"
            "I'm interested in the AI Research Support role. I review and validate "
            "AI-generated code daily as part of my work building autonomous agent systems.\n\n"
            "Relevant experience:\n"
            "- Build and maintain multi-agent AI systems (Claude, GPT-4) that generate, "
            "test, and deploy code autonomously\n"
            "- Strong in Python, JavaScript, C#, with daily use of debugging and validating "
            "AI outputs\n"
            "- Experience with algorithm benchmarking and structured technical feedback loops\n"
            "- Background in construction tech (Revit API, BIM automation) showing I can work "
            "across specialized domains\n\n"
            "I'm available 15-25 hrs/week as described. My rate is $100/hr, in line with "
            "your posted range. I can start immediately.\n\n"
            "Happy to do a short paid trial task so you can evaluate my work directly.\n\n"
            "Best,\n"
            "Weber Gouin\n"
            "weber@bimopsstudio.com"
        )

        # Try to find message textarea
        msg_filled = False
        msg_selectors = [
            'textarea[name="message"]',
            '#message',
            'textarea[name="body"]',
            '.usertext-edit textarea',
            'textarea',
        ]
        for sel in msg_selectors:
            try:
                els = page.query_selector_all(sel)
                for el in els:
                    if el.is_visible():
                        el.click()
                        el.fill(proposal)
                        print(f"Filled message via {sel}")
                        msg_filled = True
                        break
                if msg_filled:
                    break
            except Exception as e:
                print(f"Message {sel}: {e}")

        time.sleep(1)
        page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_rd_dm2.png")
        print("Screenshot saved: .screenshot_rd_dm2.png")

        if subject_filled and msg_filled:
            # Look for send button
            send_selectors = [
                'button[type="submit"]',
                'button:has-text("Send")',
                'button:has-text("send")',
                'input[type="submit"]',
            ]
            for sel in send_selectors:
                try:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        print(f"Found send button: {sel}")
                        print(">>> CLICKING SEND <<<")
                        btn.click()
                        time.sleep(5)
                        page.screenshot(
                            path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_rd_dm3.png"
                        )
                        print("Sent! Screenshot saved: .screenshot_rd_dm3.png")
                        break
                except Exception as e:
                    print(f"Send {sel}: {e}")
        else:
            print(f"Subject filled: {subject_filled}, Message filled: {msg_filled}")
            print("Could not fill all fields - check screenshots")

    except Exception as e:
        print(f"Error: {e}")
        try:
            page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_rd_err.png")
        except:
            pass

    pw.stop()


if __name__ == "__main__":
    main()

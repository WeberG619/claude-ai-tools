"""Submit Reddit DM to marketing-girlkhushi for opportunity #658 via Edge CDP."""

import time
from playwright.sync_api import sync_playwright

PROPOSAL_TITLE = "Re: Commission-Based Business Developer - Automation Partner"

PROPOSAL_MSG = """Hi,

Your post caught my attention - not for the typical lead gen angle, but because of the automation infrastructure behind it. I build AI-powered automation systems professionally, and what you're describing (CRM automation, follow-up flows, conversion tracking) is exactly what I architect daily.

Why I'd be a strong partner:

I'm a full-stack developer and automation specialist. My daily work involves building systems that run autonomously - lead routing, multi-channel follow-up sequences, CRM integrations, and data pipelines connecting ad platforms to reporting dashboards without manual intervention.

- Built production automation pipelines handling lead capture > qualification > CRM entry > automated follow-up sequences across email, WhatsApp, and SMS
- API integration expertise across Meta Ads, Google Ads, HubSpot, GoHighLevel, and custom CRM platforms - conversion tracking and ROAS reporting that reflects reality
- Real estate tech background - I work in the AEC/construction industry, so I understand the real estate client mindset. Property leads and investor inquiries aren't abstract to me

What I bring to the split:

Beyond outreach, I can enhance your fulfillment offering. If a prospect needs AI-powered lead scoring, intelligent chatbot qualification, or custom reporting dashboards - I can build it. You're not just selling ads, you're selling a tech-enabled service.

I'd focus on Real Estate first (faster close cycle), targeting US and Canadian markets through LinkedIn outreach and direct engagement in RE investor communities.

Can start immediately - happy to do a quick call to align on targeting and messaging.

Best,
Weber Gouin"""


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    print("Connected to Edge CDP")

    context = browser.contexts[0]
    page = context.new_page()

    page.goto(
        "https://www.reddit.com/message/compose/?to=marketing-girlkhushi",
        wait_until="domcontentloaded",
        timeout=30000,
    )
    time.sleep(5)
    print(f"On page: {page.url}")

    # Fill Title
    title_filled = False
    for inp in page.query_selector_all("input"):
        try:
            nm = inp.get_attribute("name") or ""
            ph = inp.get_attribute("placeholder") or ""
            if "title" in nm.lower() or "subject" in nm.lower() or "title" in ph.lower():
                inp.click()
                inp.fill(PROPOSAL_TITLE)
                title_filled = True
                print(f"Title filled (name={nm})")
                break
        except:
            pass

    # Fill Message
    msg_filled = False
    for el in page.query_selector_all("textarea"):
        try:
            if el.is_visible():
                el.click()
                el.fill(PROPOSAL_MSG)
                msg_filled = True
                print("Message filled")
                break
        except:
            pass

    time.sleep(1)
    page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_658_filled.png")
    print(f"Title: {title_filled}, Message: {msg_filled}")

    if title_filled and msg_filled:
        for sel in ['button:has-text("Send")', 'button[type="submit"]']:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    print(f">>> CLICKING SEND via {sel} <<<")
                    btn.click()
                    time.sleep(5)
                    page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_658_sent.png")
                    print("SENT!")
                    break
            except Exception as e:
                print(f"Send {sel}: {e}")
    else:
        print("Could not fill all fields")

    pw.stop()


if __name__ == "__main__":
    main()

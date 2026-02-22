"""Submit Reddit DM to EtikDigital512 for opportunity #979 (Polymarket bot) via Edge CDP."""

import time
from playwright.sync_api import sync_playwright

PROPOSAL_TITLE = "Re: Python Developer - Polymarket Trading Bot"

PROPOSAL_MSG = """Hi,

Saw your post about the Polymarket trading bot. This is right in my wheelhouse - I build Python automation and API integration systems daily.

Relevant experience:
- Python expert - pandas, requests, asyncio, WebSocket clients for real-time data
- Built multiple API integration pipelines handling real-time data streams and automated decision logic
- Experience with financial/trading APIs and order execution workflows
- Clean, documented code with error handling and logging as standard practice

For your specific project:
- py-clob-client integration with Polymarket's API
- BTC 5-min candle monitoring with configurable technical indicators (green candles + volume)
- Trade execution with proper error handling, rate limiting, and logging
- Clean architecture so you can tweak strategy parameters without touching core logic

I can have an MVP running within a week. Happy to review your detailed specs first and give you a precise timeline.

$400 works - I can move fast on this.

Best,
Weber Gouin"""


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    print("Connected to Edge CDP")

    context = browser.contexts[0]
    page = context.new_page()

    page.goto(
        "https://www.reddit.com/message/compose/?to=EtikDigital512",
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
            if "title" in nm.lower() or "subject" in nm.lower():
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

    if title_filled and msg_filled:
        for sel in ['button:has-text("Send")', 'button[type="submit"]']:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    print(f">>> CLICKING SEND via {sel} <<<")
                    btn.click()
                    time.sleep(5)
                    page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_979_sent.png")
                    print("SENT!")
                    break
            except Exception as e:
                print(f"Send {sel}: {e}")
    else:
        print(f"Title: {title_filled}, Message: {msg_filled} - check page")
        page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_979_err.png")

    pw.stop()


if __name__ == "__main__":
    main()

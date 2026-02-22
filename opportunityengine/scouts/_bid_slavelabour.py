"""Post $bid comments on both Telegram tasks in r/slavelabour."""
import time
from playwright.sync_api import sync_playwright

def safe_print(s):
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode('ascii', errors='replace').decode('ascii'))

BIDS = [
    {
        "url": "https://old.reddit.com/r/slavelabour/comments/1r58whc/task_telegram_ai_chatbot/",
        "name": "Telegram AI Chatbot",
        "comment": """$bid

I build Python + AI systems daily (Telegram bots, API integrations, database pipelines). I can have a working Telegram chatbot with database-backed price lookups running within 24-48 hours. Clean interface, async, production-ready.

Stack: Python + python-telegram-bot + SQLite/Postgres, with optional LLM layer for natural language queries.

Happy to discuss scope and pricing in DMs.""",
    },
    {
        "url": "https://old.reddit.com/r/slavelabour/comments/1r55jgl/task_lf_python_dev_telegram_channel_monitor_ai/",
        "name": "Telegram Monitor + AI Valuation",
        "comment": """$bid

This is right in my wheelhouse. I work with Python + Telethon + LLM pipelines daily.

- Telegram scraping: experienced with Telethon for read-only channel monitoring and backfilling
- Data parsing: regex + LLM-assisted extraction for unstructured listing data
- AI valuations: I'll wire in Claude/GPT API calls for lightweight valuation analysis with structured output
- Output: Google Sheets API, JSON, or CSV - your pick
- Multi-account handling: Telethon session management with rotation

I can deliver a working MVP in ~5-7 days. Happy to start with a small paid proof-of-concept on one channel first.

Payment: PayPal or crypto both work. DM me for details.""",
    },
]

def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    page = context.new_page()

    for bid in BIDS:
        safe_print(f"\n--- Bidding on: {bid['name']} ---")
        page.goto(bid["url"], wait_until="domcontentloaded", timeout=20000)
        time.sleep(3)

        # Find the comment textarea
        comment_box = page.query_selector('textarea[name="text"]')
        if not comment_box:
            # Try clicking "add a comment" or similar
            comment_link = page.query_selector('a:has-text("comment")')
            if comment_link:
                comment_link.click()
                time.sleep(2)
                comment_box = page.query_selector('textarea[name="text"]')

        if comment_box:
            comment_box.click()
            time.sleep(0.5)
            comment_box.fill(bid["comment"])
            safe_print("Comment filled")
            time.sleep(1)

            # Click save/submit button
            save_btn = page.query_selector('.save-button button, button[type="submit"]:has-text("save"), .usertext-buttons button:has-text("save")')
            if not save_btn:
                buttons = page.query_selector_all('button')
                for btn in buttons:
                    try:
                        if btn.inner_text().strip().lower() == 'save':
                            save_btn = btn
                            break
                    except:
                        continue

            if save_btn:
                save_btn.click()
                safe_print("Comment submitted!")
                time.sleep(3)
            else:
                safe_print("Could not find save button")
                page.screenshot(path=f"D:\\_CLAUDE-TOOLS\\opportunityengine\\.screenshot_sl_nosave.png")
        else:
            safe_print("Could not find comment box")
            page.screenshot(path=f"D:\\_CLAUDE-TOOLS\\opportunityengine\\.screenshot_sl_nobox.png")

    page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_sl_bids_done.png")
    page.close()
    pw.stop()

if __name__ == "__main__":
    main()

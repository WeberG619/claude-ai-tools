"""Check which qualified opportunities are still live."""
import time
from playwright.sync_api import sync_playwright

TARGETS = [
    {"id": 1017, "url": "https://old.reddit.com/r/slavelabour/comments/1ipgy3f/task_lf_python_dev_telegram_monitor/", "name": "Telegram monitor"},
    {"id": 1134, "url": "https://www.freelancer.com/projects/streamlit/streamlit-ops-control-panel-build", "name": "Streamlit Ops Panel"},
    {"id": 1131, "url": "https://www.freelancer.com/projects/revit/custom-home-architecture-plans", "name": "Architecture Plans"},
]

def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]
    page = context.new_page()

    for t in TARGETS:
        try:
            page.goto(t["url"], wait_until="domcontentloaded", timeout=20000)
            time.sleep(3)
            url = page.url
            body = page.inner_text("body")[:800]
            removed = any(w in body.lower() for w in ["removed", "doesn't exist", "not found", "oops", "deleted", "expired", "closed"])
            status = "DEAD" if removed else "LIVE"
            print(f"#{t['id']} {t['name']}: {status}")
            print(f"  URL: {url}")
            if status == "DEAD":
                print(f"  Reason: {body[:200]}")
            else:
                print(f"  Preview: {body[:200]}")
            print()
        except Exception as e:
            print(f"#{t['id']} {t['name']}: ERROR - {e}")
            print()

    page.close()
    pw.stop()

if __name__ == "__main__":
    main()

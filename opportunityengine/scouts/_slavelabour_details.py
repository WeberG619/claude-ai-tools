"""Get details on the best r/slavelabour tasks."""
import time
from playwright.sync_api import sync_playwright

def safe_print(s):
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode('ascii', errors='replace').decode('ascii'))

TARGETS = [
    "https://old.reddit.com/r/slavelabour/comments/1r58whc/task_telegram_ai_chatbot/",
    "https://old.reddit.com/r/slavelabour/comments/1r55jgl/task_lf_python_dev_telegram_channel_monitor_ai/",
    "https://old.reddit.com/r/slavelabour/comments/1r5lq6w/task_new_opportunity/",
]

def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    page = context.new_page()

    for url in TARGETS:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(3)

        # Get post content and comments
        post_body = page.evaluate("""() => {
            const selftext = document.querySelector('.expando .usertext-body');
            const title = document.querySelector('.title a.title');
            const author = document.querySelector('.tagline a.author');
            const comments = document.querySelectorAll('.comment .usertext-body');
            const commentTexts = [];
            for (let i = 0; i < Math.min(comments.length, 5); i++) {
                commentTexts.push(comments[i].textContent.trim().substring(0, 200));
            }
            return {
                title: title ? title.textContent.trim() : '',
                author: author ? author.textContent.trim() : '',
                body: selftext ? selftext.textContent.trim().substring(0, 1500) : '',
                topComments: commentTexts,
            };
        }""")

        safe_print(f"\\n{'='*60}")
        safe_print(f"TITLE: {post_body['title']}")
        safe_print(f"AUTHOR: {post_body['author']}")
        safe_print(f"\\n{post_body['body']}")
        safe_print(f"\\n--- Top comments ({len(post_body['topComments'])}) ---")
        for c in post_body['topComments']:
            safe_print(f"  > {c[:150]}")
        safe_print("")

    page.close()
    pw.stop()

if __name__ == "__main__":
    main()

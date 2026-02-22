"""Scan r/slavelabour for active [TASK] posts - quick cash opportunities."""
import time
from playwright.sync_api import sync_playwright

def safe_print(s):
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode('ascii', errors='replace').decode('ascii'))

def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    page = context.new_page()
    # Search for TASK posts sorted by new
    page.goto("https://old.reddit.com/r/slavelabour/new/", wait_until="domcontentloaded", timeout=30000)
    time.sleep(4)

    if "login" in page.url.lower():
        print("NOT LOGGED IN")
        pw.stop()
        return

    # Extract task posts
    posts = page.evaluate("""() => {
        const results = [];
        const things = document.querySelectorAll('.thing.link');
        for (const t of things) {
            const titleEl = t.querySelector('a.title');
            if (!titleEl) continue;
            const title = titleEl.textContent.trim();
            const href = titleEl.href;
            const flair = t.querySelector('.linkflairlabel');
            const flairText = flair ? flair.textContent.trim() : '';
            const time = t.querySelector('time');
            const timeText = time ? time.getAttribute('title') || time.textContent : '';
            const score = t.querySelector('.score.unvoted');
            const scoreText = score ? score.textContent : '0';
            const comments = t.querySelector('.comments');
            const commentsText = comments ? comments.textContent : '0';
            
            if (title.toLowerCase().includes('[task]') || flairText.toLowerCase().includes('task')) {
                results.push({
                    title: title.substring(0, 200),
                    url: href,
                    flair: flairText,
                    posted: timeText,
                    score: scoreText,
                    comments: commentsText,
                });
            }
        }
        return results;
    }""")

    safe_print(f"Found {len(posts)} [TASK] posts:\\n")
    for i, p in enumerate(posts):
        safe_print(f"{i+1}. {p['title']}")
        safe_print(f"   Posted: {p['posted']}")
        safe_print(f"   Comments: {p['comments']} | Score: {p['score']}")
        safe_print(f"   URL: {p['url']}")
        safe_print("")

    page.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_slavelabour.png")

    # Also check page 2
    page.goto("https://old.reddit.com/r/slavelabour/new/?count=25&after=", wait_until="domcontentloaded", timeout=20000)
    time.sleep(3)

    page.close()
    pw.stop()

if __name__ == "__main__":
    main()

"""Get job URLs - wait longer for Angular rendering."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

url = "https://www.upwork.com/nx/search/jobs/?q=python+automation&sort=recency&proposals=0-4&payment_verified=1"
page.evaluate(f"window.location.href = '{url}'")

# Wait longer
time.sleep(5)
for i in range(30):
    try:
        title = page.title()
        if "Just a moment" in title:
            print(f"Cloudflare... ({i+1})")
            time.sleep(2)
        else:
            # Check if jobs have loaded
            count = page.evaluate("document.querySelectorAll('a[href*=\"/jobs/~\"]').length")
            print(f"[{i+1}] Title: {title[:40]}, job links: {count}")
            if count > 0:
                break
            time.sleep(2)
    except Exception as e:
        print(f"[{i+1}] Error: {e}")
        time.sleep(2)

time.sleep(3)
print(f"\nFinal: {page.title()[:50]} | {page.url[:60]}")

# Check page content
text = page.evaluate("document.body.innerText.substring(0, 1000)")
print(f"\nPage text:\n{text[:500]}")

# Try to find job links
links = page.evaluate("""(() => {
    const all = document.querySelectorAll('a');
    return Array.from(all).filter(a => a.href && a.href.includes('/jobs/')).map(a => ({
        href: a.href.substring(0, 100),
        text: a.textContent.trim().substring(0, 60),
    })).slice(0, 20);
})()""")
print(f"\nJob-related links ({len(links)}):")
for l in links:
    print(f"  {l['text'][:50]} -> {l['href'][:80]}")

pw.stop()

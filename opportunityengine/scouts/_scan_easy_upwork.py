"""Scan Upwork for easy, quick-win jobs matching our skills."""
from playwright.sync_api import sync_playwright
import time
import json

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

SEARCHES = [
    "https://www.upwork.com/nx/search/jobs/?q=revit%20script&sort=recency&payment_verified=1&amount=0-500",
    "https://www.upwork.com/nx/search/jobs/?q=python%20web%20scraping&sort=recency&payment_verified=1&amount=0-500&proposals=0-4",
    "https://www.upwork.com/nx/search/jobs/?q=python%20automation%20script&sort=recency&payment_verified=1&amount=0-500&proposals=0-4",
    "https://www.upwork.com/nx/search/jobs/?q=autocad%20revit&sort=recency&payment_verified=1&amount=0-100",
    "https://www.upwork.com/nx/search/jobs/?q=csv%20excel%20python&sort=recency&payment_verified=1&amount=0-200&proposals=0-4",
]

all_jobs = []

for search_url in SEARCHES:
    query = search_url.split("q=")[1].split("&")[0].replace("%20", " ")
    print(f"\n{'='*60}")
    print(f"Searching: {query}")

    page.evaluate(f"window.location.href = '{search_url}'")
    time.sleep(3)

    # Wait for page load / Cloudflare
    for i in range(20):
        try:
            title = page.title()
            if "Just a moment" in title:
                print(f"  Cloudflare... ({i+1})")
                time.sleep(2)
            elif "search" in page.url.lower() or "jobs" in title.lower():
                break
            else:
                time.sleep(2)
        except:
            time.sleep(2)

    time.sleep(3)
    print(f"  Page: {page.title()[:50]}")

    if "Just a moment" in page.title():
        print("  Cloudflare blocked, skipping...")
        continue

    # Extract job listings
    jobs = page.evaluate("""(() => {
        const cards = document.querySelectorAll('[data-test="job-tile-list"] section, [class*="job-tile"], article[data-ev-label]');
        if (cards.length === 0) {
            // Try alternative selectors
            const altCards = document.querySelectorAll('[data-test="UpCLineClamp"] , h2 a[href*="/jobs/"]');
            const results = [];
            const seen = new Set();
            const links = document.querySelectorAll('a[href*="/jobs/~"]');
            for (const link of links) {
                const href = link.href;
                if (seen.has(href)) continue;
                seen.add(href);
                const card = link.closest('section') || link.closest('article') || link.closest('[class*="tile"]') || link.parentElement.parentElement;
                if (!card) continue;
                const text = card.innerText || '';
                const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                results.push({
                    title: link.textContent.trim().substring(0, 100),
                    url: href,
                    text: lines.slice(0, 8).join(' | '),
                });
            }
            return results.slice(0, 10);
        }

        return Array.from(cards).slice(0, 10).map(card => {
            const titleEl = card.querySelector('a[href*="/jobs/"]');
            const text = card.innerText || '';
            const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            return {
                title: titleEl ? titleEl.textContent.trim().substring(0, 100) : lines[0] || '',
                url: titleEl ? titleEl.href : '',
                text: lines.slice(0, 8).join(' | '),
            };
        });
    })()""")

    print(f"  Found {len(jobs)} jobs")
    for j in jobs:
        print(f"    - {j['title'][:70]}")
        print(f"      {j['text'][:120]}")
        print(f"      {j['url'][:80]}")
        j['query'] = query
        all_jobs.append(j)

# Also check best matches
print(f"\n{'='*60}")
print(f"Checking Best Matches...")
page.evaluate("window.location.href = 'https://www.upwork.com/nx/find-work/best-matches'")
time.sleep(3)
for i in range(20):
    try:
        if "Just a moment" in page.title():
            time.sleep(2)
        else:
            break
    except:
        time.sleep(2)
time.sleep(3)

best_matches = page.evaluate("""(() => {
    const links = document.querySelectorAll('a[href*="/jobs/~"]');
    const seen = new Set();
    const results = [];
    for (const link of links) {
        const href = link.href;
        if (seen.has(href)) continue;
        seen.add(href);
        const card = link.closest('section') || link.closest('article') || link.closest('[class*="tile"]') || link.parentElement.parentElement;
        if (!card) continue;
        const text = card.innerText || '';
        const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
        results.push({
            title: link.textContent.trim().substring(0, 100),
            url: href,
            text: lines.slice(0, 8).join(' | '),
        });
    }
    return results.slice(0, 10);
})()""")

print(f"  Found {len(best_matches)} best matches")
for j in best_matches:
    print(f"    - {j['title'][:70]}")
    print(f"      {j['text'][:120]}")
    j['query'] = 'best-matches'
    all_jobs.append(j)

# Summary
print(f"\n{'='*60}")
print(f"TOTAL JOBS FOUND: {len(all_jobs)}")
print(f"{'='*60}")

# Save for processing
with open('/mnt/d/_CLAUDE-TOOLS/opportunityengine/scouts/_scan_results.json', 'w') as f:
    json.dump(all_jobs, f, indent=2)
print(f"Saved to _scan_results.json")

pw.stop()

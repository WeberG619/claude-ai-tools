"""Scan Upwork for LOW competition jobs (0-4 proposals) posted recently."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

# Use search with strict filters: verified payment, 0-4 proposals, recent
SEARCHES = [
    ("python script", "https://www.upwork.com/nx/search/jobs/?q=python%20script&sort=recency&payment_verified=1&proposals=0-4&per_page=20"),
    ("web scraping", "https://www.upwork.com/nx/search/jobs/?q=web%20scraping&sort=recency&payment_verified=1&proposals=0-4&per_page=20"),
    ("data extraction", "https://www.upwork.com/nx/search/jobs/?q=data%20extraction&sort=recency&payment_verified=1&proposals=0-4&per_page=20"),
    ("automation bot", "https://www.upwork.com/nx/search/jobs/?q=automation%20bot&sort=recency&payment_verified=1&proposals=0-4&per_page=20"),
    ("revit cad bim", "https://www.upwork.com/nx/search/jobs/?q=revit%20OR%20cad%20OR%20bim&sort=recency&payment_verified=1&proposals=0-4&per_page=20"),
]

for query_name, search_url in SEARCHES:
    print(f"\n{'='*60}")
    print(f"SEARCH: {query_name} (low competition)")

    page.evaluate(f"window.location.href = '{search_url}'")
    time.sleep(3)
    for i in range(25):
        try:
            if "Just a moment" in page.title():
                time.sleep(2)
            elif "search" in page.url.lower():
                break
            else:
                time.sleep(1)
        except:
            time.sleep(2)
    time.sleep(3)

    if "Just a moment" in page.title():
        print("  Cloudflare blocked")
        continue

    # Extract ALL job info from the search results page
    jobs = page.evaluate("""(() => {
        // Get all job links
        const jobLinks = document.querySelectorAll('a[href*="/jobs/~"]');
        const seen = new Set();
        const results = [];

        for (const link of jobLinks) {
            const href = link.href.split('?')[0];
            if (seen.has(href) || !link.textContent.trim()) continue;
            seen.add(href);

            // Walk up to find the job card container
            let card = link;
            for (let i = 0; i < 10; i++) {
                if (!card.parentElement) break;
                card = card.parentElement;
                if (card.tagName === 'SECTION' || card.tagName === 'ARTICLE') break;
                const cls = (typeof card.className === 'string') ? card.className : '';
                if (cls.includes('tile') || cls.includes('card') || cls.includes('job')) break;
            }

            const cardText = card.innerText || '';
            const lines = cardText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);

            // Extract key fields from card text
            let budget = '', level = '', proposals = '', posted = '', description = '';
            for (const line of lines) {
                if (line.includes('Est. budget') || line.match(/^\\$\\d/)) budget = line;
                if (line.includes('Entry Level') || line.includes('Intermediate') || line.includes('Expert')) {
                    if (line.length < 30) level = line;
                }
                if (line.includes('Proposals') || line.match(/^Less than \\d/)) proposals = line;
                if (line.includes('Posted') || line.includes('ago')) {
                    if (line.length < 50) posted = line;
                }
            }
            // Description is usually the longest line
            const descLines = lines.filter(l => l.length > 80);
            if (descLines.length > 0) description = descLines[0];

            results.push({
                title: link.textContent.trim().substring(0, 100),
                url: href,
                budget: budget,
                level: level,
                proposals: proposals,
                posted: posted,
                description: description.substring(0, 200),
                applied: cardText.includes('Applied'),
            });
        }

        return results;
    })()""")

    print(f"  Found {len(jobs)} unique jobs")
    for j in jobs:
        if j['applied']:
            print(f"  [APPLIED] {j['title'][:60]}")
            continue
        print(f"\n  >> {j['title'][:70]}")
        if j['posted']: print(f"     Posted: {j['posted']}")
        if j['budget']: print(f"     Budget: {j['budget']}")
        if j['level']: print(f"     Level: {j['level']}")
        if j['proposals']: print(f"     Proposals: {j['proposals']}")
        if j['description']: print(f"     Desc: {j['description'][:150]}...")
        print(f"     URL: {j['url'][:80]}")

pw.stop()

"""Scan Upwork for jobs with <5 proposals - best shot at winning."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

SEARCHES = [
    ("python automation <5 proposals", "https://www.upwork.com/nx/search/jobs/?q=python+automation&sort=recency&proposals=0-4&payment_verified=1"),
    ("web scraping <5 proposals", "https://www.upwork.com/nx/search/jobs/?q=web+scraping&sort=recency&proposals=0-4&payment_verified=1"),
    ("revit OR autocad <5 proposals", "https://www.upwork.com/nx/search/jobs/?q=revit+OR+autocad&sort=recency&proposals=0-4&payment_verified=1"),
    ("data entry excel <5 proposals", "https://www.upwork.com/nx/search/jobs/?q=data+entry+excel+python&sort=recency&proposals=0-4&payment_verified=1"),
    ("bot automation api <5 proposals", "https://www.upwork.com/nx/search/jobs/?q=bot+automation+api&sort=recency&proposals=0-4&payment_verified=1"),
]

all_jobs = []

for search_name, search_url in SEARCHES:
    print(f"\n{'='*60}")
    print(f"SEARCH: {search_name}")

    page.evaluate(f"window.location.href = '{search_url}'")
    time.sleep(4)
    for i in range(25):
        try:
            if "Just a moment" in page.title():
                time.sleep(2)
            else:
                break
        except:
            time.sleep(2)
    time.sleep(3)

    if "Just a moment" in page.title():
        print("  Cloudflare blocked")
        continue

    # Get full page text and parse job listings
    jobs_text = page.evaluate("""(() => {
        const body = document.body.innerText;
        // Split by "Posted" to get individual job blocks
        const blocks = body.split(/(?=Posted \\d+ (?:minutes?|hours?|days?|weeks?) ago)/);
        const jobs = [];

        for (const block of blocks) {
            if (!block.startsWith('Posted')) continue;
            const lines = block.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            if (lines.length < 5) continue;

            const posted = lines[0] || '';
            let title = '';
            let budget = '';
            let level = '';
            let proposals = '';
            let description = '';
            let payment = '';
            let spent = '';
            let rating = '';
            let applied = false;

            for (const line of lines) {
                if (line.includes('Job Feedback') && !title) {
                    const idx = lines.indexOf(line);
                    if (idx > 0) title = lines[idx].replace('Job Feedback', '').trim();
                }
                if (line.includes('Est. budget')) budget = line;
                if (line.match(/^Hourly:/)) budget = line;
                if (line.includes('Fixed price')) budget += ' Fixed';
                if (line.match(/^(Entry Level|Intermediate|Expert)$/)) level = line;
                if (line.includes('Proposals:')) proposals = line;
                if (line.includes('Payment verified')) payment = 'verified';
                if (line.includes('Payment unverified')) payment = 'unverified';
                if (line.match(/^\\$[\\d,]+/)) spent = line;
                if (line.includes('Rating is')) rating = line;
                if (line === 'Applied') applied = true;
            }

            // Get description - longest line
            const descLines = lines.filter(l => l.length > 100 && !l.includes('Job Feedback'));
            description = descLines.length > 0 ? descLines[0] : '';

            // Get title from second line if not found
            if (!title && lines.length > 1) {
                for (const line of lines.slice(1)) {
                    if (line.length > 15 && line.length < 120 && !line.includes('Save Job') && !line.includes('Feedback')) {
                        title = line;
                        break;
                    }
                }
            }

            if (title && !applied) {
                jobs.push({posted, title, budget, level, proposals, description: description.substring(0, 250), payment, spent, rating});
            }
        }
        return jobs;
    })()""")

    print(f"  Found {len(jobs_text)} jobs")
    for j in jobs_text:
        print(f"\n  >> {j['title'][:70]}")
        print(f"     {j['posted']} | {j['budget']} | {j['level']} | {j['proposals']}")
        if j['spent']: print(f"     Client: {j['payment']}, spent {j['spent']}, {j['rating']}")
        if j['description']: print(f"     {j['description'][:150]}")
        all_jobs.append(j)

# Summary of best candidates
print(f"\n\n{'='*60}")
print(f"TOTAL UNIQUE JOBS FOUND: {len(all_jobs)}")
print(f"{'='*60}")

pw.stop()

"""Scan Reddit for fresh gigs and get usernames for existing opps."""
from playwright.sync_api import sync_playwright
import time
import json

CDP_URL = "http://localhost:9222"

# Reddit URLs to check for usernames
EXISTING_OPPS = [
    {"id": 259, "url": "https://www.reddit.com/r/freelance_forhire/comments/1r2egbv/hiring_hello_im_looking_for_someone/", "title": "freelance_forhire $700"},
    {"id": 298, "url": "https://www.reddit.com/r/PythonJobs/comments/1qyi0em/i_need_5_people_for_a_work_200_pay/", "title": "PythonJobs $200"},
]

# Subreddits to scan for new gigs
SCAN_SUBS = [
    "https://www.reddit.com/r/forhire/new/",
    "https://www.reddit.com/r/slavelabour/new/",
    "https://www.reddit.com/r/freelance_forhire/new/",
]

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp(CDP_URL)
context = browser.contexts[0]
page = context.pages[0]

print(f"Current: {page.title()[:50]}")

# First get usernames for existing opps
print("\n=== Getting usernames for existing opps ===")
for opp in EXISTING_OPPS:
    print(f"\nOpp #{opp['id']}: {opp['title']}")
    page.evaluate(f"window.location.href = '{opp['url']}'")
    time.sleep(4)

    # Wait for page
    for i in range(15):
        try:
            if "reddit.com" in page.url and "comments" in page.url:
                break
            time.sleep(1)
        except:
            time.sleep(1)
    time.sleep(2)

    # Get author
    author = page.evaluate("""(() => {
        // Try multiple selectors for the post author
        const authorLinks = document.querySelectorAll('a[href*="/user/"]');
        for (const a of authorLinks) {
            const href = a.href;
            const match = href.match(/\\/user\\/([^\\/\\?]+)/);
            if (match && a.closest('[class*="post"], [class*="Post"], article, [data-testid*="post"]')) {
                return match[1];
            }
        }
        // Fallback: first user link
        for (const a of authorLinks) {
            const match = a.href.match(/\\/user\\/([^\\/\\?]+)/);
            if (match && match[1] !== 'AutoModerator') return match[1];
        }
        return null;
    })()""")

    if author:
        print(f"  Author: u/{author}")
        opp['author'] = author
    else:
        # Try getting from page text
        text = page.evaluate("document.body.innerText.substring(0, 500)")
        print(f"  Author not found. Page text: {text[:200]}")
        opp['author'] = None

# Now scan for new gigs
print(f"\n\n=== Scanning for NEW Reddit gigs ===")
new_gigs = []

for sub_url in SCAN_SUBS:
    sub_name = sub_url.split("/r/")[1].split("/")[0]
    print(f"\n--- r/{sub_name} ---")

    page.evaluate(f"window.location.href = '{sub_url}'")
    time.sleep(4)

    for i in range(10):
        try:
            if "reddit.com" in page.url:
                break
            time.sleep(1)
        except:
            time.sleep(1)
    time.sleep(2)

    # Get recent [Hiring] posts
    posts = page.evaluate("""(() => {
        const links = document.querySelectorAll('a[href*="/comments/"]');
        const seen = new Set();
        const results = [];

        for (const link of links) {
            const href = link.href.split('?')[0];
            if (seen.has(href)) continue;
            const text = link.textContent.trim();
            if (text.length < 15 || text.length > 300) continue;
            // Look for hiring posts
            const lowerText = text.toLowerCase();
            if (lowerText.includes('[hiring]') || lowerText.includes('[task]') ||
                lowerText.includes('looking for') || lowerText.includes('need someone') ||
                lowerText.includes('hire') || lowerText.includes('paying')) {
                seen.add(href);
                results.push({title: text.substring(0, 150), url: href});
            }
        }
        return results.slice(0, 10);
    })()""")

    print(f"  Found {len(posts)} hiring posts")
    for p in posts:
        print(f"    {p['title'][:80]}")
        print(f"    {p['url'][:80]}")
        new_gigs.append({**p, 'subreddit': sub_name})

# Summary
print(f"\n\n{'='*60}")
print("READY TO DM:")
for opp in EXISTING_OPPS:
    if opp.get('author'):
        print(f"  Opp #{opp['id']}: u/{opp['author']} - {opp['title']}")

print(f"\nNEW GIGS FOUND: {len(new_gigs)}")
for g in new_gigs:
    print(f"  [{g['subreddit']}] {g['title'][:70]}")

pw.stop()

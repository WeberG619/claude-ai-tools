"""Scan Reddit for gigs and get poster usernames - fixed waits."""
from playwright.sync_api import sync_playwright
import time

CDP_URL = "http://localhost:9222"

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp(CDP_URL)
context = browser.contexts[0]
page = context.pages[0]

def safe_navigate(page, url, wait_secs=6):
    """Navigate and wait safely."""
    page.evaluate(f"window.location.href = '{url}'")
    time.sleep(wait_secs)
    for i in range(10):
        try:
            page.title()
            return True
        except:
            time.sleep(1)
    return False

def get_author(page):
    """Get post author from Reddit page."""
    try:
        return page.evaluate("""(() => {
            const links = document.querySelectorAll('a[href*="/user/"]');
            for (const a of links) {
                const m = a.href.match(/\\/user\\/([A-Za-z0-9_-]+)/);
                if (m && m[1] !== 'AutoModerator' && m[1] !== 'reddit') return m[1];
            }
            return null;
        })()""")
    except:
        return None

# Scan r/forhire for hiring posts
print("=== Scanning r/forhire/new ===")
safe_navigate(page, "https://www.reddit.com/r/forhire/new/")

forhire = page.evaluate("""(() => {
    const posts = document.querySelectorAll('a[href*="/comments/"]');
    const seen = new Set();
    const results = [];
    for (const a of posts) {
        const href = a.href.split('?')[0];
        if (seen.has(href) || !a.textContent.trim()) continue;
        const text = a.textContent.trim();
        if (text.length < 15 || text.length > 300) continue;
        if (text.toLowerCase().includes('[hiring]') || text.toLowerCase().includes('[task]')) {
            seen.add(href);
            results.push({title: text.substring(0, 150), url: href});
        }
    }
    return results.slice(0, 8);
})()""")

print(f"Found {len(forhire)} hiring posts:")
for p in forhire:
    print(f"  {p['title'][:80]}")

# Scan r/slavelabour
print("\n=== Scanning r/slavelabour/new ===")
safe_navigate(page, "https://www.reddit.com/r/slavelabour/new/")

slavelabour = page.evaluate("""(() => {
    const posts = document.querySelectorAll('a[href*="/comments/"]');
    const seen = new Set();
    const results = [];
    for (const a of posts) {
        const href = a.href.split('?')[0];
        if (seen.has(href) || !a.textContent.trim()) continue;
        const text = a.textContent.trim();
        if (text.length < 15 || text.length > 300) continue;
        if (text.toLowerCase().includes('[task]') || text.toLowerCase().includes('$') || text.toLowerCase().includes('need')) {
            seen.add(href);
            results.push({title: text.substring(0, 150), url: href});
        }
    }
    return results.slice(0, 8);
})()""")

print(f"Found {len(slavelabour)} task posts:")
for p in slavelabour:
    print(f"  {p['title'][:80]}")

# Scan r/freelance_forhire
print("\n=== Scanning r/freelance_forhire/new ===")
safe_navigate(page, "https://www.reddit.com/r/freelance_forhire/new/")

freelance = page.evaluate("""(() => {
    const posts = document.querySelectorAll('a[href*="/comments/"]');
    const seen = new Set();
    const results = [];
    for (const a of posts) {
        const href = a.href.split('?')[0];
        if (seen.has(href) || !a.textContent.trim()) continue;
        const text = a.textContent.trim();
        if (text.length < 15 || text.length > 300) continue;
        if (text.toLowerCase().includes('[hiring]') || text.toLowerCase().includes('looking for') || text.toLowerCase().includes('need')) {
            seen.add(href);
            results.push({title: text.substring(0, 150), url: href});
        }
    }
    return results.slice(0, 8);
})()""")

print(f"Found {len(freelance)} hiring posts:")
for p in freelance:
    print(f"  {p['title'][:80]}")

# Now check the most promising posts for tech/automation/python gigs
all_posts = forhire + slavelabour + freelance
tech_gigs = []

for post in all_posts:
    title_lower = post['title'].lower()
    tech_keywords = ['python', 'script', 'automat', 'web', 'scrip', 'bot', 'data', 'excel',
                     'api', 'develop', 'code', 'program', 'software', 'ai', 'machine learn',
                     'cad', 'revit', 'design', 'website']
    if any(kw in title_lower for kw in tech_keywords):
        tech_gigs.append(post)

print(f"\n\n=== TECH GIGS ({len(tech_gigs)}) ===")
for g in tech_gigs:
    print(f"  {g['title'][:80]}")
    print(f"  {g['url'][:80]}")

# For each tech gig, get author
print("\n=== Getting authors ===")
for g in tech_gigs[:5]:  # Top 5 only
    print(f"\nChecking: {g['title'][:60]}")
    safe_navigate(page, g['url'])
    author = get_author(page)
    g['author'] = author
    if author:
        print(f"  Author: u/{author}")

        # Get post content
        try:
            content = page.evaluate("""(() => {
                const posts = document.querySelectorAll('[data-testid="post-container"], [class*="Post"], article');
                for (const p of posts) {
                    const text = p.innerText;
                    if (text.length > 100) return text.substring(0, 500);
                }
                return document.body.innerText.substring(0, 500);
            })()""")
            g['content'] = content
            print(f"  Content: {content[:150]}...")
        except:
            g['content'] = ''
    else:
        print(f"  Author not found")

# Summary
print(f"\n\n{'='*60}")
print("READY TO DM:")
for g in tech_gigs:
    if g.get('author'):
        print(f"\n  u/{g['author']}: {g['title'][:70]}")
        print(f"  URL: {g['url'][:80]}")

pw.stop()

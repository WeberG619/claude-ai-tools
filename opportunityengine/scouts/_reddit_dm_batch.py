# -*- coding: utf-8 -*-
"""Get authors for top Reddit gigs and send DMs."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

CDP_URL = "http://localhost:9222"

# Best tech gigs to pursue
GIGS = [
    {
        "title": "Create a AI Agent",
        "search_url": "https://www.reddit.com/r/slavelabour/search/?q=create+AI+agent&sort=new&t=week",
        "sub": "slavelabour",
    },
    {
        "title": "Bin schedule ICS file",
        "search_url": "https://www.reddit.com/r/slavelabour/search/?q=bin+schedule+ICS&sort=new&t=month",
        "sub": "slavelabour",
    },
    {
        "title": "Simple paid Tasks $30",
        "search_url": "https://www.reddit.com/r/forhire/search/?q=simple+paid+tasks&sort=new&t=week",
        "sub": "forhire",
    },
    {
        "title": "Create additional pages on website",
        "search_url": "https://www.reddit.com/r/slavelabour/search/?q=create+pages+website&sort=new&t=week",
        "sub": "slavelabour",
    },
]

# Direct URLs from the subreddit scan
DIRECT_URLS = []

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp(CDP_URL)
context = browser.contexts[0]
page = context.pages[0]

def safe_nav(url, wait=5):
    page.evaluate(f"window.location.href = '{url}'")
    time.sleep(wait)
    for i in range(5):
        try:
            page.title()
            return True
        except:
            time.sleep(1)
    return False

def get_author():
    try:
        return page.evaluate("""(() => {
            const links = document.querySelectorAll('a[href*="/user/"]');
            for (const a of links) {
                const m = a.href.match(/\\/user\\/([A-Za-z0-9_-]+)/);
                if (m && m[1] !== 'AutoModerator' && m[1] !== 'reddit' && m[1] !== 'BotDefense') return m[1];
            }
            return null;
        })()""")
    except:
        return None

def send_dm(username, subject, body):
    """Send a Reddit DM."""
    compose_url = f"https://www.reddit.com/message/compose/?to={username}"
    safe_nav(compose_url, 5)

    title_input = page.locator('input[name="message-title"]')
    try:
        title_input.fill(subject, timeout=5000)
        time.sleep(0.5)
    except Exception as e:
        print(f"  Title fill failed: {e}")
        return False

    body_input = page.locator('textarea[name="message-content"]')
    try:
        body_input.fill(body, timeout=5000)
        time.sleep(0.5)
    except Exception as e:
        print(f"  Body fill failed: {e}")
        return False

    # Click Send
    send_btn = page.locator('button:has-text("Send message"), button[type="submit"]:has-text("Send")')
    try:
        send_btn.click(timeout=5000)
        time.sleep(3)
        print(f"  DM sent to u/{username}!")
        return True
    except Exception as e:
        print(f"  Send failed: {e}")
        return False


# Step 1: Navigate to r/slavelabour/new to find the AI Agent post
print("=== Finding AI Agent post ===")
safe_nav("https://www.reddit.com/r/slavelabour/new/")

# Get post URLs from the page
posts = page.evaluate("""(() => {
    const links = document.querySelectorAll('a[href*="/comments/"]');
    const seen = new Set();
    const results = [];
    for (const a of links) {
        const href = a.href.split('?')[0];
        if (seen.has(href)) continue;
        const text = a.textContent.trim();
        if (text.length < 10 || text.length > 300) continue;
        seen.add(href);
        results.push({title: text, url: href});
    }
    return results.slice(0, 20);
})()""")

# Find our target posts
targets = []
for p in posts:
    title_lower = p['title'].lower()
    if ('ai agent' in title_lower or 'bin schedule' in title_lower or
        'ics' in title_lower or 'website' in title_lower and 'pages' in title_lower):
        targets.append(p)
        print(f"  Found: {p['title'][:70]}")

# Also check r/forhire for the simple tasks post
print("\n=== Finding Simple Tasks post ===")
safe_nav("https://www.reddit.com/r/forhire/new/")

forhire_posts = page.evaluate("""(() => {
    const links = document.querySelectorAll('a[href*="/comments/"]');
    const seen = new Set();
    const results = [];
    for (const a of links) {
        const href = a.href.split('?')[0];
        if (seen.has(href)) continue;
        const text = a.textContent.trim();
        if (text.length < 10 || text.length > 300) continue;
        seen.add(href);
        results.push({title: text, url: href});
    }
    return results.slice(0, 20);
})()""")

for p in forhire_posts:
    if 'simple paid' in p['title'].lower() or 'website designer' in p['title'].lower():
        targets.append(p)
        print(f"  Found: {p['title'][:70]}")

print(f"\n=== Processing {len(targets)} target posts ===")

# Get author for each and prepare DMs
dm_queue = []
for t in targets:
    print(f"\nPost: {t['title'][:60]}")
    safe_nav(t['url'])
    author = get_author()
    if not author:
        print("  No author found")
        continue
    print(f"  Author: u/{author}")

    # Get post content for context
    try:
        content = page.evaluate("document.body.innerText.substring(0, 800)")
    except:
        content = ''

    t['author'] = author
    t['content'] = content

    # Generate appropriate DM based on the post
    title_lower = t['title'].lower()

    if 'ai agent' in title_lower:
        subject = "Re: Create an AI Agent - I build these professionally"
        body = """Hi,

I saw your post about creating an AI agent. This is exactly what I do - I build production AI agent systems with Python, including:

- Autonomous agents that run 24/7 with task queues and decision engines
- Claude/GPT API integration with tool use and function calling
- Browser automation agents (Playwright)
- Multi-platform agents (Telegram, Discord, web)

I've built a full autonomous agent framework with scheduled tasks, API integrations, voice TTS, and a SQLite backend. Happy to scope out what you need.

What's the agent supposed to do? I can give you a realistic estimate and approach.

Best,
Weber Gouin"""
    elif 'bin schedule' in title_lower or 'ics' in title_lower:
        subject = "Re: Bin Schedule to ICS - Quick job, I can do this today"
        body = """Hi,

Saw your post about converting a council bin schedule to an ICS calendar file. I can knock this out quickly.

My approach:
- Parse the council schedule (PDF/webpage)
- Generate a proper .ics file with recurring events for each bin type
- Include reminders so you get notified the night before

I work with Python and calendar APIs regularly. This is a quick one - I could have it done within a few hours.

Want to share the council schedule link?

Best,
Weber Gouin"""
    elif 'simple paid' in title_lower:
        subject = "Re: Simple Paid Tasks - Available and ready"
        body = """Hi,

Interested in the simple paid tasks you posted about. I'm a developer with experience in:
- Python scripting and automation
- Web scraping and data extraction
- Excel/CSV data processing
- API integrations

What kind of tasks do you have? Happy to start with one to show my work quality.

Best,
Weber Gouin"""
    elif 'website' in title_lower and ('pages' in title_lower or 'designer' in title_lower):
        subject = "Re: Website Work - Full-stack developer available"
        body = """Hi,

Saw your post about website work. I build websites with HTML/CSS, React, and Python backends. I can create clean, responsive pages quickly.

Happy to discuss the details - what pages do you need and do you have an existing site/framework?

Best,
Weber Gouin"""
    else:
        continue

    dm_queue.append({
        'author': author,
        'subject': subject,
        'body': body,
        'title': t['title'],
    })

# Send DMs
print(f"\n\n{'='*60}")
print(f"SENDING {len(dm_queue)} DMs")
print(f"{'='*60}")

results = []
for dm in dm_queue:
    print(f"\nDM to u/{dm['author']}: {dm['subject'][:50]}")
    ok = send_dm(dm['author'], dm['subject'], dm['body'])
    results.append({'author': dm['author'], 'ok': ok, 'title': dm['title']})
    time.sleep(3)  # Rate limit between DMs

print(f"\n\n{'='*60}")
print("RESULTS:")
for r in results:
    status = "SENT" if r['ok'] else "FAILED"
    print(f"  [{status}] u/{r['author']}: {r['title'][:60]}")

pw.stop()

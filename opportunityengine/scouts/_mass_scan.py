# -*- coding: utf-8 -*-
"""Mass scan Upwork + Reddit for easy quick-win gigs, then submit."""
from playwright.sync_api import sync_playwright
import time
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

CDP_URL = "http://localhost:9222"

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp(CDP_URL)
context = browser.contexts[0]
page = context.pages[0]

def safe_nav(url, wait=5):
    page.evaluate(f"window.location.href = '{url}'")
    time.sleep(wait)
    for i in range(8):
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
                if (m && !['AutoModerator','reddit','BotDefense','RemindMeBot'].includes(m[1])) return m[1];
            }
            return null;
        })()""")
    except:
        return None

def send_dm(username, subject, body):
    safe_nav(f"https://www.reddit.com/message/compose/?to={username}", 5)
    try:
        page.locator('input[name="message-title"]').fill(subject, timeout=5000)
        time.sleep(0.3)
        page.locator('textarea[name="message-content"]').fill(body, timeout=5000)
        time.sleep(0.3)
        page.locator('button:has-text("Send message"), button[type="submit"]:has-text("Send")').click(timeout=5000)
        time.sleep(3)
        return True
    except Exception as e:
        print(f"    DM failed: {str(e)[:80]}")
        return False

# ============================================================
# PART 1: UPWORK - More keyword searches
# ============================================================
print("=" * 60)
print("PART 1: UPWORK SCANNING")
print("=" * 60)

UPWORK_SEARCHES = [
    "simple+python+script",
    "quick+task+python",
    "excel+macro+automation",
    "pdf+data+extraction",
    "small+website+fix",
    "bug+fix+python",
    "google+sheets+automation",
    "chatgpt+api+integration",
    "claude+api",
    "n8n+automation",
    "zapier+make+automation",
    "selenium+playwright+scraping",
]

upwork_jobs = []

for query in UPWORK_SEARCHES:
    url = f"https://www.upwork.com/nx/search/jobs/?q={query}&sort=recency&proposals=0-4&payment_verified=1"
    safe_nav(url, 5)

    # Wait for results
    for i in range(15):
        try:
            if "Just a moment" in page.title():
                time.sleep(2)
            else:
                count = page.evaluate("document.querySelectorAll('a[href*=\"/jobs/\"]').length")
                if count > 3:
                    break
                time.sleep(1)
        except:
            time.sleep(1)
    time.sleep(2)

    if "Just a moment" in page.title():
        continue

    # Extract jobs
    jobs = page.evaluate("""(() => {
        const body = document.body.innerText;
        const blocks = body.split(/(?=Posted \\d+ (?:minutes?|hours?|days?) ago)/);
        const jobs = [];
        for (const block of blocks) {
            if (!block.startsWith('Posted')) continue;
            const lines = block.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            if (lines.length < 3) continue;
            let title = '', budget = '', proposals = '', posted = lines[0], applied = false;
            for (const line of lines) {
                if (line.includes('Est. budget')) budget = line;
                if (line.match(/^Hourly/)) budget = line;
                if (line.includes('Proposals:')) proposals = line;
                if (line === 'Applied') applied = true;
            }
            const descLines = lines.filter(l => l.length > 80);
            const desc = descLines.length > 0 ? descLines[0] : '';
            // Title is the line after "Posted X ago" that contains "Job Feedback"
            for (const line of lines.slice(1)) {
                if (line.length > 10 && line.length < 120 && !line.includes('Save Job') && !line.includes('Feedback') && !line.includes('Fixed price') && !line.includes('Hourly')) {
                    title = line;
                    break;
                }
            }
            if (title && !applied) jobs.push({title, budget, proposals, posted, desc: desc.substring(0, 200)});
        }
        return jobs;
    })()""")

    q_display = query.replace("+", " ")
    if jobs:
        print(f"\n  [{q_display}] {len(jobs)} jobs")
        for j in jobs:
            print(f"    {j['title'][:65]} | {j['budget'][:30]} | {j['proposals']}")
            upwork_jobs.append({**j, 'query': q_display})

# Get URLs for the best Upwork jobs
print(f"\n\nTotal Upwork jobs found: {len(upwork_jobs)}")

# Deduplicate by title
seen_titles = set()
unique_jobs = []
for j in upwork_jobs:
    if j['title'] not in seen_titles:
        seen_titles.add(j['title'])
        unique_jobs.append(j)
upwork_jobs = unique_jobs
print(f"After dedup: {len(upwork_jobs)}")

# Get URLs for the most promising ones
print("\n=== Getting Upwork job URLs ===")
# Go back to search to grab URLs
best_queries = list(set(j['query'] for j in upwork_jobs[:10]))
job_urls = {}

for q in best_queries[:5]:
    encoded = q.replace(" ", "+")
    url = f"https://www.upwork.com/nx/search/jobs/?q={encoded}&sort=recency&proposals=0-4&payment_verified=1"
    safe_nav(url, 5)
    time.sleep(3)

    links = page.evaluate("""(() => {
        const links = document.querySelectorAll('a[href*="/jobs/"]');
        const results = {};
        for (const a of links) {
            const text = a.textContent.trim();
            if (text.length > 10 && text.length < 150) {
                results[text] = a.href.split('?')[0];
            }
        }
        return results;
    })()""")

    for title, url in links.items():
        if title not in job_urls:
            job_urls[title] = url

print(f"Mapped {len(job_urls)} job URLs")

# ============================================================
# PART 2: REDDIT - More subreddits
# ============================================================
print("\n" + "=" * 60)
print("PART 2: REDDIT SCANNING")
print("=" * 60)

REDDIT_SUBS = [
    ("r/slavelabour/new", ["[task]", "$", "need", "looking for", "pay"]),
    ("r/forhire/new", ["[hiring]"]),
    ("r/freelance_forhire/new", ["[hiring]"]),
    ("r/PythonJobs/new", ["hiring", "need", "$"]),
    ("r/webdev/new", ["hiring", "freelance", "looking for"]),
]

reddit_gigs = []
already_dmed = {"eddy14207", "GenericUser104", "AdMental6886", "Penoliya_Haruhi", "Reasonable_Salary182"}

for sub_path, keywords in REDDIT_SUBS:
    sub_name = sub_path.split("/")[0]
    print(f"\n--- {sub_path} ---")
    safe_nav(f"https://www.reddit.com/{sub_path}/")

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
        return results.slice(0, 15);
    })()""")

    for p in posts:
        title_lower = p['title'].lower()
        if any(kw in title_lower for kw in keywords):
            # Filter for tech gigs
            tech_words = ['python', 'script', 'automat', 'web', 'scrip', 'bot', 'data', 'excel',
                          'api', 'develop', 'code', 'program', 'software', 'ai', 'design',
                          'website', 'app', 'database', 'server', 'deploy', 'fix', 'debug',
                          'task', '$', 'pay', 'simple', 'quick', 'small']
            if any(tw in title_lower for tw in tech_words):
                reddit_gigs.append({**p, 'sub': sub_name})
                print(f"  {p['title'][:75]}")

print(f"\n\nTotal Reddit tech gigs: {len(reddit_gigs)}")

# Get authors and send DMs for the best ones
print("\n=== Processing Reddit gigs ===")
dm_results = []

for gig in reddit_gigs[:8]:  # Process top 8
    print(f"\n>> {gig['title'][:65]}")
    safe_nav(gig['url'])
    author = get_author()

    if not author:
        print("  No author found")
        continue

    if author in already_dmed:
        print(f"  Already DM'd u/{author}, skipping")
        continue

    print(f"  Author: u/{author}")

    # Get post content for context
    try:
        content = page.evaluate("document.body.innerText.substring(0, 600)")
    except:
        content = ''

    # Generate DM based on post content
    title_lower = gig['title'].lower()

    if any(kw in title_lower for kw in ['python', 'script', 'automat', 'bot', 'api', 'code', 'program', 'software', 'ai']):
        subject = f"Re: {gig['title'][:60]}"
        body = f"""Hi,

Saw your post and I'm interested. I'm a Python developer specializing in automation, APIs, and AI integration. I've built production systems including:

- Autonomous AI agents with Claude/GPT APIs
- Browser automation with Playwright/Selenium
- Data pipelines and web scrapers
- n8n/Make workflow automation

Happy to discuss scope and pricing. What specifically do you need built?

Best,
Weber Gouin"""

    elif any(kw in title_lower for kw in ['web', 'website', 'design', 'app', 'page']):
        subject = f"Re: {gig['title'][:60]}"
        body = f"""Hi,

Saw your post. I'm a full-stack developer - I build websites and web apps with HTML/CSS, React, Python backends, and can handle both design and development.

What do you need done? Happy to give you a quick estimate.

Best,
Weber Gouin"""

    elif any(kw in title_lower for kw in ['data', 'excel', 'scrip', 'scrap']):
        subject = f"Re: {gig['title'][:60]}"
        body = f"""Hi,

Saw your post. I build data extraction and processing tools with Python - web scraping, PDF parsing, Excel automation, API integrations.

What data do you need collected/processed? I can usually turn these around quickly.

Best,
Weber Gouin"""

    else:
        subject = f"Re: {gig['title'][:60]}"
        body = f"""Hi,

Saw your post and I'm interested. I'm a developer with experience in Python, automation, web development, and AI integration. Happy to discuss what you need.

Best,
Weber Gouin"""

    # Send DM
    print(f"  Sending DM...")
    ok = send_dm(author, subject, body)
    dm_results.append({'author': author, 'title': gig['title'], 'ok': ok})
    already_dmed.add(author)
    time.sleep(2)

# ============================================================
# SUMMARY
# ============================================================
print(f"\n\n{'='*60}")
print("SUMMARY")
print(f"{'='*60}")

print(f"\nUpwork jobs found (< 5 proposals): {len(upwork_jobs)}")
for j in upwork_jobs[:10]:
    print(f"  {j['title'][:60]} | {j['budget'][:25]}")

print(f"\nReddit DMs sent: {len([r for r in dm_results if r['ok']])}/{len(dm_results)}")
for r in dm_results:
    status = "SENT" if r['ok'] else "FAILED"
    print(f"  [{status}] u/{r['author']}: {r['title'][:55]}")

# Save Upwork jobs for submission
with open('D:/_CLAUDE-TOOLS/opportunityengine/scouts/_upwork_targets.json', 'w', encoding='utf-8') as f:
    json.dump({'jobs': upwork_jobs, 'urls': job_urls}, f, indent=2, ensure_ascii=False)
print(f"\nUpwork targets saved to _upwork_targets.json")

pw.stop()

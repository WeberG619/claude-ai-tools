# -*- coding: utf-8 -*-
"""Vet Reddit users who responded to our DMs - check account age, karma, post history."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

page = [p for p in context.pages if 'newtab-footer' not in p.url][0]

# Users who accepted chat invites
USERS = ['Pr0b0pass', 'dot90zoom', 'eddy14207', 'AdMental6886', 'Reasonable_Salary182']

def safe_nav(url, wait=5):
    page.evaluate(f"window.location.href = '{url}'")
    time.sleep(wait)
    for i in range(10):
        try:
            if "Just a moment" not in page.title():
                return True
            time.sleep(2)
        except:
            time.sleep(1)
    return False

results = []

for username in USERS:
    print(f"\n{'='*50}")
    print(f"CHECKING: u/{username}")
    print(f"{'='*50}")

    # Use old Reddit for reliable rendering
    safe_nav(f"https://old.reddit.com/user/{username}")
    time.sleep(2)

    # Get account info
    info = page.evaluate("""(() => {
        const text = document.body.innerText;

        // Account age - look for "redditor for X"
        const ageMatch = text.match(/redditor for (\\d+ (?:years?|months?|days?|hours?))/i);
        const age = ageMatch ? ageMatch[1] : 'unknown';

        // Karma
        const karmaMatch = text.match(/(\\d[\\d,]*) post karma.*?(\\d[\\d,]*) comment karma/i) ||
                           text.match(/(\\d[\\d,]*) karma/i);
        const karma = karmaMatch ? karmaMatch[0] : 'unknown';

        // Check if account exists
        const notFound = text.includes('page not found') || text.includes('this user has deleted');
        const suspended = text.includes('suspended');

        // Get recent post titles
        const links = document.querySelectorAll('a.title');
        const posts = [];
        for (let i = 0; i < Math.min(links.length, 5); i++) {
            posts.push(links[i].textContent.trim().substring(0, 100));
        }

        // Get subreddits they post in
        const subLinks = document.querySelectorAll('a[href*="/r/"]');
        const subs = new Set();
        for (const a of subLinks) {
            const m = a.href.match(/\\/r\\/([A-Za-z0-9_]+)/);
            if (m && m[1] !== 'all' && m[1] !== 'popular') subs.add(m[1]);
        }

        return {
            age: age,
            karma: karma,
            notFound: notFound,
            suspended: suspended,
            recentPosts: posts,
            subreddits: Array.from(subs).slice(0, 10)
        };
    })()""")

    if info['notFound']:
        print(f"  ACCOUNT NOT FOUND / DELETED")
        results.append({'user': username, 'status': 'NOT FOUND', 'risk': 'HIGH'})
        continue

    if info['suspended']:
        print(f"  ACCOUNT SUSPENDED")
        results.append({'user': username, 'status': 'SUSPENDED', 'risk': 'HIGH'})
        continue

    print(f"  Account age: {info['age']}")
    print(f"  Karma: {info['karma']}")
    print(f"  Active subreddits: {', '.join(info['subreddits'][:8])}")

    if info['recentPosts']:
        print(f"  Recent posts:")
        for p in info['recentPosts']:
            print(f"    - {p[:80]}")

    # Risk assessment
    risk = 'LOW'
    flags = []

    if info['age'] == 'unknown':
        flags.append('could not determine age')
    elif 'day' in info['age'] or 'hour' in info['age']:
        risk = 'HIGH'
        flags.append(f'very new account ({info["age"]})')
    elif 'month' in info['age']:
        months = int(info['age'].split()[0]) if info['age'].split()[0].isdigit() else 0
        if months < 3:
            risk = 'MEDIUM'
            flags.append(f'relatively new ({info["age"]})')

    if not info['recentPosts']:
        risk = max(risk, 'MEDIUM')
        flags.append('no visible posts')

    if flags:
        print(f"  RISK: {risk} - {', '.join(flags)}")
    else:
        print(f"  RISK: {risk} - Looks legitimate")

    results.append({
        'user': username,
        'age': info['age'],
        'karma': info['karma'],
        'risk': risk,
        'flags': flags,
        'subs': info['subreddits'][:5],
        'posts': len(info['recentPosts'])
    })

# Summary
print(f"\n\n{'='*60}")
print("VETTING SUMMARY")
print(f"{'='*60}")
for r in results:
    risk_emoji = {'LOW': 'OK', 'MEDIUM': 'CAUTION', 'HIGH': 'WARNING'}
    print(f"  [{risk_emoji.get(r.get('risk','?'), '?')}] u/{r['user']}: {r.get('age', '?')} | {r.get('karma', '?')} | Risk: {r.get('risk', '?')}")
    if r.get('flags'):
        print(f"        Flags: {', '.join(r['flags'])}")

pw.stop()

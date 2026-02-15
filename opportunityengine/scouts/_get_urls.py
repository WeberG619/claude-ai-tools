"""Get actual job URLs from the original search results."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

# Go to python automation search with <5 proposals filter
url = "https://www.upwork.com/nx/search/jobs/?q=python+automation&sort=recency&proposals=0-4&payment_verified=1"
page.evaluate(f"window.location.href = '{url}'")
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

# Get ALL job links with their titles
print("=== python automation <5 proposals ===")
jobs1 = page.evaluate("""(() => {
    const links = document.querySelectorAll('a[href*="/jobs/~"]');
    const seen = new Set();
    const results = [];
    for (const link of links) {
        const href = link.href.split('?')[0];
        const title = link.textContent.trim();
        if (seen.has(href) || !title || title.length < 10) continue;
        seen.add(href);
        results.push({title, url: href});
    }
    return results;
})()""")
for j in jobs1:
    print(f"  {j['title'][:60]} -> {j['url']}")

# Now revit/cad search
url2 = "https://www.upwork.com/nx/search/jobs/?q=revit+OR+autocad&sort=recency&proposals=0-4&payment_verified=1"
page.evaluate(f"window.location.href = '{url2}'")
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

print("\n=== revit/autocad <5 proposals ===")
jobs2 = page.evaluate("""(() => {
    const links = document.querySelectorAll('a[href*="/jobs/~"]');
    const seen = new Set();
    const results = [];
    for (const link of links) {
        const href = link.href.split('?')[0];
        const title = link.textContent.trim();
        if (seen.has(href) || !title || title.length < 10) continue;
        seen.add(href);
        results.push({title, url: href});
    }
    return results;
})()""")
for j in jobs2:
    print(f"  {j['title'][:60]} -> {j['url']}")

# bot automation api search
url3 = "https://www.upwork.com/nx/search/jobs/?q=bot+automation+api&sort=recency&proposals=0-4&payment_verified=1"
page.evaluate(f"window.location.href = '{url3}'")
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

print("\n=== bot automation api <5 proposals ===")
jobs3 = page.evaluate("""(() => {
    const links = document.querySelectorAll('a[href*="/jobs/~"]');
    const seen = new Set();
    const results = [];
    for (const link of links) {
        const href = link.href.split('?')[0];
        const title = link.textContent.trim();
        if (seen.has(href) || !title || title.length < 10) continue;
        seen.add(href);
        results.push({title, url: href});
    }
    return results;
})()""")
for j in jobs3:
    print(f"  {j['title'][:60]} -> {j['url']}")

pw.stop()

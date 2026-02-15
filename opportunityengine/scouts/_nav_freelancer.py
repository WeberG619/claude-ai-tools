"""Navigate to Freelancer.com job page for Opp #186."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

job_url = "https://www.freelancer.com/projects/data-collection/scrape-nsw-transport-contact-list"
print(f"Navigating to Freelancer job #186...")
page.evaluate(f"window.location.href = '{job_url}'")

time.sleep(3)
for i in range(20):
    try:
        title = page.title()
        url = page.url
        if "Just a moment" in title or "Checking" in title:
            print(f"  Cloudflare... ({i+1})")
            time.sleep(2)
        elif "freelancer" in url.lower():
            break
        else:
            time.sleep(2)
    except:
        time.sleep(2)

time.sleep(3)
print(f"\nTitle: {page.title()}")
print(f"URL: {page.url}")

# Check if logged in
login_check = page.evaluate("""(() => {
    const body = document.body.innerText;
    const url = window.location.href;
    if (url.includes('/login') || url.includes('signup')) return {loggedIn: false, reason: 'login page redirect'};

    // Look for user menu or avatar (sign of being logged in)
    const userMenu = document.querySelector('[class*="user-menu"], [class*="avatar"], [class*="profile-image"], [data-uitest-target*="user"]');
    const loginBtn = document.querySelector('a[href*="login"], button:has-text("Log In"), a:has-text("Log In")');

    return {
        loggedIn: !!userMenu && !loginBtn,
        hasUserMenu: !!userMenu,
        hasLoginBtn: !!loginBtn,
        url: url.substring(0, 80),
    };
})()""")
print(f"\nLogin check: {login_check}")

# Check for bid button
bid_check = page.evaluate("""(() => {
    const buttons = Array.from(document.querySelectorAll('button, a.btn, [role="button"]'))
        .filter(b => b.offsetParent !== null)
        .map(b => ({text: b.textContent.trim().substring(0, 50), href: b.href || '', tag: b.tagName}))
        .filter(b => b.text.length > 2);
    return buttons.slice(0, 20);
})()""")
print(f"\nVisible buttons:")
for b in bid_check:
    print(f"  [{b['tag']}] {b['text'][:50]}")

# Check for any bid form
form_check = page.evaluate("""(() => {
    const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), textarea, select'))
        .filter(i => i.offsetParent !== null)
        .map(i => ({tag: i.tagName, type: i.type || '', name: i.name || '', id: i.id || '', ph: (i.placeholder || '').substring(0, 30)}));
    return inputs;
})()""")
if form_check:
    print(f"\nVisible form fields:")
    for f in form_check:
        print(f"  [{f['tag']}] name={f['name']}, id={f['id']}, ph={f['ph']}")

pw.stop()

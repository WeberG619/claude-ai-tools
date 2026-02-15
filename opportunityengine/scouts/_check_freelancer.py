"""Check Freelancer.com job #186 page state."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

time.sleep(1)
print(f"Title: {page.title()}")
print(f"URL: {page.url}")

# Check if logged in and page state
page_state = page.evaluate("""(() => {
    const url = window.location.href;
    if (url.includes('/login') || url.includes('signup')) return {loggedIn: false, reason: 'login redirect'};

    // Check for user avatar/menu (logged in indicator)
    const allEls = document.querySelectorAll('*');
    let hasAvatar = false;
    let hasLoginLink = false;
    for (const el of allEls) {
        const cls = el.className || '';
        const text = el.textContent || '';
        if (typeof cls === 'string' && (cls.includes('avatar') || cls.includes('user-menu') || cls.includes('profile-image'))) hasAvatar = true;
        if (el.tagName === 'A' && el.href && el.href.includes('/login') && text.trim() === 'Log In') hasLoginLink = true;
    }

    return {loggedIn: hasAvatar, hasLoginLink: hasLoginLink, url: url.substring(0, 80)};
})()""")
print(f"\nLogin state: {page_state}")

# List all visible buttons
buttons = page.evaluate("""(() => {
    const btns = document.querySelectorAll('button, a[class*="btn"], [role="button"], input[type="submit"]');
    return Array.from(btns)
        .filter(b => b.offsetParent !== null)
        .map(b => ({
            tag: b.tagName,
            text: b.textContent.trim().substring(0, 60),
            href: (b.href || '').substring(0, 60),
            disabled: b.disabled || false,
            cls: (b.className || '').toString().substring(0, 60)
        }))
        .filter(b => b.text.length > 1)
        .slice(0, 25);
})()""")
print(f"\nVisible buttons ({len(buttons)}):")
for b in buttons:
    d = " [DISABLED]" if b['disabled'] else ""
    print(f"  [{b['tag']}] {b['text'][:50]}{d}")

# List visible form fields
fields = page.evaluate("""(() => {
    const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
    return Array.from(inputs)
        .filter(i => i.offsetParent !== null)
        .map(i => ({
            tag: i.tagName,
            type: i.type || '',
            name: i.name || '',
            id: i.id || '',
            ph: (i.placeholder || '').substring(0, 40),
            val: (i.value || '').substring(0, 20)
        }));
})()""")
if fields:
    print(f"\nVisible form fields ({len(fields)}):")
    for f in fields:
        print(f"  [{f['tag']}] type={f['type']}, name={f['name']}, id={f['id']}, ph={f['ph']}")

# Check for project/job details
job_info = page.evaluate("""(() => {
    const body = document.body.innerText;
    const lines = body.split('\\n').map(l => l.trim()).filter(l => l.length > 3 && l.length < 200);
    const keywords = ['bid', 'place', 'budget', 'proposal', 'submit', 'connect', 'award', 'deadline', 'skills'];
    return lines.filter(l => keywords.some(k => l.toLowerCase().includes(k))).slice(0, 20);
})()""")
print(f"\nJob-related text:")
for j in job_info:
    print(f"  {j[:120]}")

pw.stop()

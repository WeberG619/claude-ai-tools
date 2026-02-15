# -*- coding: utf-8 -*-
"""Check Reddit chat messages for actual responses."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

page = [p for p in context.pages if 'newtab-footer' not in p.url][0]

# Navigate to chat
page.evaluate("window.location.href = 'https://www.reddit.com/chat'")
time.sleep(6)
for i in range(10):
    try:
        if "Just a moment" not in page.title():
            break
        time.sleep(2)
    except:
        time.sleep(1)
time.sleep(3)

print(f"URL: {page.url[:60]}")
print(f"Title: {page.title()[:60]}")

# Get the chat sidebar - list of conversations
text = page.evaluate("document.body.innerText.substring(0, 5000)")
print(f"\nChat page content:\n{text[:4000]}")

# Try to get chat list items
chats = page.evaluate("""(() => {
    // Look for chat conversation items
    const items = document.querySelectorAll('[class*="chat"], [class*="conversation"], [class*="thread"], [class*="message"]');
    const results = [];
    for (const item of items) {
        const text = item.textContent.trim();
        if (text.length > 5 && text.length < 500) {
            results.push(text.substring(0, 200));
        }
    }
    return results.slice(0, 20);
})()""")
print(f"\nChat items found: {len(chats)}")
for c in chats:
    print(f"  {c[:150]}")

# Try clicking on each chat to see messages
# First get all links/buttons that might be chat conversations
chat_links = page.evaluate("""(() => {
    const links = document.querySelectorAll('a[href*="/chat/"]');
    return Array.from(links).map(a => ({text: a.textContent.trim().substring(0, 100), href: a.href})).filter(l => l.text.length > 0);
})()""")
print(f"\nChat links: {len(chat_links)}")
for cl in chat_links[:10]:
    print(f"  {cl['text'][:60]} -> {cl['href'][:60]}")

# Also try to find chat badge count
badge = page.evaluate("""(() => {
    const text = document.body.innerText;
    const m = text.match(/chat messages\\s*(\\d+)/i) || text.match(/(\\d+)\\s*unread/i);
    return m ? m[0] : null;
})()""")
print(f"\nChat badge: {badge}")

# Let's check the notification page again for the "4 chat messages" we saw
page.evaluate("window.location.href = 'https://old.reddit.com/message/inbox/'")
time.sleep(5)

# We saw "chat messages4" in the old reddit header - meaning 4 unread chat messages
unread = page.evaluate("""(() => {
    const text = document.body.innerText;
    const m = text.match(/chat messages(\\d+)/);
    return m ? m[1] : '0';
})()""")
print(f"\nUnread chat messages: {unread}")

pw.stop()

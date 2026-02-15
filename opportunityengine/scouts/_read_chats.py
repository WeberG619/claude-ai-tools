# -*- coding: utf-8 -*-
"""Read Reddit chat messages by interacting with the chat UI."""
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
time.sleep(8)

print(f"URL: {page.url[:60]}")

# Get full HTML structure to understand the chat layout
structure = page.evaluate("""(() => {
    const body = document.body;
    function getStructure(el, depth) {
        if (depth > 4) return '';
        const tag = el.tagName;
        const cls = el.className ? (' class="' + String(el.className).substring(0, 60) + '"') : '';
        const id = el.id ? (' id="' + el.id + '"') : '';
        const text = el.childNodes.length === 1 && el.childNodes[0].nodeType === 3 ? ' text="' + el.textContent.trim().substring(0, 50) + '"' : '';
        let result = '  '.repeat(depth) + '<' + tag + id + cls + text + '>\\n';
        for (const child of el.children) {
            result += getStructure(child, depth + 1);
        }
        return result;
    }
    return getStructure(body, 0).substring(0, 5000);
})()""")
print(f"DOM structure:\n{structure[:3000]}")

# Try to find any elements with aria labels related to chat
aria = page.evaluate("""(() => {
    const els = document.querySelectorAll('[aria-label]');
    return Array.from(els).map(e => ({
        tag: e.tagName,
        aria: e.getAttribute('aria-label'),
        text: e.textContent.trim().substring(0, 80)
    })).filter(e => e.text.length > 0).slice(0, 30);
})()""")
print(f"\nAria-labeled elements:")
for a in aria:
    print(f"  {a['tag']} aria='{a['aria'][:50]}' text='{a['text'][:60]}'")

# Try to find chat thread buttons/items using roles
roles = page.evaluate("""(() => {
    const els = document.querySelectorAll('[role="listitem"], [role="option"], [role="button"], [role="link"]');
    return Array.from(els).map(e => ({
        tag: e.tagName,
        role: e.getAttribute('role'),
        text: e.textContent.trim().substring(0, 100)
    })).filter(e => e.text.length > 2 && e.text.length < 200).slice(0, 30);
})()""")
print(f"\nRole elements:")
for r in roles:
    print(f"  {r['tag']} role='{r['role']}' text='{r['text'][:80]}'")

# Try iframes
iframes = page.evaluate("document.querySelectorAll('iframe').length")
print(f"\nIframes on page: {iframes}")

# Try shadow DOM
shadows = page.evaluate("""(() => {
    const all = document.querySelectorAll('*');
    let count = 0;
    for (const el of all) {
        if (el.shadowRoot) count++;
    }
    return count;
})()""")
print(f"Shadow DOM elements: {shadows}")

pw.stop()

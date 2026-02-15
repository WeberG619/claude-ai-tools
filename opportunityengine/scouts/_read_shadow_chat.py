# -*- coding: utf-8 -*-
"""Read Reddit chat by piercing shadow DOM."""
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
time.sleep(10)

print(f"URL: {page.url[:60]}")
print(f"Title: {page.title()[:60]}")

# Pierce shadow DOM to get chat content
shadow_content = page.evaluate("""(() => {
    function getAllText(root, depth) {
        if (depth > 8) return '';
        let text = '';
        const nodes = root.childNodes;
        for (const node of nodes) {
            if (node.nodeType === 3) {
                const t = node.textContent.trim();
                if (t) text += t + '\\n';
            } else if (node.nodeType === 1) {
                if (node.shadowRoot) {
                    text += getAllText(node.shadowRoot, depth + 1);
                }
                text += getAllText(node, depth + 1);
            }
        }
        return text;
    }
    return getAllText(document.body, 0).substring(0, 8000);
})()""")

print(f"\nShadow DOM content ({len(shadow_content)} chars):")
print(shadow_content[:6000])

pw.stop()

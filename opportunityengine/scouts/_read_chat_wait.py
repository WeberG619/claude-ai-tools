# -*- coding: utf-8 -*-
"""Read Reddit chat - wait for full load and pierce shadow DOM."""
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

# Wait for chat to fully load - poll until we see conversation items
for attempt in range(20):
    content = page.evaluate("""(() => {
        function getAllText(root, depth) {
            if (depth > 10) return '';
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
        return getAllText(document.body, 0);
    })()""")

    if 'Welcome to chat' not in content and len(content) > 800:
        print(f"Chat loaded after {attempt+1} attempts")
        break

    # Check if we see usernames
    if any(name in content for name in ['Pr0b0pass', 'dot90zoom', 'eddy14207', 'AdMental6886', 'Reasonable_Salary182']):
        print(f"Found usernames after {attempt+1} attempts")
        break

    time.sleep(2)
    print(f"  Waiting... ({attempt+1}/20) - content length: {len(content)}")

print(f"\nFinal content ({len(content)} chars):")
print(content[:6000])

# Also try to find chat elements using Playwright's built-in shadow DOM piercing
print("\n\n=== PLAYWRIGHT SHADOW PIERCE ===")
try:
    # Playwright can pierce shadow DOM with >> syntax
    items = page.locator('rs-app >> *').all_text_contents()
    print(f"rs-app contents: {len(items)} items")
    for item in items[:30]:
        if item.strip() and len(item.strip()) > 2:
            print(f"  {item.strip()[:100]}")
except Exception as e:
    print(f"rs-app pierce failed: {e}")

# Try to get all visible text via accessibility tree
print("\n\n=== ACCESSIBILITY SNAPSHOT ===")
try:
    snapshot = page.accessibility.snapshot()
    if snapshot:
        def print_tree(node, depth=0):
            name = node.get('name', '')
            role = node.get('role', '')
            if name and len(name) > 2:
                print(f"{'  '*depth}{role}: {name[:100]}")
            for child in node.get('children', []):
                if depth < 4:
                    print_tree(child, depth + 1)
        print_tree(snapshot)
except Exception as e:
    print(f"Accessibility failed: {e}")

pw.stop()

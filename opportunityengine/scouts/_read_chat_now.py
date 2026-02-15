# -*- coding: utf-8 -*-
"""Read Reddit chat messages - page should be loaded now."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = [p for p in context.pages if 'newtab-footer' not in p.url][0]

print(f"URL: {page.url[:80]}")
print(f"Title: {page.title()[:60]}")

# Method 1: Deep shadow DOM pierce
print("\n=== METHOD 1: Shadow DOM deep traverse ===")
content = page.evaluate("""(() => {
    function getAllText(root, depth) {
        if (depth > 12) return '';
        let text = '';
        for (const node of root.childNodes) {
            if (node.nodeType === 3) {
                const t = node.textContent.trim();
                if (t && t.length > 1 && !t.startsWith('.snoo') && !t.startsWith('SML.') && !t.startsWith('window.')) text += t + '\\n';
            } else if (node.nodeType === 1) {
                if (node.shadowRoot) text += getAllText(node.shadowRoot, depth + 1);
                text += getAllText(node, depth + 1);
            }
        }
        return text;
    }
    return getAllText(document.body, 0);
})()""")
print(f"Content ({len(content)} chars):\n{content[:5000]}")

# Method 2: Playwright shadow-piercing locators
print("\n=== METHOD 2: Playwright locator text ===")
try:
    all_text = page.locator('body').inner_text(timeout=5000)
    print(f"Body text ({len(all_text)} chars):\n{all_text[:3000]}")
except Exception as e:
    print(f"Failed: {e}")

# Method 3: Try to find specific chat elements
print("\n=== METHOD 3: Chat-specific elements ===")
try:
    # Try various selectors that might match chat messages
    for selector in [
        'rs-app',
        '[class*="message"]',
        '[class*="chat"]',
        '[data-testid]',
        'p',
        'span',
    ]:
        try:
            els = page.locator(selector)
            count = els.count()
            if count > 0 and count < 200:
                texts = []
                for i in range(min(count, 20)):
                    try:
                        t = els.nth(i).inner_text(timeout=1000)
                        if t.strip() and len(t.strip()) > 3 and len(t) < 500:
                            texts.append(t.strip())
                    except:
                        pass
                if texts:
                    print(f"\n  {selector} ({count} elements, {len(texts)} with text):")
                    for t in texts[:15]:
                        print(f"    {t[:120]}")
        except:
            pass
except Exception as e:
    print(f"Error: {e}")

# Method 4: Screenshot approach - take a screenshot for the user
print("\n=== METHOD 4: Page screenshot ===")
try:
    page.screenshot(path="D:/_CLAUDE-TOOLS/opportunityengine/scouts/_chat_screenshot.png", full_page=False)
    print("Screenshot saved to _chat_screenshot.png")
except Exception as e:
    print(f"Screenshot failed: {e}")

pw.stop()

"""Inspect Reddit DM page structure, fill Title, and Send."""

import time
import sys
from playwright.sync_api import sync_playwright


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9222")
    print("Connected")

    context = browser.contexts[0]

    # Find the existing Reddit DM tab
    page = None
    for p in context.pages:
        if "message/compose" in p.url:
            page = p
            print(f"Found DM tab: {p.url}")
            break

    if not page:
        print("No DM tab found")
        pw.stop()
        return

    # Skip clearing search bar - may not be visible

    # Dump all input/textarea elements with their attributes
    print("\n=== ALL INPUTS ===")
    elements = page.query_selector_all("input, textarea, [contenteditable]")
    for i, el in enumerate(elements):
        try:
            tag = el.evaluate("e => e.tagName")
            name = el.get_attribute("name") or ""
            placeholder = el.get_attribute("placeholder") or ""
            aria_label = el.get_attribute("aria-label") or ""
            el_type = el.get_attribute("type") or ""
            el_id = el.get_attribute("id") or ""
            ce = el.get_attribute("contenteditable") or ""
            role = el.get_attribute("role") or ""
            vis = el.is_visible()
            val = ""
            try:
                val = el.input_value()[:50]
            except:
                try:
                    val = el.inner_text()[:50]
                except:
                    pass
            print(
                f"  [{i}] <{tag}> name={name} id={el_id} type={el_type} "
                f"placeholder={placeholder} aria={aria_label} ce={ce} "
                f"role={role} visible={vis} val={val}"
            )
        except Exception as e:
            print(f"  [{i}] Error: {e}")

    # Also look for faceplate-text-input or other custom elements
    print("\n=== CUSTOM ELEMENTS (faceplate, shreddit) ===")
    custom = page.query_selector_all("[class*='title'], [class*='Title'], [data-testid*='title'], faceplate-text-input, shreddit-composer")
    for i, el in enumerate(custom):
        try:
            tag = el.evaluate("e => e.tagName")
            cls = el.get_attribute("class") or ""
            testid = el.get_attribute("data-testid") or ""
            name = el.get_attribute("name") or ""
            vis = el.is_visible()
            print(f"  [{i}] <{tag}> class={cls[:80]} testid={testid} name={name} vis={vis}")
        except:
            pass

    # Try getting the shadow DOM / inner structure around the Title label
    print("\n=== TITLE AREA INSPECTION ===")
    try:
        # Find the element that contains "Title" text
        title_area = page.evaluate("""() => {
            const all = document.querySelectorAll('*');
            const results = [];
            for (const el of all) {
                if (el.textContent && el.textContent.trim() === 'Title' && el.children.length === 0) {
                    const parent = el.parentElement;
                    const grandparent = parent ? parent.parentElement : null;
                    results.push({
                        tag: el.tagName,
                        class: el.className,
                        parentTag: parent ? parent.tagName : '',
                        parentClass: parent ? parent.className : '',
                        parentHTML: parent ? parent.innerHTML.substring(0, 300) : '',
                        gpTag: grandparent ? grandparent.tagName : '',
                        gpHTML: grandparent ? grandparent.innerHTML.substring(0, 500) : '',
                    });
                }
            }
            return results;
        }""")
        for item in title_area:
            print(f"  Title text in <{item['tag']}> class={item['class']}")
            print(f"  Parent: <{item['parentTag']}> class={item['parentClass']}")
            print(f"  Parent HTML: {item['parentHTML'][:200]}")
            print(f"  GP HTML: {item['gpHTML'][:300]}")
            print()
    except Exception as e:
        print(f"  Inspection error: {e}")

    pw.stop()


if __name__ == "__main__":
    main()

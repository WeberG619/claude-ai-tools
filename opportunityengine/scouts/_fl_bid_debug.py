"""Debug the Freelancer bid form - find all required fields and their state."""

import time
from playwright.sync_api import sync_playwright


def main():
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://localhost:9225")
    context = browser.contexts[0]

    fl = None
    for p in context.pages:
        if "freelancer.com" in p.url:
            fl = p
            break

    if not fl:
        print("No Freelancer tab found")
        pw.stop()
        return

    # Scroll to bottom to load everything
    fl.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)
    fl.screenshot(path=r"D:\_CLAUDE-TOOLS\opportunityengine\.screenshot_fl_bid_bottom.png")

    # Get ALL form elements and their state
    form_data = fl.evaluate("""() => {
        const results = [];

        // All inputs
        const inputs = document.querySelectorAll('input, textarea, select');
        for (const el of inputs) {
            const rect = el.getBoundingClientRect();
            results.push({
                tag: el.tagName,
                type: el.type || 'text',
                name: el.name || '',
                id: el.id || '',
                placeholder: el.placeholder || '',
                value: el.value || '',
                required: el.required,
                visible: rect.width > 0 && rect.height > 0,
                ariaLabel: el.getAttribute('aria-label') || '',
                classList: Array.from(el.classList).join(' '),
                disabled: el.disabled,
                checked: el.checked || false,
            });
        }

        // Check for validation errors
        const errors = document.querySelectorAll('[class*="error"], [class*="invalid"], .ng-invalid');
        const errorTexts = [];
        for (const e of errors) {
            if (e.textContent && e.textContent.trim().length < 200) {
                errorTexts.push({
                    text: e.textContent.trim(),
                    tag: e.tagName,
                    class: e.className.substring(0, 100),
                });
            }
        }

        // Checkboxes specifically
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        const cbData = [];
        for (const cb of checkboxes) {
            const label = cb.closest('label') ? cb.closest('label').textContent.trim() : '';
            cbData.push({
                checked: cb.checked,
                name: cb.name || cb.id,
                label: label.substring(0, 100),
                required: cb.required,
            });
        }

        return {inputs: results, errors: errorTexts, checkboxes: cbData};
    }""")

    print("=== FORM INPUTS ===")
    for inp in form_data.get("inputs", []):
        if inp["visible"]:
            print(f"  [{inp['tag']}] type={inp['type']} name='{inp['name']}' id='{inp['id']}' "
                  f"value='{inp['value'][:50]}' required={inp['required']} "
                  f"placeholder='{inp['placeholder'][:40]}'")

    print("\n=== VALIDATION ERRORS ===")
    for err in form_data.get("errors", []):
        print(f"  {err['tag']}: {err['text'][:150]}")
        print(f"    class: {err['class']}")

    print("\n=== CHECKBOXES ===")
    for cb in form_data.get("checkboxes", []):
        print(f"  [{('X' if cb['checked'] else ' ')}] name='{cb['name']}' required={cb['required']} "
              f"label='{cb['label'][:80]}'")

    # Also check NDA/agreement section
    nda = fl.evaluate("""() => {
        const body = document.body.innerHTML;
        const ndaIdx = body.toLowerCase().indexOf('nda');
        const agreeIdx = body.toLowerCase().indexOf('agree');
        const termsIdx = body.toLowerCase().indexOf('terms');
        return {
            hasNDA: ndaIdx > -1,
            hasAgree: agreeIdx > -1,
            hasTerms: termsIdx > -1,
        };
    }""")
    print(f"\n=== FORM FLAGS === NDA={nda['hasNDA']} Agree={nda['hasAgree']} Terms={nda['hasTerms']}")

    pw.stop()


if __name__ == "__main__":
    main()

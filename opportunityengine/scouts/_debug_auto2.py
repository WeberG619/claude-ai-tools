"""Debug full form state for Automation job proposal."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.pages[0]

# Get full page text focused on the form
text = page.evaluate("document.body.innerText")
# Find the form section
form_start = text.find("Proposal settings")
if form_start == -1:
    form_start = text.find("Submit a proposal")
form_end = text.find("Footer navigation")
if form_start >= 0 and form_end >= 0:
    form_text = text[form_start:form_end]
else:
    form_text = text[:5000]

print("=== FULL FORM TEXT ===")
print(form_text[:4000])

# Check all visible inputs with their values
print("\n=== ALL FORM INPUTS ===")
inputs = page.evaluate("""(() => {
    const all = document.querySelectorAll('input, textarea, select, [contenteditable="true"]');
    return Array.from(all)
        .filter(i => i.offsetParent !== null)
        .map(i => ({
            tag: i.tagName,
            type: i.type || '',
            name: i.name || '',
            id: i.id || '',
            value: (i.value || '').substring(0, 50),
            ph: (i.placeholder || '').substring(0, 40),
            required: i.required || false,
            validity: i.validity ? {valid: i.validity.valid, valueMissing: i.validity.valueMissing} : null,
        }));
})()""")

for inp in inputs:
    req = " [REQUIRED]" if inp['required'] else ""
    valid = ""
    if inp['validity']:
        valid = f" valid={inp['validity']['valid']}, missing={inp['validity']['valueMissing']}"
    print(f"  [{inp['tag']}] type={inp['type']}, name={inp['name']}, val='{inp['value']}', ph='{inp['ph']}'{req}{valid}")

# Check dropdowns state
dds = page.evaluate("""(() => {
    const dds = document.querySelectorAll('[role="combobox"][data-test="dropdown-toggle"]');
    return Array.from(dds).filter(d => d.offsetParent !== null).map(d => ({
        text: d.textContent.trim(),
        ariaExpanded: d.getAttribute('aria-expanded'),
    }));
})()""")
print(f"\nDropdowns:")
for d in dds:
    print(f"  '{d['text']}' (expanded={d['ariaExpanded']})")

pw.stop()

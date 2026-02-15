# -*- coding: utf-8 -*-
"""Resend corrected resume to ben@apliiq.com via Gmail."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

page = context.new_page()
time.sleep(1)

compose_url = "https://mail.google.com/mail/u/0/?view=cm&fs=1&to=ben@apliiq.com&su=Weber%20Gouin%20-%20Updated%20Resume%20(corrected)"
page.goto(compose_url, wait_until="domcontentloaded", timeout=30000)
time.sleep(10)

print(f"Title: {page.title()[:60]}")

# Wait for compose
for i in range(15):
    try:
        body = page.locator('div[contenteditable="true"]')
        if body.count() > 0:
            print("Compose loaded")
            break
        time.sleep(2)
    except:
        time.sleep(2)

# Fill body
body_text = """Hi Ben,

Quick follow-up - sending an updated version of my resume with a corrected GitHub link.

Here's the correct profile: github.com/WeberG619

Sorry about that, and thanks again for your time.

Best,
Weber Gouin"""

try:
    editable = page.locator('div[contenteditable="true"]').last
    editable.click(timeout=5000)
    time.sleep(0.5)
    page.keyboard.type(body_text, delay=5)
    print("Body typed")
except Exception as e:
    print(f"Body failed: {e}")

time.sleep(1)

# Attach PDF
pdf_path = "D:/_CLAUDE-TOOLS/Weber_Gouin_Resume_2026.pdf"
try:
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(pdf_path)
    print("PDF attached")
    time.sleep(5)
except Exception as e:
    print(f"Attach method 1 failed: {e}")
    try:
        with page.expect_file_chooser() as fc_info:
            page.locator('[aria-label*="Attach"], [data-tooltip*="Attach"]').first.click(timeout=5000)
        fc_info.value.set_files(pdf_path)
        print("PDF attached via file chooser")
        time.sleep(5)
    except Exception as e2:
        print(f"Attach method 2 failed: {e2}")

# Verify attachment
time.sleep(3)
has_attachment = page.evaluate("""(() => {
    const text = document.body.innerText;
    return text.includes('Weber_Gouin') || text.includes('Resume_2026') || text.includes('.pdf');
})()""")
print(f"Attachment visible: {has_attachment}")

# Send via Ctrl+Enter
time.sleep(1)
page.keyboard.press("Control+Enter")
time.sleep(8)
print("Sent via Ctrl+Enter")

print(f"Final URL: {page.url[:80]}")

pw.stop()

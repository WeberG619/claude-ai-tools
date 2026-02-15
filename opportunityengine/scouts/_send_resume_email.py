# -*- coding: utf-8 -*-
"""Send resume email with PDF attachment via Gmail in Chrome CDP."""
from playwright.sync_api import sync_playwright
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

# Use a new page for Gmail
page = context.new_page()
time.sleep(1)

# Navigate to Gmail compose
compose_url = "https://mail.google.com/mail/u/0/?view=cm&fs=1&to=ben@apliiq.com&su=Weber%20Gouin%20-%20Resume%20for%20Remote%20Personal%20Assistant%20Role"
page.goto(compose_url, wait_until="domcontentloaded", timeout=30000)
time.sleep(8)

print(f"URL: {page.url[:80]}")
print(f"Title: {page.title()[:60]}")

# Wait for compose window to load
for i in range(15):
    try:
        # Check if compose form is ready
        has_body = page.locator('[aria-label="Message Body"]').count()
        if has_body > 0:
            print("Compose form loaded")
            break
        time.sleep(2)
    except:
        time.sleep(2)

# Fill the email body
body_text = """Hi Ben,

I saw the Remote Personal Assistant (Sales / Biz Dev + Occasional Customer Service) position and I'm very interested.

I'm a developer and automation specialist with deep experience in Python, AI agent systems, browser automation, and full-stack development. I also have 30+ years of background in architecture and BIM coordination.

Please find my resume attached. Happy to chat anytime.

Best,
Weber Gouin"""

try:
    body_field = page.locator('[aria-label="Message Body"]').first
    body_field.click(timeout=5000)
    time.sleep(0.5)
    body_field.fill(body_text)
    print("Body filled")
except Exception as e:
    print(f"Body fill failed: {e}")
    # Try alternative
    try:
        page.locator('div[contenteditable="true"]').last.click()
        time.sleep(0.3)
        page.keyboard.type(body_text, delay=5)
        print("Body typed via keyboard")
    except Exception as e2:
        print(f"Body keyboard also failed: {e2}")

time.sleep(1)

# Attach PDF - find the file input for attachments
pdf_path = "D:/_CLAUDE-TOOLS/Weber_Gouin_Resume_Dev.pdf"

try:
    # Gmail has a hidden file input for attachments
    file_input = page.locator('input[type="file"][name="Filedata"]').first
    file_input.set_input_files(pdf_path)
    print(f"PDF attached: {pdf_path}")
    time.sleep(5)
except Exception as e:
    print(f"Direct file input failed: {e}")
    # Try finding any file input
    try:
        inputs = page.locator('input[type="file"]')
        count = inputs.count()
        print(f"Found {count} file inputs")
        if count > 0:
            inputs.nth(0).set_input_files(pdf_path)
            print("Attached via first file input")
            time.sleep(5)
        else:
            # Click the attachment button to trigger file dialog
            attach_btn = page.locator('[aria-label*="Attach"], [data-tooltip*="Attach"]').first
            print(f"Trying attach button...")
            # Use file chooser
            with page.expect_file_chooser() as fc_info:
                attach_btn.click(timeout=5000)
            file_chooser = fc_info.value
            file_chooser.set_files(pdf_path)
            print("Attached via file chooser")
            time.sleep(5)
    except Exception as e2:
        print(f"All attach methods failed: {e2}")

# Verify attachment appears
time.sleep(3)
has_attachment = page.evaluate("""(() => {
    const text = document.body.innerText;
    return text.includes('Weber_Gouin') || text.includes('.pdf') || text.includes('Resume');
})()""")
print(f"Attachment visible: {has_attachment}")

# Send the email
try:
    send_btn = page.locator('[aria-label*="Send"], [data-tooltip*="Send"]').first
    send_btn.click(timeout=5000)
    print("Send clicked!")
    time.sleep(5)

    # Check if sent
    sent_confirm = page.evaluate("document.body.innerText.includes('Message sent') || document.body.innerText.includes('Sent')")
    print(f"Send confirmed: {sent_confirm}")
except Exception as e:
    print(f"Send failed: {e}")
    # Try Ctrl+Enter
    try:
        page.keyboard.press("Control+Enter")
        time.sleep(5)
        print("Sent via Ctrl+Enter")
    except:
        print("Could not send - may need manual send")

print(f"\nFinal URL: {page.url[:80]}")

pw.stop()

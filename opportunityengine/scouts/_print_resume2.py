# -*- coding: utf-8 -*-
"""Convert resume HTML to PDF using a fresh Playwright page."""
from playwright.sync_api import sync_playwright
import time

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

# Create a new page for the resume
page = context.new_page()
time.sleep(1)

# Navigate to resume HTML
page.goto("file:///D:/_CLAUDE-TOOLS/Weber_Gouin_Resume_Dev.html", wait_until="networkidle", timeout=15000)
time.sleep(2)

print(f"URL: {page.url[:80]}")
print(f"Title: {page.title()[:60]}")

# Verify we're on the resume
text = page.evaluate("document.body.innerText.substring(0, 200)")
print(f"Content preview: {text[:150]}")

# Print to PDF
pdf_path = "D:/_CLAUDE-TOOLS/Weber_Gouin_Resume_Dev.pdf"
pdf_bytes = page.pdf(
    path=pdf_path,
    format="Letter",
    margin={"top": "0.5in", "bottom": "0.5in", "left": "0.6in", "right": "0.6in"},
    print_background=True,
)
print(f"\nPDF saved: {pdf_path} ({len(pdf_bytes)} bytes)")

page.close()
pw.stop()

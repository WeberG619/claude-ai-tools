# -*- coding: utf-8 -*-
"""Convert resume HTML to PDF using Chrome CDP, then open in Bluebeam."""
from playwright.sync_api import sync_playwright
import time
import subprocess

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]

page = [p for p in context.pages if 'newtab-footer' not in p.url][0]

# Navigate to the resume HTML
page.evaluate("window.location.href = 'file:///D:/_CLAUDE-TOOLS/Weber_Gouin_Resume_Dev.html'")
time.sleep(3)

print(f"URL: {page.url[:80]}")
print(f"Title: {page.title()[:60]}")

# Print to PDF
pdf_path = "D:/_CLAUDE-TOOLS/Weber_Gouin_Resume_Dev.pdf"
pdf_bytes = page.pdf(
    path=pdf_path,
    format="Letter",
    margin={"top": "0.6in", "bottom": "0.6in", "left": "0.7in", "right": "0.7in"},
    print_background=True,
)
print(f"PDF saved: {pdf_path} ({len(pdf_bytes)} bytes)")

pw.stop()

# Open in Bluebeam
print("Opening in Bluebeam...")
subprocess.Popen(
    ['cmd', '/c', 'start', '', pdf_path],
    shell=False
)
print("Done!")

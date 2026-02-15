# -*- coding: utf-8 -*-
"""Regenerate resume PDF - save to new filename to avoid lock."""
from playwright.sync_api import sync_playwright
import time
import subprocess

pw = sync_playwright().start()
browser = pw.chromium.connect_over_cdp("http://localhost:9222")
context = browser.contexts[0]
page = context.new_page()
time.sleep(1)

page.goto("file:///D:/_CLAUDE-TOOLS/Weber_Gouin_Resume_Dev.html", wait_until="networkidle", timeout=15000)
time.sleep(2)

pdf_path = "D:/_CLAUDE-TOOLS/Weber_Gouin_Resume_2026.pdf"
pdf_bytes = page.pdf(
    path=pdf_path,
    format="Letter",
    margin={"top": "0.5in", "bottom": "0.5in", "left": "0.6in", "right": "0.6in"},
    print_background=True,
)
print(f"PDF saved: {pdf_path} ({len(pdf_bytes)} bytes)")

page.close()
pw.stop()

# Open in Bluebeam
subprocess.Popen([
    r"C:\Program Files\Bluebeam Software\Bluebeam Revu\2017\Revu\Revu.exe",
    pdf_path
])
print("Opened in Bluebeam")

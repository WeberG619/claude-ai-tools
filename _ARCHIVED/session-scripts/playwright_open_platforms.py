"""
Open gig platform signup pages in existing Chrome via CDP.
Connects to Chrome's remote debugging port and opens tabs.
"""
import asyncio
from playwright.async_api import async_playwright

PLATFORMS = [
    ("DataAnnotation.tech", "https://www.dataannotation.tech/"),
    ("Outlier AI", "https://outlier.ai/"),
    ("iWriter", "https://www.iwriter.com/"),
    ("Textbroker", "https://www.textbroker.com/"),
    ("Freelancer.com", "https://www.freelancer.com/"),
    ("Fiverr", "https://www.fiverr.com/"),
    ("PeoplePerHour", "https://www.peopleperhour.com/"),
    ("Contra", "https://contra.com/"),
    ("CAD Crowd", "https://www.cadcrowd.com/"),
    ("Guru.com", "https://www.guru.com/"),
]

async def main():
    async with async_playwright() as p:
        # Connect to existing Chrome via CDP
        print("Connecting to Chrome on port 9222...")
        browser = await p.chromium.connect_over_cdp("http://172.24.224.1:9222")

        # Get existing contexts
        contexts = browser.contexts
        if not contexts:
            print("No browser contexts found!")
            return

        context = contexts[0]
        print(f"Connected! Found {len(contexts)} context(s), {len(context.pages)} existing page(s)")

        # Open each platform in a new tab
        opened = []
        for name, url in PLATFORMS:
            try:
                page = await context.new_page()
                print(f"Opening {name}... ", end="", flush=True)
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                title = await page.title()
                print(f"OK - {title}")
                opened.append((name, url, title))
            except Exception as e:
                print(f"WARN: {name} - {e}")
                opened.append((name, url, f"Error: {e}"))

        print(f"\n--- Opened {len(opened)} tabs ---")
        for name, url, title in opened:
            print(f"  {name}: {title}")

        # Don't close - leave tabs open for user
        print("\nAll tabs open. Browser stays connected.")

if __name__ == "__main__":
    asyncio.run(main())

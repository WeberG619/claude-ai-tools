#!/usr/bin/env python3
"""
Browser Screenshot Capture Service for Live Dashboard.

Monitors the agent status file for browser_navigate activities
and captures screenshots using Playwright.

Usage:
    python browser_capture.py

The service runs in the background and captures screenshots whenever
an agent navigates to a URL. Screenshots are saved to /tmp/browser_screenshot.png
which the dashboard server serves to the browser view.
"""

import asyncio
import json
import time
from pathlib import Path
from playwright.async_api import async_playwright

STATUS_FILE = Path("/tmp/agent_speech_status.json")
SCREENSHOT_FILE = Path("/tmp/browser_screenshot.png")

class BrowserCaptureService:
    """Captures browser screenshots for dashboard display."""

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.last_url = None
        self.last_activity_time = 0

    async def start(self):
        """Initialize Playwright browser."""
        print("Starting browser capture service...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.page = await self.browser.new_page(
            viewport={'width': 1280, 'height': 800}
        )
        print("Browser ready for captures")

    async def stop(self):
        """Clean up browser resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("Browser capture service stopped")

    async def capture_url(self, url: str, title: str = None):
        """Navigate to URL and capture screenshot."""
        if not self.page:
            print("Browser not initialized")
            return False

        try:
            print(f"Capturing: {url}")

            # Navigate with timeout
            await self.page.goto(url, timeout=15000, wait_until='domcontentloaded')

            # Wait a bit for content to render
            await asyncio.sleep(1)

            # Capture screenshot
            await self.page.screenshot(path=str(SCREENSHOT_FILE))

            self.last_url = url
            print(f"Screenshot saved: {SCREENSHOT_FILE}")
            return True

        except Exception as e:
            print(f"Capture failed: {e}")
            return False

    async def monitor_loop(self):
        """Monitor status file for browser navigation activities."""
        print("Monitoring for browser activities...")

        while True:
            try:
                if STATUS_FILE.exists():
                    with open(STATUS_FILE) as f:
                        status = json.load(f)

                    activity = status.get('activity', {})
                    activity_time = status.get('activity_timestamp', 0)

                    # Check if this is a new browser navigation
                    if (activity.get('type') == 'browser_navigate' and
                        activity_time > self.last_activity_time):

                        url = activity.get('url')
                        title = activity.get('title')

                        if url and url != self.last_url:
                            self.last_activity_time = activity_time
                            await self.capture_url(url, title)

            except Exception as e:
                print(f"Monitor error: {e}")

            await asyncio.sleep(0.5)  # Check every 500ms


async def main():
    """Run the browser capture service."""
    service = BrowserCaptureService()

    try:
        await service.start()
        await service.monitor_loop()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await service.stop()


if __name__ == "__main__":
    print("=" * 50)
    print("  Browser Capture Service for Live Dashboard")
    print("=" * 50)
    asyncio.run(main())

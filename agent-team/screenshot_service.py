#!/usr/bin/env python3
"""
Fast Screenshot Service - Captures websites for dashboard display.
Uses a pre-launched browser for instant captures.
"""

import asyncio
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

STATUS_FILE = Path("/tmp/agent_speech_status.json")
SCREENSHOT_FILE = Path("/tmp/browser_screenshot.png")

class ScreenshotService:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.ready = False
        self.last_url = None
        self.last_capture_time = 0

    async def initialize(self):
        """Pre-launch browser for fast captures."""
        print("Initializing browser...", flush=True)
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
        )
        self.page = await self.browser.new_page(viewport={'width': 1200, 'height': 750})
        self.ready = True
        print("Browser ready!", flush=True)

    async def capture(self, url: str) -> bool:
        """Capture screenshot of URL."""
        if not self.ready:
            print("Browser not ready", flush=True)
            return False

        try:
            print(f"Capturing: {url}", flush=True)
            await self.page.goto(url, timeout=10000, wait_until='domcontentloaded')
            await asyncio.sleep(0.5)  # Brief wait for render
            await self.page.screenshot(path=str(SCREENSHOT_FILE))
            self.last_url = url
            print(f"Screenshot saved!", flush=True)
            return True
        except Exception as e:
            print(f"Capture error: {e}", flush=True)
            return False

    async def monitor(self):
        """Monitor for browser navigation activities."""
        print("Monitoring for activities...", flush=True)
        last_activity_time = 0

        while True:
            try:
                if STATUS_FILE.exists():
                    with open(STATUS_FILE) as f:
                        status = json.load(f)

                    activity = status.get('activity', {})
                    activity_time = status.get('activity_timestamp', 0)

                    if (activity.get('type') == 'browser_navigate' and
                        activity_time > last_activity_time):

                        url = activity.get('url')
                        if url:
                            last_activity_time = activity_time
                            await self.capture(url)

            except Exception as e:
                print(f"Monitor error: {e}", flush=True)

            await asyncio.sleep(0.3)

    async def cleanup(self):
        """Clean up resources."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

async def main():
    service = ScreenshotService()
    try:
        await service.initialize()
        await service.monitor()
    except KeyboardInterrupt:
        print("\nShutting down...", flush=True)
    finally:
        await service.cleanup()

if __name__ == "__main__":
    print("=" * 40, flush=True)
    print("Screenshot Service for Live Dashboard", flush=True)
    print("=" * 40, flush=True)
    asyncio.run(main())

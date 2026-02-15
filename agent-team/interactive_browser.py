#!/usr/bin/env python3
"""
Interactive Browser Controller - Agents can control a real browser
==================================================================
Provides browser automation capabilities for autonomous agents:
- Navigate to URLs
- Click elements
- Type text
- Take screenshots
- Extract page content
- Fill forms
- Log into websites

The browser runs visibly so viewers can see what's happening.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

# Status file for dashboard integration
STATUS_FILE = Path("/mnt/d/_CLAUDE-TOOLS/agent-team/agent_status.json")
SCREENSHOT_DIR = Path("/tmp/agent_browser_screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


@dataclass
class BrowserAction:
    """Represents a browser action for logging."""
    action_type: str
    target: str = ""
    value: str = ""
    success: bool = True
    screenshot: str = ""


class InteractiveBrowser:
    """
    Interactive browser that agents can control.
    Runs in visible mode so viewers can see actions.
    """

    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.action_history: List[BrowserAction] = []
        self._initialized = False

    async def start(self, headless: bool = False):
        """
        Start the browser.

        Args:
            headless: If False (default), browser is visible for OBS capture
        """
        if self._initialized:
            return

        self.playwright = await async_playwright().start()

        # Launch visible browser for OBS capture
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                '--window-size=1280,800',
                '--window-position=100,100',
                '--disable-blink-features=AutomationControlled',
            ]
        )

        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        self.page = await self.context.new_page()
        self._initialized = True

        # Notify dashboard
        self._update_status("browser_started", "Browser ready")

    async def stop(self):
        """Stop the browser."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self._initialized = False

    def _update_status(self, action_type: str, description: str):
        """Update dashboard status file."""
        try:
            status = {
                "activity": {
                    "type": "browser_action",
                    "action": action_type,
                    "description": description,
                    "url": self.page.url if self.page else ""
                },
                "activity_timestamp": time.time()
            }

            # Merge with existing status
            if STATUS_FILE.exists():
                existing = json.loads(STATUS_FILE.read_text())
                existing.update(status)
                status = existing

            STATUS_FILE.write_text(json.dumps(status))
        except Exception as e:
            print(f"Status update error: {e}")

    async def _log_action(self, action: BrowserAction):
        """Log action and take screenshot."""
        self.action_history.append(action)

        # Take screenshot
        if self.page:
            screenshot_path = SCREENSHOT_DIR / f"action_{len(self.action_history)}.png"
            await self.page.screenshot(path=str(screenshot_path))
            action.screenshot = str(screenshot_path)

    # =========================================================================
    # Navigation
    # =========================================================================

    async def goto(self, url: str, wait_for: str = "domcontentloaded") -> bool:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
            wait_for: Wait condition ('domcontentloaded', 'load', 'networkidle')

        Returns:
            True if successful
        """
        if not self._initialized:
            await self.start()

        try:
            self._update_status("navigating", f"Going to {url}")
            await self.page.goto(url, wait_until=wait_for, timeout=30000)

            action = BrowserAction("navigate", url, success=True)
            await self._log_action(action)

            self._update_status("navigated", f"At {url}")
            return True

        except Exception as e:
            print(f"Navigation error: {e}")
            return False

    async def go_back(self) -> bool:
        """Go back in browser history."""
        try:
            await self.page.go_back()
            self._update_status("navigated", "Went back")
            return True
        except:
            return False

    async def go_forward(self) -> bool:
        """Go forward in browser history."""
        try:
            await self.page.go_forward()
            self._update_status("navigated", "Went forward")
            return True
        except:
            return False

    async def refresh(self) -> bool:
        """Refresh the current page."""
        try:
            await self.page.reload()
            self._update_status("refreshed", "Page refreshed")
            return True
        except:
            return False

    # =========================================================================
    # Interaction
    # =========================================================================

    async def click(self, selector: str, timeout: int = 5000) -> bool:
        """
        Click an element.

        Args:
            selector: CSS selector or text to find element
            timeout: Max time to wait for element

        Returns:
            True if clicked successfully
        """
        try:
            self._update_status("clicking", f"Clicking {selector}")

            # Try CSS selector first, then text
            try:
                await self.page.click(selector, timeout=timeout)
            except:
                # Try by text content
                await self.page.click(f"text={selector}", timeout=timeout)

            action = BrowserAction("click", selector, success=True)
            await self._log_action(action)

            self._update_status("clicked", f"Clicked {selector}")
            return True

        except Exception as e:
            print(f"Click error: {e}")
            return False

    async def type_text(self, selector: str, text: str, delay: int = 50) -> bool:
        """
        Type text into an input field.

        Args:
            selector: CSS selector for the input
            text: Text to type
            delay: Delay between keystrokes (ms) for natural typing

        Returns:
            True if successful
        """
        try:
            self._update_status("typing", f"Typing into {selector}")

            await self.page.fill(selector, "")  # Clear first
            await self.page.type(selector, text, delay=delay)

            action = BrowserAction("type", selector, text[:50], success=True)
            await self._log_action(action)

            self._update_status("typed", f"Entered text into {selector}")
            return True

        except Exception as e:
            print(f"Type error: {e}")
            return False

    async def press_key(self, key: str) -> bool:
        """
        Press a keyboard key.

        Args:
            key: Key to press (e.g., 'Enter', 'Tab', 'Escape')
        """
        try:
            await self.page.keyboard.press(key)
            self._update_status("key_pressed", f"Pressed {key}")
            return True
        except:
            return False

    async def scroll(self, direction: str = "down", amount: int = 500) -> bool:
        """
        Scroll the page.

        Args:
            direction: 'up' or 'down'
            amount: Pixels to scroll
        """
        try:
            delta = amount if direction == "down" else -amount
            await self.page.mouse.wheel(0, delta)
            self._update_status("scrolled", f"Scrolled {direction}")
            return True
        except:
            return False

    # =========================================================================
    # Forms
    # =========================================================================

    async def fill_form(self, fields: Dict[str, str]) -> bool:
        """
        Fill multiple form fields.

        Args:
            fields: Dictionary of {selector: value}

        Returns:
            True if all fields filled successfully
        """
        success = True
        for selector, value in fields.items():
            if not await self.type_text(selector, value):
                success = False

        return success

    async def submit_form(self, form_selector: str = "form") -> bool:
        """Submit a form."""
        try:
            await self.page.evaluate(f'document.querySelector("{form_selector}").submit()')
            self._update_status("submitted", "Form submitted")
            return True
        except:
            # Try pressing Enter as fallback
            return await self.press_key("Enter")

    async def select_option(self, selector: str, value: str) -> bool:
        """Select an option from a dropdown."""
        try:
            await self.page.select_option(selector, value)
            self._update_status("selected", f"Selected {value}")
            return True
        except:
            return False

    # =========================================================================
    # Content Extraction
    # =========================================================================

    async def get_text(self, selector: str = "body") -> str:
        """Get text content of an element."""
        try:
            return await self.page.text_content(selector) or ""
        except:
            return ""

    async def get_html(self, selector: str = "body") -> str:
        """Get HTML content of an element."""
        try:
            return await self.page.inner_html(selector)
        except:
            return ""

    async def get_page_content(self) -> Dict[str, Any]:
        """
        Get structured page content for AI analysis.

        Returns:
            Dictionary with title, url, main text, links, etc.
        """
        try:
            content = {
                "url": self.page.url,
                "title": await self.page.title(),
                "text": await self.get_text("body"),
                "links": await self.page.evaluate('''
                    () => Array.from(document.querySelectorAll('a'))
                        .map(a => ({text: a.innerText.trim(), href: a.href}))
                        .filter(a => a.text && a.href)
                        .slice(0, 50)
                '''),
                "inputs": await self.page.evaluate('''
                    () => Array.from(document.querySelectorAll('input, textarea, select'))
                        .map(el => ({
                            type: el.type || el.tagName.toLowerCase(),
                            name: el.name,
                            id: el.id,
                            placeholder: el.placeholder
                        }))
                '''),
                "buttons": await self.page.evaluate('''
                    () => Array.from(document.querySelectorAll('button, input[type="submit"]'))
                        .map(b => b.innerText.trim() || b.value)
                        .filter(Boolean)
                ''')
            }
            return content
        except Exception as e:
            return {"error": str(e)}

    async def screenshot(self, path: str = None) -> str:
        """
        Take a screenshot.

        Args:
            path: Optional path to save screenshot

        Returns:
            Path to screenshot file
        """
        if not path:
            path = str(SCREENSHOT_DIR / f"screenshot_{int(time.time())}.png")

        await self.page.screenshot(path=path)
        return path

    # =========================================================================
    # Waiting
    # =========================================================================

    async def wait_for_selector(self, selector: str, timeout: int = 10000) -> bool:
        """Wait for an element to appear."""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            return True
        except:
            return False

    async def wait_for_navigation(self, timeout: int = 30000) -> bool:
        """Wait for navigation to complete."""
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
            return True
        except:
            return False

    async def wait(self, seconds: float):
        """Wait for a specified time."""
        await asyncio.sleep(seconds)

    # =========================================================================
    # High-Level Actions
    # =========================================================================

    async def search_google(self, query: str) -> bool:
        """
        Perform a Google search.

        Args:
            query: Search query

        Returns:
            True if search was successful
        """
        await self.goto("https://www.google.com")
        await self.type_text('textarea[name="q"]', query)
        await self.press_key("Enter")
        await self.wait_for_navigation()
        return True

    async def search_github(self, query: str) -> bool:
        """
        Search GitHub repositories.

        Args:
            query: Search query
        """
        url = f"https://github.com/search?q={query.replace(' ', '+')}&type=repositories"
        return await self.goto(url)

    async def login(self, url: str, username_selector: str, password_selector: str,
                    username: str, password: str, submit_selector: str = None) -> bool:
        """
        Log into a website.

        Args:
            url: Login page URL
            username_selector: Selector for username field
            password_selector: Selector for password field
            username: Username to enter
            password: Password to enter
            submit_selector: Optional submit button selector

        Returns:
            True if login form was submitted
        """
        await self.goto(url)
        await self.type_text(username_selector, username)
        await self.type_text(password_selector, password)

        if submit_selector:
            await self.click(submit_selector)
        else:
            await self.press_key("Enter")

        await self.wait_for_navigation()
        return True


class BrowserAgent:
    """
    Wrapper that provides browser control to autonomous agents.
    Integrates with the visual session for dashboard display.
    """

    def __init__(self):
        self.browser = InteractiveBrowser()
        self._started = False

    async def ensure_started(self):
        """Ensure browser is started."""
        if not self._started:
            await self.browser.start(headless=False)
            self._started = True

    async def research(self, topic: str) -> Dict[str, Any]:
        """
        Research a topic by searching and extracting content.

        Args:
            topic: What to research

        Returns:
            Dictionary with search results and content
        """
        await self.ensure_started()

        # Search GitHub
        await self.browser.search_github(topic)
        await self.browser.wait(2)

        # Get page content
        content = await self.browser.get_page_content()

        return {
            "query": topic,
            "url": content.get("url"),
            "title": content.get("title"),
            "results": content.get("links", [])[:10]
        }

    async def open_and_analyze(self, url: str) -> Dict[str, Any]:
        """
        Open a URL and analyze its content.

        Args:
            url: URL to open

        Returns:
            Page analysis
        """
        await self.ensure_started()
        await self.browser.goto(url)
        await self.browser.wait(1)

        return await self.browser.get_page_content()

    async def close(self):
        """Close the browser."""
        await self.browser.stop()
        self._started = False


async def demo_interactive_browser():
    """Demo the interactive browser capabilities."""
    print("\n" + "="*60)
    print("  INTERACTIVE BROWSER DEMO")
    print("="*60 + "\n")

    browser = InteractiveBrowser()

    try:
        # Start visible browser
        print("Starting browser...")
        await browser.start(headless=False)

        # Navigate to GitHub
        print("Navigating to GitHub...")
        await browser.goto("https://github.com")
        await browser.wait(2)

        # Search for something
        print("Searching for 'mcp server python'...")
        await browser.search_github("mcp server python")
        await browser.wait(3)

        # Get page content
        print("\nExtracting page content...")
        content = await browser.get_page_content()
        print(f"Title: {content['title']}")
        print(f"Found {len(content.get('links', []))} links")

        # Take screenshot
        screenshot = await browser.screenshot()
        print(f"Screenshot saved: {screenshot}")

        # Scroll down
        print("\nScrolling down...")
        await browser.scroll("down", 500)
        await browser.wait(2)

        print("\n" + "="*60)
        print("  DEMO COMPLETE")
        print("="*60)

    finally:
        await browser.stop()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        asyncio.run(demo_interactive_browser())
    else:
        print("Interactive Browser Controller")
        print("-" * 40)
        print("Usage:")
        print("  python interactive_browser.py demo   # Run demo")
        print()
        print("Or import and use:")
        print("  from interactive_browser import BrowserAgent")
        print("  agent = BrowserAgent()")
        print("  await agent.research('topic')")

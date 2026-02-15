"""
Stealth Browser - Undetected Chrome Automation
Bypasses common bot detection mechanisms
"""

import asyncio
import json
import os
import random
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Will use undetected-chromedriver for stealth
try:
    import undetected_chromedriver as uc
    HAS_UNDETECTED = True
except ImportError:
    HAS_UNDETECTED = False

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .human_behavior import HumanBehavior

# Paths
BROWSER_DIR = Path(__file__).parent
SESSIONS_DIR = BROWSER_DIR.parent / "sessions"
USER_DATA_DIR = SESSIONS_DIR / "chrome_profile"


class StealthBrowser:
    """
    Stealth browser that avoids bot detection.

    Features:
    - Undetected Chrome driver
    - Human-like mouse movements
    - Random delays between actions
    - Session persistence
    - Cookie management
    """

    def __init__(self, headless: bool = False, proxy: str = None):
        """
        Initialize stealth browser.

        Args:
            headless: Run without visible window (less stealthy)
            proxy: Optional proxy server (format: "host:port")
        """
        self.headless = headless
        self.proxy = proxy
        self.driver = None
        self.human = HumanBehavior()
        self._action_log = []

    def _log_action(self, action: str, details: dict = None):
        """Log an action for audit trail"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details or {}
        }
        self._action_log.append(entry)
        return entry

    def start(self) -> dict:
        """Start the browser"""
        self._log_action("browser_start", {"headless": self.headless})

        # Ensure user data directory exists
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

        if HAS_UNDETECTED:
            # Use undetected-chromedriver (best for avoiding detection)
            options = uc.ChromeOptions()

            if self.headless:
                options.add_argument("--headless=new")

            # Human-like settings
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--start-maximized")
            options.add_argument("--disable-blink-features=AutomationControlled")

            # Use persistent profile for session continuity
            options.add_argument(f"--user-data-dir={USER_DATA_DIR}")

            if self.proxy:
                options.add_argument(f"--proxy-server={self.proxy}")

            try:
                self.driver = uc.Chrome(options=options, version_main=None)
                return {"status": "success", "method": "undetected_chromedriver"}
            except Exception as e:
                # Fall back to regular selenium
                pass

        # Fallback: Regular Selenium with stealth settings
        options = Options()

        if self.headless:
            options.add_argument("--headless=new")

        # Anti-detection settings
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument(f"--user-data-dir={USER_DATA_DIR}")

        if self.proxy:
            options.add_argument(f"--proxy-server={self.proxy}")

        self.driver = webdriver.Chrome(options=options)

        # Execute stealth scripts
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = {runtime: {}};
            """
        })

        return {"status": "success", "method": "selenium_stealth"}

    def stop(self) -> dict:
        """Stop the browser and save session"""
        self._log_action("browser_stop")
        if self.driver:
            # Cookies are auto-saved with persistent profile
            self.driver.quit()
            self.driver = None
        return {"status": "stopped"}

    def navigate(self, url: str, wait_for_load: bool = True) -> dict:
        """
        Navigate to URL with human-like behavior.

        Args:
            url: URL to navigate to
            wait_for_load: Wait for page to fully load
        """
        if not self.driver:
            return {"status": "error", "message": "Browser not started"}

        self._log_action("navigate", {"url": url})

        # Random delay before navigation (humans don't instantly click)
        self.human.random_delay(0.3, 0.8)

        self.driver.get(url)

        if wait_for_load:
            try:
                WebDriverWait(self.driver, 30).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except TimeoutException:
                return {"status": "timeout", "url": url}

        # Small delay after load
        self.human.random_delay(0.5, 1.5)

        return {
            "status": "success",
            "url": self.driver.current_url,
            "title": self.driver.title
        }

    def click(self, selector: str, by: str = "css", human_like: bool = True) -> dict:
        """
        Click an element with human-like behavior.

        Args:
            selector: Element selector
            by: Selector type (css, xpath, id, name, class)
            human_like: Use human-like mouse movement
        """
        if not self.driver:
            return {"status": "error", "message": "Browser not started"}

        by_map = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME
        }

        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((by_map.get(by, By.CSS_SELECTOR), selector))
            )

            self._log_action("click", {"selector": selector, "by": by})

            if human_like:
                # Move to element with human-like movement
                self.human.human_move_to_element(self.driver, element)
                self.human.random_delay(0.1, 0.3)

            element.click()

            self.human.random_delay(0.3, 0.7)

            return {"status": "success", "selector": selector}

        except TimeoutException:
            return {"status": "not_found", "selector": selector}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def type_text(self, selector: str, text: str, by: str = "css",
                  human_like: bool = True, clear_first: bool = True) -> dict:
        """
        Type text into an element with human-like behavior.

        Args:
            selector: Element selector
            text: Text to type
            by: Selector type
            human_like: Type with random delays between characters
            clear_first: Clear existing text before typing
        """
        if not self.driver:
            return {"status": "error", "message": "Browser not started"}

        by_map = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME
        }

        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((by_map.get(by, By.CSS_SELECTOR), selector))
            )

            # Click the element first
            self.human.human_move_to_element(self.driver, element)
            element.click()
            self.human.random_delay(0.1, 0.2)

            if clear_first:
                element.clear()
                self.human.random_delay(0.1, 0.2)

            self._log_action("type", {"selector": selector, "text_length": len(text)})

            if human_like:
                # Type character by character with random delays
                self.human.human_type(element, text)
            else:
                element.send_keys(text)

            self.human.random_delay(0.2, 0.5)

            return {"status": "success", "selector": selector}

        except TimeoutException:
            return {"status": "not_found", "selector": selector}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def screenshot(self, filepath: str = None) -> dict:
        """Take a screenshot"""
        if not self.driver:
            return {"status": "error", "message": "Browser not started"}

        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(SESSIONS_DIR / f"screenshot_{timestamp}.png")

        self._log_action("screenshot", {"filepath": filepath})
        self.driver.save_screenshot(filepath)

        return {"status": "success", "filepath": filepath}

    def get_page_source(self) -> dict:
        """Get current page HTML"""
        if not self.driver:
            return {"status": "error", "message": "Browser not started"}

        return {
            "status": "success",
            "html": self.driver.page_source,
            "url": self.driver.current_url
        }

    def get_cookies(self) -> dict:
        """Get all cookies for current domain"""
        if not self.driver:
            return {"status": "error", "message": "Browser not started"}

        cookies = self.driver.get_cookies()
        return {
            "status": "success",
            "cookies": cookies,
            "count": len(cookies)
        }

    def set_cookies(self, cookies: List[dict]) -> dict:
        """Set cookies (for session restoration)"""
        if not self.driver:
            return {"status": "error", "message": "Browser not started"}

        for cookie in cookies:
            try:
                self.driver.add_cookie(cookie)
            except Exception:
                pass  # Some cookies may fail due to domain restrictions

        return {"status": "success", "set_count": len(cookies)}

    def find_element(self, selector: str, by: str = "css") -> dict:
        """Find an element and return its details"""
        if not self.driver:
            return {"status": "error", "message": "Browser not started"}

        by_map = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME
        }

        try:
            element = self.driver.find_element(by_map.get(by, By.CSS_SELECTOR), selector)
            return {
                "status": "found",
                "tag": element.tag_name,
                "text": element.text[:200] if element.text else "",
                "visible": element.is_displayed(),
                "enabled": element.is_enabled()
            }
        except NoSuchElementException:
            return {"status": "not_found", "selector": selector}

    def wait_for_element(self, selector: str, by: str = "css",
                        timeout: int = 30, visible: bool = True) -> dict:
        """Wait for an element to appear"""
        if not self.driver:
            return {"status": "error", "message": "Browser not started"}

        by_map = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "name": By.NAME,
            "class": By.CLASS_NAME
        }

        try:
            if visible:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((by_map.get(by, By.CSS_SELECTOR), selector))
                )
            else:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by_map.get(by, By.CSS_SELECTOR), selector))
                )

            return {
                "status": "found",
                "selector": selector,
                "tag": element.tag_name
            }
        except TimeoutException:
            return {"status": "timeout", "selector": selector}

    def execute_script(self, script: str, *args) -> dict:
        """Execute JavaScript in the browser"""
        if not self.driver:
            return {"status": "error", "message": "Browser not started"}

        try:
            result = self.driver.execute_script(script, *args)
            self._log_action("execute_script", {"script_length": len(script)})
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def scroll(self, direction: str = "down", amount: int = 500) -> dict:
        """Scroll the page"""
        if not self.driver:
            return {"status": "error", "message": "Browser not started"}

        if direction == "down":
            self.driver.execute_script(f"window.scrollBy(0, {amount});")
        elif direction == "up":
            self.driver.execute_script(f"window.scrollBy(0, -{amount});")
        elif direction == "top":
            self.driver.execute_script("window.scrollTo(0, 0);")
        elif direction == "bottom":
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        self.human.random_delay(0.3, 0.6)
        return {"status": "success", "direction": direction, "amount": amount}

    def get_action_log(self) -> List[dict]:
        """Get the action log for this session"""
        return self._action_log.copy()

    def press_key(self, key: str) -> dict:
        """Press a keyboard key"""
        if not self.driver:
            return {"status": "error", "message": "Browser not started"}

        key_map = {
            "enter": Keys.ENTER,
            "tab": Keys.TAB,
            "escape": Keys.ESCAPE,
            "backspace": Keys.BACKSPACE,
            "delete": Keys.DELETE,
            "space": Keys.SPACE,
            "up": Keys.UP,
            "down": Keys.DOWN,
            "left": Keys.LEFT,
            "right": Keys.RIGHT
        }

        actual_key = key_map.get(key.lower(), key)

        actions = ActionChains(self.driver)
        actions.send_keys(actual_key)
        actions.perform()

        self._log_action("press_key", {"key": key})
        return {"status": "success", "key": key}


# Singleton for easy access
_browser_instance = None

def get_browser(headless: bool = False, proxy: str = None) -> StealthBrowser:
    """Get or create browser instance"""
    global _browser_instance
    if _browser_instance is None:
        _browser_instance = StealthBrowser(headless=headless, proxy=proxy)
    return _browser_instance


if __name__ == "__main__":
    # Test the browser
    browser = StealthBrowser()
    result = browser.start()
    print(f"Browser started: {result}")

    nav_result = browser.navigate("https://www.google.com")
    print(f"Navigation: {nav_result}")

    browser.screenshot()
    browser.stop()

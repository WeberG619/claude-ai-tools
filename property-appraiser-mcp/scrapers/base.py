"""
Base scraper class with common logic for property appraiser websites.

Uses CDP (Chrome DevTools Protocol) to connect to an already-running
Chrome instance on port 9222 for browser automation.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from cdp_client import CDPBrowser, CDPPage

logger = logging.getLogger("property-appraiser-mcp")


class BaseScraper(ABC):
    """Base class for property appraiser website scrapers."""

    RATE_LIMIT_SECONDS = 3.0

    def __init__(self):
        self._browser: Optional[CDPBrowser] = None
        self._last_request_time: float = 0.0

    def _ensure_browser(self) -> CDPBrowser:
        """Get or create the CDP browser connection."""
        if self._browser is None:
            self._browser = CDPBrowser()
        return self._browser

    async def _new_page(self) -> CDPPage:
        """Create a new browser tab via CDP."""
        browser = self._ensure_browser()
        connected = await browser.check_connection()
        if not connected:
            raise RuntimeError(
                "Chrome is not running with remote debugging enabled. "
                "Start Chrome with --remote-debugging-port=9222"
            )
        return await browser.new_page()

    async def _rate_limit(self):
        """Enforce minimum delay between requests."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.RATE_LIMIT_SECONDS:
            delay = self.RATE_LIMIT_SECONDS - elapsed
            logger.debug(f"Rate limiting: waiting {delay:.1f}s")
            await asyncio.sleep(delay)
        self._last_request_time = time.monotonic()

    async def close(self):
        """Shut down all browser tabs cleanly."""
        if self._browser:
            await self._browser.close_all()
            self._browser = None

    # ---- Abstract interface ----

    @abstractmethod
    async def search_property(
        self, address: Optional[str] = None, folio: Optional[str] = None
    ) -> list[dict]:
        ...

    @abstractmethod
    async def get_property_details(self, folio: str) -> dict:
        ...

    @abstractmethod
    async def get_sales_history(self, folio: str) -> list[dict]:
        ...

    # ---- Utility helpers ----

    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        if not text:
            return ""
        return " ".join(text.strip().split())

    @staticmethod
    def parse_currency(text: Optional[str]) -> Optional[float]:
        if not text:
            return None
        cleaned = text.replace("$", "").replace(",", "").strip()
        if not cleaned or cleaned in ("N/A", "-"):
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def parse_int(text: Optional[str]) -> Optional[int]:
        if not text:
            return None
        cleaned = text.replace(",", "").strip()
        if not cleaned or cleaned in ("N/A", "-"):
            return None
        try:
            return int(float(cleaned))
        except ValueError:
            return None

    @staticmethod
    def normalize_folio(folio: str) -> str:
        return folio.replace("-", "").replace(" ", "").strip()

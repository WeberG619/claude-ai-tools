"""
Base scraper class for eTRAKiT / CentralSquare permit portal websites.

Uses CDP (Chrome DevTools Protocol) to connect to an already-running
Chrome instance on port 9222 for browser automation.

eTRAKiT portals share a common CentralSquare architecture:
- ASP.NET WebForms with ViewState
- Telerik RadGrid, RadTabStrip, RadMultiPage controls
- __EVENTTARGET / __EVENTARGUMENT postback pattern
- AJAX partial postbacks via RadAjaxManager
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from cdp_client import CDPBrowser, CDPPage

logger = logging.getLogger("etrakit-mcp")


class BasePermitScraper(ABC):
    """Base class for eTRAKiT permit portal scrapers."""

    RATE_LIMIT_SECONDS = 3.0
    AJAX_TIMEOUT_MS = 15000

    def __init__(self):
        self._browser: Optional[CDPBrowser] = None
        self._last_request_time: float = 0.0

    # ---- Browser Management ----

    def _ensure_browser(self) -> CDPBrowser:
        if self._browser is None:
            self._browser = CDPBrowser()
        return self._browser

    async def _new_page(self) -> CDPPage:
        browser = self._ensure_browser()
        connected = await browser.check_connection()
        if not connected:
            raise RuntimeError(
                "Chrome is not running with remote debugging enabled. "
                "Start Chrome with --remote-debugging-port=9222"
            )
        return await browser.new_page()

    async def _rate_limit(self):
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.RATE_LIMIT_SECONDS:
            delay = self.RATE_LIMIT_SECONDS - elapsed
            logger.debug(f"Rate limiting: waiting {delay:.1f}s")
            await asyncio.sleep(delay)
        self._last_request_time = time.monotonic()

    async def close(self):
        if self._browser:
            await self._browser.close_all()
            self._browser = None

    # ---- ASP.NET WebForms Helpers ----

    async def _wait_for_ajax(self, page: CDPPage, timeout_ms: Optional[int] = None):
        """Wait for ASP.NET AJAX / Telerik partial postback to complete."""
        timeout = timeout_ms or self.AJAX_TIMEOUT_MS
        try:
            await page.wait_for_function(
                """(() => {
                    const panels = document.querySelectorAll('.RadAjax_Loading, .raLoading, [id*="LoadingPanel"]');
                    for (const p of panels) {
                        if (p.offsetParent !== null) return false;
                    }
                    if (typeof Sys !== 'undefined' && Sys.WebForms && Sys.WebForms.PageRequestManager) {
                        const prm = Sys.WebForms.PageRequestManager.getInstance();
                        if (prm && prm.get_isInAsyncPostBack()) return false;
                    }
                    return true;
                })()""",
                timeout_ms=timeout,
            )
        except (asyncio.TimeoutError, Exception):
            logger.debug("AJAX wait timed out, continuing...")

    async def _do_postback(self, page: CDPPage, event_target: str, event_argument: str = ""):
        """Trigger an ASP.NET __doPostBack call."""
        await page.evaluate(f"__doPostBack('{event_target}', '{event_argument}')")

    async def _get_viewstate(self, page: CDPPage) -> dict:
        """Extract ASP.NET ViewState and related hidden fields."""
        return await page.evaluate("""
            (() => {
                const fields = {};
                for (const name of ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION',
                                     '__EVENTTARGET', '__EVENTARGUMENT']) {
                    const el = document.querySelector('input[name="' + name + '"]');
                    fields[name] = el ? el.value : '';
                }
                return fields;
            })()
        """) or {}

    # ---- Tab Navigation Helper ----

    async def _click_tab(self, page: CDPPage, tab_text: str):
        """Click a RadTabStrip tab by its visible text label."""
        clicked = await page.evaluate(f"""
            (() => {{
                const text = {repr(tab_text)};
                // Try Telerik tab spans
                const spans = document.querySelectorAll('.rtsTxt, .rtsLink span, .rtsLI span');
                for (const span of spans) {{
                    if (span.textContent.trim() === text) {{
                        span.click();
                        return true;
                    }}
                }}
                // Fallback: any clickable element with exact text
                const all = document.querySelectorAll('a, span, li, div');
                for (const el of all) {{
                    if (el.textContent.trim() === text && el.offsetParent !== null) {{
                        el.click();
                        return true;
                    }}
                }}
                return false;
            }})()
        """)

        if not clicked:
            logger.warning(f"Could not find tab '{tab_text}'")
            return

        await asyncio.sleep(0.5)
        await self._wait_for_ajax(page)
        await asyncio.sleep(0.5)

    # ---- Data Extraction Helpers ----

    async def _extract_table_rows(self, page: CDPPage, table_selector: str) -> list[dict]:
        """Extract data from a RadGrid or HTML table."""
        return await page.evaluate(f"""
            ((selector) => {{
                const table = document.querySelector(selector);
                if (!table) return [];

                const headers = [];
                const headerCells = table.querySelectorAll('thead th, .rgHeader');
                headerCells.forEach(th => headers.push(th.innerText.trim()));

                if (headers.length === 0) {{
                    const firstRow = table.querySelector('tr');
                    if (firstRow) {{
                        firstRow.querySelectorAll('th, td').forEach(cell => {{
                            headers.push(cell.innerText.trim());
                        }});
                    }}
                }}

                const rows = [];
                const dataRows = table.querySelectorAll('tbody tr, .rgRow, .rgAltRow');
                dataRows.forEach(tr => {{
                    if (tr.classList.contains('rgHeader') || tr.classList.contains('rgPager')) return;
                    const cells = tr.querySelectorAll('td');
                    const row = {{}};
                    cells.forEach((td, i) => {{
                        const key = i < headers.length ? headers[i] : 'col_' + i;
                        row[key] = td.innerText.trim();
                    }});
                    if (Object.keys(row).length > 0) rows.push(row);
                }});
                return rows;
            }})('{table_selector}')
        """) or []

    async def _extract_label_value_pairs(self, page: CDPPage, container_selector: str) -> dict:
        """Extract label-value pairs from a form-like layout."""
        return await page.evaluate(f"""
            ((selector) => {{
                const container = document.querySelector(selector);
                if (!container) return {{}};

                const result = {{}};

                const labels = container.querySelectorAll('.LabelColumn, .PermitDetailLabel, [class*="Label"]');
                labels.forEach(label => {{
                    const key = label.innerText.replace(/:$/, '').trim();
                    const value = label.nextElementSibling;
                    if (key && value) result[key] = value.innerText.trim();
                }});

                if (Object.keys(result).length === 0) {{
                    const rows = container.querySelectorAll('tr');
                    rows.forEach(tr => {{
                        const cells = tr.querySelectorAll('td, th');
                        if (cells.length >= 2) {{
                            const key = cells[0].innerText.replace(/:$/, '').trim();
                            const val = cells[1].innerText.trim();
                            if (key && val) result[key] = val;
                        }}
                    }});
                }}

                if (Object.keys(result).length === 0) {{
                    const allText = container.innerHTML;
                    const matches = allText.matchAll(/<(?:b|strong)[^>]*>([^<]+)<\\/(?:b|strong)>\\s*:?\\s*([^<]*)/gi);
                    for (const match of matches) {{
                        const key = match[1].replace(/:$/, '').trim();
                        const val = match[2].trim();
                        if (key && val) result[key] = val;
                    }}
                }}

                return result;
            }})('{container_selector}')
        """) or {}

    async def _get_all_grid_pages(self, page: CDPPage, grid_selector: str) -> list[dict]:
        """Extract all rows from a paginated RadGrid."""
        all_rows = []
        page_num = 1
        max_pages = 20

        while page_num <= max_pages:
            rows = await self._extract_table_rows(
                page, f"{grid_selector} table, {grid_selector} .rgMasterTable"
            )
            if not rows:
                break
            all_rows.extend(rows)

            has_next = await page.evaluate(f"""
                (() => {{
                    const grid = document.querySelector('{grid_selector}');
                    if (!grid) return false;
                    const pager = grid.querySelector('.rgPager, .rgAdvPart');
                    if (!pager) return false;
                    const nextBtn = pager.querySelector('.rgPageNext:not(.rgDisabled), .rgCurrentPage + a, input[title="Next Page"]');
                    return nextBtn !== null;
                }})()
            """)

            if not has_next:
                break

            clicked = await page.evaluate(f"""
                (() => {{
                    const grid = document.querySelector('{grid_selector}');
                    if (!grid) return false;
                    const btn = grid.querySelector('.rgPageNext:not(.rgDisabled), input[title="Next Page"]');
                    if (btn) {{ btn.click(); return true; }}
                    return false;
                }})()
            """)

            if not clicked:
                break

            await self._wait_for_ajax(page)
            await asyncio.sleep(1)
            page_num += 1

        return all_rows

    # ---- Utility Helpers ----

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
        if not cleaned or cleaned in ("N/A", "-", ""):
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def normalize_permit_number(permit_no: str) -> str:
        return permit_no.strip().upper()

    # ---- Abstract Interface ----

    @abstractmethod
    async def search_permits(self, query: str, search_type: str = "address") -> list[dict]:
        ...

    @abstractmethod
    async def get_permit_details(self, permit_number: str) -> dict:
        ...

    @abstractmethod
    async def get_permit_inspections(self, permit_number: str) -> list[dict]:
        ...

    @abstractmethod
    async def get_permit_comments(self, permit_number: str) -> list[dict]:
        ...

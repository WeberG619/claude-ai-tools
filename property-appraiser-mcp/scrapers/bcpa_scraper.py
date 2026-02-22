"""
Broward County Property Appraiser (BCPA) scraper.

Website: https://web.bcpa.net/BcpaClient/
Architecture: AngularJS 1.8.2 SPA with ui-router

Uses CDP to connect to Chrome for browser automation.
All DOM extraction is done via single JavaScript evaluate() calls
for efficiency (one round-trip instead of many).
"""

import logging
import re
from typing import Optional

from cdp_client import CDPPage, CDPError
from .base import BaseScraper

logger = logging.getLogger("property-appraiser-mcp")

BASE_URL = "https://web.bcpa.net/BcpaClient"

# Shared JavaScript function for extracting labeled values from page DOM.
# Injected into each evaluate() call that needs it.
JS_GET_LABELED = """
function getLabeled(labels) {
    for (const label of labels) {
        // dt/dd
        for (const dt of document.querySelectorAll('dt')) {
            if (dt.textContent.trim().toLowerCase().includes(label.toLowerCase())) {
                const dd = dt.nextElementSibling;
                if (dd && dd.tagName === 'DD') {
                    const v = dd.innerText.trim();
                    if (v) return v;
                }
            }
        }
        // th/td
        for (const th of document.querySelectorAll('th')) {
            if (th.textContent.trim().toLowerCase().includes(label.toLowerCase())) {
                const td = th.nextElementSibling;
                if (td && td.tagName === 'TD') {
                    const v = td.innerText.trim();
                    if (v) return v;
                }
            }
        }
        // label + sibling
        for (const lbl of document.querySelectorAll('label')) {
            if (lbl.textContent.trim().toLowerCase().includes(label.toLowerCase())) {
                const sib = lbl.nextElementSibling;
                if (sib) {
                    const v = sib.innerText.trim();
                    if (v) return v;
                }
            }
        }
        // span in parent
        for (const span of document.querySelectorAll('span')) {
            if (span.textContent.trim().toLowerCase().includes(label.toLowerCase())) {
                const parent = span.parentElement;
                if (parent) {
                    const text = parent.textContent.trim();
                    const idx = text.toLowerCase().indexOf(label.toLowerCase());
                    if (idx >= 0) {
                        let after = text.substring(idx + label.length).replace(/^[\\s:]+/, '').trim();
                        if (after) return after.split('\\n')[0].trim();
                    }
                }
            }
        }
        // .label + .value divs
        for (const el of document.querySelectorAll('.label, .field-label')) {
            if (el.textContent.trim().toLowerCase().includes(label.toLowerCase())) {
                const sib = el.nextElementSibling;
                if (sib) {
                    const v = sib.innerText.trim();
                    if (v) return v;
                }
            }
        }
        // Text pattern "Label: Value"
        const escaped = label.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
        const re = new RegExp(escaped + '\\\\s*:\\\\s*(.+)', 'im');
        const match = document.body.innerText.match(re);
        if (match) {
            const v = match[1].trim().split('\\n')[0].trim();
            if (v && !v.endsWith(':')) return v;
        }
    }
    return '';
}
"""


class BCPAScraper(BaseScraper):
    """Scraper for the Broward County Property Appraiser website."""

    async def search_property(
        self, address: Optional[str] = None, folio: Optional[str] = None
    ) -> list[dict]:
        if not address and not folio:
            raise ValueError("Provide either an address or folio number to search.")

        await self._rate_limit()

        if folio:
            return await self._search_by_folio(folio)
        else:
            return await self._search_by_address(address)

    async def _search_by_folio(self, folio: str) -> list[dict]:
        folio_clean = self.normalize_folio(folio)
        logger.info(f"BCPA: Searching by folio {folio_clean}")

        page = await self._new_page()
        try:
            # Try direct detail URL first
            detail_url = f"{BASE_URL}/#/Record-Detail/{folio_clean}"
            logger.info(f"BCPA: Navigating to {detail_url}")
            await page.goto(detail_url)
            await page.wait(3000)

            summary = await self._extract_property_summary(page)
            if summary and summary.get("folio"):
                return [summary]

            # Try search page with folio input
            search_url = f"{BASE_URL}/#/Record-Search"
            logger.info(f"BCPA: Trying search page: {search_url}")
            await page.goto(search_url)
            await page.wait(2000)

            filled = await page.fill_first_visible([
                'input[ng-model*="folio" i]',
                'input[placeholder*="folio" i]',
                'input[name*="folio" i]',
                'input[id*="folio" i]',
                '#txtFolio',
            ], folio_clean)

            if filled:
                clicked = await page.click_first_visible([
                    'button[type="submit"]',
                    'input[type="submit"]',
                    '#btnSearch',
                    'button.btn-primary',
                ])
                if not clicked:
                    await page.press_enter()
                await page.wait(3000)

                results = await self._extract_search_results(page)
                if results:
                    return results

            # Last resort: search.aspx URL
            alt_url = f"{BASE_URL}/search.aspx?Folio={folio_clean}"
            logger.info(f"BCPA: Trying {alt_url}")
            await page.goto(alt_url)
            await page.wait(3000)

            summary = await self._extract_property_summary(page)
            if summary and summary.get("folio"):
                return [summary]

            return []

        except CDPError as e:
            logger.error(f"BCPA folio search error: {e}")
            return []
        finally:
            await page.close()

    async def _search_by_address(self, address: str) -> list[dict]:
        logger.info(f"BCPA: Searching by address: {address}")

        page = await self._new_page()
        try:
            url = f"{BASE_URL}/#/Record-Search"
            await page.goto(url)
            await page.wait(2000)

            parts = address.strip().split()
            house_number = ""
            street_name = ""
            if parts and parts[0].isdigit():
                house_number = parts[0]
                street_name = " ".join(parts[1:])
            else:
                street_name = address.strip()

            # Try filling separate house number and street name fields
            filled = False
            if house_number:
                await page.fill_first_visible([
                    'input[ng-model*="houseNumber" i]',
                    'input[ng-model*="streetNumber" i]',
                    'input[placeholder*="house" i]',
                    'input[placeholder*="number" i]',
                    '#txtHouseNumber',
                ], house_number)

            street_filled = await page.fill_first_visible([
                'input[ng-model*="streetName" i]',
                'input[ng-model*="street" i]',
                'input[placeholder*="street" i]',
                '#txtStreetName',
            ], street_name)

            if street_filled:
                filled = True
                clicked = await page.click_first_visible([
                    'button[type="submit"]',
                    'input[type="submit"]',
                    '#btnSearch',
                    'button.btn-primary',
                ])
                if not clicked:
                    await page.press_enter()
                await page.wait(3000)

            # Fallback: single search input
            if not filled:
                filled = await page.fill_first_visible([
                    'input[type="search"]',
                    'input[placeholder*="search" i]',
                    'input[ng-model*="search" i]',
                    '#searchInput',
                ], address)
                if filled:
                    await page.press_enter()
                    await page.wait(3000)

            if not filled:
                # Last resort: first visible text input
                filled = await page.evaluate(f"""
                    (() => {{
                        const inputs = document.querySelectorAll('input[type="text"]');
                        for (const inp of inputs) {{
                            if (inp.offsetParent !== null) {{
                                inp.focus();
                                inp.value = {repr(address)};
                                inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                                return true;
                            }}
                        }}
                        return false;
                    }})()
                """)
                if filled:
                    await page.press_enter()
                    await page.wait(3000)

            if not filled:
                logger.warning("BCPA: Could not find address search fields")
                return []

            results = await self._extract_search_results(page)
            return results

        except CDPError as e:
            logger.error(f"BCPA address search error: {e}")
            return []
        finally:
            await page.close()

    async def _extract_search_results(self, page: CDPPage) -> list[dict]:
        """Extract property search results from the page."""
        results = await page.evaluate("""
            (() => {
                const results = [];
                const seen = new Set();

                // Try table rows, ng-repeat elements, etc.
                const rows = document.querySelectorAll(
                    'table tbody tr, .search-results tr, .result-row, ' +
                    '[ng-repeat*="result"], [ng-repeat*="property"], ' +
                    '[ng-repeat*="record"], .property-row'
                );

                for (const row of [...rows].slice(0, 20)) {
                    const text = row.innerText || '';
                    const record = {folio: '', address: '', owner_name: '', assessed_value: null, county: 'broward'};

                    // Find 12-digit folio
                    const folioMatch = text.replace(/[-\\s]/g, '').match(/\\b(\\d{12})\\b/);
                    if (folioMatch) record.folio = folioMatch[1];

                    // Check links for folio
                    const links = row.querySelectorAll('a');
                    for (const link of links) {
                        const href = link.href || '';
                        const m = href.replace(/[-\\s]/g, '').match(/(\\d{12})/);
                        if (m) record.folio = m[1];
                    }

                    // Parse cells
                    const cells = row.querySelectorAll('td');
                    for (const cell of cells) {
                        const ct = cell.innerText.trim();
                        const ctClean = ct.replace(/[-\\s]/g, '');
                        if (/^\\d{12}$/.test(ctClean) && !record.folio) {
                            record.folio = ctClean;
                        } else if (ct.includes('$') || (/^[\\d,]+$/.test(ct) && ct.length > 3)) {
                            const val = parseFloat(ct.replace(/[$,]/g, ''));
                            if (val > 1000) record.assessed_value = val;
                        } else if (/^\\d+\\s+\\w+/.test(ct) && ct.length > 8 && !record.address) {
                            record.address = ct;
                        } else if (ct && !/^\\d/.test(ct.substring(0, 3)) && !record.owner_name && ct.length > 2) {
                            record.owner_name = ct;
                        }
                    }

                    if (record.folio && !seen.has(record.folio)) {
                        seen.add(record.folio);
                        results.push(record);
                    }
                }

                // Fallback: extract folios from body text
                if (results.length === 0) {
                    const bodyText = document.body.innerText.replace(/[-\\s]/g, '');
                    const matches = bodyText.match(/\\b\\d{12}\\b/g) || [];
                    for (const folio of matches) {
                        if (!seen.has(folio)) {
                            seen.add(folio);
                            results.push({folio, address: '', owner_name: '', assessed_value: null, county: 'broward'});
                        }
                    }
                }

                return results;
            })()
        """) or []

        logger.info(f"BCPA: Extracted {len(results)} results")
        return results

    async def _extract_property_summary(self, page: CDPPage) -> dict:
        """Extract a property summary from a detail page."""
        return await page.evaluate(f"""
            (() => {{
                {JS_GET_LABELED}

                const record = {{folio: '', address: '', owner_name: '', assessed_value: null, county: 'broward'}};

                const bodyText = document.body.innerText.replace(/[-\\s]/g, '');
                const folioMatch = bodyText.match(/\\b(\\d{{12}})\\b/);
                if (folioMatch) record.folio = folioMatch[1];

                record.owner_name = getLabeled(['Owner', 'Property Owner', 'Owner Name']);
                record.address = getLabeled(['Property Address', 'Site Address', 'Address', 'Location']);

                const valText = getLabeled(['Just Value', 'Assessed Value', 'Total Value', 'Market Value']);
                if (valText) {{
                    const v = parseFloat(valText.replace(/[$,]/g, ''));
                    if (!isNaN(v)) record.assessed_value = v;
                }}

                return record;
            }})()
        """) or {}

    async def get_property_details(self, folio: str) -> dict:
        folio_clean = self.normalize_folio(folio)
        logger.info(f"BCPA: Getting details for folio {folio_clean}")

        await self._rate_limit()

        page = await self._new_page()
        try:
            detail_url = f"{BASE_URL}/#/Record-Detail/{folio_clean}"
            logger.info(f"BCPA: Navigating to {detail_url}")
            await page.goto(detail_url)
            await page.wait(3000)

            # Check if page loaded with content
            body_text = await page.get_text("body")
            if len(body_text.strip()) < 100 or "not found" in body_text.lower():
                alt_url = f"{BASE_URL}/search.aspx?Folio={folio_clean}"
                logger.info(f"BCPA: Trying alternate URL: {alt_url}")
                await page.goto(alt_url)
                await page.wait(3000)

            details = await self._extract_full_details(page, folio_clean)
            return details

        except CDPError as e:
            logger.error(f"BCPA detail error: {e}")
            return {"error": str(e), "folio": folio_clean, "county": "broward"}
        finally:
            await page.close()

    async def _extract_full_details(self, page: CDPPage, folio: str) -> dict:
        """Extract all property details in a single JS evaluation."""
        details = await page.evaluate(f"""
            (() => {{
                {JS_GET_LABELED}

                function parseCurrency(text) {{
                    if (!text) return null;
                    const v = parseFloat(text.replace(/[$,]/g, ''));
                    return isNaN(v) ? null : v;
                }}

                function parseInt2(text) {{
                    if (!text) return null;
                    const v = parseInt(text.replace(/,/g, ''));
                    return isNaN(v) ? null : v;
                }}

                const d = {{
                    folio: '{folio}',
                    county: 'broward',
                    owner_name: getLabeled(['Owner', 'Property Owner', 'Owner Name', 'Owner(s)']),
                    mailing_address: getLabeled(['Mailing Address', 'Mail Address', 'Owner Address']),
                    property_address: getLabeled(['Property Address', 'Site Address', 'Address', 'Location']),
                    legal_description: getLabeled(['Legal Description', 'Legal', 'Legal Desc']),
                    land_use_code: getLabeled(['Land Use', 'Use Code', 'Land Use Code', 'Property Use']),
                    zoning: getLabeled(['Zoning', 'Zone', 'Zoning Code']),
                    lot_dimensions: getLabeled(['Lot Dimensions', 'Dimensions', 'Lot Size']),
                    lot_size_sf: parseInt2(getLabeled(['Lot Size', 'Lot Area', 'Land Area', 'Lot SF', 'Land Size'])),
                    assessed_value: {{
                        land: parseCurrency(getLabeled(['Land Value', 'Land Assessed', 'Assessed Land'])),
                        building: parseCurrency(getLabeled(['Building Value', 'Improvement Value', 'Building Assessed', 'Assessed Building', 'Improvement'])),
                        total: parseCurrency(getLabeled(['Assessed Value', 'Total Assessed', 'Total Assessment', 'Assessed'])),
                    }},
                    market_value: {{
                        land: parseCurrency(getLabeled(['Market Land', 'Just Land', 'Land Market'])),
                        building: parseCurrency(getLabeled(['Market Building', 'Just Building', 'Building Market', 'Market Improvement'])),
                        total: parseCurrency(getLabeled(['Just Value', 'Market Value', 'Total Market', 'Total Just', 'Fair Market Value'])),
                    }},
                    taxable_value: parseCurrency(getLabeled(['Taxable Value', 'Taxable', 'Net Taxable'])),
                    exemptions: [],
                    building_info: {{
                        year_built: parseInt2(getLabeled(['Year Built', 'Built', 'Year Constructed'])),
                        bedrooms: parseInt2(getLabeled(['Bedrooms', 'Beds', 'BR'])),
                        bathrooms: parseInt2(getLabeled(['Bathrooms', 'Baths', 'BA', 'Full Baths'])),
                        living_area_sf: parseInt2(getLabeled(['Living Area', 'Living SF', 'Living Sq Ft', 'Total Living', 'Heated Area', 'Adjusted Area'])),
                        construction_type: getLabeled(['Construction', 'Construction Type', 'Structure Type']),
                        roof_type: getLabeled(['Roof', 'Roof Type', 'Roof Material', 'Roofing']),
                        stories: parseInt2(getLabeled(['Stories', 'Floors', 'Number of Stories'])),
                    }},
                    sales_history: [],
                }};

                // Exemptions
                const exemptionText = getLabeled(['Exemptions', 'Exemption', 'Tax Exemptions']);
                if (exemptionText) {{
                    d.exemptions = exemptionText.split(',').map(e => e.trim()).filter(e => e);
                }}

                // Sales history from tables
                const tables = document.querySelectorAll('table');
                for (const table of tables) {{
                    const headerText = table.innerText.toLowerCase();
                    if (!['sale', 'transfer', 'deed', 'conveyance', 'transaction'].some(kw => headerText.includes(kw))) continue;

                    const rows = table.querySelectorAll('tbody tr, tr');
                    for (const row of rows) {{
                        const cells = row.querySelectorAll('td');
                        if (cells.length < 2) continue;

                        const sale = {{date: '', price: null, buyer: '', seller: '', qualified: '', book_page: ''}};
                        for (const cell of cells) {{
                            const ct = cell.innerText.trim();
                            const dateMatch = ct.match(/(\\d{{1,2}}\\/\\d{{1,2}}\\/\\d{{4}}|\\d{{4}}-\\d{{2}}-\\d{{2}})/);
                            if (dateMatch && !sale.date) {{ sale.date = dateMatch[1]; continue; }}
                            if (ct.includes('$') || (/^[\\d,]+$/.test(ct) && ct.length > 3)) {{
                                const p = parseFloat(ct.replace(/[$,]/g, ''));
                                if (p > 0) {{ sale.price = p; continue; }}
                            }}
                            const lower = ct.toLowerCase().trim();
                            if (['q', 'u', 'qualified', 'unqualified', 'yes', 'no'].includes(lower)) {{
                                sale.qualified = ct; continue;
                            }}
                            if (/^\\d+\\/\\d+$/.test(ct) || ct.toUpperCase().includes('OR')) {{
                                sale.book_page = ct; continue;
                            }}
                        }}
                        if (sale.date || sale.price) d.sales_history.push(sale);
                    }}
                    if (d.sales_history.length > 0) break;
                }}

                // Fallback sales from text
                if (d.sales_history.length === 0) {{
                    const lines = document.body.innerText.split('\\n');
                    for (const line of lines) {{
                        const dateMatch = line.match(/(\\d{{1,2}}\\/\\d{{1,2}}\\/\\d{{4}})/);
                        const priceMatch = line.match(/\\$[\\d,]+/);
                        if (dateMatch && priceMatch) {{
                            d.sales_history.push({{
                                date: dateMatch[1],
                                price: parseFloat(priceMatch[0].replace(/[$,]/g, '')),
                                buyer: '', seller: '', qualified: '', book_page: '',
                            }});
                        }}
                    }}
                }}

                return d;
            }})()
        """)

        return details or {"error": "No data extracted", "folio": folio, "county": "broward"}

    async def get_sales_history(self, folio: str) -> list[dict]:
        folio_clean = self.normalize_folio(folio)
        logger.info(f"BCPA: Getting sales history for folio {folio_clean}")

        await self._rate_limit()

        page = await self._new_page()
        try:
            detail_url = f"{BASE_URL}/#/Record-Detail/{folio_clean}"
            await page.goto(detail_url)
            await page.wait(3000)

            details = await self._extract_full_details(page, folio_clean)
            return details.get("sales_history", [])

        except CDPError as e:
            logger.error(f"BCPA sales history error: {e}")
            return []
        finally:
            await page.close()

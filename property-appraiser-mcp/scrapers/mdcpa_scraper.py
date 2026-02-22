"""
Miami-Dade County Property Appraiser (MDCPA) scraper.

Website: https://www.miamidade.gov/Apps/PA/propertysearch/
Architecture: Web application with search form

Uses CDP to connect to Chrome for browser automation.
All DOM extraction is done via single JavaScript evaluate() calls.
"""

import logging
import re
from typing import Optional

from cdp_client import CDPPage, CDPError
from .base import BaseScraper

logger = logging.getLogger("property-appraiser-mcp")

BASE_URL = "https://www.miamidade.gov/Apps/PA/propertysearch"

# Same JS helper as BCPA, with one addition for .label/.value div pattern
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
        // .label + .value div pattern (common in MDCPA)
        for (const el of document.querySelectorAll('.label, .field-label')) {
            if (el.textContent.trim().toLowerCase().includes(label.toLowerCase())) {
                const sib = el.nextElementSibling;
                if (sib) {
                    const v = sib.innerText.trim();
                    if (v) return v;
                }
            }
        }
        // Text pattern
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


class MDCPAScraper(BaseScraper):
    """Scraper for the Miami-Dade County Property Appraiser website."""

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
        logger.info(f"MDCPA: Searching by folio {folio_clean}")

        page = await self._new_page()
        try:
            # Try direct property URL first
            property_url = f"{BASE_URL}/#/property/{folio_clean}"
            logger.info(f"MDCPA: Navigating to {property_url}")
            await page.goto(property_url)
            await page.wait(3000)

            summary = await self._extract_property_summary(page)
            if summary and summary.get("folio"):
                return [summary]

            # Try folio search page
            search_url = f"{BASE_URL}/#/folioSearch"
            logger.info(f"MDCPA: Trying folio search: {search_url}")
            await page.goto(search_url)
            await page.wait(2000)

            filled = await page.fill_first_visible([
                'input[id*="folio" i]',
                'input[name*="folio" i]',
                'input[placeholder*="folio" i]',
                'input[ng-model*="folio" i]',
                '#folioNumber',
                '#txtFolio',
                'input.folio-input',
            ], folio_clean)

            if filled:
                clicked = await page.click_first_visible([
                    'button[type="submit"]',
                    'input[type="submit"]',
                    '#btnSearch',
                    'button.btn-primary',
                    'i.fa-search',
                ])
                if not clicked:
                    await page.press_enter()
                await page.wait(3000)

                results = await self._extract_search_results(page)
                if results:
                    return results

                # Check if navigated to a property detail
                summary = await self._extract_property_summary(page)
                if summary and summary.get("folio"):
                    return [summary]

            return []

        except CDPError as e:
            logger.error(f"MDCPA folio search error: {e}")
            return []
        finally:
            await page.close()

    async def _search_by_address(self, address: str) -> list[dict]:
        logger.info(f"MDCPA: Searching by address: {address}")

        page = await self._new_page()
        try:
            url = f"{BASE_URL}/#/addressSearch"
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

            filled = False
            if house_number:
                await page.fill_first_visible([
                    'input[id*="houseNumber" i]',
                    'input[name*="houseNumber" i]',
                    'input[placeholder*="house" i]',
                    'input[placeholder*="number" i]',
                    'input[ng-model*="houseNumber" i]',
                    '#txtHouseNo',
                ], house_number)

            street_filled = await page.fill_first_visible([
                'input[id*="streetName" i]',
                'input[name*="streetName" i]',
                'input[placeholder*="street" i]',
                'input[ng-model*="streetName" i]',
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

            if not filled:
                filled = await page.fill_first_visible([
                    'input[type="search"]',
                    'input[placeholder*="search" i]',
                    'input[placeholder*="address" i]',
                    'input[ng-model*="search" i]',
                    '#searchInput',
                ], address)
                if filled:
                    await page.press_enter()
                    await page.wait(3000)

            if not filled:
                logger.warning("MDCPA: Could not find address search fields")
                return []

            results = await self._extract_search_results(page)
            return results

        except CDPError as e:
            logger.error(f"MDCPA address search error: {e}")
            return []
        finally:
            await page.close()

    async def _extract_search_results(self, page: CDPPage) -> list[dict]:
        results = await page.evaluate("""
            (() => {
                const results = [];
                const seen = new Set();

                const rows = document.querySelectorAll(
                    'table tbody tr, .search-results tr, .result-row, ' +
                    '.property-row, [ng-repeat*="result"], [ng-repeat*="property"], ' +
                    '.search-result-item, .property-card'
                );

                for (const row of [...rows].slice(0, 20)) {
                    const text = (row.innerText || '').replace(/[-\\s]/g, '');
                    const record = {folio: '', address: '', owner_name: '', assessed_value: null, county: 'miami-dade'};

                    // Miami-Dade folios: 10-13 digits
                    const folioMatch = text.match(/\\b(\\d{10,13})\\b/);
                    if (folioMatch) record.folio = folioMatch[1];

                    // Check links
                    for (const link of row.querySelectorAll('a')) {
                        const href = (link.href || '').replace(/[-\\s]/g, '');
                        const m = href.match(/(\\d{10,13})/);
                        if (m) record.folio = m[1];
                    }

                    // Parse cells
                    for (const cell of row.querySelectorAll('td')) {
                        const ct = cell.innerText.trim();
                        const ctClean = ct.replace(/[-\\s]/g, '');
                        if (/^\\d{10,13}$/.test(ctClean) && !record.folio) {
                            record.folio = ctClean;
                        } else if (ct.includes('$')) {
                            const v = parseFloat(ct.replace(/[$,]/g, ''));
                            if (v > 1000) record.assessed_value = v;
                        } else if (/^\\d+\\s+\\w+/.test(ct) && ct.length > 8 && !record.address) {
                            record.address = ct;
                        } else if (ct && !/^\\d/.test(ct.substring(0, 3)) && ct.length > 3 && !record.owner_name) {
                            record.owner_name = ct;
                        }
                    }

                    if (record.folio && !seen.has(record.folio)) {
                        seen.add(record.folio);
                        results.push(record);
                    }
                }

                // Fallback
                if (results.length === 0) {
                    const bodyText = document.body.innerText.replace(/[-\\s]/g, '');
                    const matches = bodyText.match(/\\b\\d{13}\\b/g) || [];
                    for (const folio of matches) {
                        if (!seen.has(folio)) {
                            seen.add(folio);
                            results.push({folio, address: '', owner_name: '', assessed_value: null, county: 'miami-dade'});
                        }
                    }
                }

                return results;
            })()
        """) or []

        logger.info(f"MDCPA: Extracted {len(results)} results")
        return results

    async def _extract_property_summary(self, page: CDPPage) -> dict:
        return await page.evaluate(f"""
            (() => {{
                {JS_GET_LABELED}

                const record = {{folio: '', address: '', owner_name: '', assessed_value: null, county: 'miami-dade'}};

                const bodyText = document.body.innerText.replace(/[-\\s]/g, '');
                const m13 = bodyText.match(/\\b(\\d{{13}})\\b/);
                if (m13) record.folio = m13[1];
                else {{
                    const m10 = bodyText.match(/\\b(\\d{{10,13}})\\b/);
                    if (m10) record.folio = m10[1];
                }}

                record.owner_name = getLabeled(['Owner', 'Property Owner', 'Owner Name']);
                record.address = getLabeled(['Property Address', 'Site Address', 'Address', 'Location']);

                const valText = getLabeled(['Assessed Value', 'Just Value', 'Total Value', 'Market Value']);
                if (valText) {{
                    const v = parseFloat(valText.replace(/[$,]/g, ''));
                    if (!isNaN(v)) record.assessed_value = v;
                }}

                return record;
            }})()
        """) or {}

    async def get_property_details(self, folio: str) -> dict:
        folio_clean = self.normalize_folio(folio)
        logger.info(f"MDCPA: Getting details for folio {folio_clean}")

        await self._rate_limit()

        page = await self._new_page()
        try:
            property_url = f"{BASE_URL}/#/property/{folio_clean}"
            logger.info(f"MDCPA: Navigating to {property_url}")
            await page.goto(property_url)
            await page.wait(3000)

            body_text = await page.get_text("body")
            if len(body_text.strip()) < 100 or "not found" in body_text.lower():
                search_url = f"{BASE_URL}/#/folioSearch"
                await page.goto(search_url)
                await page.wait(2000)
                filled = await page.fill_first_visible([
                    'input[id*="folio" i]',
                    'input[name*="folio" i]',
                    '#folioNumber',
                ], folio_clean)
                if filled:
                    await page.press_enter()
                    await page.wait(3000)
                else:
                    return {"error": "Could not load property record", "folio": folio_clean, "county": "miami-dade"}

            details = await self._extract_full_details(page, folio_clean)
            return details

        except CDPError as e:
            logger.error(f"MDCPA detail error: {e}")
            return {"error": str(e), "folio": folio_clean, "county": "miami-dade"}
        finally:
            await page.close()

    async def _extract_full_details(self, page: CDPPage, folio: str) -> dict:
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
                    county: 'miami-dade',
                    owner_name: getLabeled(['Owner', 'Property Owner', 'Owner Name', 'Owner(s)']),
                    mailing_address: getLabeled(['Mailing Address', 'Mail Address', 'Owner Address', 'Mailing']),
                    property_address: getLabeled(['Property Address', 'Site Address', 'Address', 'Location']),
                    legal_description: getLabeled(['Legal Description', 'Legal', 'Legal Desc']),
                    land_use_code: getLabeled(['Land Use', 'Use Code', 'Land Use Code', 'Primary Land Use']),
                    zoning: getLabeled(['Zoning', 'Zone', 'Zoning Code', 'Municipal Zoning']),
                    lot_dimensions: getLabeled(['Lot Dimensions', 'Dimensions']),
                    lot_size_sf: parseInt2(getLabeled(['Lot Size', 'Lot Area', 'Land Area', 'Total Land Area'])),
                    assessed_value: {{
                        land: parseCurrency(getLabeled(['Land Value', 'Assessed Land', 'Land Assessed'])),
                        building: parseCurrency(getLabeled(['Building Value', 'Improvement Value', 'Building Assessed', 'Improvements'])),
                        total: parseCurrency(getLabeled(['Assessed Value', 'Total Assessed', 'County Assessed Value'])),
                    }},
                    market_value: {{
                        land: parseCurrency(getLabeled(['Market Land', 'Land Market Value'])),
                        building: parseCurrency(getLabeled(['Market Building', 'Building Market Value'])),
                        total: parseCurrency(getLabeled(['Just Value', 'Market Value', 'Total Market', 'Fair Market Value'])),
                    }},
                    taxable_value: parseCurrency(getLabeled(['Taxable Value', 'Taxable', 'County Taxable Value', 'School Taxable Value'])),
                    exemptions: [],
                    building_info: {{
                        year_built: parseInt2(getLabeled(['Year Built', 'Built', 'Year Constructed', 'Actual Year Built'])),
                        bedrooms: parseInt2(getLabeled(['Bedrooms', 'Beds', 'BR'])),
                        bathrooms: parseInt2(getLabeled(['Bathrooms', 'Baths', 'BA', 'Full Baths'])),
                        living_area_sf: parseInt2(getLabeled(['Living Area', 'Living SF', 'Adj Bldg Sq Ft', 'Adjusted Sq Ft', 'Total Living Area', 'Building Sq Ft', 'Living Square Feet'])),
                        construction_type: getLabeled(['Construction', 'Construction Type', 'Building Type', 'Structure Type']),
                        roof_type: getLabeled(['Roof', 'Roof Type', 'Roof Material', 'Roof Cover']),
                        stories: parseInt2(getLabeled(['Stories', 'Floors', 'Number of Floors'])),
                    }},
                    sales_history: [],
                }};

                const exemptionText = getLabeled(['Exemptions', 'Exemption', 'Tax Exemptions']);
                if (exemptionText) {{
                    d.exemptions = exemptionText.split(',').map(e => e.trim()).filter(e => e);
                }}

                // Sales history
                const tables = document.querySelectorAll('table');
                for (const table of tables) {{
                    const headerText = table.innerText.toLowerCase();
                    if (!['sale', 'transfer', 'deed', 'conveyance', 'transaction'].some(kw => headerText.includes(kw))) continue;

                    for (const row of table.querySelectorAll('tbody tr, tr')) {{
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

                if (d.sales_history.length === 0) {{
                    for (const line of document.body.innerText.split('\\n')) {{
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

        return details or {"error": "No data extracted", "folio": folio, "county": "miami-dade"}

    async def get_sales_history(self, folio: str) -> list[dict]:
        folio_clean = self.normalize_folio(folio)
        logger.info(f"MDCPA: Getting sales history for folio {folio_clean}")

        await self._rate_limit()

        page = await self._new_page()
        try:
            property_url = f"{BASE_URL}/#/property/{folio_clean}"
            await page.goto(property_url)
            await page.wait(3000)

            details = await self._extract_full_details(page, folio_clean)
            return details.get("sales_history", [])

        except CDPError as e:
            logger.error(f"MDCPA sales history error: {e}")
            return []
        finally:
            await page.close()

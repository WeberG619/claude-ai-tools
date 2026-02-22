"""
Coral Springs eTRAKiT permit portal scraper.

Portal URL: https://etrakit.coralsprings.gov/etrakit/
Platform: CentralSquare eTRAKiT (ASP.NET WebForms + Telerik)

Uses CDP to connect to Chrome for browser automation.
"""

import asyncio
import logging
import re
from typing import Optional

from cdp_client import CDPPage, CDPError
from .base import BasePermitScraper

logger = logging.getLogger("etrakit-mcp")

BASE_URL = "https://etrakit.coralsprings.gov/etrakit"
SEARCH_URL = f"{BASE_URL}/Search/Permit.aspx"


class CoralSpringsScraper(BasePermitScraper):
    """Scraper for Coral Springs eTRAKiT permit portal."""

    SEARCH_FIELD_MAP = {
        "permit_number": "PERMIT #",
        "address": "SITE ADDRESS",
        "contractor": "CONTRACTOR",
        "folio": "FOLIO",
        "owner": "OWNER",
        "status": "STATUS",
        "type": "PERMIT TYPE",
    }

    SEARCH_OPERATOR_MAP = {
        "permit_number": "Equals",
        "address": "Contains",
        "contractor": "Contains",
        "folio": "Equals",
        "owner": "Contains",
        "status": "Equals",
        "type": "Equals",
    }

    async def _navigate_to_search(self, page: CDPPage):
        """Navigate to the permit search page."""
        await self._rate_limit()
        logger.info(f"Navigating to {SEARCH_URL}")
        await page.goto(SEARCH_URL)
        await page.wait(1000)

    async def _perform_search(self, page: CDPPage, query: str, search_type: str = "address") -> bool:
        """Fill and submit the search form. Returns True if submitted."""
        field_label = self.SEARCH_FIELD_MAP.get(search_type, "SITE ADDRESS")
        operator = self.SEARCH_OPERATOR_MAP.get(search_type, "Contains")

        logger.info(f"Searching permits: {field_label} {operator} '{query}'")

        # Set the search field dropdown
        await self._try_set_dropdown(page, "SearchBy", field_label)

        # Set the operator dropdown
        await self._try_set_dropdown(page, "SearchOp", operator)

        # Fill the search input
        search_filled = await page.fill_first_visible([
            "input[id*='txtSearchString']",
            "input[id*='SearchString']",
            "#ctl00_cplMain_txtSearchString",
            "input.riTextBox[id*='cplMain']",
            "input[name*='txtSearchString']",
        ], query)

        if not search_filled:
            # Last resort: JS-based fill
            search_filled = await page.evaluate(f"""
                (() => {{
                    const inputs = document.querySelectorAll('input[type="text"]');
                    for (const inp of inputs) {{
                        if (inp.id.includes('Search') || inp.id.includes('search')) {{
                            inp.value = {repr(query)};
                            inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                            return true;
                        }}
                    }}
                    return false;
                }})()
            """)

        if not search_filled:
            logger.error("Could not fill search input")
            return False

        await page.wait(500)

        # Click the Search button
        search_clicked = await page.click_first_visible([
            "input[id*='btnSearch']",
            "#ctl00_cplMain_btnSearch",
            "input[value='Search']",
            "input[type='submit'][value*='Search']",
            "a[id*='btnSearch']",
        ])

        if not search_clicked:
            await page.press_enter()

        # Wait for results
        await page.wait(1000)
        await self._wait_for_ajax(page)
        await page.wait(1000)

        return True

    async def _try_set_dropdown(self, page: CDPPage, dropdown_key: str, value: str) -> bool:
        """Try to set a dropdown value."""
        # Try via standard select_option
        selectors = [
            f"select[id*='{dropdown_key}']",
            f"select[id*='dd{dropdown_key}']",
            f"#ctl00_cplMain_dd{dropdown_key}",
            f"select[name*='{dropdown_key}']",
        ]

        for sel in selectors:
            result = await page.select_option(sel, value)
            if result:
                logger.debug(f"Set dropdown {dropdown_key}='{value}' via {sel}")
                return True

        # Fallback: JS-based
        return bool(await page.evaluate(f"""
            (() => {{
                const key = {repr(dropdown_key)};
                const value = {repr(value)};
                const selects = document.querySelectorAll('select');
                for (const sel of selects) {{
                    if (sel.id.includes(key) || sel.name.includes(key)) {{
                        for (const opt of sel.options) {{
                            if (opt.text.includes(value) || opt.value.includes(value)) {{
                                sel.value = opt.value;
                                sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                                return true;
                            }}
                        }}
                    }}
                }}
                return false;
            }})()
        """))

    async def _extract_search_results(self, page: CDPPage) -> list[dict]:
        """Extract permit search results from the RadGrid."""
        raw_rows = None

        # Try the known grid selectors
        for grid_sel in [
            "#ctl00_cplMain_rgSearchRslts",
            "[id*='rgSearchRslts']",
            ".RadGrid",
            "table.rgMasterTable",
        ]:
            rows = await self._extract_table_rows(page, f"{grid_sel} table, {grid_sel}")
            if rows:
                logger.info(f"Found {len(rows)} results using selector: {grid_sel}")
                raw_rows = rows
                break

        # Fallback: any table with 3+ columns
        if not raw_rows:
            raw_rows = await page.evaluate("""
                (() => {
                    const results = [];
                    for (const table of document.querySelectorAll('table')) {
                        for (const tr of table.querySelectorAll('tbody tr, tr.rgRow, tr.rgAltRow')) {
                            const cells = tr.querySelectorAll('td');
                            if (cells.length >= 3) {
                                const row = {};
                                cells.forEach((td, i) => { row['col_' + i] = td.innerText.trim(); });
                                const link = tr.querySelector('a');
                                if (link) {
                                    row['_link'] = link.href;
                                    row['_link_text'] = link.innerText.trim();
                                }
                                results.push(row);
                            }
                        }
                    }
                    return results;
                })()
            """) or []

        results = []
        for row in (raw_rows or []):
            normalized = self._normalize_search_result(row)
            if normalized:
                results.append(normalized)

        return results

    def _normalize_search_result(self, row: dict) -> Optional[dict]:
        if not row:
            return None

        permit_number = ""
        permit_type = ""
        status = ""
        address = ""
        description = ""

        for key, val in row.items():
            key_lower = key.lower().strip()
            val = self.clean_text(val)
            if not val:
                continue

            if any(k in key_lower for k in ("activity", "permit #", "permit no", "permit number", "number")):
                permit_number = val
            elif key_lower in ("type", "permit type", "activity type"):
                permit_type = val
            elif key_lower == "status":
                status = val
            elif any(k in key_lower for k in ("address", "site", "location")):
                address = val
            elif any(k in key_lower for k in ("description", "scope", "work")):
                description = val

        if not permit_number:
            for key in sorted(row.keys()):
                val = self.clean_text(row[key])
                if val and re.match(r'^[A-Z]{2,4}\d{2}-\d+', val):
                    permit_number = val
                    break

        if not permit_number and "_link_text" in row:
            link_text = row["_link_text"].strip()
            if re.match(r'^[A-Z]{2,4}\d{2}-\d+', link_text):
                permit_number = link_text

        if not permit_number:
            return None

        return {
            "permit_number": permit_number,
            "type": permit_type,
            "status": status,
            "address": address,
            "description": description,
        }

    async def _navigate_to_permit(self, page: CDPPage, permit_number: str):
        """Navigate directly to a permit detail page."""
        await self._rate_limit()
        url = f"{SEARCH_URL}?ActivityNo={permit_number}"
        logger.info(f"Navigating to permit detail: {url}")
        await page.goto(url)
        await page.wait(1000)
        await self._wait_for_ajax(page)

    async def _click_permit_in_grid(self, page: CDPPage, permit_number: str) -> bool:
        """Click a permit number link in the search results grid."""
        return bool(await page.evaluate(f"""
            (() => {{
                const pn = {repr(permit_number)};
                // Try clicking a link with the permit number text
                for (const a of document.querySelectorAll('a')) {{
                    if (a.textContent.trim().includes(pn)) {{
                        a.click();
                        return true;
                    }}
                }}
                // Try clicking a row containing the permit number
                for (const tr of document.querySelectorAll('tr')) {{
                    if (tr.textContent.includes(pn)) {{
                        const link = tr.querySelector('a');
                        if (link) {{ link.click(); return true; }}
                        tr.click();
                        return true;
                    }}
                }}
                return false;
            }})()
        """))

    # ---- Tab Content Extraction ----

    async def _extract_permit_info(self, page: CDPPage) -> dict:
        await self._click_tab(page, "Permit Info")

        for sel in [
            "[id*='RadMultiPageSearch'] [id*='pagePermitInfo']",
            "[id*='RadMultiPage'] .rmpPage",
            "[id*='pnlPermitInfo']",
            "[id*='PermitInfo']",
        ]:
            pairs = await self._extract_label_value_pairs(page, sel)
            if pairs:
                return pairs

        return await self._extract_visible_content(page)

    async def _extract_site_info(self, page: CDPPage) -> dict:
        await self._click_tab(page, "Site Info")
        await page.wait(500)

        for sel in ["[id*='pageSiteInfo']", "[id*='SiteInfo']", ".RadMultiPage > div"]:
            pairs = await self._extract_label_value_pairs(page, sel)
            if pairs:
                return pairs

        return await self._extract_visible_content(page)

    async def _extract_contacts(self, page: CDPPage) -> list[dict]:
        await self._click_tab(page, "Contacts")
        await page.wait(500)

        for sel in ["[id*='Contacts'] table", "[id*='pageContacts'] table", "[id*='rgContacts']"]:
            rows = await self._extract_table_rows(page, sel)
            if rows:
                return rows

        pairs = await self._extract_visible_content(page)
        return [pairs] if pairs else []

    async def _extract_fees(self, page: CDPPage) -> list[dict]:
        await self._click_tab(page, "Fees")
        await page.wait(500)

        for sel in ["[id*='Fees'] table", "[id*='pageFees'] table", "[id*='rgFees']"]:
            rows = await self._extract_table_rows(page, sel)
            if rows:
                return rows
        return []

    async def _extract_inspections(self, page: CDPPage) -> list[dict]:
        await self._click_tab(page, "Inspections")
        await page.wait(500)

        for sel in [
            "[id*='Inspections'] table",
            "[id*='pageInspections'] table",
            "[id*='rgInspections']",
            "[id*='Inspection'] .RadGrid table",
        ]:
            rows = await self._extract_table_rows(page, sel)
            if rows:
                inspections = []
                for row in rows:
                    normalized = self._normalize_inspection(row)
                    if normalized:
                        inspections.append(normalized)
                return inspections
        return []

    async def _extract_chronology(self, page: CDPPage) -> list[dict]:
        await self._click_tab(page, "Chronology")
        await page.wait(500)

        for sel in [
            "[id*='Chronology'] table",
            "[id*='pageChronology'] table",
            "[id*='rgChronology']",
            "[id*='Chronolog'] .RadGrid table",
        ]:
            rows = await self._extract_table_rows(page, sel)
            if rows:
                entries = []
                for row in rows:
                    entry = self._normalize_chronology_entry(row)
                    if entry:
                        entries.append(entry)
                return entries
        return []

    async def _extract_conditions(self, page: CDPPage) -> list[dict]:
        await self._click_tab(page, "Conditions")
        await page.wait(500)

        for sel in ["[id*='Conditions'] table", "[id*='pageConditions'] table", "[id*='rgConditions']"]:
            rows = await self._extract_table_rows(page, sel)
            if rows:
                return rows
        return []

    async def _extract_reviews(self, page: CDPPage) -> list[dict]:
        await self._click_tab(page, "Reviews")
        await page.wait(500)

        for sel in [
            "[id*='Reviews'] table",
            "[id*='pageReviews'] table",
            "[id*='rgReviews']",
            "[id*='Review'] .RadGrid table",
        ]:
            rows = await self._extract_table_rows(page, sel)
            if rows:
                reviews = []
                for row in rows:
                    review = self._normalize_review(row)
                    if review:
                        reviews.append(review)
                return reviews
        return []

    async def _extract_visible_content(self, page: CDPPage) -> dict:
        """Extract label-value content from the currently active tab."""
        return await page.evaluate("""
            (() => {
                const result = {};
                const panels = document.querySelectorAll('.rmpPage');
                let activePanel = null;
                for (const p of panels) {
                    if (p.offsetParent !== null || p.style.display !== 'none') {
                        activePanel = p;
                        break;
                    }
                }
                if (!activePanel) activePanel = document;

                for (const table of activePanel.querySelectorAll('table')) {
                    for (const tr of table.querySelectorAll('tr')) {
                        const cells = tr.querySelectorAll('td, th');
                        if (cells.length >= 2) {
                            const key = cells[0].innerText.replace(/:$/, '').trim();
                            const val = cells[1].innerText.trim();
                            if (key && val && key.length < 100 && val.length < 1000) {
                                result[key] = val;
                            }
                        }
                    }
                }

                for (const label of activePanel.querySelectorAll('[class*="Label"], [class*="label"], b, strong')) {
                    const key = label.innerText.replace(/:$/, '').trim();
                    if (key && key.length < 100) {
                        const sibling = label.nextElementSibling || label.parentElement?.nextElementSibling;
                        if (sibling) {
                            const val = sibling.innerText.trim();
                            if (val && val.length < 1000) result[key] = val;
                        }
                    }
                }

                return result;
            })()
        """) or {}

    # ---- Result Normalizers ----

    def _normalize_inspection(self, row: dict) -> Optional[dict]:
        if not row:
            return None

        inspection = {
            "date": "", "type": "", "result": "", "inspector": "",
            "comments": "", "status": "", "requested_date": "", "scheduled_date": "",
        }

        for key, val in row.items():
            key_lower = key.lower().strip()
            val = self.clean_text(val)
            if not val:
                continue

            if any(k in key_lower for k in ("date", "inspdate", "insp date")) and "request" not in key_lower and "schedule" not in key_lower:
                inspection["date"] = val
            elif any(k in key_lower for k in ("type", "inspection type", "insp type")):
                inspection["type"] = val
            elif any(k in key_lower for k in ("result", "outcome")):
                inspection["result"] = val
            elif any(k in key_lower for k in ("inspector", "performed by", "inspected by")):
                inspection["inspector"] = val
            elif any(k in key_lower for k in ("comment", "note", "remark")):
                inspection["comments"] = val
            elif key_lower == "status":
                inspection["status"] = val
            elif "request" in key_lower:
                inspection["requested_date"] = val
            elif "schedule" in key_lower:
                inspection["scheduled_date"] = val

        if not inspection["type"] and not inspection["date"]:
            return None
        return inspection

    def _normalize_chronology_entry(self, row: dict) -> Optional[dict]:
        if not row:
            return None

        entry = {"date": "", "type": "", "comment": "", "reviewer": "", "status": ""}

        for key, val in row.items():
            key_lower = key.lower().strip()
            val = self.clean_text(val)
            if not val:
                continue

            if "date" in key_lower:
                entry["date"] = val
            elif any(k in key_lower for k in ("type", "action", "activity")):
                entry["type"] = val
            elif any(k in key_lower for k in ("comment", "note", "description", "remark", "text")):
                entry["comment"] = val
            elif any(k in key_lower for k in ("reviewer", "user", "by", "name")):
                entry["reviewer"] = val
            elif key_lower == "status":
                entry["status"] = val

        if not entry["date"] and not entry["comment"]:
            return None
        return entry

    def _normalize_review(self, row: dict) -> Optional[dict]:
        if not row:
            return None

        review = {"date": "", "discipline": "", "reviewer": "", "status": "", "cycle": "", "comments": ""}

        for key, val in row.items():
            key_lower = key.lower().strip()
            val = self.clean_text(val)
            if not val:
                continue

            if "date" in key_lower:
                review["date"] = val
            elif any(k in key_lower for k in ("discipline", "department", "division", "review type")):
                review["discipline"] = val
            elif any(k in key_lower for k in ("reviewer", "reviewed by", "examiner")):
                review["reviewer"] = val
            elif key_lower == "status" or "result" in key_lower:
                review["status"] = val
            elif "cycle" in key_lower:
                review["cycle"] = val
            elif any(k in key_lower for k in ("comment", "note", "remark")):
                review["comments"] = val

        if not review["discipline"] and not review["date"]:
            return None
        return review

    # ---- Public Interface ----

    async def search_permits(self, query: str, search_type: str = "address") -> list[dict]:
        page = await self._new_page()
        try:
            await self._navigate_to_search(page)

            success = await self._perform_search(page, query, search_type)
            if not success:
                logger.warning("Search submission may have failed")
                return []

            await page.wait(2000)

            no_results = await page.evaluate("""
                (() => {
                    const body = document.body.innerText;
                    return body.includes('No records found') ||
                           body.includes('0 records') ||
                           body.includes('No results') ||
                           body.includes('no matching');
                })()
            """)
            if no_results:
                logger.info("Search returned no results")
                return []

            results = await self._extract_search_results(page)

            # Check for pagination
            has_more = await page.evaluate("""
                (() => {
                    const btn = document.querySelector(
                        "input[value*='More'], a:has-text('More Results'), " +
                        "input[id*='btnMore'], a[id*='btnMore']"
                    );
                    return btn !== null && btn.offsetParent !== null;
                })()
            """)
            if has_more and results:
                logger.info("More results available (pagination)")
                grid_sel = "[id*='rgSearchRslts'], .RadGrid"
                additional = await self._get_all_grid_pages(page, grid_sel)
                seen = {r["permit_number"] for r in results}
                for row in additional:
                    normalized = self._normalize_search_result(row)
                    if normalized and normalized["permit_number"] not in seen:
                        results.append(normalized)
                        seen.add(normalized["permit_number"])

            logger.info(f"Found {len(results)} permit(s)")
            return results

        except CDPError as e:
            logger.error(f"Error searching permits: {e}")
            return []
        finally:
            await page.close()

    async def get_permit_details(self, permit_number: str) -> dict:
        permit_number = self.normalize_permit_number(permit_number)
        page = await self._new_page()

        details = {
            "permit_number": permit_number,
            "city": "coral-springs",
            "permit_info": {},
            "site_info": {},
            "contacts": [],
            "fees": [],
            "inspections": [],
            "chronology": [],
            "conditions": [],
            "reviews": [],
            "error": None,
        }

        try:
            await self._navigate_to_permit(page, permit_number)

            page_text = await page.get_text("body")
            if "not found" in page_text.lower() or "no records" in page_text.lower():
                details["error"] = f"Permit {permit_number} not found"
                return details

            # Check if we're on a search results page
            is_search_page = await page.evaluate("""
                (() => {
                    const grid = document.querySelector('[id*="rgSearchRslts"]');
                    const tabs = document.querySelector('[id*="tcSearchDetails"]');
                    return grid !== null && (tabs === null || tabs.style.display === 'none');
                })()
            """)

            if is_search_page:
                clicked = await self._click_permit_in_grid(page, permit_number)
                if not clicked:
                    await self._navigate_to_search(page)
                    success = await self._perform_search(page, permit_number, "permit_number")
                    if success:
                        await page.wait(1000)
                        clicked = await self._click_permit_in_grid(page, permit_number)
                    if not clicked:
                        details["error"] = f"Could not navigate to permit {permit_number}"
                        return details
                await page.wait(1000)
                await self._wait_for_ajax(page)

            logger.info(f"Extracting details for permit {permit_number}")

            try:
                details["permit_info"] = await self._extract_permit_info(page)
            except Exception as e:
                logger.warning(f"Error extracting Permit Info: {e}")

            await self._rate_limit()

            try:
                details["site_info"] = await self._extract_site_info(page)
            except Exception as e:
                logger.warning(f"Error extracting Site Info: {e}")

            await self._rate_limit()

            try:
                details["contacts"] = await self._extract_contacts(page)
            except Exception as e:
                logger.warning(f"Error extracting Contacts: {e}")

            await self._rate_limit()

            try:
                details["fees"] = await self._extract_fees(page)
            except Exception as e:
                logger.warning(f"Error extracting Fees: {e}")

            await self._rate_limit()

            try:
                details["inspections"] = await self._extract_inspections(page)
            except Exception as e:
                logger.warning(f"Error extracting Inspections: {e}")

            await self._rate_limit()

            try:
                details["chronology"] = await self._extract_chronology(page)
            except Exception as e:
                logger.warning(f"Error extracting Chronology: {e}")

            await self._rate_limit()

            try:
                details["conditions"] = await self._extract_conditions(page)
            except Exception as e:
                logger.warning(f"Error extracting Conditions: {e}")

            await self._rate_limit()

            try:
                details["reviews"] = await self._extract_reviews(page)
            except Exception as e:
                logger.warning(f"Error extracting Reviews: {e}")

            return details

        except CDPError as e:
            details["error"] = f"Error loading permit {permit_number}: {str(e)}"
            logger.error(f"Error getting permit details: {e}")
            return details
        finally:
            await page.close()

    async def get_permit_inspections(self, permit_number: str) -> list[dict]:
        permit_number = self.normalize_permit_number(permit_number)
        page = await self._new_page()

        try:
            await self._navigate_to_permit(page, permit_number)

            is_search_page = await page.evaluate("""
                (() => document.querySelector('[id*="rgSearchRslts"]') !== null)()
            """)
            if is_search_page:
                clicked = await self._click_permit_in_grid(page, permit_number)
                if not clicked:
                    return []
                await page.wait(1000)
                await self._wait_for_ajax(page)

            return await self._extract_inspections(page)

        except Exception as e:
            logger.error(f"Error getting inspections for {permit_number}: {e}")
            return []
        finally:
            await page.close()

    async def get_permit_comments(self, permit_number: str) -> list[dict]:
        permit_number = self.normalize_permit_number(permit_number)
        page = await self._new_page()

        try:
            await self._navigate_to_permit(page, permit_number)

            is_search_page = await page.evaluate("""
                (() => document.querySelector('[id*="rgSearchRslts"]') !== null)()
            """)
            if is_search_page:
                clicked = await self._click_permit_in_grid(page, permit_number)
                if not clicked:
                    return []
                await page.wait(1000)
                await self._wait_for_ajax(page)

            chronology = await self._extract_chronology(page)
            reviews = await self._extract_reviews(page)

            all_comments = []
            for entry in chronology:
                entry["source"] = "chronology"
                all_comments.append(entry)
            for entry in reviews:
                entry["source"] = "review"
                all_comments.append(entry)

            return all_comments

        except Exception as e:
            logger.error(f"Error getting comments for {permit_number}: {e}")
            return []
        finally:
            await page.close()

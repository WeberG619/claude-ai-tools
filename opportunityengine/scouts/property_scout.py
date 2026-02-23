"""PropertyScout - Local lead generation from public permit & property data.

Scans South Florida building permit portals and property records
to find new construction projects, recent property sales, and
renovation candidates that might need BIM/architectural services.

Data sources (via existing MCP tools, run as subprocesses):
  - etrakit-mcp: New commercial/mixed-use building permits (Broward County)
  - property-appraiser-mcp: Recent property sales (new owners = renovation candidates)
  - govdata-mcp: Code violations, zoning data

Focus: Broward + Miami-Dade counties, commercial/multi-family >$100K.
Scan interval: every 6 hours (permits don't change fast).
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False


def _run_ps(cmd, timeout=30):
    if _HAS_BRIDGE:
        return _ps_bridge(cmd, timeout)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, timeout=timeout)
    class _R:
        stdout = r.stdout; stderr = r.stderr; returncode = r.returncode; success = r.returncode == 0
    return _R()


from scouts.base_scout import BaseScout
from core.database import Database
from core.models import Opportunity, CompetitionLevel
from core.config import (
    PROPERTY_SEARCH_CITIES, PROPERTY_SEARCH_COUNTIES,
    PROPERTY_PERMIT_TYPES, PROPERTY_MIN_VALUE,
)

logger = logging.getLogger("opportunityengine.scouts.property")


class PropertyScout(BaseScout):
    """Scans local permit portals and property records for leads."""

    def __init__(self, db: Database):
        super().__init__(db)

    @property
    def source_name(self) -> str:
        return "property"

    def _fetch_opportunities(self) -> list[Opportunity]:
        opportunities = []

        # 1. Scan building permits (etrakit)
        opportunities.extend(self._scan_permits())

        # 2. Scan recent property sales
        opportunities.extend(self._scan_sales())

        # Dedup within batch
        seen = set()
        unique = []
        for opp in opportunities:
            if opp.source_id not in seen:
                seen.add(opp.source_id)
                unique.append(opp)

        return unique

    def _scan_permits(self) -> list[Opportunity]:
        """Scan eTRAKiT permit portals for new commercial permits."""
        opportunities = []

        for city in PROPERTY_SEARCH_CITIES:
            for permit_type in PROPERTY_PERMIT_TYPES:
                try:
                    # Run the etrakit search via Python subprocess
                    # (MCP tools are CDP-based, need Windows Python)
                    script = f"""
import sys, json
sys.path.insert(0, r'D:\\_CLAUDE-TOOLS\\etrakit-mcp')
from scrapers.coral_springs import CoralSpringsScraper
from cache import PermitCache

cache = PermitCache()
scraper = CoralSpringsScraper()
try:
    results = scraper.search_permits('{permit_type}', max_results=10)
    print(json.dumps(results, default=str))
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
"""
                    cmd = f"cd 'D:\\_CLAUDE-TOOLS\\etrakit-mcp'; python -c \"{script.strip()}\" 2>$null"
                    result = _run_ps(cmd, timeout=60)

                    stdout = result.stdout.strip() if result.stdout else ""
                    if not stdout:
                        continue

                    json_start = stdout.find("[")
                    if json_start == -1:
                        json_start = stdout.find("{")
                    if json_start == -1:
                        continue

                    data = json.loads(stdout[json_start:])
                    if isinstance(data, dict) and data.get("error"):
                        logger.warning(f"Permit search error for {city}/{permit_type}: {data['error']}")
                        continue

                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        opp = self._permit_to_opportunity(item, city, permit_type)
                        if opp:
                            opportunities.append(opp)

                except subprocess.TimeoutExpired:
                    logger.warning(f"Permit search timed out for {city}/{permit_type}")
                except Exception as e:
                    logger.error(f"Permit search error for {city}/{permit_type}: {e}")

        return opportunities

    def _scan_sales(self) -> list[Opportunity]:
        """Scan property appraiser for recent commercial sales."""
        opportunities = []

        for county in PROPERTY_SEARCH_COUNTIES:
            try:
                # Use property-appraiser-mcp scraper
                scraper_class = "BCPAScraper" if county == "broward" else "MDCPAScraper"
                module = "bcpa_scraper" if county == "broward" else "mdcpa_scraper"

                script = f"""
import sys, json
sys.path.insert(0, r'D:\\_CLAUDE-TOOLS\\property-appraiser-mcp')
from scrapers.{module} import {scraper_class}

scraper = {scraper_class}()
try:
    results = scraper.search_recent_sales(property_type='commercial', max_results=10)
    print(json.dumps(results, default=str))
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
"""
                cmd = f"cd 'D:\\_CLAUDE-TOOLS\\property-appraiser-mcp'; python -c \"{script.strip()}\" 2>$null"
                result = _run_ps(cmd, timeout=60)

                stdout = result.stdout.strip() if result.stdout else ""
                if not stdout:
                    continue

                json_start = stdout.find("[")
                if json_start == -1:
                    json_start = stdout.find("{")
                if json_start == -1:
                    continue

                data = json.loads(stdout[json_start:])
                if isinstance(data, dict) and data.get("error"):
                    logger.warning(f"Sales search error for {county}: {data['error']}")
                    continue

                items = data if isinstance(data, list) else [data]
                for item in items:
                    opp = self._sale_to_opportunity(item, county)
                    if opp:
                        opportunities.append(opp)

            except subprocess.TimeoutExpired:
                logger.warning(f"Sales search timed out for {county}")
            except Exception as e:
                logger.error(f"Sales search error for {county}: {e}")

        return opportunities

    def _permit_to_opportunity(self, item: dict, city: str, permit_type: str) -> Optional[Opportunity]:
        """Convert a permit record to an Opportunity."""
        permit_num = item.get("permit_number", item.get("number", ""))
        address = item.get("address", item.get("project_address", ""))
        description = item.get("description", item.get("work_description", ""))
        value = item.get("value", item.get("construction_value", 0))

        if not permit_num and not address:
            return None

        # Filter: only commercial/multi-family above minimum value
        try:
            numeric_value = float(str(value).replace("$", "").replace(",", ""))
        except (ValueError, TypeError):
            numeric_value = 0

        if numeric_value > 0 and numeric_value < PROPERTY_MIN_VALUE:
            return None

        title = f"New Permit: {permit_type} - {address or permit_num}"
        desc = (
            f"Building permit filed in {city}.\n"
            f"Permit: {permit_num}\n"
            f"Type: {permit_type}\n"
            f"Address: {address}\n"
            f"Description: {description}\n"
            f"Construction Value: ${numeric_value:,.0f}\n\n"
            f"Potential BIM/CD services opportunity for new construction project."
        )

        return Opportunity(
            source="property",
            source_id=f"permit/{city}/{permit_num}",
            title=title[:200],
            description=desc,
            budget_min=numeric_value * 0.02 if numeric_value else None,  # ~2% of construction value
            budget_max=numeric_value * 0.05 if numeric_value else None,  # ~5% of construction value
            currency="USD",
            skills_required=["revit", "bim", "construction_documents", "architecture"],
            competition_level=CompetitionLevel.LOW,  # Local permits = less competitive
            client_info={
                "city": city,
                "permit_type": permit_type,
                "construction_value": numeric_value,
                "address": address,
            },
            raw_data=item,
        )

    def _sale_to_opportunity(self, item: dict, county: str) -> Optional[Opportunity]:
        """Convert a property sale record to an Opportunity."""
        folio = item.get("folio", item.get("folio_number", ""))
        address = item.get("address", item.get("site_address", ""))
        sale_price = item.get("sale_price", item.get("price", 0))
        owner = item.get("owner", item.get("new_owner", ""))

        if not folio and not address:
            return None

        try:
            numeric_price = float(str(sale_price).replace("$", "").replace(",", ""))
        except (ValueError, TypeError):
            numeric_price = 0

        if numeric_price > 0 and numeric_price < PROPERTY_MIN_VALUE:
            return None

        title = f"Recent Sale: {address or folio} (${numeric_price:,.0f})"
        desc = (
            f"Commercial property recently sold in {county.title()} County.\n"
            f"Address: {address}\n"
            f"Folio: {folio}\n"
            f"Sale Price: ${numeric_price:,.0f}\n"
            f"New Owner: {owner}\n\n"
            f"New owners often renovate. Potential BIM/architectural services lead."
        )

        return Opportunity(
            source="property",
            source_id=f"sale/{county}/{folio}",
            title=title[:200],
            description=desc,
            budget_min=numeric_price * 0.01 if numeric_price else None,
            budget_max=numeric_price * 0.03 if numeric_price else None,
            currency="USD",
            skills_required=["revit", "bim", "construction_documents", "architecture"],
            competition_level=CompetitionLevel.LOW,
            client_info={
                "county": county,
                "sale_price": numeric_price,
                "address": address,
                "owner": owner,
            },
            raw_data=item,
        )

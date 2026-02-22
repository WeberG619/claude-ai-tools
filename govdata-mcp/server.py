#!/usr/bin/env python3
"""
Government Data MCP Server - Building Permits, Code Violations, Zoning & More

Data Sources:
- ArcGIS Open Data (Miami-Dade, Palm Beach, Pinellas, Jacksonville, Portland, Atlanta, FL state)
- Socrata SODA API (SF, NYC, Chicago, LA, Orlando, Houston, Dallas, Austin, Seattle, Denver, Phoenix, Philadelphia, Boston, DC)
- Reference portals (Broward, Coral Springs, Hillsborough, FL DBPR)
- Census Bureau Building Permits Survey (aggregate statistics)
- OSHA Enforcement Data (construction inspections)
- Building Code Reference (IBC 2021, IRC 2021, FBC 2023, FBC Residential 2023)

Tools:
1. search_permits - Search building permits by address, type, status
2. get_permit_details - Get full details for a specific permit
3. search_code_violations - Search code violations by address
4. lookup_zoning - Look up zoning for an address
5. search_contractors - Search licensed contractors
6. get_building_permits_stats - Aggregate permit statistics
7. search_osha_inspections - OSHA construction inspections
8. lookup_building_code - IBC/IRC/FBC code section reference
9. list_jurisdictions - List all supported jurisdictions with filtering
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import asyncio

# MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

import requests

# Paths
SCRIPT_DIR = Path(__file__).parent
JURISDICTIONS_FILE = SCRIPT_DIR / "jurisdictions.json"
BUILDING_CODES_DIR = SCRIPT_DIR / "building_codes"

# Mapping from edition names to JSON files
BUILDING_CODE_FILES = {
    "2021 IBC": "ibc_2021.json",
    "2021 IRC": "irc_2021.json",
    "2023 FBC": "fbc_2023.json",
    "2023 FBC Residential": "fbc_residential_2023.json",
}

# Cache for loaded building code JSON files
_building_code_cache: dict[str, dict] = {}

# API Keys (optional, from environment)
CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "")
SOCRATA_APP_TOKEN = os.environ.get("SOCRATA_APP_TOKEN", "")

# Initialize MCP server
server = Server("govdata-mcp")

# Cache for API calls (government data doesn't change fast)
_cache: dict[str, tuple[Any, float]] = {}
CACHE_DURATION = 1800  # 30 minutes


# ============== UTILITIES ==============

def get_cached(key: str, fetch_func, duration: int = CACHE_DURATION):
    """Simple cache to avoid hammering government APIs."""
    now = datetime.now().timestamp()
    if key in _cache:
        data, timestamp = _cache[key]
        if now - timestamp < duration:
            return data
    try:
        data = fetch_func()
    except Exception as e:
        # If cache exists but is expired, return stale data on error
        if key in _cache:
            data, _ = _cache[key]
            return data
        raise
    _cache[key] = (data, now)
    return data


def load_jurisdictions() -> dict:
    """Load jurisdiction configuration."""
    if JURISDICTIONS_FILE.exists():
        with open(JURISDICTIONS_FILE) as f:
            return json.load(f)
    return {}


def safe_request(url: str, params: dict = None, timeout: int = 30,
                 headers: dict = None) -> requests.Response:
    """Make HTTP request with defensive error handling for government APIs."""
    default_headers = {
        "User-Agent": "GovData-MCP/1.0 (Research Tool)",
        "Accept": "application/json",
    }
    if headers:
        default_headers.update(headers)

    try:
        resp = requests.get(url, params=params, headers=default_headers,
                            timeout=timeout)
        # Government APIs sometimes return HTML error pages with 200 status
        content_type = resp.headers.get("Content-Type", "")
        if resp.status_code == 200 and "text/html" in content_type:
            # Check if it's actually JSON wrapped in HTML
            text = resp.text.strip()
            if text.startswith("{") or text.startswith("["):
                return resp
            raise ValueError(
                f"API returned HTML instead of JSON. "
                f"The endpoint may be down or require authentication."
            )
        resp.raise_for_status()
        return resp
    except requests.exceptions.Timeout:
        raise TimeoutError(
            f"Government API timed out after {timeout}s. "
            f"These services can be slow; try again shortly."
        )
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            f"Could not connect to government API at {url}. "
            f"The service may be temporarily unavailable."
        )


def format_epoch_date(value) -> str:
    """Convert epoch milliseconds to readable date string, or return as-is."""
    if value is None:
        return ""
    if isinstance(value, (int, float)) and value > 1000000000:
        try:
            dt = datetime.fromtimestamp(value / 1000)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, OSError):
            pass
    return str(value).strip()


def format_permit(permit: dict, jurisdiction: str) -> str:
    """Format a single permit record for display."""
    lines = []
    # Try common field names across different platforms
    # MDC uses: PROCNUM, ADDRESS/STNDADDR, TYPE, BPSTATUS, ISSUDATE, DESC1, ESTVALUE, CONTRNAME, CONTRNUM
    permit_num = (permit.get("permit_number") or permit.get("PERMIT_NUM")
                  or permit.get("permit_no") or permit.get("PERMITNUMBER")
                  or permit.get("application_number") or permit.get("JOB_NUMBER")
                  or permit.get("PROCNUM")  # Miami-Dade
                  or permit.get("OBJECTID", "N/A"))
    address = (permit.get("address") or permit.get("ADDRESS")
               or permit.get("street_address") or permit.get("SITE_ADDRESS")
               or permit.get("STNDADDR")  # Miami-Dade standardized address
               or permit.get("location") or permit.get("LOCATION", "N/A"))
    permit_type = (permit.get("permit_type") or permit.get("PERMIT_TYPE")
                   or permit.get("type") or permit.get("WORK_TYPE")
                   or permit.get("TYPE")  # Miami-Dade
                   or permit.get("permit_type_definition", "N/A"))
    status = (permit.get("status") or permit.get("STATUS")
              or permit.get("current_status") or permit.get("PERMIT_STATUS")
              or permit.get("BPSTATUS")  # Miami-Dade
              or permit.get("status_current", "N/A"))
    issued = (permit.get("issue_date") or permit.get("ISSUE_DATE")
              or permit.get("issued_date") or permit.get("ISSUEDDATE")
              or permit.get("ISSUDATE")  # Miami-Dade (epoch ms)
              or permit.get("filed_date", ""))
    description = (permit.get("description") or permit.get("DESCRIPTION")
                   or permit.get("work_description")
                   or permit.get("JOB_DESCRIPTION")
                   or permit.get("DESC1")  # Miami-Dade primary description
                   or "")
    contractor = (permit.get("contractor") or permit.get("CONTRACTOR_NAME")
                  or permit.get("contractor_name")
                  or permit.get("CONTRNAME")  # Miami-Dade
                  or "")
    value = (permit.get("estimated_cost") or permit.get("ESTIMATED_COST")
             or permit.get("project_value") or permit.get("TOTAL_FEE")
             or permit.get("ESTVALUE")  # Miami-Dade
             or "")

    # MDC-specific extras
    folio = permit.get("FOLIO", "")
    contractor_num = permit.get("CONTRNUM", "")
    app_type = permit.get("APPTYPE", "")
    prop_use = permit.get("PROPUSE", "")

    # Format epoch dates
    issued = format_epoch_date(issued)

    # Clean up MDC estimated value (strip leading zeros)
    if isinstance(value, str) and value.isdigit():
        value = str(int(value))

    # Decode MDC status codes
    mdc_status_map = {
        "A": "Active",
        "C": "Closed/Complete",
        "E": "Expired",
        "F": "Finaled",
        "I": "In Review",
        "P": "Pending",
        "V": "Void",
    }
    if status in mdc_status_map:
        status = f"{mdc_status_map[status]} ({status})"

    lines.append(f"  Permit #: {permit_num}")
    lines.append(f"  Address: {address}")
    lines.append(f"  Type: {permit_type}")
    lines.append(f"  Status: {status}")
    if issued:
        lines.append(f"  Issued: {issued}")
    if description:
        lines.append(f"  Description: {str(description)[:200].strip()}")
    if contractor:
        contractor_str = str(contractor).strip()
        if contractor_num:
            contractor_str += f" (Lic# {str(contractor_num).strip()})"
        lines.append(f"  Contractor: {contractor_str}")
    if value and str(value) != "0":
        lines.append(f"  Estimated Cost: ${value}")
    if folio:
        lines.append(f"  Folio: {folio}")
    if app_type:
        lines.append(f"  Application Type: {app_type}")
    if prop_use:
        lines.append(f"  Property Use: {prop_use}")
    return "\n".join(lines)


def format_violation(violation: dict) -> str:
    """Format a single violation record for display."""
    lines = []
    # MDC BuildingViolation_gdb uses: CASE_NUM, CASE_TYPE, PROP_ADDR, OPEN_DATE, CLOSED_DATE, VIOL_NAME
    # MDC EnergovCodeCase uses: CASENUMBER, TYPE, STATUS, ADDRESSLINE1, OPENEDDATE, CLOSEDDATE, DESCRIPTION
    # MDC CodeCompliance uses: CASE_NUM, CASE_DATE, CASE_STATUS, ADDRESS, PROBLEM, PROBLEM_DESC
    case_num = (violation.get("case_number") or violation.get("CASE_NUMBER")
                or violation.get("case_no")
                or violation.get("CASE_NUM")  # MDC violations & code compliance
                or violation.get("CASENUMBER")  # MDC Energov
                or violation.get("OBJECTID", "N/A"))
    address = (violation.get("address") or violation.get("ADDRESS")
               or violation.get("violation_address")
               or violation.get("PROP_ADDR")  # MDC BuildingViolation
               or violation.get("ADDRESSLINE1")  # MDC Energov
               or violation.get("LOCATION", "N/A"))
    vtype = (violation.get("violation_type") or violation.get("VIOLATION_TYPE")
             or violation.get("type") or violation.get("TYPE")
             or violation.get("CASE_TYPE")  # MDC violations
             or violation.get("PROBLEM")  # MDC code compliance
             or "N/A")
    status = (violation.get("status") or violation.get("STATUS")
              or violation.get("case_status")
              or violation.get("CASE_STATUS")  # MDC code compliance
              or violation.get("STAT_DESC")  # MDC code compliance description
              or "N/A")
    date = (violation.get("date") or violation.get("DATE")
            or violation.get("violation_date")
            or violation.get("OPENED_DATE")
            or violation.get("OPENEDDATE")  # MDC Energov
            or violation.get("OPEN_DATE")  # MDC BuildingViolation
            or violation.get("CASE_DATE")  # MDC code compliance
            or "")
    closed_date = (violation.get("CLOSED_DATE")
                   or violation.get("CLOSEDDATE")
                   or violation.get("closed_date", ""))
    description = (violation.get("description") or violation.get("DESCRIPTION")
                   or violation.get("violation_description")
                   or violation.get("PROBLEM_DESC")  # MDC code compliance
                   or "")

    # MDC-specific extras
    owner_name = violation.get("VIOL_NAME", "")  # MDC violations owner name
    folio = (violation.get("FOLIO")
             or violation.get("PARCELNUMBER", ""))
    permit_num = violation.get("PERMIT_NUM", "")
    last_activity = violation.get("LAST_ACTV", "")
    city = violation.get("CITY", "")

    # Format epoch dates
    date = format_epoch_date(date)
    closed_date = format_epoch_date(closed_date)

    # Decode MDC status codes (code compliance uses numeric codes)
    mdc_compliance_status = {"1": "Open", "2": "Closed", "3": "Pending"}
    if status in mdc_compliance_status:
        status = mdc_compliance_status[status]

    lines.append(f"  Case #: {case_num}")
    lines.append(f"  Address: {str(address).strip()}")
    if city:
        lines[-1] += f", {city}"
    lines.append(f"  Type: {vtype}")
    lines.append(f"  Status: {status}")
    if date:
        lines.append(f"  Opened: {date}")
    if closed_date:
        lines.append(f"  Closed: {closed_date}")
    if description:
        lines.append(f"  Description: {str(description)[:200].strip()}")
    if owner_name:
        lines.append(f"  Owner/Violator: {str(owner_name).strip()}")
    if folio:
        lines.append(f"  Folio: {folio}")
    if permit_num and str(permit_num).strip():
        lines.append(f"  Related Permit: {permit_num}")
    if last_activity:
        lines.append(f"  Last Activity: {str(last_activity).strip()}")
    return "\n".join(lines)


# ============== QUERY BUILDERS ==============

def query_arcgis(endpoint_url: str, where_clause: str = "1=1",
                 out_fields: str = "*", max_records: int = 25,
                 order_by: str = "") -> list[dict]:
    """Query an ArcGIS FeatureServer/MapServer endpoint."""
    params = {
        "where": where_clause,
        "outFields": out_fields,
        "returnGeometry": "false",
        "f": "json",
        "resultRecordCount": str(max_records),
    }
    if order_by:
        params["orderByFields"] = order_by

    cache_key = f"arcgis:{endpoint_url}:{where_clause}:{max_records}"

    def fetch():
        resp = safe_request(endpoint_url, params=params)
        data = resp.json()
        if "error" in data:
            err = data["error"]
            # If order_by caused the error, retry without it
            if order_by and err.get("code") == 400:
                params_retry = dict(params)
                params_retry.pop("orderByFields", None)
                resp2 = safe_request(endpoint_url, params=params_retry)
                data2 = resp2.json()
                if "error" not in data2:
                    features = data2.get("features", [])
                    return [f.get("attributes", f) for f in features]
            raise ValueError(
                f"ArcGIS API error {err.get('code', '?')}: "
                f"{err.get('message', 'Unknown error')}"
            )
        features = data.get("features", [])
        return [f.get("attributes", f) for f in features]

    return get_cached(cache_key, fetch)


def query_socrata(endpoint_url: str, params: dict = None,
                  limit: int = 25) -> list[dict]:
    """Query a Socrata SODA API endpoint."""
    if params is None:
        params = {}
    params["$limit"] = str(limit)
    if SOCRATA_APP_TOKEN:
        params["$$app_token"] = SOCRATA_APP_TOKEN

    cache_key = f"socrata:{endpoint_url}:{json.dumps(params, sort_keys=True)}"

    def fetch():
        resp = safe_request(endpoint_url, params=params)
        return resp.json()

    return get_cached(cache_key, fetch)


def get_endpoint(jurisdiction: str, endpoint_name: str) -> dict | None:
    """Get the API endpoint config for a jurisdiction and data type."""
    jurisdictions = load_jurisdictions()
    jur = jurisdictions.get(jurisdiction)
    if not jur:
        return None
    return jur.get("endpoints", {}).get(endpoint_name)


def build_address_filter(address: str, platform: str) -> str:
    """Build an address search filter for the given platform."""
    addr = address.strip().upper()
    if platform == "arcgis":
        # ArcGIS SQL-like WHERE clause
        return f"UPPER(ADDRESS) LIKE '%{addr}%' OR UPPER(SITE_ADDRESS) LIKE '%{addr}%' OR UPPER(LOCATION) LIKE '%{addr}%'"
    elif platform == "socrata":
        # Socrata SoQL
        return f"upper(address) like '%{addr}%'"
    return ""


# ============== DATA FETCHERS ==============

def fetch_permits(jurisdiction: str, address: str = None,
                  permit_type: str = None, status: str = None,
                  date_from: str = None, date_to: str = None,
                  limit: int = 25) -> list[dict]:
    """Fetch building permits from the appropriate data source."""
    endpoint = get_endpoint(jurisdiction, "building_permits")
    if not endpoint:
        raise ValueError(
            f"No building permits endpoint configured for '{jurisdiction}'. "
            f"Supported: {list_supported_jurisdictions('building_permits')}"
        )

    jurisdictions = load_jurisdictions()
    platform = jurisdictions[jurisdiction].get("data_platform", "socrata")

    if platform == "arcgis":
        clauses = []
        # Use endpoint metadata to determine field names, with fallbacks
        addr_field = endpoint.get("address_field", "ADDRESS")
        addr_field_alt = endpoint.get("address_field_alt", "SITE_ADDRESS")
        status_field = endpoint.get("status_field", "STATUS")
        type_field = endpoint.get("type_field", "PERMIT_TYPE")
        date_field = endpoint.get("date_field", "ISSUE_DATE")

        if address:
            clauses.append(
                f"(UPPER({addr_field}) LIKE '%{address.upper()}%' OR "
                f"UPPER({addr_field_alt}) LIKE '%{address.upper()}%')"
            )
        if permit_type:
            clauses.append(
                f"UPPER({type_field}) LIKE '%{permit_type.upper()}%'"
            )
        if status:
            clauses.append(
                f"UPPER({status_field}) LIKE '%{status.upper()}%'"
            )
        if date_from:
            clauses.append(f"{date_field} >= '{date_from}'")
        if date_to:
            clauses.append(f"{date_field} <= '{date_to}'")

        where = " AND ".join(clauses) if clauses else "1=1"
        order_by = f"{date_field} DESC" if date_field else ""
        return query_arcgis(endpoint["url"], where_clause=where,
                            max_records=limit, order_by=order_by)

    elif platform == "socrata":
        params = {}
        where_parts = []
        if address:
            # Try multiple possible field names
            where_parts.append(
                f"upper(address) like '%{address.upper()}%'"
            )
        if permit_type:
            where_parts.append(
                f"upper(permit_type) like '%{permit_type.upper()}%'"
            )
        if status:
            where_parts.append(
                f"upper(status) like '%{status.upper()}%'"
            )
        if date_from:
            where_parts.append(f"issued_date >= '{date_from}'")
        if date_to:
            where_parts.append(f"issued_date <= '{date_to}'")

        if where_parts:
            params["$where"] = " AND ".join(where_parts)
        params["$order"] = "issued_date DESC"
        return query_socrata(endpoint["url"], params=params, limit=limit)

    elif platform == "reference":
        return format_reference_response(jurisdiction, endpoint, address)

    else:
        raise ValueError(f"Unknown platform type: {platform}")


def fetch_violations(jurisdiction: str, address: str = None,
                     violation_type: str = None, status: str = None,
                     limit: int = 25) -> list[dict]:
    """Fetch code violations from the appropriate data source."""
    endpoint = get_endpoint(jurisdiction, "building_violations")
    if not endpoint:
        raise ValueError(
            f"No violations endpoint configured for '{jurisdiction}'. "
            f"Supported: {list_supported_jurisdictions('building_violations')}"
        )

    jurisdictions = load_jurisdictions()
    platform = jurisdictions[jurisdiction].get("data_platform", "socrata")

    if platform == "arcgis":
        clauses = []
        # Use endpoint metadata to determine field names, with fallbacks
        addr_field = endpoint.get("address_field", "ADDRESS")
        type_field = endpoint.get("type_field", "CASE_TYPE")
        status_field = endpoint.get("status_field", "STATUS")
        date_field = endpoint.get("date_field", "OPEN_DATE")

        if address:
            # Use the configured address field; only add fallbacks if
            # key_fields metadata lists them (avoids querying non-existent fields)
            key_fields = endpoint.get("key_fields", [])
            addr_fields = [addr_field]
            # Add common fallback fields only if they exist in this layer
            for fallback in ["ADDRESS", "LOCATION"]:
                if fallback != addr_field and fallback in key_fields:
                    addr_fields.append(fallback)
            addr_clauses = " OR ".join(
                f"UPPER({f}) LIKE '%{address.upper()}%'" for f in addr_fields
            )
            clauses.append(f"({addr_clauses})")
        if violation_type:
            clauses.append(
                f"(UPPER({type_field}) LIKE '%{violation_type.upper()}%')"
            )
        if status:
            clauses.append(
                f"(UPPER({status_field}) LIKE '%{status.upper()}%')"
            )
        where = " AND ".join(clauses) if clauses else "1=1"
        order_by = f"{date_field} DESC" if date_field else ""
        return query_arcgis(endpoint["url"], where_clause=where,
                            max_records=limit, order_by=order_by)

    elif platform == "socrata":
        params = {}
        where_parts = []
        if address:
            where_parts.append(
                f"upper(address) like '%{address.upper()}%'"
            )
        if violation_type:
            where_parts.append(
                f"upper(violation_type) like '%{violation_type.upper()}%'"
            )
        if status:
            where_parts.append(
                f"upper(status) like '%{status.upper()}%'"
            )
        if where_parts:
            params["$where"] = " AND ".join(where_parts)
        return query_socrata(endpoint["url"], params=params, limit=limit)

    elif platform == "reference":
        return format_reference_response(jurisdiction, endpoint, address)

    else:
        raise ValueError(f"Unknown platform type: {platform}")


def fetch_zoning(jurisdiction: str, address: str = "") -> list[dict]:
    """Fetch zoning information for an address."""
    endpoint = get_endpoint(jurisdiction, "zoning")
    if not endpoint:
        raise ValueError(
            f"No zoning endpoint configured for '{jurisdiction}'. "
            f"Supported: {list_supported_jurisdictions('zoning')}"
        )

    jurisdictions = load_jurisdictions()
    platform = jurisdictions[jurisdiction].get("data_platform", "socrata")

    if platform == "arcgis":
        where = "1=1"
        if address:
            # Check endpoint key_fields to determine which fields exist
            key_fields = endpoint.get("key_fields", [])
            addr_parts = []
            # Try address-like fields
            for field in ["ADDRESS", "LOCATION", "SITE_ADDRESS"]:
                if not key_fields or field in key_fields:
                    addr_parts.append(
                        f"UPPER({field}) LIKE '%{address.upper()}%'"
                    )
            # Try description/zone fields
            for field in ["ZONE_DESC", "PZDESC", "DESCRIPTION"]:
                if not key_fields or field in key_fields:
                    addr_parts.append(
                        f"UPPER({field}) LIKE '%{address.upper()}%'"
                    )
            if addr_parts:
                where = " OR ".join(addr_parts)
            else:
                # Fallback: search PZDESC and DESCRIPTION for MDC
                where = (
                    f"UPPER(PZDESC) LIKE '%{address.upper()}%' OR "
                    f"UPPER(DESCRIPTION) LIKE '%{address.upper()}%'"
                )
        return query_arcgis(endpoint["url"], where_clause=where,
                            max_records=10)

    elif platform == "socrata":
        params = {}
        if address:
            params["$where"] = (
                f"upper(address) like '%{address.upper()}%'"
            )
        return query_socrata(endpoint["url"], params=params, limit=10)

    elif platform == "reference":
        return format_reference_response(jurisdiction, endpoint, address)

    else:
        raise ValueError(f"Unknown platform type: {platform}")


def format_reference_response(jurisdiction: str, endpoint: dict,
                              address: str = None) -> list[dict]:
    """Format a response for reference-only jurisdictions (no REST API)."""
    jur_data = load_jurisdictions().get(jurisdiction, {})
    portal_url = endpoint.get("portal_url", jur_data.get("portal_url", "N/A"))
    description = endpoint.get("description", "")
    instructions = endpoint.get("instructions", "Visit the portal URL to search.")

    result = {
        "type": "reference",
        "jurisdiction": jurisdiction,
        "jurisdiction_name": jur_data.get("name", jurisdiction),
        "portal_url": portal_url,
        "description": description,
        "instructions": instructions,
        "note": "This jurisdiction does not have a public REST API. Use the portal URL to search manually.",
    }
    if address:
        result["search_address"] = address
    if jur_data.get("building_code"):
        result["building_code"] = jur_data["building_code"]
    if jur_data.get("hvhz"):
        result["hvhz"] = "Yes - High-Velocity Hurricane Zone (Miami-Dade/Broward)"
    return [result]


def format_reference_text(ref: dict) -> str:
    """Format a reference-type response for display."""
    lines = [
        f"=== {ref.get('jurisdiction_name', ref.get('jurisdiction', 'Unknown'))} ===",
        f"Platform: Reference only (no public REST API)",
        f"Portal URL: {ref.get('portal_url', 'N/A')}",
        f"Description: {ref.get('description', 'N/A')}",
        f"Instructions: {ref.get('instructions', 'Visit the portal URL to search.')}",
    ]
    if ref.get("search_address"):
        lines.append(f"\nSearch for: {ref['search_address']}")
    if ref.get("building_code"):
        lines.append(f"Building Code: {ref['building_code']}")
    if ref.get("hvhz"):
        lines.append(f"HVHZ: {ref['hvhz']}")
    lines.append(
        "\nNote: This jurisdiction does not expose a public REST API. "
        "Visit the portal URL above to search, or use a browser automation tool."
    )
    return "\n".join(lines)


def fetch_census_permits_stats(state: str = None, period: str = "monthly",
                               year: str = None) -> dict:
    """Fetch building permit statistics from Census Bureau BPS."""
    if not CENSUS_API_KEY:
        return {
            "error": "CENSUS_API_KEY environment variable not set. "
                     "Get a free key at https://api.census.gov/data/key_signup.html"
        }

    if year is None:
        year = str(datetime.now().year - 1)  # Use previous year for complete data

    base_url = "https://api.census.gov/data/timeseries/bps"

    params = {
        "get": "PERMITS,UNITS",
        "key": CENSUS_API_KEY,
        "time": year,
    }
    if state:
        params["for"] = f"state:{state}"
    else:
        params["for"] = "us:*"

    if period == "monthly":
        params["MONTH"] = "*"  # Get all months

    cache_key = f"census_bps:{json.dumps(params, sort_keys=True)}"

    def fetch():
        resp = safe_request(base_url, params=params, timeout=45)
        return resp.json()

    return get_cached(cache_key, fetch)


def fetch_osha_inspections(company: str = None, state: str = None,
                           violation_type: str = None,
                           limit: int = 25) -> list[dict]:
    """Fetch OSHA construction inspection data."""
    # OSHA data is available via their data catalog downloads
    # We'll use the DOL enforcement data API
    base_url = "https://enforcedata.dol.gov/views/data_summary.php"

    # OSHA doesn't have a clean REST API; we simulate a search
    # and parse what we can. For production, bulk CSV downloads are better.
    params = {
        "agency": "osha",
        "tab": "inspections",
        "format": "json",
    }
    if company:
        params["estab_name"] = company
    if state:
        params["state"] = state.upper()

    cache_key = f"osha:{json.dumps(params, sort_keys=True)}"

    def fetch():
        # Try the enforcement data API
        try:
            resp = safe_request(base_url, params=params, timeout=30)
            data = resp.json()
            if isinstance(data, list):
                return data[:limit]
            return []
        except (ValueError, json.JSONDecodeError):
            # OSHA often returns HTML; fall back to a helpful message
            return [{
                "note": "OSHA enforcement data API returned non-JSON response. "
                        "For reliable access, visit: "
                        "https://www.osha.gov/data or "
                        "https://enforcedata.dol.gov/views/data_catalogs.php",
                "search_params": params
            }]

    return get_cached(cache_key, fetch)


def list_supported_jurisdictions(endpoint_type: str = None) -> list[str]:
    """List jurisdictions that support a given endpoint type."""
    jurisdictions = load_jurisdictions()
    result = []
    for key, value in jurisdictions.items():
        if key.startswith("_"):
            continue  # Skip federal/meta entries
        if endpoint_type:
            if endpoint_type in value.get("endpoints", {}):
                result.append(key)
        else:
            result.append(key)
    return result


# ============== BUILDING CODE REFERENCE ==============

def load_building_code(edition: str) -> dict | None:
    """Load building code sections from JSON file. Returns the sections dict or None."""
    if edition in _building_code_cache:
        return _building_code_cache[edition]

    filename = BUILDING_CODE_FILES.get(edition)
    if not filename:
        return None

    filepath = BUILDING_CODES_DIR / filename
    if not filepath.exists():
        return None

    with open(filepath) as f:
        data = json.load(f)

    sections = data.get("sections", {})
    _building_code_cache[edition] = sections
    return sections


def get_available_editions() -> list[str]:
    """Return list of available building code editions."""
    return list(BUILDING_CODE_FILES.keys())


def lookup_code(code_section: str = None, keyword: str = None,
                code_edition: str = "2021 IBC") -> str:
    """Look up a building code section or search by keyword."""
    code_data = load_building_code(code_edition)
    if not code_data:
        available = get_available_editions()
        return (f"Code edition '{code_edition}' not found. "
                f"Available: {', '.join(available)}")

    if code_section:
        # Direct section lookup
        # Try exact match first
        section = code_data.get(code_section)
        if section:
            return format_code_section(code_section, section, code_edition)

        # Try partial match
        matches = []
        for sec_num, sec_data in code_data.items():
            if code_section in sec_num or sec_num.startswith(code_section):
                matches.append((sec_num, sec_data))
            # Check subsections
            for sub_num in sec_data.get("subsections", {}):
                if code_section in sub_num:
                    matches.append((sec_num, sec_data))
                    break

        if matches:
            results = []
            for sec_num, sec_data in matches[:5]:
                results.append(
                    format_code_section(sec_num, sec_data, code_edition)
                )
            return "\n\n".join(results)

        return (f"Section '{code_section}' not found in {code_edition}. "
                f"Available sections: {', '.join(sorted(code_data.keys()))}")

    elif keyword:
        # Keyword search
        keyword_upper = keyword.upper()
        matches = []
        for sec_num, sec_data in code_data.items():
            searchable = json.dumps(sec_data).upper()
            if keyword_upper in searchable:
                matches.append((sec_num, sec_data))

        if matches:
            results = []
            for sec_num, sec_data in matches[:5]:
                results.append(
                    format_code_section(sec_num, sec_data, code_edition)
                )
            header = (
                f"Found {len(matches)} section(s) matching '{keyword}' "
                f"in {code_edition}:"
            )
            return header + "\n\n" + "\n\n".join(results)

        return f"No sections matching '{keyword}' found in {code_edition}."

    else:
        # Return table of contents
        lines = [f"{code_edition} - Available Sections:\n"]
        for sec_num in sorted(code_data.keys()):
            title = code_data[sec_num].get("title", "")
            lines.append(f"  Section {sec_num}: {title}")
        return "\n".join(lines)


def format_code_section(section_num: str, section_data: dict,
                        edition: str) -> str:
    """Format a building code section for display."""
    lines = [
        f"--- {edition} Section {section_num} ---",
        f"Title: {section_data.get('title', 'N/A')}",
        f"Summary: {section_data.get('summary', 'N/A')}",
    ]
    if "subsections" in section_data:
        lines.append("Subsections:")
        for sub_num, sub_desc in section_data["subsections"].items():
            lines.append(f"  {sub_num}: {sub_desc}")
    if "key_terms" in section_data:
        lines.append("Key Terms:")
        for term in section_data["key_terms"]:
            lines.append(f"  - {term}")
    lines.append(
        "\nNote: This is a simplified reference. For the full code text, "
        "consult the ICC official publication at https://codes.iccsafe.org/"
    )
    return "\n".join(lines)


# ============== CONTRACTOR SEARCH ==============

def search_contractor_data(name: str = None, license_number: str = None,
                           trade: str = None, state: str = "FL") -> str:
    """Search for contractor licensing information.

    Note: Most state licensing boards don't have public APIs.
    This returns guidance on how to search.
    """
    state_info = {
        "FL": {
            "name": "Florida Department of Business and Professional Regulation",
            "url": "https://www.myfloridalicense.com/wl11.asp",
            "verify_url": "https://www.myfloridalicense.com/wl11.asp?mode=0&SID=&bession_id=&page=1",
            "notes": "Florida requires contractor licensing for most construction work. "
                     "Search the DBPR database for license verification."
        },
        "CA": {
            "name": "California Contractors State License Board (CSLB)",
            "url": "https://www.cslb.ca.gov/onlineservices/checklicenseII/checklicense.aspx",
            "notes": "All California contractors must be licensed by the CSLB for work over $500."
        },
        "NY": {
            "name": "NYC Department of Buildings / NY DOS",
            "url": "https://www.nyc.gov/site/buildings/industry/licensing.page",
            "notes": "NYC requires specific licenses for different trades. "
                     "State registration through Department of State."
        },
        "TX": {
            "name": "Texas Department of Licensing and Regulation",
            "url": "https://www.tdlr.texas.gov/",
            "notes": "Texas does not require a general contractor license statewide, "
                     "but specialty trades (electrical, plumbing, HVAC) require licensing."
        },
        "IL": {
            "name": "Illinois Division of Professional Regulation",
            "url": "https://online-dfpr.micropact.com/lookup/licenselookup.aspx",
            "notes": "Illinois does not have a statewide general contractor license. "
                     "Individual municipalities may require licenses."
        }
    }

    info = state_info.get(state.upper())
    if not info:
        return (
            f"State '{state}' contractor licensing info not available. "
            f"Supported states: {', '.join(sorted(state_info.keys()))}.\n\n"
            f"Most states provide online license verification through their "
            f"state licensing board website."
        )

    lines = [
        f"--- Contractor Licensing: {state.upper()} ---",
        f"Agency: {info['name']}",
        f"Lookup URL: {info['url']}",
        f"Notes: {info['notes']}",
        "",
    ]

    search_terms = []
    if name:
        search_terms.append(f"Name: {name}")
    if license_number:
        search_terms.append(f"License #: {license_number}")
    if trade:
        search_terms.append(f"Trade: {trade}")

    if search_terms:
        lines.append("Search Criteria:")
        for term in search_terms:
            lines.append(f"  {term}")
        lines.append("")
        lines.append(
            "Note: Contractor license databases typically do not offer "
            "public REST APIs. Use the lookup URL above to search directly, "
            "or ask Claude to use a browser tool to search on your behalf."
        )
    else:
        lines.append(
            "Provide a contractor name, license number, or trade to search."
        )

    return "\n".join(lines)


# ============== TOOL DEFINITIONS ==============

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available government data tools."""
    return [
        # === PERMITS ===
        Tool(
            name="search_permits",
            description="Search building permits across 25+ US jurisdictions. Use list_jurisdictions to see all supported cities/counties. Returns permit number, address, type, status, dates, and contractor info. For reference-only jurisdictions (no API), returns portal URL and instructions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Street address or partial address to search"
                    },
                    "permit_type": {
                        "type": "string",
                        "description": "Type of permit (e.g., 'building', 'electrical', 'plumbing', 'mechanical', 'demolition')"
                    },
                    "status": {
                        "type": "string",
                        "description": "Permit status (e.g., 'issued', 'approved', 'pending', 'expired', 'closed')"
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date filter (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date filter (YYYY-MM-DD)"
                    },
                    "jurisdiction": {
                        "type": "string",
                        "description": "Jurisdiction slug (e.g., 'miami-dade', 'orlando', 'broward', 'houston', 'seattle'). Use list_jurisdictions to see all options. Default: miami-dade",
                        "default": "miami-dade"
                    }
                },
                "required": []
            }
        ),

        Tool(
            name="get_permit_details",
            description="Get full details of a specific building permit by permit number. Works with ArcGIS and Socrata jurisdictions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "permit_number": {
                        "type": "string",
                        "description": "The permit number to look up"
                    },
                    "jurisdiction": {
                        "type": "string",
                        "description": "Jurisdiction slug. Use list_jurisdictions to see options. Default: miami-dade",
                        "default": "miami-dade"
                    }
                },
                "required": ["permit_number"]
            }
        ),

        # === VIOLATIONS ===
        Tool(
            name="search_code_violations",
            description="Search building code violations by address or area. Returns case number, violation type, status, and details. For reference-only jurisdictions, returns portal URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Street address or partial address to search"
                    },
                    "violation_type": {
                        "type": "string",
                        "description": "Type of violation to filter by"
                    },
                    "status": {
                        "type": "string",
                        "description": "Violation status (e.g., 'open', 'closed', 'pending')"
                    },
                    "jurisdiction": {
                        "type": "string",
                        "description": "Jurisdiction slug. Use list_jurisdictions to see options. Default: miami-dade",
                        "default": "miami-dade"
                    }
                },
                "required": []
            }
        ),

        # === ZONING ===
        Tool(
            name="lookup_zoning",
            description="Look up zoning information for an address. Returns zoning designation, allowed uses, and restrictions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Street address to look up zoning for"
                    },
                    "jurisdiction": {
                        "type": "string",
                        "description": "Jurisdiction slug. Use list_jurisdictions to see options. Default: miami-dade",
                        "default": "miami-dade"
                    }
                },
                "required": ["address"]
            }
        ),

        # === CONTRACTORS ===
        Tool(
            name="search_contractors",
            description="Search for licensed contractors by name, license number, or trade. Provides state licensing board lookup info.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Contractor name to search"
                    },
                    "license_number": {
                        "type": "string",
                        "description": "License number to verify"
                    },
                    "trade": {
                        "type": "string",
                        "description": "Trade specialty (e.g., 'general', 'electrical', 'plumbing', 'HVAC', 'roofing')"
                    },
                    "state": {
                        "type": "string",
                        "description": "State abbreviation (FL, CA, NY, TX, IL). Default: FL",
                        "default": "FL"
                    }
                },
                "required": []
            }
        ),

        # === STATISTICS ===
        Tool(
            name="get_building_permits_stats",
            description="Get aggregate building permit statistics from the Census Bureau Building Permits Survey. Shows permit counts, units authorized, and trends.",
            inputSchema={
                "type": "object",
                "properties": {
                    "jurisdiction": {
                        "type": "string",
                        "description": "State FIPS code (e.g., '12' for Florida, '06' for California) or leave empty for national data"
                    },
                    "period": {
                        "type": "string",
                        "description": "Time period: 'monthly' or 'annual'. Default: monthly",
                        "default": "monthly"
                    },
                    "permit_type": {
                        "type": "string",
                        "description": "Not used for Census data, reserved for future use"
                    }
                },
                "required": []
            }
        ),

        # === OSHA ===
        Tool(
            name="search_osha_inspections",
            description="Search OSHA construction site inspections and violations. Returns inspection records, violation types, and penalties.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "Company or establishment name to search"
                    },
                    "state": {
                        "type": "string",
                        "description": "State abbreviation (e.g., 'FL', 'CA', 'NY')"
                    },
                    "violation_type": {
                        "type": "string",
                        "description": "Type of violation (e.g., 'serious', 'willful', 'repeat', 'other')"
                    }
                },
                "required": []
            }
        ),

        # === BUILDING CODE ===
        Tool(
            name="lookup_building_code",
            description="Reference IBC/IRC/FBC building code sections. Look up by section number or search by keyword. Covers 4 editions: IBC 2021 (25+ sections), IRC 2021 (20+ sections), FBC 2023 with HVHZ/wind/flood amendments, and FBC Residential 2023. Covers occupancy, construction types, fire/smoke protection, egress, structural loads, FL wind/flood, and more.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code_section": {
                        "type": "string",
                        "description": "Code section number (e.g., '302', '903', 'R311', 'R602', 'FL1609', 'FL_HVHZ')"
                    },
                    "keyword": {
                        "type": "string",
                        "description": "Keyword to search for (e.g., 'sprinkler', 'egress', 'fire', 'wind', 'hurricane', 'HVHZ', 'flood')"
                    },
                    "code_edition": {
                        "type": "string",
                        "description": "Code edition: '2021 IBC', '2021 IRC', '2023 FBC', '2023 FBC Residential'. Default: 2021 IBC",
                        "default": "2021 IBC"
                    }
                },
                "required": []
            }
        ),

        # === LIST JURISDICTIONS ===
        Tool(
            name="list_jurisdictions",
            description="List all supported jurisdictions. Filter by state, data type, or platform. Shows jurisdiction name, state, platform type, available data endpoints, and building code edition.",
            inputSchema={
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "description": "Filter by state abbreviation (e.g., 'FL', 'CA', 'TX', 'NY')"
                    },
                    "data_type": {
                        "type": "string",
                        "description": "Filter by data type: 'building_permits', 'building_violations', 'zoning', 'parcels', 'wetlands', etc."
                    },
                    "platform": {
                        "type": "string",
                        "description": "Filter by platform: 'arcgis', 'socrata', 'reference'"
                    }
                },
                "required": []
            }
        ),
    ]


# ============== TOOL HANDLERS ==============

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute government data tools."""

    try:
        # === SEARCH PERMITS ===
        if name == "search_permits":
            jurisdiction = arguments.get("jurisdiction", "miami-dade")
            address = arguments.get("address")
            permit_type = arguments.get("permit_type")
            status = arguments.get("status")
            date_from = arguments.get("date_from")
            date_to = arguments.get("date_to")

            permits = fetch_permits(
                jurisdiction=jurisdiction,
                address=address,
                permit_type=permit_type,
                status=status,
                date_from=date_from,
                date_to=date_to,
            )

            # Check for reference-type response
            if permits and isinstance(permits[0], dict) and permits[0].get("type") == "reference":
                return [TextContent(type="text", text=format_reference_text(permits[0]))]

            if not permits:
                filters = []
                if address:
                    filters.append(f"address='{address}'")
                if permit_type:
                    filters.append(f"type='{permit_type}'")
                if status:
                    filters.append(f"status='{status}'")
                filter_str = ", ".join(filters) if filters else "none"
                return [TextContent(
                    type="text",
                    text=f"No permits found in {jurisdiction} with filters: {filter_str}\n\n"
                         f"Tips:\n"
                         f"- Try a broader search (e.g., just the street name)\n"
                         f"- Check the jurisdiction spelling\n"
                         f"- Some jurisdictions have limited date ranges"
                )]

            lines = [
                f"=== Building Permits: {jurisdiction.upper()} ===",
                f"Found {len(permits)} permit(s)\n",
            ]
            for i, permit in enumerate(permits, 1):
                lines.append(f"--- Permit {i} ---")
                lines.append(format_permit(permit, jurisdiction))
                lines.append("")

            lines.append(
                f"Source: {load_jurisdictions().get(jurisdiction, {}).get('open_data_url', 'Government open data portal')}"
            )
            return [TextContent(type="text", text="\n".join(lines))]

        # === GET PERMIT DETAILS ===
        elif name == "get_permit_details":
            permit_number = arguments["permit_number"]
            jurisdiction = arguments.get("jurisdiction", "miami-dade")

            endpoint = get_endpoint(jurisdiction, "building_permits")
            if not endpoint:
                return [TextContent(
                    type="text",
                    text=f"No permits endpoint for '{jurisdiction}'. "
                         f"Supported: {list_supported_jurisdictions('building_permits')}"
                )]

            jurisdictions = load_jurisdictions()
            platform = jurisdictions[jurisdiction].get("data_platform", "socrata")

            if platform == "reference":
                ref = format_reference_response(jurisdiction, endpoint, permit_number)
                return [TextContent(type="text", text=format_reference_text(ref[0]))]
            elif platform == "arcgis":
                # Build WHERE clause using endpoint metadata for permit number field
                pn_field = endpoint.get("permit_number_field", "")
                where_parts = []
                if pn_field:
                    where_parts.append(f"{pn_field} = '{permit_number}'")
                # Also try common field names as fallback
                for field in ["PERMIT_NUM", "PERMITNUMBER", "APPLICATION_NUMBER", "PROCNUM"]:
                    if field != pn_field:
                        where_parts.append(f"{field} = '{permit_number}'")
                where = " OR ".join(where_parts)
                results = query_arcgis(endpoint["url"], where_clause=where,
                                       max_records=1)
            elif platform == "socrata":
                params = {
                    "$where": (
                        f"permit_number = '{permit_number}' OR "
                        f"application_number = '{permit_number}'"
                    )
                }
                results = query_socrata(endpoint["url"], params=params,
                                        limit=1)
            else:
                results = []

            if not results:
                return [TextContent(
                    type="text",
                    text=f"Permit '{permit_number}' not found in {jurisdiction}.\n"
                         f"Try searching with search_permits first to find the exact permit number format."
                )]

            permit = results[0]
            lines = [
                f"=== Permit Details: {permit_number} ===",
                f"Jurisdiction: {jurisdiction}\n",
            ]

            # Display all available fields
            for key, value in sorted(permit.items()):
                if value is not None and str(value).strip():
                    # Clean up field names for display
                    display_key = key.replace("_", " ").title()
                    lines.append(f"  {display_key}: {value}")

            return [TextContent(type="text", text="\n".join(lines))]

        # === SEARCH CODE VIOLATIONS ===
        elif name == "search_code_violations":
            jurisdiction = arguments.get("jurisdiction", "miami-dade")
            address = arguments.get("address")
            violation_type = arguments.get("violation_type")
            status = arguments.get("status")

            violations = fetch_violations(
                jurisdiction=jurisdiction,
                address=address,
                violation_type=violation_type,
                status=status,
            )

            # Check for reference-type response
            if violations and isinstance(violations[0], dict) and violations[0].get("type") == "reference":
                return [TextContent(type="text", text=format_reference_text(violations[0]))]

            if not violations:
                return [TextContent(
                    type="text",
                    text=f"No code violations found in {jurisdiction} with the given filters.\n"
                         f"Tips: Try a broader search or check spelling."
                )]

            lines = [
                f"=== Code Violations: {jurisdiction.upper()} ===",
                f"Found {len(violations)} violation(s)\n",
            ]
            for i, v in enumerate(violations, 1):
                lines.append(f"--- Violation {i} ---")
                lines.append(format_violation(v))
                lines.append("")

            return [TextContent(type="text", text="\n".join(lines))]

        # === LOOKUP ZONING ===
        elif name == "lookup_zoning":
            address = arguments["address"]
            jurisdiction = arguments.get("jurisdiction", "miami-dade")

            results = fetch_zoning(jurisdiction, address)

            # Check for reference-type response
            if results and isinstance(results[0], dict) and results[0].get("type") == "reference":
                return [TextContent(type="text", text=format_reference_text(results[0]))]

            if not results:
                return [TextContent(
                    type="text",
                    text=f"No zoning information found for '{address}' in {jurisdiction}.\n"
                         f"Tips:\n"
                         f"- Try a simpler address (just street number and name)\n"
                         f"- Zoning data may use parcel-based lookups rather than addresses\n"
                         f"- Check the jurisdiction's GIS viewer directly"
                )]

            lines = [
                f"=== Zoning Information: {jurisdiction.upper()} ===",
                f"Address: {address}\n",
            ]
            for i, z in enumerate(results, 1):
                lines.append(f"--- Result {i} ---")
                for key, value in sorted(z.items()):
                    if value is not None and str(value).strip():
                        display_key = key.replace("_", " ").title()
                        lines.append(f"  {display_key}: {value}")
                lines.append("")

            lines.append(
                "Note: For authoritative zoning determinations, always verify "
                "with the local planning/zoning department."
            )
            return [TextContent(type="text", text="\n".join(lines))]

        # === SEARCH CONTRACTORS ===
        elif name == "search_contractors":
            name_arg = arguments.get("name")
            license_number = arguments.get("license_number")
            trade = arguments.get("trade")
            state = arguments.get("state", "FL")

            result = search_contractor_data(
                name=name_arg,
                license_number=license_number,
                trade=trade,
                state=state,
            )
            return [TextContent(type="text", text=result)]

        # === BUILDING PERMITS STATS ===
        elif name == "get_building_permits_stats":
            jurisdiction = arguments.get("jurisdiction", "")
            period = arguments.get("period", "monthly")

            data = fetch_census_permits_stats(
                state=jurisdiction if jurisdiction else None,
                period=period,
            )

            if isinstance(data, dict) and "error" in data:
                return [TextContent(type="text", text=data["error"])]

            if isinstance(data, list) and len(data) > 1:
                headers = data[0]
                rows = data[1:]

                lines = [
                    "=== Census Bureau Building Permits Survey ===",
                    f"Period: {period}",
                    f"Records: {len(rows)}\n",
                    "  |  ".join(str(h) for h in headers),
                    "-" * 60,
                ]
                for row in rows[:50]:  # Limit display
                    lines.append("  |  ".join(str(v) for v in row))

                if len(rows) > 50:
                    lines.append(f"\n... and {len(rows) - 50} more rows")

                lines.append(
                    "\nSource: U.S. Census Bureau, Building Permits Survey"
                )
                return [TextContent(type="text", text="\n".join(lines))]
            else:
                return [TextContent(
                    type="text",
                    text=f"Census API returned unexpected format:\n{json.dumps(data, indent=2)[:2000]}"
                )]

        # === OSHA INSPECTIONS ===
        elif name == "search_osha_inspections":
            company = arguments.get("company")
            state = arguments.get("state")
            violation_type = arguments.get("violation_type")

            results = fetch_osha_inspections(
                company=company,
                state=state,
                violation_type=violation_type,
            )

            if not results:
                return [TextContent(
                    type="text",
                    text="No OSHA inspection records found with the given criteria.\n"
                         "Tips:\n"
                         "- Try searching by company name\n"
                         "- OSHA data may have limited API access; consider visiting "
                         "https://www.osha.gov/data directly"
                )]

            # Check if we got a fallback message
            if len(results) == 1 and "note" in results[0]:
                lines = [
                    "=== OSHA Inspection Search ===\n",
                    results[0]["note"],
                    "",
                    "Alternative access methods:",
                    "  1. OSHA Inspection Lookup: https://www.osha.gov/ords/imis/establishment.html",
                    "  2. DOL Enforcement Data: https://enforcedata.dol.gov/views/data_catalogs.php",
                    "  3. Bulk data downloads: https://www.osha.gov/data",
                ]
                if "search_params" in results[0]:
                    lines.append(f"\nSearch parameters used: {results[0]['search_params']}")
                return [TextContent(type="text", text="\n".join(lines))]

            lines = [
                "=== OSHA Construction Inspections ===",
                f"Found {len(results)} record(s)\n",
            ]
            for i, record in enumerate(results, 1):
                lines.append(f"--- Record {i} ---")
                for key, value in sorted(record.items()):
                    if value is not None and str(value).strip():
                        display_key = key.replace("_", " ").title()
                        lines.append(f"  {display_key}: {value}")
                lines.append("")

            lines.append("Source: U.S. Department of Labor, OSHA Enforcement Data")
            return [TextContent(type="text", text="\n".join(lines))]

        # === BUILDING CODE LOOKUP ===
        elif name == "lookup_building_code":
            code_section = arguments.get("code_section")
            keyword = arguments.get("keyword")
            code_edition = arguments.get("code_edition", "2021 IBC")

            result = lookup_code(
                code_section=code_section,
                keyword=keyword,
                code_edition=code_edition,
            )
            return [TextContent(type="text", text=result)]

        # === LIST JURISDICTIONS ===
        elif name == "list_jurisdictions":
            state_filter = arguments.get("state", "").upper()
            data_type_filter = arguments.get("data_type", "")
            platform_filter = arguments.get("platform", "")

            jurisdictions = load_jurisdictions()
            lines = ["=== Supported Jurisdictions ===\n"]
            filters_desc = []
            if state_filter:
                filters_desc.append(f"state={state_filter}")
            if data_type_filter:
                filters_desc.append(f"data_type={data_type_filter}")
            if platform_filter:
                filters_desc.append(f"platform={platform_filter}")
            if filters_desc:
                lines.append(f"Filters: {', '.join(filters_desc)}\n")

            count = 0
            for key, value in sorted(jurisdictions.items()):
                if key.startswith("_"):
                    continue
                if not isinstance(value, dict) or "name" not in value:
                    continue

                # Apply filters
                if state_filter and value.get("state", "").upper() != state_filter:
                    continue
                if platform_filter and value.get("data_platform", "") != platform_filter:
                    continue
                if data_type_filter:
                    if data_type_filter not in value.get("endpoints", {}):
                        continue

                count += 1
                platform = value.get("data_platform", "unknown")
                state = value.get("state", "")
                name = value.get("name", key)
                endpoints = list(value.get("endpoints", {}).keys())
                code = value.get("building_code", "")
                hvhz = " [HVHZ]" if value.get("hvhz") else ""

                lines.append(f"  {key}")
                lines.append(f"    Name: {name}")
                lines.append(f"    State: {state} | Platform: {platform}{hvhz}")
                if code:
                    lines.append(f"    Building Code: {code}")
                lines.append(f"    Data: {', '.join(endpoints)}")
                lines.append("")

            lines.insert(1, f"Total: {count} jurisdiction(s)\n")
            lines.append(
                f"Building code editions available: {', '.join(get_available_editions())}"
            )
            return [TextContent(type="text", text="\n".join(lines))]

        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}. Use list_tools to see available tools."
            )]

    except TimeoutError as e:
        return [TextContent(type="text", text=f"Timeout: {str(e)}")]
    except ConnectionError as e:
        return [TextContent(type="text", text=f"Connection Error: {str(e)}")]
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error executing {name}: {type(e).__name__}: {str(e)}\n\n"
                 f"Government APIs can be unreliable. If this persists, "
                 f"try again in a few minutes or check the data source directly."
        )]


# ============== ENTRY POINT ==============

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

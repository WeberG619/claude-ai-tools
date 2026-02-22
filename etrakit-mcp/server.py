#!/usr/bin/env python3
"""
eTRAKiT Permit MCP Server

Scrapes CentralSquare eTRAKiT permit portals used by Broward County cities
to return structured permit data including permit info, inspections,
review comments, fees, contacts, conditions, and status tracking.

Currently supports:
- Coral Springs (etrakit.coralsprings.gov)

Architecture is extensible for other Broward County eTRAKiT cities.

Tools:
1. search_permits        - Search by address, permit number, contractor, folio, or owner
2. get_permit_details    - Full permit record with all tabs
3. get_permit_inspections - Inspection history and upcoming
4. get_permit_comments   - Review comments / chronology
5. monitor_permit_status - Check if a permit has changed since last check

Uses CDP (Chrome DevTools Protocol) to connect to an already-running
Chrome instance for browser automation. SQLite caching with 30-min TTL.
"""

import asyncio
import json
import logging
import sys
import time
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from cache import PermitCache
from scrapers.base import BasePermitScraper
from scrapers.coral_springs import CoralSpringsScraper

# ---- Logging ----

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("etrakit-mcp")

# ---- Globals ----

server = Server("etrakit-mcp")
cache = PermitCache()

# Scraper instances (lazily initialized, reused across calls)
_scrapers: dict[str, BasePermitScraper] = {}

# Supported cities and their aliases
CITY_ALIASES = {
    "coral-springs": "coral-springs",
    "coral_springs": "coral-springs",
    "coralsprings": "coral-springs",
    "cs": "coral-springs",
    # Future cities:
    # "pompano-beach": "pompano-beach",
    # "fort-lauderdale": "fort-lauderdale",
    # "margate": "margate",
    # "coconut-creek": "coconut-creek",
    # "parkland": "parkland",
}


def normalize_city(city: str) -> str:
    """Normalize city name to canonical form."""
    city = city.lower().strip().replace(" ", "-")
    return CITY_ALIASES.get(city, city)


def get_scraper(city: str) -> BasePermitScraper:
    """Get or create a scraper for the given city."""
    city = normalize_city(city)

    if city == "coral-springs":
        if city not in _scrapers:
            _scrapers[city] = CoralSpringsScraper()
        return _scrapers[city]
    else:
        supported = ", ".join(sorted(set(CITY_ALIASES.values())))
        raise ValueError(
            f"Unsupported city: '{city}'. Supported: {supported}"
        )


# ---- Formatters ----

def format_search_results(results: list[dict], city: str, query: str, cached: bool = False) -> str:
    """Format permit search results for display."""
    if not results:
        return (
            f"No permits found in {city.replace('-', ' ').title()} "
            f"matching '{query}'.\n\n"
            f"Tips:\n"
            f"- For address search, try a partial street name (e.g., 'Woodside')\n"
            f"- For permit number, use the full format (e.g., 'BP24-000146')\n"
            f"- The eTRAKiT portal may be temporarily unavailable"
        )

    cache_note = " [cached]" if cached else ""
    lines = [
        f"=== Permit Search Results ({city.replace('-', ' ').title()}) ===",
        f"Found {len(results)} permit(s){cache_note}",
        f"Query: '{query}'",
        "",
    ]

    for i, permit in enumerate(results, 1):
        lines.append(f"--- Result {i} ---")
        lines.append(f"  Permit #: {permit.get('permit_number', 'N/A')}")
        if permit.get("type"):
            lines.append(f"  Type: {permit['type']}")
        if permit.get("status"):
            lines.append(f"  Status: {permit['status']}")
        if permit.get("address"):
            lines.append(f"  Address: {permit['address']}")
        if permit.get("description"):
            lines.append(f"  Description: {permit['description']}")
        lines.append("")

    return "\n".join(lines)


def format_permit_details(details: dict) -> str:
    """Format full permit details for display."""
    if details.get("error"):
        return (
            f"Error: {details['error']}\n"
            f"Permit: {details.get('permit_number', 'N/A')}"
        )

    lines = [
        f"=== Permit Details: {details.get('permit_number', 'N/A')} ===",
        f"City: {details.get('city', 'N/A').replace('-', ' ').title()}",
        "",
    ]

    # Permit Info
    permit_info = details.get("permit_info", {})
    if permit_info:
        lines.append("--- Permit Information ---")
        for key, val in permit_info.items():
            if val:
                lines.append(f"  {key}: {val}")
        lines.append("")

    # Site Info
    site_info = details.get("site_info", {})
    if site_info:
        lines.append("--- Site Information ---")
        for key, val in site_info.items():
            if val:
                lines.append(f"  {key}: {val}")
        lines.append("")

    # Contacts
    contacts = details.get("contacts", [])
    if contacts:
        lines.append("--- Contacts ---")
        for i, contact in enumerate(contacts, 1):
            if isinstance(contact, dict):
                parts = []
                for key, val in contact.items():
                    if val:
                        parts.append(f"{key}: {val}")
                lines.append(f"  Contact {i}: {' | '.join(parts)}")
            else:
                lines.append(f"  Contact {i}: {contact}")
        lines.append("")

    # Fees
    fees = details.get("fees", [])
    if fees:
        lines.append("--- Fees ---")
        for i, fee in enumerate(fees, 1):
            if isinstance(fee, dict):
                parts = []
                for key, val in fee.items():
                    if val:
                        parts.append(f"{key}: {val}")
                lines.append(f"  Fee {i}: {' | '.join(parts)}")
            else:
                lines.append(f"  Fee {i}: {fee}")
        lines.append("")

    # Inspections
    inspections = details.get("inspections", [])
    if inspections:
        lines.append("--- Inspections ---")
        for i, insp in enumerate(inspections, 1):
            parts = [f"Inspection {i}:"]
            if insp.get("date"):
                parts.append(f"Date: {insp['date']}")
            if insp.get("type"):
                parts.append(f"Type: {insp['type']}")
            if insp.get("result"):
                parts.append(f"Result: {insp['result']}")
            if insp.get("inspector"):
                parts.append(f"Inspector: {insp['inspector']}")
            if insp.get("status"):
                parts.append(f"Status: {insp['status']}")
            if insp.get("comments"):
                parts.append(f"Comments: {insp['comments']}")
            lines.append(f"  {' | '.join(parts)}")
        lines.append("")

    # Chronology
    chronology = details.get("chronology", [])
    if chronology:
        lines.append("--- Chronology / Comments ---")
        for i, entry in enumerate(chronology, 1):
            parts = [f"Entry {i}:"]
            if entry.get("date"):
                parts.append(f"Date: {entry['date']}")
            if entry.get("type"):
                parts.append(f"Type: {entry['type']}")
            if entry.get("reviewer"):
                parts.append(f"By: {entry['reviewer']}")
            if entry.get("comment"):
                parts.append(f"Comment: {entry['comment']}")
            if entry.get("status"):
                parts.append(f"Status: {entry['status']}")
            lines.append(f"  {' | '.join(parts)}")
        lines.append("")

    # Conditions
    conditions = details.get("conditions", [])
    if conditions:
        lines.append("--- Conditions ---")
        for i, cond in enumerate(conditions, 1):
            if isinstance(cond, dict):
                parts = []
                for key, val in cond.items():
                    if val:
                        parts.append(f"{key}: {val}")
                lines.append(f"  Condition {i}: {' | '.join(parts)}")
            else:
                lines.append(f"  Condition {i}: {cond}")
        lines.append("")

    # Reviews
    reviews = details.get("reviews", [])
    if reviews:
        lines.append("--- Reviews ---")
        for i, rev in enumerate(reviews, 1):
            parts = [f"Review {i}:"]
            if rev.get("date"):
                parts.append(f"Date: {rev['date']}")
            if rev.get("discipline"):
                parts.append(f"Discipline: {rev['discipline']}")
            if rev.get("reviewer"):
                parts.append(f"Reviewer: {rev['reviewer']}")
            if rev.get("status"):
                parts.append(f"Status: {rev['status']}")
            if rev.get("cycle"):
                parts.append(f"Cycle: {rev['cycle']}")
            if rev.get("comments"):
                parts.append(f"Comments: {rev['comments']}")
            lines.append(f"  {' | '.join(parts)}")
        lines.append("")

    return "\n".join(lines)


def format_inspections(inspections: list[dict], permit_number: str) -> str:
    """Format inspection list for display."""
    if not inspections:
        return f"No inspections found for permit {permit_number}."

    lines = [
        f"=== Inspections: {permit_number} ===",
        f"Found {len(inspections)} inspection(s)",
        "",
    ]

    for i, insp in enumerate(inspections, 1):
        lines.append(f"--- Inspection {i} ---")
        if insp.get("date"):
            lines.append(f"  Date: {insp['date']}")
        if insp.get("requested_date"):
            lines.append(f"  Requested: {insp['requested_date']}")
        if insp.get("scheduled_date"):
            lines.append(f"  Scheduled: {insp['scheduled_date']}")
        if insp.get("type"):
            lines.append(f"  Type: {insp['type']}")
        if insp.get("result"):
            lines.append(f"  Result: {insp['result']}")
        if insp.get("status"):
            lines.append(f"  Status: {insp['status']}")
        if insp.get("inspector"):
            lines.append(f"  Inspector: {insp['inspector']}")
        if insp.get("comments"):
            lines.append(f"  Comments: {insp['comments']}")
        lines.append("")

    return "\n".join(lines)


def format_comments(comments: list[dict], permit_number: str) -> str:
    """Format comments/chronology list for display."""
    if not comments:
        return f"No comments or chronology found for permit {permit_number}."

    lines = [
        f"=== Comments & Reviews: {permit_number} ===",
        f"Found {len(comments)} entry/entries",
        "",
    ]

    for i, entry in enumerate(comments, 1):
        source = entry.get("source", "unknown")
        lines.append(f"--- Entry {i} [{source}] ---")
        if entry.get("date"):
            lines.append(f"  Date: {entry['date']}")
        if entry.get("type") or entry.get("discipline"):
            lines.append(f"  Type: {entry.get('type') or entry.get('discipline')}")
        if entry.get("reviewer"):
            lines.append(f"  By: {entry['reviewer']}")
        if entry.get("status"):
            lines.append(f"  Status: {entry['status']}")
        if entry.get("comment") or entry.get("comments"):
            lines.append(f"  Comment: {entry.get('comment') or entry.get('comments')}")
        if entry.get("cycle"):
            lines.append(f"  Cycle: {entry['cycle']}")
        lines.append("")

    return "\n".join(lines)


def format_status_check(comparison: dict, current_details: dict, permit_number: str) -> str:
    """Format a status monitoring check for display."""
    lines = [
        f"=== Status Check: {permit_number} ===",
        "",
    ]

    if comparison.get("first_check"):
        lines.append("This is the first time checking this permit.")
        lines.append(f"Current Status: {comparison.get('new_status', 'Unknown')}")
        lines.append("")
        lines.append("Future checks will compare against this baseline.")
    elif comparison.get("changed"):
        lines.append("*** CHANGES DETECTED ***")
        lines.append("")
        if comparison.get("status_changed"):
            lines.append(f"  Status: {comparison['old_status']} -> {comparison['new_status']}")
        else:
            lines.append(f"  Status: {comparison.get('new_status', 'Unknown')} (unchanged)")
        lines.append("")
        lines.append("Changes:")
        for change in comparison.get("changes", []):
            lines.append(f"  - {change}")
    else:
        lines.append("No changes detected since last check.")
        lines.append(f"Current Status: {comparison.get('new_status', 'Unknown')}")

    lines.append("")

    # Add summary of current state
    inspections = current_details.get("inspections", [])
    if inspections:
        latest = inspections[-1] if inspections else None
        if latest:
            lines.append(f"Latest Inspection: {latest.get('type', '?')} - {latest.get('result', 'pending')} ({latest.get('date', '?')})")

    reviews = current_details.get("reviews", [])
    if reviews:
        latest_review = reviews[-1] if reviews else None
        if latest_review:
            lines.append(f"Latest Review: {latest_review.get('discipline', '?')} - {latest_review.get('status', '?')} ({latest_review.get('date', '?')})")

    return "\n".join(lines)


# ============== TOOL DEFINITIONS ==============

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all eTRAKiT permit tools."""
    return [
        Tool(
            name="search_permits",
            description=(
                "Search for building permits in Broward County city eTRAKiT portals. "
                "Search by address, permit number, contractor name, property folio number, "
                "or owner name. Returns a list of matching permits with permit number, "
                "type, status, address, and description. "
                "Currently supports Coral Springs. Uses CDP to scrape the eTRAKiT portal."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search string. For address search, use partial or full "
                            "street address (e.g., '4020 Woodside Dr', 'Woodside'). "
                            "For permit search, use the permit number (e.g., 'BP24-000146'). "
                            "For contractor, use contractor name or license number."
                        ),
                    },
                    "search_type": {
                        "type": "string",
                        "description": (
                            "Type of search to perform. Default: 'address'"
                        ),
                        "default": "address",
                        "enum": ["address", "permit_number", "contractor", "folio", "owner"],
                    },
                    "city": {
                        "type": "string",
                        "description": (
                            "City to search in. Default: 'coral-springs'. "
                            "Currently only Coral Springs is supported."
                        ),
                        "default": "coral-springs",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_permit_details",
            description=(
                "Get the full record for a specific building permit from an eTRAKiT portal. "
                "Returns all available data from every tab: permit info (type, status, dates, "
                "scope of work), site info (address, folio, zoning), contacts (owner, contractor, "
                "engineer), fees (amounts, paid status), inspections (dates, results, inspector), "
                "chronology/comments (review history, status changes), conditions, and reviews "
                "(discipline, reviewer, cycle, status)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "permit_number": {
                        "type": "string",
                        "description": (
                            "Permit number (e.g., 'BP24-000146', 'EC24-001234'). "
                            "Use search_permits to find permit numbers."
                        ),
                    },
                    "city": {
                        "type": "string",
                        "description": "City. Default: 'coral-springs'",
                        "default": "coral-springs",
                    },
                },
                "required": ["permit_number"],
            },
        ),
        Tool(
            name="get_permit_inspections",
            description=(
                "Get the inspection history and upcoming inspections for a specific "
                "building permit. Returns dates, inspection types, results (pass/fail), "
                "inspector names, and any comments. Useful for tracking inspection progress "
                "and identifying failed inspections that need re-inspection."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "permit_number": {
                        "type": "string",
                        "description": "Permit number (e.g., 'BP24-000146')",
                    },
                    "city": {
                        "type": "string",
                        "description": "City. Default: 'coral-springs'",
                        "default": "coral-springs",
                    },
                },
                "required": ["permit_number"],
            },
        ),
        Tool(
            name="get_permit_comments",
            description=(
                "Get review comments and chronology/timeline for a specific building permit. "
                "Returns the combined chronology entries and review records, including dates, "
                "reviewers, disciplines, review cycles, statuses, and comments. "
                "Useful for understanding what reviews have been completed, what corrections "
                "are needed, and the overall permit review timeline."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "permit_number": {
                        "type": "string",
                        "description": "Permit number (e.g., 'BP24-000146')",
                    },
                    "city": {
                        "type": "string",
                        "description": "City. Default: 'coral-springs'",
                        "default": "coral-springs",
                    },
                },
                "required": ["permit_number"],
            },
        ),
        Tool(
            name="monitor_permit_status",
            description=(
                "Check if a permit's status has changed since the last time it was checked. "
                "Compares the current permit data against a stored baseline and reports "
                "any differences: status changes, new inspections, new review comments, "
                "new conditions, or fee changes. On first check, establishes the baseline. "
                "Useful for monitoring permits through the review/approval process."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "permit_number": {
                        "type": "string",
                        "description": "Permit number to monitor (e.g., 'BP24-000146')",
                    },
                    "city": {
                        "type": "string",
                        "description": "City. Default: 'coral-springs'",
                        "default": "coral-springs",
                    },
                },
                "required": ["permit_number"],
            },
        ),
    ]


# ============== TOOL HANDLERS ==============

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute an eTRAKiT permit tool."""

    try:
        # === SEARCH PERMITS ===
        if name == "search_permits":
            query = arguments.get("query", "").strip()
            search_type = arguments.get("search_type", "address").strip().lower()
            city = normalize_city(arguments.get("city", "coral-springs"))

            if not query:
                return [TextContent(
                    type="text",
                    text="Error: 'query' is required. Provide an address, permit number, contractor, folio, or owner name.",
                )]

            # Check cache
            cache_key = f"search:{search_type}:{query.lower()}"
            cached = cache.get_search_results(cache_key, city)
            if cached:
                logger.info(f"Returning cached search results for '{query}'")
                text = format_search_results(cached, city, query, cached=True)
                return [TextContent(type="text", text=text)]

            # Scrape
            scraper = get_scraper(city)
            logger.info(f"Searching {city} permits: {search_type}='{query}'")

            results = await scraper.search_permits(query=query, search_type=search_type)

            # Cache results
            if results:
                cache.put_search_results(cache_key, city, results)

            text = format_search_results(results, city, query)
            return [TextContent(type="text", text=text)]

        # === GET PERMIT DETAILS ===
        elif name == "get_permit_details":
            permit_number = arguments["permit_number"].strip().upper()
            city = normalize_city(arguments.get("city", "coral-springs"))

            # Check cache
            cached = cache.get(permit_number, city, data_type="details")
            if cached:
                logger.info(f"Returning cached details for {permit_number}")
                text = format_permit_details(cached)
                text += "\n[Data from cache]"
                text += f"\n\n--- Raw JSON ---\n{json.dumps(cached, indent=2, default=str)}"
                return [TextContent(type="text", text=text)]

            # Scrape
            scraper = get_scraper(city)
            logger.info(f"Fetching permit details for {permit_number} from {city}")

            details = await scraper.get_permit_details(permit_number)

            # Cache if no error
            if not details.get("error"):
                cache.put(permit_number, city, details, data_type="details")

            text = format_permit_details(details)
            text += f"\n\n--- Raw JSON ---\n{json.dumps(details, indent=2, default=str)}"
            return [TextContent(type="text", text=text)]

        # === GET PERMIT INSPECTIONS ===
        elif name == "get_permit_inspections":
            permit_number = arguments["permit_number"].strip().upper()
            city = normalize_city(arguments.get("city", "coral-springs"))

            # Check details cache first (inspections are part of full details)
            cached_details = cache.get(permit_number, city, data_type="details")
            if cached_details and cached_details.get("inspections"):
                logger.info(f"Returning cached inspections for {permit_number}")
                text = format_inspections(cached_details["inspections"], permit_number)
                text += "\n[Data from cache]"
                return [TextContent(type="text", text=text)]

            # Check dedicated inspections cache
            cached_insp = cache.get(permit_number, city, data_type="inspections")
            if cached_insp:
                inspections = cached_insp if isinstance(cached_insp, list) else []
                text = format_inspections(inspections, permit_number)
                text += "\n[Data from cache]"
                return [TextContent(type="text", text=text)]

            # Scrape
            scraper = get_scraper(city)
            logger.info(f"Fetching inspections for {permit_number} from {city}")

            inspections = await scraper.get_permit_inspections(permit_number)

            # Cache
            if inspections:
                cache.put(permit_number, city, inspections, data_type="inspections")

            text = format_inspections(inspections, permit_number)
            if inspections:
                text += f"\n\n--- Raw JSON ---\n{json.dumps(inspections, indent=2, default=str)}"

            return [TextContent(type="text", text=text)]

        # === GET PERMIT COMMENTS ===
        elif name == "get_permit_comments":
            permit_number = arguments["permit_number"].strip().upper()
            city = normalize_city(arguments.get("city", "coral-springs"))

            # Check details cache (comments are part of full details)
            cached_details = cache.get(permit_number, city, data_type="details")
            if cached_details:
                all_comments = []
                for entry in cached_details.get("chronology", []):
                    entry["source"] = "chronology"
                    all_comments.append(entry)
                for entry in cached_details.get("reviews", []):
                    entry["source"] = "review"
                    all_comments.append(entry)
                if all_comments:
                    logger.info(f"Returning cached comments for {permit_number}")
                    text = format_comments(all_comments, permit_number)
                    text += "\n[Data from cache]"
                    return [TextContent(type="text", text=text)]

            # Check dedicated comments cache
            cached_comments = cache.get(permit_number, city, data_type="comments")
            if cached_comments:
                comments = cached_comments if isinstance(cached_comments, list) else []
                text = format_comments(comments, permit_number)
                text += "\n[Data from cache]"
                return [TextContent(type="text", text=text)]

            # Scrape
            scraper = get_scraper(city)
            logger.info(f"Fetching comments for {permit_number} from {city}")

            comments = await scraper.get_permit_comments(permit_number)

            # Cache
            if comments:
                cache.put(permit_number, city, comments, data_type="comments")

            text = format_comments(comments, permit_number)
            if comments:
                text += f"\n\n--- Raw JSON ---\n{json.dumps(comments, indent=2, default=str)}"

            return [TextContent(type="text", text=text)]

        # === MONITOR PERMIT STATUS ===
        elif name == "monitor_permit_status":
            permit_number = arguments["permit_number"].strip().upper()
            city = normalize_city(arguments.get("city", "coral-springs"))

            # Always fetch fresh data for monitoring (bypass cache)
            scraper = get_scraper(city)
            logger.info(f"Monitoring status for {permit_number} from {city}")

            details = await scraper.get_permit_details(permit_number)

            if details.get("error"):
                return [TextContent(
                    type="text",
                    text=f"Error checking permit {permit_number}: {details['error']}",
                )]

            # Compare against last known status
            comparison = cache.compare_status(permit_number, city, details)

            # Extract current status for storage
            current_status = ""
            for key, val in details.get("permit_info", {}).items():
                if "status" in key.lower():
                    current_status = val
                    break

            # Build a snapshot for future comparisons
            snapshot = {
                "inspections": details.get("inspections", []),
                "chronology": details.get("chronology", []),
                "reviews": details.get("reviews", []),
                "conditions": details.get("conditions", []),
                "fees": details.get("fees", []),
            }

            # Update the stored status
            cache.update_status(permit_number, city, current_status, snapshot)

            # Also cache the full details
            cache.put(permit_number, city, details, data_type="details")

            text = format_status_check(comparison, details, permit_number)
            return [TextContent(type="text", text=text)]

        else:
            return [TextContent(
                type="text",
                text=(
                    f"Unknown tool: {name}. Available: search_permits, "
                    f"get_permit_details, get_permit_inspections, "
                    f"get_permit_comments, monitor_permit_status"
                ),
            )]

    except ValueError as e:
        return [TextContent(type="text", text=f"Input Error: {str(e)}")]
    except RuntimeError as e:
        return [TextContent(type="text", text=f"Runtime Error: {str(e)}")]
    except Exception as e:
        logger.exception(f"Unexpected error in {name}")
        return [TextContent(
            type="text",
            text=(
                f"Error executing {name}: {type(e).__name__}: {str(e)}\n\n"
                f"The eTRAKiT portal may be temporarily unavailable "
                f"or the page structure may have changed. Check the logs for details."
            ),
        )]


# ============== ENTRY POINT ==============

async def run_server():
    """Run the MCP server over stdio."""
    logger.info("Starting eTRAKiT Permit MCP server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


async def run_test():
    """Run a quick test to verify the server components work."""
    print("=" * 60)
    print("eTRAKiT Permit MCP Server - Test Mode")
    print("=" * 60)
    print()

    # Test 1: Cache
    print("[1/4] Testing SQLite cache...")
    try:
        test_cache = PermitCache()
        test_cache.put("TEST-001", "coral-springs", {"test": True}, data_type="test")
        result = test_cache.get("TEST-001", "coral-springs", data_type="test")
        assert result == {"test": True}, f"Cache read mismatch: {result}"
        stats = test_cache.stats()
        print(f"  Cache OK: {stats['total_entries']} entries, "
              f"DB at {stats['db_path']}")
        test_cache._conn.execute(
            "DELETE FROM permit_cache WHERE cache_key='TEST-001' AND data_type='test'"
        )
        test_cache._conn.commit()
    except Exception as e:
        print(f"  Cache FAILED: {e}")
        return False

    # Test 2: Status tracking
    print("[2/4] Testing status tracking...")
    try:
        test_cache.update_status("TEST-001", "coral-springs", "Under Review", {"inspections": []})
        last = test_cache.get_last_status("TEST-001", "coral-springs")
        assert last is not None, "Status not stored"
        assert last["status"] == "Under Review"
        print(f"  Status tracking OK")
        test_cache._conn.execute(
            "DELETE FROM permit_status WHERE permit_number='TEST-001'"
        )
        test_cache._conn.commit()
        test_cache.close()
    except Exception as e:
        print(f"  Status tracking FAILED: {e}")
        return False

    # Test 3: Scraper instantiation
    print("[3/4] Testing scraper instantiation...")
    try:
        scraper = CoralSpringsScraper()
        print(f"  CoralSpringsScraper: OK")
    except Exception as e:
        print(f"  Scraper instantiation FAILED: {e}")
        return False

    # Test 4: CDP connection
    print("[4/4] Testing CDP browser connection...")
    try:
        from cdp_client import CDPBrowser
        browser = CDPBrowser()
        connected = await browser.check_connection()
        if connected:
            page = await browser.new_page()
            await page.goto("about:blank")
            title = await page.evaluate("document.title")
            await page.close()
            await browser.close_all()
            print(f"  CDP connection: OK (title: '{title}')")
        else:
            print("  CDP connection: FAILED - Chrome not running on port 9222")
            print("  Hint: Start Chrome with --remote-debugging-port=9222")
            return False
    except Exception as e:
        print(f"  CDP connection FAILED: {e}")
        return False

    print()
    print("=" * 60)
    print("All core tests passed. Server is ready to run.")
    print()
    print("To start the server:")
    print("  python3 server.py")
    print("=" * 60)
    return True


def main():
    """Entry point supporting both server mode and test mode."""
    if "--test" in sys.argv:
        success = asyncio.run(run_test())
        sys.exit(0 if success else 1)
    else:
        asyncio.run(run_server())


if __name__ == "__main__":
    main()

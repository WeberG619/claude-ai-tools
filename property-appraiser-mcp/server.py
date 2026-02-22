#!/usr/bin/env python3
"""
Property Appraiser MCP Server

Scrapes Broward County (BCPA) and Miami-Dade County property appraiser
websites to return structured property data including ownership, assessed
values, building characteristics, and sales history.

Tools:
1. search_property   - Search by address or folio number
2. get_property_details - Full property record for a folio
3. get_sales_history - Sales/transfer history for a property

Uses CDP (Chrome DevTools Protocol) to connect to an already-running
Chrome instance for browser automation. SQLite caching with 7-day TTL.
"""

import asyncio
import json
import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from cache import PropertyCache
from scrapers.base import BaseScraper
from scrapers.bcpa_scraper import BCPAScraper
from scrapers.mdcpa_scraper import MDCPAScraper

# ---- Logging ----

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("property-appraiser-mcp")

# ---- Globals ----

server = Server("property-appraiser-mcp")
cache = PropertyCache()

# Scraper instances (lazily initialized, reused across calls)
_scrapers: dict[str, BaseScraper] = {}


def get_scraper(county: str) -> BaseScraper:
    """Get or create a scraper for the given county."""
    county = county.lower().strip()
    if county in ("broward", "bcpa"):
        key = "broward"
        if key not in _scrapers:
            _scrapers[key] = BCPAScraper()
        return _scrapers[key]
    elif county in ("miami-dade", "miami_dade", "miamidade", "mdcpa", "dade"):
        key = "miami-dade"
        if key not in _scrapers:
            _scrapers[key] = MDCPAScraper()
        return _scrapers[key]
    else:
        raise ValueError(
            f"Unsupported county: '{county}'. "
            f"Supported: 'broward' (BCPA), 'miami-dade' (MDCPA)"
        )


def normalize_county(county: str) -> str:
    """Normalize county name to canonical form."""
    county = county.lower().strip()
    if county in ("broward", "bcpa"):
        return "broward"
    elif county in ("miami-dade", "miami_dade", "miamidade", "mdcpa", "dade"):
        return "miami-dade"
    return county


def format_currency(value) -> str:
    """Format a number as currency string."""
    if value is None:
        return "N/A"
    try:
        return f"${value:,.0f}"
    except (ValueError, TypeError):
        return str(value)


def format_property_summary(prop: dict) -> str:
    """Format a property search result for display."""
    lines = []
    lines.append(f"  Folio: {prop.get('folio', 'N/A')}")
    if prop.get("address"):
        lines.append(f"  Address: {prop['address']}")
    if prop.get("owner_name"):
        lines.append(f"  Owner: {prop['owner_name']}")
    if prop.get("assessed_value"):
        lines.append(f"  Assessed Value: {format_currency(prop['assessed_value'])}")
    lines.append(f"  County: {prop.get('county', 'N/A')}")
    return "\n".join(lines)


def format_property_details(details: dict) -> str:
    """Format full property details for display."""
    if details.get("error"):
        return f"Error: {details['error']}\nFolio: {details.get('folio', 'N/A')}"

    lines = [
        f"=== Property Details: {details.get('folio', 'N/A')} ===",
        f"County: {details.get('county', 'N/A')}",
        "",
    ]

    # Owner & location
    section = []
    if details.get("owner_name"):
        section.append(f"  Owner: {details['owner_name']}")
    if details.get("mailing_address"):
        section.append(f"  Mailing Address: {details['mailing_address']}")
    if details.get("property_address"):
        section.append(f"  Property Address: {details['property_address']}")
    if details.get("legal_description"):
        section.append(f"  Legal Description: {details['legal_description']}")
    if section:
        lines.append("--- Owner & Location ---")
        lines.extend(section)
        lines.append("")

    # Land info
    section = []
    if details.get("land_use_code"):
        section.append(f"  Land Use: {details['land_use_code']}")
    if details.get("zoning"):
        section.append(f"  Zoning: {details['zoning']}")
    if details.get("lot_size_sf"):
        section.append(f"  Lot Size: {details['lot_size_sf']:,} SF")
    if details.get("lot_dimensions"):
        section.append(f"  Lot Dimensions: {details['lot_dimensions']}")
    if section:
        lines.append("--- Land Information ---")
        lines.extend(section)
        lines.append("")

    # Assessment values
    assessed = details.get("assessed_value", {})
    market = details.get("market_value", {})
    section = []

    if any(v is not None for v in assessed.values()):
        if assessed.get("land") is not None:
            section.append(f"  Assessed Land: {format_currency(assessed['land'])}")
        if assessed.get("building") is not None:
            section.append(f"  Assessed Building: {format_currency(assessed['building'])}")
        if assessed.get("total") is not None:
            section.append(f"  Assessed Total: {format_currency(assessed['total'])}")

    if any(v is not None for v in market.values()):
        if market.get("land") is not None:
            section.append(f"  Market Land: {format_currency(market['land'])}")
        if market.get("building") is not None:
            section.append(f"  Market Building: {format_currency(market['building'])}")
        if market.get("total") is not None:
            section.append(f"  Market/Just Value: {format_currency(market['total'])}")

    if details.get("taxable_value") is not None:
        section.append(f"  Taxable Value: {format_currency(details['taxable_value'])}")

    if details.get("exemptions"):
        section.append(f"  Exemptions: {', '.join(details['exemptions'])}")

    if section:
        lines.append("--- Assessed & Market Values ---")
        lines.extend(section)
        lines.append("")

    # Building info
    bldg = details.get("building_info", {})
    section = []
    if bldg.get("year_built"):
        section.append(f"  Year Built: {bldg['year_built']}")
    if bldg.get("bedrooms"):
        section.append(f"  Bedrooms: {bldg['bedrooms']}")
    if bldg.get("bathrooms"):
        section.append(f"  Bathrooms: {bldg['bathrooms']}")
    if bldg.get("living_area_sf"):
        section.append(f"  Living Area: {bldg['living_area_sf']:,} SF")
    if bldg.get("construction_type"):
        section.append(f"  Construction: {bldg['construction_type']}")
    if bldg.get("roof_type"):
        section.append(f"  Roof: {bldg['roof_type']}")
    if bldg.get("stories"):
        section.append(f"  Stories: {bldg['stories']}")
    if section:
        lines.append("--- Building Characteristics ---")
        lines.extend(section)
        lines.append("")

    # Sales history
    sales = details.get("sales_history", [])
    if sales:
        lines.append("--- Sales History ---")
        for i, sale in enumerate(sales, 1):
            parts = [f"  Sale {i}:"]
            if sale.get("date"):
                parts.append(f"Date: {sale['date']}")
            if sale.get("price") is not None:
                parts.append(f"Price: {format_currency(sale['price'])}")
            if sale.get("qualified"):
                parts.append(f"Qualified: {sale['qualified']}")
            if sale.get("book_page"):
                parts.append(f"Book/Page: {sale['book_page']}")
            if sale.get("buyer"):
                parts.append(f"Buyer: {sale['buyer']}")
            if sale.get("seller"):
                parts.append(f"Seller: {sale['seller']}")
            lines.append(" | ".join(parts))
        lines.append("")

    return "\n".join(lines)


def format_sales_history(sales: list[dict], folio: str, county: str) -> str:
    """Format sales history for display."""
    if not sales:
        return f"No sales history found for folio {folio} in {county}."

    lines = [
        f"=== Sales History: {folio} ({county}) ===",
        f"Found {len(sales)} transaction(s)",
        "",
    ]

    for i, sale in enumerate(sales, 1):
        lines.append(f"--- Transaction {i} ---")
        if sale.get("date"):
            lines.append(f"  Date: {sale['date']}")
        if sale.get("price") is not None:
            lines.append(f"  Price: {format_currency(sale['price'])}")
        if sale.get("buyer"):
            lines.append(f"  Buyer: {sale['buyer']}")
        if sale.get("seller"):
            lines.append(f"  Seller: {sale['seller']}")
        if sale.get("qualified"):
            lines.append(f"  Qualified: {sale['qualified']}")
        if sale.get("book_page"):
            lines.append(f"  Book/Page: {sale['book_page']}")
        lines.append("")

    return "\n".join(lines)


# ============== TOOL DEFINITIONS ==============

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all property appraiser tools."""
    return [
        Tool(
            name="search_property",
            description=(
                "Search for properties by address or folio number in Broward County (BCPA) "
                "or Miami-Dade County property appraiser databases. Returns a list of matching "
                "properties with folio number, address, owner name, and assessed value. "
                "Uses CDP to scrape the county property appraiser websites."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": (
                            "Partial or full street address to search "
                            "(e.g., '4020 Woodside', '123 Main St')"
                        ),
                    },
                    "folio": {
                        "type": "string",
                        "description": (
                            "Property folio number. Broward uses 12 digits "
                            "(e.g., '484114012150'), Miami-Dade uses 13 digits "
                            "(e.g., '0132340690001'). Dashes are stripped automatically."
                        ),
                    },
                    "county": {
                        "type": "string",
                        "description": (
                            "County to search: 'broward' for BCPA or "
                            "'miami-dade' for Miami-Dade PA. Default: broward"
                        ),
                        "default": "broward",
                        "enum": ["broward", "miami-dade"],
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_property_details",
            description=(
                "Get full property details for a specific folio number from Broward County "
                "(BCPA) or Miami-Dade County property appraiser. Returns owner info, "
                "mailing/property address, legal description, land use, zoning, lot size, "
                "assessed and market values, taxable value, exemptions, building info "
                "(year built, bedrooms, bathrooms, living area, construction type, roof, "
                "stories), and sales history."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "folio": {
                        "type": "string",
                        "description": (
                            "Property folio number. Broward: 12 digits, "
                            "Miami-Dade: 13 digits."
                        ),
                    },
                    "county": {
                        "type": "string",
                        "description": "County: 'broward' or 'miami-dade'. Default: broward",
                        "default": "broward",
                        "enum": ["broward", "miami-dade"],
                    },
                },
                "required": ["folio"],
            },
        ),
        Tool(
            name="get_sales_history",
            description=(
                "Get the sales/transfer history for a property by folio number. "
                "Returns a list of transactions with dates, sale prices, buyer/seller "
                "names, qualification status, and official records book/page references."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "folio": {
                        "type": "string",
                        "description": "Property folio number.",
                    },
                    "county": {
                        "type": "string",
                        "description": "County: 'broward' or 'miami-dade'. Default: broward",
                        "default": "broward",
                        "enum": ["broward", "miami-dade"],
                    },
                },
                "required": ["folio"],
            },
        ),
    ]


# ============== TOOL HANDLERS ==============

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a property appraiser tool."""

    try:
        # === SEARCH PROPERTY ===
        if name == "search_property":
            address = arguments.get("address")
            folio = arguments.get("folio")
            county = normalize_county(arguments.get("county", "broward"))

            if not address and not folio:
                return [TextContent(
                    type="text",
                    text="Error: Provide either an 'address' or 'folio' to search.",
                )]

            # Check cache for folio searches
            if folio:
                folio_clean = BaseScraper.normalize_folio(folio)
                cached = cache.get(folio_clean, county, data_type="search")
                if cached:
                    logger.info(f"Returning cached search results for {folio_clean}")
                    results = cached if isinstance(cached, list) else [cached]
                    lines = [
                        f"=== Property Search Results ({county.title()}) ===",
                        f"Found {len(results)} result(s) [cached]",
                        "",
                    ]
                    for i, prop in enumerate(results, 1):
                        lines.append(f"--- Result {i} ---")
                        lines.append(format_property_summary(prop))
                        lines.append("")
                    return [TextContent(type="text", text="\n".join(lines))]

            # Check cache for address searches
            if address:
                cache_key = f"addr:{address.lower().strip()}"
                cached = cache.get_search_results(cache_key, county)
                if cached:
                    logger.info(f"Returning cached search results for '{address}'")
                    lines = [
                        f"=== Property Search Results ({county.title()}) ===",
                        f"Found {len(cached)} result(s) [cached]",
                        "",
                    ]
                    for i, prop in enumerate(cached, 1):
                        lines.append(f"--- Result {i} ---")
                        lines.append(format_property_summary(prop))
                        lines.append("")
                    return [TextContent(type="text", text="\n".join(lines))]

            # Scrape
            scraper = get_scraper(county)
            logger.info(f"Searching {county} PA for address='{address}' folio='{folio}'")

            results = await scraper.search_property(address=address, folio=folio)

            if not results:
                search_term = folio if folio else address
                return [TextContent(
                    type="text",
                    text=(
                        f"No properties found in {county.title()} County "
                        f"matching '{search_term}'.\n\n"
                        f"Tips:\n"
                        f"- For address search, try just the house number and street name\n"
                        f"- For folio search, ensure you have the correct number of digits\n"
                        f"  (Broward: 12 digits, Miami-Dade: 13 digits)\n"
                        f"- The property appraiser website may be temporarily unavailable"
                    ),
                )]

            # Cache results
            if folio:
                folio_clean = BaseScraper.normalize_folio(folio)
                cache.put(folio_clean, county, results, data_type="search")
            if address:
                cache_key = f"addr:{address.lower().strip()}"
                cache.put_search_results(cache_key, county, results)

            lines = [
                f"=== Property Search Results ({county.title()}) ===",
                f"Found {len(results)} result(s)",
                "",
            ]
            for i, prop in enumerate(results, 1):
                lines.append(f"--- Result {i} ---")
                lines.append(format_property_summary(prop))
                lines.append("")

            return [TextContent(type="text", text="\n".join(lines))]

        # === GET PROPERTY DETAILS ===
        elif name == "get_property_details":
            folio = arguments["folio"]
            county = normalize_county(arguments.get("county", "broward"))
            folio_clean = BaseScraper.normalize_folio(folio)

            # Check cache
            cached = cache.get(folio_clean, county, data_type="details")
            if cached:
                logger.info(f"Returning cached details for {folio_clean}")
                text = format_property_details(cached)
                text += "\n[Data from cache]"
                return [TextContent(type="text", text=text)]

            # Scrape
            scraper = get_scraper(county)
            logger.info(f"Fetching details for {folio_clean} from {county}")

            details = await scraper.get_property_details(folio_clean)

            # Cache if no error
            if not details.get("error"):
                cache.put(folio_clean, county, details, data_type="details")

            text = format_property_details(details)

            # Also return raw JSON for programmatic use
            text += f"\n\n--- Raw JSON ---\n{json.dumps(details, indent=2, default=str)}"

            return [TextContent(type="text", text=text)]

        # === GET SALES HISTORY ===
        elif name == "get_sales_history":
            folio = arguments["folio"]
            county = normalize_county(arguments.get("county", "broward"))
            folio_clean = BaseScraper.normalize_folio(folio)

            # Check cache (sales are part of details)
            cached = cache.get(folio_clean, county, data_type="details")
            if cached and cached.get("sales_history"):
                logger.info(f"Returning cached sales history for {folio_clean}")
                text = format_sales_history(
                    cached["sales_history"], folio_clean, county
                )
                text += "\n[Data from cache]"
                return [TextContent(type="text", text=text)]

            # Also check dedicated sales cache
            cached_sales = cache.get(folio_clean, county, data_type="sales")
            if cached_sales:
                sales = cached_sales if isinstance(cached_sales, list) else []
                text = format_sales_history(sales, folio_clean, county)
                text += "\n[Data from cache]"
                return [TextContent(type="text", text=text)]

            # Scrape
            scraper = get_scraper(county)
            logger.info(f"Fetching sales history for {folio_clean} from {county}")

            sales = await scraper.get_sales_history(folio_clean)

            # Cache
            if sales:
                cache.put(folio_clean, county, sales, data_type="sales")

            text = format_sales_history(sales, folio_clean, county)

            if sales:
                text += f"\n\n--- Raw JSON ---\n{json.dumps(sales, indent=2, default=str)}"

            return [TextContent(type="text", text=text)]

        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}. Available: search_property, get_property_details, get_sales_history",
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
                f"The property appraiser website may be temporarily unavailable "
                f"or the page structure may have changed. Check the logs for details."
            ),
        )]


# ============== ENTRY POINT ==============

async def run_server():
    """Run the MCP server over stdio."""
    logger.info("Starting Property Appraiser MCP server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


async def run_test():
    """Run a quick test to verify the server components work."""
    print("=" * 60)
    print("Property Appraiser MCP Server - Test Mode")
    print("=" * 60)
    print()

    # Test 1: Cache
    print("[1/4] Testing SQLite cache...")
    try:
        test_cache = PropertyCache()
        test_cache.put("test123", "broward", {"test": True}, data_type="test")
        result = test_cache.get("test123", "broward", data_type="test")
        assert result == {"test": True}, f"Cache read mismatch: {result}"
        stats = test_cache.stats()
        print(f"  Cache OK: {stats['total_entries']} entries, "
              f"DB at {stats['db_path']}")
        test_cache._conn.execute(
            "DELETE FROM property_cache WHERE folio='test123' AND data_type='test'"
        )
        test_cache._conn.commit()
    except Exception as e:
        print(f"  Cache FAILED: {e}")
        return False

    # Test 2: Scraper instantiation
    print("[2/4] Testing scraper instantiation...")
    try:
        bcpa = BCPAScraper()
        mdcpa = MDCPAScraper()
        print("  BCPAScraper: OK")
        print("  MDCPAScraper: OK")
    except Exception as e:
        print(f"  Scraper instantiation FAILED: {e}")
        return False

    # Test 3: CDP connection check
    print("[3/4] Testing CDP browser connection...")
    try:
        from cdp_client import CDPBrowser
        browser = CDPBrowser()
        connected = await browser.check_connection()
        if connected:
            print("  CDP connection: OK")
        else:
            print("  CDP connection: FAILED - Chrome not running on port 9222")
            print("  Hint: Start Chrome with --remote-debugging-port=9222")
            return False
    except Exception as e:
        print(f"  CDP connection FAILED: {e}")
        return False

    # Test 4: New tab + navigate
    print("[4/4] Testing CDP page creation...")
    try:
        page = await browser.new_page()
        await page.goto("about:blank")
        title = await page.evaluate("document.title")
        await page.close()
        await browser.close_all()
        print(f"  Page creation: OK (title: '{title}')")
    except Exception as e:
        print(f"  Page creation FAILED: {e}")
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

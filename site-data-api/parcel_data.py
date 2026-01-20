#!/usr/bin/env python3
"""
Florida Parcel/Property Data API Integration

NOTE: As of Jan 2026, the FL DOT parcel service requires authentication.
This module now returns a message directing users to county property appraiser sites.

For direct parcel lookups, use:
- Miami-Dade: https://www.miamidade.gov/pa/
- Broward: https://www.bcpa.net/
- Palm Beach: https://www.pbcgov.org/papa/
"""

import requests
import json
from typing import Optional, Dict, Any, List

# Florida county layer IDs in the FDOT Parcel FeatureServer
FL_COUNTY_LAYERS = {
    "ALACHUA": 0, "BAKER": 1, "BAY": 2, "BRADFORD": 3, "BREVARD": 4,
    "BROWARD": 5, "CALHOUN": 6, "CHARLOTTE": 7, "CITRUS": 8, "CLAY": 9,
    "COLLIER": 10, "COLUMBIA": 11, "DESOTO": 12, "MIAMI-DADE": 13, "DIXIE": 14,
    "DUVAL": 15, "ESCAMBIA": 16, "FLAGLER": 17, "FRANKLIN": 18, "GADSDEN": 19,
    "GILCHRIST": 20, "GLADES": 21, "GULF": 22, "HAMILTON": 23, "HARDEE": 24,
    "HENDRY": 25, "HERNANDO": 26, "HIGHLANDS": 27, "HILLSBOROUGH": 28, "HOLMES": 29,
    "INDIAN RIVER": 30, "JACKSON": 31, "JEFFERSON": 32, "LAFAYETTE": 33, "LAKE": 34,
    "LEE": 35, "LEON": 36, "LEVY": 37, "LIBERTY": 38, "MADISON": 39,
    "MANATEE": 40, "MARION": 41, "MARTIN": 42, "MONROE": 43, "NASSAU": 44,
    "OKALOOSA": 45, "OKEECHOBEE": 46, "ORANGE": 47, "OSCEOLA": 48, "PALM BEACH": 49,
    "PASCO": 50, "PINELLAS": 51, "POLK": 52, "PUTNAM": 53, "SANTA ROSA": 54,
    "SARASOTA": 55, "SEMINOLE": 56, "ST. JOHNS": 57, "ST. LUCIE": 58, "SUMTER": 59,
    "SUWANNEE": 60, "TAYLOR": 61, "UNION": 62, "VOLUSIA": 63, "WAKULLA": 64,
    "WALTON": 65, "WASHINGTON": 66
}


def get_parcel_by_coordinates(lat: float, lon: float, county: str = None) -> Dict[str, Any]:
    """
    Get parcel data for coordinates.

    NOTE: As of Jan 2026, the FL DOT parcel service requires authentication.
    This function now returns helpful links to county property appraiser sites.

    Args:
        lat: Latitude
        lon: Longitude
        county: Optional county name

    Returns:
        Dict with lookup links for manual search
    """
    # County property appraiser websites for manual lookup
    county_links = {
        "MIAMI-DADE": "https://www.miamidade.gov/pa/",
        "BROWARD": "https://www.bcpa.net/",
        "PALM BEACH": "https://www.pbcgov.org/papa/",
        "MONROE": "https://www.mcpafl.org/",
        "COLLIER": "https://www.collierappraiser.com/",
        "LEE": "https://www.leepa.org/",
        "HILLSBOROUGH": "https://www.hcpafl.org/",
        "ORANGE": "https://www.ocpafl.org/",
        "DUVAL": "https://www.coj.net/departments/property-appraiser"
    }

    # Determine likely county based on coordinates (rough bounding boxes)
    likely_county = "MIAMI-DADE"  # Default for South Florida
    if lat > 26.3:
        likely_county = "PALM BEACH"
    elif lat > 25.9:
        likely_county = "BROWARD"

    return {
        "found": False,
        "note": "FL DOT parcel API now requires authentication",
        "manual_lookup": county_links.get(likely_county, county_links["MIAMI-DADE"]),
        "all_county_links": county_links,
        "coordinates": {"latitude": lat, "longitude": lon},
        "likely_county": likely_county,
        "tip": f"Visit {county_links.get(likely_county)} and search by address or coordinates"
    }


def query_parcel_layer(lat: float, lon: float, layer_id: int, county_name: str) -> Optional[Dict[str, Any]]:
    """
    Query a specific county parcel layer
    """
    url = f"https://gis.fdot.gov/arcgis/rest/services/Parcels/FeatureServer/{layer_id}/query"

    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "true",
        "f": "json"
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("features") and len(data["features"]) > 0:
            feature = data["features"][0]
            attrs = feature.get("attributes", {})
            geometry = feature.get("geometry", {})

            # Extract common fields (field names vary by county)
            parcel_data = {
                "found": True,
                "county": county_name,
                "parcel_id": extract_field(attrs, ["PARCELNO", "PARCEL_ID", "FOESSION", "PIN", "PARCEL"]),
                "folio": extract_field(attrs, ["FOESSION", "FOLIO", "PARCELNO"]),
                "owner_name": extract_field(attrs, ["OWNERNAME", "OWNER", "OWNER_NAME", "NAME"]),
                "site_address": extract_field(attrs, ["SITEADDR", "SITE_ADDR", "ADDRESS", "PHYSICAL_ADDRESS"]),
                "site_city": extract_field(attrs, ["SITECITY", "CITY"]),
                "site_zip": extract_field(attrs, ["SITEZIP", "ZIP", "ZIPCODE"]),
                "legal_description": extract_field(attrs, ["LEGALDESC", "LEGAL", "LEGAL_DESC"]),
                "land_use": extract_field(attrs, ["LANDUSE", "LAND_USE", "USE_CODE", "DOR_UC"]),
                "land_use_desc": extract_field(attrs, ["LUNAME", "USE_DESC", "LAND_USE_DESC"]),
                "zoning": extract_field(attrs, ["ZONING", "ZONE", "ZONE_CODE"]),
                "acreage": extract_numeric(attrs, ["ACRES", "ACREAGE", "GISACRES", "CALC_ACRES"]),
                "sqft": extract_numeric(attrs, ["SQFT", "LOTSQFT", "LOT_SQFT"]),
                "just_value": extract_numeric(attrs, ["JUSTVALUE", "JUST_VALUE", "TOTAL_VALUE", "VALUE"]),
                "assessed_value": extract_numeric(attrs, ["ASMTVALUE", "ASSESSED", "ASSESSED_VALUE"]),
                "year_built": extract_field(attrs, ["YEARBUILT", "YEAR_BUILT", "YR_BUILT"]),
                "bedrooms": extract_numeric(attrs, ["BEDROOMS", "BEDS"]),
                "bathrooms": extract_numeric(attrs, ["BATHROOMS", "BATHS"]),
                "building_sqft": extract_numeric(attrs, ["BLDGSQFT", "BLDG_SQFT", "LIVING_AREA"]),
                "coordinates": {"latitude": lat, "longitude": lon},
                "geometry_rings": geometry.get("rings", []),
                "raw_attributes": attrs,
                "source": "Florida DOT Parcel Service"
            }

            # Calculate lot dimensions if geometry available
            if parcel_data["geometry_rings"]:
                parcel_data["lot_dimensions"] = estimate_lot_dimensions(parcel_data["geometry_rings"])

            return parcel_data

        return None

    except Exception as e:
        return None


def extract_field(attrs: dict, field_names: list) -> Optional[str]:
    """Try multiple field names and return first match"""
    for name in field_names:
        value = attrs.get(name)
        if value and str(value).strip() and str(value) != "None":
            return str(value).strip()
    return None


def extract_numeric(attrs: dict, field_names: list) -> Optional[float]:
    """Try multiple field names and return first numeric match"""
    for name in field_names:
        value = attrs.get(name)
        if value is not None:
            try:
                num = float(value)
                if num > 0:
                    return num
            except (ValueError, TypeError):
                continue
    return None


def estimate_lot_dimensions(rings: list) -> Dict[str, float]:
    """
    Estimate lot dimensions from parcel geometry
    Returns approximate width, depth, and perimeter
    """
    if not rings or not rings[0]:
        return {}

    coords = rings[0]
    if len(coords) < 3:
        return {}

    # Calculate bounding box
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    # Convert to approximate feet (at Florida latitudes)
    # 1 degree latitude ≈ 364,000 feet
    # 1 degree longitude ≈ 288,000 feet (at 25°N)
    lat_center = (min_lat + max_lat) / 2
    lon_scale = 364000 * abs(math.cos(math.radians(lat_center))) if 'math' in dir() else 288000

    width_ft = (max_lon - min_lon) * 288000  # Approximate for FL
    depth_ft = (max_lat - min_lat) * 364000

    # Calculate perimeter
    perimeter_ft = 0
    for i in range(len(coords)):
        p1 = coords[i]
        p2 = coords[(i + 1) % len(coords)]
        dx = (p2[0] - p1[0]) * 288000
        dy = (p2[1] - p1[1]) * 364000
        perimeter_ft += (dx**2 + dy**2)**0.5

    return {
        "approx_width_ft": round(width_ft, 1),
        "approx_depth_ft": round(depth_ft, 1),
        "approx_perimeter_ft": round(perimeter_ft, 1),
        "note": "Approximate dimensions from GIS boundary"
    }


def get_adjacent_parcels(lat: float, lon: float, radius_ft: float = 200) -> List[Dict[str, Any]]:
    """
    Get parcels within a radius of a point
    Useful for context analysis
    """
    # Convert radius to degrees (approximate)
    radius_deg = radius_ft / 364000

    # This would require more complex geometry queries
    # For now, return the main parcel
    return [get_parcel_by_coordinates(lat, lon)]


def format_parcel_report(parcel: Dict[str, Any]) -> str:
    """Format parcel data as a readable report"""
    if not parcel.get("found"):
        return f"Parcel not found: {parcel.get('error', 'Unknown error')}"

    lines = [
        "=" * 60,
        "PARCEL REPORT",
        "=" * 60,
        f"County: {parcel.get('county', 'Unknown')}",
        f"Parcel ID: {parcel.get('parcel_id', 'N/A')}",
        f"Folio: {parcel.get('folio', 'N/A')}",
        "",
        "OWNER & ADDRESS:",
        f"  Owner: {parcel.get('owner_name', 'N/A')}",
        f"  Site Address: {parcel.get('site_address', 'N/A')}",
        f"  City: {parcel.get('site_city', 'N/A')} {parcel.get('site_zip', '')}",
        "",
        "LOT INFORMATION:",
        f"  Acreage: {parcel.get('acreage', 'N/A')}",
        f"  Square Feet: {parcel.get('sqft', 'N/A'):,.0f}" if parcel.get('sqft') else "  Square Feet: N/A",
        f"  Land Use: {parcel.get('land_use_desc', parcel.get('land_use', 'N/A'))}",
        f"  Zoning: {parcel.get('zoning', 'N/A')}",
        "",
        "VALUES:",
        f"  Just Value: ${parcel.get('just_value', 0):,.0f}" if parcel.get('just_value') else "  Just Value: N/A",
        f"  Assessed Value: ${parcel.get('assessed_value', 0):,.0f}" if parcel.get('assessed_value') else "  Assessed Value: N/A",
    ]

    if parcel.get("year_built"):
        lines.extend([
            "",
            "BUILDING:",
            f"  Year Built: {parcel.get('year_built')}",
            f"  Building SF: {parcel.get('building_sqft', 'N/A'):,.0f}" if parcel.get('building_sqft') else "  Building SF: N/A",
            f"  Bedrooms: {parcel.get('bedrooms', 'N/A')}",
            f"  Bathrooms: {parcel.get('bathrooms', 'N/A')}",
        ])

    if parcel.get("lot_dimensions"):
        dims = parcel["lot_dimensions"]
        lines.extend([
            "",
            "LOT DIMENSIONS (approximate):",
            f"  Width: ~{dims.get('approx_width_ft', 'N/A')} ft",
            f"  Depth: ~{dims.get('approx_depth_ft', 'N/A')} ft",
            f"  Perimeter: ~{dims.get('approx_perimeter_ft', 'N/A')} ft",
        ])

    lines.extend([
        "",
        f"Legal Description: {parcel.get('legal_description', 'N/A')[:100]}..."
            if parcel.get('legal_description') and len(parcel.get('legal_description', '')) > 100
            else f"Legal Description: {parcel.get('legal_description', 'N/A')}",
        "",
        "=" * 60,
        f"Source: {parcel.get('source', 'FL DOT')}",
        f"Coordinates: {parcel.get('coordinates', {})}",
        "=" * 60
    ])

    return "\n".join(lines)


# Import math for lot dimension calculations
import math


if __name__ == "__main__":
    # Test with Miami coordinates
    lat, lon = 25.7617, -80.1918
    print(f"\nLooking up parcel at ({lat}, {lon})...\n")

    parcel = get_parcel_by_coordinates(lat, lon)
    print(format_parcel_report(parcel))

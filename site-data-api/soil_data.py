#!/usr/bin/env python3
"""
USDA Soil Survey API Integration
Free, no API key required

Uses USDA Soil Data Access (SDA) REST service
"""

import requests
from typing import Optional, Dict, Any


# Descriptions for soil properties
DRAINAGE_DESCRIPTIONS = {
    "Excessively drained": "Water removed very rapidly; sandy soils, good for foundations",
    "Somewhat excessively drained": "Water removed rapidly; coarse textures",
    "Well drained": "Water removed readily; ideal for most construction",
    "Moderately well drained": "Water removed somewhat slowly; may need drainage",
    "Somewhat poorly drained": "Water removed slowly; high water table possible",
    "Poorly drained": "Water removed very slowly; wetland indicators likely",
    "Very poorly drained": "Water at/near surface most of year; wetland"
}

HYDRO_GROUP_DESCRIPTIONS = {
    "A": "Low runoff potential - Sandy, deep, well drained",
    "B": "Moderate infiltration - Moderately deep, moderately drained",
    "C": "Slow infiltration - Layer impeding downward movement",
    "D": "High runoff potential - Clay, high water table, shallow to bedrock",
    "A/D": "Drained/undrained - A if drained, D if not",
    "B/D": "Drained/undrained - B if drained, D if not",
    "C/D": "Drained/undrained - C if drained, D if not"
}


def get_soil_data(lat: float, lon: float) -> Dict[str, Any]:
    """
    Get soil data for a coordinate using USDA Soil Data Access
    Returns soil type, drainage class, and engineering properties

    Free, no API key required
    """
    url = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"

    # Step 1: Get the mapunit key for this location
    mukey = _get_mukey_for_point(lat, lon)

    if not mukey:
        return {
            "soil_name": "No data available",
            "drainage_class": "Unknown",
            "drainage_description": "Soil survey data not available (may be urban area or water)",
            "hydrologic_group": "Unknown",
            "hydrologic_description": "Unknown",
            "engineering_notes": "Manual soil investigation recommended",
            "source": "USDA NRCS Soil Data Access"
        }

    # Step 2: Get soil properties using the mukey
    query = f"""
    SELECT TOP 1
        mu.muname AS soil_name,
        c.compname AS component_name,
        c.comppct_r AS component_percent,
        c.drainagecl AS drainage_class,
        c.hydgrp AS hydrologic_group,
        c.slope_r AS slope_percent,
        c.taxclname AS taxonomic_class,
        c.taxorder AS soil_order
    FROM mapunit mu
    INNER JOIN component c ON c.mukey = mu.mukey
    WHERE mu.mukey = '{mukey}' AND c.majcompflag = 'Yes'
    ORDER BY c.comppct_r DESC
    """

    try:
        response = requests.post(
            url,
            data={"query": query, "format": "JSON+COLUMNNAME"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        # Parse table with column names in first row
        if data.get("Table") and len(data["Table"]) > 1:
            headers = [h.lower() for h in data["Table"][0]]
            values = data["Table"][1]

            # Create dict from headers and values
            row = dict(zip(headers, values))

            drainage = row.get("drainage_class") or "Unknown"
            hydro = row.get("hydrologic_group") or "Unknown"

            return {
                "soil_name": row.get("soil_name") or "Unknown",
                "component_name": row.get("component_name") or "Unknown",
                "component_percent": row.get("component_percent"),
                "drainage_class": drainage,
                "drainage_description": DRAINAGE_DESCRIPTIONS.get(drainage, "Unknown drainage classification"),
                "hydrologic_group": hydro,
                "hydrologic_description": HYDRO_GROUP_DESCRIPTIONS.get(hydro, "Unknown hydrologic group"),
                "slope_percent": row.get("slope_percent"),
                "taxonomic_class": row.get("taxonomic_class") or "Unknown",
                "soil_order": row.get("soil_order") or "Unknown",
                "engineering_notes": get_engineering_notes(drainage, hydro),
                "source": "USDA NRCS Soil Data Access"
            }

    except Exception as e:
        print(f"Soil properties query error: {e}")

    return {
        "soil_name": "Query failed",
        "drainage_class": "Unknown",
        "drainage_description": "Could not retrieve soil properties",
        "hydrologic_group": "Unknown",
        "hydrologic_description": "Unknown",
        "engineering_notes": "Manual soil investigation required",
        "source": "USDA NRCS Soil Data Access"
    }


def _get_mukey_for_point(lat: float, lon: float) -> Optional[str]:
    """Get the map unit key for a point location"""
    url = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"

    # Use the SDA spatial function
    query = f"""
    SELECT TOP 1 mukey
    FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('POINT({lon} {lat})')
    """

    try:
        response = requests.post(
            url,
            data={"query": query, "format": "JSON+COLUMNNAME"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            # Format is {"Table": [["col1", "col2"], ["val1", "val2"]]}
            # With COLUMNNAME format, first row is headers
            if data.get("Table") and len(data["Table"]) > 1:
                headers = data["Table"][0]
                values = data["Table"][1]
                mukey_idx = headers.index("mukey") if "mukey" in headers else 0
                return str(values[mukey_idx])

    except Exception as e:
        print(f"Mukey lookup error: {e}")

    return None


def get_engineering_notes(drainage: str, hydro_group: str) -> str:
    """Generate engineering notes based on soil properties"""
    notes = []

    # Drainage-based notes
    if drainage in ["Poorly drained", "Very poorly drained"]:
        notes.append("HIGH WATER TABLE - Dewatering may be required during construction")
        notes.append("Consider elevated foundation or pile system")
        notes.append("Potential wetland - environmental review recommended")
    elif drainage == "Somewhat poorly drained":
        notes.append("Seasonal high water table possible")
        notes.append("French drains or foundation waterproofing recommended")
    elif drainage in ["Excessively drained", "Somewhat excessively drained"]:
        notes.append("Sandy soil - check bearing capacity")
        notes.append("Low water retention - irrigation may be needed for landscaping")
    elif drainage in ["Well drained", "Moderately well drained"]:
        notes.append("Generally suitable for standard foundation systems")

    # Hydrologic group notes
    if hydro_group in ["D", "C/D", "B/D", "A/D"]:
        notes.append("High runoff potential - stormwater management critical")
        notes.append("Consider retention/detention requirements")
    elif hydro_group == "A":
        notes.append("High infiltration - pervious pavement may be viable")

    # Florida-specific
    notes.append("FL: Verify depth to limestone/water table with geotechnical report")

    return "; ".join(notes) if notes else "Standard construction practices applicable"


def get_soil_layers(lat: float, lon: float) -> list:
    """
    Get detailed soil horizon/layer data
    Returns depth and properties of each soil layer
    """
    mukey = _get_mukey_for_point(lat, lon)
    if not mukey:
        return []

    url = "https://SDMDataAccess.sc.egov.usda.gov/Tabular/post.rest"

    query = f"""
    SELECT
        h.hzname AS horizon_name,
        h.hzdept_r AS depth_top_cm,
        h.hzdepb_r AS depth_bottom_cm,
        h.sandtotal_r AS sand_pct,
        h.silttotal_r AS silt_pct,
        h.claytotal_r AS clay_pct,
        t.texcl AS texture_class
    FROM mapunit mu
    INNER JOIN component c ON c.mukey = mu.mukey
    INNER JOIN chorizon h ON h.cokey = c.cokey
    LEFT JOIN chtexturegrp t ON t.chkey = h.chkey AND t.rvindicator = 'Yes'
    WHERE mu.mukey = '{mukey}' AND c.majcompflag = 'Yes'
    ORDER BY h.hzdept_r
    """

    try:
        response = requests.post(
            url,
            data={"query": query, "format": "JSON+COLUMNNAME"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        layers = []
        if data.get("Table") and len(data["Table"]) > 1:
            headers = [h.lower() for h in data["Table"][0]]
            for values in data["Table"][1:]:
                row = dict(zip(headers, values))
                depth_top_cm = row.get("depth_top_cm") or 0
                depth_bottom_cm = row.get("depth_bottom_cm") or 0

                layers.append({
                    "horizon": row.get("horizon_name") or "",
                    "depth_top_in": round(float(depth_top_cm) * 0.393701, 1) if depth_top_cm else 0,
                    "depth_bottom_in": round(float(depth_bottom_cm) * 0.393701, 1) if depth_bottom_cm else 0,
                    "texture": row.get("texture_class") or "Unknown",
                    "sand_pct": row.get("sand_pct"),
                    "silt_pct": row.get("silt_pct"),
                    "clay_pct": row.get("clay_pct")
                })

        return layers

    except Exception as e:
        print(f"Soil layers query error: {e}")
        return []


if __name__ == "__main__":
    # Test with a Florida location that should have soil data
    # Using a more rural area that's more likely to have data
    lat, lon = 26.1224, -80.1373  # Fort Lauderdale area
    print(f"\nTesting soil data for ({lat}, {lon})...\n")

    soil = get_soil_data(lat, lon)
    print("SOIL DATA:")
    for key, value in soil.items():
        print(f"  {key}: {value}")

    print("\nSOIL LAYERS:")
    layers = get_soil_layers(lat, lon)
    if layers:
        for layer in layers:
            print(f"  {layer['depth_top_in']}\"-{layer['depth_bottom_in']}\": {layer['texture']}")
    else:
        print("  No layer data available")

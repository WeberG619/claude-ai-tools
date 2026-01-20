#!/usr/bin/env python3
"""
Overpass API (OpenStreetMap) Integration
100% Free, no API key, no limits

Queries surrounding context for a site:
- Nearby buildings (footprints, heights, types)
- Roads and highways (noise, access)
- Transit stops (walkability)
- Amenities (schools, hospitals, retail)
- Infrastructure (power lines, utilities)
- Water features
- Parks and green space

Essential for understanding site context in architecture projects.
"""

import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
import math


# Overpass API endpoints (multiple for redundancy)
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def get_site_context(lat: float, lon: float, radius_meters: int = 500) -> Dict[str, Any]:
    """
    Get comprehensive site context from OpenStreetMap

    Args:
        lat: Latitude
        lon: Longitude
        radius_meters: Search radius (default 500m, ~1/3 mile)

    Returns:
        Dict with buildings, roads, transit, amenities, etc.
    """
    result = {
        "buildings": [],
        "roads": [],
        "transit": [],
        "amenities": {},
        "water": [],
        "infrastructure": [],
        "parks": [],
        "summary": {},
        "coordinates": {"latitude": lat, "longitude": lon},
        "radius_meters": radius_meters,
        "timestamp": datetime.now().isoformat(),
        "source": "OpenStreetMap via Overpass API"
    }

    # Build Overpass query for all relevant features
    query = _build_comprehensive_query(lat, lon, radius_meters)

    # Try each endpoint until one works
    data = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = requests.post(
                endpoint,
                data={"data": query},
                timeout=60,
                headers={"User-Agent": "SiteDataAPI/1.0 (Architecture Tool)"}
            )
            if response.status_code == 200:
                data = response.json()
                break
        except Exception as e:
            continue

    if not data:
        result["error"] = "Could not reach Overpass API"
        return result

    # Parse results
    elements = data.get("elements", [])

    # Process each element
    for element in elements:
        tags = element.get("tags", {})
        element_type = _classify_element(tags)

        if element_type == "building":
            result["buildings"].append(_parse_building(element))
        elif element_type == "road":
            result["roads"].append(_parse_road(element))
        elif element_type == "transit":
            result["transit"].append(_parse_transit(element))
        elif element_type == "water":
            result["water"].append(_parse_water(element))
        elif element_type == "park":
            result["parks"].append(_parse_park(element))
        elif element_type == "infrastructure":
            result["infrastructure"].append(_parse_infrastructure(element))
        elif element_type == "amenity":
            amenity_type = tags.get("amenity", "other")
            if amenity_type not in result["amenities"]:
                result["amenities"][amenity_type] = []
            result["amenities"][amenity_type].append(_parse_amenity(element))

    # Generate summary
    result["summary"] = _generate_context_summary(result, lat, lon)

    return result


def _build_comprehensive_query(lat: float, lon: float, radius: int) -> str:
    """Build Overpass QL query for all relevant features"""
    return f"""
[out:json][timeout:45];
(
  // Buildings
  way["building"](around:{radius},{lat},{lon});
  relation["building"](around:{radius},{lat},{lon});

  // Roads
  way["highway"](around:{radius},{lat},{lon});

  // Transit
  node["public_transport"](around:{radius},{lat},{lon});
  node["railway"="station"](around:{radius},{lat},{lon});
  node["railway"="halt"](around:{radius},{lat},{lon});
  node["amenity"="bus_station"](around:{radius},{lat},{lon});
  node["highway"="bus_stop"](around:{radius},{lat},{lon});

  // Amenities
  node["amenity"](around:{radius},{lat},{lon});
  way["amenity"](around:{radius},{lat},{lon});

  // Schools
  way["amenity"="school"](around:{radius},{lat},{lon});
  way["amenity"="university"](around:{radius},{lat},{lon});
  way["amenity"="college"](around:{radius},{lat},{lon});

  // Healthcare
  node["amenity"="hospital"](around:{radius},{lat},{lon});
  way["amenity"="hospital"](around:{radius},{lat},{lon});
  node["amenity"="clinic"](around:{radius},{lat},{lon});

  // Retail
  node["shop"](around:{radius},{lat},{lon});
  way["shop"](around:{radius},{lat},{lon});

  // Water features
  way["natural"="water"](around:{radius},{lat},{lon});
  way["waterway"](around:{radius},{lat},{lon});
  relation["natural"="water"](around:{radius},{lat},{lon});

  // Parks and recreation
  way["leisure"="park"](around:{radius},{lat},{lon});
  way["leisure"="playground"](around:{radius},{lat},{lon});
  way["landuse"="recreation_ground"](around:{radius},{lat},{lon});

  // Infrastructure
  way["power"="line"](around:{radius},{lat},{lon});
  node["power"="tower"](around:{radius},{lat},{lon});
  node["power"="substation"](around:{radius},{lat},{lon});
  way["man_made"="pipeline"](around:{radius},{lat},{lon});
);
out body;
>;
out skel qt;
"""


def _classify_element(tags: Dict) -> str:
    """Classify an OSM element by type"""
    if "building" in tags:
        return "building"
    if "highway" in tags:
        highway_type = tags["highway"]
        if highway_type == "bus_stop":
            return "transit"
        return "road"
    if "public_transport" in tags or "railway" in tags:
        return "transit"
    if "natural" in tags and tags["natural"] == "water":
        return "water"
    if "waterway" in tags:
        return "water"
    if "leisure" in tags and tags["leisure"] in ["park", "playground", "garden"]:
        return "park"
    if "landuse" in tags and tags["landuse"] == "recreation_ground":
        return "park"
    if "power" in tags or "man_made" in tags:
        return "infrastructure"
    if "amenity" in tags or "shop" in tags:
        return "amenity"
    return "other"


def _parse_building(element: Dict) -> Dict:
    """Parse building element"""
    tags = element.get("tags", {})

    building_info = {
        "id": element.get("id"),
        "type": tags.get("building", "yes"),
        "name": tags.get("name"),
        "height": None,
        "levels": None,
        "use": None,
    }

    # Parse height
    if "height" in tags:
        try:
            height_str = tags["height"].replace("m", "").replace("'", "").strip()
            building_info["height_m"] = float(height_str)
            building_info["height_ft"] = round(float(height_str) * 3.28084, 1)
        except:
            pass

    # Parse levels
    if "building:levels" in tags:
        try:
            building_info["levels"] = int(tags["building:levels"])
        except:
            pass

    # Determine use
    building_type = tags.get("building", "")
    if building_type in ["residential", "apartments", "house", "detached"]:
        building_info["use"] = "residential"
    elif building_type in ["commercial", "retail", "office"]:
        building_info["use"] = "commercial"
    elif building_type in ["industrial", "warehouse"]:
        building_info["use"] = "industrial"
    elif tags.get("amenity"):
        building_info["use"] = tags.get("amenity")

    return building_info


def _parse_road(element: Dict) -> Dict:
    """Parse road element"""
    tags = element.get("tags", {})

    road_info = {
        "id": element.get("id"),
        "type": tags.get("highway"),
        "name": tags.get("name"),
        "lanes": None,
        "speed_limit": None,
        "surface": tags.get("surface"),
        "noise_level": "unknown"
    }

    # Parse lanes
    if "lanes" in tags:
        try:
            road_info["lanes"] = int(tags["lanes"])
        except:
            pass

    # Parse speed limit
    if "maxspeed" in tags:
        road_info["speed_limit"] = tags["maxspeed"]

    # Estimate noise level based on road type
    highway_type = tags.get("highway", "")
    if highway_type in ["motorway", "trunk"]:
        road_info["noise_level"] = "high"
    elif highway_type in ["primary", "secondary"]:
        road_info["noise_level"] = "moderate"
    elif highway_type in ["tertiary", "residential"]:
        road_info["noise_level"] = "low"
    elif highway_type in ["footway", "cycleway", "path"]:
        road_info["noise_level"] = "minimal"

    return road_info


def _parse_transit(element: Dict) -> Dict:
    """Parse transit element"""
    tags = element.get("tags", {})

    transit_info = {
        "id": element.get("id"),
        "type": None,
        "name": tags.get("name"),
        "operator": tags.get("operator"),
        "routes": tags.get("route_ref"),
    }

    # Determine transit type
    if tags.get("railway") in ["station", "halt"]:
        transit_info["type"] = "rail"
    elif tags.get("highway") == "bus_stop" or tags.get("amenity") == "bus_station":
        transit_info["type"] = "bus"
    elif tags.get("public_transport") == "station":
        transit_info["type"] = tags.get("station", "transit")
    else:
        transit_info["type"] = tags.get("public_transport", "transit")

    # Get coordinates
    if element.get("lat") and element.get("lon"):
        transit_info["lat"] = element["lat"]
        transit_info["lon"] = element["lon"]

    return transit_info


def _parse_water(element: Dict) -> Dict:
    """Parse water feature"""
    tags = element.get("tags", {})

    return {
        "id": element.get("id"),
        "type": tags.get("natural") or tags.get("waterway", "water"),
        "name": tags.get("name"),
    }


def _parse_park(element: Dict) -> Dict:
    """Parse park/green space"""
    tags = element.get("tags", {})

    return {
        "id": element.get("id"),
        "type": tags.get("leisure") or tags.get("landuse", "park"),
        "name": tags.get("name"),
        "access": tags.get("access", "public"),
    }


def _parse_infrastructure(element: Dict) -> Dict:
    """Parse infrastructure element"""
    tags = element.get("tags", {})

    infra_info = {
        "id": element.get("id"),
        "type": None,
        "voltage": tags.get("voltage"),
        "operator": tags.get("operator"),
    }

    if "power" in tags:
        infra_info["type"] = f"power_{tags['power']}"
    elif "man_made" in tags:
        infra_info["type"] = tags["man_made"]

    return infra_info


def _parse_amenity(element: Dict) -> Dict:
    """Parse amenity element"""
    tags = element.get("tags", {})

    amenity_info = {
        "id": element.get("id"),
        "type": tags.get("amenity") or tags.get("shop"),
        "name": tags.get("name"),
        "cuisine": tags.get("cuisine"),  # For restaurants
        "healthcare": tags.get("healthcare"),  # For medical
    }

    # Get coordinates
    if element.get("lat") and element.get("lon"):
        amenity_info["lat"] = element["lat"]
        amenity_info["lon"] = element["lon"]

    return amenity_info


def _generate_context_summary(data: Dict, lat: float, lon: float) -> Dict:
    """Generate summary of site context"""
    summary = {
        "building_count": len(data["buildings"]),
        "building_types": {},
        "transit_access": "none",
        "transit_stops": len(data["transit"]),
        "road_noise_risk": "low",
        "major_roads_nearby": 0,
        "amenity_count": sum(len(v) for v in data["amenities"].values()),
        "water_features": len(data["water"]),
        "parks_nearby": len(data["parks"]),
        "infrastructure_concerns": [],
        "walkability_indicators": [],
    }

    # Count building types
    for building in data["buildings"]:
        use = building.get("use") or building.get("type", "unknown")
        summary["building_types"][use] = summary["building_types"].get(use, 0) + 1

    # Analyze transit access
    if data["transit"]:
        rail_stops = [t for t in data["transit"] if t.get("type") == "rail"]
        bus_stops = [t for t in data["transit"] if t.get("type") == "bus"]

        if rail_stops:
            summary["transit_access"] = "excellent"
            summary["walkability_indicators"].append(f"Rail station within {data['radius_meters']}m")
        elif len(bus_stops) >= 3:
            summary["transit_access"] = "good"
            summary["walkability_indicators"].append(f"{len(bus_stops)} bus stops nearby")
        elif bus_stops:
            summary["transit_access"] = "moderate"
            summary["walkability_indicators"].append("Bus service available")

    # Analyze road noise
    high_noise_roads = [r for r in data["roads"] if r.get("noise_level") in ["high", "moderate"]]
    if high_noise_roads:
        summary["major_roads_nearby"] = len(high_noise_roads)
        highway_types = [r.get("type") for r in high_noise_roads]
        if any(t in ["motorway", "trunk"] for t in highway_types):
            summary["road_noise_risk"] = "high"
            summary["infrastructure_concerns"].append("Major highway nearby - noise mitigation may be needed")
        elif any(t in ["primary", "secondary"] for t in highway_types):
            summary["road_noise_risk"] = "moderate"
            summary["infrastructure_concerns"].append("Arterial road nearby - consider noise impact")

    # Check infrastructure concerns
    power_lines = [i for i in data["infrastructure"] if "power" in str(i.get("type", ""))]
    if power_lines:
        summary["infrastructure_concerns"].append(f"{len(power_lines)} power line segments nearby - check easements")

    # Walkability indicators
    if data["amenities"].get("restaurant") or data["amenities"].get("cafe"):
        count = len(data["amenities"].get("restaurant", [])) + len(data["amenities"].get("cafe", []))
        summary["walkability_indicators"].append(f"{count} restaurants/cafes")

    if data["amenities"].get("school"):
        summary["walkability_indicators"].append(f"{len(data['amenities']['school'])} schools")

    shops = data["amenities"].get("shop", [])
    if shops:
        summary["walkability_indicators"].append(f"{len(shops)} retail shops")

    if data["parks"]:
        summary["walkability_indicators"].append(f"{len(data['parks'])} parks/green spaces")

    # Overall walkability assessment
    walkability_score = 0
    if summary["transit_access"] in ["excellent", "good"]:
        walkability_score += 2
    if summary["amenity_count"] > 10:
        walkability_score += 2
    elif summary["amenity_count"] > 5:
        walkability_score += 1
    if data["parks"]:
        walkability_score += 1

    if walkability_score >= 4:
        summary["walkability"] = "Excellent"
    elif walkability_score >= 2:
        summary["walkability"] = "Good"
    elif walkability_score >= 1:
        summary["walkability"] = "Moderate"
    else:
        summary["walkability"] = "Car-dependent"

    return summary


def get_nearby_buildings_detailed(lat: float, lon: float, radius_meters: int = 200) -> List[Dict]:
    """
    Get detailed information about nearby buildings
    Smaller radius for more focused analysis
    """
    query = f"""
[out:json][timeout:30];
(
  way["building"](around:{radius_meters},{lat},{lon});
  relation["building"](around:{radius_meters},{lat},{lon});
);
out body;
>;
out skel qt;
"""

    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = requests.post(
                endpoint,
                data={"data": query},
                timeout=30,
                headers={"User-Agent": "SiteDataAPI/1.0"}
            )
            if response.status_code == 200:
                data = response.json()
                buildings = []
                for element in data.get("elements", []):
                    if element.get("tags", {}).get("building"):
                        buildings.append(_parse_building(element))
                return buildings
        except:
            continue

    return []


def get_transit_walkscore(lat: float, lon: float) -> Dict[str, Any]:
    """
    Calculate a simple transit/walk score based on nearby amenities
    """
    # Get context with larger radius for transit
    context = get_site_context(lat, lon, radius_meters=800)

    score = {
        "transit_score": 0,
        "walk_score": 0,
        "bike_score": 0,
        "factors": []
    }

    summary = context.get("summary", {})

    # Transit score (0-100)
    transit_access = summary.get("transit_access", "none")
    transit_stops = summary.get("transit_stops", 0)

    if transit_access == "excellent":
        score["transit_score"] = 80 + min(transit_stops * 2, 20)
        score["factors"].append("Rail transit accessible")
    elif transit_access == "good":
        score["transit_score"] = 60 + min(transit_stops * 3, 25)
        score["factors"].append("Good bus service")
    elif transit_access == "moderate":
        score["transit_score"] = 30 + min(transit_stops * 5, 30)
        score["factors"].append("Limited transit options")
    else:
        score["transit_score"] = 10
        score["factors"].append("Minimal transit access")

    # Walk score (0-100)
    amenity_count = summary.get("amenity_count", 0)
    parks = summary.get("parks_nearby", 0)

    base_walk = min(amenity_count * 3, 50)
    base_walk += min(parks * 10, 20)
    if transit_access in ["excellent", "good"]:
        base_walk += 20

    score["walk_score"] = min(base_walk, 100)

    if score["walk_score"] >= 70:
        score["factors"].append("Very walkable area")
    elif score["walk_score"] >= 50:
        score["factors"].append("Somewhat walkable")
    else:
        score["factors"].append("Car-dependent area")

    # Bike score (estimate)
    # Check for bike infrastructure
    score["bike_score"] = max(score["walk_score"] - 10, 20)

    return score


def format_context_report(data: Dict[str, Any]) -> str:
    """Format context data as readable report"""
    summary = data.get("summary", {})

    lines = [
        "=" * 60,
        "SITE CONTEXT REPORT (OpenStreetMap)",
        "=" * 60,
        "",
        f"Search Radius: {data.get('radius_meters', 500)}m ({data.get('radius_meters', 500) * 3.28084:.0f}ft)",
        "",
        "BUILDINGS NEARBY:",
        f"  Total: {summary.get('building_count', 0)} structures",
    ]

    # Building type breakdown
    if summary.get("building_types"):
        for btype, count in sorted(summary["building_types"].items(), key=lambda x: -x[1])[:5]:
            lines.append(f"    • {btype}: {count}")

    lines.extend([
        "",
        "TRANSIT ACCESS:",
        f"  Rating: {summary.get('transit_access', 'unknown').upper()}",
        f"  Stops Nearby: {summary.get('transit_stops', 0)}",
    ])

    # Transit details
    for stop in data.get("transit", [])[:5]:
        name = stop.get("name") or f"{stop.get('type', 'Stop')}"
        lines.append(f"    • {name} ({stop.get('type', 'transit')})")

    lines.extend([
        "",
        "ROAD ANALYSIS:",
        f"  Noise Risk: {summary.get('road_noise_risk', 'unknown').upper()}",
        f"  Major Roads: {summary.get('major_roads_nearby', 0)}",
    ])

    # Road details
    major_roads = [r for r in data.get("roads", []) if r.get("noise_level") in ["high", "moderate"]]
    for road in major_roads[:3]:
        name = road.get("name") or road.get("type", "Road")
        lines.append(f"    • {name} ({road.get('type')}) - {road.get('noise_level')} noise")

    lines.extend([
        "",
        "AMENITIES:",
        f"  Total: {summary.get('amenity_count', 0)} locations",
    ])

    # Amenity breakdown
    for atype, items in sorted(data.get("amenities", {}).items(), key=lambda x: -len(x[1]))[:6]:
        lines.append(f"    • {atype}: {len(items)}")

    lines.extend([
        "",
        "GREEN SPACE:",
        f"  Parks Nearby: {summary.get('parks_nearby', 0)}",
    ])
    for park in data.get("parks", [])[:3]:
        name = park.get("name") or "Unnamed park"
        lines.append(f"    • {name}")

    lines.extend([
        "",
        "WATER FEATURES:",
        f"  Count: {summary.get('water_features', 0)}",
    ])

    # Infrastructure concerns
    if summary.get("infrastructure_concerns"):
        lines.extend(["", "INFRASTRUCTURE CONCERNS:"])
        for concern in summary["infrastructure_concerns"]:
            lines.append(f"  ⚠ {concern}")

    lines.extend([
        "",
        "WALKABILITY ASSESSMENT:",
        f"  Rating: {summary.get('walkability', 'Unknown')}",
    ])
    for indicator in summary.get("walkability_indicators", []):
        lines.append(f"    • {indicator}")

    lines.extend([
        "",
        "=" * 60,
        f"Source: {data.get('source', 'OpenStreetMap')}",
        "=" * 60,
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    # Test with Goulds, FL location
    lat, lon = 25.5659, -80.3827
    print(f"\nGetting site context for ({lat}, {lon})...\n")

    data = get_site_context(lat, lon, radius_meters=500)
    print(format_context_report(data))

    print("\n\nTransit/Walk Score:")
    scores = get_transit_walkscore(lat, lon)
    print(f"  Transit Score: {scores['transit_score']}/100")
    print(f"  Walk Score: {scores['walk_score']}/100")
    for factor in scores['factors']:
        print(f"    • {factor}")

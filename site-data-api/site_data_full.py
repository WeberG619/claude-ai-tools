#!/usr/bin/env python3
"""
Complete Site Data API - 11 Free APIs for Architecture/Construction Projects

APIs Integrated (all free, no keys required):
1. Nominatim (OpenStreetMap) - Geocoding
2. Open-Elevation - Elevation data
3. FEMA NFHL - Flood zone lookup
4. Open-Meteo - Weather data
5. USDA Soil Survey - Soil properties
6. Sun Path Calculator - Solar analysis (offline calculations)
7. FL DOT Parcels - Property/parcel data (Florida only)
8. NOAA Storm Data - Hurricane/wind zones, storm history
9. EPA Environmental - Superfund, brownfields, wetlands
10. Census ACS - Demographics, housing, income
11. Overpass/OSM - Site context (buildings, transit, amenities, roads)

Usage:
    python site_data_full.py "123 Main St, Miami, FL 33130"
    python site_data_full.py "123 Main St, Miami, FL 33130" --json
    python site_data_full.py "123 Main St, Miami, FL 33130" --quick  # Skip slow APIs
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import from base module
from site_data import geocode_address, get_elevation, get_flood_zone, get_weather

# Import original additional modules
from soil_data import get_soil_data, get_soil_layers
from sun_path import get_sun_path_data
from parcel_data import get_parcel_by_coordinates

# Import new modules
from noaa_storm_data import get_complete_storm_data
from epa_environmental import get_complete_environmental_data
from census_demographics import get_complete_demographics
from overpass_context import get_site_context, get_transit_walkscore


@dataclass
class CompleteSiteData:
    """Complete site data from all 11 APIs"""
    # Basic info
    address: str
    latitude: float
    longitude: float

    # Original 4 APIs
    elevation_ft: float
    flood_zone: Dict[str, Any]
    weather: Dict[str, Any]

    # Extended APIs (original 3)
    soil: Dict[str, Any]
    sun_path: Dict[str, Any]
    parcel: Dict[str, Any]

    # New APIs (4 more)
    storm_wind: Dict[str, Any]
    environmental: Dict[str, Any]
    demographics: Dict[str, Any]
    site_context: Dict[str, Any]  # Overpass/OSM data

    # Metadata
    timestamp: str
    apis_used: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


def get_complete_site_data(address: str, quick_mode: bool = False,
                           skip_parcel: bool = False,
                           skip_soil: bool = False,
                           skip_storm: bool = False,
                           skip_environmental: bool = False,
                           skip_demographics: bool = False,
                           skip_context: bool = False) -> Optional[CompleteSiteData]:
    """
    Get complete site data from all APIs

    Args:
        address: Street address to look up
        quick_mode: Skip slower APIs (soil, parcel, environmental, demographics, context)
        skip_parcel: Skip parcel lookup (for non-FL addresses)
        skip_soil: Skip soil data lookup
        skip_storm: Skip storm/wind data
        skip_environmental: Skip EPA environmental screening
        skip_demographics: Skip Census demographics
        skip_context: Skip Overpass/OSM site context

    Returns:
        CompleteSiteData object with all available data
    """
    apis_used = []

    print(f"\n{'='*70}")
    print(f"COMPLETE SITE DATA REPORT - 11 APIs")
    print(f"Address: {address}")
    print(f"{'='*70}\n")

    # Step 1: Geocode (required)
    print("1. GEOCODING ADDRESS...")
    geo = geocode_address(address)
    if not geo:
        print("   ERROR: Could not geocode address. Cannot proceed.")
        return None

    lat, lon = geo["latitude"], geo["longitude"]
    print(f"   ✓ Coordinates: {lat:.6f}, {lon:.6f}")
    print(f"   ✓ Resolved: {geo['display_name'][:80]}...")
    apis_used.append("Nominatim/OpenStreetMap")

    # Step 2: Elevation
    print("\n2. GETTING ELEVATION...")
    elevation = get_elevation(lat, lon)
    if elevation is not None:
        print(f"   ✓ Elevation: {elevation} ft above sea level")
        apis_used.append("Open-Elevation")
    else:
        print("   ✗ Elevation: Could not retrieve")
        elevation = 0.0

    # Step 3: FEMA Flood Zone
    print("\n3. CHECKING FEMA FLOOD ZONE...")
    flood = get_flood_zone(lat, lon)
    if flood.get("zone") != "Error":
        print(f"   ✓ Zone: {flood['full_zone']}")
        print(f"   ✓ Risk: {flood['description'][:60]}...")
        apis_used.append("FEMA NFHL")
    else:
        print(f"   ✗ Could not retrieve flood data")

    # Step 4: Weather
    print("\n4. GETTING WEATHER DATA...")
    weather = get_weather(lat, lon)
    if weather.get("current"):
        curr = weather["current"]
        print(f"   ✓ Current: {curr.get('temperature_f')}°F, {curr.get('condition')}")
        print(f"   ✓ Wind: {curr.get('wind_speed_mph')} mph")
        apis_used.append("Open-Meteo")
    else:
        print("   ✗ Weather data unavailable")

    # Step 5: Sun Path (always available - offline calculation)
    print("\n5. CALCULATING SUN PATH...")
    sun_data = get_sun_path_data(lat, lon)
    pos = sun_data["current_position"]
    print(f"   ✓ Current sun: {pos['direction']} ({pos['azimuth']}°), altitude {pos['altitude']}°")
    print(f"   ✓ Today: Sunrise {sun_data['today']['sunrise']}, Sunset {sun_data['today']['sunset']}")
    orient = sun_data["orientation_recommendation"]
    print(f"   ✓ Optimal building axis: {orient['optimal_long_axis']}")
    apis_used.append("Sun Path Calculator (offline)")

    # Step 6: Soil Data (can be slow)
    soil_data = {}
    if not quick_mode and not skip_soil:
        print("\n6. GETTING USDA SOIL DATA...")
        soil_data = get_soil_data(lat, lon)
        if soil_data.get("soil_name") and soil_data["soil_name"] not in ["Error", "No data available"]:
            print(f"   ✓ Soil: {soil_data.get('soil_name', 'Unknown')}")
            print(f"   ✓ Drainage: {soil_data.get('drainage_class', 'Unknown')}")
            print(f"   ✓ Hydro Group: {soil_data.get('hydrologic_group', 'Unknown')}")
            apis_used.append("USDA Soil Data Access")
        else:
            print(f"   ✗ Soil data unavailable for this location")
    else:
        print("\n6. SKIPPING USDA SOIL DATA (quick mode)")

    # Step 7: Parcel Data (Florida only, can be slow)
    parcel_data = {}
    # Check if address is in Florida
    is_florida = any(fl in address.upper() for fl in [", FL", " FL ", "FLORIDA"])

    if not quick_mode and not skip_parcel and is_florida:
        print("\n7. GETTING FL PARCEL DATA...")
        parcel_data = get_parcel_by_coordinates(lat, lon)
        if parcel_data.get("found"):
            print(f"   ✓ County: {parcel_data.get('county', 'Unknown')}")
            print(f"   ✓ Parcel ID: {parcel_data.get('parcel_id', 'Unknown')}")
            print(f"   ✓ Owner: {parcel_data.get('owner_name', 'Unknown')}")
            print(f"   ✓ Zoning: {parcel_data.get('zoning', 'Unknown')}")
            if parcel_data.get("acreage"):
                print(f"   ✓ Acreage: {parcel_data.get('acreage')}")
            apis_used.append("FL DOT Parcel Service")
        else:
            print(f"   ⚠ Parcel API requires auth - manual lookup links provided")
    elif not is_florida:
        print("\n7. SKIPPING PARCEL DATA (Florida only)")
    else:
        print("\n7. SKIPPING PARCEL DATA (quick mode)")

    # Step 8: Storm/Wind Data (NEW)
    storm_data = {}
    if not quick_mode and not skip_storm:
        print("\n8. GETTING NOAA STORM/WIND DATA...")
        storm_data = get_complete_storm_data(lat, lon)
        wind = storm_data.get("wind_design", {})
        print(f"   ✓ Design Wind Speed: {wind.get('design_wind_speed_mph', 'N/A')} mph")
        print(f"   ✓ Exposure Category: {wind.get('exposure_category', 'N/A')}")
        if wind.get("hvhz"):
            print(f"   ⚠ HIGH-VELOCITY HURRICANE ZONE (HVHZ)")
        risk = storm_data.get("storm_history", {}).get("hurricane_risk", {})
        print(f"   ✓ Hurricane Risk: {risk.get('level', 'Unknown')}")
        apis_used.append("NOAA Storm Data + ASCE 7")
    else:
        print("\n8. SKIPPING STORM/WIND DATA (quick mode)")

    # Step 9: Environmental Data (NEW)
    environmental_data = {}
    if not quick_mode and not skip_environmental:
        print("\n9. GETTING EPA ENVIRONMENTAL DATA...")
        environmental_data = get_complete_environmental_data(lat, lon)
        summary = environmental_data.get("summary", {})
        print(f"   ✓ Risk Level: {summary.get('risk_level', 'Unknown')}")
        print(f"   ✓ Phase I ESA Recommended: {'Yes' if summary.get('phase1_recommended') else 'No'}")
        wetlands = environmental_data.get("wetlands", {})
        print(f"   ✓ Wetlands Nearby: {wetlands.get('wetlands_nearby', 'Unknown')}")
        apis_used.append("EPA ECHO/Envirofacts")
    else:
        print("\n9. SKIPPING ENVIRONMENTAL DATA (quick mode)")

    # Step 10: Demographics (NEW)
    demographics_data = {}
    if not quick_mode and not skip_demographics:
        print("\n10. GETTING CENSUS DEMOGRAPHICS...")
        demographics_data = get_complete_demographics(lat, lon)
        if demographics_data.get("tract_data", {}).get("found"):
            tract = demographics_data["tract_data"]
            pop = tract.get("population", {}).get("total")
            income = tract.get("income", {}).get("median_household")
            value = tract.get("housing", {}).get("median_value")
            print(f"   ✓ Tract Population: {pop:,}" if pop else "   ✓ Population: N/A")
            print(f"   ✓ Median Income: ${income:,}" if income else "   ✓ Median Income: N/A")
            print(f"   ✓ Median Home Value: ${value:,}" if value else "   ✓ Median Home Value: N/A")
            indicators = demographics_data.get("market_indicators", {})
            print(f"   ✓ Market Strength: {indicators.get('market_strength', 'Unknown')}")
            apis_used.append("US Census ACS")
        else:
            print(f"   ✗ Demographics data unavailable")
    else:
        print("\n10. SKIPPING DEMOGRAPHICS (quick mode)")

    # Step 11: Site Context from OpenStreetMap (NEW)
    context_data = {}
    if not quick_mode and not skip_context:
        print("\n11. GETTING SITE CONTEXT (OpenStreetMap)...")
        context_data = get_site_context(lat, lon, radius_meters=500)
        summary = context_data.get("summary", {})
        print(f"   ✓ Buildings Nearby: {summary.get('building_count', 0)}")
        print(f"   ✓ Transit Access: {summary.get('transit_access', 'unknown').upper()}")
        print(f"   ✓ Walkability: {summary.get('walkability', 'Unknown')}")
        print(f"   ✓ Road Noise Risk: {summary.get('road_noise_risk', 'unknown').upper()}")
        print(f"   ✓ Amenities: {summary.get('amenity_count', 0)} locations")
        if summary.get("infrastructure_concerns"):
            for concern in summary["infrastructure_concerns"][:2]:
                print(f"   ⚠ {concern}")
        apis_used.append("Overpass/OpenStreetMap")
    else:
        print("\n11. SKIPPING SITE CONTEXT (quick mode)")

    # Build complete result
    complete_data = CompleteSiteData(
        address=geo["display_name"],
        latitude=lat,
        longitude=lon,
        elevation_ft=elevation,
        flood_zone=flood,
        weather=weather,
        soil=soil_data,
        sun_path=sun_data,
        parcel=parcel_data,
        storm_wind=storm_data,
        environmental=environmental_data,
        demographics=demographics_data,
        site_context=context_data,
        timestamp=datetime.now().isoformat(),
        apis_used=apis_used
    )

    return complete_data


def print_complete_report(data: CompleteSiteData):
    """Print a formatted complete report"""
    print(f"\n{'='*70}")
    print("COMPLETE SITE ANALYSIS REPORT")
    print(f"{'='*70}")

    print(f"\nADDRESS: {data.address}")
    print(f"\nCOORDINATES:")
    print(f"  Latitude:  {data.latitude:.6f}")
    print(f"  Longitude: {data.longitude:.6f}")

    print(f"\n{'─'*70}")
    print("SITE CONDITIONS")
    print(f"{'─'*70}")
    print(f"\nELEVATION: {data.elevation_ft} ft above sea level")

    print(f"\nFLOOD ZONE:")
    print(f"  Zone: {data.flood_zone.get('full_zone', 'Unknown')}")
    print(f"  {data.flood_zone.get('description', 'No description')}")

    if data.soil and data.soil.get("soil_name"):
        print(f"\nSOIL DATA:")
        print(f"  Type: {data.soil.get('soil_name', 'Unknown')}")
        print(f"  Drainage: {data.soil.get('drainage_class', 'Unknown')}")
        print(f"  {data.soil.get('drainage_description', '')}")
        print(f"  Hydrologic Group: {data.soil.get('hydrologic_group', 'Unknown')}")
        print(f"  {data.soil.get('hydrologic_description', '')}")
        if data.soil.get("engineering_notes"):
            print(f"\n  ENGINEERING NOTES:")
            for note in data.soil.get("engineering_notes", "").split("; "):
                print(f"    • {note}")

    # Storm/Wind Section (NEW)
    if data.storm_wind:
        print(f"\n{'─'*70}")
        print("STORM & WIND DESIGN")
        print(f"{'─'*70}")
        wind = data.storm_wind.get("wind_design", {})
        print(f"\n  Design Wind Speed: {wind.get('design_wind_speed_mph', 'N/A')} mph")
        print(f"  Exposure Category: {wind.get('exposure_category', 'N/A')}")
        print(f"  Risk Category: {wind.get('risk_category', 'N/A')}")
        print(f"  Reference Pressure: {wind.get('reference_pressure_psf', 'N/A')} psf")

        if wind.get("hvhz"):
            print(f"\n  ⚠️  HIGH-VELOCITY HURRICANE ZONE (HVHZ)")
            print(f"      {wind.get('hvhz_note', '')}")

        risk = data.storm_wind.get("storm_history", {}).get("hurricane_risk", {})
        print(f"\n  Hurricane Risk Level: {risk.get('level', 'Unknown')}")
        print(f"  Annual Probability: {risk.get('annual_probability', 'Unknown')}")
        if risk.get("factors"):
            print(f"\n  Risk Factors:")
            for factor in risk.get("factors", [])[:4]:
                print(f"    • {factor}")

    # Environmental Section (NEW)
    if data.environmental:
        print(f"\n{'─'*70}")
        print("ENVIRONMENTAL SCREENING")
        print(f"{'─'*70}")
        summary = data.environmental.get("summary", {})
        print(f"\n  Risk Level: {summary.get('risk_level', 'Unknown')}")
        print(f"  Phase I ESA Recommended: {'Yes' if summary.get('phase1_recommended') else 'Not required'}")
        print(f"\n  {summary.get('recommendation', '')}")

        if summary.get("concerns"):
            print(f"\n  Concerns:")
            for concern in summary.get("concerns", [])[:3]:
                print(f"    • {concern}")

        wetlands = data.environmental.get("wetlands", {})
        print(f"\n  Wetlands Nearby: {wetlands.get('wetlands_nearby', 'Unknown')}")
        if wetlands.get("regulatory_note"):
            print(f"    • {wetlands.get('regulatory_note')}")

    # Demographics Section (NEW)
    if data.demographics and data.demographics.get("tract_data", {}).get("found"):
        print(f"\n{'─'*70}")
        print("DEMOGRAPHICS & MARKET")
        print(f"{'─'*70}")
        tract = data.demographics["tract_data"]
        county = data.demographics.get("county_data", {})
        indicators = data.demographics.get("market_indicators", {})

        print(f"\n  Census Tract: {data.demographics.get('geography', {}).get('tract', 'N/A')}")

        pop = tract.get("population", {})
        print(f"\n  POPULATION:")
        print(f"    Tract: {pop.get('total', 'N/A'):,}" if pop.get('total') else "    Tract: N/A")
        print(f"    Median Age: {pop.get('median_age', 'N/A')}")

        housing = tract.get("housing", {})
        print(f"\n  HOUSING:")
        print(f"    Total Units: {housing.get('total_units', 'N/A'):,}" if housing.get('total_units') else "    Total Units: N/A")
        print(f"    Vacancy Rate: {housing.get('vacancy_rate_pct', 'N/A')}%")
        print(f"    Median Value: ${housing.get('median_value', 0):,}" if housing.get('median_value') else "    Median Value: N/A")
        print(f"    Median Rent: ${housing.get('median_rent', 0):,}/mo" if housing.get('median_rent') else "    Median Rent: N/A")

        income = tract.get("income", {})
        print(f"\n  INCOME:")
        print(f"    Median Household: ${income.get('median_household', 0):,}" if income.get('median_household') else "    Median Household: N/A")
        print(f"    Per Capita: ${income.get('per_capita', 0):,}" if income.get('per_capita') else "    Per Capita: N/A")

        print(f"\n  MARKET INDICATORS:")
        print(f"    Market Strength: {indicators.get('market_strength', 'Unknown')}")
        print(f"    Affordability: {indicators.get('affordability', 'Unknown')}")
        print(f"    Development Potential: {indicators.get('development_potential', 'Unknown')}")
        if indicators.get("price_to_income_ratio"):
            print(f"    Price-to-Income Ratio: {indicators['price_to_income_ratio']}")

        if indicators.get("factors"):
            print(f"\n  Analysis:")
            for factor in indicators.get("factors", [])[:4]:
                print(f"    • {factor}")

    # Site Context Section (NEW)
    if data.site_context and data.site_context.get("summary"):
        print(f"\n{'─'*70}")
        print("SITE CONTEXT (OpenStreetMap)")
        print(f"{'─'*70}")
        ctx = data.site_context
        summary = ctx.get("summary", {})

        print(f"\n  Search Radius: {ctx.get('radius_meters', 500)}m")

        print(f"\n  BUILDINGS:")
        print(f"    Nearby: {summary.get('building_count', 0)} structures")
        if summary.get("building_types"):
            for btype, count in sorted(summary["building_types"].items(), key=lambda x: -x[1])[:4]:
                print(f"      • {btype}: {count}")

        print(f"\n  TRANSIT:")
        print(f"    Access: {summary.get('transit_access', 'unknown').upper()}")
        print(f"    Stops: {summary.get('transit_stops', 0)}")
        for stop in ctx.get("transit", [])[:3]:
            name = stop.get("name") or stop.get("type", "Stop")
            print(f"      • {name} ({stop.get('type', 'transit')})")

        print(f"\n  ROADS:")
        print(f"    Noise Risk: {summary.get('road_noise_risk', 'unknown').upper()}")
        print(f"    Major Roads: {summary.get('major_roads_nearby', 0)}")

        print(f"\n  AMENITIES:")
        print(f"    Total: {summary.get('amenity_count', 0)} locations")
        for atype, items in sorted(ctx.get("amenities", {}).items(), key=lambda x: -len(x[1]))[:4]:
            print(f"      • {atype}: {len(items)}")

        print(f"\n  GREEN SPACE:")
        print(f"    Parks: {summary.get('parks_nearby', 0)}")

        print(f"\n  WALKABILITY: {summary.get('walkability', 'Unknown')}")
        for indicator in summary.get("walkability_indicators", [])[:4]:
            print(f"    • {indicator}")

        if summary.get("infrastructure_concerns"):
            print(f"\n  INFRASTRUCTURE CONCERNS:")
            for concern in summary["infrastructure_concerns"]:
                print(f"    ⚠ {concern}")

    print(f"\n{'─'*70}")
    print("SOLAR ANALYSIS")
    print(f"{'─'*70}")
    if data.sun_path:
        pos = data.sun_path.get("current_position", {})
        today = data.sun_path.get("today", {})
        orient = data.sun_path.get("orientation_recommendation", {})

        print(f"\nCURRENT SUN POSITION:")
        print(f"  Direction: {pos.get('direction', 'N/A')} ({pos.get('azimuth', 0)}°)")
        print(f"  Altitude: {pos.get('altitude', 0)}° above horizon")

        print(f"\nTODAY ({today.get('date', 'N/A')}):")
        print(f"  Sunrise: {today.get('sunrise', 'N/A')}")
        print(f"  Solar Noon: {today.get('solar_noon', 'N/A')}")
        print(f"  Sunset: {today.get('sunset', 'N/A')}")
        print(f"  Day Length: {today.get('day_length_hours', 0)} hours")

        summer = data.sun_path.get("summer_solstice", {})
        winter = data.sun_path.get("winter_solstice", {})
        print(f"\nSEASONAL VARIATION:")
        print(f"  Summer Solstice: {summer.get('day_length_hours', 0)} hrs daylight")
        print(f"  Winter Solstice: {winter.get('day_length_hours', 0)} hrs daylight")

        print(f"\nBUILDING ORIENTATION RECOMMENDATIONS:")
        print(f"  Optimal Long Axis: {orient.get('optimal_long_axis', 'E-W')}")
        print(f"  South Facade: {orient.get('south_facade', 'N/A')}")
        print(f"  West Facade: {orient.get('west_facade', 'N/A')}")
        print(f"  Solar Panel Angle: {orient.get('roof_solar_angle', 'N/A')}")

    print(f"\n{'─'*70}")
    print("WEATHER")
    print(f"{'─'*70}")
    if data.weather.get("current"):
        w = data.weather["current"]
        print(f"\nCURRENT CONDITIONS:")
        print(f"  Temperature: {w.get('temperature_f')}°F")
        print(f"  Humidity: {w.get('humidity_pct')}%")
        print(f"  Condition: {w.get('condition')}")
        print(f"  Wind: {w.get('wind_speed_mph')} mph")

    if data.weather.get("forecast"):
        print(f"\n7-DAY FORECAST:")
        print(f"  {'Date':<12} {'High':<8} {'Low':<8} {'Rain%':<8} {'Condition'}")
        print(f"  {'-'*55}")
        for day in data.weather["forecast"]:
            print(f"  {day['date']:<12} {day['high_f']:<8.1f} {day['low_f']:<8.1f} {day['precip_chance_pct']:<8} {day['condition']}")

    if data.parcel:
        print(f"\n{'─'*70}")
        print("PARCEL/PROPERTY DATA")
        print(f"{'─'*70}")
        p = data.parcel
        if p.get("found"):
            print(f"\n  County: {p.get('county', 'Unknown')}")
            print(f"  Parcel ID: {p.get('parcel_id', 'N/A')}")
            print(f"  Folio: {p.get('folio', 'N/A')}")
            print(f"\n  Owner: {p.get('owner_name', 'N/A')}")
            print(f"  Site Address: {p.get('site_address', 'N/A')}")
            print(f"\n  Land Use: {p.get('land_use_desc', p.get('land_use', 'N/A'))}")
            print(f"  Zoning: {p.get('zoning', 'N/A')}")
            if p.get("acreage"):
                print(f"  Acreage: {p.get('acreage')}")
            if p.get("just_value"):
                print(f"  Just Value: ${p.get('just_value'):,.0f}")
        else:
            # Show manual lookup info
            print(f"\n  Note: {p.get('note', 'Automated lookup unavailable')}")
            print(f"  Likely County: {p.get('likely_county', 'Unknown')}")
            print(f"  Manual Lookup: {p.get('manual_lookup', 'N/A')}")
            print(f"\n  Tip: {p.get('tip', 'Search by address on county property appraiser site')}")

    print(f"\n{'='*70}")
    print(f"APIs Used ({len(data.apis_used)}): {', '.join(data.apis_used)}")
    print(f"Report Generated: {data.timestamp}")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Get complete site data for architecture/construction projects (10 APIs)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python site_data_full.py "100 Biscayne Blvd, Miami, FL 33132"
  python site_data_full.py "123 Main St, Miami, FL" --quick
  python site_data_full.py "456 Ocean Dr, Miami Beach, FL" --json > site.json
        """
    )

    parser.add_argument("address", help="Street address to look up")
    parser.add_argument("--quick", "-q", action="store_true",
                       help="Quick mode - skip slower APIs (soil, parcel, storm, environmental, demographics)")
    parser.add_argument("--json", "-j", action="store_true",
                       help="Output JSON only (no formatted report)")
    parser.add_argument("--skip-parcel", action="store_true",
                       help="Skip parcel lookup")
    parser.add_argument("--skip-soil", action="store_true",
                       help="Skip soil data lookup")
    parser.add_argument("--skip-storm", action="store_true",
                       help="Skip storm/wind data lookup")
    parser.add_argument("--skip-environmental", action="store_true",
                       help="Skip EPA environmental screening")
    parser.add_argument("--skip-demographics", action="store_true",
                       help="Skip Census demographics")
    parser.add_argument("--skip-context", action="store_true",
                       help="Skip OpenStreetMap site context")
    parser.add_argument("--output", "-o", type=str,
                       help="Save JSON to specified file")

    args = parser.parse_args()

    # Get data
    data = get_complete_site_data(
        args.address,
        quick_mode=args.quick,
        skip_parcel=args.skip_parcel,
        skip_soil=args.skip_soil,
        skip_storm=args.skip_storm,
        skip_environmental=args.skip_environmental,
        skip_demographics=args.skip_demographics,
        skip_context=args.skip_context
    )

    if not data:
        print("Failed to retrieve site data.")
        sys.exit(1)

    # Output
    if args.json:
        print(data.to_json())
    else:
        print_complete_report(data)

    # Save JSON if requested
    output_file = args.output or "site_data_complete.json"
    with open(output_file, "w") as f:
        f.write(data.to_json())

    if not args.json:
        print(f"JSON saved to: {output_file}")


if __name__ == "__main__":
    main()

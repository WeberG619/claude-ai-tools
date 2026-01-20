#!/usr/bin/env python3
"""
US Census Bureau API Integration
Free, API key optional (higher rate limits with key)

APIs Used:
- Census Geocoder (for tract/block lookup)
- American Community Survey (ACS) 5-Year Estimates
- Decennial Census data

Useful for market analysis, feasibility studies, housing demand assessment
"""

import requests
from typing import Dict, Any, List, Optional
from datetime import datetime


# Census API base URLs
CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
CENSUS_DATA_URL = "https://api.census.gov/data"

# ACS variable codes for key demographics
ACS_VARIABLES = {
    # Population
    "B01003_001E": "total_population",
    "B01002_001E": "median_age",

    # Housing
    "B25001_001E": "total_housing_units",
    "B25002_002E": "occupied_units",
    "B25002_003E": "vacant_units",
    "B25077_001E": "median_home_value",
    "B25064_001E": "median_gross_rent",
    "B25035_001E": "median_year_built",

    # Income
    "B19013_001E": "median_household_income",
    "B19301_001E": "per_capita_income",

    # Employment
    "B23025_002E": "labor_force",
    "B23025_005E": "unemployed",

    # Education (25+ years)
    "B15003_022E": "bachelors_degree",
    "B15003_023E": "masters_degree",
    "B15003_025E": "doctorate_degree",

    # Commute
    "B08301_001E": "total_commuters",
    "B08303_001E": "travel_time_total",
}


def get_census_geography(lat: float, lon: float) -> Dict[str, Any]:
    """
    Get Census geography (tract, block group, county) for coordinates

    Uses Census Geocoder - free, no API key required
    """
    result = {
        "state_fips": None,
        "county_fips": None,
        "tract": None,
        "block_group": None,
        "block": None,
        "county_name": None,
        "state_name": None,
        "found": False
    }

    params = {
        "x": lon,
        "y": lat,
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "layers": "all",
        "format": "json"
    }

    try:
        response = requests.get(CENSUS_GEOCODER_URL, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()

            if data.get("result", {}).get("geographies"):
                geographies = data["result"]["geographies"]

                # Census Tracts
                if "Census Tracts" in geographies and geographies["Census Tracts"]:
                    tract_info = geographies["Census Tracts"][0]
                    result["state_fips"] = tract_info.get("STATE")
                    result["county_fips"] = tract_info.get("COUNTY")
                    result["tract"] = tract_info.get("TRACT")
                    result["geoid"] = tract_info.get("GEOID")
                    result["found"] = True

                # Counties
                if "Counties" in geographies and geographies["Counties"]:
                    county_info = geographies["Counties"][0]
                    result["county_name"] = county_info.get("NAME")

                # States
                if "States" in geographies and geographies["States"]:
                    state_info = geographies["States"][0]
                    result["state_name"] = state_info.get("NAME")

                # Block Groups
                if "Census Block Groups" in geographies and geographies["Census Block Groups"]:
                    bg_info = geographies["Census Block Groups"][0]
                    result["block_group"] = bg_info.get("BLKGRP")

                # Census Blocks
                if "2020 Census Blocks" in geographies and geographies["2020 Census Blocks"]:
                    block_info = geographies["2020 Census Blocks"][0]
                    result["block"] = block_info.get("BLOCK")

    except Exception as e:
        print(f"Census Geocoder error: {e}")

    return result


def get_acs_demographics(state_fips: str, county_fips: str, tract: str = None) -> Dict[str, Any]:
    """
    Get American Community Survey demographics for a geography

    Args:
        state_fips: State FIPS code (e.g., "12" for Florida)
        county_fips: County FIPS code (e.g., "086" for Miami-Dade)
        tract: Optional census tract for more specific data

    Returns:
        Dictionary of demographic data
    """
    result = {
        "population": {},
        "housing": {},
        "income": {},
        "employment": {},
        "education": {},
        "found": False,
        "geography_level": "county" if not tract else "tract"
    }

    # Build variable list
    variables = ",".join(ACS_VARIABLES.keys())

    # ACS 5-Year Estimates (most recent)
    year = 2022  # Most recent available

    # Build URL based on geography level
    if tract:
        url = f"{CENSUS_DATA_URL}/{year}/acs/acs5"
        params = {
            "get": f"NAME,{variables}",
            "for": f"tract:{tract}",
            "in": f"state:{state_fips}+county:{county_fips}"
        }
    else:
        url = f"{CENSUS_DATA_URL}/{year}/acs/acs5"
        params = {
            "get": f"NAME,{variables}",
            "for": f"county:{county_fips}",
            "in": f"state:{state_fips}"
        }

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()

            if len(data) >= 2:
                headers = data[0]
                values = data[1]

                # Create mapping
                raw_data = dict(zip(headers, values))
                result["raw"] = raw_data
                result["geography_name"] = raw_data.get("NAME", "Unknown")

                # Parse into categories
                result["population"] = {
                    "total": _safe_int(raw_data.get("B01003_001E")),
                    "median_age": _safe_float(raw_data.get("B01002_001E")),
                }

                result["housing"] = {
                    "total_units": _safe_int(raw_data.get("B25001_001E")),
                    "occupied": _safe_int(raw_data.get("B25002_002E")),
                    "vacant": _safe_int(raw_data.get("B25002_003E")),
                    "median_value": _safe_int(raw_data.get("B25077_001E")),
                    "median_rent": _safe_int(raw_data.get("B25064_001E")),
                    "median_year_built": _safe_int(raw_data.get("B25035_001E")),
                }

                # Calculate vacancy rate
                if result["housing"]["total_units"]:
                    result["housing"]["vacancy_rate_pct"] = round(
                        (result["housing"]["vacant"] or 0) / result["housing"]["total_units"] * 100, 1
                    )

                result["income"] = {
                    "median_household": _safe_int(raw_data.get("B19013_001E")),
                    "per_capita": _safe_int(raw_data.get("B19301_001E")),
                }

                labor_force = _safe_int(raw_data.get("B23025_002E"))
                unemployed = _safe_int(raw_data.get("B23025_005E"))
                result["employment"] = {
                    "labor_force": labor_force,
                    "unemployed": unemployed,
                    "unemployment_rate_pct": round(unemployed / labor_force * 100, 1) if labor_force else None,
                }

                bachelors = _safe_int(raw_data.get("B15003_022E")) or 0
                masters = _safe_int(raw_data.get("B15003_023E")) or 0
                doctorate = _safe_int(raw_data.get("B15003_025E")) or 0
                result["education"] = {
                    "bachelors_degree": bachelors,
                    "masters_degree": masters,
                    "doctorate_degree": doctorate,
                    "college_educated": bachelors + masters + doctorate,
                }

                result["found"] = True
                result["year"] = year
                result["source"] = f"ACS 5-Year Estimates {year}"

    except Exception as e:
        print(f"ACS API error: {e}")

    return result


def get_housing_market_indicators(demographics: Dict) -> Dict[str, Any]:
    """
    Calculate housing market indicators from demographics
    """
    indicators = {
        "market_strength": "Unknown",
        "affordability": "Unknown",
        "development_potential": "Unknown",
        "factors": []
    }

    housing = demographics.get("housing", {})
    income = demographics.get("income", {})

    # Vacancy rate analysis
    vacancy = housing.get("vacancy_rate_pct", 0)
    if vacancy:
        if vacancy < 5:
            indicators["factors"].append("Low vacancy - tight market, strong demand")
            indicators["market_strength"] = "Strong"
        elif vacancy < 10:
            indicators["factors"].append("Moderate vacancy - balanced market")
            indicators["market_strength"] = "Moderate"
        else:
            indicators["factors"].append("High vacancy - potential oversupply")
            indicators["market_strength"] = "Weak"

    # Affordability analysis (median home value vs income)
    median_value = housing.get("median_value", 0)
    median_income = income.get("median_household", 0)

    if median_value and median_income:
        price_to_income = median_value / median_income
        indicators["price_to_income_ratio"] = round(price_to_income, 1)

        if price_to_income < 3:
            indicators["affordability"] = "Affordable"
            indicators["factors"].append(f"Price-to-income ratio {price_to_income:.1f} - affordable market")
        elif price_to_income < 5:
            indicators["affordability"] = "Moderate"
            indicators["factors"].append(f"Price-to-income ratio {price_to_income:.1f} - moderate affordability")
        else:
            indicators["affordability"] = "Expensive"
            indicators["factors"].append(f"Price-to-income ratio {price_to_income:.1f} - expensive market")

    # Age of housing stock
    median_year = housing.get("median_year_built", 0)
    if median_year:
        age = 2024 - median_year
        if age > 40:
            indicators["factors"].append(f"Aging housing stock (median built {median_year}) - renovation/redevelopment opportunity")
            indicators["development_potential"] = "High"
        elif age > 25:
            indicators["factors"].append(f"Mature housing stock (median built {median_year})")
            indicators["development_potential"] = "Moderate"
        else:
            indicators["factors"].append(f"Newer housing stock (median built {median_year})")
            indicators["development_potential"] = "Lower"

    # Income analysis
    if median_income:
        if median_income > 80000:
            indicators["factors"].append("High-income area - luxury market potential")
        elif median_income > 50000:
            indicators["factors"].append("Middle-income area - broad market appeal")
        else:
            indicators["factors"].append("Lower-income area - workforce housing opportunity")

    return indicators


def get_complete_demographics(lat: float, lon: float) -> Dict[str, Any]:
    """
    Get complete demographic profile for a location
    """
    # First, get census geography
    geography = get_census_geography(lat, lon)

    if not geography["found"]:
        return {
            "error": "Could not determine census geography for coordinates",
            "coordinates": {"latitude": lat, "longitude": lon}
        }

    # Get ACS data for the tract
    demographics = get_acs_demographics(
        geography["state_fips"],
        geography["county_fips"],
        geography["tract"]
    )

    # Get county-level data for comparison
    county_demographics = get_acs_demographics(
        geography["state_fips"],
        geography["county_fips"]
    )

    # Calculate market indicators
    indicators = get_housing_market_indicators(demographics)

    return {
        "geography": geography,
        "tract_data": demographics,
        "county_data": county_demographics,
        "market_indicators": indicators,
        "coordinates": {"latitude": lat, "longitude": lon},
        "timestamp": datetime.now().isoformat(),
        "source": "US Census Bureau ACS 5-Year Estimates"
    }


def _safe_int(value) -> Optional[int]:
    """Safely convert to int"""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_float(value) -> Optional[float]:
    """Safely convert to float"""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def format_demographics_report(data: Dict[str, Any]) -> str:
    """Format demographic data as readable report"""
    if data.get("error"):
        return f"Error: {data['error']}"

    geo = data["geography"]
    tract = data["tract_data"]
    county = data.get("county_data", {})
    indicators = data["market_indicators"]

    lines = [
        "=" * 60,
        "DEMOGRAPHIC PROFILE",
        "=" * 60,
        "",
        f"Location: {tract.get('geography_name', 'Unknown')}",
        f"County: {geo.get('county_name', 'Unknown')}, {geo.get('state_name', 'Unknown')}",
        f"Census Tract: {geo.get('tract', 'Unknown')}",
        "",
        "POPULATION:",
        f"  Total (Tract): {tract['population'].get('total', 'N/A'):,}" if tract['population'].get('total') else "  Total: N/A",
        f"  Total (County): {county.get('population', {}).get('total', 'N/A'):,}" if county.get('population', {}).get('total') else "",
        f"  Median Age: {tract['population'].get('median_age', 'N/A')}",
        "",
        "HOUSING:",
        f"  Total Units: {tract['housing'].get('total_units', 'N/A'):,}" if tract['housing'].get('total_units') else "  Total Units: N/A",
        f"  Vacancy Rate: {tract['housing'].get('vacancy_rate_pct', 'N/A')}%",
        f"  Median Value: ${tract['housing'].get('median_value', 0):,}" if tract['housing'].get('median_value') else "  Median Value: N/A",
        f"  Median Rent: ${tract['housing'].get('median_rent', 0):,}/mo" if tract['housing'].get('median_rent') else "  Median Rent: N/A",
        f"  Median Year Built: {tract['housing'].get('median_year_built', 'N/A')}",
        "",
        "INCOME:",
        f"  Median Household: ${tract['income'].get('median_household', 0):,}" if tract['income'].get('median_household') else "  Median Household: N/A",
        f"  Per Capita: ${tract['income'].get('per_capita', 0):,}" if tract['income'].get('per_capita') else "  Per Capita: N/A",
        "",
        "EMPLOYMENT:",
        f"  Unemployment Rate: {tract['employment'].get('unemployment_rate_pct', 'N/A')}%",
        "",
        "MARKET INDICATORS:",
        f"  Market Strength: {indicators.get('market_strength', 'Unknown')}",
        f"  Affordability: {indicators.get('affordability', 'Unknown')}",
        f"  Development Potential: {indicators.get('development_potential', 'Unknown')}",
    ]

    if indicators.get("price_to_income_ratio"):
        lines.append(f"  Price-to-Income Ratio: {indicators['price_to_income_ratio']}")

    lines.append("")
    lines.append("ANALYSIS:")
    for factor in indicators.get("factors", []):
        lines.append(f"  • {factor}")

    lines.extend([
        "",
        "=" * 60,
        f"Source: {data['source']}",
        f"Data Year: {tract.get('year', 'N/A')}",
        "=" * 60,
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    # Test with Goulds, FL location
    lat, lon = 25.5659, -80.3827
    print(f"\nGetting demographics for ({lat}, {lon})...\n")

    data = get_complete_demographics(lat, lon)
    print(format_demographics_report(data))

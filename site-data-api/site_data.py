#!/usr/bin/env python3
"""
Site Data API - Free APIs for Architecture/Construction Projects
Integrates: Nominatim (geocoding), Open-Elevation, FEMA Flood, Open-Meteo

All APIs are 100% free with no API keys required.

Usage:
    from site_data import get_site_data
    data = get_site_data("123 Main St, Miami, FL 33130")

CLI:
    python site_data.py "123 Main St, Miami, FL 33130"
"""

import requests
import json
import sys
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# User agent required by Nominatim
USER_AGENT = "BDArchitect-SiteData/1.0 (Architecture Project Tool)"

@dataclass
class SiteData:
    """Complete site data from all APIs"""
    address: str
    latitude: float
    longitude: float
    elevation_ft: float
    flood_zone: str
    flood_zone_description: str
    weather_current: Dict[str, Any]
    weather_forecast: list
    timestamp: str

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def geocode_address(address: str) -> Optional[Dict[str, float]]:
    """
    Convert address to coordinates using Nominatim (OpenStreetMap)
    Free, no API key, 1 request/second limit
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "addressdetails": 1
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data:
            result = data[0]
            return {
                "latitude": float(result["lat"]),
                "longitude": float(result["lon"]),
                "display_name": result.get("display_name", address),
                "address_details": result.get("address", {})
            }
        return None
    except Exception as e:
        print(f"Geocoding error: {e}")
        return None


def get_elevation(lat: float, lon: float) -> Optional[float]:
    """
    Get elevation in feet using Open-Elevation API
    Free, no API key, no strict limits
    """
    url = "https://api.open-elevation.com/api/v1/lookup"
    params = {"locations": f"{lat},{lon}"}

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("results"):
            elevation_meters = data["results"][0]["elevation"]
            elevation_feet = elevation_meters * 3.28084
            return round(elevation_feet, 1)
        return None
    except Exception as e:
        print(f"Elevation API error: {e}")
        return None


def get_flood_zone(lat: float, lon: float) -> Dict[str, str]:
    """
    Get FEMA flood zone using FEMA's Map Service
    Free, no API key
    """
    # FEMA National Flood Hazard Layer (NFHL) REST service - ArcGIS endpoint
    url = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"

    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "FLD_ZONE,ZONE_SUBTY,SFHA_TF",
        "returnGeometry": "false",
        "f": "json"
    }

    flood_zone_descriptions = {
        "A": "High Risk - 1% annual flood chance (100-year flood)",
        "AE": "High Risk - 1% annual flood chance with BFE determined",
        "AH": "High Risk - 1% annual chance of shallow flooding (1-3ft)",
        "AO": "High Risk - 1% annual chance of sheet flow flooding",
        "V": "High Risk - Coastal flood with velocity (wave action)",
        "VE": "High Risk - Coastal flood with velocity, BFE determined",
        "X": "Moderate to Low Risk - Outside 100-year floodplain",
        "D": "Undetermined Risk - No analysis performed",
        "B": "Moderate Risk - 500-year flood area (0.2% annual)",
        "C": "Low Risk - Outside 500-year floodplain"
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("features"):
            feature = data["features"][0]
            attrs = feature.get("attributes", {})
            zone = attrs.get("FLD_ZONE", "Unknown")
            subtype = attrs.get("ZONE_SUBTY", "")

            # Check if in Special Flood Hazard Area
            sfha = attrs.get("SFHA_TF", "")

            full_zone = f"{zone}{' - ' + subtype if subtype else ''}"
            description = flood_zone_descriptions.get(zone, "Unknown flood zone classification")

            if sfha == "T":
                description += " [IN SPECIAL FLOOD HAZARD AREA - Flood insurance required]"

            return {
                "zone": zone,
                "full_zone": full_zone,
                "description": description,
                "sfha": sfha == "T"
            }

        return {
            "zone": "Not Mapped",
            "full_zone": "Not Mapped",
            "description": "Location not covered by FEMA flood mapping",
            "sfha": False
        }
    except Exception as e:
        print(f"FEMA API error: {e}")
        return {
            "zone": "Error",
            "full_zone": "Error",
            "description": f"Could not retrieve flood data: {e}",
            "sfha": None
        }


def get_weather(lat: float, lon: float) -> Dict[str, Any]:
    """
    Get current weather and 7-day forecast using Open-Meteo
    Free, no API key, unlimited requests
    """
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "America/New_York",
        "forecast_days": 7
    }

    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        current = data.get("current", {})
        daily = data.get("daily", {})

        weather_code = current.get("weather_code", 0)

        current_weather = {
            "temperature_f": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "precipitation_in": current.get("precipitation"),
            "condition": weather_codes.get(weather_code, "Unknown"),
            "wind_speed_mph": current.get("wind_speed_10m"),
            "wind_direction": current.get("wind_direction_10m")
        }

        forecast = []
        if daily.get("time"):
            for i, date in enumerate(daily["time"]):
                day_code = daily["weather_code"][i] if daily.get("weather_code") else 0
                forecast.append({
                    "date": date,
                    "high_f": daily["temperature_2m_max"][i] if daily.get("temperature_2m_max") else None,
                    "low_f": daily["temperature_2m_min"][i] if daily.get("temperature_2m_min") else None,
                    "precipitation_in": daily["precipitation_sum"][i] if daily.get("precipitation_sum") else 0,
                    "precip_chance_pct": daily["precipitation_probability_max"][i] if daily.get("precipitation_probability_max") else 0,
                    "condition": weather_codes.get(day_code, "Unknown"),
                    "wind_max_mph": daily["wind_speed_10m_max"][i] if daily.get("wind_speed_10m_max") else None
                })

        return {
            "current": current_weather,
            "forecast": forecast
        }
    except Exception as e:
        print(f"Weather API error: {e}")
        return {"current": {}, "forecast": []}


def get_site_data(address: str) -> Optional[SiteData]:
    """
    Main function - Get all site data for an address
    Returns SiteData object with coordinates, elevation, flood zone, and weather
    """
    print(f"\n{'='*60}")
    print(f"SITE DATA REPORT")
    print(f"Address: {address}")
    print(f"{'='*60}\n")

    # Step 1: Geocode
    print("1. Geocoding address...")
    geo = geocode_address(address)
    if not geo:
        print("   ERROR: Could not geocode address")
        return None

    lat, lon = geo["latitude"], geo["longitude"]
    print(f"   Coordinates: {lat:.6f}, {lon:.6f}")
    print(f"   Resolved: {geo['display_name']}")

    # Respect Nominatim rate limit
    time.sleep(1)

    # Step 2: Elevation
    print("\n2. Getting elevation...")
    elevation = get_elevation(lat, lon)
    if elevation is not None:
        print(f"   Elevation: {elevation} ft")
    else:
        print("   Elevation: Could not retrieve")
        elevation = 0.0

    # Step 3: Flood Zone
    print("\n3. Checking FEMA flood zone...")
    flood = get_flood_zone(lat, lon)
    print(f"   Zone: {flood['full_zone']}")
    print(f"   Risk: {flood['description']}")

    # Step 4: Weather
    print("\n4. Getting weather data...")
    weather = get_weather(lat, lon)
    if weather.get("current"):
        curr = weather["current"]
        print(f"   Current: {curr.get('temperature_f')}°F, {curr.get('condition')}")
        print(f"   Wind: {curr.get('wind_speed_mph')} mph")

    # Build result
    site_data = SiteData(
        address=geo["display_name"],
        latitude=lat,
        longitude=lon,
        elevation_ft=elevation,
        flood_zone=flood["full_zone"],
        flood_zone_description=flood["description"],
        weather_current=weather.get("current", {}),
        weather_forecast=weather.get("forecast", []),
        timestamp=datetime.now().isoformat()
    )

    return site_data


def print_full_report(data: SiteData):
    """Print a formatted full report"""
    print(f"\n{'='*60}")
    print("COMPLETE SITE DATA REPORT")
    print(f"{'='*60}")
    print(f"\nADDRESS: {data.address}")
    print(f"\nCOORDINATES:")
    print(f"  Latitude:  {data.latitude:.6f}")
    print(f"  Longitude: {data.longitude:.6f}")
    print(f"\nELEVATION: {data.elevation_ft} ft")
    print(f"\nFLOOD ZONE:")
    print(f"  Zone: {data.flood_zone}")
    print(f"  {data.flood_zone_description}")

    if data.weather_current:
        print(f"\nCURRENT WEATHER:")
        w = data.weather_current
        print(f"  Temperature: {w.get('temperature_f')}°F")
        print(f"  Humidity: {w.get('humidity_pct')}%")
        print(f"  Condition: {w.get('condition')}")
        print(f"  Wind: {w.get('wind_speed_mph')} mph")

    if data.weather_forecast:
        print(f"\n7-DAY FORECAST:")
        print(f"  {'Date':<12} {'High':<8} {'Low':<8} {'Rain':<8} {'Condition'}")
        print(f"  {'-'*50}")
        for day in data.weather_forecast:
            print(f"  {day['date']:<12} {day['high_f']:<8} {day['low_f']:<8} {day['precip_chance_pct']}%{'':<5} {day['condition']}")

    print(f"\n{'='*60}")
    print(f"Report generated: {data.timestamp}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python site_data.py \"ADDRESS\"")
        print("Example: python site_data.py \"123 Main St, Miami, FL 33130\"")
        sys.exit(1)

    address = " ".join(sys.argv[1:])
    data = get_site_data(address)

    if data:
        print_full_report(data)

        # Save JSON output
        output_file = "site_data_result.json"
        with open(output_file, "w") as f:
            f.write(data.to_json())
        print(f"JSON saved to: {output_file}")

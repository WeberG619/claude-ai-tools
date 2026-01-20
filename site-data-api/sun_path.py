#!/usr/bin/env python3
"""
Sun Path Calculator
Pure astronomical calculations - NO API needed, works offline

Calculates sun position, sunrise/sunset, and optimal building orientation
"""

import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

@dataclass
class SunPosition:
    """Sun position at a specific time"""
    azimuth: float      # Compass direction (0=N, 90=E, 180=S, 270=W)
    altitude: float     # Angle above horizon (0-90)
    zenith: float       # Angle from vertical (90 - altitude)

    @property
    def compass_direction(self) -> str:
        """Convert azimuth to compass direction"""
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                      "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = round(self.azimuth / 22.5) % 16
        return directions[index]


def calculate_sun_position(lat: float, lon: float, dt: datetime = None) -> SunPosition:
    """
    Calculate sun position using astronomical formulas
    Based on NOAA Solar Calculator algorithms

    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
        dt: Datetime (defaults to now, local time assumed)

    Returns:
        SunPosition with azimuth, altitude, zenith
    """
    if dt is None:
        dt = datetime.now()

    # Convert to radians
    lat_rad = math.radians(lat)

    # Day of year
    day_of_year = dt.timetuple().tm_yday

    # Fractional year (gamma) in radians
    gamma = 2 * math.pi / 365 * (day_of_year - 1 + (dt.hour - 12) / 24)

    # Equation of time (minutes)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma)
                       - 0.032077 * math.sin(gamma)
                       - 0.014615 * math.cos(2 * gamma)
                       - 0.040849 * math.sin(2 * gamma))

    # Solar declination (radians)
    decl = (0.006918 - 0.399912 * math.cos(gamma)
            + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma)
            + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma)
            + 0.00148 * math.sin(3 * gamma))

    # Time offset (minutes) - assume standard time zone based on longitude
    timezone_offset = round(lon / 15) * 60  # Simple timezone estimate
    time_offset = eqtime + 4 * lon - timezone_offset

    # True solar time (minutes)
    tst = dt.hour * 60 + dt.minute + dt.second / 60 + time_offset

    # Hour angle (degrees)
    ha = (tst / 4) - 180
    ha_rad = math.radians(ha)

    # Solar zenith angle
    cos_zenith = (math.sin(lat_rad) * math.sin(decl) +
                  math.cos(lat_rad) * math.cos(decl) * math.cos(ha_rad))

    # Clamp to valid range
    cos_zenith = max(-1, min(1, cos_zenith))
    zenith = math.degrees(math.acos(cos_zenith))
    altitude = 90 - zenith

    # Solar azimuth angle
    if cos_zenith == 1:
        azimuth = 180  # Sun directly overhead
    else:
        cos_azimuth = ((math.sin(lat_rad) * cos_zenith - math.sin(decl)) /
                       (math.cos(lat_rad) * math.sin(math.radians(zenith))))
        cos_azimuth = max(-1, min(1, cos_azimuth))
        azimuth = math.degrees(math.acos(cos_azimuth))

        if ha > 0:
            azimuth = 360 - azimuth

    return SunPosition(
        azimuth=round(azimuth, 1),
        altitude=round(altitude, 1),
        zenith=round(zenith, 1)
    )


def calculate_sunrise_sunset(lat: float, lon: float, date: datetime = None) -> Dict[str, Any]:
    """
    Calculate sunrise, sunset, and solar noon for a location

    Args:
        lat: Latitude
        lon: Longitude
        date: Date to calculate (defaults to today)

    Returns:
        Dict with sunrise, sunset, solar_noon, day_length
    """
    if date is None:
        date = datetime.now()

    lat_rad = math.radians(lat)
    day_of_year = date.timetuple().tm_yday

    # Fractional year
    gamma = 2 * math.pi / 365 * (day_of_year - 1)

    # Equation of time
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gamma)
                       - 0.032077 * math.sin(gamma)
                       - 0.014615 * math.cos(2 * gamma)
                       - 0.040849 * math.sin(2 * gamma))

    # Solar declination
    decl = (0.006918 - 0.399912 * math.cos(gamma)
            + 0.070257 * math.sin(gamma)
            - 0.006758 * math.cos(2 * gamma)
            + 0.000907 * math.sin(2 * gamma)
            - 0.002697 * math.cos(3 * gamma)
            + 0.00148 * math.sin(3 * gamma))

    # Hour angle for sunrise/sunset (degrees)
    # Using standard refraction correction of 0.833 degrees
    cos_ha = (math.cos(math.radians(90.833)) /
              (math.cos(lat_rad) * math.cos(decl)) -
              math.tan(lat_rad) * math.tan(decl))

    # Check for polar day/night
    if cos_ha > 1:
        return {
            "sunrise": None,
            "sunset": None,
            "solar_noon": "12:00",
            "day_length_hours": 0,
            "note": "Polar night - sun does not rise"
        }
    elif cos_ha < -1:
        return {
            "sunrise": None,
            "sunset": None,
            "solar_noon": "12:00",
            "day_length_hours": 24,
            "note": "Polar day - sun does not set"
        }

    ha_sunrise = math.degrees(math.acos(cos_ha))

    # Time zone offset (simple estimate)
    tz_offset = round(lon / 15)

    # Solar noon in minutes from midnight (local standard time)
    solar_noon_minutes = 720 - 4 * lon - eqtime + tz_offset * 60

    # Sunrise and sunset in minutes
    sunrise_minutes = solar_noon_minutes - ha_sunrise * 4
    sunset_minutes = solar_noon_minutes + ha_sunrise * 4

    def minutes_to_time(minutes: float) -> str:
        """Convert minutes from midnight to HH:MM format"""
        minutes = minutes % 1440  # Handle day overflow
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        return f"{hours:02d}:{mins:02d}"

    day_length = (sunset_minutes - sunrise_minutes) / 60

    return {
        "sunrise": minutes_to_time(sunrise_minutes),
        "sunset": minutes_to_time(sunset_minutes),
        "solar_noon": minutes_to_time(solar_noon_minutes),
        "day_length_hours": round(day_length, 2),
        "date": date.strftime("%Y-%m-%d")
    }


def get_sun_path_data(lat: float, lon: float, date: datetime = None) -> Dict[str, Any]:
    """
    Get complete sun path data for architecture/construction use

    Returns current position, sunrise/sunset, and key times throughout the day
    """
    if date is None:
        date = datetime.now()

    # Current sun position
    current = calculate_sun_position(lat, lon, date)

    # Sunrise/sunset times
    sun_times = calculate_sunrise_sunset(lat, lon, date)

    # Calculate sun positions throughout the day (hourly)
    hourly_positions = []
    for hour in range(6, 21):  # 6 AM to 8 PM
        dt = date.replace(hour=hour, minute=0, second=0)
        pos = calculate_sun_position(lat, lon, dt)
        if pos.altitude > 0:  # Only when sun is above horizon
            hourly_positions.append({
                "time": f"{hour:02d}:00",
                "azimuth": pos.azimuth,
                "altitude": pos.altitude,
                "direction": pos.compass_direction
            })

    # Key times for construction/architecture
    # Summer solstice (June 21)
    summer = calculate_sunrise_sunset(lat, lon, datetime(date.year, 6, 21))
    # Winter solstice (December 21)
    winter = calculate_sunrise_sunset(lat, lon, datetime(date.year, 12, 21))

    # Optimal building orientation recommendation
    orientation = get_orientation_recommendation(lat)

    return {
        "current_position": {
            "azimuth": current.azimuth,
            "altitude": current.altitude,
            "direction": current.compass_direction,
            "timestamp": date.isoformat()
        },
        "today": sun_times,
        "hourly_positions": hourly_positions,
        "summer_solstice": summer,
        "winter_solstice": winter,
        "orientation_recommendation": orientation,
        "latitude": lat,
        "longitude": lon
    }


def get_orientation_recommendation(lat: float) -> Dict[str, str]:
    """
    Get building orientation recommendations based on latitude
    """
    if lat >= 0:  # Northern hemisphere
        return {
            "optimal_long_axis": "East-West",
            "reason": "Minimizes east/west sun exposure, maximizes south-facing windows for passive solar",
            "south_facade": "Ideal for windows - winter sun gain, summer overhang shading",
            "north_facade": "Minimal direct sun - good for even daylight, minimal heat gain",
            "east_facade": "Morning sun - good for bedrooms, kitchens",
            "west_facade": "Afternoon sun - needs shading, avoid large glass areas",
            "roof_solar_optimal": "South-facing at angle equal to latitude",
            "roof_solar_angle": f"{abs(lat):.0f}° from horizontal, facing south"
        }
    else:  # Southern hemisphere
        return {
            "optimal_long_axis": "East-West",
            "reason": "Minimizes east/west sun exposure, maximizes north-facing windows",
            "north_facade": "Ideal for windows - winter sun gain",
            "south_facade": "Minimal direct sun - good for even daylight",
            "east_facade": "Morning sun - good for bedrooms",
            "west_facade": "Afternoon sun - needs shading",
            "roof_solar_optimal": "North-facing at angle equal to latitude",
            "roof_solar_angle": f"{abs(lat):.0f}° from horizontal, facing north"
        }


def get_shadow_length(object_height: float, sun_altitude: float) -> float:
    """
    Calculate shadow length for an object

    Args:
        object_height: Height of object in any unit
        sun_altitude: Sun altitude angle in degrees

    Returns:
        Shadow length in same units as height
    """
    if sun_altitude <= 0:
        return float('inf')  # Sun below horizon

    return object_height / math.tan(math.radians(sun_altitude))


if __name__ == "__main__":
    # Test with Miami coordinates
    lat, lon = 25.7617, -80.1918
    print(f"\nSun Path Data for Miami ({lat}, {lon})")
    print("=" * 50)

    data = get_sun_path_data(lat, lon)

    print(f"\nCurrent Position:")
    pos = data["current_position"]
    print(f"  Azimuth: {pos['azimuth']}° ({pos['direction']})")
    print(f"  Altitude: {pos['altitude']}°")

    print(f"\nToday ({data['today']['date']}):")
    print(f"  Sunrise: {data['today']['sunrise']}")
    print(f"  Solar Noon: {data['today']['solar_noon']}")
    print(f"  Sunset: {data['today']['sunset']}")
    print(f"  Day Length: {data['today']['day_length_hours']} hours")

    print(f"\nSeasonal Comparison:")
    print(f"  Summer Solstice: {data['summer_solstice']['day_length_hours']} hrs daylight")
    print(f"  Winter Solstice: {data['winter_solstice']['day_length_hours']} hrs daylight")

    print(f"\nBuilding Orientation Recommendations:")
    for key, value in data["orientation_recommendation"].items():
        print(f"  {key}: {value}")

    print(f"\nHourly Sun Positions:")
    for pos in data["hourly_positions"]:
        print(f"  {pos['time']}: {pos['direction']} ({pos['azimuth']}°), {pos['altitude']}° alt")

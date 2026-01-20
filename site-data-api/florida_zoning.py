#!/usr/bin/env python3
"""
Florida Zoning Database
Comprehensive zoning rules for Miami-Dade, Broward, and Palm Beach counties

This database provides:
- Zoning district definitions
- Allowed uses by district
- Development standards (height, setbacks, FAR, density)
- Parking requirements
- Special overlay districts

Data sourced from official county zoning codes and compiled for quick reference.
Always verify with official sources for permitting.
"""

import sqlite3
import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


# Database path
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "florida_zoning.db")


@dataclass
class ZoningDistrict:
    """Represents a zoning district"""
    county: str
    district_code: str
    district_name: str
    category: str  # residential, commercial, industrial, mixed-use, etc.
    description: str
    min_lot_size_sf: Optional[int]
    max_height_ft: Optional[int]
    max_stories: Optional[int]
    max_far: Optional[float]
    max_density_units_acre: Optional[float]
    front_setback_ft: Optional[int]
    side_setback_ft: Optional[int]
    rear_setback_ft: Optional[int]
    min_lot_width_ft: Optional[int]
    lot_coverage_pct: Optional[int]
    allowed_uses: List[str]
    conditional_uses: List[str]
    prohibited_uses: List[str]
    parking_requirements: Dict[str, str]
    notes: Optional[str]


class FloridaZoningDatabase:
    """
    Florida Zoning Database for South Florida counties
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._init_db()

    def _init_db(self):
        """Initialize the database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS counties (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    state TEXT DEFAULT 'FL',
                    zoning_code_url TEXT,
                    last_updated TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS zoning_districts (
                    id INTEGER PRIMARY KEY,
                    county_id INTEGER NOT NULL,
                    district_code TEXT NOT NULL,
                    district_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    min_lot_size_sf INTEGER,
                    max_height_ft INTEGER,
                    max_stories INTEGER,
                    max_far REAL,
                    max_density_units_acre REAL,
                    front_setback_ft INTEGER,
                    side_setback_ft INTEGER,
                    rear_setback_ft INTEGER,
                    min_lot_width_ft INTEGER,
                    lot_coverage_pct INTEGER,
                    notes TEXT,
                    FOREIGN KEY (county_id) REFERENCES counties(id),
                    UNIQUE(county_id, district_code)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS allowed_uses (
                    id INTEGER PRIMARY KEY,
                    district_id INTEGER NOT NULL,
                    use_name TEXT NOT NULL,
                    use_type TEXT NOT NULL,  -- permitted, conditional, prohibited
                    conditions TEXT,
                    FOREIGN KEY (district_id) REFERENCES zoning_districts(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS parking_requirements (
                    id INTEGER PRIMARY KEY,
                    district_id INTEGER,
                    county_id INTEGER,
                    use_category TEXT NOT NULL,
                    requirement TEXT NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (district_id) REFERENCES zoning_districts(id),
                    FOREIGN KEY (county_id) REFERENCES counties(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS overlay_districts (
                    id INTEGER PRIMARY KEY,
                    county_id INTEGER NOT NULL,
                    overlay_code TEXT NOT NULL,
                    overlay_name TEXT NOT NULL,
                    description TEXT,
                    additional_requirements TEXT,
                    FOREIGN KEY (county_id) REFERENCES counties(id)
                )
            """)

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_districts_county ON zoning_districts(county_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_districts_code ON zoning_districts(district_code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_districts_category ON zoning_districts(category)")

            conn.commit()

    def populate_default_data(self):
        """Populate database with South Florida zoning data"""
        self._populate_counties()
        self._populate_miami_dade_zoning()
        self._populate_broward_zoning()
        self._populate_palm_beach_zoning()
        self._populate_parking_requirements()

    def _populate_counties(self):
        """Add county records"""
        counties = [
            ("Miami-Dade", "FL", "https://library.municode.com/fl/miami_-_dade_county/codes/code_of_ordinances"),
            ("Broward", "FL", "https://library.municode.com/fl/broward_county/codes/code_of_ordinances"),
            ("Palm Beach", "FL", "https://library.municode.com/fl/palm_beach_county/codes/code_of_ordinances"),
        ]

        with sqlite3.connect(self.db_path) as conn:
            for name, state, url in counties:
                conn.execute("""
                    INSERT OR IGNORE INTO counties (name, state, zoning_code_url, last_updated)
                    VALUES (?, ?, ?, ?)
                """, (name, state, url, datetime.now().isoformat()))
            conn.commit()

    def _get_county_id(self, county_name: str) -> int:
        """Get county ID by name"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "SELECT id FROM counties WHERE name = ?", (county_name,)
            ).fetchone()
            return result[0] if result else None

    def _populate_miami_dade_zoning(self):
        """Populate Miami-Dade County zoning districts"""
        county_id = self._get_county_id("Miami-Dade")
        if not county_id:
            return

        # Miami-Dade Zoning Districts (Chapter 33 of Code)
        districts = [
            # RESIDENTIAL DISTRICTS
            {
                "code": "EU-M", "name": "Estate District (Modified)",
                "category": "residential",
                "description": "Very low density single-family residential",
                "min_lot_size_sf": 43560, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.25, "max_density": 1,
                "front": 50, "side": 25, "rear": 25, "width": 150, "coverage": 25,
                "uses": ["single-family", "agriculture", "home occupation"],
                "notes": "1 acre minimum lot"
            },
            {
                "code": "EU-1", "name": "Estate District",
                "category": "residential",
                "description": "Low density single-family residential",
                "min_lot_size_sf": 30000, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.30, "max_density": 1.45,
                "front": 40, "side": 15, "rear": 25, "width": 100, "coverage": 30,
                "uses": ["single-family", "home occupation"],
                "notes": "30,000 SF minimum lot"
            },
            {
                "code": "EU-2", "name": "Estate District",
                "category": "residential",
                "description": "Low density single-family residential",
                "min_lot_size_sf": 20000, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.35, "max_density": 2.18,
                "front": 35, "side": 12, "rear": 25, "width": 85, "coverage": 35,
                "uses": ["single-family", "home occupation"],
                "notes": "20,000 SF minimum lot"
            },
            {
                "code": "RU-1", "name": "Single-Family Residential",
                "category": "residential",
                "description": "Single-family residential district",
                "min_lot_size_sf": 7500, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.40, "max_density": 5.8,
                "front": 25, "side": 7.5, "rear": 15, "width": 75, "coverage": 35,
                "uses": ["single-family", "home occupation", "accessory dwelling unit"],
                "notes": "Standard single-family district"
            },
            {
                "code": "RU-1M(a)", "name": "Modified Single-Family",
                "category": "residential",
                "description": "Modified single-family with reduced lot size",
                "min_lot_size_sf": 6000, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.45, "max_density": 7.26,
                "front": 25, "side": 5, "rear": 15, "width": 60, "coverage": 40,
                "uses": ["single-family", "home occupation", "accessory dwelling unit"],
                "notes": "Smaller lot single-family"
            },
            {
                "code": "RU-2", "name": "Two-Family Residential",
                "category": "residential",
                "description": "Duplex residential district",
                "min_lot_size_sf": 7500, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.50, "max_density": 11.6,
                "front": 25, "side": 7.5, "rear": 15, "width": 75, "coverage": 40,
                "uses": ["single-family", "duplex", "home occupation"],
                "notes": "Allows duplexes"
            },
            {
                "code": "RU-3", "name": "Townhouse Residential",
                "category": "residential",
                "description": "Townhouse residential district",
                "min_lot_size_sf": 2000, "max_height_ft": 45, "max_stories": 3,
                "max_far": 0.75, "max_density": 18,
                "front": 20, "side": 0, "rear": 10, "width": 20, "coverage": 50,
                "uses": ["townhouse", "single-family", "duplex"],
                "notes": "Attached townhouse units"
            },
            {
                "code": "RU-4", "name": "Apartment House District (Low)",
                "category": "residential",
                "description": "Low-rise multifamily residential",
                "min_lot_size_sf": 10000, "max_height_ft": 45, "max_stories": 3,
                "max_far": 1.0, "max_density": 25,
                "front": 25, "side": 15, "rear": 15, "width": 75, "coverage": 40,
                "uses": ["multifamily", "townhouse", "duplex", "single-family"],
                "notes": "Low-rise apartments"
            },
            {
                "code": "RU-4L", "name": "Apartment House District (Limited)",
                "category": "residential",
                "description": "Limited low-rise multifamily",
                "min_lot_size_sf": 10000, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.75, "max_density": 13,
                "front": 25, "side": 15, "rear": 15, "width": 75, "coverage": 35,
                "uses": ["multifamily", "townhouse", "duplex", "single-family"],
                "notes": "Limited to 2 stories"
            },
            {
                "code": "RU-5", "name": "Apartment House District (Medium)",
                "category": "residential",
                "description": "Medium-density multifamily",
                "min_lot_size_sf": 10000, "max_height_ft": 60, "max_stories": None,
                "max_far": 1.5, "max_density": 50,
                "front": 25, "side": 15, "rear": 15, "width": 75, "coverage": 40,
                "uses": ["multifamily", "townhouse", "duplex", "single-family"],
                "notes": "Mid-rise apartments"
            },
            {
                "code": "RU-5A", "name": "Apartment House District (High)",
                "category": "residential",
                "description": "High-density multifamily",
                "min_lot_size_sf": 10000, "max_height_ft": 150, "max_stories": None,
                "max_far": 2.5, "max_density": 125,
                "front": 25, "side": 15, "rear": 15, "width": 75, "coverage": 40,
                "uses": ["multifamily", "hotel", "mixed-use residential"],
                "notes": "High-rise apartments"
            },

            # COMMERCIAL DISTRICTS
            {
                "code": "BU-1", "name": "Neighborhood Business",
                "category": "commercial",
                "description": "Small-scale neighborhood commercial",
                "min_lot_size_sf": 7500, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.50, "max_density": None,
                "front": 25, "side": 10, "rear": 10, "width": 75, "coverage": 35,
                "uses": ["retail", "office", "restaurant", "personal services"],
                "notes": "Neighborhood-serving retail"
            },
            {
                "code": "BU-1A", "name": "Limited Business",
                "category": "commercial",
                "description": "Limited neighborhood business",
                "min_lot_size_sf": 5000, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.75, "max_density": None,
                "front": 20, "side": 0, "rear": 10, "width": 50, "coverage": 50,
                "uses": ["retail", "office", "restaurant", "personal services"],
                "notes": "Small neighborhood retail"
            },
            {
                "code": "BU-2", "name": "Special Business",
                "category": "commercial",
                "description": "General commercial district",
                "min_lot_size_sf": 10000, "max_height_ft": 45, "max_stories": 4,
                "max_far": 1.0, "max_density": None,
                "front": 25, "side": 10, "rear": 10, "width": 100, "coverage": 40,
                "uses": ["retail", "office", "restaurant", "hotel", "entertainment"],
                "notes": "General commercial"
            },
            {
                "code": "BU-3", "name": "Liberal Business",
                "category": "commercial",
                "description": "Highway-oriented commercial",
                "min_lot_size_sf": 20000, "max_height_ft": 45, "max_stories": 4,
                "max_far": 1.0, "max_density": None,
                "front": 50, "side": 15, "rear": 15, "width": 100, "coverage": 40,
                "uses": ["auto sales", "drive-through", "big box retail", "warehouse retail"],
                "notes": "Auto-oriented commercial"
            },

            # OFFICE DISTRICTS
            {
                "code": "OPD", "name": "Office Park District",
                "category": "office",
                "description": "Office park development",
                "min_lot_size_sf": 43560, "max_height_ft": 75, "max_stories": 6,
                "max_far": 0.50, "max_density": None,
                "front": 50, "side": 25, "rear": 25, "width": 200, "coverage": 25,
                "uses": ["office", "medical office", "research"],
                "notes": "Campus-style office"
            },

            # INDUSTRIAL DISTRICTS
            {
                "code": "IU-1", "name": "Light Industrial",
                "category": "industrial",
                "description": "Light industrial and warehouse",
                "min_lot_size_sf": 20000, "max_height_ft": 45, "max_stories": None,
                "max_far": 0.75, "max_density": None,
                "front": 40, "side": 25, "rear": 25, "width": 100, "coverage": 50,
                "uses": ["warehouse", "light manufacturing", "distribution", "flex space"],
                "notes": "Light industrial"
            },
            {
                "code": "IU-2", "name": "Medium Industrial",
                "category": "industrial",
                "description": "General industrial",
                "min_lot_size_sf": 20000, "max_height_ft": 60, "max_stories": None,
                "max_far": 1.0, "max_density": None,
                "front": 40, "side": 25, "rear": 25, "width": 100, "coverage": 60,
                "uses": ["manufacturing", "warehouse", "distribution", "processing"],
                "notes": "General industrial"
            },
            {
                "code": "IU-3", "name": "Heavy Industrial",
                "category": "industrial",
                "description": "Heavy industrial",
                "min_lot_size_sf": 43560, "max_height_ft": None, "max_stories": None,
                "max_far": 1.0, "max_density": None,
                "front": 50, "side": 50, "rear": 50, "width": 150, "coverage": 60,
                "uses": ["heavy manufacturing", "processing", "extraction"],
                "notes": "Heavy industrial, requires special permits"
            },
        ]

        self._insert_districts(county_id, districts)

    def _populate_broward_zoning(self):
        """Populate Broward County zoning districts"""
        county_id = self._get_county_id("Broward")
        if not county_id:
            return

        # Broward County Zoning (Chapter 39 of Code)
        districts = [
            # RESIDENTIAL
            {
                "code": "RS-1", "name": "Residential Single Family 1",
                "category": "residential",
                "description": "Low density single-family",
                "min_lot_size_sf": 20000, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.25, "max_density": 2,
                "front": 35, "side": 15, "rear": 25, "width": 100, "coverage": 30,
                "uses": ["single-family"],
                "notes": "Estate residential"
            },
            {
                "code": "RS-2", "name": "Residential Single Family 2",
                "category": "residential",
                "description": "Medium density single-family",
                "min_lot_size_sf": 10000, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.35, "max_density": 4,
                "front": 25, "side": 10, "rear": 20, "width": 75, "coverage": 35,
                "uses": ["single-family", "accessory dwelling"],
                "notes": "Standard single-family"
            },
            {
                "code": "RS-3", "name": "Residential Single Family 3",
                "category": "residential",
                "description": "Higher density single-family",
                "min_lot_size_sf": 7500, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.40, "max_density": 6,
                "front": 25, "side": 7.5, "rear": 15, "width": 60, "coverage": 40,
                "uses": ["single-family", "accessory dwelling"],
                "notes": "Higher density SF"
            },
            {
                "code": "RD-7", "name": "Residential Duplex 7",
                "category": "residential",
                "description": "Duplex residential",
                "min_lot_size_sf": 7500, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.50, "max_density": 7,
                "front": 25, "side": 7.5, "rear": 15, "width": 75, "coverage": 40,
                "uses": ["single-family", "duplex"],
                "notes": "Allows duplexes"
            },
            {
                "code": "RM-15", "name": "Residential Multiple 15",
                "category": "residential",
                "description": "Low-rise multifamily",
                "min_lot_size_sf": 10000, "max_height_ft": 45, "max_stories": 3,
                "max_far": 0.75, "max_density": 15,
                "front": 25, "side": 15, "rear": 15, "width": 100, "coverage": 40,
                "uses": ["multifamily", "townhouse", "single-family"],
                "notes": "Low-rise apartments"
            },
            {
                "code": "RM-25", "name": "Residential Multiple 25",
                "category": "residential",
                "description": "Medium-rise multifamily",
                "min_lot_size_sf": 10000, "max_height_ft": 65, "max_stories": 5,
                "max_far": 1.25, "max_density": 25,
                "front": 25, "side": 15, "rear": 20, "width": 100, "coverage": 40,
                "uses": ["multifamily", "townhouse"],
                "notes": "Mid-rise apartments"
            },
            {
                "code": "RM-50", "name": "Residential Multiple 50",
                "category": "residential",
                "description": "High-rise multifamily",
                "min_lot_size_sf": 20000, "max_height_ft": 150, "max_stories": None,
                "max_far": 2.5, "max_density": 50,
                "front": 25, "side": 25, "rear": 25, "width": 150, "coverage": 40,
                "uses": ["multifamily", "hotel", "mixed-use"],
                "notes": "High-rise residential"
            },

            # COMMERCIAL
            {
                "code": "B-1", "name": "Business, Office",
                "category": "commercial",
                "description": "Office and limited retail",
                "min_lot_size_sf": 10000, "max_height_ft": 45, "max_stories": 4,
                "max_far": 0.75, "max_density": None,
                "front": 25, "side": 15, "rear": 15, "width": 100, "coverage": 40,
                "uses": ["office", "medical office", "bank", "limited retail"],
                "notes": "Office district"
            },
            {
                "code": "B-2", "name": "Business, Community",
                "category": "commercial",
                "description": "Community commercial",
                "min_lot_size_sf": 15000, "max_height_ft": 55, "max_stories": 4,
                "max_far": 1.0, "max_density": None,
                "front": 25, "side": 15, "rear": 20, "width": 100, "coverage": 45,
                "uses": ["retail", "restaurant", "office", "entertainment"],
                "notes": "General commercial"
            },
            {
                "code": "B-3", "name": "Business, General",
                "category": "commercial",
                "description": "General business",
                "min_lot_size_sf": 20000, "max_height_ft": 65, "max_stories": 5,
                "max_far": 1.5, "max_density": None,
                "front": 30, "side": 15, "rear": 20, "width": 100, "coverage": 50,
                "uses": ["retail", "office", "hotel", "entertainment", "auto sales"],
                "notes": "Intensive commercial"
            },

            # INDUSTRIAL
            {
                "code": "I-1", "name": "Industrial, Light",
                "category": "industrial",
                "description": "Light industrial",
                "min_lot_size_sf": 20000, "max_height_ft": 45, "max_stories": None,
                "max_far": 0.60, "max_density": None,
                "front": 35, "side": 20, "rear": 20, "width": 100, "coverage": 50,
                "uses": ["warehouse", "light manufacturing", "distribution"],
                "notes": "Light industrial"
            },
            {
                "code": "I-2", "name": "Industrial, General",
                "category": "industrial",
                "description": "General industrial",
                "min_lot_size_sf": 30000, "max_height_ft": 55, "max_stories": None,
                "max_far": 0.75, "max_density": None,
                "front": 40, "side": 25, "rear": 25, "width": 150, "coverage": 60,
                "uses": ["manufacturing", "warehouse", "distribution", "processing"],
                "notes": "General industrial"
            },
        ]

        self._insert_districts(county_id, districts)

    def _populate_palm_beach_zoning(self):
        """Populate Palm Beach County zoning districts"""
        county_id = self._get_county_id("Palm Beach")
        if not county_id:
            return

        # Palm Beach County Zoning (ULDC Article 3)
        districts = [
            # RESIDENTIAL
            {
                "code": "RE", "name": "Residential Estate",
                "category": "residential",
                "description": "Estate residential",
                "min_lot_size_sf": 217800, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.15, "max_density": 0.2,
                "front": 75, "side": 50, "rear": 50, "width": 250, "coverage": 15,
                "uses": ["single-family", "agriculture"],
                "notes": "5-acre minimum"
            },
            {
                "code": "RS", "name": "Residential Single-Family",
                "category": "residential",
                "description": "Single-family residential",
                "min_lot_size_sf": 7500, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.40, "max_density": 5,
                "front": 25, "side": 7.5, "rear": 15, "width": 75, "coverage": 40,
                "uses": ["single-family", "accessory dwelling"],
                "notes": "Standard single-family"
            },
            {
                "code": "RT", "name": "Residential Transitional",
                "category": "residential",
                "description": "Transitional residential",
                "min_lot_size_sf": 6000, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.50, "max_density": 8,
                "front": 25, "side": 7.5, "rear": 15, "width": 60, "coverage": 45,
                "uses": ["single-family", "duplex", "zero-lot-line"],
                "notes": "Transitional density"
            },
            {
                "code": "RM", "name": "Residential Medium Density",
                "category": "residential",
                "description": "Medium density residential",
                "min_lot_size_sf": 10000, "max_height_ft": 45, "max_stories": 3,
                "max_far": 0.75, "max_density": 12,
                "front": 25, "side": 15, "rear": 20, "width": 100, "coverage": 40,
                "uses": ["multifamily", "townhouse", "duplex"],
                "notes": "Medium density MF"
            },
            {
                "code": "RH", "name": "Residential High Density",
                "category": "residential",
                "description": "High density residential",
                "min_lot_size_sf": 20000, "max_height_ft": None, "max_stories": None,
                "max_far": 2.0, "max_density": 30,
                "front": 30, "side": 20, "rear": 25, "width": 150, "coverage": 45,
                "uses": ["multifamily", "hotel", "mixed-use"],
                "notes": "High density residential"
            },

            # COMMERCIAL
            {
                "code": "CL", "name": "Commercial Low Intensity",
                "category": "commercial",
                "description": "Low intensity commercial",
                "min_lot_size_sf": 10000, "max_height_ft": 35, "max_stories": 2,
                "max_far": 0.35, "max_density": None,
                "front": 25, "side": 15, "rear": 20, "width": 100, "coverage": 35,
                "uses": ["office", "limited retail", "personal services"],
                "notes": "Neighborhood commercial"
            },
            {
                "code": "CG", "name": "Commercial General",
                "category": "commercial",
                "description": "General commercial",
                "min_lot_size_sf": 15000, "max_height_ft": 55, "max_stories": 4,
                "max_far": 1.0, "max_density": None,
                "front": 25, "side": 15, "rear": 20, "width": 100, "coverage": 50,
                "uses": ["retail", "office", "restaurant", "entertainment"],
                "notes": "General commercial"
            },
            {
                "code": "CH", "name": "Commercial High Intensity",
                "category": "commercial",
                "description": "High intensity commercial",
                "min_lot_size_sf": 20000, "max_height_ft": 75, "max_stories": 6,
                "max_far": 1.5, "max_density": None,
                "front": 30, "side": 20, "rear": 25, "width": 150, "coverage": 50,
                "uses": ["retail", "office", "hotel", "entertainment", "mixed-use"],
                "notes": "Intensive commercial"
            },

            # INDUSTRIAL
            {
                "code": "IL", "name": "Industrial Light",
                "category": "industrial",
                "description": "Light industrial",
                "min_lot_size_sf": 20000, "max_height_ft": 45, "max_stories": None,
                "max_far": 0.60, "max_density": None,
                "front": 35, "side": 20, "rear": 25, "width": 100, "coverage": 50,
                "uses": ["warehouse", "light manufacturing", "flex"],
                "notes": "Light industrial"
            },
            {
                "code": "IG", "name": "Industrial General",
                "category": "industrial",
                "description": "General industrial",
                "min_lot_size_sf": 30000, "max_height_ft": 55, "max_stories": None,
                "max_far": 0.75, "max_density": None,
                "front": 40, "side": 25, "rear": 30, "width": 150, "coverage": 55,
                "uses": ["manufacturing", "warehouse", "processing"],
                "notes": "General industrial"
            },
        ]

        self._insert_districts(county_id, districts)

    def _insert_districts(self, county_id: int, districts: List[Dict]):
        """Insert district records"""
        with sqlite3.connect(self.db_path) as conn:
            for d in districts:
                # Insert district
                conn.execute("""
                    INSERT OR REPLACE INTO zoning_districts (
                        county_id, district_code, district_name, category, description,
                        min_lot_size_sf, max_height_ft, max_stories, max_far, max_density_units_acre,
                        front_setback_ft, side_setback_ft, rear_setback_ft, min_lot_width_ft,
                        lot_coverage_pct, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    county_id, d["code"], d["name"], d["category"], d["description"],
                    d.get("min_lot_size_sf"), d.get("max_height_ft"), d.get("max_stories"),
                    d.get("max_far"), d.get("max_density"),
                    d.get("front"), d.get("side"), d.get("rear"), d.get("width"),
                    d.get("coverage"), d.get("notes")
                ))

                # Get district ID for uses
                district_id = conn.execute(
                    "SELECT id FROM zoning_districts WHERE county_id = ? AND district_code = ?",
                    (county_id, d["code"])
                ).fetchone()[0]

                # Insert allowed uses
                for use in d.get("uses", []):
                    conn.execute("""
                        INSERT OR IGNORE INTO allowed_uses (district_id, use_name, use_type)
                        VALUES (?, ?, 'permitted')
                    """, (district_id, use))

            conn.commit()

    def _populate_parking_requirements(self):
        """Populate parking requirements (county-wide)"""
        # Common parking requirements for South Florida
        parking_reqs = {
            "Miami-Dade": [
                ("Single-family residential", "2 spaces per unit"),
                ("Duplex", "2 spaces per unit"),
                ("Multifamily (efficiency)", "1.5 spaces per unit"),
                ("Multifamily (1-bedroom)", "1.5 spaces per unit"),
                ("Multifamily (2+ bedroom)", "2 spaces per unit"),
                ("Retail (general)", "1 space per 200 SF GFA"),
                ("Office (general)", "1 space per 300 SF GFA"),
                ("Restaurant", "1 space per 100 SF + 1 per 3 employees"),
                ("Hotel/Motel", "1 space per guest room + 1 per 3 employees"),
                ("Medical office", "1 space per 200 SF GFA"),
                ("Warehouse", "1 space per 2,000 SF GFA"),
                ("Industrial", "1 space per 1,000 SF GFA"),
                ("Church/Religious", "1 space per 4 seats"),
                ("School (K-8)", "1 space per classroom + 1 per 10 students"),
                ("School (High)", "1 space per classroom + 1 per 5 students"),
            ],
            "Broward": [
                ("Single-family residential", "2 spaces per unit"),
                ("Multifamily", "2 spaces per unit"),
                ("Retail", "1 space per 250 SF GFA"),
                ("Office", "1 space per 300 SF GFA"),
                ("Restaurant", "1 space per 100 SF dining area"),
                ("Hotel", "1 space per room"),
                ("Warehouse", "1 space per 2,500 SF GFA"),
                ("Industrial", "1 space per 1,000 SF GFA"),
            ],
            "Palm Beach": [
                ("Single-family", "2 spaces per unit"),
                ("Multifamily", "1.75-2.25 spaces per unit based on bedrooms"),
                ("Retail", "1 space per 200 SF GFA"),
                ("Office", "1 space per 300 SF GFA"),
                ("Restaurant", "1 space per 75 SF customer area"),
                ("Hotel", "1 space per room + 1 per 200 SF public area"),
                ("Warehouse", "1 space per 2,000 SF GFA"),
            ],
        }

        with sqlite3.connect(self.db_path) as conn:
            for county, reqs in parking_reqs.items():
                county_id = self._get_county_id(county)
                if county_id:
                    for use, req in reqs:
                        conn.execute("""
                            INSERT OR IGNORE INTO parking_requirements (county_id, use_category, requirement)
                            VALUES (?, ?, ?)
                        """, (county_id, use, req))
            conn.commit()

    # Query methods
    def get_district(self, county: str, district_code: str) -> Optional[Dict]:
        """Get zoning district details"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            result = conn.execute("""
                SELECT d.*, c.name as county_name
                FROM zoning_districts d
                JOIN counties c ON d.county_id = c.id
                WHERE c.name = ? AND d.district_code = ?
            """, (county, district_code)).fetchone()

            if result:
                district = dict(result)

                # Get allowed uses
                uses = conn.execute("""
                    SELECT use_name, use_type FROM allowed_uses WHERE district_id = ?
                """, (district['id'],)).fetchall()
                district['allowed_uses'] = [u['use_name'] for u in uses if u['use_type'] == 'permitted']
                district['conditional_uses'] = [u['use_name'] for u in uses if u['use_type'] == 'conditional']

                return district
        return None

    def search_districts(
        self,
        county: str = None,
        category: str = None,
        min_density: float = None,
        max_height: int = None,
        use: str = None
    ) -> List[Dict]:
        """Search for zoning districts matching criteria"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = """
                SELECT DISTINCT d.*, c.name as county_name
                FROM zoning_districts d
                JOIN counties c ON d.county_id = c.id
            """
            conditions = []
            params = []

            if county:
                conditions.append("c.name = ?")
                params.append(county)

            if category:
                conditions.append("d.category = ?")
                params.append(category)

            if min_density:
                conditions.append("d.max_density_units_acre >= ?")
                params.append(min_density)

            if max_height:
                conditions.append("(d.max_height_ft IS NULL OR d.max_height_ft >= ?)")
                params.append(max_height)

            if use:
                query += " LEFT JOIN allowed_uses au ON d.id = au.district_id"
                conditions.append("au.use_name LIKE ?")
                params.append(f"%{use}%")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY c.name, d.category, d.district_code"

            results = conn.execute(query, params).fetchall()
            return [dict(r) for r in results]

    def get_parking_requirements(self, county: str, use_category: str = None) -> List[Dict]:
        """Get parking requirements"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if use_category:
                results = conn.execute("""
                    SELECT p.*, c.name as county_name
                    FROM parking_requirements p
                    JOIN counties c ON p.county_id = c.id
                    WHERE c.name = ? AND p.use_category LIKE ?
                """, (county, f"%{use_category}%")).fetchall()
            else:
                results = conn.execute("""
                    SELECT p.*, c.name as county_name
                    FROM parking_requirements p
                    JOIN counties c ON p.county_id = c.id
                    WHERE c.name = ?
                """, (county,)).fetchall()

            return [dict(r) for r in results]

    def get_all_districts(self, county: str = None) -> List[Dict]:
        """Get all districts, optionally filtered by county"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if county:
                results = conn.execute("""
                    SELECT d.*, c.name as county_name
                    FROM zoning_districts d
                    JOIN counties c ON d.county_id = c.id
                    WHERE c.name = ?
                    ORDER BY d.category, d.district_code
                """, (county,)).fetchall()
            else:
                results = conn.execute("""
                    SELECT d.*, c.name as county_name
                    FROM zoning_districts d
                    JOIN counties c ON d.county_id = c.id
                    ORDER BY c.name, d.category, d.district_code
                """).fetchall()

            return [dict(r) for r in results]

    def lookup_by_density(self, county: str, target_density: float) -> List[Dict]:
        """Find districts that allow a specific density"""
        return self.search_districts(county=county, min_density=target_density)

    def compare_districts(self, districts: List[tuple]) -> List[Dict]:
        """Compare multiple districts side by side"""
        results = []
        for county, code in districts:
            district = self.get_district(county, code)
            if district:
                results.append(district)
        return results

    def format_district_report(self, district: Dict) -> str:
        """Format district data as readable report"""
        lines = [
            "=" * 60,
            f"ZONING DISTRICT: {district['district_code']}",
            "=" * 60,
            "",
            f"District Name: {district['district_name']}",
            f"County: {district['county_name']}",
            f"Category: {district['category'].title()}",
            f"Description: {district['description']}",
            "",
            "DEVELOPMENT STANDARDS:",
            f"  Minimum Lot Size: {district['min_lot_size_sf']:,} SF" if district['min_lot_size_sf'] else "  Minimum Lot Size: N/A",
            f"  Minimum Lot Width: {district['min_lot_width_ft']} ft" if district['min_lot_width_ft'] else "  Minimum Lot Width: N/A",
            f"  Maximum Height: {district['max_height_ft']} ft" if district['max_height_ft'] else "  Maximum Height: No limit",
            f"  Maximum Stories: {district['max_stories']}" if district['max_stories'] else "  Maximum Stories: No limit",
            f"  Maximum FAR: {district['max_far']}" if district['max_far'] else "  Maximum FAR: N/A",
            f"  Maximum Density: {district['max_density_units_acre']} units/acre" if district['max_density_units_acre'] else "  Maximum Density: N/A",
            f"  Lot Coverage: {district['lot_coverage_pct']}%" if district['lot_coverage_pct'] else "  Lot Coverage: N/A",
            "",
            "SETBACKS:",
            f"  Front: {district['front_setback_ft']} ft" if district['front_setback_ft'] else "  Front: N/A",
            f"  Side: {district['side_setback_ft']} ft" if district['side_setback_ft'] else "  Side: N/A",
            f"  Rear: {district['rear_setback_ft']} ft" if district['rear_setback_ft'] else "  Rear: N/A",
        ]

        if district.get('allowed_uses'):
            lines.extend(["", "PERMITTED USES:"])
            for use in district['allowed_uses']:
                lines.append(f"  • {use}")

        if district.get('notes'):
            lines.extend(["", f"NOTES: {district['notes']}"])

        lines.extend(["", "=" * 60])

        return "\n".join(lines)


def get_zoning_for_site(county: str, district_code: str) -> Dict[str, Any]:
    """
    Get zoning information for a specific site

    Args:
        county: County name (Miami-Dade, Broward, Palm Beach)
        district_code: Zoning district code (e.g., RU-1, RS-2, etc.)

    Returns:
        Dictionary with zoning details
    """
    db = FloridaZoningDatabase()

    # Ensure data is populated
    if not db.get_all_districts():
        db.populate_default_data()

    district = db.get_district(county, district_code)
    if not district:
        return {
            "found": False,
            "error": f"District {district_code} not found in {county}",
            "suggestion": "Check the county property appraiser for official zoning"
        }

    parking = db.get_parking_requirements(county)

    return {
        "found": True,
        "district": district,
        "parking_requirements": parking,
        "source": f"{county} County Zoning Code",
        "disclaimer": "Verify all information with official county sources before relying on for permitting"
    }


if __name__ == "__main__":
    print("Florida Zoning Database")
    print("=" * 60)

    # Initialize and populate
    db = FloridaZoningDatabase()
    db.populate_default_data()

    # Test queries
    print("\nMiami-Dade RU-1 (Single-Family):")
    district = db.get_district("Miami-Dade", "RU-1")
    if district:
        print(db.format_district_report(district))

    print("\nDistricts allowing 25+ units/acre in Miami-Dade:")
    high_density = db.lookup_by_density("Miami-Dade", 25)
    for d in high_density[:5]:
        print(f"  {d['district_code']}: {d['district_name']} ({d['max_density_units_acre']} u/ac)")

    print("\nParking requirements for Retail in Miami-Dade:")
    parking = db.get_parking_requirements("Miami-Dade", "Retail")
    for p in parking:
        print(f"  {p['use_category']}: {p['requirement']}")

    print("\nAll counties loaded:")
    all_districts = db.get_all_districts()
    print(f"  Total districts: {len(all_districts)}")
    for county in ["Miami-Dade", "Broward", "Palm Beach"]:
        county_count = len([d for d in all_districts if d['county_name'] == county])
        print(f"  {county}: {county_count} districts")

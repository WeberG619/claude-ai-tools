"""
Jurisdiction Requirements Database
===================================
Comprehensive database of South Florida building department requirements,
submittal procedures, fees, and contact information.

Author: BIM Ops Studio
"""

import sqlite3
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any


class JurisdictionType(Enum):
    """Types of jurisdictions"""
    COUNTY = "county"
    MUNICIPALITY = "municipality"
    SPECIAL_DISTRICT = "special_district"


class SubmissionMethod(Enum):
    """How plans can be submitted"""
    ONLINE_ONLY = "online_only"
    IN_PERSON_ONLY = "in_person_only"
    BOTH = "both"
    ELECTRONIC_REVIEW = "electronic_review"


class JurisdictionDatabase:
    """
    Database of jurisdiction-specific requirements for building permits
    in South Florida (Miami-Dade, Broward, Palm Beach counties).
    """

    def __init__(self, db_path: str = "jurisdiction_requirements.db"):
        self.db_path = db_path
        self._init_database()
        self._populate_jurisdictions()

    def _init_database(self):
        """Initialize the database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            # Main jurisdictions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jurisdictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    jurisdiction_type TEXT NOT NULL,
                    county TEXT NOT NULL,
                    hvhz BOOLEAN DEFAULT FALSE,
                    flood_zone_default TEXT,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Contact information
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jurisdiction_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jurisdiction_id INTEGER NOT NULL,
                    department TEXT NOT NULL,
                    address TEXT,
                    phone TEXT,
                    fax TEXT,
                    email TEXT,
                    website TEXT,
                    hours TEXT,
                    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(id)
                )
            """)

            # Submission requirements
            conn.execute("""
                CREATE TABLE IF NOT EXISTS submission_requirements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jurisdiction_id INTEGER NOT NULL,
                    permit_type TEXT NOT NULL,
                    requirement_name TEXT NOT NULL,
                    requirement_description TEXT,
                    required BOOLEAN DEFAULT TRUE,
                    copies_needed INTEGER DEFAULT 1,
                    format_requirements TEXT,
                    notes TEXT,
                    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(id)
                )
            """)

            # Fee structures
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fee_structures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jurisdiction_id INTEGER NOT NULL,
                    fee_type TEXT NOT NULL,
                    fee_name TEXT NOT NULL,
                    calculation_method TEXT,
                    base_fee REAL,
                    per_sqft_rate REAL,
                    minimum_fee REAL,
                    maximum_fee REAL,
                    notes TEXT,
                    effective_date TEXT,
                    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(id)
                )
            """)

            # Review timeframes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS review_timeframes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jurisdiction_id INTEGER NOT NULL,
                    permit_type TEXT NOT NULL,
                    project_type TEXT,
                    standard_review_days INTEGER,
                    expedited_review_days INTEGER,
                    expedited_fee_multiplier REAL DEFAULT 2.0,
                    notes TEXT,
                    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(id)
                )
            """)

            # Code amendments (local amendments to FBC)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS local_amendments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jurisdiction_id INTEGER NOT NULL,
                    code_section TEXT NOT NULL,
                    amendment_description TEXT NOT NULL,
                    more_restrictive BOOLEAN DEFAULT TRUE,
                    effective_date TEXT,
                    notes TEXT,
                    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(id)
                )
            """)

            # Special requirements
            conn.execute("""
                CREATE TABLE IF NOT EXISTS special_requirements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jurisdiction_id INTEGER NOT NULL,
                    requirement_type TEXT NOT NULL,
                    requirement_name TEXT NOT NULL,
                    description TEXT,
                    applies_to TEXT,
                    trigger_condition TEXT,
                    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(id)
                )
            """)

            # Online submission portals
            conn.execute("""
                CREATE TABLE IF NOT EXISTS submission_portals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jurisdiction_id INTEGER NOT NULL,
                    portal_name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    portal_type TEXT,
                    account_required BOOLEAN DEFAULT TRUE,
                    electronic_stamps_accepted BOOLEAN DEFAULT FALSE,
                    max_file_size_mb INTEGER,
                    accepted_formats TEXT,
                    notes TEXT,
                    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(id)
                )
            """)

            # Inspection requirements
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inspection_requirements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jurisdiction_id INTEGER NOT NULL,
                    permit_type TEXT NOT NULL,
                    inspection_name TEXT NOT NULL,
                    inspection_order INTEGER,
                    required BOOLEAN DEFAULT TRUE,
                    special_inspector_required BOOLEAN DEFAULT FALSE,
                    notes TEXT,
                    FOREIGN KEY (jurisdiction_id) REFERENCES jurisdictions(id)
                )
            """)

            conn.commit()

    def _populate_jurisdictions(self):
        """Populate database with South Florida jurisdictions"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if already populated
            count = conn.execute(
                "SELECT COUNT(*) FROM jurisdictions"
            ).fetchone()[0]
            if count > 0:
                return

            # =====================================================================
            # MIAMI-DADE COUNTY JURISDICTIONS
            # =====================================================================

            # Unincorporated Miami-Dade
            self._add_jurisdiction(conn, {
                "name": "Miami-Dade County (Unincorporated)",
                "type": "county",
                "county": "Miami-Dade",
                "hvhz": True,
                "contacts": [{
                    "department": "Building Department",
                    "address": "11805 SW 26th Street, Miami, FL 33175",
                    "phone": "(786) 315-2000",
                    "website": "https://www.miamidade.gov/permits/",
                    "hours": "M-F 7:30 AM - 4:30 PM"
                }],
                "portal": {
                    "name": "Miami-Dade eBuild",
                    "url": "https://www.miamidade.gov/permits/permit-application.asp",
                    "electronic_stamps": True,
                    "max_file_size_mb": 100,
                    "formats": "PDF"
                },
                "timeframes": [
                    {"permit_type": "building", "standard": 30, "expedited": 10},
                    {"permit_type": "electrical", "standard": 14, "expedited": 5},
                    {"permit_type": "mechanical", "standard": 14, "expedited": 5},
                    {"permit_type": "plumbing", "standard": 14, "expedited": 5},
                    {"permit_type": "roofing", "standard": 7, "expedited": 3}
                ],
                "fees": [
                    {"type": "building", "name": "Building Permit Fee", "method": "per_sqft",
                     "per_sqft": 0.25, "min": 100},
                    {"type": "building", "name": "Plan Review Fee", "method": "percent_of_permit",
                     "base": 0.65},
                    {"type": "electrical", "name": "Electrical Permit", "method": "flat_plus_circuits",
                     "base": 75},
                    {"type": "roofing", "name": "Re-roofing Permit", "method": "per_square",
                     "per_sqft": 10, "min": 100}
                ],
                "special_requirements": [
                    {
                        "type": "HVHZ",
                        "name": "NOA Required",
                        "description": "All exterior products must have Miami-Dade NOA approval",
                        "applies_to": "all_exterior_products"
                    },
                    {
                        "type": "HVHZ",
                        "name": "40/50 Year Recertification",
                        "description": "Buildings 40 years or older require structural recertification",
                        "applies_to": "buildings_40_years_plus"
                    },
                    {
                        "type": "impact",
                        "name": "Impact Protection Required",
                        "description": "All glazing in WBDR must be impact-rated or protected",
                        "applies_to": "glazing_in_wbdr"
                    }
                ],
                "amendments": [
                    {
                        "section": "FBC 1626",
                        "description": "More stringent requirements for high-rise buildings",
                        "restrictive": True
                    }
                ]
            })

            # City of Miami
            self._add_jurisdiction(conn, {
                "name": "City of Miami",
                "type": "municipality",
                "county": "Miami-Dade",
                "hvhz": True,
                "contacts": [{
                    "department": "Building Department",
                    "address": "444 SW 2nd Avenue, Miami, FL 33130",
                    "phone": "(305) 416-1100",
                    "website": "https://www.miamigov.com/Residents/Building",
                    "hours": "M-F 8:00 AM - 5:00 PM"
                }],
                "portal": {
                    "name": "City of Miami ePlan",
                    "url": "https://eplan.miamigov.com/",
                    "electronic_stamps": True,
                    "max_file_size_mb": 200,
                    "formats": "PDF"
                },
                "timeframes": [
                    {"permit_type": "building", "standard": 21, "expedited": 7},
                    {"permit_type": "electrical", "standard": 10, "expedited": 3},
                    {"permit_type": "mechanical", "standard": 10, "expedited": 3},
                    {"permit_type": "plumbing", "standard": 10, "expedited": 3}
                ],
                "special_requirements": [
                    {
                        "type": "zoning",
                        "name": "Zoning Review Required",
                        "description": "All building permits require prior zoning approval",
                        "applies_to": "all_building_permits"
                    },
                    {
                        "type": "historic",
                        "name": "Historic Preservation Review",
                        "description": "Projects in historic districts require HEP review",
                        "applies_to": "historic_districts"
                    }
                ]
            })

            # City of Miami Beach
            self._add_jurisdiction(conn, {
                "name": "City of Miami Beach",
                "type": "municipality",
                "county": "Miami-Dade",
                "hvhz": True,
                "contacts": [{
                    "department": "Building Department",
                    "address": "1700 Convention Center Drive, Miami Beach, FL 33139",
                    "phone": "(305) 673-7610",
                    "website": "https://www.miamibeachfl.gov/city-hall/building/",
                    "hours": "M-F 8:00 AM - 5:00 PM"
                }],
                "portal": {
                    "name": "Miami Beach ePlan",
                    "url": "https://eplan.miamibeachfl.gov/",
                    "electronic_stamps": True,
                    "max_file_size_mb": 150,
                    "formats": "PDF"
                },
                "timeframes": [
                    {"permit_type": "building", "standard": 21, "expedited": 7},
                    {"permit_type": "electrical", "standard": 10, "expedited": 5}
                ],
                "special_requirements": [
                    {
                        "type": "flood",
                        "name": "Freeboard Requirement",
                        "description": "1-foot minimum freeboard above BFE required",
                        "applies_to": "all_construction"
                    },
                    {
                        "type": "resiliency",
                        "name": "Sea Level Rise Review",
                        "description": "Projects must address sea level rise adaptation",
                        "applies_to": "new_construction"
                    },
                    {
                        "type": "historic",
                        "name": "Art Deco Historic Review",
                        "description": "Art Deco district requires Design Review Board approval",
                        "applies_to": "art_deco_district"
                    }
                ]
            })

            # City of Coral Gables
            self._add_jurisdiction(conn, {
                "name": "City of Coral Gables",
                "type": "municipality",
                "county": "Miami-Dade",
                "hvhz": True,
                "contacts": [{
                    "department": "Building & Zoning",
                    "address": "427 Biltmore Way, Coral Gables, FL 33134",
                    "phone": "(305) 460-5235",
                    "website": "https://www.coralgables.com/departments/development-services",
                    "hours": "M-F 8:00 AM - 5:00 PM"
                }],
                "portal": {
                    "name": "Coral Gables ePlan",
                    "url": "https://aca-prod.accela.com/CGCoralgables/",
                    "electronic_stamps": True,
                    "max_file_size_mb": 100,
                    "formats": "PDF"
                },
                "special_requirements": [
                    {
                        "type": "architectural",
                        "name": "Board of Architects Review",
                        "description": "All new construction requires BOA approval",
                        "applies_to": "new_construction_and_additions"
                    },
                    {
                        "type": "historic",
                        "name": "Historic Preservation",
                        "description": "Many neighborhoods have historic overlay requirements",
                        "applies_to": "designated_historic_areas"
                    }
                ]
            })

            # City of Hialeah
            self._add_jurisdiction(conn, {
                "name": "City of Hialeah",
                "type": "municipality",
                "county": "Miami-Dade",
                "hvhz": True,
                "contacts": [{
                    "department": "Building Department",
                    "address": "501 Palm Avenue, Hialeah, FL 33010",
                    "phone": "(305) 883-8075",
                    "website": "https://www.hialeahfl.gov/213/Building-Department",
                    "hours": "M-F 8:00 AM - 5:00 PM"
                }],
                "portal": {
                    "name": "Hialeah Online Permitting",
                    "url": "https://buildinghialeah.com/",
                    "electronic_stamps": True,
                    "max_file_size_mb": 50,
                    "formats": "PDF"
                }
            })

            # =====================================================================
            # BROWARD COUNTY JURISDICTIONS
            # =====================================================================

            # Unincorporated Broward
            self._add_jurisdiction(conn, {
                "name": "Broward County (Unincorporated)",
                "type": "county",
                "county": "Broward",
                "hvhz": True,
                "contacts": [{
                    "department": "Environmental Licensing & Building Permitting Division",
                    "address": "1 N. University Drive, Suite 3500, Plantation, FL 33324",
                    "phone": "(954) 765-4500",
                    "website": "https://www.broward.org/Building/",
                    "hours": "M-F 8:00 AM - 5:00 PM"
                }],
                "portal": {
                    "name": "Broward County BLDS",
                    "url": "https://www.broward.org/Building/Pages/OnlineServices.aspx",
                    "electronic_stamps": True,
                    "max_file_size_mb": 100,
                    "formats": "PDF"
                },
                "timeframes": [
                    {"permit_type": "building", "standard": 30, "expedited": 10},
                    {"permit_type": "electrical", "standard": 14, "expedited": 5},
                    {"permit_type": "mechanical", "standard": 14, "expedited": 5},
                    {"permit_type": "plumbing", "standard": 14, "expedited": 5}
                ],
                "special_requirements": [
                    {
                        "type": "HVHZ",
                        "name": "NOA or FL Product Approval",
                        "description": "Exterior products require NOA or FL# approval",
                        "applies_to": "all_exterior_products"
                    }
                ]
            })

            # City of Fort Lauderdale
            self._add_jurisdiction(conn, {
                "name": "City of Fort Lauderdale",
                "type": "municipality",
                "county": "Broward",
                "hvhz": True,
                "contacts": [{
                    "department": "Development Services Department",
                    "address": "700 NW 19th Avenue, Fort Lauderdale, FL 33311",
                    "phone": "(954) 828-5454",
                    "website": "https://www.fortlauderdale.gov/departments/development-services",
                    "hours": "M-F 8:00 AM - 4:00 PM"
                }],
                "portal": {
                    "name": "Fort Lauderdale ePLAN",
                    "url": "https://eplanreview.fortlauderdale.gov/",
                    "electronic_stamps": True,
                    "max_file_size_mb": 150,
                    "formats": "PDF"
                },
                "timeframes": [
                    {"permit_type": "building", "standard": 21, "expedited": 7},
                    {"permit_type": "electrical", "standard": 10, "expedited": 5}
                ],
                "special_requirements": [
                    {
                        "type": "sea_level",
                        "name": "Freeboard Requirement",
                        "description": "Minimum 1-foot freeboard above BFE, 2-foot for critical facilities",
                        "applies_to": "flood_zones"
                    }
                ]
            })

            # City of Hollywood
            self._add_jurisdiction(conn, {
                "name": "City of Hollywood",
                "type": "municipality",
                "county": "Broward",
                "hvhz": True,
                "contacts": [{
                    "department": "Building Division",
                    "address": "2600 Hollywood Blvd, Hollywood, FL 33020",
                    "phone": "(954) 921-3271",
                    "website": "https://www.hollywoodfl.org/186/Building-Division",
                    "hours": "M-F 8:00 AM - 4:00 PM"
                }],
                "portal": {
                    "name": "Hollywood Building Portal",
                    "url": "https://permitting.hollywoodfl.org/",
                    "electronic_stamps": True,
                    "max_file_size_mb": 100,
                    "formats": "PDF"
                }
            })

            # City of Pompano Beach
            self._add_jurisdiction(conn, {
                "name": "City of Pompano Beach",
                "type": "municipality",
                "county": "Broward",
                "hvhz": True,
                "contacts": [{
                    "department": "Building Services Division",
                    "address": "100 W Atlantic Blvd, Pompano Beach, FL 33060",
                    "phone": "(954) 786-4670",
                    "website": "https://www.pompanobeachfl.gov/pages/building",
                    "hours": "M-F 8:00 AM - 5:00 PM"
                }]
            })

            # =====================================================================
            # PALM BEACH COUNTY JURISDICTIONS
            # =====================================================================

            # Unincorporated Palm Beach
            self._add_jurisdiction(conn, {
                "name": "Palm Beach County (Unincorporated)",
                "type": "county",
                "county": "Palm Beach",
                "hvhz": False,  # Only portions are HVHZ
                "contacts": [{
                    "department": "Building Division",
                    "address": "2300 N Jog Road, West Palm Beach, FL 33411",
                    "phone": "(561) 233-5100",
                    "website": "https://discover.pbcgov.org/pzb/building/",
                    "hours": "M-F 8:00 AM - 5:00 PM"
                }],
                "portal": {
                    "name": "PBC EDMS",
                    "url": "https://pbcpermits.com/",
                    "electronic_stamps": True,
                    "max_file_size_mb": 100,
                    "formats": "PDF"
                },
                "timeframes": [
                    {"permit_type": "building", "standard": 21, "expedited": 7},
                    {"permit_type": "electrical", "standard": 14, "expedited": 5},
                    {"permit_type": "mechanical", "standard": 14, "expedited": 5},
                    {"permit_type": "plumbing", "standard": 14, "expedited": 5}
                ],
                "special_requirements": [
                    {
                        "type": "coastal",
                        "name": "Coastal Construction",
                        "description": "Coastal construction line requirements apply east of I-95",
                        "applies_to": "coastal_areas"
                    }
                ]
            })

            # City of West Palm Beach
            self._add_jurisdiction(conn, {
                "name": "City of West Palm Beach",
                "type": "municipality",
                "county": "Palm Beach",
                "hvhz": False,
                "contacts": [{
                    "department": "Development Services",
                    "address": "401 Clematis Street, West Palm Beach, FL 33401",
                    "phone": "(561) 805-6700",
                    "website": "https://www.wpb.org/Government/Departments/Development-Services",
                    "hours": "M-F 8:00 AM - 5:00 PM"
                }],
                "portal": {
                    "name": "WPB EnerGov",
                    "url": "https://energov.wpb.org/",
                    "electronic_stamps": True,
                    "max_file_size_mb": 100,
                    "formats": "PDF"
                }
            })

            # City of Boca Raton
            self._add_jurisdiction(conn, {
                "name": "City of Boca Raton",
                "type": "municipality",
                "county": "Palm Beach",
                "hvhz": False,
                "contacts": [{
                    "department": "Development Services",
                    "address": "201 W Palmetto Park Rd, Boca Raton, FL 33432",
                    "phone": "(561) 393-7700",
                    "website": "https://www.myboca.us/210/Development-Services",
                    "hours": "M-F 8:00 AM - 5:00 PM"
                }],
                "portal": {
                    "name": "Boca Raton eTRAKiT",
                    "url": "https://public.ci.boca-raton.fl.us/etrak/",
                    "electronic_stamps": True,
                    "max_file_size_mb": 75,
                    "formats": "PDF"
                }
            })

            # City of Delray Beach
            self._add_jurisdiction(conn, {
                "name": "City of Delray Beach",
                "type": "municipality",
                "county": "Palm Beach",
                "hvhz": False,
                "contacts": [{
                    "department": "Building Department",
                    "address": "100 NW 1st Avenue, Delray Beach, FL 33444",
                    "phone": "(561) 243-7200",
                    "website": "https://www.delraybeachfl.gov/our-government/departments/development-services",
                    "hours": "M-F 8:00 AM - 5:00 PM"
                }]
            })

            conn.commit()

    def _add_jurisdiction(self, conn: sqlite3.Connection, data: dict):
        """Helper to add a jurisdiction with all related data"""
        # Insert main jurisdiction
        cursor = conn.execute("""
            INSERT INTO jurisdictions (name, jurisdiction_type, county, hvhz)
            VALUES (?, ?, ?, ?)
        """, (data["name"], data["type"], data["county"], data.get("hvhz", False)))
        jur_id = cursor.lastrowid

        # Add contacts
        for contact in data.get("contacts", []):
            conn.execute("""
                INSERT INTO jurisdiction_contacts
                (jurisdiction_id, department, address, phone, fax, email, website, hours)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (jur_id, contact.get("department"), contact.get("address"),
                  contact.get("phone"), contact.get("fax"), contact.get("email"),
                  contact.get("website"), contact.get("hours")))

        # Add portal
        portal = data.get("portal")
        if portal:
            conn.execute("""
                INSERT INTO submission_portals
                (jurisdiction_id, portal_name, url, electronic_stamps_accepted,
                 max_file_size_mb, accepted_formats)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (jur_id, portal.get("name"), portal.get("url"),
                  portal.get("electronic_stamps", False),
                  portal.get("max_file_size_mb"), portal.get("formats")))

        # Add timeframes
        for tf in data.get("timeframes", []):
            conn.execute("""
                INSERT INTO review_timeframes
                (jurisdiction_id, permit_type, standard_review_days, expedited_review_days)
                VALUES (?, ?, ?, ?)
            """, (jur_id, tf["permit_type"], tf.get("standard"), tf.get("expedited")))

        # Add fees
        for fee in data.get("fees", []):
            conn.execute("""
                INSERT INTO fee_structures
                (jurisdiction_id, fee_type, fee_name, calculation_method,
                 base_fee, per_sqft_rate, minimum_fee)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (jur_id, fee.get("type"), fee.get("name"), fee.get("method"),
                  fee.get("base"), fee.get("per_sqft"), fee.get("min")))

        # Add special requirements
        for req in data.get("special_requirements", []):
            conn.execute("""
                INSERT INTO special_requirements
                (jurisdiction_id, requirement_type, requirement_name,
                 description, applies_to)
                VALUES (?, ?, ?, ?, ?)
            """, (jur_id, req.get("type"), req.get("name"),
                  req.get("description"), req.get("applies_to")))

        # Add amendments
        for amend in data.get("amendments", []):
            conn.execute("""
                INSERT INTO local_amendments
                (jurisdiction_id, code_section, amendment_description, more_restrictive)
                VALUES (?, ?, ?, ?)
            """, (jur_id, amend.get("section"), amend.get("description"),
                  amend.get("restrictive", True)))

    # =========================================================================
    # QUERY METHODS
    # =========================================================================

    def get_all_jurisdictions(self, county: str = None) -> List[Dict]:
        """Get all jurisdictions, optionally filtered by county"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM jurisdictions WHERE active = 1"
            params = []
            if county:
                query += " AND county = ?"
                params.append(county)
            query += " ORDER BY county, name"

            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_jurisdiction(self, jurisdiction_id: int = None, name: str = None) -> Optional[Dict]:
        """Get jurisdiction by ID or name"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if jurisdiction_id:
                row = conn.execute(
                    "SELECT * FROM jurisdictions WHERE id = ?",
                    (jurisdiction_id,)
                ).fetchone()
            elif name:
                row = conn.execute(
                    "SELECT * FROM jurisdictions WHERE name LIKE ?",
                    (f"%{name}%",)
                ).fetchone()
            else:
                return None

            if not row:
                return None

            jur = dict(row)

            # Get contacts
            contacts = conn.execute("""
                SELECT * FROM jurisdiction_contacts WHERE jurisdiction_id = ?
            """, (jur['id'],)).fetchall()
            jur['contacts'] = [dict(c) for c in contacts]

            # Get portal info
            portal = conn.execute("""
                SELECT * FROM submission_portals WHERE jurisdiction_id = ?
            """, (jur['id'],)).fetchone()
            jur['portal'] = dict(portal) if portal else None

            # Get special requirements
            reqs = conn.execute("""
                SELECT * FROM special_requirements WHERE jurisdiction_id = ?
            """, (jur['id'],)).fetchall()
            jur['special_requirements'] = [dict(r) for r in reqs]

            # Get local amendments
            amendments = conn.execute("""
                SELECT * FROM local_amendments WHERE jurisdiction_id = ?
            """, (jur['id'],)).fetchall()
            jur['local_amendments'] = [dict(a) for a in amendments]

            return jur

    def get_submission_requirements(
        self,
        jurisdiction_id: int,
        permit_type: str
    ) -> List[Dict]:
        """Get submission requirements for a permit type"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM submission_requirements
                WHERE jurisdiction_id = ? AND permit_type = ?
                ORDER BY required DESC, requirement_name
            """, (jurisdiction_id, permit_type)).fetchall()
            return [dict(r) for r in rows]

    def get_review_timeframe(
        self,
        jurisdiction_id: int,
        permit_type: str
    ) -> Optional[Dict]:
        """Get review timeframe for a permit type"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM review_timeframes
                WHERE jurisdiction_id = ? AND permit_type = ?
            """, (jurisdiction_id, permit_type)).fetchone()
            return dict(row) if row else None

    def get_fee_structure(
        self,
        jurisdiction_id: int,
        fee_type: str = None
    ) -> List[Dict]:
        """Get fee structure for jurisdiction"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM fee_structures WHERE jurisdiction_id = ?"
            params = [jurisdiction_id]
            if fee_type:
                query += " AND fee_type = ?"
                params.append(fee_type)

            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_special_requirements(
        self,
        jurisdiction_id: int,
        requirement_type: str = None
    ) -> List[Dict]:
        """Get special requirements for jurisdiction"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM special_requirements WHERE jurisdiction_id = ?"
            params = [jurisdiction_id]
            if requirement_type:
                query += " AND requirement_type = ?"
                params.append(requirement_type)

            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_hvhz_jurisdictions(self) -> List[Dict]:
        """Get all HVHZ jurisdictions"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM jurisdictions WHERE hvhz = 1 AND active = 1
                ORDER BY county, name
            """).fetchall()
            return [dict(r) for r in rows]

    def search_jurisdictions(self, query: str) -> List[Dict]:
        """Search jurisdictions by name or county"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM jurisdictions
                WHERE active = 1 AND (name LIKE ? OR county LIKE ?)
                ORDER BY county, name
            """, (f"%{query}%", f"%{query}%")).fetchall()
            return [dict(r) for r in rows]

    def compare_jurisdictions(
        self,
        jurisdiction_ids: List[int],
        permit_type: str = "building"
    ) -> Dict:
        """Compare requirements across multiple jurisdictions"""
        comparison = {
            "jurisdictions": [],
            "hvhz_status": [],
            "review_times": [],
            "special_requirements": {}
        }

        for jur_id in jurisdiction_ids:
            jur = self.get_jurisdiction(jurisdiction_id=jur_id)
            if jur:
                comparison["jurisdictions"].append(jur["name"])
                comparison["hvhz_status"].append({
                    "jurisdiction": jur["name"],
                    "hvhz": jur["hvhz"]
                })

                tf = self.get_review_timeframe(jur_id, permit_type)
                if tf:
                    comparison["review_times"].append({
                        "jurisdiction": jur["name"],
                        "standard_days": tf.get("standard_review_days"),
                        "expedited_days": tf.get("expedited_review_days")
                    })

                for req in jur.get("special_requirements", []):
                    req_type = req["requirement_type"]
                    if req_type not in comparison["special_requirements"]:
                        comparison["special_requirements"][req_type] = []
                    comparison["special_requirements"][req_type].append({
                        "jurisdiction": jur["name"],
                        "requirement": req["requirement_name"],
                        "description": req["description"]
                    })

        return comparison

    def get_jurisdiction_summary(self, jurisdiction_id: int) -> str:
        """Generate a human-readable summary for a jurisdiction"""
        jur = self.get_jurisdiction(jurisdiction_id=jurisdiction_id)
        if not jur:
            return "Jurisdiction not found"

        lines = [
            f"=" * 70,
            f"JURISDICTION: {jur['name']}",
            f"=" * 70,
            f"County: {jur['county']}",
            f"HVHZ: {'Yes' if jur['hvhz'] else 'No'}",
            ""
        ]

        # Contacts
        if jur.get('contacts'):
            lines.append("CONTACT INFORMATION:")
            for contact in jur['contacts']:
                lines.append(f"  {contact['department']}")
                if contact.get('address'):
                    lines.append(f"    Address: {contact['address']}")
                if contact.get('phone'):
                    lines.append(f"    Phone: {contact['phone']}")
                if contact.get('website'):
                    lines.append(f"    Website: {contact['website']}")
                if contact.get('hours'):
                    lines.append(f"    Hours: {contact['hours']}")
            lines.append("")

        # Portal
        if jur.get('portal'):
            portal = jur['portal']
            lines.append("ONLINE SUBMISSION:")
            lines.append(f"  Portal: {portal.get('portal_name')}")
            lines.append(f"  URL: {portal.get('url')}")
            lines.append(f"  Electronic Stamps: {'Accepted' if portal.get('electronic_stamps_accepted') else 'Not Accepted'}")
            if portal.get('max_file_size_mb'):
                lines.append(f"  Max File Size: {portal['max_file_size_mb']} MB")
            lines.append("")

        # Special Requirements
        if jur.get('special_requirements'):
            lines.append("SPECIAL REQUIREMENTS:")
            for req in jur['special_requirements']:
                lines.append(f"  [{req['requirement_type'].upper()}] {req['requirement_name']}")
                lines.append(f"    {req['description']}")
            lines.append("")

        # Local Amendments
        if jur.get('local_amendments'):
            lines.append("LOCAL CODE AMENDMENTS:")
            for amend in jur['local_amendments']:
                restrictive = "(More Restrictive)" if amend['more_restrictive'] else "(Less Restrictive)"
                lines.append(f"  {amend['code_section']} {restrictive}")
                lines.append(f"    {amend['amendment_description']}")
            lines.append("")

        return "\n".join(lines)


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("JURISDICTION REQUIREMENTS DATABASE")
    print("=" * 70)

    # Initialize database
    db = JurisdictionDatabase()

    # List all jurisdictions
    print("\nAll South Florida Jurisdictions:")
    print("-" * 70)
    all_jurs = db.get_all_jurisdictions()
    for jur in all_jurs:
        hvhz = "HVHZ" if jur['hvhz'] else ""
        print(f"  [{jur['county']:15}] {jur['name']:40} {hvhz}")

    print(f"\nTotal: {len(all_jurs)} jurisdictions")

    # Show HVHZ jurisdictions
    print("\n" + "-" * 70)
    print("HVHZ Jurisdictions:")
    print("-" * 70)
    hvhz_jurs = db.get_hvhz_jurisdictions()
    for jur in hvhz_jurs:
        print(f"  - {jur['name']}")

    # Show detailed info for Miami-Dade
    print("\n")
    jur = db.get_jurisdiction(name="Miami-Dade County")
    if jur:
        print(db.get_jurisdiction_summary(jur['id']))

    # Compare jurisdictions
    print("-" * 70)
    print("JURISDICTION COMPARISON")
    print("-" * 70)
    miami_dade = db.get_jurisdiction(name="Miami-Dade County")
    broward = db.get_jurisdiction(name="Broward County")
    palm_beach = db.get_jurisdiction(name="Palm Beach County")

    if all([miami_dade, broward, palm_beach]):
        comparison = db.compare_jurisdictions(
            [miami_dade['id'], broward['id'], palm_beach['id']],
            "building"
        )
        print("\nHVHZ Status:")
        for item in comparison['hvhz_status']:
            status = "Yes" if item['hvhz'] else "No"
            print(f"  {item['jurisdiction']:40} HVHZ: {status}")

        print("\nStandard Building Permit Review Times:")
        for item in comparison['review_times']:
            days = item.get('standard_days', 'N/A')
            print(f"  {item['jurisdiction']:40} {days} days")

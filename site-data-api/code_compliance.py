#!/usr/bin/env python3
"""
Code Compliance Checklists for Florida Building Plan Review

Disciplines covered:
- Building (FBC Building)
- Structural (FBC Building Ch. 16-23, ASCE 7-22)
- Mechanical (FBC Mechanical)
- Plumbing (FBC Plumbing)
- Electrical (NEC/FBC Electrical)
- Fire/Life Safety (FBC Fire, NFPA)

Each checklist item includes:
- Code reference
- Requirement description
- Verification method
- Applicability conditions
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


# Database path
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "code_compliance.db")


class Discipline(Enum):
    BUILDING = "building"
    STRUCTURAL = "structural"
    MECHANICAL = "mechanical"
    PLUMBING = "plumbing"
    ELECTRICAL = "electrical"
    FIRE = "fire"


class ItemStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "n/a"
    NEEDS_INFO = "needs_info"


class ProjectType(Enum):
    SINGLE_FAMILY = "single_family"
    MULTI_FAMILY = "multi_family"
    COMMERCIAL = "commercial"
    MIXED_USE = "mixed_use"
    INDUSTRIAL = "industrial"
    INSTITUTIONAL = "institutional"
    ADDITION = "addition"
    TENANT_IMPROVEMENT = "tenant_improvement"


@dataclass
class ChecklistItem:
    """Single checklist item"""
    id: int
    discipline: str
    category: str
    item_code: str
    description: str
    code_reference: str
    verification_method: str
    applies_to: List[str]  # Project types
    hvhz_specific: bool
    flood_zone_specific: bool
    notes: str


class CodeComplianceDatabase:
    """
    Code Compliance Checklist Database

    Manages checklist templates and project-specific checklist instances.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Checklist templates (master list of all items)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checklist_templates (
                    id INTEGER PRIMARY KEY,
                    discipline TEXT NOT NULL,
                    category TEXT NOT NULL,
                    item_code TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL,
                    code_reference TEXT,
                    verification_method TEXT,
                    applies_to TEXT,  -- JSON array of project types
                    hvhz_specific INTEGER DEFAULT 0,
                    flood_zone_specific INTEGER DEFAULT 0,
                    priority INTEGER DEFAULT 2,  -- 1=critical, 2=standard, 3=minor
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Project checklists (instances for specific projects)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_checklists (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    discipline TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    status TEXT DEFAULT 'in_progress',
                    reviewed_by TEXT,
                    UNIQUE(project_id, discipline)
                )
            """)

            # Individual item status for each project
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_checklist_items (
                    id INTEGER PRIMARY KEY,
                    checklist_id INTEGER NOT NULL,
                    template_item_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'not_started',
                    notes TEXT,
                    sheet_reference TEXT,  -- e.g., "A-101", "S-201"
                    verified_by TEXT,
                    verified_at TEXT,
                    FOREIGN KEY (checklist_id) REFERENCES project_checklists(id),
                    FOREIGN KEY (template_item_id) REFERENCES checklist_templates(id),
                    UNIQUE(checklist_id, template_item_id)
                )
            """)

            # Review comments (from building dept)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS review_comments (
                    id INTEGER PRIMARY KEY,
                    checklist_item_id INTEGER NOT NULL,
                    comment_text TEXT NOT NULL,
                    comment_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    reviewer_name TEXT,
                    response_text TEXT,
                    response_date TEXT,
                    resolved INTEGER DEFAULT 0,
                    FOREIGN KEY (checklist_item_id) REFERENCES project_checklist_items(id)
                )
            """)

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_templates_discipline ON checklist_templates(discipline)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_templates_category ON checklist_templates(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_project_items_status ON project_checklist_items(status)")

            conn.commit()

    def populate_templates(self):
        """Populate checklist templates with Florida Building Code requirements"""
        self._populate_building_checklist()
        self._populate_structural_checklist()
        self._populate_mechanical_checklist()
        self._populate_plumbing_checklist()
        self._populate_electrical_checklist()
        self._populate_fire_checklist()

    def _insert_template(self, discipline: str, category: str, item_code: str,
                         description: str, code_ref: str, verification: str,
                         applies_to: List[str] = None, hvhz: bool = False,
                         flood: bool = False, priority: int = 2, notes: str = None):
        """Insert a checklist template item"""
        applies_to = applies_to or ["all"]

        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO checklist_templates
                    (discipline, category, item_code, description, code_reference,
                     verification_method, applies_to, hvhz_specific, flood_zone_specific,
                     priority, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (discipline, category, item_code, description, code_ref,
                      verification, json.dumps(applies_to), 1 if hvhz else 0,
                      1 if flood else 0, priority, notes))
                conn.commit()
            except sqlite3.IntegrityError:
                pass  # Item already exists

    def _populate_building_checklist(self):
        """Building/Architectural code checklist items"""
        d = "building"

        # OCCUPANCY & CONSTRUCTION TYPE
        cat = "Occupancy Classification"
        self._insert_template(d, cat, "BLD-OCC-001",
            "Occupancy group correctly identified",
            "FBC 302", "Review drawings for occupancy designation",
            priority=1)
        self._insert_template(d, cat, "BLD-OCC-002",
            "Mixed occupancy separation requirements met",
            "FBC 508", "Verify fire separation between occupancies",
            applies_to=["commercial", "mixed_use"])
        self._insert_template(d, cat, "BLD-OCC-003",
            "Occupant load calculations provided",
            "FBC 1004", "Verify occupant load on plans",
            priority=1)

        cat = "Construction Type"
        self._insert_template(d, cat, "BLD-CON-001",
            "Construction type correctly identified",
            "FBC 602", "Review construction type designation",
            priority=1)
        self._insert_template(d, cat, "BLD-CON-002",
            "Fire resistance ratings comply with construction type",
            "FBC Table 601", "Verify structural fire ratings")
        self._insert_template(d, cat, "BLD-CON-003",
            "Exterior wall fire resistance per Table 602",
            "FBC Table 602", "Check exterior wall ratings based on fire separation distance")

        # BUILDING HEIGHT & AREA
        cat = "Height and Area"
        self._insert_template(d, cat, "BLD-HA-001",
            "Building height within allowable limits",
            "FBC Table 504.3", "Verify building height vs. table allowance",
            priority=1)
        self._insert_template(d, cat, "BLD-HA-002",
            "Building area within allowable limits",
            "FBC Table 506.2", "Verify building area vs. table allowance",
            priority=1)
        self._insert_template(d, cat, "BLD-HA-003",
            "Area increase calculations correct (if applicable)",
            "FBC 506.2, 506.3", "Verify frontage and sprinkler increases")
        self._insert_template(d, cat, "BLD-HA-004",
            "Number of stories within limit",
            "FBC Table 504.4", "Verify story count")

        # EGRESS
        cat = "Means of Egress"
        self._insert_template(d, cat, "BLD-EGR-001",
            "Number of exits adequate for occupant load",
            "FBC 1006.2", "Verify exit count per Table 1006.2.1",
            priority=1)
        self._insert_template(d, cat, "BLD-EGR-002",
            "Exit access travel distance within limits",
            "FBC Table 1017.2", "Measure travel distances on plans",
            priority=1)
        self._insert_template(d, cat, "BLD-EGR-003",
            "Common path of egress travel within limits",
            "FBC Table 1006.2.1", "Measure common path distances")
        self._insert_template(d, cat, "BLD-EGR-004",
            "Dead-end corridors within limits",
            "FBC 1020.4", "Verify dead-end corridor lengths")
        self._insert_template(d, cat, "BLD-EGR-005",
            "Exit width adequate for occupant load",
            "FBC 1005.1", "Calculate required exit width",
            priority=1)
        self._insert_template(d, cat, "BLD-EGR-006",
            "Exit separation (1/2 diagonal rule)",
            "FBC 1007.1.1", "Verify exit door separation")
        self._insert_template(d, cat, "BLD-EGR-007",
            "Corridor width minimum 44 inches",
            "FBC 1020.2", "Verify corridor widths")
        self._insert_template(d, cat, "BLD-EGR-008",
            "Door swing in direction of egress (50+ occupants)",
            "FBC 1010.1.2.1", "Check door swing directions")
        self._insert_template(d, cat, "BLD-EGR-009",
            "Exit signs properly located",
            "FBC 1013", "Verify exit sign locations")
        self._insert_template(d, cat, "BLD-EGR-010",
            "Emergency lighting provided",
            "FBC 1008", "Verify emergency lighting coverage")

        # STAIRS
        cat = "Stairways"
        self._insert_template(d, cat, "BLD-STR-001",
            "Stair width adequate",
            "FBC 1011.2", "Verify stair width calculations")
        self._insert_template(d, cat, "BLD-STR-002",
            "Riser height 4-7 inches",
            "FBC 1011.5.2", "Verify riser dimensions")
        self._insert_template(d, cat, "BLD-STR-003",
            "Tread depth minimum 11 inches",
            "FBC 1011.5.2", "Verify tread dimensions")
        self._insert_template(d, cat, "BLD-STR-004",
            "Handrails on both sides",
            "FBC 1011.11", "Verify handrail locations")
        self._insert_template(d, cat, "BLD-STR-005",
            "Handrail height 34-38 inches",
            "FBC 1014.2", "Verify handrail heights")
        self._insert_template(d, cat, "BLD-STR-006",
            "Guardrails minimum 42 inches",
            "FBC 1015.3", "Verify guardrail heights")
        self._insert_template(d, cat, "BLD-STR-007",
            "Stair enclosure fire rating (2+ stories)",
            "FBC 1023.2", "Verify stair enclosure ratings")

        # ACCESSIBILITY
        cat = "Accessibility"
        self._insert_template(d, cat, "BLD-ADA-001",
            "Accessible route provided from public way",
            "FBC 1104.1", "Trace accessible route on plans",
            priority=1)
        self._insert_template(d, cat, "BLD-ADA-002",
            "Required accessible parking spaces",
            "FBC 1106.1", "Calculate required accessible spaces",
            priority=1)
        self._insert_template(d, cat, "BLD-ADA-003",
            "Accessible entrance provided",
            "FBC 1105", "Identify accessible entrances")
        self._insert_template(d, cat, "BLD-ADA-004",
            "Accessible toilet rooms",
            "FBC 1109.2", "Verify accessible restroom design")
        self._insert_template(d, cat, "BLD-ADA-005",
            "Door maneuvering clearances",
            "FBC 1010.1.9", "Check door clearances")
        self._insert_template(d, cat, "BLD-ADA-006",
            "Elevator or accessible route to all floors",
            "FBC 1104.4", "Verify vertical accessibility",
            applies_to=["commercial", "multi_family", "mixed_use"])
        self._insert_template(d, cat, "BLD-ADA-007",
            "Type A and Type B dwelling units (if applicable)",
            "FBC 1107", "Verify accessible unit counts",
            applies_to=["multi_family"])

        # ENERGY CODE
        cat = "Energy Code"
        self._insert_template(d, cat, "BLD-ENG-001",
            "Building envelope compliance (R-values)",
            "FBC Energy Ch. 4", "Verify insulation R-values",
            priority=1)
        self._insert_template(d, cat, "BLD-ENG-002",
            "Window U-factor and SHGC compliance",
            "FBC Energy Table C402.4", "Verify fenestration values")
        self._insert_template(d, cat, "BLD-ENG-003",
            "Air barrier continuity",
            "FBC Energy C402.5", "Verify air barrier details")
        self._insert_template(d, cat, "BLD-ENG-004",
            "Lighting power density (LPD) compliance",
            "FBC Energy C405", "Calculate LPD",
            applies_to=["commercial", "mixed_use"])
        self._insert_template(d, cat, "BLD-ENG-005",
            "HVAC efficiency requirements",
            "FBC Energy C403", "Verify equipment efficiency")
        self._insert_template(d, cat, "BLD-ENG-006",
            "Energy compliance form (ResCheck/ComCheck)",
            "FBC Energy", "Verify compliance report included",
            priority=1)

        # INTERIOR FINISHES
        cat = "Interior Finishes"
        self._insert_template(d, cat, "BLD-INT-001",
            "Interior wall finish flame spread ratings",
            "FBC 803", "Verify finish classifications")
        self._insert_template(d, cat, "BLD-INT-002",
            "Ceiling finish flame spread ratings",
            "FBC 803", "Verify ceiling finish ratings")
        self._insert_template(d, cat, "BLD-INT-003",
            "Floor finish in exit enclosures",
            "FBC 804", "Verify floor finish in exits")

    def _populate_structural_checklist(self):
        """Structural code checklist items"""
        d = "structural"

        # LOAD CRITERIA
        cat = "Design Loads"
        self._insert_template(d, cat, "STR-LD-001",
            "Dead loads correctly identified",
            "ASCE 7-22 Ch. 3", "Review load criteria on drawings",
            priority=1)
        self._insert_template(d, cat, "STR-LD-002",
            "Live loads per Table 4.3-1",
            "ASCE 7-22 Table 4.3-1", "Verify live load values",
            priority=1)
        self._insert_template(d, cat, "STR-LD-003",
            "Roof live loads",
            "ASCE 7-22 Table 4.3-1", "Verify roof live load")

        # WIND DESIGN
        cat = "Wind Design"
        self._insert_template(d, cat, "STR-WND-001",
            "Basic wind speed correctly identified",
            "ASCE 7-22 Fig. 26.5-1", "Verify wind speed for location",
            priority=1)
        self._insert_template(d, cat, "STR-WND-002",
            "Risk category correctly identified",
            "ASCE 7-22 Table 1.5-1", "Verify risk category",
            priority=1)
        self._insert_template(d, cat, "STR-WND-003",
            "Exposure category correct",
            "ASCE 7-22 26.7", "Verify exposure category",
            priority=1)
        self._insert_template(d, cat, "STR-WND-004",
            "MWFRS design provided",
            "ASCE 7-22 Ch. 27/28", "Review main wind force resisting system")
        self._insert_template(d, cat, "STR-WND-005",
            "C&C design provided",
            "ASCE 7-22 Ch. 30", "Review components and cladding design")
        self._insert_template(d, cat, "STR-WND-006",
            "Wind-borne debris region requirements",
            "FBC 1609.1.2", "Verify impact protection",
            hvhz=True, priority=1)

        # HVHZ SPECIFIC
        cat = "HVHZ Requirements"
        self._insert_template(d, cat, "STR-HVHZ-001",
            "Miami-Dade NOA for windows/doors",
            "FBC 1626", "Verify NOA numbers on schedule",
            hvhz=True, priority=1)
        self._insert_template(d, cat, "STR-HVHZ-002",
            "Roof attachment per TAS 102/125",
            "FBC 1523", "Verify roof-to-wall connections",
            hvhz=True, priority=1)
        self._insert_template(d, cat, "STR-HVHZ-003",
            "Secondary water barrier",
            "FBC 1523.6", "Verify secondary water resistance",
            hvhz=True)
        self._insert_template(d, cat, "STR-HVHZ-004",
            "Opening protection (shutters or impact)",
            "FBC 1626.2", "Verify opening protection details",
            hvhz=True, priority=1)
        self._insert_template(d, cat, "STR-HVHZ-005",
            "Roof deck attachment per Table 1523.6.5",
            "FBC Table 1523.6.5", "Verify roof deck fastening",
            hvhz=True)

        # FLOOD DESIGN
        cat = "Flood Design"
        self._insert_template(d, cat, "STR-FLD-001",
            "Design flood elevation (DFE) identified",
            "ASCE 24, FBC 1612", "Verify DFE on drawings",
            flood=True, priority=1)
        self._insert_template(d, cat, "STR-FLD-002",
            "Lowest floor elevation at or above DFE",
            "FBC 1612.4", "Verify floor elevations",
            flood=True, priority=1)
        self._insert_template(d, cat, "STR-FLD-003",
            "Flood openings in foundation walls",
            "ASCE 24-14", "Verify flood vent sizing",
            flood=True)
        self._insert_template(d, cat, "STR-FLD-004",
            "Breakaway walls below DFE (V-zone)",
            "ASCE 24-14 Ch. 4", "Verify breakaway wall design",
            flood=True)
        self._insert_template(d, cat, "STR-FLD-005",
            "Foundation anchored for flotation/collapse",
            "FBC 1612.5", "Verify foundation anchoring",
            flood=True)
        self._insert_template(d, cat, "STR-FLD-006",
            "Utilities elevated above DFE",
            "FBC 1612.4.1", "Verify utility elevations",
            flood=True)

        # FOUNDATIONS
        cat = "Foundations"
        self._insert_template(d, cat, "STR-FND-001",
            "Geotechnical report provided/referenced",
            "FBC 1803", "Verify geotech report",
            priority=1)
        self._insert_template(d, cat, "STR-FND-002",
            "Soil bearing capacity identified",
            "FBC 1806", "Verify bearing capacity used")
        self._insert_template(d, cat, "STR-FND-003",
            "Foundation depth adequate for frost/erosion",
            "FBC 1809", "Verify foundation depth")
        self._insert_template(d, cat, "STR-FND-004",
            "Continuous footings properly reinforced",
            "FBC 1809", "Verify footing reinforcement")

        # WOOD FRAMING
        cat = "Wood Framing"
        self._insert_template(d, cat, "STR-WD-001",
            "Lumber grades specified",
            "FBC 2303", "Verify lumber grades on plans",
            applies_to=["single_family", "multi_family"])
        self._insert_template(d, cat, "STR-WD-002",
            "Wood preservative treatment where required",
            "FBC 2304.12", "Verify treated wood locations",
            applies_to=["single_family", "multi_family"])
        self._insert_template(d, cat, "STR-WD-003",
            "Connection details adequate",
            "FBC 2304, 2308", "Review connection schedule")
        self._insert_template(d, cat, "STR-WD-004",
            "Braced wall panels per FBC 2308.6",
            "FBC 2308.6", "Verify bracing layout",
            applies_to=["single_family"])

        # CONCRETE/MASONRY
        cat = "Concrete and Masonry"
        self._insert_template(d, cat, "STR-CM-001",
            "Concrete strength specified",
            "FBC 1905", "Verify f'c on drawings")
        self._insert_template(d, cat, "STR-CM-002",
            "Reinforcement clearly detailed",
            "FBC 1907", "Review reinforcement details")
        self._insert_template(d, cat, "STR-CM-003",
            "Masonry strength and type specified",
            "FBC 2103", "Verify masonry specifications")
        self._insert_template(d, cat, "STR-CM-004",
            "Masonry reinforcement detailed",
            "FBC 2108", "Review masonry reinforcement")

    def _populate_mechanical_checklist(self):
        """Mechanical code checklist items"""
        d = "mechanical"

        # LOAD CALCULATIONS
        cat = "Load Calculations"
        self._insert_template(d, cat, "MCH-LD-001",
            "Heating/cooling load calculations provided",
            "FBC Mechanical 301", "Review Manual J or equivalent",
            priority=1)
        self._insert_template(d, cat, "MCH-LD-002",
            "Equipment sizing matches load calc",
            "FBC Mechanical 301", "Verify equipment capacity vs. load")
        self._insert_template(d, cat, "MCH-LD-003",
            "Duct sizing calculations (Manual D)",
            "FBC Mechanical 601", "Review duct sizing",
            applies_to=["single_family", "multi_family"])

        # EQUIPMENT
        cat = "Equipment"
        self._insert_template(d, cat, "MCH-EQ-001",
            "Equipment efficiency meets minimum",
            "FBC Energy C403", "Verify SEER/EER/HSPF ratings",
            priority=1)
        self._insert_template(d, cat, "MCH-EQ-002",
            "Equipment location accessible for service",
            "FBC Mechanical 306", "Verify clearances")
        self._insert_template(d, cat, "MCH-EQ-003",
            "Condensate drain properly routed",
            "FBC Mechanical 307", "Verify drain routing")
        self._insert_template(d, cat, "MCH-EQ-004",
            "Secondary drain pan or shutoff",
            "FBC Mechanical 307.2.3", "Verify secondary drainage",
            applies_to=["single_family", "multi_family"])
        self._insert_template(d, cat, "MCH-EQ-005",
            "Equipment electrical disconnect",
            "FBC Mechanical 302", "Verify disconnect location")

        # VENTILATION
        cat = "Ventilation"
        self._insert_template(d, cat, "MCH-VNT-001",
            "Outdoor air ventilation rates per ASHRAE 62",
            "FBC Mechanical 401", "Verify ventilation calculations",
            priority=1)
        self._insert_template(d, cat, "MCH-VNT-002",
            "Bathroom exhaust (50 CFM intermittent)",
            "FBC Mechanical 403.3", "Verify bathroom exhaust")
        self._insert_template(d, cat, "MCH-VNT-003",
            "Kitchen exhaust (100 CFM intermittent)",
            "FBC Mechanical 403.3", "Verify kitchen exhaust")
        self._insert_template(d, cat, "MCH-VNT-004",
            "Exhaust termination clearances",
            "FBC Mechanical 501", "Verify exhaust locations")
        self._insert_template(d, cat, "MCH-VNT-005",
            "Garage ventilation (if applicable)",
            "FBC Mechanical 404", "Verify garage ventilation",
            applies_to=["commercial", "multi_family"])

        # DUCTWORK
        cat = "Ductwork"
        self._insert_template(d, cat, "MCH-DCT-001",
            "Duct material and construction specified",
            "FBC Mechanical 603", "Verify duct specifications")
        self._insert_template(d, cat, "MCH-DCT-002",
            "Duct insulation R-value adequate",
            "FBC Energy C403", "Verify duct insulation")
        self._insert_template(d, cat, "MCH-DCT-003",
            "Duct sealing specified",
            "FBC Mechanical 603", "Verify duct sealing requirements")
        self._insert_template(d, cat, "MCH-DCT-004",
            "Fire/smoke dampers at rated assemblies",
            "FBC Mechanical 607", "Verify damper locations",
            applies_to=["commercial", "multi_family", "mixed_use"])

        # FUEL GAS
        cat = "Fuel Gas"
        self._insert_template(d, cat, "MCH-GAS-001",
            "Gas pipe sizing calculations",
            "FBC Fuel Gas 402", "Verify pipe sizing")
        self._insert_template(d, cat, "MCH-GAS-002",
            "Appliance venting properly sized",
            "FBC Fuel Gas Ch. 5", "Verify vent sizing")
        self._insert_template(d, cat, "MCH-GAS-003",
            "Gas appliance clearances to combustibles",
            "FBC Fuel Gas 303", "Verify clearances")
        self._insert_template(d, cat, "MCH-GAS-004",
            "Combustion air provisions",
            "FBC Fuel Gas 304", "Verify combustion air")

    def _populate_plumbing_checklist(self):
        """Plumbing code checklist items"""
        d = "plumbing"

        # FIXTURE REQUIREMENTS
        cat = "Fixtures"
        self._insert_template(d, cat, "PLB-FX-001",
            "Fixture count per Table 403.1",
            "FBC Plumbing Table 403.1", "Verify fixture counts",
            priority=1)
        self._insert_template(d, cat, "PLB-FX-002",
            "Accessible fixtures provided",
            "FBC Plumbing 403.4", "Verify accessible fixture counts")
        self._insert_template(d, cat, "PLB-FX-003",
            "Fixture clearances adequate",
            "FBC Plumbing 405", "Verify fixture clearances")
        self._insert_template(d, cat, "PLB-FX-004",
            "Drinking fountain requirement",
            "FBC Plumbing 410", "Verify drinking fountain",
            applies_to=["commercial", "institutional"])

        # WATER SUPPLY
        cat = "Water Supply"
        self._insert_template(d, cat, "PLB-WS-001",
            "Water supply sizing (fixture units)",
            "FBC Plumbing Table 604.3", "Verify pipe sizing",
            priority=1)
        self._insert_template(d, cat, "PLB-WS-002",
            "Water heater sizing adequate",
            "FBC Plumbing 504", "Verify water heater capacity")
        self._insert_template(d, cat, "PLB-WS-003",
            "Water heater T&P relief valve",
            "FBC Plumbing 504.6", "Verify T&P relief")
        self._insert_template(d, cat, "PLB-WS-004",
            "Backflow prevention devices",
            "FBC Plumbing 608", "Verify backflow protection",
            priority=1)
        self._insert_template(d, cat, "PLB-WS-005",
            "Hot water maximum temperature (120°F max)",
            "FBC Plumbing 607.1", "Verify temperature limiting")

        # DRAINAGE
        cat = "Drainage"
        self._insert_template(d, cat, "PLB-DR-001",
            "Drainage pipe sizing (DFU)",
            "FBC Plumbing Table 710.1", "Verify drain sizing",
            priority=1)
        self._insert_template(d, cat, "PLB-DR-002",
            "Cleanouts properly located",
            "FBC Plumbing 708", "Verify cleanout locations")
        self._insert_template(d, cat, "PLB-DR-003",
            "Trap sizes adequate",
            "FBC Plumbing 1002", "Verify trap sizes")
        self._insert_template(d, cat, "PLB-DR-004",
            "Grease interceptor (if required)",
            "FBC Plumbing 1003", "Verify grease trap",
            applies_to=["commercial"])

        # VENTING
        cat = "Venting"
        self._insert_template(d, cat, "PLB-VNT-001",
            "Vent pipe sizing",
            "FBC Plumbing Table 916.1", "Verify vent sizing",
            priority=1)
        self._insert_template(d, cat, "PLB-VNT-002",
            "Vent termination height (6\" above roof)",
            "FBC Plumbing 903.1", "Verify vent termination")
        self._insert_template(d, cat, "PLB-VNT-003",
            "Vent clearance from openings (10 ft horiz)",
            "FBC Plumbing 903.5", "Verify vent clearances")
        self._insert_template(d, cat, "PLB-VNT-004",
            "Each fixture properly vented",
            "FBC Plumbing 904", "Verify fixture venting")

        # WATER HEATER
        cat = "Water Heater"
        self._insert_template(d, cat, "PLB-WH-001",
            "Water heater location/clearances",
            "FBC Plumbing 504.1", "Verify location clearances")
        self._insert_template(d, cat, "PLB-WH-002",
            "Drain pan (if over living space)",
            "FBC Plumbing 504.7", "Verify drain pan")
        self._insert_template(d, cat, "PLB-WH-003",
            "Expansion tank (closed system)",
            "FBC Plumbing 607.3", "Verify expansion tank")
        self._insert_template(d, cat, "PLB-WH-004",
            "Seismic strapping (if required)",
            "FBC Plumbing 504.8", "Verify strapping")

    def _populate_electrical_checklist(self):
        """Electrical code checklist items"""
        d = "electrical"

        # SERVICE & LOAD
        cat = "Service and Load"
        self._insert_template(d, cat, "ELC-SVC-001",
            "Load calculations provided",
            "NEC Article 220", "Review load calculation",
            priority=1)
        self._insert_template(d, cat, "ELC-SVC-002",
            "Service size adequate for calculated load",
            "NEC Article 230", "Verify service sizing",
            priority=1)
        self._insert_template(d, cat, "ELC-SVC-003",
            "Main disconnect location (6 throw rule)",
            "NEC 230.71", "Verify disconnect location")
        self._insert_template(d, cat, "ELC-SVC-004",
            "Service entrance conductor sizing",
            "NEC 230.42", "Verify conductor sizing")
        self._insert_template(d, cat, "ELC-SVC-005",
            "Grounding electrode system",
            "NEC Article 250", "Verify grounding details",
            priority=1)

        # BRANCH CIRCUITS
        cat = "Branch Circuits"
        self._insert_template(d, cat, "ELC-BC-001",
            "Kitchen small appliance circuits (2 req'd)",
            "NEC 210.52(B)", "Verify kitchen circuits",
            applies_to=["single_family", "multi_family"])
        self._insert_template(d, cat, "ELC-BC-002",
            "Laundry circuit provided",
            "NEC 210.52(F)", "Verify laundry circuit",
            applies_to=["single_family", "multi_family"])
        self._insert_template(d, cat, "ELC-BC-003",
            "Bathroom circuit(s) provided",
            "NEC 210.52(D)", "Verify bathroom circuits")
        self._insert_template(d, cat, "ELC-BC-004",
            "Dedicated circuit for HVAC equipment",
            "NEC 422", "Verify HVAC circuits")
        self._insert_template(d, cat, "ELC-BC-005",
            "Garage circuit provided",
            "NEC 210.52(G)", "Verify garage circuit",
            applies_to=["single_family"])

        # RECEPTACLES
        cat = "Receptacles"
        self._insert_template(d, cat, "ELC-RCP-001",
            "Receptacle spacing (12 ft / 6 ft from door)",
            "NEC 210.52", "Verify receptacle spacing",
            applies_to=["single_family", "multi_family"])
        self._insert_template(d, cat, "ELC-RCP-002",
            "Outdoor receptacle(s) provided",
            "NEC 210.52(E)", "Verify outdoor receptacles")
        self._insert_template(d, cat, "ELC-RCP-003",
            "Kitchen countertop receptacle spacing (4 ft)",
            "NEC 210.52(C)", "Verify kitchen receptacles",
            applies_to=["single_family", "multi_family"])

        # GFCI/AFCI
        cat = "GFCI and AFCI"
        self._insert_template(d, cat, "ELC-GF-001",
            "GFCI protection for bathrooms",
            "NEC 210.8(A)(1)", "Verify bathroom GFCI",
            priority=1)
        self._insert_template(d, cat, "ELC-GF-002",
            "GFCI protection for kitchen countertops",
            "NEC 210.8(A)(6)", "Verify kitchen GFCI",
            priority=1)
        self._insert_template(d, cat, "ELC-GF-003",
            "GFCI protection for outdoor receptacles",
            "NEC 210.8(A)(3)", "Verify outdoor GFCI")
        self._insert_template(d, cat, "ELC-GF-004",
            "GFCI protection for garage receptacles",
            "NEC 210.8(A)(2)", "Verify garage GFCI")
        self._insert_template(d, cat, "ELC-GF-005",
            "AFCI protection for bedrooms/living areas",
            "NEC 210.12", "Verify AFCI coverage",
            priority=1, applies_to=["single_family", "multi_family"])

        # LIGHTING
        cat = "Lighting"
        self._insert_template(d, cat, "ELC-LT-001",
            "Lighting outlet in each habitable room",
            "NEC 210.70", "Verify lighting outlets")
        self._insert_template(d, cat, "ELC-LT-002",
            "Exterior lighting at entries",
            "NEC 210.70(A)(2)", "Verify exterior lighting")
        self._insert_template(d, cat, "ELC-LT-003",
            "Stairway lighting with 3-way switches",
            "NEC 210.70(A)(2)", "Verify stair lighting")
        self._insert_template(d, cat, "ELC-LT-004",
            "Garage lighting outlet",
            "NEC 210.70(A)(2)", "Verify garage lighting")

        # PANEL/WIRING
        cat = "Panel and Wiring"
        self._insert_template(d, cat, "ELC-PN-001",
            "Panel clearance (36\" front, 30\" wide)",
            "NEC 110.26", "Verify panel clearances",
            priority=1)
        self._insert_template(d, cat, "ELC-PN-002",
            "Panel directory provided",
            "NEC 408.4", "Verify panel schedule")
        self._insert_template(d, cat, "ELC-PN-003",
            "Wire sizing adequate for circuit loads",
            "NEC Table 310.16", "Verify wire sizing")
        self._insert_template(d, cat, "ELC-PN-004",
            "Smoke detector circuit(s)",
            "NEC 760", "Verify smoke detector wiring")

        # EV CHARGING
        cat = "EV Charging"
        self._insert_template(d, cat, "ELC-EV-001",
            "EV-ready parking (if required)",
            "FBC Energy C405.13", "Verify EV infrastructure",
            applies_to=["multi_family", "commercial"])

    def _populate_fire_checklist(self):
        """Fire and Life Safety checklist items"""
        d = "fire"

        # FIRE PROTECTION SYSTEMS
        cat = "Sprinkler Systems"
        self._insert_template(d, cat, "FIR-SPR-001",
            "Automatic sprinkler system required?",
            "FBC 903", "Determine sprinkler requirement",
            priority=1)
        self._insert_template(d, cat, "FIR-SPR-002",
            "NFPA 13/13R/13D system specified",
            "FBC 903.3", "Verify system type",
            applies_to=["multi_family", "commercial"])
        self._insert_template(d, cat, "FIR-SPR-003",
            "Fire department connection provided",
            "FBC 903.3.7", "Verify FDC location",
            applies_to=["commercial", "multi_family"])
        self._insert_template(d, cat, "FIR-SPR-004",
            "Sprinkler coverage in all areas",
            "NFPA 13", "Verify coverage",
            applies_to=["commercial", "multi_family"])

        # FIRE ALARM
        cat = "Fire Alarm"
        self._insert_template(d, cat, "FIR-ALM-001",
            "Fire alarm system required?",
            "FBC 907", "Determine alarm requirement",
            priority=1)
        self._insert_template(d, cat, "FIR-ALM-002",
            "Manual pull station locations",
            "FBC 907.4", "Verify pull station locations",
            applies_to=["commercial", "multi_family"])
        self._insert_template(d, cat, "FIR-ALM-003",
            "Smoke detector locations per NFPA 72",
            "FBC 907.2", "Verify detector layout",
            priority=1)
        self._insert_template(d, cat, "FIR-ALM-004",
            "Audible/visual notification coverage",
            "FBC 907.5", "Verify notification devices",
            applies_to=["commercial", "multi_family"])
        self._insert_template(d, cat, "FIR-ALM-005",
            "Fire alarm panel location",
            "FBC 907", "Verify FACP location",
            applies_to=["commercial", "multi_family"])

        # RESIDENTIAL SMOKE/CO
        cat = "Smoke and CO Alarms"
        self._insert_template(d, cat, "FIR-SM-001",
            "Smoke alarms in each bedroom",
            "FBC 907.2.11", "Verify bedroom smoke alarms",
            priority=1, applies_to=["single_family", "multi_family"])
        self._insert_template(d, cat, "FIR-SM-002",
            "Smoke alarm outside sleeping areas",
            "FBC 907.2.11", "Verify hall smoke alarms",
            applies_to=["single_family", "multi_family"])
        self._insert_template(d, cat, "FIR-SM-003",
            "Smoke alarm on each level",
            "FBC 907.2.11", "Verify floor coverage",
            applies_to=["single_family", "multi_family"])
        self._insert_template(d, cat, "FIR-SM-004",
            "Interconnection of smoke alarms",
            "FBC 907.2.11", "Verify interconnection",
            applies_to=["single_family", "multi_family"])
        self._insert_template(d, cat, "FIR-SM-005",
            "Carbon monoxide alarms (if fuel-burning)",
            "FBC 908", "Verify CO alarms",
            applies_to=["single_family", "multi_family"])

        # FIRE SEPARATION
        cat = "Fire Separation"
        self._insert_template(d, cat, "FIR-SEP-001",
            "Occupancy separation per Table 508.4",
            "FBC Table 508.4", "Verify separation ratings",
            applies_to=["commercial", "mixed_use"])
        self._insert_template(d, cat, "FIR-SEP-002",
            "Dwelling unit separation (1-hr or per Table 508)",
            "FBC 420.2", "Verify unit separation",
            applies_to=["multi_family"])
        self._insert_template(d, cat, "FIR-SEP-003",
            "Corridor fire rating (if required)",
            "FBC Table 1020.1", "Verify corridor rating",
            applies_to=["commercial", "multi_family"])
        self._insert_template(d, cat, "FIR-SEP-004",
            "Shaft enclosure rating",
            "FBC 713", "Verify shaft ratings",
            applies_to=["commercial", "multi_family"])
        self._insert_template(d, cat, "FIR-SEP-005",
            "Garage separation from dwelling",
            "FBC 406.3", "Verify garage separation",
            applies_to=["single_family", "multi_family"])

        # FIRE EXTINGUISHERS
        cat = "Fire Extinguishers"
        self._insert_template(d, cat, "FIR-EXT-001",
            "Portable fire extinguisher locations",
            "FBC 906", "Verify extinguisher coverage",
            applies_to=["commercial", "multi_family", "mixed_use"])
        self._insert_template(d, cat, "FIR-EXT-002",
            "Travel distance to extinguisher (75 ft max)",
            "FBC 906.1", "Verify travel distances",
            applies_to=["commercial"])

        # EGRESS
        cat = "Fire/Life Safety Egress"
        self._insert_template(d, cat, "FIR-EGR-001",
            "Exit discharge to public way",
            "FBC 1028", "Verify exit discharge",
            priority=1)
        self._insert_template(d, cat, "FIR-EGR-002",
            "Emergency escape windows (sleeping rooms)",
            "FBC 1030", "Verify EERO dimensions",
            applies_to=["single_family", "multi_family"])
        self._insert_template(d, cat, "FIR-EGR-003",
            "Fire-rated exit passageways",
            "FBC 1024", "Verify exit passageway ratings",
            applies_to=["commercial", "multi_family"])

    # =========================================================================
    # PROJECT CHECKLIST OPERATIONS
    # =========================================================================

    def create_project_checklist(
        self,
        project_id: int,
        discipline: str,
        project_type: str = "all",
        hvhz: bool = False,
        flood_zone: bool = False
    ) -> int:
        """
        Create a checklist instance for a project

        Args:
            project_id: Project ID from project database
            discipline: Discipline (building, structural, mechanical, etc.)
            project_type: Type of project for filtering items
            hvhz: Is project in High-Velocity Hurricane Zone?
            flood_zone: Is project in flood zone?

        Returns:
            Checklist ID
        """
        with sqlite3.connect(self.db_path) as conn:
            # Create checklist record
            cursor = conn.execute("""
                INSERT INTO project_checklists (project_id, discipline)
                VALUES (?, ?)
                ON CONFLICT(project_id, discipline) DO UPDATE SET
                    status = 'in_progress',
                    completed_at = NULL
            """, (project_id, discipline))

            checklist_id = cursor.lastrowid

            # Get applicable template items
            query = """
                SELECT id FROM checklist_templates
                WHERE discipline = ?
                AND (applies_to LIKE '%"all"%' OR applies_to LIKE ?)
            """
            params = [discipline, f'%"{project_type}"%']

            # If not in HVHZ, exclude HVHZ-specific items
            if not hvhz:
                query += " AND hvhz_specific = 0"

            # If not in flood zone, exclude flood-specific items
            if not flood_zone:
                query += " AND flood_zone_specific = 0"

            templates = conn.execute(query, params).fetchall()

            # Create checklist items
            for (template_id,) in templates:
                conn.execute("""
                    INSERT OR IGNORE INTO project_checklist_items
                    (checklist_id, template_item_id, status)
                    VALUES (?, ?, 'not_started')
                """, (checklist_id, template_id))

            conn.commit()
            return checklist_id

    def get_project_checklist(
        self,
        project_id: int,
        discipline: str
    ) -> Dict[str, Any]:
        """Get checklist with all items for a project/discipline"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get checklist
            checklist = conn.execute("""
                SELECT * FROM project_checklists
                WHERE project_id = ? AND discipline = ?
            """, (project_id, discipline)).fetchone()

            if not checklist:
                return None

            checklist = dict(checklist)

            # Get items with template details
            items = conn.execute("""
                SELECT
                    pci.id,
                    pci.status,
                    pci.notes,
                    pci.sheet_reference,
                    pci.verified_by,
                    pci.verified_at,
                    ct.category,
                    ct.item_code,
                    ct.description,
                    ct.code_reference,
                    ct.verification_method,
                    ct.priority,
                    ct.hvhz_specific,
                    ct.flood_zone_specific
                FROM project_checklist_items pci
                JOIN checklist_templates ct ON pci.template_item_id = ct.id
                WHERE pci.checklist_id = ?
                ORDER BY ct.category, ct.priority, ct.item_code
            """, (checklist['id'],)).fetchall()

            # Group by category
            categories = {}
            for item in items:
                item = dict(item)
                cat = item['category']
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)

            checklist['categories'] = categories
            checklist['total_items'] = len(items)

            # Calculate stats
            stats = {'not_started': 0, 'in_progress': 0, 'compliant': 0,
                     'non_compliant': 0, 'n/a': 0, 'needs_info': 0}
            for item in items:
                status = item['status']
                stats[status] = stats.get(status, 0) + 1

            checklist['stats'] = stats
            checklist['completion_pct'] = round(
                (stats['compliant'] + stats['n/a']) / len(items) * 100
            ) if items else 0

            return checklist

    def update_item_status(
        self,
        item_id: int,
        status: str,
        notes: str = None,
        sheet_reference: str = None,
        verified_by: str = None
    ) -> bool:
        """Update status of a checklist item"""
        with sqlite3.connect(self.db_path) as conn:
            updates = ["status = ?"]
            params = [status]

            if notes is not None:
                updates.append("notes = ?")
                params.append(notes)

            if sheet_reference is not None:
                updates.append("sheet_reference = ?")
                params.append(sheet_reference)

            if verified_by is not None:
                updates.append("verified_by = ?")
                params.append(verified_by)
                updates.append("verified_at = ?")
                params.append(datetime.now().isoformat())

            params.append(item_id)

            conn.execute(f"""
                UPDATE project_checklist_items
                SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            conn.commit()
            return True

    def add_review_comment(
        self,
        item_id: int,
        comment: str,
        reviewer_name: str = None
    ) -> int:
        """Add a review comment from building department"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO review_comments
                (checklist_item_id, comment_text, reviewer_name)
                VALUES (?, ?, ?)
            """, (item_id, comment, reviewer_name))

            # Update item status
            conn.execute("""
                UPDATE project_checklist_items
                SET status = 'non_compliant'
                WHERE id = ?
            """, (item_id,))

            conn.commit()
            return cursor.lastrowid

    def respond_to_comment(
        self,
        comment_id: int,
        response: str,
        resolved: bool = False
    ) -> bool:
        """Add response to a review comment"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE review_comments
                SET response_text = ?,
                    response_date = ?,
                    resolved = ?
                WHERE id = ?
            """, (response, datetime.now().isoformat(), 1 if resolved else 0, comment_id))
            conn.commit()
            return True

    def get_checklist_summary(self, project_id: int) -> Dict[str, Any]:
        """Get summary of all checklists for a project"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            checklists = conn.execute("""
                SELECT discipline, status, created_at, completed_at
                FROM project_checklists
                WHERE project_id = ?
            """, (project_id,)).fetchall()

            summary = {
                "project_id": project_id,
                "disciplines": {},
                "overall_status": "not_started",
                "total_items": 0,
                "completed_items": 0
            }

            for cl in checklists:
                cl = dict(cl)
                discipline = cl['discipline']

                # Get stats for this discipline
                stats = conn.execute("""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN pci.status IN ('compliant', 'n/a') THEN 1 ELSE 0 END) as complete,
                        SUM(CASE WHEN pci.status = 'non_compliant' THEN 1 ELSE 0 END) as issues
                    FROM project_checklist_items pci
                    JOIN project_checklists pc ON pci.checklist_id = pc.id
                    WHERE pc.project_id = ? AND pc.discipline = ?
                """, (project_id, discipline)).fetchone()

                summary["disciplines"][discipline] = {
                    "status": cl['status'],
                    "total": stats['total'],
                    "complete": stats['complete'],
                    "issues": stats['issues'],
                    "completion_pct": round(stats['complete'] / stats['total'] * 100) if stats['total'] else 0
                }

                summary["total_items"] += stats['total']
                summary["completed_items"] += stats['complete']

            if summary["total_items"] > 0:
                summary["overall_completion_pct"] = round(
                    summary["completed_items"] / summary["total_items"] * 100
                )

                if summary["overall_completion_pct"] == 100:
                    summary["overall_status"] = "complete"
                elif summary["overall_completion_pct"] > 0:
                    summary["overall_status"] = "in_progress"

            return summary

    def generate_checklist_report(
        self,
        project_id: int,
        discipline: str,
        include_compliant: bool = False
    ) -> str:
        """Generate a text report of checklist status"""
        checklist = self.get_project_checklist(project_id, discipline)

        if not checklist:
            return f"No {discipline} checklist found for project {project_id}"

        lines = [
            "=" * 70,
            f"CODE COMPLIANCE CHECKLIST - {discipline.upper()}",
            "=" * 70,
            f"Project ID: {project_id}",
            f"Status: {checklist['status']}",
            f"Completion: {checklist['completion_pct']}%",
            f"Total Items: {checklist['total_items']}",
            "",
            "STATISTICS:",
            f"  Compliant: {checklist['stats']['compliant']}",
            f"  Non-Compliant: {checklist['stats']['non_compliant']}",
            f"  In Progress: {checklist['stats']['in_progress']}",
            f"  Not Started: {checklist['stats']['not_started']}",
            f"  Not Applicable: {checklist['stats']['n/a']}",
            "",
        ]

        for category, items in checklist['categories'].items():
            lines.append("-" * 70)
            lines.append(f"CATEGORY: {category}")
            lines.append("-" * 70)

            for item in items:
                if not include_compliant and item['status'] == 'compliant':
                    continue

                status_icon = {
                    'compliant': '✓',
                    'non_compliant': '✗',
                    'in_progress': '○',
                    'not_started': '□',
                    'n/a': '-',
                    'needs_info': '?'
                }.get(item['status'], '?')

                lines.append(f"\n  [{status_icon}] {item['item_code']}: {item['description']}")
                lines.append(f"      Code: {item['code_reference']}")
                lines.append(f"      Verify: {item['verification_method']}")

                if item['sheet_reference']:
                    lines.append(f"      Sheet: {item['sheet_reference']}")

                if item['notes']:
                    lines.append(f"      Notes: {item['notes']}")

        lines.extend(["", "=" * 70])

        return "\n".join(lines)

    def get_all_templates(self, discipline: str = None) -> List[Dict]:
        """Get all template items, optionally filtered by discipline"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if discipline:
                results = conn.execute("""
                    SELECT * FROM checklist_templates
                    WHERE discipline = ?
                    ORDER BY category, priority, item_code
                """, (discipline,)).fetchall()
            else:
                results = conn.execute("""
                    SELECT * FROM checklist_templates
                    ORDER BY discipline, category, priority, item_code
                """).fetchall()

            return [dict(r) for r in results]


# Convenience functions
def create_compliance_database() -> CodeComplianceDatabase:
    """Create and populate the compliance database"""
    db = CodeComplianceDatabase()
    db.populate_templates()
    return db


def get_discipline_checklist(
    project_id: int,
    discipline: str,
    project_type: str = "all",
    hvhz: bool = False,
    flood_zone: bool = False
) -> Dict[str, Any]:
    """Quick function to get a checklist for a project"""
    db = CodeComplianceDatabase()

    # Ensure templates exist
    templates = db.get_all_templates(discipline)
    if not templates:
        db.populate_templates()

    # Create checklist if doesn't exist
    db.create_project_checklist(project_id, discipline, project_type, hvhz, flood_zone)

    return db.get_project_checklist(project_id, discipline)


if __name__ == "__main__":
    print("=" * 70)
    print("CODE COMPLIANCE CHECKLIST SYSTEM")
    print("=" * 70)

    # Initialize and populate
    db = CodeComplianceDatabase()
    db.populate_templates()

    # Show template counts
    print("\nTemplate Items by Discipline:")
    for discipline in ["building", "structural", "mechanical", "plumbing", "electrical", "fire"]:
        templates = db.get_all_templates(discipline)
        print(f"  {discipline.title()}: {len(templates)} items")

    # Demo: Create a checklist for a sample project
    print("\n" + "-" * 70)
    print("Demo: Creating checklist for single-family project in HVHZ")
    print("-" * 70)

    # Create checklists for project ID 1
    project_id = 1

    for discipline in ["building", "structural", "electrical"]:
        checklist_id = db.create_project_checklist(
            project_id=project_id,
            discipline=discipline,
            project_type="single_family",
            hvhz=True,
            flood_zone=False
        )

        checklist = db.get_project_checklist(project_id, discipline)
        print(f"\n{discipline.title()} Checklist:")
        print(f"  Total Items: {checklist['total_items']}")
        print(f"  Categories: {len(checklist['categories'])}")

    # Show summary
    print("\n" + "-" * 70)
    print("Project Compliance Summary")
    print("-" * 70)

    summary = db.get_checklist_summary(project_id)
    print(f"\nOverall Status: {summary['overall_status']}")
    print(f"Total Items: {summary['total_items']}")

    for disc, stats in summary['disciplines'].items():
        print(f"\n  {disc.title()}:")
        print(f"    Items: {stats['total']}")
        print(f"    Complete: {stats['complete']}")
        print(f"    Issues: {stats['issues']}")

    print("\n" + "=" * 70)
    print("System ready for code compliance tracking")
    print("=" * 70)

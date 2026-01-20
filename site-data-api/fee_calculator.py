"""
Automated Permit Fee Calculator
================================
Calculates permit fees for South Florida jurisdictions based on
project valuation, square footage, and permit type.

Author: BIM Ops Studio
"""

import sqlite3
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
import math


class FeeType(Enum):
    """Types of permit fees"""
    BUILDING_PERMIT = "building_permit"
    PLAN_REVIEW = "plan_review"
    ELECTRICAL = "electrical"
    MECHANICAL = "mechanical"
    PLUMBING = "plumbing"
    ROOFING = "roofing"
    FIRE_ALARM = "fire_alarm"
    FIRE_SPRINKLER = "fire_sprinkler"
    IMPACT_FEE = "impact_fee"
    TECHNOLOGY_FEE = "technology_fee"
    CERTIFICATE_OF_USE = "certificate_of_use"
    ZONING = "zoning"
    DRC_REVIEW = "drc_review"
    EXPEDITE = "expedite"
    RE_INSPECTION = "re_inspection"


class CalculationMethod(Enum):
    """Methods for calculating fees"""
    FLAT = "flat"
    PER_SQFT = "per_sqft"
    PERCENT_OF_VALUE = "percent_of_value"
    PERCENT_OF_PERMIT = "percent_of_permit"
    TIERED = "tiered"
    PER_FIXTURE = "per_fixture"
    PER_CIRCUIT = "per_circuit"
    PER_TON = "per_ton"
    PER_SQUARE = "per_square"


class PermitFeeCalculator:
    """
    Automated permit fee calculator for South Florida jurisdictions.

    Supports:
    - Building permits (based on valuation)
    - Plan review fees
    - Trade permits (electrical, mechanical, plumbing)
    - Specialty permits (roofing, fire alarm, fire sprinkler)
    - Impact fees
    - Technology/administrative fees
    """

    def __init__(self, db_path: str = "fee_calculator.db"):
        self.db_path = db_path
        self._init_database()
        self._populate_fee_schedules()

    def _init_database(self):
        """Initialize the database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            # Fee schedules by jurisdiction
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fee_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jurisdiction TEXT NOT NULL,
                    fee_type TEXT NOT NULL,
                    fee_name TEXT NOT NULL,
                    calculation_method TEXT NOT NULL,

                    -- Calculation parameters
                    flat_fee REAL,
                    per_unit_rate REAL,
                    percent_rate REAL,
                    minimum_fee REAL,
                    maximum_fee REAL,

                    -- For tiered calculations
                    tier_data TEXT,

                    -- Unit descriptions
                    unit_type TEXT,

                    effective_date TEXT,
                    notes TEXT,

                    UNIQUE(jurisdiction, fee_type, fee_name)
                )
            """)

            # Valuation table (ICC Building Valuation Data)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS valuation_table (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occupancy_group TEXT NOT NULL,
                    construction_type TEXT NOT NULL,
                    cost_per_sqft REAL NOT NULL,
                    effective_year INTEGER,
                    notes TEXT,
                    UNIQUE(occupancy_group, construction_type)
                )
            """)

            # Fee calculations history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fee_calculations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    jurisdiction TEXT NOT NULL,
                    calculation_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    project_value REAL,
                    total_sqft REAL,
                    fee_breakdown TEXT,
                    total_fees REAL,
                    notes TEXT
                )
            """)

            conn.commit()

    def _populate_fee_schedules(self):
        """Populate fee schedules for South Florida jurisdictions"""
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM fee_schedules").fetchone()[0]
            if count > 0:
                return

            # =================================================================
            # MIAMI-DADE COUNTY (UNINCORPORATED)
            # =================================================================
            miami_dade_fees = [
                # Building Permit - Tiered by valuation
                ("building_permit", "Building Permit Fee", "tiered", None, None, None, 93, None,
                 '[{"min":0,"max":2000,"fee":93},{"min":2000,"max":25000,"rate":0.0215},{"min":25000,"max":50000,"rate":0.0165},{"min":50000,"max":100000,"rate":0.0125},{"min":100000,"max":500000,"rate":0.0088},{"min":500000,"max":1000000,"rate":0.007},{"min":1000000,"max":null,"rate":0.0055}]',
                 "valuation"),

                # Plan Review - 65% of building permit
                ("plan_review", "Plan Review Fee", "percent_of_permit", None, None, 0.65, 50, None, None, None),

                # Technology Fee - 4% of permit
                ("technology_fee", "Technology Fee", "percent_of_permit", None, None, 0.04, 2, None, None, None),

                # Electrical
                ("electrical", "Electrical Permit", "tiered", 75, None, None, 75, None,
                 '[{"name":"base","fee":75},{"name":"per_circuit","rate":3.5}]', "circuits"),

                # Mechanical
                ("mechanical", "Mechanical Permit", "per_ton", 85, 12, None, 85, None, None, "tons"),

                # Plumbing
                ("plumbing", "Plumbing Permit", "per_fixture", 75, 8, None, 75, None, None, "fixtures"),

                # Roofing - per square (100 sqft)
                ("roofing", "Roofing Permit", "per_square", 85, 10, None, 85, None, None, "squares"),

                # Fire Alarm
                ("fire_alarm", "Fire Alarm Permit", "tiered", None, None, None, 150, None,
                 '[{"min":0,"max":10,"fee":150},{"min":10,"max":50,"rate":8},{"min":50,"max":null,"rate":5}]',
                 "devices"),

                # Fire Sprinkler
                ("fire_sprinkler", "Fire Sprinkler Permit", "tiered", None, None, None, 200, None,
                 '[{"min":0,"max":20,"fee":200},{"min":20,"max":100,"rate":6},{"min":100,"max":null,"rate":4}]',
                 "heads"),

                # Re-inspection
                ("re_inspection", "Re-inspection Fee", "flat", 75, None, None, None, None, None, None),

                # Certificate of Occupancy
                ("certificate_of_use", "Certificate of Occupancy", "flat", 50, None, None, None, None, None, None),
            ]

            for fee in miami_dade_fees:
                conn.execute("""
                    INSERT INTO fee_schedules
                    (jurisdiction, fee_type, fee_name, calculation_method,
                     flat_fee, per_unit_rate, percent_rate, minimum_fee, maximum_fee,
                     tier_data, unit_type)
                    VALUES ('Miami-Dade County', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, fee)

            # =================================================================
            # CITY OF MIAMI
            # =================================================================
            miami_fees = [
                ("building_permit", "Building Permit Fee", "tiered", None, None, None, 100, None,
                 '[{"min":0,"max":5000,"fee":100},{"min":5000,"max":50000,"rate":0.02},{"min":50000,"max":100000,"rate":0.015},{"min":100000,"max":500000,"rate":0.01},{"min":500000,"max":null,"rate":0.008}]',
                 "valuation"),
                ("plan_review", "Plan Review Fee", "percent_of_permit", None, None, 0.65, 75, None, None, None),
                ("technology_fee", "Technology Fee", "percent_of_permit", None, None, 0.05, 5, None, None, None),
                ("electrical", "Electrical Permit", "tiered", 80, None, None, 80, None,
                 '[{"name":"base","fee":80},{"name":"per_circuit","rate":4}]', "circuits"),
                ("mechanical", "Mechanical Permit", "per_ton", 90, 15, None, 90, None, None, "tons"),
                ("plumbing", "Plumbing Permit", "per_fixture", 80, 10, None, 80, None, None, "fixtures"),
                ("roofing", "Roofing Permit", "per_square", 90, 12, None, 90, None, None, "squares"),
                ("zoning", "Zoning Review Fee", "flat", 200, None, None, None, None, None, None),
                ("re_inspection", "Re-inspection Fee", "flat", 100, None, None, None, None, None, None),
            ]

            for fee in miami_fees:
                conn.execute("""
                    INSERT INTO fee_schedules
                    (jurisdiction, fee_type, fee_name, calculation_method,
                     flat_fee, per_unit_rate, percent_rate, minimum_fee, maximum_fee,
                     tier_data, unit_type)
                    VALUES ('City of Miami', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, fee)

            # =================================================================
            # BROWARD COUNTY
            # =================================================================
            broward_fees = [
                ("building_permit", "Building Permit Fee", "tiered", None, None, None, 85, None,
                 '[{"min":0,"max":2500,"fee":85},{"min":2500,"max":25000,"rate":0.02},{"min":25000,"max":100000,"rate":0.015},{"min":100000,"max":500000,"rate":0.01},{"min":500000,"max":null,"rate":0.007}]',
                 "valuation"),
                ("plan_review", "Plan Review Fee", "percent_of_permit", None, None, 0.60, 50, None, None, None),
                ("technology_fee", "Technology Fee", "percent_of_permit", None, None, 0.03, 2, None, None, None),
                ("electrical", "Electrical Permit", "tiered", 70, None, None, 70, None,
                 '[{"name":"base","fee":70},{"name":"per_circuit","rate":3}]', "circuits"),
                ("mechanical", "Mechanical Permit", "per_ton", 80, 10, None, 80, None, None, "tons"),
                ("plumbing", "Plumbing Permit", "per_fixture", 70, 7, None, 70, None, None, "fixtures"),
                ("roofing", "Roofing Permit", "per_square", 80, 9, None, 80, None, None, "squares"),
                ("re_inspection", "Re-inspection Fee", "flat", 65, None, None, None, None, None, None),
            ]

            for fee in broward_fees:
                conn.execute("""
                    INSERT INTO fee_schedules
                    (jurisdiction, fee_type, fee_name, calculation_method,
                     flat_fee, per_unit_rate, percent_rate, minimum_fee, maximum_fee,
                     tier_data, unit_type)
                    VALUES ('Broward County', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, fee)

            # =================================================================
            # PALM BEACH COUNTY
            # =================================================================
            palm_beach_fees = [
                ("building_permit", "Building Permit Fee", "tiered", None, None, None, 80, None,
                 '[{"min":0,"max":3000,"fee":80},{"min":3000,"max":25000,"rate":0.018},{"min":25000,"max":100000,"rate":0.014},{"min":100000,"max":500000,"rate":0.009},{"min":500000,"max":null,"rate":0.006}]',
                 "valuation"),
                ("plan_review", "Plan Review Fee", "percent_of_permit", None, None, 0.55, 45, None, None, None),
                ("technology_fee", "Technology Fee", "flat", 25, None, None, None, None, None, None),
                ("electrical", "Electrical Permit", "tiered", 65, None, None, 65, None,
                 '[{"name":"base","fee":65},{"name":"per_circuit","rate":2.5}]', "circuits"),
                ("mechanical", "Mechanical Permit", "per_ton", 75, 10, None, 75, None, None, "tons"),
                ("plumbing", "Plumbing Permit", "per_fixture", 65, 6, None, 65, None, None, "fixtures"),
                ("roofing", "Roofing Permit", "per_square", 75, 8, None, 75, None, None, "squares"),
                ("re_inspection", "Re-inspection Fee", "flat", 55, None, None, None, None, None, None),
            ]

            for fee in palm_beach_fees:
                conn.execute("""
                    INSERT INTO fee_schedules
                    (jurisdiction, fee_type, fee_name, calculation_method,
                     flat_fee, per_unit_rate, percent_rate, minimum_fee, maximum_fee,
                     tier_data, unit_type)
                    VALUES ('Palm Beach County', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, fee)

            # =================================================================
            # ICC BUILDING VALUATION DATA (2024)
            # =================================================================
            valuation_data = [
                # Group A - Assembly
                ("A-1", "IA", 298.45), ("A-1", "IB", 288.65), ("A-1", "IIA", 280.95),
                ("A-1", "IIB", 268.35), ("A-1", "IIIA", 262.40), ("A-1", "IIIB", 252.60),
                ("A-1", "IV", 268.85), ("A-1", "VA", 246.70), ("A-1", "VB", 236.90),

                # Group B - Business
                ("B", "IA", 234.55), ("B", "IB", 226.30), ("B", "IIA", 219.75),
                ("B", "IIB", 209.90), ("B", "IIIA", 204.45), ("B", "IIIB", 196.20),
                ("B", "IV", 209.35), ("B", "VA", 190.40), ("B", "VB", 182.15),

                # Group E - Educational
                ("E", "IA", 246.90), ("E", "IB", 238.65), ("E", "IIA", 232.10),
                ("E", "IIB", 222.25), ("E", "IIIA", 216.80), ("E", "IIIB", 208.55),
                ("E", "IV", 221.70), ("E", "VA", 202.75), ("E", "VB", 194.50),

                # Group F - Factory/Industrial
                ("F-1", "IA", 123.85), ("F-1", "IB", 118.60), ("F-1", "IIA", 114.30),
                ("F-1", "IIB", 107.55), ("F-1", "IIIA", 103.30), ("F-1", "IIIB", 98.05),
                ("F-1", "IV", 107.00), ("F-1", "VA", 93.25), ("F-1", "VB", 87.95),

                # Group H - Hazardous
                ("H", "IA", 123.85), ("H", "IB", 118.60), ("H", "IIA", 114.30),
                ("H", "IIB", 107.55), ("H", "IIIA", 103.30), ("H", "IIIB", 98.05),

                # Group I - Institutional
                ("I-1", "IA", 241.85), ("I-1", "IB", 233.60), ("I-1", "IIA", 227.05),
                ("I-1", "IIB", 217.20), ("I-1", "IIIA", 211.75), ("I-1", "IIIB", 203.50),

                # Group M - Mercantile
                ("M", "IA", 174.50), ("M", "IB", 167.85), ("M", "IIA", 162.90),
                ("M", "IIB", 155.30), ("M", "IIIA", 151.10), ("M", "IIIB", 144.45),
                ("M", "IV", 154.75), ("M", "VA", 139.85), ("M", "VB", 133.20),

                # Group R-1 - Hotels
                ("R-1", "IA", 209.55), ("R-1", "IB", 202.00), ("R-1", "IIA", 196.40),
                ("R-1", "IIB", 187.70), ("R-1", "IIIA", 183.05), ("R-1", "IIIB", 175.50),
                ("R-1", "IV", 187.15), ("R-1", "VA", 170.20), ("R-1", "VB", 162.65),

                # Group R-2 - Apartments
                ("R-2", "IA", 175.60), ("R-2", "IB", 169.60), ("R-2", "IIA", 164.85),
                ("R-2", "IIB", 157.55), ("R-2", "IIIA", 153.40), ("R-2", "IIIB", 147.40),
                ("R-2", "IV", 157.00), ("R-2", "VA", 142.40), ("R-2", "VB", 136.40),

                # Group R-3 - Single Family
                ("R-3", "VB", 148.65),

                # Group S - Storage
                ("S-1", "IA", 115.65), ("S-1", "IB", 110.40), ("S-1", "IIA", 106.10),
                ("S-1", "IIB", 99.35), ("S-1", "IIIA", 95.10), ("S-1", "IIIB", 89.85),
                ("S-1", "IV", 98.80), ("S-1", "VA", 85.05), ("S-1", "VB", 79.80),
            ]

            for occ, const, cost in valuation_data:
                conn.execute("""
                    INSERT OR REPLACE INTO valuation_table
                    (occupancy_group, construction_type, cost_per_sqft, effective_year)
                    VALUES (?, ?, ?, 2024)
                """, (occ, const, cost))

            conn.commit()

    # =========================================================================
    # FEE CALCULATION METHODS
    # =========================================================================

    def calculate_project_value(
        self,
        sqft: float,
        occupancy_group: str,
        construction_type: str
    ) -> float:
        """Calculate project value using ICC Building Valuation Data"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("""
                SELECT cost_per_sqft FROM valuation_table
                WHERE occupancy_group = ? AND construction_type = ?
            """, (occupancy_group, construction_type)).fetchone()

            if row:
                return sqft * row[0]
            else:
                # Default value if not found
                return sqft * 150  # Conservative estimate

    def _calculate_tiered_fee(self, tier_data: str, value: float, unit_type: str) -> float:
        """Calculate fee using tiered schedule"""
        import json
        tiers = json.loads(tier_data)
        total_fee = 0

        if unit_type == "valuation":
            # Tiered by project value
            remaining = value
            for tier in tiers:
                tier_min = tier.get("min", 0)
                tier_max = tier.get("max")
                tier_fee = tier.get("fee")
                tier_rate = tier.get("rate")

                if tier_max is None:
                    tier_max = float('inf')

                if remaining <= 0:
                    break

                if tier_fee and tier_min == 0:
                    # Base fee
                    total_fee += tier_fee
                    remaining -= tier_max
                elif tier_rate:
                    # Rate-based
                    if value > tier_min:
                        taxable = min(remaining, tier_max - tier_min)
                        total_fee += taxable * tier_rate
                        remaining -= taxable
        else:
            # Count-based tiers (circuits, fixtures, devices, etc.)
            count = value
            for tier in tiers:
                if tier.get("name") == "base":
                    total_fee += tier.get("fee", 0)
                elif tier.get("name") == "per_circuit" or tier.get("rate"):
                    total_fee += count * tier.get("rate", 0)

        return total_fee

    def calculate_permit_fee(
        self,
        jurisdiction: str,
        fee_type: str,
        value: float = 0,
        unit_count: float = 0
    ) -> Dict:
        """Calculate a specific permit fee"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Find the fee schedule
            row = conn.execute("""
                SELECT * FROM fee_schedules
                WHERE jurisdiction LIKE ? AND fee_type = ?
            """, (f"%{jurisdiction}%", fee_type)).fetchone()

            if not row:
                return {"error": f"Fee schedule not found for {jurisdiction} - {fee_type}"}

            schedule = dict(row)
            method = schedule['calculation_method']
            calculated_fee = 0

            if method == "flat":
                calculated_fee = schedule['flat_fee']

            elif method == "per_sqft":
                calculated_fee = value * schedule['per_unit_rate']

            elif method == "percent_of_value":
                calculated_fee = value * schedule['percent_rate']

            elif method == "percent_of_permit":
                # This needs the building permit fee to be calculated first
                calculated_fee = value * schedule['percent_rate']

            elif method == "per_fixture" or method == "per_ton" or method == "per_square":
                base = schedule['flat_fee'] or 0
                per_unit = schedule['per_unit_rate'] or 0
                calculated_fee = base + (unit_count * per_unit)

            elif method == "tiered":
                calculated_fee = self._calculate_tiered_fee(
                    schedule['tier_data'],
                    value if value else unit_count,
                    schedule['unit_type']
                )

            # Apply minimum/maximum
            if schedule['minimum_fee']:
                calculated_fee = max(calculated_fee, schedule['minimum_fee'])
            if schedule['maximum_fee']:
                calculated_fee = min(calculated_fee, schedule['maximum_fee'])

            return {
                "fee_type": fee_type,
                "fee_name": schedule['fee_name'],
                "calculation_method": method,
                "input_value": value,
                "unit_count": unit_count,
                "calculated_fee": round(calculated_fee, 2)
            }

    def calculate_all_fees(
        self,
        jurisdiction: str,
        project_value: float,
        sqft: float = 0,
        electrical_circuits: int = 0,
        mechanical_tons: float = 0,
        plumbing_fixtures: int = 0,
        roofing_squares: float = 0,
        fire_alarm_devices: int = 0,
        fire_sprinkler_heads: int = 0,
        include_plan_review: bool = True,
        include_technology_fee: bool = True
    ) -> Dict:
        """Calculate all applicable permit fees for a project"""

        fees = []
        total = 0

        # Building permit (required)
        building = self.calculate_permit_fee(jurisdiction, "building_permit", project_value)
        if "error" not in building:
            fees.append(building)
            total += building['calculated_fee']

            # Plan review (percentage of building permit)
            if include_plan_review:
                plan_review = self.calculate_permit_fee(
                    jurisdiction, "plan_review", building['calculated_fee']
                )
                if "error" not in plan_review:
                    fees.append(plan_review)
                    total += plan_review['calculated_fee']

            # Technology fee (percentage of building permit)
            if include_technology_fee:
                tech = self.calculate_permit_fee(
                    jurisdiction, "technology_fee", building['calculated_fee']
                )
                if "error" not in tech:
                    fees.append(tech)
                    total += tech['calculated_fee']

        # Trade permits
        if electrical_circuits > 0:
            elec = self.calculate_permit_fee(
                jurisdiction, "electrical", electrical_circuits, electrical_circuits
            )
            if "error" not in elec:
                fees.append(elec)
                total += elec['calculated_fee']

        if mechanical_tons > 0:
            mech = self.calculate_permit_fee(
                jurisdiction, "mechanical", 0, mechanical_tons
            )
            if "error" not in mech:
                fees.append(mech)
                total += mech['calculated_fee']

        if plumbing_fixtures > 0:
            plumb = self.calculate_permit_fee(
                jurisdiction, "plumbing", 0, plumbing_fixtures
            )
            if "error" not in plumb:
                fees.append(plumb)
                total += plumb['calculated_fee']

        if roofing_squares > 0:
            roof = self.calculate_permit_fee(
                jurisdiction, "roofing", 0, roofing_squares
            )
            if "error" not in roof:
                fees.append(roof)
                total += roof['calculated_fee']

        if fire_alarm_devices > 0:
            alarm = self.calculate_permit_fee(
                jurisdiction, "fire_alarm", 0, fire_alarm_devices
            )
            if "error" not in alarm:
                fees.append(alarm)
                total += alarm['calculated_fee']

        if fire_sprinkler_heads > 0:
            sprinkler = self.calculate_permit_fee(
                jurisdiction, "fire_sprinkler", 0, fire_sprinkler_heads
            )
            if "error" not in sprinkler:
                fees.append(sprinkler)
                total += sprinkler['calculated_fee']

        return {
            "jurisdiction": jurisdiction,
            "project_value": project_value,
            "fees": fees,
            "subtotal": round(total, 2),
            "total_estimated": round(total, 2)
        }

    def generate_fee_estimate(
        self,
        jurisdiction: str,
        project_value: float,
        sqft: float,
        project_name: str = None,
        **kwargs
    ) -> str:
        """Generate a formatted fee estimate"""
        result = self.calculate_all_fees(jurisdiction, project_value, sqft, **kwargs)

        lines = [
            "=" * 60,
            "PERMIT FEE ESTIMATE",
            "=" * 60,
            f"Date: {datetime.now().strftime('%B %d, %Y')}",
            ""
        ]

        if project_name:
            lines.append(f"Project: {project_name}")
        lines.extend([
            f"Jurisdiction: {result['jurisdiction']}",
            f"Estimated Project Value: ${result['project_value']:,.2f}",
            f"Square Footage: {sqft:,.0f} SF",
            "",
            "-" * 60,
            "FEE BREAKDOWN",
            "-" * 60,
            ""
        ])

        for fee in result['fees']:
            lines.append(f"  {fee['fee_name']:<35} ${fee['calculated_fee']:>10,.2f}")

        lines.extend([
            "",
            "-" * 60,
            f"  {'ESTIMATED TOTAL':<35} ${result['total_estimated']:>10,.2f}",
            "=" * 60,
            "",
            "Notes:",
            "- This is an estimate only. Actual fees may vary.",
            "- Impact fees and DRC fees may apply depending on project.",
            "- Contact building department for exact fee calculation.",
            "- Fees subject to change without notice."
        ])

        return "\n".join(lines)

    def compare_jurisdiction_fees(
        self,
        jurisdictions: List[str],
        project_value: float
    ) -> Dict:
        """Compare fees across multiple jurisdictions"""
        comparison = {
            "project_value": project_value,
            "jurisdictions": []
        }

        for jur in jurisdictions:
            result = self.calculate_all_fees(jur, project_value)
            comparison["jurisdictions"].append({
                "name": jur,
                "total": result['total_estimated'],
                "breakdown": {f['fee_name']: f['calculated_fee'] for f in result['fees']}
            })

        # Sort by total
        comparison["jurisdictions"].sort(key=lambda x: x['total'])

        return comparison


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("PERMIT FEE CALCULATOR")
    print("=" * 60)

    calc = PermitFeeCalculator()

    # Test project
    project_value = 500000
    sqft = 5000

    print(f"\nTest Project: ${project_value:,} value, {sqft:,} SF")

    # Calculate for Miami-Dade
    print("\n" + "-" * 60)
    print("Miami-Dade County Fees:")
    print("-" * 60)
    result = calc.calculate_all_fees(
        jurisdiction="Miami-Dade County",
        project_value=project_value,
        sqft=sqft,
        electrical_circuits=40,
        mechanical_tons=15,
        plumbing_fixtures=25
    )
    for fee in result['fees']:
        print(f"  {fee['fee_name']:<35} ${fee['calculated_fee']:>10,.2f}")
    print(f"\n  {'TOTAL':<35} ${result['total_estimated']:>10,.2f}")

    # Compare jurisdictions
    print("\n" + "-" * 60)
    print("Jurisdiction Comparison ($500,000 project):")
    print("-" * 60)
    comparison = calc.compare_jurisdiction_fees(
        ["Miami-Dade County", "City of Miami", "Broward County", "Palm Beach County"],
        500000
    )
    for jur in comparison['jurisdictions']:
        print(f"  {jur['name']:<30} ${jur['total']:>10,.2f}")

    # Full estimate
    print("\n")
    estimate = calc.generate_fee_estimate(
        jurisdiction="Miami-Dade County",
        project_value=750000,
        sqft=7500,
        project_name="Goulds Tower Commercial Building",
        electrical_circuits=60,
        mechanical_tons=25,
        plumbing_fixtures=40,
        roofing_squares=80,
        fire_alarm_devices=50,
        fire_sprinkler_heads=150
    )
    print(estimate)

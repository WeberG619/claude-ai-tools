"""
NOA/Product Approval Database
==============================
Database for tracking Miami-Dade NOA (Notice of Acceptance) approved products
and Florida Product Approvals for HVHZ construction.

In the High-Velocity Hurricane Zone (HVHZ), all exterior products must have
either a Miami-Dade NOA or Florida Product Approval (FL#).

Author: BIM Ops Studio
"""

import sqlite3
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import re


class ProductCategory(Enum):
    """Categories of building products requiring approval"""
    WINDOWS = "windows"
    DOORS = "doors"
    IMPACT_GLASS = "impact_glass"
    SHUTTERS = "shutters"
    ROOFING = "roofing"
    SKYLIGHTS = "skylights"
    GARAGE_DOORS = "garage_doors"
    EXTERIOR_WALLS = "exterior_walls"
    FASTENERS = "fasteners"
    SEALANTS = "sealants"
    HARDWARE = "hardware"
    LOUVERS = "louvers"
    PANELS = "panels"


class ApprovalType(Enum):
    """Types of product approvals"""
    MIAMI_DADE_NOA = "miami_dade_noa"
    FLORIDA_PRODUCT = "florida_product"
    ICC_ES = "icc_es"
    UL_LISTED = "ul_listed"


class NOADatabase:
    """
    Database for managing product approvals in HVHZ construction.

    Features:
    - Track NOA and FL# product approvals
    - Link products to projects
    - Check approval expiration
    - Search by manufacturer, category, or performance rating
    - Generate product approval schedules for submittals
    """

    def __init__(self, db_path: str = "noa_database.db"):
        self.db_path = db_path
        self._init_database()
        self._populate_sample_products()

    def _init_database(self):
        """Initialize the database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            # Manufacturers table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS manufacturers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    website TEXT,
                    phone TEXT,
                    rep_name TEXT,
                    rep_email TEXT,
                    rep_phone TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Product approvals table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS product_approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    manufacturer_id INTEGER,
                    approval_type TEXT NOT NULL,
                    approval_number TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT,
                    model_numbers TEXT,
                    description TEXT,

                    -- Performance ratings
                    design_pressure_positive REAL,
                    design_pressure_negative REAL,
                    design_pressure_unit TEXT DEFAULT 'psf',
                    missile_impact_level TEXT,
                    water_resistance TEXT,
                    air_infiltration TEXT,
                    structural_rating TEXT,
                    fire_rating TEXT,
                    energy_rating TEXT,

                    -- HVHZ specific
                    hvhz_approved BOOLEAN DEFAULT TRUE,
                    large_missile_approved BOOLEAN DEFAULT FALSE,
                    small_missile_approved BOOLEAN DEFAULT FALSE,

                    -- Approval dates
                    approval_date TEXT,
                    expiration_date TEXT,
                    last_verified TEXT,

                    -- Documentation
                    noa_document_url TEXT,
                    installation_instructions_url TEXT,

                    -- Status
                    active BOOLEAN DEFAULT TRUE,
                    notes TEXT,

                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id),
                    UNIQUE(approval_type, approval_number)
                )
            """)

            # Project product selections
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    product_approval_id INTEGER NOT NULL,
                    location TEXT,
                    quantity INTEGER,
                    spec_section TEXT,
                    sheet_reference TEXT,
                    submittal_status TEXT DEFAULT 'pending',
                    approved_date TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_approval_id) REFERENCES product_approvals(id)
                )
            """)

            # Product alternatives (substitutions)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS product_alternatives (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    primary_product_id INTEGER NOT NULL,
                    alternative_product_id INTEGER NOT NULL,
                    equivalency_notes TEXT,
                    FOREIGN KEY (primary_product_id) REFERENCES product_approvals(id),
                    FOREIGN KEY (alternative_product_id) REFERENCES product_approvals(id)
                )
            """)

            conn.commit()

    def _populate_sample_products(self):
        """Populate with common HVHZ-approved products"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if already populated
            count = conn.execute("SELECT COUNT(*) FROM manufacturers").fetchone()[0]
            if count > 0:
                return

            # Add manufacturers
            manufacturers = [
                ("PGT Industries", "https://www.pgtindustries.com", "(941) 480-1600"),
                ("CGI Windows & Doors", "https://www.cgiwindows.com", "(800) 442-9042"),
                ("Impact Windows of Florida", "https://www.impactwindowsfl.com", "(305) 821-8852"),
                ("ES Windows", "https://www.eswindows.com", "(305) 638-8282"),
                ("Lawson Industries", "https://www.lawsonwindows.com", "(305) 638-4696"),
                ("YKK AP America", "https://www.ykkap.com", "(678) 838-6000"),
                ("Kolbe Windows & Doors", "https://www.kolbewindows.com", "(800) 955-8177"),
                ("GAF Roofing", "https://www.gaf.com", "(973) 628-3000"),
                ("CertainTeed Roofing", "https://www.certainteed.com", "(800) 233-8990"),
                ("Boral Roofing", "https://www.boralamerica.com", "(800) 699-8453"),
                ("Roll-A-Way Storm Shutters", "https://www.roll-a-way.com", "(305) 687-8787"),
                ("HV Aluminum", "https://www.hvaluminum.com", "(305) 835-1422"),
                ("Clopay Garage Doors", "https://www.clopaydoor.com", "(800) 225-6729"),
                ("Amarr Garage Doors", "https://www.amarr.com", "(800) 503-3667"),
                ("Simpson Strong-Tie", "https://www.strongtie.com", "(800) 999-5099"),
            ]

            for name, website, phone in manufacturers:
                conn.execute("""
                    INSERT INTO manufacturers (name, website, phone)
                    VALUES (?, ?, ?)
                """, (name, website, phone))

            # Get manufacturer IDs
            mfr_ids = {}
            for row in conn.execute("SELECT id, name FROM manufacturers").fetchall():
                mfr_ids[row[1]] = row[0]

            # Add sample products
            products = [
                # Windows - PGT
                {
                    "manufacturer": "PGT Industries",
                    "type": "miami_dade_noa",
                    "number": "NOA 21-0609.01",
                    "name": "PGT WinGuard Aluminum Single Hung",
                    "category": "windows",
                    "subcategory": "single_hung",
                    "models": "WG-SHXX Series",
                    "dp_pos": 75, "dp_neg": -90,
                    "missile": "Large Missile",
                    "hvhz": True, "large": True, "small": True,
                    "expiration": "2027-03-15"
                },
                {
                    "manufacturer": "PGT Industries",
                    "type": "miami_dade_noa",
                    "number": "NOA 21-0609.02",
                    "name": "PGT WinGuard Aluminum Horizontal Roller",
                    "category": "windows",
                    "subcategory": "horizontal_sliding",
                    "models": "WG-HRXX Series",
                    "dp_pos": 70, "dp_neg": -85,
                    "missile": "Large Missile",
                    "hvhz": True, "large": True, "small": True,
                    "expiration": "2027-03-15"
                },
                # Windows - CGI
                {
                    "manufacturer": "CGI Windows & Doors",
                    "type": "miami_dade_noa",
                    "number": "NOA 20-1215.04",
                    "name": "CGI Sentinel Series Single Hung",
                    "category": "windows",
                    "subcategory": "single_hung",
                    "models": "SEN-SH Series",
                    "dp_pos": 80, "dp_neg": -95,
                    "missile": "Large Missile",
                    "hvhz": True, "large": True, "small": True,
                    "expiration": "2026-12-01"
                },
                {
                    "manufacturer": "CGI Windows & Doors",
                    "type": "miami_dade_noa",
                    "number": "NOA 20-1215.06",
                    "name": "CGI Estate Collection Fixed Picture",
                    "category": "windows",
                    "subcategory": "fixed",
                    "models": "EST-FP Series",
                    "dp_pos": 100, "dp_neg": -120,
                    "missile": "Large Missile",
                    "hvhz": True, "large": True, "small": True,
                    "expiration": "2026-12-01"
                },
                # Doors - PGT
                {
                    "manufacturer": "PGT Industries",
                    "type": "miami_dade_noa",
                    "number": "NOA 21-0610.01",
                    "name": "PGT WinGuard Sliding Glass Door",
                    "category": "doors",
                    "subcategory": "sliding_glass",
                    "models": "WG-SGDXX Series",
                    "dp_pos": 65, "dp_neg": -80,
                    "missile": "Large Missile",
                    "hvhz": True, "large": True, "small": True,
                    "expiration": "2027-03-15"
                },
                {
                    "manufacturer": "CGI Windows & Doors",
                    "type": "miami_dade_noa",
                    "number": "NOA 20-1216.02",
                    "name": "CGI Targa Sliding Glass Door",
                    "category": "doors",
                    "subcategory": "sliding_glass",
                    "models": "TARGA-SGD Series",
                    "dp_pos": 70, "dp_neg": -85,
                    "missile": "Large Missile",
                    "hvhz": True, "large": True, "small": True,
                    "expiration": "2026-12-01"
                },
                # Entry Doors
                {
                    "manufacturer": "ES Windows",
                    "type": "miami_dade_noa",
                    "number": "NOA 19-0823.05",
                    "name": "ES Hurricane Entry Door System",
                    "category": "doors",
                    "subcategory": "entry",
                    "models": "ES-ENTRY Series",
                    "dp_pos": 75, "dp_neg": -90,
                    "missile": "Large Missile",
                    "hvhz": True, "large": True, "small": True,
                    "expiration": "2026-08-20"
                },
                # Shutters
                {
                    "manufacturer": "Roll-A-Way Storm Shutters",
                    "type": "miami_dade_noa",
                    "number": "NOA 18-0312.02",
                    "name": "Roll-A-Way Rolling Shutter",
                    "category": "shutters",
                    "subcategory": "rolling",
                    "models": "RAW-RS Series",
                    "dp_pos": 85, "dp_neg": -100,
                    "missile": "Large Missile",
                    "hvhz": True, "large": True, "small": True,
                    "expiration": "2026-03-15"
                },
                {
                    "manufacturer": "HV Aluminum",
                    "type": "miami_dade_noa",
                    "number": "NOA 19-0415.03",
                    "name": "HV Accordion Hurricane Shutter",
                    "category": "shutters",
                    "subcategory": "accordion",
                    "models": "HVA-ACC Series",
                    "dp_pos": 80, "dp_neg": -95,
                    "missile": "Large Missile",
                    "hvhz": True, "large": True, "small": True,
                    "expiration": "2026-04-15"
                },
                {
                    "manufacturer": "HV Aluminum",
                    "type": "miami_dade_noa",
                    "number": "NOA 19-0415.05",
                    "name": "HV Bahama Hurricane Shutter",
                    "category": "shutters",
                    "subcategory": "bahama",
                    "models": "HVA-BAH Series",
                    "dp_pos": 75, "dp_neg": -90,
                    "missile": "Large Missile",
                    "hvhz": True, "large": True, "small": True,
                    "expiration": "2026-04-15"
                },
                # Garage Doors
                {
                    "manufacturer": "Clopay Garage Doors",
                    "type": "miami_dade_noa",
                    "number": "NOA 20-0718.01",
                    "name": "Clopay Wind Code Garage Door",
                    "category": "garage_doors",
                    "subcategory": "sectional",
                    "models": "WC-GD Series",
                    "dp_pos": 50, "dp_neg": -60,
                    "missile": "Large Missile",
                    "hvhz": True, "large": True, "small": True,
                    "expiration": "2027-07-18"
                },
                {
                    "manufacturer": "Amarr Garage Doors",
                    "type": "miami_dade_noa",
                    "number": "NOA 20-0522.03",
                    "name": "Amarr Hurricane Series",
                    "category": "garage_doors",
                    "subcategory": "sectional",
                    "models": "AMR-HURR Series",
                    "dp_pos": 55, "dp_neg": -65,
                    "missile": "Large Missile",
                    "hvhz": True, "large": True, "small": True,
                    "expiration": "2027-05-22"
                },
                # Roofing
                {
                    "manufacturer": "GAF Roofing",
                    "type": "miami_dade_noa",
                    "number": "NOA 21-0103.07",
                    "name": "GAF Timberline HDZ Shingles",
                    "category": "roofing",
                    "subcategory": "asphalt_shingles",
                    "models": "TL-HDZ",
                    "dp_pos": None, "dp_neg": None,
                    "missile": None,
                    "structural": "Class H (150 mph)",
                    "hvhz": True, "large": False, "small": False,
                    "expiration": "2028-01-03"
                },
                {
                    "manufacturer": "Boral Roofing",
                    "type": "miami_dade_noa",
                    "number": "NOA 19-0918.02",
                    "name": "Boral Barcelona 900 Concrete Tile",
                    "category": "roofing",
                    "subcategory": "concrete_tile",
                    "models": "BCN-900",
                    "dp_pos": None, "dp_neg": None,
                    "missile": None,
                    "structural": "Class H (180 mph)",
                    "hvhz": True, "large": False, "small": False,
                    "expiration": "2026-09-18"
                },
                # Fasteners
                {
                    "manufacturer": "Simpson Strong-Tie",
                    "type": "miami_dade_noa",
                    "number": "NOA 20-0612.15",
                    "name": "Simpson H2.5A Hurricane Tie",
                    "category": "fasteners",
                    "subcategory": "hurricane_ties",
                    "models": "H2.5A, H2.5AZ",
                    "dp_pos": None, "dp_neg": None,
                    "missile": None,
                    "structural": "1500 lb uplift",
                    "hvhz": True, "large": False, "small": False,
                    "expiration": "2027-06-12"
                },
                {
                    "manufacturer": "Simpson Strong-Tie",
                    "type": "miami_dade_noa",
                    "number": "NOA 20-0612.18",
                    "name": "Simpson HDU Hold-Down",
                    "category": "fasteners",
                    "subcategory": "hold_downs",
                    "models": "HDU2, HDU4, HDU8",
                    "dp_pos": None, "dp_neg": None,
                    "missile": None,
                    "structural": "Up to 14,930 lb",
                    "hvhz": True, "large": False, "small": False,
                    "expiration": "2027-06-12"
                },
            ]

            for p in products:
                mfr_id = mfr_ids.get(p["manufacturer"])
                conn.execute("""
                    INSERT INTO product_approvals
                    (manufacturer_id, approval_type, approval_number, product_name,
                     category, subcategory, model_numbers,
                     design_pressure_positive, design_pressure_negative,
                     missile_impact_level, structural_rating,
                     hvhz_approved, large_missile_approved, small_missile_approved,
                     expiration_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (mfr_id, p["type"], p["number"], p["name"],
                      p["category"], p.get("subcategory"), p.get("models"),
                      p.get("dp_pos"), p.get("dp_neg"),
                      p.get("missile"), p.get("structural"),
                      p.get("hvhz", True), p.get("large", False), p.get("small", False),
                      p.get("expiration")))

            conn.commit()

    # =========================================================================
    # QUERY METHODS
    # =========================================================================

    def search_products(
        self,
        category: str = None,
        manufacturer: str = None,
        approval_number: str = None,
        min_design_pressure: float = None,
        large_missile_required: bool = False,
        active_only: bool = True
    ) -> List[Dict]:
        """Search for approved products"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = """
                SELECT pa.*, m.name as manufacturer_name
                FROM product_approvals pa
                LEFT JOIN manufacturers m ON pa.manufacturer_id = m.id
                WHERE 1=1
            """
            params = []

            if category:
                query += " AND pa.category = ?"
                params.append(category)

            if manufacturer:
                query += " AND m.name LIKE ?"
                params.append(f"%{manufacturer}%")

            if approval_number:
                query += " AND pa.approval_number LIKE ?"
                params.append(f"%{approval_number}%")

            if min_design_pressure:
                query += " AND pa.design_pressure_negative <= ?"
                params.append(-abs(min_design_pressure))

            if large_missile_required:
                query += " AND pa.large_missile_approved = 1"

            if active_only:
                query += " AND pa.active = 1"

            query += " ORDER BY m.name, pa.product_name"

            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_product(self, product_id: int = None, approval_number: str = None) -> Optional[Dict]:
        """Get product by ID or approval number"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if product_id:
                row = conn.execute("""
                    SELECT pa.*, m.name as manufacturer_name, m.website, m.phone
                    FROM product_approvals pa
                    LEFT JOIN manufacturers m ON pa.manufacturer_id = m.id
                    WHERE pa.id = ?
                """, (product_id,)).fetchone()
            elif approval_number:
                row = conn.execute("""
                    SELECT pa.*, m.name as manufacturer_name, m.website, m.phone
                    FROM product_approvals pa
                    LEFT JOIN manufacturers m ON pa.manufacturer_id = m.id
                    WHERE pa.approval_number LIKE ?
                """, (f"%{approval_number}%",)).fetchone()
            else:
                return None

            return dict(row) if row else None

    def get_categories(self) -> List[str]:
        """Get all product categories"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT DISTINCT category FROM product_approvals
                ORDER BY category
            """).fetchall()
            return [r[0] for r in rows]

    def get_manufacturers(self) -> List[Dict]:
        """Get all manufacturers"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT m.*, COUNT(pa.id) as product_count
                FROM manufacturers m
                LEFT JOIN product_approvals pa ON m.id = pa.manufacturer_id
                GROUP BY m.id
                ORDER BY m.name
            """).fetchall()
            return [dict(r) for r in rows]

    def check_expiring_approvals(self, days: int = 90) -> List[Dict]:
        """Get products with approvals expiring soon"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cutoff = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

            rows = conn.execute("""
                SELECT pa.*, m.name as manufacturer_name
                FROM product_approvals pa
                LEFT JOIN manufacturers m ON pa.manufacturer_id = m.id
                WHERE pa.expiration_date <= ? AND pa.active = 1
                ORDER BY pa.expiration_date
            """, (cutoff,)).fetchall()
            return [dict(r) for r in rows]

    # =========================================================================
    # PROJECT PRODUCT MANAGEMENT
    # =========================================================================

    def add_product_to_project(
        self,
        project_id: int,
        product_approval_id: int,
        location: str = None,
        quantity: int = None,
        spec_section: str = None,
        sheet_reference: str = None
    ) -> int:
        """Add a product selection to a project"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO project_products
                (project_id, product_approval_id, location, quantity,
                 spec_section, sheet_reference)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (project_id, product_approval_id, location, quantity,
                  spec_section, sheet_reference))
            conn.commit()
            return cursor.lastrowid

    def get_project_products(self, project_id: int) -> List[Dict]:
        """Get all products selected for a project"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT pp.*, pa.approval_number, pa.product_name, pa.category,
                       pa.design_pressure_positive, pa.design_pressure_negative,
                       pa.missile_impact_level, pa.expiration_date,
                       m.name as manufacturer_name
                FROM project_products pp
                JOIN product_approvals pa ON pp.product_approval_id = pa.id
                LEFT JOIN manufacturers m ON pa.manufacturer_id = m.id
                WHERE pp.project_id = ?
                ORDER BY pa.category, pa.product_name
            """, (project_id,)).fetchall()
            return [dict(r) for r in rows]

    def generate_product_schedule(self, project_id: int) -> str:
        """Generate a product approval schedule for submittals"""
        products = self.get_project_products(project_id)

        if not products:
            return "No products selected for this project."

        lines = [
            "=" * 70,
            "PRODUCT APPROVAL SCHEDULE",
            "=" * 70,
            f"Project ID: {project_id}",
            f"Generated: {datetime.now().strftime('%B %d, %Y')}",
            "",
            "This schedule lists all Miami-Dade NOA and Florida Product Approvals",
            "for exterior products used on this project.",
            "",
            "-" * 70
        ]

        # Group by category
        categories = {}
        for p in products:
            cat = p['category'].upper().replace('_', ' ')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(p)

        for category, items in sorted(categories.items()):
            lines.append(f"\n{category}")
            lines.append("-" * 40)

            for item in items:
                lines.append(f"\n  Product: {item['product_name']}")
                lines.append(f"  Manufacturer: {item['manufacturer_name']}")
                lines.append(f"  Approval #: {item['approval_number']}")

                if item.get('design_pressure_negative'):
                    lines.append(f"  Design Pressure: +{item['design_pressure_positive']}/-{abs(item['design_pressure_negative'])} psf")

                if item.get('missile_impact_level'):
                    lines.append(f"  Impact Rating: {item['missile_impact_level']}")

                if item.get('location'):
                    lines.append(f"  Location: {item['location']}")

                if item.get('quantity'):
                    lines.append(f"  Quantity: {item['quantity']}")

                if item.get('expiration_date'):
                    lines.append(f"  Approval Expires: {item['expiration_date']}")

        lines.extend([
            "",
            "-" * 70,
            "Note: Verify all NOA numbers are current before permit submittal.",
            "NOA documents available at: https://www.miamidade.gov/permits/product-approval.asp",
            "=" * 70
        ])

        return "\n".join(lines)

    def find_alternatives(self, product_id: int) -> List[Dict]:
        """Find alternative products with similar specifications"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get the product
            product = self.get_product(product_id=product_id)
            if not product:
                return []

            # Find products in same category with similar or better specs
            query = """
                SELECT pa.*, m.name as manufacturer_name
                FROM product_approvals pa
                LEFT JOIN manufacturers m ON pa.manufacturer_id = m.id
                WHERE pa.category = ?
                  AND pa.id != ?
                  AND pa.active = 1
                  AND pa.hvhz_approved = 1
            """
            params = [product['category'], product_id]

            # Match missile rating if required
            if product.get('large_missile_approved'):
                query += " AND pa.large_missile_approved = 1"

            # Match or exceed design pressure
            if product.get('design_pressure_negative'):
                query += " AND pa.design_pressure_negative <= ?"
                params.append(product['design_pressure_negative'])

            query += " ORDER BY m.name, pa.product_name"

            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("NOA/PRODUCT APPROVAL DATABASE")
    print("=" * 70)

    db = NOADatabase()

    # Show categories
    print("\nProduct Categories:")
    for cat in db.get_categories():
        print(f"  - {cat}")

    # Show manufacturers
    print("\n" + "-" * 70)
    print("Manufacturers:")
    print("-" * 70)
    for m in db.get_manufacturers():
        print(f"  {m['name']}: {m['product_count']} products")

    # Search for windows
    print("\n" + "-" * 70)
    print("Impact Windows (Large Missile Approved):")
    print("-" * 70)
    windows = db.search_products(category="windows", large_missile_required=True)
    for w in windows:
        print(f"\n  {w['product_name']}")
        print(f"    Manufacturer: {w['manufacturer_name']}")
        print(f"    NOA: {w['approval_number']}")
        print(f"    Design Pressure: +{w['design_pressure_positive']}/-{abs(w['design_pressure_negative'])} psf")
        print(f"    Impact: {w['missile_impact_level']}")

    # Check expiring approvals
    print("\n" + "-" * 70)
    print("Approvals Expiring in 180 Days:")
    print("-" * 70)
    expiring = db.check_expiring_approvals(days=180)
    for e in expiring:
        print(f"  {e['approval_number']}: {e['product_name']} (expires {e['expiration_date']})")

    # Simulate project product selection
    print("\n" + "-" * 70)
    print("Project Product Schedule Demo:")
    print("-" * 70)

    # Add products to test project
    project_id = 1
    windows = db.search_products(category="windows", large_missile_required=True)
    doors = db.search_products(category="doors", large_missile_required=True)
    shutters = db.search_products(category="shutters")

    if windows:
        db.add_product_to_project(project_id, windows[0]['id'], "All Windows", 45, "08 51 00")
    if doors:
        db.add_product_to_project(project_id, doors[0]['id'], "Entry Doors", 4, "08 11 00")
    if shutters:
        db.add_product_to_project(project_id, shutters[0]['id'], "Hurricane Protection", 20, "10 25 00")

    # Generate schedule
    schedule = db.generate_product_schedule(project_id)
    print(schedule)

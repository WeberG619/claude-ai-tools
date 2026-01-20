"""
Comment Response System
========================
System for managing, responding to, and tracking building department
review comments across all projects and disciplines.

Author: BIM Ops Studio
"""

import sqlite3
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re


class CommentCategory(Enum):
    """Categories of review comments"""
    CODE_COMPLIANCE = "code_compliance"
    DRAWING_CLARITY = "drawing_clarity"
    MISSING_INFO = "missing_info"
    CALCULATION_ERROR = "calculation_error"
    SPECIFICATION = "specification"
    COORDINATION = "coordination"
    PERMIT_REQUIREMENT = "permit_requirement"
    ZONING = "zoning"
    ACCESSIBILITY = "accessibility"
    LIFE_SAFETY = "life_safety"
    STRUCTURAL = "structural"
    MEP = "mep"
    ENERGY = "energy"


class ResponseType(Enum):
    """Types of responses to comments"""
    REVISED = "revised"
    CLARIFICATION = "clarification"
    NO_CHANGE_REQUIRED = "no_change_required"
    DEFERRED = "deferred"
    ALTERNATE_COMPLIANCE = "alternate_compliance"
    ADDITIONAL_INFO = "additional_info"


class CommentResponseSystem:
    """
    Comprehensive system for managing building department review comments
    and generating professional responses.
    """

    def __init__(self, db_path: str = "comment_response.db"):
        self.db_path = db_path
        self._init_database()
        self._populate_templates()

    def _init_database(self):
        """Initialize the database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")

            # Response templates - reusable response patterns
            conn.execute("""
                CREATE TABLE IF NOT EXISTS response_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discipline TEXT NOT NULL,
                    category TEXT NOT NULL,
                    pattern_keywords TEXT,
                    code_section TEXT,
                    response_template TEXT NOT NULL,
                    response_type TEXT NOT NULL,
                    typical_action TEXT,
                    usage_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Project comments - actual comments received
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    cycle_number INTEGER DEFAULT 1,
                    comment_number INTEGER,
                    discipline TEXT NOT NULL,
                    reviewer_name TEXT,
                    code_section TEXT,
                    sheet_reference TEXT,
                    comment_text TEXT NOT NULL,
                    category TEXT,
                    priority TEXT DEFAULT 'normal',
                    status TEXT DEFAULT 'open',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Comment responses - our responses to comments
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comment_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comment_id INTEGER NOT NULL,
                    response_type TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    revised_sheets TEXT,
                    additional_documents TEXT,
                    responded_by TEXT,
                    approved_by TEXT,
                    response_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (comment_id) REFERENCES project_comments(id)
                )
            """)

            # Comment history - track recurrence across cycles
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comment_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    original_comment_id INTEGER,
                    recurring_comment_id INTEGER,
                    similarity_score REAL,
                    notes TEXT,
                    FOREIGN KEY (original_comment_id) REFERENCES project_comments(id),
                    FOREIGN KEY (recurring_comment_id) REFERENCES project_comments(id)
                )
            """)

            # Common issues tracker - lessons learned
            conn.execute("""
                CREATE TABLE IF NOT EXISTS common_issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discipline TEXT NOT NULL,
                    issue_description TEXT NOT NULL,
                    prevention_tip TEXT,
                    code_reference TEXT,
                    occurrence_count INTEGER DEFAULT 1,
                    last_occurred TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    def _populate_templates(self):
        """Populate response templates for common comment types"""
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM response_templates").fetchone()[0]
            if count > 0:
                return

            templates = [
                # =============================================================
                # BUILDING / ARCHITECTURAL
                # =============================================================
                {
                    "discipline": "building",
                    "category": "code_compliance",
                    "keywords": "occupant load, egress",
                    "code": "FBC 1004",
                    "template": "The occupant load calculations have been added to sheet {sheet}. The calculations are based on FBC Table 1004.5 using the appropriate function area factors. Please refer to the revised sheet for complete tabulation.",
                    "type": "revised",
                    "action": "Add occupant load calculations to code compliance sheet"
                },
                {
                    "discipline": "building",
                    "category": "life_safety",
                    "keywords": "exit, travel distance, egress width",
                    "code": "FBC 1017",
                    "template": "Exit travel distances have been verified and documented on {sheet}. All travel distances comply with FBC Section 1017.1 maximum limits. The exit access travel distance from the most remote point is {distance} feet, which is within the {max_distance} feet allowed.",
                    "type": "revised",
                    "action": "Add travel distance annotations to floor plans"
                },
                {
                    "discipline": "building",
                    "category": "accessibility",
                    "keywords": "accessible, ada, wheelchair",
                    "code": "FBC Ch. 11",
                    "template": "Accessibility requirements have been addressed on sheet {sheet}. The design complies with FBC Chapter 11 and ANSI A117.1 standards. {specific_detail}",
                    "type": "revised",
                    "action": "Add accessibility details/dimensions"
                },
                {
                    "discipline": "building",
                    "category": "drawing_clarity",
                    "keywords": "dimension, unclear, scale",
                    "code": None,
                    "template": "Dimensions have been added/clarified on sheet {sheet} as requested. The drawing has been updated at the noted location for improved clarity.",
                    "type": "revised",
                    "action": "Add missing dimensions or improve drawing clarity"
                },
                {
                    "discipline": "building",
                    "category": "missing_info",
                    "keywords": "provide, show, indicate, add",
                    "code": None,
                    "template": "The requested information has been provided on sheet {sheet}. Please refer to the revised drawings.",
                    "type": "revised",
                    "action": "Add missing information to drawings"
                },
                {
                    "discipline": "building",
                    "category": "permit_requirement",
                    "keywords": "noa, product approval, florida product",
                    "code": "FBC 1507",
                    "template": "Miami-Dade NOA approval numbers have been added to the specifications on sheet {sheet}. All exterior products listed comply with HVHZ requirements per FBC Section 1507.",
                    "type": "revised",
                    "action": "Add NOA numbers to specifications"
                },
                {
                    "discipline": "building",
                    "category": "energy",
                    "keywords": "energy, r-value, u-factor, solar heat gain",
                    "code": "FBC Energy",
                    "template": "Energy compliance has been verified using {method} method. The calculations are provided on sheet {sheet}. {specific_detail}",
                    "type": "revised",
                    "action": "Provide energy calculations"
                },

                # =============================================================
                # STRUCTURAL
                # =============================================================
                {
                    "discipline": "structural",
                    "category": "code_compliance",
                    "keywords": "wind, asce 7, design criteria",
                    "code": "ASCE 7-22",
                    "template": "Wind design criteria statement has been added to sheet {sheet} in accordance with ASCE 7-22. Design parameters include: Ultimate Wind Speed = {wind_speed} mph, Exposure Category = {exposure}, Risk Category = {risk_cat}.",
                    "type": "revised",
                    "action": "Add wind design criteria statement"
                },
                {
                    "discipline": "structural",
                    "category": "structural",
                    "keywords": "connection, attachment, anchor",
                    "code": "FBC",
                    "template": "Connection details have been provided on sheet {sheet}. The connection design is based on {load_requirement} and complies with FBC requirements.",
                    "type": "revised",
                    "action": "Provide connection details"
                },
                {
                    "discipline": "structural",
                    "category": "missing_info",
                    "keywords": "foundation, footing, slab",
                    "code": "FBC 1807",
                    "template": "Foundation details have been added to sheet {sheet}. Design is based on soil bearing capacity of {bearing} psf from the geotechnical report dated {geo_date}.",
                    "type": "revised",
                    "action": "Add foundation details"
                },
                {
                    "discipline": "structural",
                    "category": "calculation_error",
                    "keywords": "calculation, verify, check",
                    "code": None,
                    "template": "Calculations have been revised and verified. The corrected calculations are included in the sealed calculation package. See page {page} of the structural calculations.",
                    "type": "revised",
                    "action": "Revise calculations"
                },
                {
                    "discipline": "structural",
                    "category": "permit_requirement",
                    "keywords": "threshold, special inspector",
                    "code": "FBC 1709",
                    "template": "This project meets threshold building criteria per FBC Section 1709. Threshold inspection acknowledgment and Special Inspector qualifications are provided as required.",
                    "type": "additional_info",
                    "action": "Provide threshold building documentation"
                },

                # =============================================================
                # MECHANICAL / HVAC
                # =============================================================
                {
                    "discipline": "mechanical",
                    "category": "code_compliance",
                    "keywords": "ventilation, outdoor air, ashrae",
                    "code": "FMC 401",
                    "template": "Outdoor air ventilation requirements have been calculated per ASHRAE 62.1 and FMC Section 401. Calculations are provided on sheet {sheet}. Minimum OA rate = {cfm} CFM.",
                    "type": "revised",
                    "action": "Provide ventilation calculations"
                },
                {
                    "discipline": "mechanical",
                    "category": "missing_info",
                    "keywords": "equipment schedule, capacity",
                    "code": None,
                    "template": "Equipment schedule has been updated on sheet {sheet} to include {detail}. All equipment capacities and specifications are now shown.",
                    "type": "revised",
                    "action": "Update equipment schedule"
                },
                {
                    "discipline": "mechanical",
                    "category": "coordination",
                    "keywords": "coordinate, conflict, clearance",
                    "code": None,
                    "template": "Coordination between {discipline1} and {discipline2} has been verified. Clearances are adequate and routing has been adjusted as shown on sheet {sheet}.",
                    "type": "revised",
                    "action": "Coordinate with other disciplines"
                },
                {
                    "discipline": "mechanical",
                    "category": "permit_requirement",
                    "keywords": "load calculation, manual j",
                    "code": "FMC 302",
                    "template": "HVAC load calculations have been provided per Manual J methodology. Total cooling load = {cooling_load} BTU/hr, Heating load = {heating_load} BTU/hr. See mechanical calculations.",
                    "type": "additional_info",
                    "action": "Provide load calculations"
                },

                # =============================================================
                # ELECTRICAL
                # =============================================================
                {
                    "discipline": "electrical",
                    "category": "code_compliance",
                    "keywords": "receptacle, outlet, spacing",
                    "code": "NEC 210.52",
                    "template": "Receptacle spacing has been verified and complies with NEC 210.52. Additional outlets have been added on sheet {sheet} as required.",
                    "type": "revised",
                    "action": "Add/relocate receptacles per code"
                },
                {
                    "discipline": "electrical",
                    "category": "missing_info",
                    "keywords": "panel schedule, load calculation",
                    "code": "NEC Article 220",
                    "template": "Panel schedule has been completed on sheet {sheet} with full load calculations per NEC Article 220. Total connected load = {load} VA, Demand load = {demand} VA.",
                    "type": "revised",
                    "action": "Complete panel schedule"
                },
                {
                    "discipline": "electrical",
                    "category": "life_safety",
                    "keywords": "emergency, exit lighting, egress illumination",
                    "code": "NEC 700",
                    "template": "Emergency egress lighting has been provided per NEC Article 700 and FBC 1008.3. Emergency fixtures are indicated on sheet {sheet}.",
                    "type": "revised",
                    "action": "Add emergency lighting"
                },
                {
                    "discipline": "electrical",
                    "category": "code_compliance",
                    "keywords": "gfci, ground fault, arc fault",
                    "code": "NEC 210.8",
                    "template": "GFCI/AFCI protection has been provided per NEC 210.8/210.12. Protected circuits are noted on the panel schedule on sheet {sheet}.",
                    "type": "revised",
                    "action": "Add GFCI/AFCI protection"
                },
                {
                    "discipline": "electrical",
                    "category": "permit_requirement",
                    "keywords": "service, utility, fpl",
                    "code": None,
                    "template": "Coordination with FPL/utility has been completed. Service entrance details are shown on sheet {sheet}. Utility approval letter is included with resubmittal.",
                    "type": "additional_info",
                    "action": "Coordinate with utility"
                },

                # =============================================================
                # PLUMBING
                # =============================================================
                {
                    "discipline": "plumbing",
                    "category": "code_compliance",
                    "keywords": "fixture count, toilet, lavatory",
                    "code": "FPC Table 403",
                    "template": "Plumbing fixture count has been verified per FPC Table 403.1. Required fixtures based on occupant load: {fixture_count}. See calculation on sheet {sheet}.",
                    "type": "revised",
                    "action": "Verify fixture count"
                },
                {
                    "discipline": "plumbing",
                    "category": "missing_info",
                    "keywords": "riser diagram, isometric",
                    "code": None,
                    "template": "Plumbing riser diagram has been provided on sheet {sheet}, showing all supply, waste, and vent piping with sizes as required.",
                    "type": "revised",
                    "action": "Provide riser diagram"
                },
                {
                    "discipline": "plumbing",
                    "category": "code_compliance",
                    "keywords": "water heater, expansion tank",
                    "code": "FPC 608",
                    "template": "Thermal expansion tank has been added to the water heater installation per FPC 608.3. See detail on sheet {sheet}.",
                    "type": "revised",
                    "action": "Add expansion tank"
                },
                {
                    "discipline": "plumbing",
                    "category": "permit_requirement",
                    "keywords": "backflow, cross connection",
                    "code": "FPC 608",
                    "template": "Backflow prevention has been provided per FPC 608. Device type and location are shown on sheet {sheet}. Backflow preventer schedule is included.",
                    "type": "revised",
                    "action": "Add backflow prevention"
                },

                # =============================================================
                # FIRE PROTECTION / LIFE SAFETY
                # =============================================================
                {
                    "discipline": "fire",
                    "category": "life_safety",
                    "keywords": "sprinkler, fire suppression, nfpa 13",
                    "code": "NFPA 13",
                    "template": "Fire sprinkler system has been designed per NFPA 13 requirements. Hydraulic calculations and coverage diagrams are provided on sheet {sheet}.",
                    "type": "revised",
                    "action": "Provide sprinkler design"
                },
                {
                    "discipline": "fire",
                    "category": "life_safety",
                    "keywords": "fire alarm, detection, notification",
                    "code": "NFPA 72",
                    "template": "Fire alarm system design complies with NFPA 72. Device layout and zoning diagram are shown on sheet {sheet}. Battery calculations are included.",
                    "type": "revised",
                    "action": "Provide fire alarm design"
                },
                {
                    "discipline": "fire",
                    "category": "code_compliance",
                    "keywords": "fire rating, separation, wall assembly",
                    "code": "FBC 706",
                    "template": "Fire-rated assembly details have been provided on sheet {sheet}. Assembly type: {assembly_type}, Fire Rating: {rating} hours. UL design number: {ul_number}.",
                    "type": "revised",
                    "action": "Provide fire-rated assembly details"
                },
                {
                    "discipline": "fire",
                    "category": "permit_requirement",
                    "keywords": "fire flow, hydrant",
                    "code": None,
                    "template": "Fire flow requirements have been verified with the local fire department. Required fire flow = {flow} GPM. Fire hydrant locations are shown on sheet {sheet}.",
                    "type": "additional_info",
                    "action": "Verify fire flow"
                },

                # =============================================================
                # ZONING
                # =============================================================
                {
                    "discipline": "zoning",
                    "category": "zoning",
                    "keywords": "setback, yard, lot coverage",
                    "code": None,
                    "template": "Setback dimensions have been clarified on sheet {sheet}. The proposed setbacks comply with the zoning requirements for the {zoning_district} district. {specific_detail}",
                    "type": "revised",
                    "action": "Add setback dimensions"
                },
                {
                    "discipline": "zoning",
                    "category": "zoning",
                    "keywords": "height, story, building height",
                    "code": None,
                    "template": "Building height has been verified and shown on sheet {sheet}. Maximum height = {max_height}, Proposed height = {proposed_height}. The building complies with zoning height limits.",
                    "type": "revised",
                    "action": "Clarify building height"
                },
                {
                    "discipline": "zoning",
                    "category": "zoning",
                    "keywords": "parking, parking space, ada parking",
                    "code": None,
                    "template": "Parking calculations have been provided on sheet {sheet}. Required spaces: {required}, Provided spaces: {provided} (including {ada} ADA spaces). Parking complies with zoning requirements.",
                    "type": "revised",
                    "action": "Provide parking calculations"
                },

                # =============================================================
                # CLARIFICATION / NO CHANGE RESPONSES
                # =============================================================
                {
                    "discipline": "general",
                    "category": "drawing_clarity",
                    "keywords": "see, refer, shown",
                    "code": None,
                    "template": "The requested information is shown on sheet {sheet}, {detail_location}. No changes to drawings required - please refer to the noted location.",
                    "type": "clarification",
                    "action": "Provide clarification"
                },
                {
                    "discipline": "general",
                    "category": "code_compliance",
                    "keywords": "alternate, variance, equivalent",
                    "code": None,
                    "template": "An alternate means of compliance is proposed per FBC Section 104.11. The proposed alternate method provides equivalent {safety/performance} through {description}. Supporting documentation is attached.",
                    "type": "alternate_compliance",
                    "action": "Request alternate compliance"
                }
            ]

            for t in templates:
                conn.execute("""
                    INSERT INTO response_templates
                    (discipline, category, pattern_keywords, code_section,
                     response_template, response_type, typical_action)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (t["discipline"], t["category"], t.get("keywords"),
                      t.get("code"), t["template"], t["type"], t.get("action")))

            conn.commit()

    # =========================================================================
    # COMMENT MANAGEMENT
    # =========================================================================

    def add_project_comment(
        self,
        project_id: int,
        discipline: str,
        comment_text: str,
        cycle_number: int = 1,
        code_section: str = None,
        sheet_reference: str = None,
        reviewer_name: str = None,
        priority: str = "normal"
    ) -> int:
        """Add a review comment to a project"""
        with sqlite3.connect(self.db_path) as conn:
            # Get next comment number for this cycle
            result = conn.execute("""
                SELECT COALESCE(MAX(comment_number), 0) + 1
                FROM project_comments
                WHERE project_id = ? AND cycle_number = ?
            """, (project_id, cycle_number)).fetchone()
            comment_num = result[0]

            # Auto-categorize the comment
            category = self._categorize_comment(comment_text, discipline)

            cursor = conn.execute("""
                INSERT INTO project_comments
                (project_id, cycle_number, comment_number, discipline, reviewer_name,
                 code_section, sheet_reference, comment_text, category, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (project_id, cycle_number, comment_num, discipline, reviewer_name,
                  code_section, sheet_reference, comment_text, category, priority))

            conn.commit()
            return cursor.lastrowid

    def _categorize_comment(self, comment_text: str, discipline: str) -> str:
        """Auto-categorize a comment based on keywords"""
        text_lower = comment_text.lower()

        category_keywords = {
            "code_compliance": ["code", "comply", "compliance", "fbc", "nec", "nfpa", "asce"],
            "life_safety": ["egress", "exit", "fire", "emergency", "life safety", "smoke"],
            "accessibility": ["accessible", "ada", "handicap", "wheelchair", "grab bar"],
            "missing_info": ["provide", "show", "add", "include", "missing", "indicate"],
            "drawing_clarity": ["dimension", "scale", "unclear", "clarify", "label", "note"],
            "calculation_error": ["calculation", "verify", "check", "error", "incorrect"],
            "coordination": ["coordinate", "conflict", "match", "consistent"],
            "structural": ["structural", "foundation", "footing", "connection", "load"],
            "mep": ["hvac", "duct", "pipe", "electrical", "mechanical", "plumbing"],
            "energy": ["energy", "insulation", "r-value", "u-factor", "envelope"],
            "zoning": ["setback", "height", "parking", "lot coverage", "zoning"]
        }

        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category

        return "general"

    def add_batch_comments(
        self,
        project_id: int,
        comments: List[Dict],
        cycle_number: int = 1
    ) -> List[int]:
        """Add multiple comments at once"""
        comment_ids = []
        for comment in comments:
            comment_id = self.add_project_comment(
                project_id=project_id,
                discipline=comment.get("discipline", "building"),
                comment_text=comment["text"],
                cycle_number=cycle_number,
                code_section=comment.get("code_section"),
                sheet_reference=comment.get("sheet_reference"),
                reviewer_name=comment.get("reviewer_name"),
                priority=comment.get("priority", "normal")
            )
            comment_ids.append(comment_id)
        return comment_ids

    def get_project_comments(
        self,
        project_id: int,
        cycle_number: int = None,
        discipline: str = None,
        status: str = None
    ) -> List[Dict]:
        """Get comments for a project with optional filters"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM project_comments WHERE project_id = ?"
            params = [project_id]

            if cycle_number:
                query += " AND cycle_number = ?"
                params.append(cycle_number)
            if discipline:
                query += " AND discipline = ?"
                params.append(discipline)
            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY cycle_number, comment_number"

            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    # =========================================================================
    # RESPONSE GENERATION
    # =========================================================================

    def suggest_response(self, comment_id: int) -> List[Dict]:
        """Suggest response templates based on comment content"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get the comment
            comment = conn.execute("""
                SELECT * FROM project_comments WHERE id = ?
            """, (comment_id,)).fetchone()

            if not comment:
                return []

            comment = dict(comment)
            comment_lower = comment['comment_text'].lower()
            discipline = comment['discipline']

            # Find matching templates
            templates = conn.execute("""
                SELECT * FROM response_templates
                WHERE (discipline = ? OR discipline = 'general')
                ORDER BY usage_count DESC
            """, (discipline,)).fetchall()

            suggestions = []
            for template in templates:
                template = dict(template)
                keywords = template.get('pattern_keywords', '')
                if keywords:
                    keyword_list = [k.strip() for k in keywords.split(',')]
                    matches = sum(1 for k in keyword_list if k in comment_lower)
                    if matches > 0:
                        template['match_score'] = matches
                        suggestions.append(template)

            # Sort by match score
            suggestions.sort(key=lambda x: x.get('match_score', 0), reverse=True)
            return suggestions[:5]  # Return top 5 suggestions

    def add_response(
        self,
        comment_id: int,
        response_type: str,
        response_text: str,
        revised_sheets: str = None,
        additional_documents: str = None,
        responded_by: str = None
    ) -> int:
        """Add a response to a comment"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO comment_responses
                (comment_id, response_type, response_text, revised_sheets,
                 additional_documents, responded_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (comment_id, response_type, response_text, revised_sheets,
                  additional_documents, responded_by))

            # Update comment status
            conn.execute("""
                UPDATE project_comments
                SET status = 'responded', updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), comment_id))

            conn.commit()
            return cursor.lastrowid

    def get_response(self, comment_id: int) -> Optional[Dict]:
        """Get response for a comment"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM comment_responses WHERE comment_id = ?
            """, (comment_id,)).fetchone()
            return dict(row) if row else None

    # =========================================================================
    # LETTER GENERATION
    # =========================================================================

    def generate_response_letter(
        self,
        project_id: int,
        cycle_number: int,
        project_name: str = None,
        project_address: str = None,
        permit_number: str = None,
        preparer_name: str = None,
        company_name: str = None
    ) -> str:
        """Generate a formal response letter for all comments in a cycle"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get all comments and responses for this cycle
            rows = conn.execute("""
                SELECT pc.*, cr.response_type, cr.response_text, cr.revised_sheets
                FROM project_comments pc
                LEFT JOIN comment_responses cr ON pc.id = cr.comment_id
                WHERE pc.project_id = ? AND pc.cycle_number = ?
                ORDER BY pc.discipline, pc.comment_number
            """, (project_id, cycle_number)).fetchall()

            if not rows:
                return "No comments found for this review cycle."

            comments_by_discipline = {}
            for row in rows:
                row = dict(row)
                discipline = row['discipline'].upper()
                if discipline not in comments_by_discipline:
                    comments_by_discipline[discipline] = []
                comments_by_discipline[discipline].append(row)

            # Build letter
            lines = [
                "=" * 70,
                "RESPONSE TO PLAN REVIEW COMMENTS",
                "=" * 70,
                "",
                f"Date: {datetime.now().strftime('%B %d, %Y')}",
                ""
            ]

            if project_name:
                lines.append(f"Project: {project_name}")
            if project_address:
                lines.append(f"Address: {project_address}")
            if permit_number:
                lines.append(f"Permit #: {permit_number}")

            lines.extend([
                f"Review Cycle: {cycle_number}",
                "",
                "=" * 70,
                ""
            ])

            # Add responses by discipline
            for discipline, comments in sorted(comments_by_discipline.items()):
                lines.append(f"{discipline} REVIEW COMMENTS")
                lines.append("-" * 50)
                lines.append("")

                for comment in comments:
                    lines.append(f"Comment #{comment['comment_number']}:")
                    if comment.get('code_section'):
                        lines.append(f"Code Reference: {comment['code_section']}")
                    if comment.get('sheet_reference'):
                        lines.append(f"Sheet Reference: {comment['sheet_reference']}")
                    lines.append(f"Comment: {comment['comment_text']}")
                    lines.append("")

                    if comment.get('response_text'):
                        response_type = comment.get('response_type', 'revised').upper()
                        lines.append(f"RESPONSE ({response_type}):")
                        lines.append(comment['response_text'])
                        if comment.get('revised_sheets'):
                            lines.append(f"Revised Sheets: {comment['revised_sheets']}")
                    else:
                        lines.append("RESPONSE: [Pending]")

                    lines.append("")
                    lines.append("-" * 30)
                    lines.append("")

                lines.append("")

            # Summary
            total_comments = sum(len(c) for c in comments_by_discipline.values())
            responded = sum(1 for d in comments_by_discipline.values()
                          for c in d if c.get('response_text'))

            lines.extend([
                "=" * 70,
                "SUMMARY",
                "=" * 70,
                f"Total Comments: {total_comments}",
                f"Responses Provided: {responded}",
                f"Pending: {total_comments - responded}",
                ""
            ])

            if preparer_name:
                lines.extend([
                    "Prepared by:",
                    preparer_name
                ])
            if company_name:
                lines.append(company_name)

            return "\n".join(lines)

    # =========================================================================
    # ANALYTICS & TRACKING
    # =========================================================================

    def get_comment_statistics(self, project_id: int = None) -> Dict:
        """Get statistics about comments"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query_filter = "WHERE project_id = ?" if project_id else ""
            params = (project_id,) if project_id else ()

            # Total comments
            total = conn.execute(f"""
                SELECT COUNT(*) FROM project_comments {query_filter}
            """, params).fetchone()[0]

            # By status
            by_status = {}
            for row in conn.execute(f"""
                SELECT status, COUNT(*) as count FROM project_comments
                {query_filter} GROUP BY status
            """, params).fetchall():
                by_status[row['status']] = row['count']

            # By discipline
            by_discipline = {}
            for row in conn.execute(f"""
                SELECT discipline, COUNT(*) as count FROM project_comments
                {query_filter} GROUP BY discipline ORDER BY count DESC
            """, params).fetchall():
                by_discipline[row['discipline']] = row['count']

            # By category
            by_category = {}
            for row in conn.execute(f"""
                SELECT category, COUNT(*) as count FROM project_comments
                {query_filter} GROUP BY category ORDER BY count DESC
            """, params).fetchall():
                by_category[row['category']] = row['count']

            return {
                "total_comments": total,
                "by_status": by_status,
                "by_discipline": by_discipline,
                "by_category": by_category
            }

    def track_common_issue(
        self,
        discipline: str,
        issue_description: str,
        prevention_tip: str = None,
        code_reference: str = None
    ) -> int:
        """Track a common issue for lessons learned"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if similar issue exists
            existing = conn.execute("""
                SELECT id, occurrence_count FROM common_issues
                WHERE discipline = ? AND issue_description = ?
            """, (discipline, issue_description)).fetchone()

            if existing:
                conn.execute("""
                    UPDATE common_issues
                    SET occurrence_count = occurrence_count + 1,
                        last_occurred = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), existing[0]))
                conn.commit()
                return existing[0]
            else:
                cursor = conn.execute("""
                    INSERT INTO common_issues
                    (discipline, issue_description, prevention_tip,
                     code_reference, last_occurred)
                    VALUES (?, ?, ?, ?, ?)
                """, (discipline, issue_description, prevention_tip,
                      code_reference, datetime.now().isoformat()))
                conn.commit()
                return cursor.lastrowid

    def get_common_issues(self, discipline: str = None, limit: int = 10) -> List[Dict]:
        """Get most common issues"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM common_issues"
            params = []

            if discipline:
                query += " WHERE discipline = ?"
                params.append(discipline)

            query += " ORDER BY occurrence_count DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]


# =============================================================================
# STANDALONE TEST
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("COMMENT RESPONSE SYSTEM")
    print("=" * 70)

    # Initialize system
    system = CommentResponseSystem()

    # Simulate a project review
    project_id = 1

    # Add comments from building department
    print("\nAdding review comments...")
    comments = [
        {
            "discipline": "building",
            "text": "Provide occupant load calculations on A-100",
            "code_section": "FBC 1004.1",
            "sheet_reference": "A-100"
        },
        {
            "discipline": "structural",
            "text": "Show wind design criteria statement on cover sheet per ASCE 7-22",
            "code_section": "ASCE 7-22",
            "sheet_reference": "S-001"
        },
        {
            "discipline": "electrical",
            "text": "Add GFCI protection to kitchen receptacles",
            "code_section": "NEC 210.8",
            "sheet_reference": "E-101"
        },
        {
            "discipline": "mechanical",
            "text": "Provide outdoor air ventilation calculations",
            "code_section": "FMC 401",
            "sheet_reference": "M-001"
        },
        {
            "discipline": "plumbing",
            "text": "Show fixture count based on occupant load",
            "code_section": "FPC Table 403",
            "sheet_reference": "P-001"
        }
    ]

    comment_ids = system.add_batch_comments(project_id, comments, cycle_number=1)
    print(f"  Added {len(comment_ids)} comments")

    # Get suggested responses
    print("\n" + "-" * 70)
    print("SUGGESTED RESPONSES")
    print("-" * 70)
    for comment_id in comment_ids[:2]:
        suggestions = system.suggest_response(comment_id)
        comments_list = system.get_project_comments(project_id)
        comment = next((c for c in comments_list if c['id'] == comment_id), None)
        if comment:
            print(f"\nComment: {comment['comment_text']}")
            print(f"Category: {comment['category']}")
            if suggestions:
                print(f"Suggested Response Template:")
                print(f"  {suggestions[0]['response_template'][:100]}...")

    # Add responses
    print("\n" + "-" * 70)
    print("ADDING RESPONSES")
    print("-" * 70)

    system.add_response(
        comment_ids[0],
        "revised",
        "The occupant load calculations have been added to sheet A-100. The calculations are based on FBC Table 1004.5 using the appropriate function area factors.",
        revised_sheets="A-100",
        responded_by="John Architect"
    )

    system.add_response(
        comment_ids[1],
        "revised",
        "Wind design criteria statement has been added to sheet S-001. Design parameters: Ultimate Wind Speed = 195 mph, Exposure Category = C, Risk Category II.",
        revised_sheets="S-001",
        responded_by="Jane Engineer"
    )

    print("  Added 2 responses")

    # Generate response letter
    print("\n")
    letter = system.generate_response_letter(
        project_id=project_id,
        cycle_number=1,
        project_name="Test Commercial Building",
        project_address="123 Main Street, Miami, FL 33101",
        permit_number="BD-2024-12345",
        preparer_name="John Architect, AIA",
        company_name="ABC Architecture, Inc."
    )
    print(letter)

    # Show statistics
    print("\n" + "-" * 70)
    print("COMMENT STATISTICS")
    print("-" * 70)
    stats = system.get_comment_statistics(project_id)
    print(f"Total Comments: {stats['total_comments']}")
    print(f"By Status: {stats['by_status']}")
    print(f"By Discipline: {stats['by_discipline']}")
    print(f"By Category: {stats['by_category']}")

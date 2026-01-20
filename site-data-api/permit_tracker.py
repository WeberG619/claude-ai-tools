#!/usr/bin/env python3
"""
Permit Application Tracker

Tracks permit applications through the building department process:
- Multiple permit types per project
- Submission and review tracking
- Document requirements
- Review comments and responses
- Fee tracking
- Timeline management
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


# Database path
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "permit_tracker.db")


class PermitType(Enum):
    BUILDING = "building"
    ELECTRICAL = "electrical"
    MECHANICAL = "mechanical"
    PLUMBING = "plumbing"
    ROOFING = "roofing"
    FIRE_ALARM = "fire_alarm"
    FIRE_SPRINKLER = "fire_sprinkler"
    DEMOLITION = "demolition"
    SITEWORK = "sitework"
    SIGN = "sign"
    FENCE = "fence"
    POOL = "pool"
    SHELL = "shell"
    TENANT_IMPROVEMENT = "tenant_improvement"
    FOUNDATION_ONLY = "foundation_only"


class PermitStatus(Enum):
    DRAFT = "draft"
    READY_TO_SUBMIT = "ready_to_submit"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    CORRECTIONS_REQUIRED = "corrections_required"
    RESUBMITTED = "resubmitted"
    APPROVED = "approved"
    ISSUED = "issued"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class ReviewCycle(Enum):
    FIRST_REVIEW = "first_review"
    SECOND_REVIEW = "second_review"
    THIRD_REVIEW = "third_review"
    FOURTH_PLUS = "fourth_plus"


@dataclass
class PermitApplication:
    """Permit application record"""
    id: int
    project_id: int
    permit_type: str
    permit_number: Optional[str]
    jurisdiction: str
    status: str
    current_review_cycle: int
    submission_date: Optional[str]
    approval_date: Optional[str]
    expiration_date: Optional[str]
    estimated_fee: Optional[float]
    actual_fee: Optional[float]
    contractor_name: Optional[str]
    contractor_license: Optional[str]
    notes: str


class PermitTracker:
    """
    Permit Application Tracking System

    Manages permit applications from draft through issuance.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Permit applications
            conn.execute("""
                CREATE TABLE IF NOT EXISTS permit_applications (
                    id INTEGER PRIMARY KEY,
                    project_id INTEGER NOT NULL,
                    permit_type TEXT NOT NULL,
                    permit_number TEXT,
                    jurisdiction TEXT NOT NULL,
                    status TEXT DEFAULT 'draft',
                    current_review_cycle INTEGER DEFAULT 0,
                    submission_date TEXT,
                    target_approval_date TEXT,
                    approval_date TEXT,
                    issue_date TEXT,
                    expiration_date TEXT,
                    estimated_fee REAL,
                    actual_fee REAL,
                    contractor_name TEXT,
                    contractor_license TEXT,
                    private_provider TEXT,
                    private_provider_number TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Required documents for each permit
            conn.execute("""
                CREATE TABLE IF NOT EXISTS required_documents (
                    id INTEGER PRIMARY KEY,
                    permit_id INTEGER NOT NULL,
                    document_name TEXT NOT NULL,
                    document_type TEXT,  -- plans, calculations, forms, etc.
                    required INTEGER DEFAULT 1,
                    received INTEGER DEFAULT 0,
                    received_date TEXT,
                    notes TEXT,
                    FOREIGN KEY (permit_id) REFERENCES permit_applications(id)
                )
            """)

            # Submissions (each time plans are submitted)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY,
                    permit_id INTEGER NOT NULL,
                    submission_number INTEGER NOT NULL,
                    submission_date TEXT NOT NULL,
                    submission_type TEXT,  -- initial, resubmission, revision
                    submitted_by TEXT,
                    tracking_number TEXT,
                    notes TEXT,
                    FOREIGN KEY (permit_id) REFERENCES permit_applications(id)
                )
            """)

            # Review cycles
            conn.execute("""
                CREATE TABLE IF NOT EXISTS review_cycles (
                    id INTEGER PRIMARY KEY,
                    permit_id INTEGER NOT NULL,
                    cycle_number INTEGER NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    status TEXT,  -- in_progress, complete_approved, complete_corrections
                    reviewer_name TEXT,
                    review_discipline TEXT,  -- building, structural, fire, etc.
                    FOREIGN KEY (permit_id) REFERENCES permit_applications(id)
                )
            """)

            # Review comments
            conn.execute("""
                CREATE TABLE IF NOT EXISTS review_comments (
                    id INTEGER PRIMARY KEY,
                    review_cycle_id INTEGER NOT NULL,
                    comment_number INTEGER,
                    discipline TEXT NOT NULL,
                    code_section TEXT,
                    comment_text TEXT NOT NULL,
                    sheet_reference TEXT,
                    response_text TEXT,
                    response_date TEXT,
                    resolved INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (review_cycle_id) REFERENCES review_cycles(id)
                )
            """)

            # Inspections
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inspections (
                    id INTEGER PRIMARY KEY,
                    permit_id INTEGER NOT NULL,
                    inspection_type TEXT NOT NULL,
                    scheduled_date TEXT,
                    actual_date TEXT,
                    inspector_name TEXT,
                    result TEXT,  -- pass, fail, partial
                    comments TEXT,
                    reinspection_required INTEGER DEFAULT 0,
                    FOREIGN KEY (permit_id) REFERENCES permit_applications(id)
                )
            """)

            # Fee payments
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fee_payments (
                    id INTEGER PRIMARY KEY,
                    permit_id INTEGER NOT NULL,
                    fee_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    payment_date TEXT,
                    payment_method TEXT,
                    receipt_number TEXT,
                    notes TEXT,
                    FOREIGN KEY (permit_id) REFERENCES permit_applications(id)
                )
            """)

            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_permits_project ON permit_applications(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_permits_status ON permit_applications(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_comments_resolved ON review_comments(resolved)")

            conn.commit()

    # =========================================================================
    # PERMIT APPLICATION OPERATIONS
    # =========================================================================

    def create_permit_application(
        self,
        project_id: int,
        permit_type: str,
        jurisdiction: str,
        contractor_name: str = None,
        contractor_license: str = None,
        private_provider: str = None,
        estimated_fee: float = None,
        notes: str = None
    ) -> int:
        """Create a new permit application"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO permit_applications
                (project_id, permit_type, jurisdiction, contractor_name,
                 contractor_license, private_provider, estimated_fee, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (project_id, permit_type, jurisdiction, contractor_name,
                  contractor_license, private_provider, estimated_fee, notes))
            permit_id = cursor.lastrowid

            # Add standard required documents based on permit type
            self._add_standard_documents(conn, permit_id, permit_type, jurisdiction)

            conn.commit()
            return permit_id

    def _add_standard_documents(self, conn, permit_id: int, permit_type: str, jurisdiction: str):
        """Add standard required documents for permit type"""
        # Standard documents by permit type
        standard_docs = {
            "building": [
                ("Architectural Plans", "plans"),
                ("Structural Plans", "plans"),
                ("Site Plan", "plans"),
                ("Energy Calculations", "calculations"),
                ("Building Permit Application", "forms"),
                ("Owner Authorization", "forms"),
                ("Contractor License Copy", "forms"),
                ("Product Approvals (NOA)", "approvals"),
                ("Survey", "survey"),
            ],
            "electrical": [
                ("Electrical Plans", "plans"),
                ("Load Calculations", "calculations"),
                ("Electrical Permit Application", "forms"),
                ("Panel Schedule", "plans"),
            ],
            "mechanical": [
                ("Mechanical Plans", "plans"),
                ("HVAC Load Calculations", "calculations"),
                ("Mechanical Permit Application", "forms"),
                ("Equipment Specifications", "specifications"),
            ],
            "plumbing": [
                ("Plumbing Plans", "plans"),
                ("Plumbing Permit Application", "forms"),
                ("Fixture Schedule", "plans"),
            ],
            "roofing": [
                ("Roofing Plans", "plans"),
                ("Roofing Permit Application", "forms"),
                ("Product Approvals (NOA)", "approvals"),
                ("Roof Deck Attachment Schedule", "plans"),
            ],
            "fire_alarm": [
                ("Fire Alarm Plans", "plans"),
                ("Fire Alarm Permit Application", "forms"),
                ("Device Specifications", "specifications"),
                ("Battery Calculations", "calculations"),
            ],
            "fire_sprinkler": [
                ("Sprinkler Plans", "plans"),
                ("Hydraulic Calculations", "calculations"),
                ("Fire Sprinkler Permit Application", "forms"),
            ],
        }

        docs = standard_docs.get(permit_type, [])

        # Add Miami-Dade specific docs
        if "Miami-Dade" in jurisdiction:
            if permit_type == "building":
                docs.extend([
                    ("Miami-Dade NOA Schedule", "approvals"),
                    ("Wind Design Criteria Statement", "forms"),
                    ("HVHZ Roof Attachment Details", "plans"),
                ])

        for doc_name, doc_type in docs:
            conn.execute("""
                INSERT INTO required_documents (permit_id, document_name, document_type)
                VALUES (?, ?, ?)
            """, (permit_id, doc_name, doc_type))

    def get_permit(self, permit_id: int) -> Optional[Dict]:
        """Get permit application details"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            permit = conn.execute("""
                SELECT * FROM permit_applications WHERE id = ?
            """, (permit_id,)).fetchone()

            if not permit:
                return None

            permit = dict(permit)

            # Get required documents
            docs = conn.execute("""
                SELECT * FROM required_documents WHERE permit_id = ?
            """, (permit_id,)).fetchall()
            permit['documents'] = [dict(d) for d in docs]

            # Get submissions
            subs = conn.execute("""
                SELECT * FROM submissions WHERE permit_id = ? ORDER BY submission_number
            """, (permit_id,)).fetchall()
            permit['submissions'] = [dict(s) for s in subs]

            # Get review cycles
            cycles = conn.execute("""
                SELECT * FROM review_cycles WHERE permit_id = ? ORDER BY cycle_number
            """, (permit_id,)).fetchall()
            permit['review_cycles'] = [dict(c) for c in cycles]

            # Get unresolved comment count
            unresolved = conn.execute("""
                SELECT COUNT(*) as count FROM review_comments rc
                JOIN review_cycles cy ON rc.review_cycle_id = cy.id
                WHERE cy.permit_id = ? AND rc.resolved = 0
            """, (permit_id,)).fetchone()
            permit['unresolved_comments'] = unresolved['count']

            # Get inspections
            inspections = conn.execute("""
                SELECT * FROM inspections WHERE permit_id = ? ORDER BY scheduled_date
            """, (permit_id,)).fetchall()
            permit['inspections'] = [dict(i) for i in inspections]

            return permit

    def update_permit_status(
        self,
        permit_id: int,
        status: str,
        permit_number: str = None,
        notes: str = None,
        _conn: sqlite3.Connection = None
    ) -> bool:
        """Update permit status

        Args:
            _conn: Internal use - pass existing connection to avoid locks
        """
        # Use existing connection or create new one
        conn = _conn if _conn else sqlite3.connect(self.db_path)
        try:
            updates = ["status = ?", "updated_at = ?"]
            params = [status, datetime.now().isoformat()]

            if permit_number:
                updates.append("permit_number = ?")
                params.append(permit_number)

            if notes:
                updates.append("notes = ?")
                params.append(notes)

            # Set dates based on status
            if status == "submitted":
                updates.append("submission_date = COALESCE(submission_date, ?)")
                params.append(datetime.now().isoformat())
            elif status == "approved":
                updates.append("approval_date = ?")
                params.append(datetime.now().isoformat())
            elif status == "issued":
                updates.append("issue_date = ?")
                params.append(datetime.now().isoformat())
                # Set expiration (typically 1 year from issue in Florida)
                updates.append("expiration_date = ?")
                params.append((datetime.now() + timedelta(days=365)).isoformat())

            params.append(permit_id)

            conn.execute(f"""
                UPDATE permit_applications
                SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            # Only commit if we own the connection
            if not _conn:
                conn.commit()
            return True
        finally:
            # Only close if we created the connection
            if not _conn:
                conn.close()

    # =========================================================================
    # SUBMISSION TRACKING
    # =========================================================================

    def record_submission(
        self,
        permit_id: int,
        submission_type: str = "initial",
        submitted_by: str = None,
        tracking_number: str = None,
        notes: str = None
    ) -> int:
        """Record a plan submission"""
        with sqlite3.connect(self.db_path) as conn:
            # Get next submission number
            result = conn.execute("""
                SELECT COALESCE(MAX(submission_number), 0) + 1 as next_num
                FROM submissions WHERE permit_id = ?
            """, (permit_id,)).fetchone()
            submission_num = result[0]

            cursor = conn.execute("""
                INSERT INTO submissions
                (permit_id, submission_number, submission_date, submission_type,
                 submitted_by, tracking_number, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (permit_id, submission_num, datetime.now().isoformat(),
                  submission_type, submitted_by, tracking_number, notes))

            # Update permit status (pass connection to avoid lock)
            if submission_type == "initial":
                self.update_permit_status(permit_id, "submitted", _conn=conn)
            else:
                self.update_permit_status(permit_id, "resubmitted", _conn=conn)

            conn.commit()
            return cursor.lastrowid

    # =========================================================================
    # REVIEW CYCLE TRACKING
    # =========================================================================

    def start_review_cycle(
        self,
        permit_id: int,
        review_discipline: str = None
    ) -> int:
        """Start a new review cycle"""
        with sqlite3.connect(self.db_path) as conn:
            # Get next cycle number
            result = conn.execute("""
                SELECT COALESCE(MAX(cycle_number), 0) + 1 as next_num
                FROM review_cycles WHERE permit_id = ?
            """, (permit_id,)).fetchone()
            cycle_num = result[0]

            cursor = conn.execute("""
                INSERT INTO review_cycles
                (permit_id, cycle_number, start_date, status, review_discipline)
                VALUES (?, ?, ?, 'in_progress', ?)
            """, (permit_id, cycle_num, datetime.now().isoformat(), review_discipline))

            # Update permit
            conn.execute("""
                UPDATE permit_applications
                SET status = 'in_review', current_review_cycle = ?, updated_at = ?
                WHERE id = ?
            """, (cycle_num, datetime.now().isoformat(), permit_id))

            conn.commit()
            return cursor.lastrowid

    def complete_review_cycle(
        self,
        cycle_id: int,
        approved: bool,
        reviewer_name: str = None
    ) -> bool:
        """Complete a review cycle"""
        with sqlite3.connect(self.db_path) as conn:
            status = "complete_approved" if approved else "complete_corrections"

            conn.execute("""
                UPDATE review_cycles
                SET end_date = ?, status = ?, reviewer_name = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), status, reviewer_name, cycle_id))

            # Get permit ID and update status
            result = conn.execute("""
                SELECT permit_id FROM review_cycles WHERE id = ?
            """, (cycle_id,)).fetchone()

            if result:
                permit_id = result[0]
                new_status = "approved" if approved else "corrections_required"
                self.update_permit_status(permit_id, new_status, _conn=conn)

            conn.commit()
            return True

    # =========================================================================
    # REVIEW COMMENTS
    # =========================================================================

    def add_review_comment(
        self,
        review_cycle_id: int,
        discipline: str,
        comment_text: str,
        code_section: str = None,
        sheet_reference: str = None
    ) -> int:
        """Add a review comment from building department"""
        with sqlite3.connect(self.db_path) as conn:
            # Get next comment number for this cycle
            result = conn.execute("""
                SELECT COALESCE(MAX(comment_number), 0) + 1 as next_num
                FROM review_comments WHERE review_cycle_id = ?
            """, (review_cycle_id,)).fetchone()
            comment_num = result[0]

            cursor = conn.execute("""
                INSERT INTO review_comments
                (review_cycle_id, comment_number, discipline, code_section,
                 comment_text, sheet_reference)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (review_cycle_id, comment_num, discipline, code_section,
                  comment_text, sheet_reference))

            conn.commit()
            return cursor.lastrowid

    def respond_to_comment(
        self,
        comment_id: int,
        response_text: str,
        resolved: bool = False
    ) -> bool:
        """Add response to a review comment"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE review_comments
                SET response_text = ?, response_date = ?, resolved = ?
                WHERE id = ?
            """, (response_text, datetime.now().isoformat(),
                  1 if resolved else 0, comment_id))
            conn.commit()
            return True

    def get_review_comments(
        self,
        permit_id: int,
        cycle_number: int = None,
        unresolved_only: bool = False
    ) -> List[Dict]:
        """Get review comments for a permit"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = """
                SELECT rc.*, cy.cycle_number
                FROM review_comments rc
                JOIN review_cycles cy ON rc.review_cycle_id = cy.id
                WHERE cy.permit_id = ?
            """
            params = [permit_id]

            if cycle_number:
                query += " AND cy.cycle_number = ?"
                params.append(cycle_number)

            if unresolved_only:
                query += " AND rc.resolved = 0"

            query += " ORDER BY cy.cycle_number, rc.discipline, rc.comment_number"

            results = conn.execute(query, params).fetchall()
            return [dict(r) for r in results]

    # =========================================================================
    # DOCUMENT TRACKING
    # =========================================================================

    def update_document_status(
        self,
        document_id: int,
        received: bool,
        notes: str = None
    ) -> bool:
        """Update document received status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE required_documents
                SET received = ?, received_date = ?, notes = ?
                WHERE id = ?
            """, (1 if received else 0,
                  datetime.now().isoformat() if received else None,
                  notes, document_id))
            conn.commit()
            return True

    def add_required_document(
        self,
        permit_id: int,
        document_name: str,
        document_type: str = "other",
        required: bool = True
    ) -> int:
        """Add a required document to permit"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO required_documents
                (permit_id, document_name, document_type, required)
                VALUES (?, ?, ?, ?)
            """, (permit_id, document_name, document_type, 1 if required else 0))
            conn.commit()
            return cursor.lastrowid

    def get_document_checklist(self, permit_id: int) -> Dict[str, Any]:
        """Get document checklist with completion status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            docs = conn.execute("""
                SELECT * FROM required_documents
                WHERE permit_id = ?
                ORDER BY document_type, document_name
            """, (permit_id,)).fetchall()

            docs = [dict(d) for d in docs]

            total = len(docs)
            received = sum(1 for d in docs if d['received'])
            required = sum(1 for d in docs if d['required'])
            required_received = sum(1 for d in docs if d['required'] and d['received'])

            return {
                "documents": docs,
                "total": total,
                "received": received,
                "outstanding": total - received,
                "required_total": required,
                "required_received": required_received,
                "ready_to_submit": required_received == required,
                "completion_pct": round(received / total * 100) if total else 0
            }

    # =========================================================================
    # INSPECTION TRACKING
    # =========================================================================

    def schedule_inspection(
        self,
        permit_id: int,
        inspection_type: str,
        scheduled_date: str
    ) -> int:
        """Schedule an inspection"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO inspections
                (permit_id, inspection_type, scheduled_date)
                VALUES (?, ?, ?)
            """, (permit_id, inspection_type, scheduled_date))
            conn.commit()
            return cursor.lastrowid

    def record_inspection_result(
        self,
        inspection_id: int,
        result: str,
        inspector_name: str = None,
        comments: str = None
    ) -> bool:
        """Record inspection result"""
        with sqlite3.connect(self.db_path) as conn:
            reinspection = 1 if result == "fail" else 0

            conn.execute("""
                UPDATE inspections
                SET actual_date = ?, result = ?, inspector_name = ?,
                    comments = ?, reinspection_required = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), result, inspector_name,
                  comments, reinspection, inspection_id))
            conn.commit()
            return True

    # =========================================================================
    # FEE TRACKING
    # =========================================================================

    def record_fee_payment(
        self,
        permit_id: int,
        fee_type: str,
        amount: float,
        payment_method: str = None,
        receipt_number: str = None
    ) -> int:
        """Record a fee payment"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO fee_payments
                (permit_id, fee_type, amount, payment_date, payment_method, receipt_number)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (permit_id, fee_type, amount, datetime.now().isoformat(),
                  payment_method, receipt_number))

            # Update actual fee total
            total = conn.execute("""
                SELECT SUM(amount) FROM fee_payments WHERE permit_id = ?
            """, (permit_id,)).fetchone()[0]

            conn.execute("""
                UPDATE permit_applications SET actual_fee = ? WHERE id = ?
            """, (total, permit_id))

            conn.commit()
            return cursor.lastrowid

    def get_fee_summary(self, permit_id: int) -> Dict[str, Any]:
        """Get fee summary for permit"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            payments = conn.execute("""
                SELECT * FROM fee_payments WHERE permit_id = ?
            """, (permit_id,)).fetchall()

            permit = conn.execute("""
                SELECT estimated_fee, actual_fee FROM permit_applications
                WHERE id = ?
            """, (permit_id,)).fetchone()

            return {
                "estimated_fee": permit['estimated_fee'],
                "actual_fee": permit['actual_fee'] or 0,
                "payments": [dict(p) for p in payments],
                "total_paid": sum(p['amount'] for p in payments)
            }

    # =========================================================================
    # PROJECT SUMMARY
    # =========================================================================

    def get_project_permits(self, project_id: int) -> List[Dict]:
        """Get all permits for a project"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            permits = conn.execute("""
                SELECT * FROM permit_applications
                WHERE project_id = ?
                ORDER BY permit_type
            """, (project_id,)).fetchall()

            results = []
            for p in permits:
                permit = dict(p)

                # Get unresolved comment count
                unresolved = conn.execute("""
                    SELECT COUNT(*) FROM review_comments rc
                    JOIN review_cycles cy ON rc.review_cycle_id = cy.id
                    WHERE cy.permit_id = ? AND rc.resolved = 0
                """, (permit['id'],)).fetchone()[0]

                permit['unresolved_comments'] = unresolved

                # Get document status
                doc_status = self.get_document_checklist(permit['id'])
                permit['docs_ready'] = doc_status['ready_to_submit']
                permit['docs_completion'] = doc_status['completion_pct']

                results.append(permit)

            return results

    def get_project_permit_summary(self, project_id: int) -> Dict[str, Any]:
        """Get summary of all permits for a project"""
        permits = self.get_project_permits(project_id)

        summary = {
            "project_id": project_id,
            "total_permits": len(permits),
            "by_status": {},
            "by_type": {},
            "total_estimated_fees": 0,
            "total_actual_fees": 0,
            "total_unresolved_comments": 0,
            "permits": permits
        }

        for p in permits:
            # By status
            status = p['status']
            summary['by_status'][status] = summary['by_status'].get(status, 0) + 1

            # By type
            ptype = p['permit_type']
            summary['by_type'][ptype] = summary['by_type'].get(ptype, 0) + 1

            # Fees
            if p['estimated_fee']:
                summary['total_estimated_fees'] += p['estimated_fee']
            if p['actual_fee']:
                summary['total_actual_fees'] += p['actual_fee']

            # Comments
            summary['total_unresolved_comments'] += p['unresolved_comments']

        return summary

    # =========================================================================
    # REPORTING
    # =========================================================================

    def generate_permit_status_report(self, permit_id: int) -> str:
        """Generate a text report for a permit"""
        permit = self.get_permit(permit_id)

        if not permit:
            return f"Permit {permit_id} not found"

        lines = [
            "=" * 70,
            f"PERMIT STATUS REPORT",
            "=" * 70,
            f"Permit Type: {permit['permit_type'].upper()}",
            f"Permit Number: {permit['permit_number'] or 'Not yet assigned'}",
            f"Jurisdiction: {permit['jurisdiction']}",
            f"Status: {permit['status'].upper()}",
            f"Review Cycle: {permit['current_review_cycle']}",
            "",
            "DATES:",
            f"  Submitted: {permit['submission_date'] or 'Not submitted'}",
            f"  Approved: {permit['approval_date'] or 'Pending'}",
            f"  Expires: {permit['expiration_date'] or 'N/A'}",
            "",
            "CONTRACTOR:",
            f"  Name: {permit['contractor_name'] or 'Not specified'}",
            f"  License: {permit['contractor_license'] or 'Not specified'}",
        ]

        if permit['private_provider']:
            lines.extend([
                "",
                "PRIVATE PROVIDER:",
                f"  Company: {permit['private_provider']}",
                f"  Number: {permit['private_provider_number'] or 'N/A'}",
            ])

        # Documents
        doc_checklist = self.get_document_checklist(permit_id)
        lines.extend([
            "",
            "-" * 70,
            "REQUIRED DOCUMENTS:",
            f"  Total: {doc_checklist['total']}",
            f"  Received: {doc_checklist['received']}",
            f"  Outstanding: {doc_checklist['outstanding']}",
            f"  Ready to Submit: {'Yes' if doc_checklist['ready_to_submit'] else 'No'}",
        ])

        # Outstanding docs
        outstanding = [d for d in doc_checklist['documents'] if not d['received'] and d['required']]
        if outstanding:
            lines.append("\n  MISSING REQUIRED DOCUMENTS:")
            for doc in outstanding:
                lines.append(f"    • {doc['document_name']}")

        # Review comments
        comments = self.get_review_comments(permit_id, unresolved_only=True)
        if comments:
            lines.extend([
                "",
                "-" * 70,
                f"UNRESOLVED COMMENTS ({len(comments)}):",
            ])
            for c in comments[:10]:  # Show first 10
                lines.append(f"\n  [{c['discipline']}] {c['code_section'] or ''}")
                lines.append(f"    {c['comment_text'][:100]}...")
                if c['sheet_reference']:
                    lines.append(f"    Sheet: {c['sheet_reference']}")

        # Fees
        fee_summary = self.get_fee_summary(permit_id)
        lines.extend([
            "",
            "-" * 70,
            "FEES:",
            f"  Estimated: ${fee_summary['estimated_fee'] or 0:,.2f}",
            f"  Actual: ${fee_summary['actual_fee']:,.2f}",
            f"  Paid: ${fee_summary['total_paid']:,.2f}",
        ])

        lines.extend(["", "=" * 70])

        return "\n".join(lines)

    def generate_comment_response_letter(
        self,
        permit_id: int,
        cycle_number: int = None
    ) -> str:
        """Generate a comment response letter"""
        permit = self.get_permit(permit_id)
        comments = self.get_review_comments(permit_id, cycle_number)

        if not comments:
            return "No comments to respond to"

        lines = [
            "PLAN REVIEW COMMENT RESPONSE",
            "=" * 70,
            f"Project: {permit['project_id']}",
            f"Permit Type: {permit['permit_type']}",
            f"Permit Number: {permit['permit_number'] or 'Pending'}",
            f"Review Cycle: {cycle_number or 'All'}",
            f"Date: {datetime.now().strftime('%B %d, %Y')}",
            "",
            "-" * 70,
        ]

        # Group by discipline
        by_discipline = {}
        for c in comments:
            disc = c['discipline']
            if disc not in by_discipline:
                by_discipline[disc] = []
            by_discipline[disc].append(c)

        for discipline, disc_comments in by_discipline.items():
            lines.extend([
                "",
                f"{discipline.upper()} COMMENTS",
                "-" * 40,
            ])

            for c in disc_comments:
                status = "✓ RESOLVED" if c['resolved'] else "○ PENDING"
                lines.extend([
                    "",
                    f"Comment #{c['comment_number']}: [{status}]",
                    f"Code Section: {c['code_section'] or 'N/A'}",
                    f"Sheet: {c['sheet_reference'] or 'N/A'}",
                    "",
                    f"COMMENT: {c['comment_text']}",
                    "",
                    f"RESPONSE: {c['response_text'] or '[Response pending]'}",
                ])

        lines.extend(["", "=" * 70])

        return "\n".join(lines)


# Convenience functions
def create_permit(
    project_id: int,
    permit_type: str,
    jurisdiction: str = "Miami-Dade County",
    **kwargs
) -> int:
    """Quick function to create a permit"""
    tracker = PermitTracker()
    return tracker.create_permit_application(project_id, permit_type, jurisdiction, **kwargs)


def get_permit_status(permit_id: int) -> Dict:
    """Quick function to get permit status"""
    tracker = PermitTracker()
    return tracker.get_permit(permit_id)


if __name__ == "__main__":
    print("=" * 70)
    print("PERMIT APPLICATION TRACKER")
    print("=" * 70)

    tracker = PermitTracker()

    # Demo: Create permits for a sample project
    project_id = 1

    print("\nCreating permit applications for project 1...")

    # Building permit
    bldg_id = tracker.create_permit_application(
        project_id=project_id,
        permit_type="building",
        jurisdiction="Miami-Dade County",
        contractor_name="ABC Construction",
        contractor_license="CGC123456",
        estimated_fee=5000.00
    )
    print(f"  Building Permit ID: {bldg_id}")

    # Electrical permit
    elec_id = tracker.create_permit_application(
        project_id=project_id,
        permit_type="electrical",
        jurisdiction="Miami-Dade County",
        contractor_name="XYZ Electric",
        contractor_license="EC13001234",
        estimated_fee=800.00
    )
    print(f"  Electrical Permit ID: {elec_id}")

    # Mechanical permit
    mech_id = tracker.create_permit_application(
        project_id=project_id,
        permit_type="mechanical",
        jurisdiction="Miami-Dade County",
        estimated_fee=600.00
    )
    print(f"  Mechanical Permit ID: {mech_id}")

    # Check document requirements
    print("\n" + "-" * 70)
    print("Building Permit Document Requirements:")
    doc_checklist = tracker.get_document_checklist(bldg_id)
    for doc in doc_checklist['documents']:
        status = "✓" if doc['received'] else "○"
        print(f"  [{status}] {doc['document_name']}")

    print(f"\n  Ready to submit: {doc_checklist['ready_to_submit']}")

    # Demo: Submit the building permit
    print("\n" + "-" * 70)
    print("Simulating permit workflow...")

    # Mark some documents as received
    for doc in doc_checklist['documents'][:5]:
        tracker.update_document_status(doc['id'], True)

    # Record submission
    tracker.record_submission(bldg_id, "initial", "John Architect")
    print("  Submitted building permit")

    # Start review cycle
    cycle_id = tracker.start_review_cycle(bldg_id, "building")
    print("  Started review cycle")

    # Add some review comments
    tracker.add_review_comment(
        cycle_id, "building", "Provide occupant load calculations on A-100",
        "FBC 1004.1", "A-100"
    )
    tracker.add_review_comment(
        cycle_id, "structural", "Show wind design criteria statement on cover sheet",
        "ASCE 7-22", "S-001"
    )
    print("  Added review comments")

    # Project summary
    print("\n" + "-" * 70)
    print("Project Permit Summary:")
    summary = tracker.get_project_permit_summary(project_id)
    print(f"  Total Permits: {summary['total_permits']}")
    print(f"  Total Estimated Fees: ${summary['total_estimated_fees']:,.2f}")
    print(f"  Unresolved Comments: {summary['total_unresolved_comments']}")

    print("\n  By Status:")
    for status, count in summary['by_status'].items():
        print(f"    {status}: {count}")

    # Generate status report
    print("\n" + "=" * 70)
    print(tracker.generate_permit_status_report(bldg_id))

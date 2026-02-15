"""SQLite database layer for OpportunityEngine."""

from __future__ import annotations

import sqlite3
import os
from pathlib import Path
from typing import Optional

from core.models import Opportunity, Proposal, Template, ScanLog

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "pipeline.db"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    budget_min REAL,
    budget_max REAL,
    currency TEXT DEFAULT 'USD',
    deadline TEXT,
    skills_required TEXT,
    competition_level TEXT,
    client_info TEXT,
    score INTEGER DEFAULT 0,
    status TEXT DEFAULT 'discovered',
    discovered_at TEXT NOT NULL,
    qualified_at TEXT,
    submitted_at TEXT,
    resolved_at TEXT,
    notes TEXT,
    raw_data TEXT
);

CREATE TABLE IF NOT EXISTS proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opportunity_id INTEGER REFERENCES opportunities(id),
    content TEXT NOT NULL,
    pricing TEXT,
    template_used TEXT,
    status TEXT DEFAULT 'draft',
    created_at TEXT NOT NULL,
    approved_at TEXT,
    submitted_at TEXT,
    client_response TEXT,
    lessons_learned TEXT
);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    content TEXT NOT NULL,
    times_used INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    last_used TEXT
);

CREATE TABLE IF NOT EXISTS scan_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    scanned_at TEXT NOT NULL,
    opportunities_found INTEGER DEFAULT 0,
    new_opportunities INTEGER DEFAULT 0,
    errors TEXT,
    duration_ms INTEGER
);

CREATE INDEX IF NOT EXISTS idx_opp_source ON opportunities(source);
CREATE INDEX IF NOT EXISTS idx_opp_status ON opportunities(status);
CREATE INDEX IF NOT EXISTS idx_opp_score ON opportunities(score DESC);
CREATE INDEX IF NOT EXISTS idx_opp_source_id ON opportunities(source, source_id);
CREATE INDEX IF NOT EXISTS idx_proposals_opp ON proposals(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_scan_source ON scan_log(source);
"""


class Database:
    """SQLite-backed storage for the opportunity pipeline."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript(SCHEMA)
        # Migrate: add score_breakdown column if missing
        cols = [r["name"] for r in self._conn.execute("PRAGMA table_info(opportunities)")]
        if "score_breakdown" not in cols:
            self._conn.execute("ALTER TABLE opportunities ADD COLUMN score_breakdown TEXT")
        self._conn.commit()

    def close(self):
        self._conn.close()

    # ── Opportunities ────────────────────────────────────────────────

    def insert_opportunity(self, opp: Opportunity) -> int:
        row = opp.to_row()
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        cur = self._conn.execute(
            f"INSERT INTO opportunities ({cols}) VALUES ({placeholders})",
            list(row.values()),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_opportunity(self, opp_id: int) -> Optional[Opportunity]:
        cur = self._conn.execute(
            "SELECT * FROM opportunities WHERE id = ?", (opp_id,)
        )
        row = cur.fetchone()
        return Opportunity.from_row(dict(row)) if row else None

    def find_by_source_id(self, source: str, source_id: str) -> Optional[Opportunity]:
        cur = self._conn.execute(
            "SELECT * FROM opportunities WHERE source = ? AND source_id = ?",
            (source, source_id),
        )
        row = cur.fetchone()
        return Opportunity.from_row(dict(row)) if row else None

    def list_opportunities(
        self,
        status: Optional[str] = None,
        source: Optional[str] = None,
        min_score: int = 0,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Opportunity]:
        query = "SELECT * FROM opportunities WHERE score >= ?"
        params: list = [min_score]
        if status:
            query += " AND status = ?"
            params.append(status)
        if source:
            query += " AND source = ?"
            params.append(source)
        query += " ORDER BY score DESC, discovered_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cur = self._conn.execute(query, params)
        return [Opportunity.from_row(dict(r)) for r in cur.fetchall()]

    def update_opportunity(self, opp_id: int, **fields) -> bool:
        if not fields:
            return False
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [opp_id]
        self._conn.execute(
            f"UPDATE opportunities SET {sets} WHERE id = ?", vals
        )
        self._conn.commit()
        return True

    def count_by_status(self) -> dict[str, int]:
        cur = self._conn.execute(
            "SELECT status, COUNT(*) as cnt FROM opportunities GROUP BY status"
        )
        return {row["status"]: row["cnt"] for row in cur.fetchall()}

    def count_by_source(self) -> dict[str, int]:
        cur = self._conn.execute(
            "SELECT source, COUNT(*) as cnt FROM opportunities GROUP BY source"
        )
        return {row["source"]: row["cnt"] for row in cur.fetchall()}

    # ── Proposals ────────────────────────────────────────────────────

    def insert_proposal(self, prop: Proposal) -> int:
        row = prop.to_row()
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        cur = self._conn.execute(
            f"INSERT INTO proposals ({cols}) VALUES ({placeholders})",
            list(row.values()),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_proposal(self, prop_id: int) -> Optional[Proposal]:
        cur = self._conn.execute("SELECT * FROM proposals WHERE id = ?", (prop_id,))
        row = cur.fetchone()
        return Proposal.from_row(dict(row)) if row else None

    def get_proposal_for_opportunity(self, opp_id: int) -> Optional[Proposal]:
        cur = self._conn.execute(
            "SELECT * FROM proposals WHERE opportunity_id = ? ORDER BY created_at DESC LIMIT 1",
            (opp_id,),
        )
        row = cur.fetchone()
        return Proposal.from_row(dict(row)) if row else None

    def update_proposal(self, prop_id: int, **fields) -> bool:
        if not fields:
            return False
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [prop_id]
        self._conn.execute(f"UPDATE proposals SET {sets} WHERE id = ?", vals)
        self._conn.commit()
        return True

    def list_proposals(
        self, status: Optional[str] = None, limit: int = 50
    ) -> list[Proposal]:
        query = "SELECT * FROM proposals"
        params: list = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cur = self._conn.execute(query, params)
        return [Proposal.from_row(dict(r)) for r in cur.fetchall()]

    # ── Templates ────────────────────────────────────────────────────

    def insert_template(self, tmpl: Template) -> int:
        row = tmpl.to_row()
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        cur = self._conn.execute(
            f"INSERT INTO templates ({cols}) VALUES ({placeholders})",
            list(row.values()),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_template(self, tmpl_id: int) -> Optional[Template]:
        cur = self._conn.execute("SELECT * FROM templates WHERE id = ?", (tmpl_id,))
        row = cur.fetchone()
        return Template.from_row(dict(row)) if row else None

    def get_template_by_name(self, name: str) -> Optional[Template]:
        cur = self._conn.execute("SELECT * FROM templates WHERE name = ?", (name,))
        row = cur.fetchone()
        return Template.from_row(dict(row)) if row else None

    def list_templates(self) -> list[Template]:
        cur = self._conn.execute("SELECT * FROM templates ORDER BY wins DESC")
        return [Template.from_row(dict(r)) for r in cur.fetchall()]

    def update_template(self, tmpl_id: int, **fields) -> bool:
        if not fields:
            return False
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [tmpl_id]
        self._conn.execute(f"UPDATE templates SET {sets} WHERE id = ?", vals)
        self._conn.commit()
        return True

    # ── Scan Log ─────────────────────────────────────────────────────

    def insert_scan_log(self, log: ScanLog) -> int:
        row = log.to_row()
        cols = ", ".join(row.keys())
        placeholders = ", ".join(["?"] * len(row))
        cur = self._conn.execute(
            f"INSERT INTO scan_log ({cols}) VALUES ({placeholders})",
            list(row.values()),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_last_scan(self, source: str) -> Optional[ScanLog]:
        cur = self._conn.execute(
            "SELECT * FROM scan_log WHERE source = ? ORDER BY scanned_at DESC LIMIT 1",
            (source,),
        )
        row = cur.fetchone()
        return ScanLog.from_row(dict(row)) if row else None

    def list_scan_logs(self, source: Optional[str] = None, limit: int = 20) -> list[ScanLog]:
        query = "SELECT * FROM scan_log"
        params: list = []
        if source:
            query += " WHERE source = ?"
            params.append(source)
        query += " ORDER BY scanned_at DESC LIMIT ?"
        params.append(limit)
        cur = self._conn.execute(query, params)
        return [ScanLog.from_row(dict(r)) for r in cur.fetchall()]

    # ── Stats ────────────────────────────────────────────────────────

    def pipeline_stats(self) -> dict:
        """Overall pipeline statistics."""
        status_counts = self.count_by_status()
        source_counts = self.count_by_source()

        # Win rate
        won = status_counts.get("won", 0)
        lost = status_counts.get("lost", 0)
        total_resolved = won + lost
        win_rate = (won / total_resolved * 100) if total_resolved > 0 else 0

        # Proposal stats
        cur = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM proposals WHERE status = 'submitted'"
        )
        submitted_proposals = cur.fetchone()["cnt"]

        return {
            "by_status": status_counts,
            "by_source": source_counts,
            "total": sum(status_counts.values()),
            "win_rate": round(win_rate, 1),
            "wins": won,
            "losses": lost,
            "proposals_submitted": submitted_proposals,
        }

    def source_stats(self, source: str) -> dict:
        """Per-source statistics."""
        cur = self._conn.execute(
            "SELECT status, COUNT(*) as cnt FROM opportunities WHERE source = ? GROUP BY status",
            (source,),
        )
        status_counts = {row["status"]: row["cnt"] for row in cur.fetchall()}
        won = status_counts.get("won", 0)
        lost = status_counts.get("lost", 0)
        total_resolved = won + lost

        cur2 = self._conn.execute(
            "SELECT AVG(score) as avg_score FROM opportunities WHERE source = ? AND score > 0",
            (source,),
        )
        avg_score = cur2.fetchone()["avg_score"] or 0

        return {
            "source": source,
            "by_status": status_counts,
            "total": sum(status_counts.values()),
            "win_rate": round((won / total_resolved * 100) if total_resolved > 0 else 0, 1),
            "avg_score": round(avg_score, 1),
        }

"""
Founder's Companion - Database Layer
====================================
SQLite storage for all platform data.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from models import (
    Founder, VaultEntry, DailyCheckIn, FounderMatch, Message,
    MoodLevel, ChallengeCategory, StartupStage, SubscriptionTier,
    generate_anonymous_name
)
from config import get_config


class Database:
    """SQLite database for Founder's Companion."""

    def __init__(self, db_path: Optional[str] = None):
        config = get_config()
        self.db_path = db_path or config.database.db_path
        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Connect to database."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def _create_tables(self):
        """Create all database tables."""
        cursor = self.conn.cursor()

        # Founders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS founders (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                anonymous_name TEXT NOT NULL,
                first_name TEXT,
                company_name TEXT,
                stage TEXT DEFAULT 'idea',
                industry TEXT DEFAULT 'technology',
                team_size INTEGER DEFAULT 1,
                years_as_founder REAL DEFAULT 0,
                current_challenges TEXT DEFAULT '[]',
                current_mood TEXT DEFAULT 'OKAY',
                tier TEXT DEFAULT 'free_trial',
                tier_expires TEXT,
                open_to_matching INTEGER DEFAULT 1,
                anonymous_until_consent INTEGER DEFAULT 1,
                timezone TEXT DEFAULT 'UTC',
                created_at TEXT NOT NULL,
                last_active TEXT NOT NULL
            )
        """)

        # Vault entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vault_entries (
                id TEXT PRIMARY KEY,
                founder_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                encrypted_content BLOB,
                mood_before TEXT,
                mood_after TEXT,
                challenge_category TEXT,
                ai_response TEXT,
                response_helpful INTEGER,
                FOREIGN KEY (founder_id) REFERENCES founders(id)
            )
        """)

        # Daily check-ins table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkins (
                id TEXT PRIMARY KEY,
                founder_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                check_in_type TEXT DEFAULT 'morning',
                mood TEXT,
                energy_level INTEGER,
                sleep_quality INTEGER,
                stress_level INTEGER,
                biggest_worry TEXT,
                small_win TEXT,
                gratitude TEXT,
                intention TEXT,
                ai_prompt TEXT,
                ai_response TEXT,
                helpful_rating INTEGER,
                FOREIGN KEY (founder_id) REFERENCES founders(id)
            )
        """)

        # Matches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id TEXT PRIMARY KEY,
                founder_1_id TEXT NOT NULL,
                founder_2_id TEXT NOT NULL,
                matched_at TEXT NOT NULL,
                compatibility_score REAL,
                common_challenges TEXT DEFAULT '[]',
                match_reason TEXT,
                status TEXT DEFAULT 'pending',
                founder_1_accepted INTEGER DEFAULT 0,
                founder_2_accepted INTEGER DEFAULT 0,
                founder_1_revealed INTEGER DEFAULT 0,
                founder_2_revealed INTEGER DEFAULT 0,
                messages_exchanged INTEGER DEFAULT 0,
                last_interaction TEXT,
                ended_at TEXT,
                end_reason TEXT,
                FOREIGN KEY (founder_1_id) REFERENCES founders(id),
                FOREIGN KEY (founder_2_id) REFERENCES founders(id)
            )
        """)

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                match_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                content TEXT,
                read INTEGER DEFAULT 0,
                read_at TEXT,
                FOREIGN KEY (match_id) REFERENCES matches(id),
                FOREIGN KEY (sender_id) REFERENCES founders(id)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_founder ON vault_entries(founder_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_checkins_founder ON checkins(founder_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_founder1 ON matches(founder_1_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_founder2 ON matches(founder_2_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_match ON messages(match_id)")

        self.conn.commit()

    # ========== Founder Methods ==========

    def create_founder(self, email: str, **kwargs) -> Founder:
        """Create a new founder."""
        founder = Founder(
            email=email,
            anonymous_name=generate_anonymous_name(),
            created_at=datetime.now(),
            last_active=datetime.now(),
            **kwargs
        )

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO founders
            (id, email, anonymous_name, first_name, company_name, stage, industry,
             team_size, years_as_founder, current_challenges, current_mood, tier,
             open_to_matching, anonymous_until_consent, timezone, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            founder.id, founder.email, founder.anonymous_name, founder.first_name,
            founder.company_name, founder.stage.value, founder.industry,
            founder.team_size, founder.years_as_founder,
            json.dumps([c.value for c in founder.current_challenges]),
            founder.current_mood.name, founder.tier.value,
            founder.open_to_matching, founder.anonymous_until_consent,
            founder.timezone, founder.created_at.isoformat(), founder.last_active.isoformat()
        ))
        self.conn.commit()
        return founder

    def get_founder(self, founder_id: str) -> Optional[Founder]:
        """Get founder by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM founders WHERE id = ?", (founder_id,))
        row = cursor.fetchone()
        return self._row_to_founder(row) if row else None

    def get_founder_by_email(self, email: str) -> Optional[Founder]:
        """Get founder by email."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM founders WHERE email = ?", (email,))
        row = cursor.fetchone()
        return self._row_to_founder(row) if row else None

    def update_founder(self, founder: Founder):
        """Update founder record."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE founders SET
                first_name = ?, company_name = ?, stage = ?, industry = ?,
                team_size = ?, years_as_founder = ?, current_challenges = ?,
                current_mood = ?, tier = ?, open_to_matching = ?,
                anonymous_until_consent = ?, last_active = ?
            WHERE id = ?
        """, (
            founder.first_name, founder.company_name, founder.stage.value,
            founder.industry, founder.team_size, founder.years_as_founder,
            json.dumps([c.value for c in founder.current_challenges]),
            founder.current_mood.name, founder.tier.value,
            founder.open_to_matching, founder.anonymous_until_consent,
            founder.last_active.isoformat(), founder.id
        ))
        self.conn.commit()

    def get_matchable_founders(
        self,
        exclude_id: str,
        open_to_matching: bool = True
    ) -> List[Founder]:
        """Get founders available for matching."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM founders
            WHERE id != ? AND open_to_matching = ?
        """, (exclude_id, open_to_matching))
        return [self._row_to_founder(row) for row in cursor.fetchall()]

    def _row_to_founder(self, row) -> Founder:
        """Convert database row to Founder object."""
        challenges = json.loads(row["current_challenges"] or "[]")
        return Founder(
            id=row["id"],
            email=row["email"],
            anonymous_name=row["anonymous_name"],
            first_name=row["first_name"],
            company_name=row["company_name"],
            stage=StartupStage(row["stage"]),
            industry=row["industry"],
            team_size=row["team_size"],
            years_as_founder=row["years_as_founder"],
            current_challenges=[ChallengeCategory(c) for c in challenges],
            current_mood=MoodLevel[row["current_mood"]],
            tier=SubscriptionTier(row["tier"]),
            open_to_matching=bool(row["open_to_matching"]),
            anonymous_until_consent=bool(row["anonymous_until_consent"]),
            timezone=row["timezone"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_active=datetime.fromisoformat(row["last_active"])
        )

    # ========== Vault Methods ==========

    def save_vault_entry(self, entry: VaultEntry):
        """Save vault entry."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO vault_entries
            (id, founder_id, timestamp, encrypted_content, mood_before,
             mood_after, challenge_category, ai_response, response_helpful)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id, entry.founder_id, entry.timestamp.isoformat(),
            entry.encrypted_content, entry.mood_before.name,
            entry.mood_after.name if entry.mood_after else None,
            entry.challenge_category.value if entry.challenge_category else None,
            entry.ai_response, entry.response_helpful
        ))
        self.conn.commit()

    def get_vault_entry(self, entry_id: str) -> Optional[VaultEntry]:
        """Get vault entry by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM vault_entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        return self._row_to_vault_entry(row) if row else None

    def update_vault_entry(self, entry: VaultEntry):
        """Update vault entry."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE vault_entries SET
                mood_after = ?, response_helpful = ?
            WHERE id = ?
        """, (
            entry.mood_after.name if entry.mood_after else None,
            entry.response_helpful, entry.id
        ))
        self.conn.commit()

    def get_vault_entries_by_founder(
        self,
        founder_id: str,
        limit: int = 100,
        days: int = 30
    ) -> List[VaultEntry]:
        """Get vault entries for a founder."""
        cursor = self.conn.cursor()
        since = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT * FROM vault_entries
            WHERE founder_id = ? AND timestamp > ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (founder_id, since, limit))
        return [self._row_to_vault_entry(row) for row in cursor.fetchall()]

    def _row_to_vault_entry(self, row) -> VaultEntry:
        """Convert database row to VaultEntry."""
        return VaultEntry(
            id=row["id"],
            founder_id=row["founder_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            encrypted_content=row["encrypted_content"],
            mood_before=MoodLevel[row["mood_before"]],
            mood_after=MoodLevel[row["mood_after"]] if row["mood_after"] else None,
            challenge_category=ChallengeCategory(row["challenge_category"]) if row["challenge_category"] else None,
            ai_response=row["ai_response"],
            response_helpful=row["response_helpful"]
        )

    # ========== Check-in Methods ==========

    def save_checkin(self, checkin: DailyCheckIn):
        """Save check-in."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO checkins
            (id, founder_id, timestamp, check_in_type, mood, energy_level,
             sleep_quality, stress_level, biggest_worry, small_win, gratitude,
             intention, ai_prompt, ai_response, helpful_rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            checkin.id, checkin.founder_id, checkin.timestamp.isoformat(),
            checkin.check_in_type, checkin.mood.name if checkin.mood else None,
            checkin.energy_level, checkin.sleep_quality, checkin.stress_level,
            checkin.biggest_worry, checkin.small_win, checkin.gratitude,
            checkin.intention, checkin.ai_prompt, checkin.ai_response,
            checkin.helpful_rating
        ))
        self.conn.commit()

    def get_checkin(self, checkin_id: str) -> Optional[DailyCheckIn]:
        """Get check-in by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM checkins WHERE id = ?", (checkin_id,))
        row = cursor.fetchone()
        return self._row_to_checkin(row) if row else None

    def update_checkin(self, checkin: DailyCheckIn):
        """Update check-in."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE checkins SET
                mood = ?, energy_level = ?, biggest_worry = ?, small_win = ?,
                intention = ?, ai_response = ?, helpful_rating = ?
            WHERE id = ?
        """, (
            checkin.mood.name if checkin.mood else None, checkin.energy_level,
            checkin.biggest_worry, checkin.small_win, checkin.intention,
            checkin.ai_response, checkin.helpful_rating, checkin.id
        ))
        self.conn.commit()

    def get_last_checkin(self, founder_id: str) -> Optional[DailyCheckIn]:
        """Get most recent check-in for founder."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM checkins WHERE founder_id = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (founder_id,))
        row = cursor.fetchone()
        return self._row_to_checkin(row) if row else None

    def get_recent_checkins(
        self,
        founder_id: str,
        days: int = 7
    ) -> List[DailyCheckIn]:
        """Get recent check-ins."""
        cursor = self.conn.cursor()
        since = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("""
            SELECT * FROM checkins
            WHERE founder_id = ? AND timestamp > ?
            ORDER BY timestamp DESC
        """, (founder_id, since))
        return [self._row_to_checkin(row) for row in cursor.fetchall()]

    def _row_to_checkin(self, row) -> DailyCheckIn:
        """Convert database row to DailyCheckIn."""
        return DailyCheckIn(
            id=row["id"],
            founder_id=row["founder_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            check_in_type=row["check_in_type"],
            mood=MoodLevel[row["mood"]] if row["mood"] else MoodLevel.OKAY,
            energy_level=row["energy_level"] or 5,
            sleep_quality=row["sleep_quality"],
            stress_level=row["stress_level"] or 5,
            biggest_worry=row["biggest_worry"],
            small_win=row["small_win"],
            gratitude=row["gratitude"],
            intention=row["intention"],
            ai_prompt=row["ai_prompt"],
            ai_response=row["ai_response"],
            helpful_rating=row["helpful_rating"]
        )

    # ========== Match Methods ==========

    def save_match(self, match: FounderMatch):
        """Save match."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO matches
            (id, founder_1_id, founder_2_id, matched_at, compatibility_score,
             common_challenges, match_reason, status, founder_1_accepted,
             founder_2_accepted, founder_1_revealed, founder_2_revealed,
             messages_exchanged, last_interaction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match.id, match.founder_1_id, match.founder_2_id,
            match.matched_at.isoformat(), match.compatibility_score,
            json.dumps([c.value for c in match.common_challenges]),
            match.match_reason, match.status,
            match.founder_1_accepted, match.founder_2_accepted,
            match.founder_1_revealed, match.founder_2_revealed,
            match.messages_exchanged,
            match.last_interaction.isoformat() if match.last_interaction else None
        ))
        self.conn.commit()

    def get_match(self, match_id: str) -> Optional[FounderMatch]:
        """Get match by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
        row = cursor.fetchone()
        return self._row_to_match(row) if row else None

    def update_match(self, match: FounderMatch):
        """Update match."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE matches SET
                status = ?, founder_1_accepted = ?, founder_2_accepted = ?,
                founder_1_revealed = ?, founder_2_revealed = ?,
                messages_exchanged = ?, last_interaction = ?,
                ended_at = ?, end_reason = ?
            WHERE id = ?
        """, (
            match.status, match.founder_1_accepted, match.founder_2_accepted,
            match.founder_1_revealed, match.founder_2_revealed,
            match.messages_exchanged,
            match.last_interaction.isoformat() if match.last_interaction else None,
            match.ended_at.isoformat() if match.ended_at else None,
            match.end_reason, match.id
        ))
        self.conn.commit()

    def get_matches_by_founder(
        self,
        founder_id: str,
        status: Optional[str] = None
    ) -> List[FounderMatch]:
        """Get matches for a founder."""
        cursor = self.conn.cursor()
        if status:
            cursor.execute("""
                SELECT * FROM matches
                WHERE (founder_1_id = ? OR founder_2_id = ?) AND status = ?
            """, (founder_id, founder_id, status))
        else:
            cursor.execute("""
                SELECT * FROM matches
                WHERE founder_1_id = ? OR founder_2_id = ?
            """, (founder_id, founder_id))
        return [self._row_to_match(row) for row in cursor.fetchall()]

    def _row_to_match(self, row) -> FounderMatch:
        """Convert database row to FounderMatch."""
        challenges = json.loads(row["common_challenges"] or "[]")
        return FounderMatch(
            id=row["id"],
            founder_1_id=row["founder_1_id"],
            founder_2_id=row["founder_2_id"],
            matched_at=datetime.fromisoformat(row["matched_at"]),
            compatibility_score=row["compatibility_score"],
            common_challenges=[ChallengeCategory(c) for c in challenges],
            match_reason=row["match_reason"],
            status=row["status"],
            founder_1_accepted=bool(row["founder_1_accepted"]),
            founder_2_accepted=bool(row["founder_2_accepted"]),
            founder_1_revealed=bool(row["founder_1_revealed"]),
            founder_2_revealed=bool(row["founder_2_revealed"]),
            messages_exchanged=row["messages_exchanged"],
            last_interaction=datetime.fromisoformat(row["last_interaction"]) if row["last_interaction"] else None,
            ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
            end_reason=row["end_reason"]
        )

    # ========== Message Methods ==========

    def save_message(self, message: Message):
        """Save message."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO messages
            (id, match_id, sender_id, timestamp, content, read, read_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            message.id, message.match_id, message.sender_id,
            message.timestamp.isoformat(), message.content,
            message.read,
            message.read_at.isoformat() if message.read_at else None
        ))
        self.conn.commit()

    def get_messages(self, match_id: str) -> List[Message]:
        """Get messages for a match."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM messages WHERE match_id = ?
            ORDER BY timestamp ASC
        """, (match_id,))
        return [self._row_to_message(row) for row in cursor.fetchall()]

    def _row_to_message(self, row) -> Message:
        """Convert database row to Message."""
        return Message(
            id=row["id"],
            match_id=row["match_id"],
            sender_id=row["sender_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            content=row["content"],
            read=bool(row["read"]),
            read_at=datetime.fromisoformat(row["read_at"]) if row["read_at"] else None
        )

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

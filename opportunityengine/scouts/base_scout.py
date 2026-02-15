"""Abstract base class for platform scouts."""

from __future__ import annotations

import time
import logging
from abc import ABC, abstractmethod
from datetime import datetime

from core.database import Database
from core.models import Opportunity, ScanLog

logger = logging.getLogger("opportunityengine.scouts")


class BaseScout(ABC):
    """Base class for all platform scouts.

    Subclasses must implement:
        - source_name: str property
        - _fetch_opportunities() -> list[Opportunity]
    """

    def __init__(self, db: Database):
        self.db = db

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Platform identifier (e.g. 'upwork', 'github')."""
        ...

    @abstractmethod
    def _fetch_opportunities(self) -> list[Opportunity]:
        """Fetch raw opportunities from the platform.

        Returns a list of Opportunity objects with at least:
            - source, source_id, title, description
            - Any available: budget_min/max, skills_required, client_info, raw_data
        """
        ...

    def scan(self) -> ScanLog:
        """Run a scan: fetch, deduplicate, insert new opportunities.

        Returns a ScanLog entry with results.
        """
        start_ms = time.monotonic_ns() // 1_000_000
        errors = []
        found = 0
        new = 0

        try:
            raw_opps = self._fetch_opportunities()
            found = len(raw_opps)

            for opp in raw_opps:
                opp.source = self.source_name
                # Dedup by source + source_id
                if opp.source_id and self.db.find_by_source_id(self.source_name, opp.source_id):
                    continue
                opp.discovered_at = datetime.utcnow().isoformat()
                self.db.insert_opportunity(opp)
                new += 1

        except Exception as e:
            logger.exception(f"Scout {self.source_name} error")
            errors.append(str(e))

        duration_ms = (time.monotonic_ns() // 1_000_000) - start_ms

        log = ScanLog(
            source=self.source_name,
            scanned_at=datetime.utcnow().isoformat(),
            opportunities_found=found,
            new_opportunities=new,
            errors="; ".join(errors),
            duration_ms=duration_ms,
        )
        self.db.insert_scan_log(log)

        logger.info(
            f"[{self.source_name}] Found {found}, {new} new, "
            f"{len(errors)} errors, {duration_ms}ms"
        )
        return log

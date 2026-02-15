"""
Project Matcher - Identifies project numbers and names from files.
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProjectMatch:
    project_number: str
    project_name: Optional[str]
    confidence: float
    matched_pattern: str


class ProjectMatcher:
    """Matches files to projects based on project number patterns."""

    # Common project number patterns in architecture
    DEFAULT_PATTERNS = [
        # Standard formats: 2024-001, 24-001, 24001
        r"(?P<year>20\d{2})-(?P<num>\d{3,4})",
        r"(?P<year>\d{2})-(?P<num>\d{3,4})",
        r"(?P<year>\d{2})(?P<num>\d{3,4})",
        # With prefix: PRJ-2024-001, A-24-001
        r"[A-Z]{1,3}-(?P<year>20?\d{2})-(?P<num>\d{3,4})",
        # Address-based: 123 Main St, 456_Oak_Ave
        r"(?P<address>\d{3,5}[\s_-][A-Za-z]+[\s_-][A-Za-z]+)",
    ]

    def __init__(self, custom_patterns: List[str] = None,
                 project_registry: Dict[str, str] = None):
        """
        Initialize project matcher.

        Args:
            custom_patterns: Additional regex patterns for project numbers
            project_registry: Dict mapping project numbers to names
        """
        self.patterns = [re.compile(p, re.IGNORECASE)
                        for p in (custom_patterns or []) + self.DEFAULT_PATTERNS]
        self.registry = project_registry or {}

    def extract_project_number(self, text: str) -> Optional[ProjectMatch]:
        """Extract project number from text (filename or content)."""
        for pattern in self.patterns:
            if match := pattern.search(text):
                groups = match.groupdict()

                # Build project number
                if "year" in groups and "num" in groups:
                    year = groups["year"]
                    num = groups["num"]
                    # Normalize year to 4 digits
                    if len(year) == 2:
                        year = f"20{year}"
                    project_num = f"{year}-{num}"
                elif "address" in groups:
                    project_num = groups["address"].replace(" ", "_")
                else:
                    project_num = match.group()

                # Look up project name
                project_name = self.registry.get(project_num)

                # Calculate confidence
                confidence = 0.8 if "year" in groups else 0.6
                if project_name:
                    confidence += 0.1

                return ProjectMatch(
                    project_number=project_num,
                    project_name=project_name,
                    confidence=confidence,
                    matched_pattern=pattern.pattern
                )

        return None

    def match_file(self, filepath: str) -> Optional[ProjectMatch]:
        """Match project from filepath."""
        # Try filename first
        from pathlib import Path
        filename = Path(filepath).stem

        if match := self.extract_project_number(filename):
            return match

        # Try path components
        for part in Path(filepath).parts:
            if match := self.extract_project_number(part):
                return match

        return None

    def register_project(self, number: str, name: str):
        """Register a project number with its name."""
        self.registry[number] = name

    def suggest_project_folder(self, match: ProjectMatch) -> str:
        """Suggest a folder name for a project."""
        if match.project_name:
            # Clean name for folder use
            clean_name = re.sub(r'[<>:"/\\|?*]', '', match.project_name)
            return f"{match.project_number} - {clean_name}"
        return match.project_number

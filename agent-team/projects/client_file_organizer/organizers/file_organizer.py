"""
File Organizer - Core logic for organizing files into project folders.
"""
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..matchers import ClientMatcher, ProjectMatcher, FileTypeMatcher


@dataclass
class OrganizeResult:
    source_path: str
    destination_path: str
    client: Optional[str]
    project: Optional[str]
    file_type: Optional[str]
    action: str  # moved, copied, skipped, error
    reason: Optional[str] = None


class FileOrganizer:
    """Organizes files into structured project folders."""

    def __init__(self, base_path: str, client_config: Dict = None,
                 project_registry: Dict = None):
        """
        Initialize file organizer.

        Args:
            base_path: Base directory for organized files
            client_config: Client patterns configuration
            project_registry: Project number to name mapping
        """
        self.base_path = Path(base_path)
        self.client_matcher = ClientMatcher(client_config)
        self.project_matcher = ProjectMatcher(project_registry=project_registry)
        self.file_type_matcher = FileTypeMatcher()
        self.results: List[OrganizeResult] = []

    def determine_destination(self, filepath: str) -> Tuple[Path, Dict]:
        """
        Determine where a file should be organized.

        Returns:
            Tuple of (destination_path, match_info)
        """
        path = Path(filepath)
        match_info = {
            "client": None,
            "project": None,
            "file_type": None,
            "confidence": 0.0
        }

        # Match client
        if client_match := self.client_matcher.match_file(filepath):
            match_info["client"] = client_match.client_name
            match_info["confidence"] += client_match.confidence

        # Match project
        if project_match := self.project_matcher.match_file(filepath):
            match_info["project"] = project_match.project_number
            match_info["confidence"] += project_match.confidence

        # Match file type
        if type_match := self.file_type_matcher.match_file(filepath):
            match_info["file_type"] = type_match.category
            match_info["confidence"] += type_match.confidence

        # Build destination path
        dest_parts = [self.base_path]

        # Client folder
        if match_info["client"]:
            client_folder = self.client_matcher.get_client_folder(match_info["client"])
            dest_parts.append(client_folder)

        # Project folder
        if match_info["project"]:
            project_folder = match_info["project"]
            if project_match and project_match.project_name:
                project_folder = self.project_matcher.suggest_project_folder(project_match)
            dest_parts.append(project_folder)

        # File type subfolder
        if type_match:
            dest_parts.append(type_match.suggested_folder)

        # Final destination
        dest_path = Path(*dest_parts) / path.name

        return dest_path, match_info

    def organize_file(self, filepath: str, mode: str = "copy",
                      dry_run: bool = False) -> OrganizeResult:
        """
        Organize a single file.

        Args:
            filepath: Path to file to organize
            mode: "copy" or "move"
            dry_run: If True, don't actually move/copy files

        Returns:
            OrganizeResult with action taken
        """
        source = Path(filepath)

        if not source.exists():
            return OrganizeResult(
                source_path=filepath,
                destination_path="",
                client=None,
                project=None,
                file_type=None,
                action="error",
                reason="Source file not found"
            )

        dest_path, match_info = self.determine_destination(filepath)

        # Skip if low confidence
        if match_info["confidence"] < 0.3:
            return OrganizeResult(
                source_path=filepath,
                destination_path=str(dest_path),
                client=match_info["client"],
                project=match_info["project"],
                file_type=match_info["file_type"],
                action="skipped",
                reason="Low confidence match"
            )

        # Check if already in correct location
        if source.parent == dest_path.parent:
            return OrganizeResult(
                source_path=filepath,
                destination_path=str(dest_path),
                client=match_info["client"],
                project=match_info["project"],
                file_type=match_info["file_type"],
                action="skipped",
                reason="Already in correct location"
            )

        action = mode + ("_dry" if dry_run else "")

        if not dry_run:
            # Create destination directory
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Handle existing file
            if dest_path.exists():
                # Add timestamp to avoid overwrite
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_name = f"{dest_path.stem}_{timestamp}{dest_path.suffix}"
                dest_path = dest_path.parent / new_name

            # Move or copy
            if mode == "move":
                shutil.move(str(source), str(dest_path))
            else:
                shutil.copy2(str(source), str(dest_path))

        result = OrganizeResult(
            source_path=filepath,
            destination_path=str(dest_path),
            client=match_info["client"],
            project=match_info["project"],
            file_type=match_info["file_type"],
            action=action
        )

        self.results.append(result)
        return result

    def get_summary(self) -> Dict:
        """Get summary of organization results."""
        actions = {}
        for r in self.results:
            actions[r.action] = actions.get(r.action, 0) + 1

        return {
            "total_files": len(self.results),
            "by_action": actions,
            "by_client": self._group_by("client"),
            "by_project": self._group_by("project"),
            "by_type": self._group_by("file_type")
        }

    def _group_by(self, field: str) -> Dict[str, int]:
        """Group results by a field."""
        groups = {}
        for r in self.results:
            value = getattr(r, field, None) or "Unknown"
            groups[value] = groups.get(value, 0) + 1
        return groups

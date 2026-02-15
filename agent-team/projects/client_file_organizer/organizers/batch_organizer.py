"""
Batch Organizer - Process multiple files or directories.
"""
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
import json

from .file_organizer import FileOrganizer, OrganizeResult


class BatchOrganizer:
    """Batch process files for organization."""

    def __init__(self, organizer: FileOrganizer, max_workers: int = 4):
        self.organizer = organizer
        self.max_workers = max_workers
        self.results: List[OrganizeResult] = []

    def scan_directory(self, directory: str,
                      extensions: List[str] = None,
                      recursive: bool = True) -> List[str]:
        """
        Scan directory for files to organize.

        Args:
            directory: Directory to scan
            extensions: List of extensions to include (e.g., ['.pdf', '.dwg'])
            recursive: Whether to scan subdirectories

        Returns:
            List of file paths
        """
        path = Path(directory)
        if not path.exists():
            return []

        files = []
        pattern = "**/*" if recursive else "*"

        for f in path.glob(pattern):
            if not f.is_file():
                continue

            # Filter by extension
            if extensions:
                if f.suffix.lower() not in [e.lower() for e in extensions]:
                    continue

            files.append(str(f))

        return sorted(files)

    def organize_batch(self, files: List[str],
                       mode: str = "copy",
                       dry_run: bool = False) -> List[OrganizeResult]:
        """
        Organize a batch of files.

        Args:
            files: List of file paths
            mode: "copy" or "move"
            dry_run: If True, don't actually move/copy files

        Returns:
            List of OrganizeResults
        """
        self.results = []

        # Process files (could be parallelized for large batches)
        for filepath in files:
            result = self.organizer.organize_file(filepath, mode, dry_run)
            self.results.append(result)

        return self.results

    def organize_directory(self, directory: str,
                          extensions: List[str] = None,
                          mode: str = "copy",
                          dry_run: bool = False,
                          recursive: bool = True) -> List[OrganizeResult]:
        """
        Organize all files in a directory.

        Args:
            directory: Source directory
            extensions: File extensions to include
            mode: "copy" or "move"
            dry_run: Preview mode
            recursive: Include subdirectories

        Returns:
            List of OrganizeResults
        """
        files = self.scan_directory(directory, extensions, recursive)
        return self.organize_batch(files, mode, dry_run)

    def preview(self, files: List[str]) -> Dict:
        """
        Preview organization without making changes.

        Returns summary of what would happen.
        """
        results = self.organize_batch(files, mode="copy", dry_run=True)

        preview = {
            "total_files": len(results),
            "would_organize": [],
            "would_skip": []
        }

        for r in results:
            item = {
                "source": r.source_path,
                "destination": r.destination_path,
                "client": r.client,
                "project": r.project,
                "type": r.file_type
            }

            if "skip" in r.action:
                item["reason"] = r.reason
                preview["would_skip"].append(item)
            else:
                preview["would_organize"].append(item)

        return preview

    def export_results(self, filepath: str, format: str = "json"):
        """Export results to file."""
        if format == "json":
            data = [
                {
                    "source": r.source_path,
                    "destination": r.destination_path,
                    "client": r.client,
                    "project": r.project,
                    "file_type": r.file_type,
                    "action": r.action,
                    "reason": r.reason
                }
                for r in self.results
            ]
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        elif format == "csv":
            import csv
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Source", "Destination", "Client", "Project", "Type", "Action", "Reason"])
                for r in self.results:
                    writer.writerow([
                        r.source_path, r.destination_path, r.client,
                        r.project, r.file_type, r.action, r.reason
                    ])

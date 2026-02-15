"""
Bluebeam CSV export extractor.

Parses markup data exported from Bluebeam Revu via:
- Markups > Summary > Export to CSV
- Or via Bluebeam MCP automation

Bluebeam CSV typically includes columns like:
- Subject, Label, Page, Date, Author, Status, Color, Space
- Comments, Layer, Custom Columns, etc.
"""

import csv
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False


@dataclass
class BluebeamMarkup:
    """Represents a markup from Bluebeam CSV export."""
    id: str
    page: int
    subject: str
    label: str
    author: str
    date: Optional[str]
    status: str
    color: Optional[str]
    layer: str
    space: str
    comments: str
    checkmark: bool
    locked: bool
    custom_columns: Dict[str, str]
    source_file: str
    raw_row: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BluebeamCSVExtractor:
    """Extract markups from Bluebeam CSV export files."""

    # Standard Bluebeam CSV columns
    STANDARD_COLUMNS = {
        "Subject": "subject",
        "Label": "label",
        "Page": "page",
        "Page Label": "page_label",
        "Date": "date",
        "Author": "author",
        "Status": "status",
        "Color": "color",
        "Layer": "layer",
        "Space": "space",
        "Comments": "comments",
        "Checkmark": "checkmark",
        "Locked": "locked",
        "X": "x",
        "Y": "y",
        "Width": "width",
        "Height": "height",
    }

    def __init__(self, bluebeam_mcp_path: Optional[str] = None):
        """
        Initialize the extractor.

        Args:
            bluebeam_mcp_path: Optional path to Bluebeam MCP server for direct export
        """
        self.bluebeam_mcp_path = bluebeam_mcp_path or "/mnt/d/_CLAUDE-TOOLS/bluebeam-mcp"

    def extract_from_csv(self, csv_path: str) -> List[BluebeamMarkup]:
        """
        Extract markups from a Bluebeam CSV export file.

        Args:
            csv_path: Path to the CSV file

        Returns:
            List of BluebeamMarkup objects
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV not found: {csv_path}")

        markups = []

        # Try different encodings (Bluebeam sometimes uses UTF-16)
        encodings = ["utf-8", "utf-16", "utf-8-sig", "cp1252"]

        for encoding in encodings:
            try:
                with open(csv_path, "r", encoding=encoding, newline="") as f:
                    reader = csv.DictReader(f)

                    # Identify custom columns
                    standard_cols = set(self.STANDARD_COLUMNS.keys())
                    custom_cols = [
                        c for c in reader.fieldnames if c not in standard_cols
                    ] if reader.fieldnames else []

                    for idx, row in enumerate(reader):
                        markup = self._parse_row(row, idx, str(csv_path), custom_cols)
                        if markup:
                            markups.append(markup)

                break  # Success, exit encoding loop

            except UnicodeDecodeError:
                continue
            except Exception as e:
                if encoding == encodings[-1]:
                    raise e
                continue

        return markups

    def _parse_row(
        self,
        row: Dict[str, str],
        idx: int,
        source_file: str,
        custom_cols: List[str]
    ) -> Optional[BluebeamMarkup]:
        """Parse a single CSV row into a BluebeamMarkup."""
        try:
            # Extract standard fields with defaults
            page_str = row.get("Page", "1")
            try:
                page = int(page_str.split()[0]) if page_str else 1
            except (ValueError, IndexError):
                page = 1

            # Parse date
            date_str = row.get("Date", "")
            date = None
            if date_str:
                for fmt in ["%m/%d/%Y %I:%M %p", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"]:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        date = dt.isoformat()
                        break
                    except ValueError:
                        continue
                if not date:
                    date = date_str

            # Parse boolean fields
            checkmark = row.get("Checkmark", "").lower() in ("yes", "true", "1", "x")
            locked = row.get("Locked", "").lower() in ("yes", "true", "1", "x")

            # Extract custom columns
            custom_data = {col: row.get(col, "") for col in custom_cols if row.get(col)}

            return BluebeamMarkup(
                id=f"bb_{idx:04d}",
                page=page,
                subject=row.get("Subject", ""),
                label=row.get("Label", ""),
                author=row.get("Author", ""),
                date=date,
                status=row.get("Status", ""),
                color=row.get("Color", ""),
                layer=row.get("Layer", ""),
                space=row.get("Space", ""),
                comments=row.get("Comments", ""),
                checkmark=checkmark,
                locked=locked,
                custom_columns=custom_data,
                source_file=source_file,
                raw_row=dict(row),
            )

        except Exception as e:
            print(f"Warning: Failed to parse row {idx}: {e}")
            return None

    def export_from_bluebeam(
        self,
        output_csv: str,
        pdf_path: Optional[str] = None,
        timeout: int = 30
    ) -> Optional[str]:
        """
        Export markups from currently open Bluebeam document to CSV.

        This uses PowerShell/COM automation to trigger the export.

        Args:
            output_csv: Path for the output CSV file
            pdf_path: Optional PDF path (uses current doc if not specified)
            timeout: Timeout in seconds

        Returns:
            Path to exported CSV or None if failed
        """
        output_csv = Path(output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)

        # Convert to Windows path
        win_csv = str(output_csv)
        if win_csv.startswith("/mnt/"):
            drive = win_csv[5].upper()
            win_csv = f"{drive}:{win_csv[6:]}".replace("/", "\\")

        # PowerShell script to export markups
        script = f'''
        Add-Type -AssemblyName System.Windows.Forms

        $revu = Get-Process -Name 'Revu' -ErrorAction SilentlyContinue
        if (-not $revu) {{
            Write-Error "Bluebeam not running"
            exit 1
        }}

        # Bring Bluebeam to foreground
        Add-Type @"
        using System;
        using System.Runtime.InteropServices;
        public class Win32Export {{
            [DllImport("user32.dll")]
            public static extern bool SetForegroundWindow(IntPtr hWnd);
        }}
"@
        [Win32Export]::SetForegroundWindow($revu.MainWindowHandle) | Out-Null
        Start-Sleep -Milliseconds 500

        # Open Markup Summary panel (Alt+M, then S)
        [System.Windows.Forms.SendKeys]::SendWait("%m")
        Start-Sleep -Milliseconds 200
        [System.Windows.Forms.SendKeys]::SendWait("s")
        Start-Sleep -Milliseconds 500

        # Export to CSV (Ctrl+Shift+E is common, or right-click menu)
        # This varies by Bluebeam version - using menu approach
        [System.Windows.Forms.SendKeys]::SendWait("^+e")
        Start-Sleep -Milliseconds 1000

        # Type the filename and press Enter
        [System.Windows.Forms.SendKeys]::SendWait("{win_csv}")
        Start-Sleep -Milliseconds 200
        [System.Windows.Forms.SendKeys]::SendWait("{{ENTER}}")

        "Export initiated to: {win_csv}"
        '''

        try:
            if _HAS_BRIDGE:
                result = _ps_bridge(script, timeout=timeout)
            else:
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-Command", script],
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )

            if result.returncode == 0:
                # Wait for file to appear
                import time
                for _ in range(10):
                    if output_csv.exists():
                        return str(output_csv)
                    time.sleep(0.5)

                # Check if file was created
                if output_csv.exists():
                    return str(output_csv)

            print(f"Export failed: {result.stderr or result.stdout}")
            return None

        except subprocess.TimeoutExpired:
            print("Export timed out")
            return None
        except Exception as e:
            print(f"Export error: {e}")
            return None

    def extract_to_dict(self, csv_path: str) -> List[Dict[str, Any]]:
        """Extract markups and return as list of dictionaries."""
        markups = self.extract_from_csv(csv_path)
        return [m.to_dict() for m in markups]

    def get_summary(self, csv_path: str) -> Dict[str, Any]:
        """Get a summary of markups from a Bluebeam CSV."""
        markups = self.extract_from_csv(csv_path)

        # Count by various fields
        subject_counts = {}
        author_counts = {}
        status_counts = {}
        page_counts = {}

        for m in markups:
            subject_counts[m.subject] = subject_counts.get(m.subject, 0) + 1
            if m.author:
                author_counts[m.author] = author_counts.get(m.author, 0) + 1
            if m.status:
                status_counts[m.status] = status_counts.get(m.status, 0) + 1
            page_counts[m.page] = page_counts.get(m.page, 0) + 1

        return {
            "file": csv_path,
            "total_markups": len(markups),
            "by_subject": subject_counts,
            "by_author": author_counts,
            "by_status": status_counts,
            "by_page": page_counts,
            "pages_with_markups": len(page_counts),
            "checkmarked": sum(1 for m in markups if m.checkmark),
            "locked": sum(1 for m in markups if m.locked),
        }


# Convenience function
def extract_bluebeam_csv(csv_path: str) -> List[BluebeamMarkup]:
    """Extract all markups from a Bluebeam CSV export."""
    extractor = BluebeamCSVExtractor()
    return extractor.extract_from_csv(csv_path)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python bluebeam_extractor.py <csv_file>")
        sys.exit(1)

    csv_file = sys.argv[1]
    extractor = BluebeamCSVExtractor()

    print(f"Extracting markups from: {csv_file}\n")

    summary = extractor.get_summary(csv_file)
    print(f"Total markups: {summary['total_markups']}")
    print(f"By subject: {json.dumps(summary['by_subject'], indent=2)}")
    print(f"By author: {json.dumps(summary['by_author'], indent=2)}")
    print(f"By status: {json.dumps(summary['by_status'], indent=2)}")

    print("\n--- All Markups ---")
    markups = extractor.extract_from_csv(csv_file)
    for m in markups[:10]:  # Show first 10
        print(f"\nPage {m.page} | {m.subject} | {m.author}")
        if m.comments:
            print(f"  Comments: {m.comments[:100]}...")

    if len(markups) > 10:
        print(f"\n... and {len(markups) - 10} more markups")

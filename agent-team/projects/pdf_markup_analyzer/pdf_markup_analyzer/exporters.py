"""
Export utilities for markups and tasks.

Supports:
- JSON export (with pretty formatting)
- CSV export (compatible with Excel, project management tools)
- Markdown export (for documentation, reports)
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

try:
    from .task_generator import Task
except ImportError:
    Task = None


def export_json(
    data: List[Union[Dict[str, Any], "Task"]],
    output_path: str,
    indent: int = 2,
    include_metadata: bool = True
) -> str:
    """
    Export data to JSON file.

    Args:
        data: List of dictionaries or Task objects
        output_path: Path to output file
        indent: JSON indentation (default 2)
        include_metadata: Include export metadata

    Returns:
        Path to exported file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dictionaries
    items = []
    for item in data:
        if hasattr(item, "to_dict"):
            items.append(item.to_dict())
        elif isinstance(item, dict):
            items.append(item)
        else:
            items.append({"value": str(item)})

    # Build export structure
    export_data = {
        "items": items,
        "count": len(items),
    }

    if include_metadata:
        export_data["metadata"] = {
            "exported_at": datetime.now().isoformat(),
            "format": "json",
            "version": "1.0",
        }

    # Write file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=indent, ensure_ascii=False, default=str)

    return str(output_path)


def export_csv(
    data: List[Union[Dict[str, Any], "Task"]],
    output_path: str,
    columns: Optional[List[str]] = None,
    include_all_columns: bool = True
) -> str:
    """
    Export data to CSV file.

    Args:
        data: List of dictionaries or Task objects
        output_path: Path to output file
        columns: Specific columns to include (in order)
        include_all_columns: Include all columns not in 'columns' list

    Returns:
        Path to exported file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not data:
        # Write empty file with headers if no data
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            pass
        return str(output_path)

    # Convert to dictionaries
    items = []
    for item in data:
        if hasattr(item, "to_dict"):
            items.append(item.to_dict())
        elif isinstance(item, dict):
            items.append(item)
        else:
            items.append({"value": str(item)})

    # Flatten nested dictionaries
    flat_items = [_flatten_dict(item) for item in items]

    # Determine columns
    all_columns = set()
    for item in flat_items:
        all_columns.update(item.keys())

    if columns:
        # Start with specified columns, then add others
        final_columns = list(columns)
        if include_all_columns:
            for col in sorted(all_columns):
                if col not in final_columns:
                    final_columns.append(col)
    else:
        # Default column order for tasks/markups
        preferred_order = [
            "id", "title", "task_type", "priority", "status",
            "category", "page", "source_page", "source_file",
            "content", "comments", "description",
            "author", "assignee", "due_date",
            "created_at", "created", "modified", "date",
            "tags", "type", "subtype", "subject", "label",
        ]
        final_columns = []
        for col in preferred_order:
            if col in all_columns:
                final_columns.append(col)
        for col in sorted(all_columns):
            if col not in final_columns:
                final_columns.append(col)

    # Write CSV
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=final_columns, extrasaction="ignore")
        writer.writeheader()

        for item in flat_items:
            # Convert lists to strings
            row = {}
            for key, value in item.items():
                if isinstance(value, list):
                    row[key] = "; ".join(str(v) for v in value)
                elif isinstance(value, dict):
                    row[key] = json.dumps(value)
                else:
                    row[key] = value
            writer.writerow(row)

    return str(output_path)


def export_markdown(
    data: List[Union[Dict[str, Any], "Task"]],
    output_path: str,
    title: str = "Markup Analysis Report",
    include_summary: bool = True,
    group_by: Optional[str] = None
) -> str:
    """
    Export data to Markdown file.

    Args:
        data: List of dictionaries or Task objects
        output_path: Path to output file
        title: Report title
        include_summary: Include summary section
        group_by: Field to group items by (e.g., "category", "priority")

    Returns:
        Path to exported file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dictionaries
    items = []
    for item in data:
        if hasattr(item, "to_dict"):
            items.append(item.to_dict())
        elif isinstance(item, dict):
            items.append(item)
        else:
            items.append({"value": str(item)})

    lines = []

    # Title
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")

    # Summary section
    if include_summary and items:
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total Items:** {len(items)}")

        # Count by common fields
        for field in ["category", "priority", "task_type", "status"]:
            counts = {}
            for item in items:
                value = item.get(field, "Unknown")
                counts[value] = counts.get(value, 0) + 1

            if counts and len(counts) > 1:
                lines.append(f"- **By {field.replace('_', ' ').title()}:**")
                for key, count in sorted(counts.items(), key=lambda x: -x[1]):
                    lines.append(f"  - {key}: {count}")

        lines.append("")

    # Items section
    if group_by and items:
        lines.append("## Items by " + group_by.replace("_", " ").title())
        lines.append("")

        # Group items
        groups = {}
        for item in items:
            key = item.get(group_by, "Other")
            if key not in groups:
                groups[key] = []
            groups[key].append(item)

        # Output each group
        for group_name in sorted(groups.keys()):
            group_items = groups[group_name]
            lines.append(f"### {group_name} ({len(group_items)})")
            lines.append("")

            for item in group_items:
                lines.extend(_format_item_markdown(item))
                lines.append("")

    else:
        lines.append("## Items")
        lines.append("")

        for item in items:
            lines.extend(_format_item_markdown(item))
            lines.append("")

    # Write file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return str(output_path)


def _format_item_markdown(item: Dict[str, Any]) -> List[str]:
    """Format a single item as Markdown."""
    lines = []

    # Determine if this is a task or markup
    is_task = "task_type" in item or "title" in item

    if is_task:
        # Task format
        title = item.get("title", item.get("id", "Untitled"))
        lines.append(f"#### {title}")
        lines.append("")

        # Key fields table
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")

        key_fields = [
            ("ID", "id"),
            ("Type", "task_type"),
            ("Priority", "priority"),
            ("Status", "status"),
            ("Assignee", "assignee"),
            ("Due Date", "due_date"),
            ("Page", "source_page"),
            ("Source", "source_file"),
        ]

        for label, field in key_fields:
            value = item.get(field, "")
            if value:
                lines.append(f"| {label} | {value} |")

        # Description
        description = item.get("description", "")
        if description:
            lines.append("")
            lines.append("**Description:**")
            lines.append("")
            # Convert to blockquote
            for desc_line in description.split("\n"):
                lines.append(f"> {desc_line}")

        # Tags
        tags = item.get("tags", [])
        if tags:
            lines.append("")
            lines.append(f"**Tags:** {', '.join(tags)}")

    else:
        # Markup format
        content = item.get("content") or item.get("comments") or item.get("label", "")
        markup_type = item.get("type") or item.get("subject", "Markup")
        page = item.get("page", "?")

        lines.append(f"#### [{markup_type}] Page {page}")
        lines.append("")

        if content:
            lines.append(f"> {content}")
            lines.append("")

        # Details
        details = []
        if item.get("author"):
            details.append(f"Author: {item['author']}")
        if item.get("created") or item.get("date"):
            details.append(f"Date: {item.get('created') or item.get('date')}")
        if item.get("category"):
            details.append(f"Category: {item['category']}")

        if details:
            lines.append(f"*{' | '.join(details)}*")

    return lines


def _flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = "_") -> Dict[str, Any]:
    """Flatten a nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k

        if isinstance(v, dict):
            # Only flatten one level deep
            for sub_k, sub_v in v.items():
                items.append((f"{new_key}_{sub_k}", sub_v))
        else:
            items.append((new_key, v))

    return dict(items)


def export_all(
    data: List[Union[Dict[str, Any], "Task"]],
    output_dir: str,
    base_name: str = "markup_report",
    formats: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Export data to multiple formats.

    Args:
        data: List of dictionaries or Task objects
        output_dir: Output directory
        base_name: Base filename (without extension)
        formats: List of formats to export ("json", "csv", "markdown")

    Returns:
        Dictionary of format -> file path
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if formats is None:
        formats = ["json", "csv", "markdown"]

    results = {}

    if "json" in formats:
        results["json"] = export_json(
            data,
            str(output_dir / f"{base_name}.json")
        )

    if "csv" in formats:
        results["csv"] = export_csv(
            data,
            str(output_dir / f"{base_name}.csv")
        )

    if "markdown" in formats or "md" in formats:
        results["markdown"] = export_markdown(
            data,
            str(output_dir / f"{base_name}.md"),
            title=base_name.replace("_", " ").title()
        )

    return results


if __name__ == "__main__":
    # Test exports
    test_data = [
        {
            "id": "TASK-001",
            "title": "RFI: Foundation detail clarification",
            "task_type": "RFI",
            "priority": "High",
            "status": "Open",
            "category": "RFI",
            "page": 5,
            "source_file": "plans.pdf",
            "assignee": "John Smith",
            "due_date": "2026-02-10",
            "tags": ["structural", "foundation"],
            "description": "Please clarify the foundation detail at grid line A-3.",
        },
        {
            "id": "TASK-002",
            "title": "Safety: Fall protection required",
            "task_type": "Action Item",
            "priority": "Critical",
            "status": "Open",
            "category": "Safety",
            "page": 12,
            "source_file": "plans.pdf",
            "assignee": "Safety Team",
            "due_date": "2026-02-04",
            "tags": ["safety"],
            "description": "Fall protection required at opening on floor 3.",
        },
    ]

    print("Exporting test data...")

    # Export all formats
    results = export_all(
        test_data,
        "/tmp/markup_export_test",
        "test_report",
        formats=["json", "csv", "markdown"]
    )

    for fmt, path in results.items():
        print(f"  {fmt}: {path}")

    # Show markdown content
    print("\n--- Markdown Preview ---")
    with open(results["markdown"], "r") as f:
        print(f.read())

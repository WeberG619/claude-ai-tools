"""
PDF Markup Analyzer - Extract, categorize, and convert PDF markups to actionable tasks.

Supports:
- PyMuPDF direct annotation extraction
- Bluebeam CSV export parsing
- Automatic categorization (RFI, ASI, correction, etc.)
- Task generation for project management
- Multiple export formats (JSON, CSV, Markdown)
"""

__version__ = "1.0.0"
__author__ = "Agent Team"

from .categorizer import MarkupCategorizer, MarkupCategory
from .task_generator import TaskGenerator, Task
from .exporters import export_json, export_csv, export_markdown

__all__ = [
    "MarkupCategorizer",
    "MarkupCategory",
    "TaskGenerator",
    "Task",
    "export_json",
    "export_csv",
    "export_markdown",
]

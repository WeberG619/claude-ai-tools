"""
Task generator - Convert categorized markups to actionable tasks.

Generates tasks suitable for:
- Project management systems (Jira, Asana, Monday.com)
- Issue trackers
- Punch list management
- RFI tracking systems
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta

try:
    from .categorizer import MarkupCategory, MarkupCategorizer
except ImportError:
    from categorizer import MarkupCategory, MarkupCategorizer


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class TaskStatus(Enum):
    """Task status values."""
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    PENDING_RESPONSE = "Pending Response"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class TaskType(Enum):
    """Task types."""
    RFI = "RFI"
    ACTION_ITEM = "Action Item"
    CORRECTION = "Correction"
    REVIEW = "Review"
    COORDINATION = "Coordination"
    PUNCH_ITEM = "Punch Item"
    INFORMATION = "Information"


@dataclass
class Task:
    """Represents an actionable task generated from a markup."""
    id: str
    title: str
    description: str
    task_type: str
    priority: str
    status: str
    assignee: Optional[str]
    due_date: Optional[str]
    source_page: int
    source_file: str
    markup_id: str
    category: str
    tags: List[str] = field(default_factory=list)
    related_items: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TaskGenerator:
    """Generate actionable tasks from categorized markups."""

    # Category to task type mapping
    CATEGORY_TO_TYPE = {
        MarkupCategory.RFI: TaskType.RFI,
        MarkupCategory.ASI: TaskType.ACTION_ITEM,
        MarkupCategory.PR: TaskType.ACTION_ITEM,
        MarkupCategory.CORRECTION: TaskType.CORRECTION,
        MarkupCategory.CLARIFICATION: TaskType.RFI,
        MarkupCategory.DIMENSION: TaskType.CORRECTION,
        MarkupCategory.QUESTION: TaskType.RFI,
        MarkupCategory.APPROVAL: TaskType.INFORMATION,
        MarkupCategory.REJECTION: TaskType.CORRECTION,
        MarkupCategory.COORDINATION: TaskType.COORDINATION,
        MarkupCategory.PUNCH_LIST: TaskType.PUNCH_ITEM,
        MarkupCategory.SAFETY: TaskType.ACTION_ITEM,
        MarkupCategory.CODE_ISSUE: TaskType.CORRECTION,
        MarkupCategory.SUBMITTAL: TaskType.REVIEW,
        MarkupCategory.REVIEW_COMMENT: TaskType.REVIEW,
        MarkupCategory.NOTE: TaskType.INFORMATION,
        MarkupCategory.UNKNOWN: TaskType.INFORMATION,
    }

    # Category to priority mapping
    CATEGORY_TO_PRIORITY = {
        MarkupCategory.SAFETY: TaskPriority.CRITICAL,
        MarkupCategory.CODE_ISSUE: TaskPriority.CRITICAL,
        MarkupCategory.RFI: TaskPriority.HIGH,
        MarkupCategory.ASI: TaskPriority.HIGH,
        MarkupCategory.REJECTION: TaskPriority.HIGH,
        MarkupCategory.COORDINATION: TaskPriority.HIGH,
        MarkupCategory.CORRECTION: TaskPriority.MEDIUM,
        MarkupCategory.PUNCH_LIST: TaskPriority.MEDIUM,
        MarkupCategory.QUESTION: TaskPriority.MEDIUM,
        MarkupCategory.CLARIFICATION: TaskPriority.MEDIUM,
        MarkupCategory.PR: TaskPriority.MEDIUM,
        MarkupCategory.SUBMITTAL: TaskPriority.MEDIUM,
        MarkupCategory.DIMENSION: TaskPriority.LOW,
        MarkupCategory.REVIEW_COMMENT: TaskPriority.LOW,
        MarkupCategory.APPROVAL: TaskPriority.LOW,
        MarkupCategory.NOTE: TaskPriority.LOW,
        MarkupCategory.UNKNOWN: TaskPriority.LOW,
    }

    # Default due date offsets (days from now)
    PRIORITY_DUE_DAYS = {
        TaskPriority.CRITICAL: 1,
        TaskPriority.HIGH: 3,
        TaskPriority.MEDIUM: 7,
        TaskPriority.LOW: 14,
    }

    def __init__(
        self,
        project_name: str = "Construction Project",
        auto_assign: bool = False,
        default_assignee: Optional[str] = None,
        generate_due_dates: bool = True,
    ):
        """
        Initialize the task generator.

        Args:
            project_name: Name of the project for task context
            auto_assign: Whether to auto-assign tasks based on markup author
            default_assignee: Default assignee if auto_assign is False
            generate_due_dates: Whether to generate due dates based on priority
        """
        self.project_name = project_name
        self.auto_assign = auto_assign
        self.default_assignee = default_assignee
        self.generate_due_dates = generate_due_dates
        self.categorizer = MarkupCategorizer()
        self._task_counter = 0

    def generate_task(
        self,
        markup: Dict[str, Any],
        category: Optional[MarkupCategory] = None
    ) -> Task:
        """
        Generate a task from a single markup.

        Args:
            markup: Markup dictionary (may already have category)
            category: Optional override category

        Returns:
            Task object
        """
        self._task_counter += 1

        # Get category if not provided
        if category is None:
            if "category" in markup:
                try:
                    category = MarkupCategory(markup["category"])
                except ValueError:
                    category = MarkupCategory.UNKNOWN
            else:
                category = self.categorizer.categorize(markup)

        # Determine task type and priority
        task_type = self.CATEGORY_TO_TYPE.get(category, TaskType.INFORMATION)
        priority = self.CATEGORY_TO_PRIORITY.get(category, TaskPriority.LOW)

        # Generate title
        title = self._generate_title(markup, category, task_type)

        # Generate description
        description = self._generate_description(markup, category)

        # Determine assignee
        assignee = None
        if self.auto_assign:
            assignee = markup.get("author") or self.default_assignee
        else:
            assignee = self.default_assignee

        # Generate due date
        due_date = None
        if self.generate_due_dates:
            days = self.PRIORITY_DUE_DAYS.get(priority, 14)
            due_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        # Generate tags
        tags = self._generate_tags(markup, category)

        # Build task
        return Task(
            id=f"TASK-{self._task_counter:04d}",
            title=title,
            description=description,
            task_type=task_type.value,
            priority=priority.value,
            status=TaskStatus.OPEN.value,
            assignee=assignee,
            due_date=due_date,
            source_page=markup.get("page", 1),
            source_file=markup.get("source_file", "Unknown"),
            markup_id=markup.get("id", f"markup_{self._task_counter}"),
            category=category.value,
            tags=tags,
            related_items=[],
            metadata={
                "project": self.project_name,
                "original_author": markup.get("author", ""),
                "markup_type": markup.get("type") or markup.get("subject", ""),
                "confidence": markup.get("category_confidence", 0.0),
            }
        )

    def _generate_title(
        self,
        markup: Dict[str, Any],
        category: MarkupCategory,
        task_type: TaskType
    ) -> str:
        """Generate a concise task title."""
        # Get content
        content = (
            markup.get("content") or
            markup.get("comments") or
            markup.get("label") or
            ""
        ).strip()

        # Extract key info
        page = markup.get("page", "?")

        # Try to extract any reference numbers
        import re
        ref_match = re.search(r"(RFI|ASI|PR|CO|SK)[\s#-]*(\d+)", content, re.IGNORECASE)
        ref_num = f"{ref_match.group(1).upper()}-{ref_match.group(2)}" if ref_match else None

        # Build title based on type
        if ref_num:
            title = f"{ref_num}: {self._truncate(content, 60)}"
        elif task_type == TaskType.RFI:
            title = f"RFI: {self._truncate(content, 60)} (Page {page})"
        elif task_type == TaskType.CORRECTION:
            title = f"Correction Required: {self._truncate(content, 50)} (Page {page})"
        elif task_type == TaskType.COORDINATION:
            title = f"Coordination: {self._truncate(content, 55)} (Page {page})"
        elif task_type == TaskType.PUNCH_ITEM:
            title = f"Punch: {self._truncate(content, 60)} (Page {page})"
        else:
            title = f"{category.value}: {self._truncate(content, 55)} (Page {page})"

        return title

    def _generate_description(
        self,
        markup: Dict[str, Any],
        category: MarkupCategory
    ) -> str:
        """Generate a detailed task description."""
        lines = []

        # Main content
        content = (
            markup.get("content") or
            markup.get("comments") or
            ""
        ).strip()

        if content:
            lines.append(f"**Markup Content:**\n{content}")

        # Location info
        page = markup.get("page", "Unknown")
        rect = markup.get("rect", {})
        if rect:
            lines.append(f"\n**Location:** Page {page} (x: {rect.get('x0', '?'):.0f}, y: {rect.get('y0', '?'):.0f})")
        else:
            lines.append(f"\n**Location:** Page {page}")

        # Source info
        source = markup.get("source_file", "Unknown")
        lines.append(f"\n**Source Document:** {source}")

        # Author info
        author = markup.get("author", "")
        if author:
            lines.append(f"\n**Marked by:** {author}")

        # Date info
        date = markup.get("created") or markup.get("date") or markup.get("modified", "")
        if date:
            lines.append(f"\n**Date:** {date}")

        # Category context
        lines.append(f"\n**Category:** {category.value}")

        # Action guidance based on category
        action = self._get_action_guidance(category)
        if action:
            lines.append(f"\n**Recommended Action:** {action}")

        return "\n".join(lines)

    def _get_action_guidance(self, category: MarkupCategory) -> str:
        """Get action guidance based on category."""
        guidance = {
            MarkupCategory.RFI: "Review the question and provide a formal written response. Track in RFI log.",
            MarkupCategory.ASI: "Implement the design change and update affected drawings.",
            MarkupCategory.PR: "Prepare cost proposal and submit for approval.",
            MarkupCategory.CORRECTION: "Verify the issue and make necessary corrections to the work/drawings.",
            MarkupCategory.CLARIFICATION: "Provide detailed clarification in writing.",
            MarkupCategory.QUESTION: "Research and respond to the question.",
            MarkupCategory.COORDINATION: "Schedule coordination meeting with affected trades.",
            MarkupCategory.SAFETY: "IMMEDIATE ACTION REQUIRED - Address safety concern before proceeding.",
            MarkupCategory.CODE_ISSUE: "Review code requirement and develop compliant solution.",
            MarkupCategory.PUNCH_LIST: "Inspect and complete the deficient work item.",
            MarkupCategory.REJECTION: "Review rejection reason, make corrections, and resubmit.",
            MarkupCategory.SUBMITTAL: "Review submittal requirements and prepare submission.",
        }
        return guidance.get(category, "Review and take appropriate action.")

    def _generate_tags(
        self,
        markup: Dict[str, Any],
        category: MarkupCategory
    ) -> List[str]:
        """Generate tags for the task."""
        tags = [category.value]

        # Add markup type as tag
        markup_type = markup.get("type") or markup.get("subject", "")
        if markup_type and markup_type.lower() not in [t.lower() for t in tags]:
            tags.append(markup_type)

        # Add discipline tags if detected
        content = str(markup.get("content", "") + markup.get("comments", "")).lower()

        disciplines = {
            "architectural": ["arch", "door", "window", "wall", "finish", "ceiling"],
            "structural": ["struct", "beam", "column", "foundation", "steel", "concrete"],
            "mechanical": ["mech", "hvac", "duct", "diffuser", "vav", "ahu"],
            "electrical": ["elec", "light", "panel", "circuit", "outlet", "switch"],
            "plumbing": ["plumb", "pipe", "drain", "fixture", "water"],
            "fire-protection": ["fire", "sprinkler", "alarm", "extinguisher"],
        }

        for discipline, keywords in disciplines.items():
            if any(kw in content for kw in keywords):
                tags.append(discipline)
                break

        return tags

    def _truncate(self, text: str, max_len: int) -> str:
        """Truncate text to max length."""
        text = text.replace("\n", " ").strip()
        if len(text) <= max_len:
            return text
        return text[:max_len - 3].strip() + "..."

    def generate_tasks(
        self,
        markups: List[Dict[str, Any]],
        filter_categories: Optional[List[MarkupCategory]] = None,
        min_priority: Optional[TaskPriority] = None,
    ) -> List[Task]:
        """
        Generate tasks from multiple markups.

        Args:
            markups: List of markup dictionaries
            filter_categories: Only generate tasks for these categories
            min_priority: Only generate tasks at or above this priority

        Returns:
            List of Task objects
        """
        # First categorize all markups if not already done
        categorized = []
        for markup in markups:
            if "category" not in markup:
                categorized.extend(self.categorizer.categorize_batch([markup]))
            else:
                categorized.append(markup)

        tasks = []
        priority_order = [p.value for p in TaskPriority]

        for markup in categorized:
            # Get category
            try:
                category = MarkupCategory(markup.get("category", "Unknown"))
            except ValueError:
                category = MarkupCategory.UNKNOWN

            # Filter by category
            if filter_categories and category not in filter_categories:
                continue

            # Generate task
            task = self.generate_task(markup, category)

            # Filter by priority
            if min_priority:
                task_priority_idx = priority_order.index(task.priority)
                min_priority_idx = priority_order.index(min_priority.value)
                if task_priority_idx > min_priority_idx:
                    continue

            tasks.append(task)

        return tasks

    def get_task_summary(self, tasks: List[Task]) -> Dict[str, Any]:
        """Get a summary of generated tasks."""
        by_type = {}
        by_priority = {}
        by_status = {}
        by_assignee = {}

        for task in tasks:
            by_type[task.task_type] = by_type.get(task.task_type, 0) + 1
            by_priority[task.priority] = by_priority.get(task.priority, 0) + 1
            by_status[task.status] = by_status.get(task.status, 0) + 1

            assignee = task.assignee or "Unassigned"
            by_assignee[assignee] = by_assignee.get(assignee, 0) + 1

        return {
            "total_tasks": len(tasks),
            "by_type": by_type,
            "by_priority": by_priority,
            "by_status": by_status,
            "by_assignee": by_assignee,
            "critical_count": by_priority.get("Critical", 0),
            "high_priority_count": by_priority.get("High", 0),
        }


# Convenience function
def generate_tasks_from_markups(
    markups: List[Dict[str, Any]],
    project_name: str = "Project"
) -> List[Task]:
    """Generate tasks from a list of markups."""
    generator = TaskGenerator(project_name=project_name)
    return generator.generate_tasks(markups)


if __name__ == "__main__":
    # Test with sample data
    test_markups = [
        {
            "id": "m1",
            "content": "RFI #123: Please clarify the foundation detail at grid line A-3",
            "page": 5,
            "author": "John Smith",
            "source_file": "Structural_Plans.pdf"
        },
        {
            "id": "m2",
            "content": "SAFETY HAZARD: Fall protection required at opening",
            "page": 12,
            "author": "Safety Inspector",
            "source_file": "Floor_Plans.pdf"
        },
        {
            "id": "m3",
            "content": "Coordinate MEP routing with structural beam",
            "page": 8,
            "author": "MEP Coordinator",
            "source_file": "MEP_Plans.pdf"
        },
        {
            "id": "m4",
            "content": "Correct dimension to 10'-6\"",
            "page": 3,
            "author": "Architect",
            "source_file": "Architectural_Plans.pdf"
        },
    ]

    generator = TaskGenerator(
        project_name="Sample Project",
        auto_assign=True,
        generate_due_dates=True
    )

    print("Generating tasks from markups:\n")
    tasks = generator.generate_tasks(test_markups)

    for task in tasks:
        print(f"{'='*60}")
        print(f"ID: {task.id}")
        print(f"Title: {task.title}")
        print(f"Type: {task.task_type} | Priority: {task.priority}")
        print(f"Assignee: {task.assignee} | Due: {task.due_date}")
        print(f"Tags: {task.tags}")
        print()

    print("\n--- Summary ---")
    summary = generator.get_task_summary(tasks)
    print(f"Total tasks: {summary['total_tasks']}")
    print(f"Critical: {summary['critical_count']}, High: {summary['high_priority_count']}")
    print(f"By type: {summary['by_type']}")

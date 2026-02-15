"""
Utility Functions - Helper functions for the Project Status Dashboard.

Written live while you watch the monitor!
"""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import json


def format_currency(amount: float) -> str:
    """Format amount as currency."""
    return f"${amount:,.2f}"


def format_hours(hours: float) -> str:
    """Format hours with appropriate precision."""
    if hours >= 100:
        return f"{hours:,.0f}h"
    return f"{hours:.1f}h"


def days_between(date1: date, date2: date) -> int:
    """Calculate days between two dates."""
    return (date2 - date1).days


def business_days_between(start: date, end: date) -> int:
    """Calculate business days between two dates (excludes weekends)."""
    days = 0
    current = start
    while current < end:
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            days += 1
        current += timedelta(days=1)
    return days


def calculate_burn_rate(hours_spent: float, start_date: date) -> float:
    """Calculate average hours burned per week."""
    weeks = max(1, days_between(start_date, date.today()) / 7)
    return hours_spent / weeks


def estimate_completion(hours_remaining: float, burn_rate: float) -> Optional[date]:
    """Estimate completion date based on burn rate."""
    if burn_rate <= 0:
        return None
    weeks_needed = hours_remaining / burn_rate
    return date.today() + timedelta(weeks=weeks_needed)


def health_color(score: int) -> str:
    """Get color code for health score."""
    if score >= 80:
        return "#3fb950"  # Green
    elif score >= 60:
        return "#d29922"  # Yellow
    else:
        return "#f85149"  # Red


def status_emoji(status: str) -> str:
    """Get emoji for project status."""
    emojis = {
        "on_track": "✅",
        "at_risk": "⚠️",
        "behind": "🔴",
        "ahead": "🚀",
        "on_hold": "⏸️"
    }
    return emojis.get(status, "❓")


def load_json_file(filepath: str) -> Dict:
    """Safely load JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json_file(data: Dict, filepath: str):
    """Save data to JSON file with pretty formatting."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)


class DateRange:
    """Helper class for date range operations."""

    def __init__(self, start: date, end: date):
        self.start = start
        self.end = end

    @property
    def days(self) -> int:
        return days_between(self.start, self.end)

    @property
    def business_days(self) -> int:
        return business_days_between(self.start, self.end)

    @property
    def weeks(self) -> float:
        return self.days / 7

    def contains(self, d: date) -> bool:
        return self.start <= d <= self.end

    def __repr__(self):
        return f"DateRange({self.start} to {self.end}, {self.days} days)"


# Built live by Christopher the Builder! 🔨
print("Utils module loaded successfully!")

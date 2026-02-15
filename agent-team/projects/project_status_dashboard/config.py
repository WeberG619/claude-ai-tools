"""
Configuration - Dashboard settings and defaults.

🔴 THIS FILE SHOULD APPEAR LIVE IN THE MONITOR! 🔴
"""
from dataclasses import dataclass
from typing import Dict, List
from pathlib import Path


@dataclass
class DashboardConfig:
    """Configuration for the project dashboard."""

    # Display settings
    theme: str = "dark"
    refresh_interval: int = 30  # seconds
    max_projects_per_page: int = 20

    # Health score thresholds
    health_good: int = 80
    health_warning: int = 60

    # Alert settings
    milestone_warning_days: int = 7
    budget_warning_percent: int = 80

    # Default phases
    phases: List[str] = None

    def __post_init__(self):
        if self.phases is None:
            self.phases = [
                "Programming",
                "Schematic Design",
                "Design Development",
                "Construction Documents",
                "Bidding",
                "Construction Administration",
                "Closeout"
            ]


# Default configuration
DEFAULT_CONFIG = DashboardConfig()


# Phase colors for visualization
PHASE_COLORS: Dict[str, str] = {
    "Programming": "#9b59b6",
    "Schematic Design": "#3498db",
    "Design Development": "#2ecc71",
    "Construction Documents": "#f39c12",
    "Bidding": "#e74c3c",
    "Construction Administration": "#1abc9c",
    "Closeout": "#95a5a6",
    "Complete": "#27ae60",
    "On Hold": "#7f8c8d"
}


# Status indicators
STATUS_CONFIG = {
    "on_track": {"color": "#3fb950", "icon": "✅", "label": "On Track"},
    "at_risk": {"color": "#d29922", "icon": "⚠️", "label": "At Risk"},
    "behind": {"color": "#f85149", "icon": "🔴", "label": "Behind"},
    "ahead": {"color": "#58a6ff", "icon": "🚀", "label": "Ahead"},
    "on_hold": {"color": "#8b949e", "icon": "⏸️", "label": "On Hold"}
}


def get_config_path() -> Path:
    """Get path to user config file."""
    return Path.home() / ".project_dashboard" / "config.json"


# Written by Christopher - did you see it appear? 🔨

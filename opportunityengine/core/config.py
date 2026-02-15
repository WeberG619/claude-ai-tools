"""Configuration for OpportunityEngine."""

from __future__ import annotations

import os

# ── Paths ────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "pipeline.db")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Existing infrastructure paths
AUTONOMOUS_AGENT_DIR = "/mnt/d/_CLAUDE-TOOLS/autonomous-agent"
AUTONOMOUS_BROWSER_DIR = "/mnt/d/_CLAUDE-TOOLS/autonomous-browser"
VOICE_SCRIPT = "/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py"

# ── Weber's Skill Inventory ─────────────────────────────────────────

SKILLS = {
    # Primary (Expert)
    "revit": {"level": "expert", "keywords": ["revit", "revit api", "pyrevit", "dynamo"]},
    "revit_api": {"level": "expert", "keywords": ["revit api", "revit plugin", "revit add-in", "revit addin"]},
    "bim": {"level": "expert", "keywords": ["bim", "building information model", "bim coordination"]},
    "construction_documents": {"level": "expert", "keywords": ["construction documents", "cd set", "permit drawings", "architectural drawings"]},
    "python": {"level": "expert", "keywords": ["python", "python3", "django", "flask", "fastapi"]},
    "csharp": {"level": "expert", "keywords": ["c#", "csharp", ".net", "dotnet", "wpf"]},
    "ai_agents": {"level": "expert", "keywords": ["ai agent", "claude", "llm", "mcp", "autonomous agent", "ai automation"]},
    "automation": {"level": "expert", "keywords": ["automation", "workflow automation", "scripting", "rpa"]},

    # Strong
    "autocad": {"level": "strong", "keywords": ["autocad", "autolisp", "cad"]},
    "javascript": {"level": "strong", "keywords": ["javascript", "typescript", "node", "react", "nextjs"]},
    "web_development": {"level": "strong", "keywords": ["web development", "html", "css", "frontend", "backend", "full stack"]},
    "api_development": {"level": "strong", "keywords": ["api", "rest api", "graphql", "api development"]},
    "database": {"level": "strong", "keywords": ["sql", "sqlite", "postgresql", "database", "mongodb"]},
    "git": {"level": "strong", "keywords": ["git", "github", "version control"]},

    # Competent
    "architecture": {"level": "competent", "keywords": ["architecture", "architectural design", "building design"]},
    "project_management": {"level": "competent", "keywords": ["project management", "coordination", "scheduling"]},
    "linux": {"level": "competent", "keywords": ["linux", "ubuntu", "bash", "shell scripting"]},
    "docker": {"level": "competent", "keywords": ["docker", "containerization", "docker-compose"]},
    "cloud": {"level": "competent", "keywords": ["aws", "azure", "cloud", "gcp"]},
    "machine_learning": {"level": "competent", "keywords": ["machine learning", "ml", "computer vision", "deep learning"]},
    "web_scraping": {"level": "strong", "keywords": ["web scraping", "scraping", "data extraction", "scrapy", "selenium", "puppeteer", "playwright"]},
    "data_processing": {"level": "strong", "keywords": ["data processing", "etl", "data pipeline", "pandas", "data analysis", "excel automation"]},
    "devops": {"level": "competent", "keywords": ["devops", "ci/cd", "github actions", "terraform", "infrastructure"]},
    "chatbot": {"level": "strong", "keywords": ["chatbot", "chat bot", "conversational ai", "discord bot", "telegram bot", "slack bot"]},
}

# Flat list of all skill keywords for matching
ALL_SKILL_KEYWORDS = []
for skill_data in SKILLS.values():
    ALL_SKILL_KEYWORDS.extend(skill_data["keywords"])

# Skill level weights for scoring
SKILL_LEVEL_WEIGHTS = {
    "expert": 1.0,
    "strong": 0.75,
    "competent": 0.5,
}

# ── Search Terms Per Platform ────────────────────────────────────────

UPWORK_SEARCH_TERMS = [
    "Revit",
    "Revit API",
    "BIM",
    "AutoCAD",
    "construction documents",
    "Python automation",
    "AI agent",
    "Claude API",
    "Revit plugin",
    "Dynamo",
    "building information modeling",
    "architectural automation",
    "MCP server",
]

FREELANCER_SEARCH_TERMS = [
    "Revit",
    "Revit API",
    "BIM",
    "AutoCAD",
    "Python automation",
    "C# programming",
    "AI automation",
    "building information modeling",
]

GITHUB_SEARCH_TERMS = [
    "bounty",
    "reward",
    "paid",
    "sponsored",
]

GITHUB_LANGUAGES = [
    "Python",
    "C#",
    "TypeScript",
    "JavaScript",
    "Rust",
]

# ── Scoring Weights ──────────────────────────────────────────────────

SCORING_WEIGHTS = {
    "skill_match": 0.35,
    "budget_roi": 0.25,
    "competition": 0.20,
    "effort": 0.15,
    "strategic_fit": 0.05,
}

# ── Scoring Thresholds ───────────────────────────────────────────────

SCORE_HOT = 80          # Immediate alert (voice + Telegram)
SCORE_QUALIFIED = 65    # Queue for review (daily digest)
SCORE_LOG_ONLY = 50     # Log only (available in dashboard)
# Below 50: auto-dismiss

# ── Budget Parameters ────────────────────────────────────────────────

# Estimated hourly rate for ROI calculations
HOURLY_RATE = 75  # USD
MIN_ACCEPTABLE_HOURLY = 40  # USD

# ── Scout Frequencies (minutes) ──────────────────────────────────────

SCAN_INTERVALS = {
    "upwork": 30,
    "github": 120,
    "freelancer": 60,
    "reddit": 90,
    "hackernews": 360,   # HN threads update monthly, check every 6h
    "remoteok": 180,     # New jobs posted a few times daily
    "linkedin": 180,
}

# Peak hours (UTC) - scan more frequently
PEAK_HOURS_UTC = range(14, 20)  # 9 AM - 3 PM EST

# ── Notification Settings ────────────────────────────────────────────

DAILY_DIGEST_HOUR_UTC = 16  # 8 AM PST / 11 AM EST

# ── Template Mapping ─────────────────────────────────────────────────

TEMPLATE_CATEGORIES = {
    "revit_bim": {
        "file": "revit_bim.md",
        "match_skills": ["revit", "revit_api", "bim", "autocad", "construction_documents"],
    },
    "construction_docs": {
        "file": "construction_docs.md",
        "match_skills": ["construction_documents", "architecture", "bim"],
    },
    "software_dev": {
        "file": "software_dev.md",
        "match_skills": ["python", "csharp", "javascript", "web_development", "api_development", "database"],
    },
    "ai_automation": {
        "file": "ai_automation.md",
        "match_skills": ["ai_agents", "automation", "python", "machine_learning"],
    },
    "github_bounty": {
        "file": "github_bounty.md",
        "match_skills": ["python", "csharp", "javascript", "git"],
    },
    "web_scraping": {
        "file": "web_scraping.md",
        "match_skills": ["web_scraping", "python", "data_processing", "automation"],
    },
    "general": {
        "file": "general.md",
        "match_skills": ["python", "javascript", "api_development", "database", "automation"],
    },
}

# ── Strategic Priorities ─────────────────────────────────────────────

# Skills we want to build portfolio in (bonus scoring)
PORTFOLIO_PRIORITIES = [
    "ai_agents",
    "revit_api",
    "automation",
]

# Preferred budget ranges (sweet spot)
PREFERRED_BUDGET_MIN = 500
PREFERRED_BUDGET_MAX = 10000

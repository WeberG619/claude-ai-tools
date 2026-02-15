"""
Markup categorizer - Classify markups by type and intent.

Categories:
- RFI (Request for Information)
- ASI (Architect's Supplemental Instructions)
- Correction / Fix
- Clarification
- Dimension / Measurement
- Note / Comment
- Approval / Acceptance
- Rejection
- Question
- Coordination Issue
"""

import re
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field

# Import markup types from extractors
try:
    from .extractors.pdf_extractor import Markup
    from .extractors.bluebeam_extractor import BluebeamMarkup
except ImportError:
    Markup = None
    BluebeamMarkup = None


class MarkupCategory(Enum):
    """Categories for construction document markups."""
    RFI = "RFI"
    ASI = "ASI"
    PR = "PR"  # Proposal Request
    CORRECTION = "Correction"
    CLARIFICATION = "Clarification"
    DIMENSION = "Dimension"
    NOTE = "Note"
    APPROVAL = "Approval"
    REJECTION = "Rejection"
    QUESTION = "Question"
    COORDINATION = "Coordination"
    REVIEW_COMMENT = "Review Comment"
    PUNCH_LIST = "Punch List"
    SAFETY = "Safety"
    CODE_ISSUE = "Code Issue"
    SUBMITTAL = "Submittal"
    UNKNOWN = "Unknown"


@dataclass
class CategoryRule:
    """Rule for categorizing markups."""
    category: MarkupCategory
    keywords: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)  # Regex patterns
    subjects: List[str] = field(default_factory=list)  # Bluebeam subjects
    colors: List[str] = field(default_factory=list)  # Color codes
    weight: float = 1.0


class MarkupCategorizer:
    """Categorize markups based on content, type, and context."""

    DEFAULT_RULES = [
        CategoryRule(
            category=MarkupCategory.RFI,
            keywords=["rfi", "request for information", "need info", "please clarify",
                      "please confirm", "verify", "information needed", "awaiting response"],
            patterns=[r"RFI[\s#-]*\d+", r"request\s+for\s+information"],
            subjects=["RFI", "Request"],
            colors=["#FF0000", "#ff0000"],  # Red often used for RFIs
            weight=1.5,
        ),
        CategoryRule(
            category=MarkupCategory.ASI,
            keywords=["asi", "supplemental instruction", "architect instruction",
                      "design change", "revision", "change to"],
            patterns=[r"ASI[\s#-]*\d+", r"bulletin[\s#-]*\d+"],
            subjects=["ASI", "Bulletin", "Change"],
            weight=1.5,
        ),
        CategoryRule(
            category=MarkupCategory.PR,
            keywords=["pr", "proposal request", "pricing", "cost", "change order",
                      "additional work", "extra"],
            patterns=[r"PR[\s#-]*\d+", r"CO[\s#-]*\d+"],
            subjects=["PR", "Proposal", "Change Order"],
            weight=1.4,
        ),
        CategoryRule(
            category=MarkupCategory.CORRECTION,
            keywords=["correct", "fix", "revise", "change", "update", "error",
                      "mistake", "wrong", "incorrect", "redo", "replace"],
            patterns=[r"correct\s+to", r"should\s+be", r"change\s+to"],
            subjects=["Correction", "Fix", "Revision"],
            colors=["#FF6600", "#ff6600"],  # Orange for corrections
            weight=1.3,
        ),
        CategoryRule(
            category=MarkupCategory.CLARIFICATION,
            keywords=["clarify", "clarification", "explain", "detail", "specify",
                      "define", "elaborate", "unclear"],
            patterns=[r"need\s+clarification", r"please\s+explain"],
            subjects=["Clarification", "Detail"],
            weight=1.2,
        ),
        CategoryRule(
            category=MarkupCategory.DIMENSION,
            keywords=["dim", "dimension", "measurement", "size", "length", "width",
                      "height", "distance", "feet", "inches", "meters"],
            patterns=[r"\d+['\"]", r"\d+\s*ft", r"\d+\s*in", r"\d+-\d+"],
            subjects=["Dimension", "Measurement", "Calibrate"],
            weight=1.0,
        ),
        CategoryRule(
            category=MarkupCategory.QUESTION,
            keywords=["?", "question", "what", "why", "how", "when", "where", "which",
                      "who", "is this", "does this", "can we", "should we"],
            patterns=[r"\?$", r"^(what|why|how|when|where|which|who)\s"],
            subjects=["Question"],
            colors=["#0000FF", "#0000ff"],  # Blue for questions
            weight=1.1,
        ),
        CategoryRule(
            category=MarkupCategory.APPROVAL,
            keywords=["approved", "accepted", "ok", "okay", "good", "confirmed",
                      "verified", "checked", "complete", "done", "pass"],
            patterns=[r"^approved", r"^ok\b", r"^accepted"],
            subjects=["Approval", "Accepted", "Verified"],
            colors=["#00FF00", "#00ff00", "#008000"],  # Green for approval
            weight=1.4,
        ),
        CategoryRule(
            category=MarkupCategory.REJECTION,
            keywords=["rejected", "denied", "no", "not accepted", "failed", "fail",
                      "unacceptable", "redo", "revise and resubmit"],
            patterns=[r"^rejected", r"^denied", r"not\s+approved"],
            subjects=["Rejected", "Denied", "Failed"],
            colors=["#FF0000", "#ff0000"],  # Red for rejection
            weight=1.4,
        ),
        CategoryRule(
            category=MarkupCategory.COORDINATION,
            keywords=["coordinate", "coordination", "conflict", "clash", "interference",
                      "overlap", "mep", "structural", "civil", "architectural"],
            patterns=[r"coordinate\s+with", r"clash\s+detected", r"conflicts?\s+with"],
            subjects=["Coordination", "Clash", "Conflict"],
            colors=["#FF00FF", "#ff00ff"],  # Magenta for coordination
            weight=1.3,
        ),
        CategoryRule(
            category=MarkupCategory.PUNCH_LIST,
            keywords=["punch", "punchlist", "punch list", "deficiency", "incomplete",
                      "outstanding", "remaining", "to be completed"],
            patterns=[r"punch\s*list", r"deficiency\s*list"],
            subjects=["Punch", "Punch List", "Deficiency"],
            weight=1.2,
        ),
        CategoryRule(
            category=MarkupCategory.SAFETY,
            keywords=["safety", "hazard", "danger", "warning", "caution", "osha",
                      "ppe", "fall protection", "fire", "egress"],
            patterns=[r"safety\s+concern", r"hazard\s+identified"],
            subjects=["Safety", "Hazard", "Warning"],
            colors=["#FFFF00", "#ffff00"],  # Yellow for safety
            weight=1.5,
        ),
        CategoryRule(
            category=MarkupCategory.CODE_ISSUE,
            keywords=["code", "violation", "ibc", "nfpa", "ada", "accessibility",
                      "compliance", "regulation", "requirement"],
            patterns=[r"code\s+violation", r"not\s+compliant", r"ibc\s+\d+"],
            subjects=["Code", "Compliance", "ADA"],
            weight=1.4,
        ),
        CategoryRule(
            category=MarkupCategory.SUBMITTAL,
            keywords=["submittal", "submit", "shop drawing", "product data",
                      "sample", "material", "specification"],
            patterns=[r"submittal[\s#-]*\d+", r"shop\s+drawing"],
            subjects=["Submittal", "Shop Drawing", "Sample"],
            weight=1.2,
        ),
        CategoryRule(
            category=MarkupCategory.REVIEW_COMMENT,
            keywords=["review", "comment", "note", "observation", "see", "refer",
                      "per", "as noted", "fyi", "for your information"],
            subjects=["Comment", "Note", "Review"],
            weight=0.8,  # Lower weight as it's more generic
        ),
        CategoryRule(
            category=MarkupCategory.NOTE,
            keywords=["note", "see", "refer to", "per", "as shown", "typical"],
            subjects=["Note", "Text", "Callout"],
            weight=0.5,  # Lowest weight - catch-all
        ),
    ]

    def __init__(self, custom_rules: Optional[List[CategoryRule]] = None):
        """
        Initialize the categorizer with rules.

        Args:
            custom_rules: Optional custom rules to add or override defaults
        """
        self.rules = self.DEFAULT_RULES.copy()
        if custom_rules:
            # Add custom rules at the beginning (higher priority)
            self.rules = custom_rules + self.rules

        # Compile regex patterns
        self._compiled_patterns = {}
        for rule in self.rules:
            self._compiled_patterns[rule.category] = [
                re.compile(p, re.IGNORECASE) for p in rule.patterns
            ]

    def categorize(
        self,
        markup: Union["Markup", "BluebeamMarkup", Dict[str, Any]]
    ) -> MarkupCategory:
        """
        Categorize a single markup.

        Args:
            markup: Markup object or dictionary with markup data

        Returns:
            MarkupCategory enum value
        """
        scores = self.get_category_scores(markup)
        if not scores:
            return MarkupCategory.UNKNOWN

        # Return highest scoring category
        return max(scores, key=scores.get)

    def get_category_scores(
        self,
        markup: Union["Markup", "BluebeamMarkup", Dict[str, Any]]
    ) -> Dict[MarkupCategory, float]:
        """
        Get scores for all categories for a markup.

        Args:
            markup: Markup object or dictionary

        Returns:
            Dictionary of category -> score
        """
        # Normalize to dictionary
        if hasattr(markup, "to_dict"):
            data = markup.to_dict()
        elif isinstance(markup, dict):
            data = markup
        else:
            data = {}

        # Extract text fields to analyze
        text_content = " ".join([
            str(data.get("content", "")),
            str(data.get("comments", "")),
            str(data.get("subject", "")),
            str(data.get("label", "")),
        ]).lower()

        subject = str(data.get("subject", "")).lower()
        color = str(data.get("color", "")).lower()

        scores = {}

        for rule in self.rules:
            score = 0.0

            # Check keywords
            for keyword in rule.keywords:
                if keyword.lower() in text_content:
                    score += 1.0

            # Check regex patterns
            for pattern in self._compiled_patterns.get(rule.category, []):
                if pattern.search(text_content):
                    score += 2.0  # Patterns are more specific

            # Check subjects (Bluebeam markup types)
            for subj in rule.subjects:
                if subj.lower() in subject:
                    score += 3.0  # Subject match is very strong signal

            # Check colors
            for rule_color in rule.colors:
                if rule_color.lower() == color:
                    score += 1.5

            # Apply weight
            if score > 0:
                scores[rule.category] = score * rule.weight

        return scores

    def categorize_batch(
        self,
        markups: List[Union["Markup", "BluebeamMarkup", Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Categorize multiple markups and return enriched data.

        Args:
            markups: List of markup objects or dictionaries

        Returns:
            List of dictionaries with added category information
        """
        results = []

        for markup in markups:
            # Normalize to dictionary
            if hasattr(markup, "to_dict"):
                data = markup.to_dict()
            elif isinstance(markup, dict):
                data = markup.copy()
            else:
                data = {}

            # Add category information
            category = self.categorize(markup)
            scores = self.get_category_scores(markup)

            data["category"] = category.value
            data["category_confidence"] = scores.get(category, 0.0)
            data["all_categories"] = {k.value: v for k, v in scores.items()}

            results.append(data)

        return results

    def get_summary(
        self,
        markups: List[Union["Markup", "BluebeamMarkup", Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Get a summary of categorized markups.

        Args:
            markups: List of markups

        Returns:
            Summary dictionary with counts and statistics
        """
        categorized = self.categorize_batch(markups)

        category_counts = {}
        high_priority = []
        action_required = []

        priority_categories = {
            MarkupCategory.RFI,
            MarkupCategory.ASI,
            MarkupCategory.CORRECTION,
            MarkupCategory.SAFETY,
            MarkupCategory.CODE_ISSUE,
            MarkupCategory.REJECTION,
        }

        action_categories = {
            MarkupCategory.RFI,
            MarkupCategory.QUESTION,
            MarkupCategory.CORRECTION,
            MarkupCategory.PUNCH_LIST,
            MarkupCategory.COORDINATION,
        }

        for item in categorized:
            cat = item.get("category", "Unknown")
            category_counts[cat] = category_counts.get(cat, 0) + 1

            cat_enum = MarkupCategory(cat) if cat in [c.value for c in MarkupCategory] else None

            if cat_enum in priority_categories:
                high_priority.append(item)

            if cat_enum in action_categories:
                action_required.append(item)

        return {
            "total_markups": len(markups),
            "by_category": category_counts,
            "high_priority_count": len(high_priority),
            "action_required_count": len(action_required),
            "high_priority_items": high_priority[:10],  # Top 10
            "action_required_items": action_required[:10],
        }


# Convenience function
def categorize_markups(
    markups: List[Union["Markup", "BluebeamMarkup", Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """Categorize a list of markups."""
    categorizer = MarkupCategorizer()
    return categorizer.categorize_batch(markups)


if __name__ == "__main__":
    # Test with sample data
    test_markups = [
        {"content": "RFI #123: Please clarify the foundation detail", "subject": "Text"},
        {"content": "ASI-05: Change door hardware to lever type", "subject": "Note"},
        {"content": "Correct dimension - should be 10'-6\" not 10'-0\"", "subject": "Dimension"},
        {"content": "Approved as submitted", "subject": "Stamp", "color": "#00FF00"},
        {"content": "Coordinate with MEP - duct conflicts with beam", "subject": "Cloud"},
        {"content": "Code violation: Egress width insufficient per IBC", "subject": "Callout"},
        {"content": "General note about the project", "subject": "Note"},
    ]

    categorizer = MarkupCategorizer()

    print("Categorizing test markups:\n")
    for markup in test_markups:
        category = categorizer.categorize(markup)
        scores = categorizer.get_category_scores(markup)
        top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]

        print(f"Content: {markup['content'][:50]}...")
        print(f"  Category: {category.value}")
        print(f"  Top scores: {[(c.value, f'{s:.1f}') for c, s in top_scores]}")
        print()

    print("\n--- Summary ---")
    summary = categorizer.get_summary(test_markups)
    print(f"Total: {summary['total_markups']}")
    print(f"By category: {summary['by_category']}")
    print(f"High priority: {summary['high_priority_count']}")
    print(f"Action required: {summary['action_required_count']}")

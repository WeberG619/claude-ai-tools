#!/usr/bin/env python3
"""
Voice Intent Parser for Wispr Flow
Parses natural language (especially voice transcriptions) into actionable intents.

Handles:
1. Voice transcription errors (see voice-corrections.md)
2. Natural language commands
3. Ambiguous requests
4. Context-aware interpretation
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Intent:
    """A parsed user intent."""
    action: str
    target: Optional[str]
    parameters: Dict
    confidence: float
    original_text: str
    corrections_applied: List[str]

class VoiceCorrections:
    """Handles common voice transcription errors."""

    # Word-level corrections
    WORD_CORRECTIONS = {
        # Software names
        "reddit": "revit",
        "read it": "revit",
        "read": "revit",  # Context-dependent
        "rabbit": "revit",
        "rivot": "revit",
        "rebbit": "revit",

        # Architecture terms
        "see the": "CD",
        "cd's": "CDs",
        "seeds": "CDs",
        "seedy": "CD",

        # Technical terms
        "em see pee": "MCP",
        "mcb": "MCP",
        "dll": "DLL",
        "a pie": "API",

        # Common mishears
        "wait": "wall",  # Context-dependent
        "door": "door",
        "flour": "floor",
        "flour plan": "floor plan",
        "sweet": "sheet",
        "she": "sheet",  # Context-dependent

        # Numbers often misheard
        "won": "one",
        "to": "two",  # Context-dependent
        "too": "two",
        "for": "four",  # Context-dependent
        "ate": "eight",
    }

    # Phrase-level corrections
    PHRASE_CORRECTIONS = {
        "open reddit": "open revit",
        "in reddit": "in revit",
        "reddit model": "revit model",
        "reddit file": "revit file",
        "the reddit": "the revit",
        "check reddit": "check revit",
        "reddit is": "revit is",
        "go to reddit": "go to revit",
        "switch to reddit": "switch to revit",
        "construction documents": "CDs",
        "see these": "CDs",
        "flour plans": "floor plans",
        "sweet number": "sheet number",
    }

    @classmethod
    def apply_corrections(cls, text: str) -> Tuple[str, List[str]]:
        """Apply corrections to text. Returns (corrected_text, list_of_corrections)."""
        corrections_applied = []
        corrected = text.lower()

        # Apply phrase corrections first (more specific)
        for phrase, correction in cls.PHRASE_CORRECTIONS.items():
            if phrase in corrected:
                corrected = corrected.replace(phrase, correction)
                corrections_applied.append(f"'{phrase}' -> '{correction}'")

        # Apply word corrections with context awareness
        words = corrected.split()
        for i, word in enumerate(words):
            if word in cls.WORD_CORRECTIONS:
                # Context checks for ambiguous words
                if word == "read" and i + 1 < len(words) and words[i + 1] not in ["the", "this", "that", "a"]:
                    words[i] = cls.WORD_CORRECTIONS[word]
                    corrections_applied.append(f"'{word}' -> '{cls.WORD_CORRECTIONS[word]}'")
                elif word not in ["read", "wait", "to", "for", "she"]:  # Skip ambiguous without context
                    words[i] = cls.WORD_CORRECTIONS[word]
                    corrections_applied.append(f"'{word}' -> '{cls.WORD_CORRECTIONS[word]}'")

        return " ".join(words), corrections_applied


class IntentParser:
    """Parses natural language into structured intents."""

    # Intent patterns (regex -> (action, target_group, params_extractor))
    PATTERNS = [
        # Revit commands
        (r"(?:create|make|add|draw|place)\s+(?:a\s+)?(\d+)?\s*(wall|door|window|room|floor|ceiling)s?",
         "revit_create", 1, lambda m: {"count": int(m.group(1) or 1), "element_type": m.group(2)}),

        (r"(?:delete|remove|erase)\s+(?:the\s+)?(\d+)?\s*(wall|door|window|element)s?",
         "revit_delete", 2, lambda m: {"count": int(m.group(1) or 1), "element_type": m.group(2)}),

        (r"(?:select|pick|choose)\s+(?:the\s+)?(\d+)?\s*(wall|door|window|element)s?",
         "revit_select", 2, lambda m: {"count": int(m.group(1) or 1), "element_type": m.group(2)}),

        (r"(?:tag|label)\s+(?:all\s+)?(?:the\s+)?(\d+)?\s*(door|window|room|wall)s?",
         "revit_tag", 2, lambda m: {"count": m.group(1), "element_type": m.group(2)}),

        (r"(?:dimension|add dimensions to)\s+(?:the\s+)?(wall|floor plan|view)",
         "revit_dimension", 1, lambda m: {"target": m.group(1)}),

        (r"(?:go to|open|show|switch to)\s+(?:the\s+)?(?:view\s+)?([a-zA-Z0-9\s-]+?)(?:\s+view)?$",
         "revit_view", 1, lambda m: {"view_name": m.group(1).strip()}),

        (r"(?:create|make|add)\s+(?:a\s+)?(?:new\s+)?sheet\s*(?:called|named)?\s*([a-zA-Z0-9\s-]*)",
         "revit_sheet", 1, lambda m: {"sheet_name": m.group(1).strip() if m.group(1) else None}),

        # Application commands
        (r"(?:open|launch|start)\s+(revit|bluebeam|chrome|edge|vs code|code)",
         "app_open", 1, lambda m: {"app": m.group(1)}),

        (r"(?:switch to|go to|focus)\s+(revit|bluebeam|chrome)",
         "app_switch", 1, lambda m: {"app": m.group(1)}),

        (r"(?:close|quit|exit)\s+(revit|bluebeam)",
         "app_close", 1, lambda m: {"app": m.group(1)}),

        # File commands
        (r"(?:open|load)\s+(?:the\s+)?(?:file\s+)?([a-zA-Z0-9\s_-]+\.(?:rvt|pdf|dwg))",
         "file_open", 1, lambda m: {"filename": m.group(1)}),

        (r"(?:save|export)\s+(?:the\s+)?(?:file|model|document)?\s*(?:as\s+)?([a-zA-Z0-9\s_-]*)",
         "file_save", 1, lambda m: {"filename": m.group(1).strip() if m.group(1) else None}),

        # Query commands
        (r"(?:what|show me|list|get)\s+(?:the\s+)?(?:all\s+)?(wall|door|window|room|level|sheet)s?",
         "query", 1, lambda m: {"element_type": m.group(1)}),

        (r"(?:how many|count)\s+(wall|door|window|room|sheet)s?",
         "query_count", 1, lambda m: {"element_type": m.group(1)}),

        (r"(?:what|which)\s+(?:project|model|file)\s+(?:is\s+)?(?:open|active)?",
         "query_project", None, lambda m: {}),

        # Navigation
        (r"(?:go to|navigate to|show)\s+(?:the\s+)?(first|second|third|ground|roof)\s*(?:floor)?(?:\s+plan)?",
         "navigate_level", 1, lambda m: {"level": m.group(1)}),

        (r"(?:zoom|fit)\s+(?:to\s+)?(all|extents|selection)",
         "view_zoom", 1, lambda m: {"mode": m.group(1)}),

        # Project commands
        (r"(?:check|verify|review)\s+(?:the\s+)?(CDs|drawings|model|tags|dimensions)",
         "review", 1, lambda m: {"target": m.group(1)}),

        (r"(?:export|print)\s+(?:the\s+)?(CDs|sheets|pdf|dwg)",
         "export", 1, lambda m: {"format": m.group(1)}),
    ]

    def __init__(self):
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), action, target_group, param_fn)
            for pattern, action, target_group, param_fn in self.PATTERNS
        ]

    def parse(self, text: str, context: Dict = None) -> Intent:
        """Parse text into an Intent."""
        context = context or {}

        # Apply voice corrections
        corrected_text, corrections = VoiceCorrections.apply_corrections(text)

        # Try to match patterns
        for pattern, action, target_group, param_fn in self.compiled_patterns:
            match = pattern.search(corrected_text)
            if match:
                params = param_fn(match)
                target = match.group(target_group) if target_group and match.lastindex >= target_group else None

                return Intent(
                    action=action,
                    target=target,
                    parameters=params,
                    confidence=0.9 if not corrections else 0.8,
                    original_text=text,
                    corrections_applied=corrections
                )

        # No pattern matched - return unknown intent
        return Intent(
            action="unknown",
            target=None,
            parameters={"raw_text": corrected_text},
            confidence=0.3,
            original_text=text,
            corrections_applied=corrections
        )

    def suggest_clarification(self, intent: Intent) -> Optional[str]:
        """Generate clarification question for ambiguous intent."""
        if intent.action == "unknown":
            return f"I didn't understand '{intent.original_text}'. Did you mean to:\n" \
                   "- Create/modify something in Revit?\n" \
                   "- Open a file or application?\n" \
                   "- Query information?"

        if intent.confidence < 0.7:
            return f"I understood '{intent.action}' but I'm not confident. " \
                   f"Did you mean: {intent.action} {intent.target or ''}?"

        return None


class CommandExecutor:
    """Executes parsed intents."""

    def __init__(self):
        self.action_handlers = {
            "revit_create": self._handle_revit_create,
            "revit_delete": self._handle_revit_delete,
            "revit_tag": self._handle_revit_tag,
            "revit_view": self._handle_revit_view,
            "app_open": self._handle_app_open,
            "app_switch": self._handle_app_switch,
            "query": self._handle_query,
            "query_count": self._handle_query_count,
        }

    def execute(self, intent: Intent) -> Dict:
        """Execute an intent and return result."""
        if intent.action in self.action_handlers:
            return self.action_handlers[intent.action](intent)

        return {
            "status": "not_implemented",
            "action": intent.action,
            "message": f"Action '{intent.action}' is recognized but not yet implemented"
        }

    def _handle_revit_create(self, intent: Intent) -> Dict:
        """Generate Revit create command."""
        element_type = intent.parameters.get("element_type", "element")
        count = intent.parameters.get("count", 1)

        # Map to actual MCP methods
        method_map = {
            "wall": "createWall",
            "door": "placeFamilyInstance",
            "window": "placeFamilyInstance",
            "room": "createRoom",
            "floor": "createFloor",
        }

        method = method_map.get(element_type, "unknown")

        return {
            "status": "ready",
            "mcp_method": method,
            "mcp_params": {"count": count, "element_type": element_type},
            "command": f"Create {count} {element_type}(s) using {method}"
        }

    def _handle_revit_delete(self, intent: Intent) -> Dict:
        return {
            "status": "ready",
            "mcp_method": "deleteElements",
            "needs_selection": True,
            "command": f"Delete selected {intent.parameters.get('element_type', 'elements')}"
        }

    def _handle_revit_tag(self, intent: Intent) -> Dict:
        element_type = intent.parameters.get("element_type", "element")
        return {
            "status": "ready",
            "mcp_method": "tagElements",
            "mcp_params": {"category": element_type},
            "command": f"Tag all {element_type}s"
        }

    def _handle_revit_view(self, intent: Intent) -> Dict:
        view_name = intent.parameters.get("view_name", "")
        return {
            "status": "ready",
            "mcp_method": "setActiveView",
            "mcp_params": {"viewName": view_name},
            "command": f"Switch to view: {view_name}"
        }

    def _handle_app_open(self, intent: Intent) -> Dict:
        app = intent.parameters.get("app", "").lower()

        app_paths = {
            "revit": r"C:\Program Files\Autodesk\Revit 2026\Revit.exe",
            "bluebeam": r"C:\Program Files\Bluebeam Software\Bluebeam Revu\2017\Revu\Revu.exe",
            "chrome": "chrome",
            "edge": "msedge",
            "vs code": "code",
            "code": "code",
        }

        return {
            "status": "ready",
            "shell_command": f'start "" "{app_paths.get(app, app)}"',
            "command": f"Open {app}"
        }

    def _handle_app_switch(self, intent: Intent) -> Dict:
        app = intent.parameters.get("app", "")
        return {
            "status": "ready",
            "shell_command": f'powershell -Command "(Get-Process {app} | Select-Object -First 1).MainWindowHandle | ForEach-Object {{ [void][System.Runtime.InteropServices.Marshal]::SetForegroundWindow($_) }}"',
            "command": f"Switch to {app}"
        }

    def _handle_query(self, intent: Intent) -> Dict:
        element_type = intent.parameters.get("element_type", "element")

        category_map = {
            "wall": "Walls",
            "door": "Doors",
            "window": "Windows",
            "room": "Rooms",
            "level": "Levels",
            "sheet": "Sheets",
        }

        return {
            "status": "ready",
            "mcp_method": "getElementsByCategory",
            "mcp_params": {"category": category_map.get(element_type, element_type)},
            "command": f"Query all {element_type}s"
        }

    def _handle_query_count(self, intent: Intent) -> Dict:
        result = self._handle_query(intent)
        result["post_process"] = "count"
        return result


def main():
    """CLI interface."""
    import sys

    parser = IntentParser()
    executor = CommandExecutor()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "parse" and len(sys.argv) > 2:
            text = " ".join(sys.argv[2:])
            intent = parser.parse(text)

            result = {
                "action": intent.action,
                "target": intent.target,
                "parameters": intent.parameters,
                "confidence": intent.confidence,
                "corrections": intent.corrections_applied,
            }

            clarification = parser.suggest_clarification(intent)
            if clarification:
                result["clarification_needed"] = clarification

            print(json.dumps(result, indent=2))

        elif cmd == "execute" and len(sys.argv) > 2:
            text = " ".join(sys.argv[2:])
            intent = parser.parse(text)
            result = executor.execute(intent)

            print(json.dumps({
                "intent": {
                    "action": intent.action,
                    "confidence": intent.confidence,
                    "corrections": intent.corrections_applied,
                },
                "execution": result
            }, indent=2))

        elif cmd == "correct" and len(sys.argv) > 2:
            text = " ".join(sys.argv[2:])
            corrected, corrections = VoiceCorrections.apply_corrections(text)
            print(json.dumps({
                "original": text,
                "corrected": corrected,
                "corrections": corrections
            }, indent=2))

        else:
            print('{"error": "Unknown command. Use: parse, execute, or correct"}')
    else:
        print(json.dumps({
            "usage": [
                "parse <text> - Parse natural language into intent",
                "execute <text> - Parse and generate execution plan",
                "correct <text> - Apply voice corrections only"
            ]
        }, indent=2))


if __name__ == "__main__":
    main()

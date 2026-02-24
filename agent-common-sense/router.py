#!/usr/bin/env python3
"""
Agent Auto-Router — Scores user input against agent trigger keywords
and suggests the best matching agent(s).

Usage:
    from router import AgentRouter
    router = AgentRouter()
    matches = router.route("place walls from this PDF")
    # [AgentMatch(name='revit-builder', score=0.85), AgentMatch(name='floor-plan-processor', score=0.62)]

CLI:
    python3 router.py "place walls from this PDF"
    python3 router.py --all   # list all agents with triggers
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict

# Re-use the frontmatter parser from agent_schema
try:
    from agent_schema import parse_yaml_frontmatter
except ImportError:
    # Inline robust parser if agent_schema not importable
    def parse_yaml_frontmatter(filepath):
        content = filepath.read_text(encoding="utf-8", errors="replace")
        if filepath.suffix == ".yaml":
            return _extract_fields(content), ""
        if not content.startswith("---"):
            return None, content
        end = content.find("\n---", 3)
        if end == -1:
            return None, content
        return _extract_fields(content[3:end].strip()), content[end+4:]

    def _extract_fields(text):
        """Extract key agent fields via regex — robust against noisy frontmatter."""
        result = {}
        for key in ("name", "description", "tier", "color"):
            m = re.search(rf'^{key}:\s*(.+)$', text, re.MULTILINE)
            if m:
                result[key] = m.group(1).strip().strip('"').strip("'")
        # triggers: [inline] format
        m = re.search(r'^triggers:\s*\[([^\]]+)\]', text, re.MULTILINE)
        if m:
            result["triggers"] = [v.strip().strip('"').strip("'") for v in m.group(1).split(",") if v.strip()]
        else:
            m = re.search(r'^triggers:\s*$', text, re.MULTILINE)
            if m:
                items = []
                for line in text[m.end():].split("\n"):
                    s = line.strip()
                    if s.startswith("- "):
                        items.append(s[2:].strip().strip('"').strip("'"))
                    elif s and not s.startswith("#"):
                        break
                if items:
                    result["triggers"] = items
        return result


AGENTS_DIR = Path.home() / ".claude" / "agents"


@dataclass
class AgentInfo:
    name: str
    description: str = ""
    triggers: List[str] = field(default_factory=list)
    tier: str = "write"
    color: str = ""
    filepath: str = ""


@dataclass
class AgentMatch:
    name: str
    score: float
    triggers_matched: List[str] = field(default_factory=list)
    tier: str = "write"
    color: str = ""

    def __repr__(self):
        return f"AgentMatch(name='{self.name}', score={self.score:.2f}, matched={self.triggers_matched})"


    # Model tier classification keywords
MODEL_TIER_SIGNALS = {
    "haiku": {
        "keywords": ["search", "find", "list", "read", "check", "status", "explore",
                      "grep", "glob", "lookup", "what is", "show me", "where is"],
        "tier_name": "Light",
        "description": "Read-only research, exploration, simple queries"
    },
    "sonnet": {
        "keywords": ["implement", "build", "create", "fix", "update", "modify", "edit",
                      "refactor", "write", "add", "change", "test", "review", "migrate"],
        "tier_name": "Standard",
        "description": "Implementation, multi-file changes, code review"
    },
    "opus": {
        "keywords": ["architect", "design", "debug complex", "integrate", "critical",
                      "production", "security", "novel", "strategy", "plan complex",
                      "multi-system", "analyze deeply"],
        "tier_name": "Heavy",
        "description": "Architecture, complex debugging, novel problems"
    }
}


def suggest_model_tier(task_description: str) -> str:
    """Suggest the appropriate model tier for a task.

    Returns: 'haiku', 'sonnet', or 'opus'
    Default: 'sonnet' (safe middle ground)
    """
    desc_lower = task_description.lower()

    scores = {"haiku": 0, "sonnet": 0, "opus": 0}

    for tier, info in MODEL_TIER_SIGNALS.items():
        for keyword in info["keywords"]:
            if keyword in desc_lower:
                scores[tier] += 1

    # Default to sonnet if no clear signal
    if max(scores.values()) == 0:
        return "sonnet"

    # If opus scores > 0, it wins (conservative — protect critical work)
    if scores["opus"] > 0:
        return "opus"

    # Otherwise highest score wins
    return max(scores, key=scores.get)


class AgentRouter:
    """Scans agent files, builds trigger index, scores user input."""

    def __init__(self, agents_dir: Path = AGENTS_DIR):
        self.agents_dir = agents_dir
        self.agents: List[AgentInfo] = []
        self._load_agents()

    def _load_agents(self):
        """Load all agent files and extract frontmatter."""
        if not self.agents_dir.exists():
            return

        for f in sorted(self.agents_dir.iterdir()):
            if f.suffix not in (".md", ".yaml") or f.name == "AGENT_PROTOCOL.md":
                continue
            try:
                fm, _ = parse_yaml_frontmatter(f)
                if fm and "name" in fm:
                    triggers = fm.get("triggers", [])
                    if isinstance(triggers, str):
                        triggers = [triggers]
                    self.agents.append(AgentInfo(
                        name=fm["name"],
                        description=fm.get("description", ""),
                        triggers=triggers,
                        tier=fm.get("tier", "write"),
                        color=fm.get("color", ""),
                        filepath=str(f),
                    ))
            except Exception:
                continue

    def route(self, user_input: str, top_n: int = 3) -> List[AgentMatch]:
        """Score user input against all agents and return top matches.

        Scoring:
        - +2.0 for multi-word trigger substring match
        - +1.0 for single-word trigger match
        - +0.1 per description keyword overlap
        - Normalized by trigger count (favors specificity)
        """
        input_lower = user_input.lower()
        input_words = set(re.findall(r'[a-z]{3,}', input_lower))

        matches = []

        for agent in self.agents:
            if not agent.triggers:
                continue

            score = 0.0
            matched_triggers = []

            for trigger in agent.triggers:
                trigger_lower = trigger.lower()

                # Multi-word trigger: substring match in input
                if " " in trigger_lower:
                    if trigger_lower in input_lower:
                        score += 2.0
                        matched_triggers.append(trigger)
                else:
                    # Single-word trigger
                    if trigger_lower in input_words or trigger_lower in input_lower:
                        score += 1.0
                        matched_triggers.append(trigger)

            # Description keyword overlap bonus
            if agent.description:
                desc_words = set(re.findall(r'[a-z]{4,}', agent.description.lower()))
                overlap = input_words & desc_words
                score += len(overlap) * 0.1

            # Normalize by trigger count (reward specificity)
            if score > 0 and len(agent.triggers) > 0:
                score = score / (len(agent.triggers) ** 0.3)

            if score > 0:
                matches.append(AgentMatch(
                    name=agent.name,
                    score=round(score, 3),
                    triggers_matched=matched_triggers,
                    tier=agent.tier,
                    color=agent.color,
                ))

        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:top_n]

    def list_agents(self) -> List[AgentInfo]:
        """Return all loaded agents."""
        return self.agents


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent Auto-Router")
    parser.add_argument("query", nargs="?", help="User input to route")
    parser.add_argument("--all", action="store_true", help="List all agents")
    parser.add_argument("--top", type=int, default=3, help="Number of matches")
    parser.add_argument("--dir", default=str(AGENTS_DIR), help="Agents directory")
    args = parser.parse_args()

    router = AgentRouter(Path(args.dir))

    if args.all:
        print(f"Loaded {len(router.agents)} agents:\n")
        for a in router.agents:
            triggers = ", ".join(a.triggers[:5])
            more = f" +{len(a.triggers)-5}" if len(a.triggers) > 5 else ""
            print(f"  [{a.tier:9s}] {a.name:30s} triggers: {triggers}{more}")
        return

    if not args.query:
        parser.print_help()
        return

    matches = router.route(args.query, top_n=args.top)

    if not matches:
        print("No matching agents found.")
        return

    print(f"Top {len(matches)} matches for: \"{args.query}\"\n")
    for i, m in enumerate(matches, 1):
        print(f"  {i}. {m.name:30s} score={m.score:.3f}  tier={m.tier}")
        print(f"     matched: {', '.join(m.triggers_matched)}")


if __name__ == "__main__":
    main()

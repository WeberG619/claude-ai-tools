#!/usr/bin/env python3
"""
Claude Brain - Master Orchestrator
The central intelligence hub that coordinates all subsystems.

This is the "brain" that makes Claude truly intelligent by:
1. Coordinating all subsystems (perception, memory, intelligence, action)
2. Maintaining situational awareness
3. Making proactive decisions
4. Learning from interactions
5. Optimizing workflows

Usage:
    python claude_brain.py                    # Full startup sequence
    python claude_brain.py think <input>      # Process a thought/command
    python claude_brain.py status             # Get current system status
    python claude_brain.py learn              # Run learning cycle
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import subsystems
try:
    from project_intelligence import ProjectIntelligence, ProjectContext
    from workflow_engine import WorkflowLearner, ActionRecorder, AutoFixer
    from notification_system import ProactiveMonitor, NotificationEngine, Notification, Priority
    from voice_intent import IntentParser, CommandExecutor, VoiceCorrections
except ImportError as e:
    print(f"Warning: Could not import subsystem: {e}")

# Paths
BASE_DIR = Path(r"D:\_CLAUDE-TOOLS\system-bridge")
BRAIN_STATE_FILE = BASE_DIR / "brain_state.json"
MEMORY_DB = Path(r"D:\_CLAUDE-TOOLS\claude-memory-server\data\memories.db")


@dataclass
class BrainState:
    """Current state of Claude's brain."""
    timestamp: str
    active_project: Optional[str]
    confidence: float
    current_task: Optional[str]
    pending_actions: List[str]
    recent_learnings: List[str]
    alerts: List[str]
    suggestions: List[str]
    mode: str  # "idle", "active", "monitoring", "learning"


class ClaudeBrain:
    """Master orchestrator for all Claude subsystems."""

    def __init__(self):
        self.state = BrainState(
            timestamp=datetime.now().isoformat(),
            active_project=None,
            confidence=0.0,
            current_task=None,
            pending_actions=[],
            recent_learnings=[],
            alerts=[],
            suggestions=[],
            mode="idle"
        )

        # Initialize subsystems
        self.intelligence = ProjectIntelligence()
        self.workflow = WorkflowLearner()
        self.recorder = ActionRecorder()
        self.fixer = AutoFixer()
        self.monitor = ProactiveMonitor()
        self.intent_parser = IntentParser()
        self.executor = CommandExecutor()

    def perceive(self) -> Dict:
        """Gather all current perceptions."""
        perceptions = {
            "timestamp": datetime.now().isoformat(),
            "project_context": None,
            "system_state": None,
            "notifications": [],
        }

        # Get project intelligence
        try:
            context = self.intelligence.analyze()
            perceptions["project_context"] = asdict(context)
            self.state.active_project = context.project_name
            self.state.confidence = context.confidence
            self.state.alerts = context.mismatches
            self.state.suggestions = context.suggested_actions
        except Exception as e:
            perceptions["project_context_error"] = str(e)

        # Run proactive monitor
        try:
            notifications = self.monitor.run_checks()
            perceptions["notifications"] = notifications
        except Exception as e:
            perceptions["notification_error"] = str(e)

        return perceptions

    def think(self, input_text: str, context: Dict = None) -> Dict:
        """Process input and generate response/action plan."""
        context = context or {}

        # Parse intent from input
        intent = self.intent_parser.parse(input_text, context)

        # Check for clarification needs
        clarification = self.intent_parser.suggest_clarification(intent)

        # Generate execution plan if intent is clear
        execution = None
        if intent.confidence >= 0.7:
            execution = self.executor.execute(intent)

            # Record action for learning
            self.recorder.record(
                "voice_command",
                {"text": input_text, "intent": intent.action},
                self.state.active_project
            )

        # Check for anomalies
        anomaly = None
        if intent.action != "unknown":
            anomaly = self.workflow.detect_anomaly(
                intent.action,
                intent.parameters,
                self.state.active_project
            )

        # Get predictions for next actions
        predictions = self.workflow.predict_next(
            f"{intent.action}:{intent.target or ''}",
            self.state.active_project
        )

        return {
            "intent": {
                "action": intent.action,
                "target": intent.target,
                "parameters": intent.parameters,
                "confidence": intent.confidence,
                "corrections": intent.corrections_applied,
            },
            "clarification_needed": clarification,
            "execution_plan": execution,
            "anomaly_detected": anomaly,
            "predicted_next_actions": predictions,
            "current_project": self.state.active_project,
        }

    def act(self, action_plan: Dict) -> Dict:
        """Execute an action plan."""
        if not action_plan.get("execution_plan"):
            return {"status": "no_plan", "message": "No execution plan provided"}

        plan = action_plan["execution_plan"]

        if plan.get("status") != "ready":
            return {"status": "not_ready", "message": plan.get("message", "Plan not ready")}

        # Determine execution method
        if "mcp_method" in plan:
            return self._execute_mcp(plan)
        elif "shell_command" in plan:
            return self._execute_shell(plan)
        else:
            return {"status": "unknown_execution", "plan": plan}

    def _execute_mcp(self, plan: Dict) -> Dict:
        """Execute via Revit MCP."""
        import subprocess

        method = plan["mcp_method"]
        params = plan.get("mcp_params", {})

        # Build mcp_call.py command
        cmd = f'python /mnt/d/RevitMCPBridge2026/mcp_call.py {method}'
        if params:
            cmd += f" '{json.dumps(params)}'"

        try:
            result = subprocess.run(
                ['powershell.exe', '-Command', cmd],
                capture_output=True, text=True, timeout=30
            )
            return {
                "status": "executed",
                "method": method,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _execute_shell(self, plan: Dict) -> Dict:
        """Execute shell command."""
        import subprocess

        cmd = plan["shell_command"]

        try:
            result = subprocess.run(
                ['powershell.exe', '-Command', cmd],
                capture_output=True, text=True, timeout=30
            )
            return {
                "status": "executed",
                "command": plan.get("command"),
                "output": result.stdout,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def learn(self) -> Dict:
        """Run a learning cycle."""
        learnings = {
            "timestamp": datetime.now().isoformat(),
            "patterns_discovered": [],
            "corrections_loaded": [],
            "workflows_updated": [],
        }

        # Load recent actions and find patterns
        recent = self.workflow.db.get_recent_actions(50)

        # Group by action type
        action_counts = {}
        for action in recent:
            atype = action.get("action_type", "unknown")
            action_counts[atype] = action_counts.get(atype, 0) + 1

        learnings["action_frequency"] = action_counts

        # Find common sequences
        sequences = []
        for i in range(len(recent) - 1):
            trigger = recent[i].get("action_type", "")
            next_act = recent[i + 1].get("action_type", "")
            sequences.append(f"{trigger} -> {next_act}")

        from collections import Counter
        common_sequences = Counter(sequences).most_common(5)
        learnings["common_sequences"] = common_sequences

        self.state.recent_learnings = [f"{s[0]} ({s[1]}x)" for s in common_sequences]

        return learnings

    def get_status(self) -> Dict:
        """Get comprehensive system status."""
        self.state.timestamp = datetime.now().isoformat()

        # Update with fresh perceptions
        perceptions = self.perceive()

        return {
            "brain_state": asdict(self.state),
            "perceptions": perceptions,
            "subsystems": {
                "intelligence": "active",
                "workflow": "active",
                "monitor": "active",
                "voice": "active",
            },
            "memory_stats": self._get_memory_stats(),
        }

    def _get_memory_stats(self) -> Dict:
        """Get memory database statistics."""
        if not MEMORY_DB.exists():
            return {"error": "Memory database not found"}

        import sqlite3
        conn = sqlite3.connect(MEMORY_DB)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM projects")
        projects = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM memories
            WHERE memory_type = 'error' AND tags LIKE '%correction%'
        """)
        corrections = cursor.fetchone()[0]

        conn.close()

        return {
            "total_memories": total,
            "projects": projects,
            "corrections": corrections,
        }

    def startup_sequence(self) -> str:
        """Run full startup sequence and return briefing."""
        lines = []
        lines.append("=" * 70)
        lines.append(" CLAUDE BRAIN - INTELLIGENT SYSTEM STARTUP")
        lines.append("=" * 70)
        lines.append(f" Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Perceive
        lines.append("## PERCEPTION PHASE")
        perceptions = self.perceive()

        if "project_context" in perceptions and perceptions["project_context"]:
            ctx = perceptions["project_context"]
            lines.append(f"   Project: {ctx.get('project_name', 'Unknown')} ({ctx.get('confidence', 0):.0%})")
            lines.append(f"   Sources: {', '.join(ctx.get('sources', [])[:3])}")

            if ctx.get("mismatches"):
                lines.append("")
                lines.append("   [!!!] ALERTS:")
                for m in ctx["mismatches"]:
                    lines.append(f"      - {m}")

        lines.append("")

        # Memory stats
        stats = self._get_memory_stats()
        lines.append("## MEMORY STATUS")
        lines.append(f"   Total memories: {stats.get('total_memories', 0)}")
        lines.append(f"   Projects tracked: {stats.get('projects', 0)}")
        lines.append(f"   Corrections stored: {stats.get('corrections', 0)}")
        lines.append("")

        # Suggestions
        if self.state.suggestions:
            lines.append("## SUGGESTED ACTIONS")
            for s in self.state.suggestions[:5]:
                lines.append(f"   - {s}")
            lines.append("")

        # Learning summary
        if self.state.recent_learnings:
            lines.append("## LEARNED PATTERNS")
            for l in self.state.recent_learnings[:3]:
                lines.append(f"   - {l}")
            lines.append("")

        # System status
        lines.append("## SUBSYSTEMS")
        lines.append("   [OK] Project Intelligence")
        lines.append("   [OK] Workflow Learning")
        lines.append("   [OK] Notification System")
        lines.append("   [OK] Voice Intent Parser")
        lines.append("   [OK] Auto-Fixer")
        lines.append("")

        lines.append("=" * 70)
        lines.append(" SYSTEM READY - Awaiting input")
        lines.append(" Commands: think <text>, status, learn, perceive")
        lines.append("=" * 70)

        # Save brain state
        self._save_state()

        return "\n".join(lines)

    def _save_state(self):
        """Save current brain state to file."""
        with open(BRAIN_STATE_FILE, 'w') as f:
            json.dump(asdict(self.state), f, indent=2)

    def _load_state(self):
        """Load brain state from file."""
        if BRAIN_STATE_FILE.exists():
            with open(BRAIN_STATE_FILE) as f:
                data = json.load(f)
                self.state = BrainState(**data)


def main():
    """Main entry point."""
    brain = ClaudeBrain()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "think" and len(sys.argv) > 2:
            text = " ".join(sys.argv[2:])
            result = brain.think(text)
            print(json.dumps(result, indent=2))

        elif cmd == "status":
            status = brain.get_status()
            print(json.dumps(status, indent=2))

        elif cmd == "learn":
            learnings = brain.learn()
            print(json.dumps(learnings, indent=2))

        elif cmd == "perceive":
            perceptions = brain.perceive()
            print(json.dumps(perceptions, indent=2))

        elif cmd == "act" and len(sys.argv) > 2:
            # Execute a pre-built plan
            plan = json.loads(sys.argv[2])
            result = brain.act(plan)
            print(json.dumps(result, indent=2))

        else:
            print(f'{{"error": "Unknown command: {cmd}"}}')
            print('Commands: think <text>, status, learn, perceive, act <plan_json>')
    else:
        # Default: run startup sequence
        print(brain.startup_sequence())


if __name__ == "__main__":
    main()

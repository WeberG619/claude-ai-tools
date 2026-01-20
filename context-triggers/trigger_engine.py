#!/usr/bin/env python3
"""
Context-Aware Trigger Engine

The central intelligence that ties everything together.
Monitors context and triggers appropriate actions automatically.

Trigger Types:
1. App Open/Close → Load relevant context
2. File Change → Run validation
3. Time-based → Periodic checks
4. Pattern Match → Pre-flight warnings
5. Workflow Stage → Next step suggestions
"""

import json
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Callable
import subprocess

# Configuration
SYSTEM_STATE_FILE = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")
TRIGGER_STATE_FILE = Path("/mnt/d/_CLAUDE-TOOLS/context-triggers/trigger_state.json")
LOG_FILE = Path("/mnt/d/_CLAUDE-TOOLS/context-triggers/triggers.log")

CHECK_INTERVAL = 5  # seconds


class TriggerEngine:
    """Context-aware trigger engine."""

    def __init__(self):
        self.state = self._load_state()
        self.triggers = self._define_triggers()
        self.last_system_state = {}
        self.cooldowns = {}

    def _load_state(self) -> Dict:
        """Load engine state."""
        if TRIGGER_STATE_FILE.exists():
            try:
                with open(TRIGGER_STATE_FILE) as f:
                    return json.load(f)
            except:
                pass
        return {"fired_triggers": [], "suppressed": []}

    def _save_state(self):
        """Save engine state."""
        TRIGGER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TRIGGER_STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)

    def log(self, message: str):
        """Log trigger activity."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, 'a') as f:
                f.write(log_msg + "\n")
        except:
            pass

    def _define_triggers(self) -> List[Dict]:
        """Define all context triggers."""
        return [
            # App triggers
            {
                "id": "revit_opened",
                "name": "Revit Project Opened",
                "condition": self._check_revit_opened,
                "action": self._action_load_revit_context,
                "cooldown": 300,  # 5 minutes
            },
            {
                "id": "bluebeam_document",
                "name": "Bluebeam Document Active",
                "condition": self._check_bluebeam_active,
                "action": self._action_offer_markup_extraction,
                "cooldown": 600,
            },
            {
                "id": "revit_model_change",
                "name": "Revit Model Changed",
                "condition": self._check_revit_changed,
                "action": self._action_suggest_validation,
                "cooldown": 60,
            },
            # Time-based triggers
            {
                "id": "periodic_memory_check",
                "name": "Periodic Memory Review",
                "condition": self._check_time_elapsed,
                "action": self._action_surface_corrections,
                "cooldown": 1800,  # 30 minutes
            },
            # Context triggers
            {
                "id": "wall_operation_warning",
                "name": "Wall Operation Pre-Warning",
                "condition": self._check_wall_context,
                "action": self._action_preflight_wall,
                "cooldown": 120,
            },
        ]

    def get_system_state(self) -> Dict:
        """Get current system state."""
        try:
            if SYSTEM_STATE_FILE.exists():
                with open(SYSTEM_STATE_FILE) as f:
                    return json.load(f)
        except:
            pass
        return {}

    def _state_hash(self, state: Dict) -> str:
        """Compute hash of relevant state parts."""
        relevant = {
            "active_window": state.get("active_window", ""),
            "bluebeam": state.get("bluebeam", {}),
        }
        return hashlib.md5(json.dumps(relevant, sort_keys=True).encode()).hexdigest()

    def _is_on_cooldown(self, trigger_id: str) -> bool:
        """Check if trigger is on cooldown."""
        if trigger_id not in self.cooldowns:
            return False
        return datetime.now() < self.cooldowns[trigger_id]

    def _set_cooldown(self, trigger_id: str, seconds: int):
        """Set cooldown for a trigger."""
        self.cooldowns[trigger_id] = datetime.now() + timedelta(seconds=seconds)

    # =========================================================================
    # Condition Checkers
    # =========================================================================

    def _check_revit_opened(self, current: Dict, previous: Dict) -> bool:
        """Check if Revit was just opened or project changed."""
        current_window = current.get("active_window", "")
        previous_window = previous.get("active_window", "")

        if "Revit" in current_window and "Revit" not in previous_window:
            return True

        # Check for project change
        if "Revit" in current_window and "Revit" in previous_window:
            current_project = self._extract_revit_project(current_window)
            previous_project = self._extract_revit_project(previous_window)
            if current_project != previous_project:
                return True

        return False

    def _extract_revit_project(self, window_title: str) -> str:
        """Extract project name from Revit window title."""
        import re
        match = re.search(r'\[([^\]]+)', window_title)
        if match:
            return match.group(1).split(" - ")[0]
        return ""

    def _check_bluebeam_active(self, current: Dict, previous: Dict) -> bool:
        """Check if Bluebeam became active with a document."""
        current_bb = current.get("bluebeam", {})
        previous_bb = previous.get("bluebeam", {})

        if current_bb.get("running") and current_bb.get("document"):
            if not previous_bb.get("document") or current_bb.get("document") != previous_bb.get("document"):
                return True
        return False

    def _check_revit_changed(self, current: Dict, previous: Dict) -> bool:
        """Check if Revit model might have changed (simplified)."""
        # In a real implementation, this would check element counts
        return False

    def _check_time_elapsed(self, current: Dict, previous: Dict) -> bool:
        """Time-based trigger (always true if not on cooldown)."""
        return True

    def _check_wall_context(self, current: Dict, previous: Dict) -> bool:
        """Check if current context involves wall operations."""
        # This would be triggered by task context
        return False

    # =========================================================================
    # Actions
    # =========================================================================

    def _action_load_revit_context(self, state: Dict):
        """Load context when Revit opens."""
        project = self._extract_revit_project(state.get("active_window", ""))
        self.log(f"ACTION: Loading context for Revit project: {project}")

        # Run proactive memory surfacer
        try:
            subprocess.run([
                "python3",
                "/mnt/d/_CLAUDE-TOOLS/proactive-memory/memory_surfacer.py"
            ], capture_output=True, timeout=10)
        except:
            pass

    def _action_offer_markup_extraction(self, state: Dict):
        """Offer to extract markups from Bluebeam."""
        document = state.get("bluebeam", {}).get("document", "")
        self.log(f"ACTION: Bluebeam document detected: {document}")
        self.log("TIP: Export markups via Document > Markups > Export > XML for Revit integration")

    def _action_suggest_validation(self, state: Dict):
        """Suggest running BIM validation."""
        self.log("ACTION: Model changes detected - consider running /verify-bim")

    def _action_surface_corrections(self, state: Dict):
        """Periodically surface relevant corrections."""
        self.log("ACTION: Periodic correction review")
        try:
            result = subprocess.run([
                "python3",
                "/mnt/d/_CLAUDE-TOOLS/pre-flight-check/pre_flight_check.py",
                "general"
            ], capture_output=True, text=True, timeout=10)
            if "KNOWN ISSUES" in result.stdout:
                self.log("ALERT: There are known issues to review")
        except:
            pass

    def _action_preflight_wall(self, state: Dict):
        """Run pre-flight check for wall operations."""
        self.log("ACTION: Pre-flight check for wall operations")
        try:
            subprocess.run([
                "python3",
                "/mnt/d/_CLAUDE-TOOLS/pre-flight-check/pre_flight_check.py",
                "wall placement DXF coordinates"
            ], capture_output=True, timeout=10)
        except:
            pass

    # =========================================================================
    # Main Loop
    # =========================================================================

    def evaluate_triggers(self, current_state: Dict) -> List[Dict]:
        """Evaluate all triggers against current state."""
        fired = []

        for trigger in self.triggers:
            trigger_id = trigger["id"]

            # Check cooldown
            if self._is_on_cooldown(trigger_id):
                continue

            # Check condition
            try:
                if trigger["condition"](current_state, self.last_system_state):
                    self.log(f"TRIGGER: {trigger['name']}")

                    # Execute action
                    trigger["action"](current_state)

                    # Set cooldown
                    self._set_cooldown(trigger_id, trigger.get("cooldown", 60))

                    fired.append({
                        "id": trigger_id,
                        "name": trigger["name"],
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                self.log(f"Trigger error {trigger_id}: {e}")

        return fired

    def run_loop(self):
        """Main monitoring loop."""
        self.log("Context-Aware Trigger Engine started")

        while True:
            try:
                current_state = self.get_system_state()

                # Evaluate triggers
                fired = self.evaluate_triggers(current_state)

                # Update state
                if fired:
                    self.state["fired_triggers"].extend(fired)
                    # Keep last 100 fired triggers
                    self.state["fired_triggers"] = self.state["fired_triggers"][-100:]
                    self._save_state()

                self.last_system_state = current_state

            except Exception as e:
                self.log(f"Loop error: {e}")

            time.sleep(CHECK_INTERVAL)

    def trigger_now(self, trigger_id: str) -> Dict:
        """Manually fire a trigger."""
        for trigger in self.triggers:
            if trigger["id"] == trigger_id:
                self.log(f"Manual trigger: {trigger['name']}")
                current_state = self.get_system_state()
                trigger["action"](current_state)
                return {"success": True, "trigger": trigger["name"]}

        return {"success": False, "error": f"Unknown trigger: {trigger_id}"}


def main():
    """CLI entry point."""
    import sys

    engine = TriggerEngine()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            for t in engine.triggers:
                print(f"{t['id']}: {t['name']} (cooldown: {t.get('cooldown', 60)}s)")

        elif sys.argv[1] == "--trigger":
            trigger_id = sys.argv[2] if len(sys.argv) > 2 else None
            if trigger_id:
                result = engine.trigger_now(trigger_id)
                print(json.dumps(result, indent=2))
            else:
                print("Usage: --trigger <trigger_id>")

        elif sys.argv[1] == "--test":
            # Run one evaluation cycle
            state = engine.get_system_state()
            fired = engine.evaluate_triggers(state)
            print(f"Fired triggers: {len(fired)}")
            for f in fired:
                print(f"  - {f['name']}")

        elif sys.argv[1] == "--daemon":
            engine.run_loop()

    else:
        print("Usage:")
        print("  trigger_engine.py --list           # List all triggers")
        print("  trigger_engine.py --trigger <id>   # Fire trigger manually")
        print("  trigger_engine.py --test           # Run one evaluation cycle")
        print("  trigger_engine.py --daemon         # Run as background daemon")


if __name__ == "__main__":
    main()

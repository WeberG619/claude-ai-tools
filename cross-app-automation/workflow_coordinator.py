#!/usr/bin/env python3
"""
Cross-App Workflow Coordinator

Orchestrates workflows across multiple applications:
- Bluebeam ↔ Revit
- PDF → Floor Plan Vision → Revit
- Revit → Export → Bluebeam markup

Features:
1. Event detection across apps
2. Automatic data transfer
3. Status synchronization
4. Task handoff between apps
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import subprocess

SYSTEM_STATE_FILE = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json")
WORKFLOW_STATE_FILE = Path("/mnt/d/_CLAUDE-TOOLS/cross-app-automation/workflow_state.json")
LOG_FILE = Path("/mnt/d/_CLAUDE-TOOLS/cross-app-automation/coordinator.log")


class WorkflowCoordinator:
    """Coordinates workflows across applications."""

    def __init__(self):
        self.state = self._load_state()
        self.workflows = self._define_workflows()

    def _load_state(self) -> Dict:
        """Load coordinator state."""
        if WORKFLOW_STATE_FILE.exists():
            try:
                with open(WORKFLOW_STATE_FILE) as f:
                    return json.load(f)
            except:
                pass
        return {"active_workflows": [], "completed": [], "pending_handoffs": []}

    def _save_state(self):
        """Save coordinator state."""
        WORKFLOW_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(WORKFLOW_STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)

    def log(self, message: str):
        """Log coordinator activity."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, 'a') as f:
                f.write(log_msg + "\n")
        except:
            pass

    def _define_workflows(self) -> Dict:
        """Define available cross-app workflows."""
        return {
            "bluebeam_to_revit": {
                "name": "Bluebeam Markup to Revit Tasks",
                "steps": [
                    {"app": "bluebeam", "action": "export_markups_xml", "output": "xml_path"},
                    {"app": "coordinator", "action": "parse_markups", "input": "xml_path", "output": "tasks"},
                    {"app": "revit", "action": "create_tasks", "input": "tasks"},
                ],
                "triggers": ["new_bluebeam_markup", "user_request"]
            },
            "pdf_to_revit": {
                "name": "PDF Floor Plan to Revit Model",
                "steps": [
                    {"app": "vision", "action": "analyze_pdf", "output": "analysis"},
                    {"app": "vision", "action": "detect_walls", "input": "analysis", "output": "walls"},
                    {"app": "revit", "action": "create_walls", "input": "walls"},
                    {"app": "validator", "action": "validate_model"},
                ],
                "triggers": ["pdf_dropped", "user_request"]
            },
            "revit_to_bluebeam": {
                "name": "Revit Sheets to Bluebeam Review",
                "steps": [
                    {"app": "revit", "action": "export_pdf", "output": "pdf_path"},
                    {"app": "bluebeam", "action": "open_pdf", "input": "pdf_path"},
                    {"app": "coordinator", "action": "notify_ready"},
                ],
                "triggers": ["user_request", "sheet_completion"]
            }
        }

    def get_system_state(self) -> Dict:
        """Get current system state."""
        try:
            if SYSTEM_STATE_FILE.exists():
                with open(SYSTEM_STATE_FILE) as f:
                    return json.load(f)
        except:
            pass
        return {}

    def detect_open_apps(self) -> Dict[str, bool]:
        """Detect which relevant apps are open."""
        state = self.get_system_state()
        apps = state.get("applications", [])

        return {
            "revit": any("Revit" in a.get("MainWindowTitle", "") for a in apps),
            "bluebeam": any("Bluebeam" in a.get("MainWindowTitle", "") or "Revu" in a.get("MainWindowTitle", "") for a in apps),
            "vscode": any(a.get("ProcessName") == "Code" for a in apps),
        }

    # =========================================================================
    # Workflow Execution
    # =========================================================================

    def start_workflow(self, workflow_id: str, params: Dict = None) -> Dict:
        """Start a cross-app workflow."""
        if workflow_id not in self.workflows:
            return {"success": False, "error": f"Unknown workflow: {workflow_id}"}

        workflow = self.workflows[workflow_id]
        self.log(f"Starting workflow: {workflow['name']}")

        execution = {
            "id": f"{workflow_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "workflow_id": workflow_id,
            "started_at": datetime.now().isoformat(),
            "status": "running",
            "current_step": 0,
            "params": params or {},
            "results": {}
        }

        self.state["active_workflows"].append(execution)
        self._save_state()

        return {"success": True, "execution_id": execution["id"]}

    def execute_step(self, execution_id: str) -> Dict:
        """Execute the next step in a workflow."""
        # Find execution
        execution = None
        for e in self.state["active_workflows"]:
            if e["id"] == execution_id:
                execution = e
                break

        if not execution:
            return {"success": False, "error": "Execution not found"}

        workflow = self.workflows.get(execution["workflow_id"])
        if not workflow:
            return {"success": False, "error": "Workflow not found"}

        step_index = execution["current_step"]
        if step_index >= len(workflow["steps"]):
            execution["status"] = "completed"
            self._save_state()
            return {"success": True, "status": "completed"}

        step = workflow["steps"][step_index]
        self.log(f"Executing step {step_index + 1}: {step['app']}.{step['action']}")

        # Execute based on app
        result = self._execute_app_action(step, execution)

        if result.get("success"):
            if step.get("output"):
                execution["results"][step["output"]] = result.get("data")
            execution["current_step"] += 1
            self._save_state()
            return {"success": True, "step_completed": step_index + 1}
        else:
            execution["status"] = "failed"
            execution["error"] = result.get("error")
            self._save_state()
            return result

    def _execute_app_action(self, step: Dict, execution: Dict) -> Dict:
        """Execute an action in a specific app."""
        app = step["app"]
        action = step["action"]

        # Get input data if needed
        input_data = None
        if step.get("input"):
            input_data = execution["results"].get(step["input"])

        # Route to appropriate handler
        if app == "bluebeam":
            return self._bluebeam_action(action, input_data, execution["params"])
        elif app == "revit":
            return self._revit_action(action, input_data, execution["params"])
        elif app == "vision":
            return self._vision_action(action, input_data, execution["params"])
        elif app == "validator":
            return self._validator_action(action, input_data, execution["params"])
        elif app == "coordinator":
            return self._coordinator_action(action, input_data, execution["params"])

        return {"success": False, "error": f"Unknown app: {app}"}

    def _bluebeam_action(self, action: str, input_data, params: Dict) -> Dict:
        """Execute Bluebeam action."""
        # This would call the bluebeam-mcp
        self.log(f"Bluebeam action: {action}")
        return {"success": True, "data": None}

    def _revit_action(self, action: str, input_data, params: Dict) -> Dict:
        """Execute Revit action."""
        # This would call RevitMCPBridge
        self.log(f"Revit action: {action}")
        return {"success": True, "data": None}

    def _vision_action(self, action: str, input_data, params: Dict) -> Dict:
        """Execute floor plan vision action."""
        self.log(f"Vision action: {action}")
        return {"success": True, "data": None}

    def _validator_action(self, action: str, input_data, params: Dict) -> Dict:
        """Execute BIM validation action."""
        self.log(f"Validator action: {action}")
        return {"success": True, "data": None}

    def _coordinator_action(self, action: str, input_data, params: Dict) -> Dict:
        """Execute coordinator internal action."""
        if action == "notify_ready":
            self.log("Workflow ready for next phase")
            return {"success": True}
        elif action == "parse_markups":
            self.log("Parsing Bluebeam markups")
            return {"success": True, "data": []}
        return {"success": True}

    # =========================================================================
    # Status & Queries
    # =========================================================================

    def get_active_workflows(self) -> List[Dict]:
        """Get list of active workflows."""
        return self.state.get("active_workflows", [])

    def get_available_workflows(self) -> List[Dict]:
        """Get list of available workflow definitions."""
        return [
            {"id": k, "name": v["name"], "triggers": v["triggers"]}
            for k, v in self.workflows.items()
        ]

    def suggest_workflow(self) -> Optional[Dict]:
        """Suggest a workflow based on current state."""
        open_apps = self.detect_open_apps()

        if open_apps["bluebeam"] and open_apps["revit"]:
            return {
                "workflow": "bluebeam_to_revit",
                "reason": "Both Bluebeam and Revit are open"
            }
        elif open_apps["revit"]:
            return {
                "workflow": "pdf_to_revit",
                "reason": "Revit is open, ready for floor plan import"
            }

        return None


def main():
    """CLI entry point."""
    import sys

    coordinator = WorkflowCoordinator()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            workflows = coordinator.get_available_workflows()
            for w in workflows:
                print(f"{w['id']}: {w['name']}")

        elif sys.argv[1] == "--status":
            active = coordinator.get_active_workflows()
            if active:
                for w in active:
                    print(f"{w['id']}: {w['status']} (step {w['current_step']})")
            else:
                print("No active workflows")

        elif sys.argv[1] == "--suggest":
            suggestion = coordinator.suggest_workflow()
            if suggestion:
                print(f"Suggested: {suggestion['workflow']}")
                print(f"Reason: {suggestion['reason']}")
            else:
                print("No workflow suggestion based on current state")

        elif sys.argv[1] == "--start":
            workflow_id = sys.argv[2] if len(sys.argv) > 2 else None
            if workflow_id:
                result = coordinator.start_workflow(workflow_id)
                print(json.dumps(result, indent=2))
            else:
                print("Usage: --start <workflow_id>")

    else:
        print("Usage:")
        print("  workflow_coordinator.py --list           # List workflows")
        print("  workflow_coordinator.py --status         # Active workflow status")
        print("  workflow_coordinator.py --suggest        # Suggest workflow")
        print("  workflow_coordinator.py --start <id>     # Start workflow")


if __name__ == "__main__":
    main()

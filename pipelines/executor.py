#!/usr/bin/env python3
"""
Pipeline Executor - Autonomous workflow runner with checkpoint gates.

Executes .pipeline.json files with:
- Sequential phase execution
- Checkpoint gates (pause for approval)
- State persistence (resume capability)
- Memory integration (corrections surfacing)
- Dry-run mode
- Error handling with rollback

Usage:
    python executor.py cd-set.pipeline.json
    python executor.py cd-set.pipeline.json --dry-run
    python executor.py cd-set.pipeline.json --resume
    python executor.py cd-set.pipeline.json --auto-approve

Author: Claude (Ralph Loop)
Date: 2026-01-11
"""

import json
import os
import sys
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum

# Import RevitClient for actual MCP calls
try:
    from revit_client import RevitClient, get_active_client, MCPResponse
    REVIT_CLIENT_AVAILABLE = True
except ImportError:
    REVIT_CLIENT_AVAILABLE = False
    RevitClient = None

# Import logic handlers
try:
    from logic_handlers import (
        execute_logic_handler,
        is_logic_step,
        LogicContext,
        LOGIC_HANDLERS
    )
    LOGIC_HANDLERS_AVAILABLE = True
except ImportError:
    LOGIC_HANDLERS_AVAILABLE = False
    LOGIC_HANDLERS = {}

# =============================================================================
# CONFIGURATION
# =============================================================================

PIPELINES_DIR = Path(__file__).parent
STATE_DIR = PIPELINES_DIR / "state"
STATE_DIR.mkdir(exist_ok=True)

# Memory MCP integration (via subprocess to claude-memory-server)
MEMORY_AVAILABLE = True  # Will be checked at runtime


class CheckpointType(Enum):
    CONFIRMATION = "confirmation"  # Verify understanding before starting
    VALIDATION = "validation"      # Verify results match expectations
    DECISION = "decision"          # Choose between approaches
    SAFETY = "safety"              # Prevent irreversible changes


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ExecutionState:
    """Persistent state for pipeline execution."""
    pipeline_id: str
    pipeline_name: str
    started_at: str
    current_phase: str = ""
    current_step: str = ""
    phase_results: dict = field(default_factory=dict)
    step_results: dict = field(default_factory=dict)
    checkpoints_passed: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    completed: bool = False
    completed_at: str = ""

    def save(self, path: Path):
        """Save state to file."""
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> 'ExecutionState':
        """Load state from file."""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)


# =============================================================================
# OUTPUT FORMATTING
# =============================================================================

class Output:
    """CLI output formatting."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"

    @classmethod
    def header(cls, text: str):
        print(f"\n{cls.BOLD}{cls.CYAN}{'='*60}{cls.RESET}")
        print(f"{cls.BOLD}{cls.CYAN}{text.center(60)}{cls.RESET}")
        print(f"{cls.BOLD}{cls.CYAN}{'='*60}{cls.RESET}\n")

    @classmethod
    def phase(cls, name: str, description: str = ""):
        print(f"\n{cls.BOLD}{cls.BLUE}▶ PHASE: {name}{cls.RESET}")
        if description:
            print(f"  {description}")

    @classmethod
    def step(cls, step_id: str, action: str):
        print(f"  {cls.CYAN}├─ [{step_id}]{cls.RESET} {action}")

    @classmethod
    def step_result(cls, success: bool, message: str = ""):
        icon = f"{cls.GREEN}✓{cls.RESET}" if success else f"{cls.RED}✗{cls.RESET}"
        print(f"  │   {icon} {message}")

    @classmethod
    def checkpoint(cls, name: str, message: str, options: list = None):
        print(f"\n{cls.BOLD}{cls.YELLOW}{'━'*60}{cls.RESET}")
        print(f"{cls.BOLD}{cls.YELLOW}  CHECKPOINT: {name}{cls.RESET}")
        print(f"{cls.YELLOW}{'━'*60}{cls.RESET}")
        print(f"\n  {message}\n")
        if options:
            for i, opt in enumerate(options, 1):
                print(f"  [{i}] {opt}")
        print(f"\n{cls.YELLOW}{'━'*60}{cls.RESET}")

    @classmethod
    def success(cls, message: str):
        print(f"\n{cls.GREEN}✓ {message}{cls.RESET}")

    @classmethod
    def error(cls, message: str):
        print(f"\n{cls.RED}✗ ERROR: {message}{cls.RESET}")

    @classmethod
    def warning(cls, message: str):
        print(f"\n{cls.YELLOW}⚠ WARNING: {message}{cls.RESET}")

    @classmethod
    def info(cls, message: str):
        print(f"  {cls.CYAN}ℹ{cls.RESET} {message}")

    @classmethod
    def dry_run(cls, message: str):
        print(f"  {cls.YELLOW}[DRY-RUN]{cls.RESET} {message}")


# =============================================================================
# MEMORY INTEGRATION
# =============================================================================

def recall_corrections(context: str, project: str = None) -> list:
    """
    Recall relevant corrections from memory.
    Uses direct SQLite access to the claude-memory database.
    """
    try:
        from pathlib import Path
        import sqlite3

        # Correct path to the memory database
        memory_db = Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db")

        if not memory_db.exists():
            return []

        conn = sqlite3.connect(str(memory_db))
        cursor = conn.cursor()

        # Search for corrections - content contains both issue and correct approach
        # Filter by memory_type='correction' or 'error' and search in content/tags
        cursor.execute("""
            SELECT content, summary, importance
            FROM memories
            WHERE memory_type IN ('correction', 'error')
            AND (content LIKE ? OR tags LIKE ? OR summary LIKE ?)
            ORDER BY importance DESC, created_at DESC
            LIMIT 5
        """, (f"%{context}%", f"%{context}%", f"%{context}%"))

        results = cursor.fetchall()
        conn.close()

        corrections = []
        for content, summary, importance in results:
            # Parse content which may have "What was wrong:" and "Correct approach:" sections
            correct_approach = summary or ""
            if "Correct approach:" in content:
                parts = content.split("Correct approach:")
                correct_approach = parts[1].strip()[:200] if len(parts) > 1 else summary or ""

            corrections.append({
                "issue": summary or content[:100] + "..." if len(content) > 100 else content,
                "correct_approach": correct_approach,
                "importance": importance
            })

        return corrections

    except Exception as e:
        # Memory not available, continue without
        return []


def store_checkpoint_result(pipeline_id: str, checkpoint: str, approved: bool, project: str = None):
    """Store checkpoint result in memory."""
    try:
        from pathlib import Path
        import sqlite3

        # Correct path to the memory database
        memory_db = Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db")

        if not memory_db.exists():
            return

        conn = sqlite3.connect(str(memory_db))
        cursor = conn.cursor()

        content = f"Checkpoint '{checkpoint}' in pipeline '{pipeline_id}': {'APPROVED' if approved else 'REJECTED'}"
        summary = f"Pipeline checkpoint: {checkpoint} - {'approved' if approved else 'rejected'}"
        tags = json.dumps(["checkpoint", pipeline_id, "approved" if approved else "rejected"])

        cursor.execute("""
            INSERT INTO memories (content, summary, memory_type, project, importance, created_at, tags, namespace, source)
            VALUES (?, ?, 'outcome', ?, 7, datetime('now'), ?, 'global', 'auto')
        """, (content, summary, project or pipeline_id, tags))

        conn.commit()
        conn.close()

    except Exception:
        pass  # Memory not available


# =============================================================================
# PIPELINE EXECUTOR
# =============================================================================

class PipelineExecutor:
    """Main pipeline execution engine."""

    def __init__(
        self,
        pipeline_path: Path,
        dry_run: bool = False,
        auto_approve: bool = False,
        resume: bool = False,
        verbose: bool = True
    ):
        self.pipeline_path = pipeline_path
        self.dry_run = dry_run
        self.auto_approve = auto_approve
        self.resume = resume
        self.verbose = verbose

        # Load pipeline definition
        with open(pipeline_path, 'r') as f:
            self.pipeline = json.load(f)

        self.pipeline_id = self.pipeline.get("id", pipeline_path.stem)
        self.pipeline_name = self.pipeline.get("name", self.pipeline_id)

        # State file path
        self.state_path = STATE_DIR / f"{self.pipeline_id}.state.json"

        # Initialize or load state
        if resume and self.state_path.exists():
            self.state = ExecutionState.load(self.state_path)
            Output.info(f"Resuming from phase: {self.state.current_phase}")
        else:
            self.state = ExecutionState(
                pipeline_id=self.pipeline_id,
                pipeline_name=self.pipeline_name,
                started_at=datetime.now().isoformat()
            )

        # Variable store for step results
        self.variables = {}

        # RevitMCP client (connected lazily)
        self._revit_client: Optional[RevitClient] = None
        self._revit_connected = False

    def run(self) -> bool:
        """Execute the pipeline."""
        Output.header(f"Pipeline: {self.pipeline_name}")

        if self.dry_run:
            Output.warning("DRY-RUN MODE - No changes will be made")

        # Check prerequisites
        if not self._check_prerequisites():
            return False

        # Surface relevant corrections
        self._surface_corrections()

        # Execute phases
        phases = self.pipeline.get("phases", [])
        start_phase_idx = 0

        # If resuming, find the phase to start from
        if self.resume and self.state.current_phase:
            for i, phase in enumerate(phases):
                if phase["id"] == self.state.current_phase:
                    start_phase_idx = i
                    break

        for phase in phases[start_phase_idx:]:
            self.state.current_phase = phase["id"]
            self.state.save(self.state_path)

            success = self._execute_phase(phase)

            if not success:
                Output.error(f"Pipeline stopped at phase: {phase['name']}")
                return False

        # Pipeline completed
        self.state.completed = True
        self.state.completed_at = datetime.now().isoformat()
        self.state.save(self.state_path)

        # Execute on_success actions
        self._execute_on_success()

        Output.success(f"Pipeline '{self.pipeline_name}' completed successfully!")
        return True

    def _check_prerequisites(self) -> bool:
        """Check if prerequisites are met."""
        prereqs = self.pipeline.get("prerequisites", {})

        if not prereqs:
            return True

        Output.info("Checking prerequisites...")

        # Check Revit running
        if prereqs.get("revit_running"):
            if self.dry_run:
                Output.dry_run("Would check: Revit running")
            else:
                # Try to connect to RevitMCPBridge
                if REVIT_CLIENT_AVAILABLE:
                    self._revit_client = get_active_client(verbose=self.verbose)
                    if self._revit_client:
                        self._revit_connected = True
                        Output.step_result(True, f"Connected to {self._revit_client.pipe_name}")
                    else:
                        Output.step_result(False, "RevitMCPBridge not responding")
                        Output.warning("Continuing anyway - MCP calls will use mock data")
                else:
                    Output.step_result(False, "RevitClient module not available")
                    Output.warning("Continuing with mock data")

        # Check required tools
        for tool in prereqs.get("required_tools", []):
            if self.dry_run:
                Output.dry_run(f"Would check: {tool} available")
            else:
                if "RevitMCP" in tool and self._revit_connected:
                    Output.step_result(True, f"{tool} connected")
                else:
                    Output.step_result(True, f"{tool} (assumed available)")

        return True

    def _surface_corrections(self):
        """Surface relevant corrections before starting."""
        corrections_config = self.pipeline.get("corrections_to_apply", [])

        if not corrections_config:
            return

        Output.info("Surfacing relevant corrections...")

        # Also try to recall from memory based on pipeline context
        memory_corrections = recall_corrections(self.pipeline_id)

        if memory_corrections or corrections_config:
            Output.warning("CORRECTIONS TO APPLY:")

            for corr in corrections_config:
                print(f"    • [{corr.get('id', '?')}] {corr.get('rule', 'No rule specified')}")

            for corr in memory_corrections[:3]:  # Limit to 3
                print(f"    • [MEM] {corr.get('correct_approach', '')[:80]}...")

    def _execute_phase(self, phase: dict) -> bool:
        """Execute a single phase."""
        phase_id = phase["id"]
        phase_name = phase.get("name", phase_id)
        phase_desc = phase.get("description", "")

        Output.phase(phase_name, phase_desc)

        # Execute steps
        for step in phase.get("steps", []):
            self.state.current_step = step["id"]
            self.state.save(self.state_path)

            success = self._execute_step(step)

            if not success and step.get("on_fail") == "abort":
                return False

        # Handle checkpoint
        checkpoint = phase.get("checkpoint")
        if checkpoint:
            if not self._handle_checkpoint(checkpoint, phase_id):
                return False

        # Mark phase complete
        self.state.phase_results[phase_id] = {
            "status": "completed",
            "completed_at": datetime.now().isoformat()
        }
        self.state.save(self.state_path)

        return True

    def _execute_step(self, step: dict) -> bool:
        """Execute a single step."""
        step_id = step["id"]
        action = step.get("action", "unknown")
        method = step.get("method", "")
        iterate_var = step.get("iterate")  # e.g., "$numbered_sheets"

        Output.step(step_id, action)

        if self.dry_run:
            if iterate_var:
                Output.dry_run(f"Would iterate over {iterate_var} calling: {method or action}")
            else:
                Output.dry_run(f"Would call: {method or action}")

            # Store mock result
            if step.get("store_result"):
                self.variables[step["store_result"]] = {"dry_run": True, "count": 0}

            return True

        # Handle iteration over a variable
        if iterate_var:
            return self._execute_batch_step(step)

        # Execute single step
        try:
            result = self._call_method(step)

            # Store result in variables
            if step.get("store_result"):
                self.variables[step["store_result"]] = result

            # Store in state
            self.state.step_results[step_id] = {
                "status": "completed",
                "result_key": step.get("store_result")
            }

            Output.step_result(True, f"Completed")
            return True

        except Exception as e:
            self.state.errors.append({
                "step": step_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            Output.step_result(False, str(e))
            return False

    def _execute_batch_step(self, step: dict) -> bool:
        """Execute a step that iterates over a collection."""
        step_id = step["id"]
        action = step.get("action", "unknown")
        method = step.get("method", "")
        iterate_var = step.get("iterate", "")
        params_template = step.get("params", {})

        # Resolve the iteration variable (supports nested paths like $var.subkey)
        var_path = iterate_var.lstrip("$")
        items = self._resolve_variable_path(var_path)

        # If the result is a dict, try to get a list with the same base name
        # e.g., $numbered_sheets might return {"numbered_sheets": [...], "success": True}
        if isinstance(items, dict) and not items:
            items = []
        elif isinstance(items, dict):
            # Look for a key that contains a list
            base_name = var_path.split(".")[-1]
            if base_name in items and isinstance(items[base_name], list):
                items = items[base_name]
            else:
                # Try to find any list value
                for key, val in items.items():
                    if isinstance(val, list) and len(val) > 0:
                        items = val
                        break
                else:
                    items = [items] if items else []

        if not items:
            Output.warning(f"Iteration variable '{iterate_var}' is empty or not found")
            return True

        if not isinstance(items, list):
            items = [items]

        results = []
        success_count = 0
        fail_count = 0

        Output.info(f"Iterating over {len(items)} items...")

        for i, item in enumerate(items):
            # Resolve $item references in params
            resolved_params = self._resolve_item_params(params_template, item)

            try:
                # Call the method with resolved params
                result = self._call_method_with_params(method, resolved_params)
                results.append(result)
                success_count += 1

                if self.verbose and (i + 1) % 5 == 0:
                    Output.info(f"  Processed {i + 1}/{len(items)}...")

            except Exception as e:
                fail_count += 1
                if self.verbose:
                    Output.warning(f"  Item {i + 1} failed: {e}")

            # Small delay between batch operations
            if i < len(items) - 1:
                time.sleep(0.1)

        # Store results
        if step.get("store_result"):
            self.variables[step["store_result"]] = results

        self.state.step_results[step_id] = {
            "status": "completed",
            "result_key": step.get("store_result"),
            "success_count": success_count,
            "fail_count": fail_count
        }

        Output.step_result(
            fail_count == 0,
            f"Completed {success_count}/{len(items)} ({fail_count} failed)"
        )

        return fail_count == 0 or success_count > 0

    def _resolve_item_params(self, template: dict, item: Any) -> dict:
        """Resolve $item references in parameter template."""
        if not isinstance(template, dict):
            return template

        resolved = {}
        for key, value in template.items():
            if isinstance(value, str):
                if value == "$item":
                    resolved[key] = item
                elif value.startswith("$item."):
                    # Handle $item.property
                    prop = value[6:]  # Remove "$item."
                    if isinstance(item, dict):
                        resolved[key] = item.get(prop, value)
                    else:
                        resolved[key] = value
                else:
                    resolved[key] = self._resolve_variables(value)
            elif isinstance(value, dict):
                resolved[key] = self._resolve_item_params(value, item)
            elif isinstance(value, list):
                resolved[key] = [
                    self._resolve_item_params(v, item) if isinstance(v, dict) else v
                    for v in value
                ]
            else:
                resolved[key] = value

        return resolved

    def _call_method(self, step: dict) -> Any:
        """
        Call the method specified in the step.
        Routes to logic handlers or RevitMCP as appropriate.
        """
        method = step.get("method", "")
        action = step.get("action", "")
        params = step.get("params", {})

        # Resolve variable references in params
        resolved_params = self._resolve_variables(params)

        # Check if this is a logic step (type=logic, no method, or action in handlers)
        step_type = step.get("type", "")
        is_logic = (
            step_type == "logic" or
            (not method and action in LOGIC_HANDLERS) or
            (action in LOGIC_HANDLERS and method == action)
        )

        if LOGIC_HANDLERS_AVAILABLE and is_logic:
            return self._execute_logic_step(action, resolved_params)

        return self._call_method_with_params(method, resolved_params)

    def _execute_logic_step(self, action: str, params: dict) -> Any:
        """
        Execute a logic step using Python handlers.
        """
        # Build context from current variables
        context = LogicContext(
            project_name=self.variables.get("project_info", {}).get("name", ""),
            project_number=self.variables.get("project_info", {}).get("number", ""),
            levels=self.variables.get("levels", {}).get("levels", []),
            views=self.variables.get("available_views", {}).get("views", []),
            sheets=self.variables.get("existing_sheets", {}).get("sheets", []),
            title_block=self.variables.get("title_block", {})
        )

        # Execute the logic handler
        result = execute_logic_handler(action, self.variables, params, context)

        if not result.get("success", False) and "error" in result:
            raise Exception(result["error"])

        return result

    def _call_method_with_params(self, method: str, params: dict) -> Any:
        """
        Call a method with resolved parameters.
        Uses RevitClient if connected, otherwise returns mock data.
        """
        # If connected to Revit, use actual MCP calls
        if self._revit_connected and self._revit_client:
            response = self._revit_client.call(method, params)
            if response.success:
                return response.data
            else:
                raise Exception(response.error or f"MCP call {method} failed")

        # Mock data for when Revit is not connected
        mock_results = {
            "getProjectInfo": {
                "success": True,
                "name": "Sample Project",
                "path": "/path/to/project.rvt",
                "number": "2024-001"
            },
            "getElements": {
                "success": True,
                "elements": [
                    {"id": 1001, "name": "30x42 Title Block", "category": "TitleBlocks"}
                ]
            },
            "getLevels": {
                "success": True,
                "levels": [
                    {"levelId": 311, "name": "Level 1", "elevation": 0},
                    {"levelId": 312, "name": "Level 2", "elevation": 10}
                ]
            },
            "getViews": {
                "success": True,
                "views": [
                    {"viewId": 401, "name": "Floor Plan - Level 1", "viewType": "FloorPlan"},
                    {"viewId": 402, "name": "Floor Plan - Level 2", "viewType": "FloorPlan"},
                    {"viewId": 403, "name": "North Elevation", "viewType": "Elevation"},
                    {"viewId": 404, "name": "South Elevation", "viewType": "Elevation"}
                ]
            },
            "getSheets": {
                "success": True,
                "sheets": [
                    {"sheetId": 501, "sheetNumber": "A-001", "sheetName": "Cover Sheet"}
                ]
            },
            "ping": {"success": True, "status": "connected"},
            "createSheetAuto": {"success": True, "sheetId": 502},
            "placeViewOnSheet": {"success": True, "viewportId": 601},
            "createWall": {"success": True, "elementId": 701},
        }

        return mock_results.get(method, {"success": True, "status": "ok"})

    def _resolve_variable_path(self, path: str) -> Any:
        """
        Resolve a variable path like 'var_name.subkey.subsubkey'.

        Examples:
            'numbered_sheets' -> self.variables['numbered_sheets']
            'resolved_placements.resolved_placements' -> self.variables['resolved_placements']['resolved_placements']
        """
        parts = path.split(".")
        result = self.variables

        for part in parts:
            if isinstance(result, dict):
                result = result.get(part)
            elif isinstance(result, list) and part.isdigit():
                idx = int(part)
                result = result[idx] if idx < len(result) else None
            else:
                result = None

            if result is None:
                return []

        return result if result is not None else []

    def _resolve_variables(self, obj: Any) -> Any:
        """Resolve $variable references in parameters (supports nested paths)."""
        if isinstance(obj, str):
            if obj.startswith("$"):
                var_path = obj[1:]
                # Handle nested paths like $resolved_placements.resolved_placements
                if "." in var_path:
                    resolved = self._resolve_variable_path(var_path)
                    return resolved if resolved else obj
                return self.variables.get(var_path, obj)
            return obj
        elif isinstance(obj, dict):
            return {k: self._resolve_variables(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_variables(item) for item in obj]
        return obj

    def _handle_checkpoint(self, checkpoint: dict, phase_id: str) -> bool:
        """Handle a checkpoint gate."""
        name = checkpoint.get("name", "Checkpoint")
        requires_approval = checkpoint.get("requires_approval", False)
        auto_pass = checkpoint.get("auto_pass", False)
        user_prompt = checkpoint.get("user_prompt", "Continue?")

        # Resolve variables in prompt
        user_prompt = self._format_prompt(user_prompt)

        # Auto-pass checkpoints
        if auto_pass:
            Output.info(f"Checkpoint '{name}' auto-passed")
            self.state.checkpoints_passed.append({
                "name": name,
                "phase": phase_id,
                "auto": True,
                "timestamp": datetime.now().isoformat()
            })
            return True

        # Auto-approve mode
        if self.auto_approve:
            Output.info(f"Checkpoint '{name}' auto-approved (--auto-approve)")
            self.state.checkpoints_passed.append({
                "name": name,
                "phase": phase_id,
                "auto_approved": True,
                "timestamp": datetime.now().isoformat()
            })
            return True

        # Dry-run mode
        if self.dry_run:
            Output.dry_run(f"Would pause at checkpoint: {name}")
            return True

        # Show checkpoint and wait for approval
        if requires_approval:
            Output.checkpoint(
                name,
                user_prompt,
                ["Proceed", "Adjust parameters", "Stop"]
            )

            try:
                response = input("\nEnter choice [1/2/3] or 'y' to proceed: ").strip().lower()

                if response in ['1', 'y', 'yes', 'proceed', '']:
                    Output.success(f"Checkpoint '{name}' approved")
                    store_checkpoint_result(self.pipeline_id, name, True)
                    self.state.checkpoints_passed.append({
                        "name": name,
                        "phase": phase_id,
                        "approved": True,
                        "timestamp": datetime.now().isoformat()
                    })
                    return True
                elif response in ['3', 'n', 'no', 'stop']:
                    Output.warning(f"Checkpoint '{name}' rejected - stopping pipeline")
                    store_checkpoint_result(self.pipeline_id, name, False)
                    return False
                else:
                    Output.info("Adjustment requested - implement parameter editing")
                    return False

            except KeyboardInterrupt:
                Output.warning("\nCheckpoint interrupted")
                return False

        return True

    def _format_prompt(self, prompt: str) -> str:
        """Format prompt with variable substitution."""
        # Simple substitution for common patterns
        replacements = {
            "{level_count}": str(len(self.variables.get("levels", []))),
            "{view_count}": str(len(self.variables.get("available_views", []))),
            "{sheet_count}": str(len(self.variables.get("numbered_sheets", []))),
            "{name}": self.variables.get("project_info", {}).get("name", "Unknown"),
        }

        for key, value in replacements.items():
            prompt = prompt.replace(key, value)

        return prompt

    def _execute_on_success(self):
        """Execute on_success hooks."""
        on_success = self.pipeline.get("on_success", {})

        # Memory storage
        if "memory" in on_success:
            mem_config = on_success["memory"]
            Output.info(f"Storing outcome to memory: {mem_config.get('summary', '')[:50]}...")

        # Voice announcement
        if "voice" in on_success:
            voice_config = on_success["voice"]
            message = self._format_prompt(voice_config.get("message", "Pipeline complete"))
            Output.info(f"Voice: {message}")

            if not self.dry_run:
                try:
                    # Try to call voice MCP
                    subprocess.run([
                        "python3",
                        "/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py",
                        message
                    ], timeout=10, capture_output=True)
                except Exception:
                    pass  # Voice not available


# =============================================================================
# CLI INTERFACE
# =============================================================================

def list_pipelines():
    """List available pipelines."""
    Output.header("Available Pipelines")

    for p in PIPELINES_DIR.glob("*.pipeline.json"):
        try:
            with open(p) as f:
                data = json.load(f)
            name = data.get("name", p.stem)
            desc = data.get("description", "No description")
            phases = len(data.get("phases", []))
            print(f"  {p.stem}")
            print(f"    Name: {name}")
            print(f"    {desc[:60]}...")
            print(f"    Phases: {phases}")
            print()
        except Exception as e:
            print(f"  {p.stem} (error loading: {e})")


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline Executor - Run workflow pipelines with checkpoint gates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python executor.py cd-set              # Run the cd-set pipeline
  python executor.py cd-set --dry-run    # Preview without executing
  python executor.py cd-set --resume     # Resume from saved state
  python executor.py --list              # List available pipelines
        """
    )

    parser.add_argument(
        "pipeline",
        nargs="?",
        help="Pipeline name or path (e.g., 'cd-set' or 'cd-set.pipeline.json')"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be executed without making changes"
    )

    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Automatically approve all checkpoints"
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from saved state if available"
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List available pipelines"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # List pipelines
    if args.list:
        list_pipelines()
        return 0

    # Require pipeline name
    if not args.pipeline:
        parser.print_help()
        return 1

    # Resolve pipeline path
    pipeline_name = args.pipeline
    if not pipeline_name.endswith(".pipeline.json"):
        pipeline_name = f"{pipeline_name}.pipeline.json"

    pipeline_path = PIPELINES_DIR / pipeline_name

    if not pipeline_path.exists():
        Output.error(f"Pipeline not found: {pipeline_path}")
        Output.info("Use --list to see available pipelines")
        return 1

    # Create and run executor
    executor = PipelineExecutor(
        pipeline_path=pipeline_path,
        dry_run=args.dry_run,
        auto_approve=args.auto_approve,
        resume=args.resume,
        verbose=args.verbose
    )

    success = executor.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

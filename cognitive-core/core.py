#!/usr/bin/env python3
"""
Cognitive Core — The unified thinking layer.

This is the main orchestrator that ties together:
- Self-Evaluation (evaluator.py)
- Goal Decomposition (decomposer.py)
- Learning Compilation (compiler.py)
- Task Routing (meta_router.py)
- Session Reflection (reflector.py)

It implements the OODA loop (Observe → Orient → Decide → Act → Evaluate)
and provides a single interface for the entire cognitive system.

Usage:
    from cognitive_core import CognitiveCore
    brain = CognitiveCore(project="ResidentialA")

    # Full think cycle — from goal to task tree with routing
    plan = brain.think("Set up CD sheets for residential project")

    # Self-evaluate after action
    eval_result = brain.evaluate(
        action="Created 5 sheets",
        result="All sheets placed, 1 warning about viewport",
        goal="Set up CD sheets"
    )

    # End of session
    reflection = brain.reflect(session_data)

    # Compile all learnings
    rules = brain.compile()

    # Dashboard
    brain.status()
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from .evaluator import Evaluator, Evaluation
    from .decomposer import GoalDecomposer, TaskTree
    from .compiler import LearningCompiler, CompiledRules
    from .meta_router import MetaRouter, RoutingDecision
    from .reflector import SessionReflector, Reflection
except ImportError:
    from evaluator import Evaluator, Evaluation
    from decomposer import GoalDecomposer, TaskTree
    from compiler import LearningCompiler, CompiledRules
    from meta_router import MetaRouter, RoutingDecision
    from reflector import SessionReflector, Reflection


DB_PATH = Path(__file__).parent / "cognitive.db"


@dataclass
class ThinkResult:
    """Result of the full think cycle."""
    goal: str = ""
    domain: str = ""
    complexity: str = ""
    task_tree: TaskTree = None
    routing_decisions: list = field(default_factory=list)  # One per task
    enforced_rules: list = field(default_factory=list)     # Applicable rules
    preflight_checklist: list = field(default_factory=list)
    recommended_approach: str = ""

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "domain": self.domain,
            "complexity": self.complexity,
            "task_tree": self.task_tree.to_dict() if self.task_tree else None,
            "routing_decisions": [r.to_dict() for r in self.routing_decisions],
            "enforced_rules": self.enforced_rules,
            "preflight_checklist": self.preflight_checklist,
            "recommended_approach": self.recommended_approach,
        }

    def summary(self) -> str:
        """Human-readable summary of the think result."""
        lines = [f"## Think: {self.goal}"]
        lines.append(f"Domain: {self.domain} | Complexity: {self.complexity}")

        if self.task_tree:
            lines.append(f"\n### Task Tree ({len(self.task_tree.tasks)} tasks)")
            lines.append(self.task_tree.dag_view())

        if self.routing_decisions:
            lines.append("\n### Routing")
            for i, rd in enumerate(self.routing_decisions):
                task = self.task_tree.tasks[i] if self.task_tree and i < len(self.task_tree.tasks) else None
                title = task.title if task else f"Task {i+1}"
                lines.append(f"  {title}: {rd.framework}/{rd.model_tier} ({rd.max_turns} turns)")

        if self.enforced_rules:
            lines.append(f"\n### Enforced Rules ({len(self.enforced_rules)})")
            for r in self.enforced_rules[:5]:
                lines.append(f"  [BLOCKING] {r.get('rule', '')[:80]}")

        if self.preflight_checklist:
            lines.append(f"\n### Pre-Flight ({len(self.preflight_checklist)} items)")
            for item in self.preflight_checklist[:5]:
                lines.append(f"  {item.get('checklist_item', item.get('item', ''))[:80]}")

        lines.append(f"\n### Approach\n{self.recommended_approach}")
        return "\n".join(lines)


class CognitiveCore:
    """
    The unified cognitive layer.

    Implements OODA: Observe → Orient → Decide → Act → Evaluate → Learn
    """

    def __init__(self, project: str = "general", db_path: Path = DB_PATH):
        self.project = project
        self.evaluator = Evaluator(db_path)
        self.decomposer = GoalDecomposer(db_path)
        self.compiler = LearningCompiler(db_path)
        self.router = MetaRouter(db_path)
        self.reflector = SessionReflector(db_path)

    # ── THINK (Full OODA Cycle) ──────────────────────────

    def think(self, goal: str, context: dict = None) -> ThinkResult:
        """
        Full cognitive cycle for a high-level goal.

        1. OBSERVE: Understand the goal, classify domain + complexity
        2. ORIENT: Check enforced rules, load relevant corrections
        3. DECIDE: Decompose into tasks, route each to a framework
        4. Return the plan (ACT happens in execution, EVALUATE after)
        """
        context = context or {}

        # OBSERVE: Decompose the goal
        task_tree = self.decomposer.decompose(goal, context)
        domain = task_tree.domain
        complexity = task_tree.complexity

        # ORIENT: Check rules and corrections
        enforced_rules = self.compiler.get_enforced_rules(domain)
        preflight = self.compiler.preflight(domain)

        # DECIDE: Route each task
        routing_decisions = []
        for task in task_tree.tasks:
            task_context = {
                **context,
                "domain": domain,
                "files_affected": context.get("files_affected"),
            }
            decision = self.router.route(task.title, task_context)
            routing_decisions.append(decision)

            # Update the task node with routing info
            task.framework = decision.framework
            task.model_tier = decision.model_tier
            if decision.agent_type:
                task.agent_type = decision.agent_type

        # Generate approach summary
        approach = self._generate_approach(
            goal, task_tree, routing_decisions, enforced_rules
        )

        return ThinkResult(
            goal=goal,
            domain=domain,
            complexity=complexity,
            task_tree=task_tree,
            routing_decisions=routing_decisions,
            enforced_rules=enforced_rules,
            preflight_checklist=preflight,
            recommended_approach=approach,
        )

    def _generate_approach(self, goal: str, tree: TaskTree,
                            routes: list, rules: list) -> str:
        """Generate a human-readable approach description."""
        parts = [f"Goal: {goal}"]
        parts.append(f"Decomposed into {len(tree.tasks)} tasks ({tree.complexity} complexity).")

        # Framework distribution
        fw_counts = {}
        model_counts = {}
        for r in routes:
            fw_counts[r.framework] = fw_counts.get(r.framework, 0) + 1
            model_counts[r.model_tier] = model_counts.get(r.model_tier, 0) + 1

        fw_desc = ", ".join(f"{k}: {v}" for k, v in fw_counts.items())
        parts.append(f"Frameworks: {fw_desc}.")

        model_desc = ", ".join(f"{k}: {v}" for k, v in model_counts.items())
        parts.append(f"Models: {model_desc}.")

        if rules:
            parts.append(f"{len(rules)} enforced rule(s) apply — check preflight.")

        total_turns = sum(r.max_turns for r in routes)
        parts.append(f"Estimated total turns: ~{total_turns}.")

        return " ".join(parts)

    # ── EVALUATE ─────────────────────────────────────────

    def evaluate(self, action: str, result: str, goal: str,
                 domain: str = None) -> Evaluation:
        """
        Self-evaluate after an action.

        If domain is not provided, auto-detects from the action text.
        """
        if not domain:
            # Quick domain detection
            action_lower = action.lower()
            if any(w in action_lower for w in ["revit", "wall", "sheet", "view"]):
                domain = "revit"
            elif any(w in action_lower for w in ["code", "function", "build", "test"]):
                domain = "code"
            elif any(w in action_lower for w in ["excel", "browser", "window"]):
                domain = "desktop"
            else:
                domain = "general"

        return self.evaluator.evaluate(action, result, goal, domain)

    # ── REFLECT ──────────────────────────────────────────

    def reflect(self, session_data: dict) -> Reflection:
        """End-of-session reflection."""
        return self.reflector.reflect(session_data)

    # ── COMPILE ──────────────────────────────────────────

    def compile(self) -> CompiledRules:
        """Compile corrections into enforced rules."""
        return self.compiler.compile()

    # ── ROUTE ────────────────────────────────────────────

    def route(self, task_description: str, context: dict = None) -> RoutingDecision:
        """Route a single task to the best framework."""
        return self.router.route(task_description, context or {})

    # ── EXECUTE ──────────────────────────────────────────

    def execute(self, task_description: str, routing: RoutingDecision = None,
                context: dict = None) -> dict:
        """
        Execute a task using the routed framework.

        If no routing is provided, routes first then executes.
        Returns execution result dict with status, output, and eval.

        Frameworks:
        - direct: Queue in autonomous-agent for claude -p execution
        - strong_agent: Queue with strong_agent.md protocol injected
        - pipeline: Invoke pipelines/executor.py
        - swarm: Invoke swarm/swarm_engine.py for parallel decomposition
        """
        context = context or {}
        if not routing:
            routing = self.route(task_description, context)

        result = {"framework": routing.framework, "model_tier": routing.model_tier,
                  "agent_type": routing.agent_type, "status": "pending"}

        if routing.framework == "direct":
            result.update(self._execute_direct(task_description, routing))
        elif routing.framework == "strong_agent":
            result.update(self._execute_strong_agent(task_description, routing))
        elif routing.framework == "pipeline":
            result.update(self._execute_pipeline(task_description, routing, context))
        elif routing.framework == "swarm":
            result.update(self._execute_swarm(task_description, routing, context))
        else:
            result.update(self._execute_direct(task_description, routing))

        return result

    def _execute_direct(self, task: str, routing: RoutingDecision) -> dict:
        """Queue task for direct execution via autonomous-agent."""
        try:
            from .dispatcher import CognitiveDispatcher
        except ImportError:
            from dispatcher import CognitiveDispatcher

        cd = CognitiveDispatcher(project=self.project)
        task_id = cd._queue_in_agent_db(
            title=f"[{routing.model_tier}] {task[:80]}",
            prompt=self._build_execution_prompt(task, routing),
            priority=8 if routing.model_tier == "opus" else 5,
        )
        return {"status": "queued", "task_id": task_id,
                "message": f"Queued as direct/{routing.model_tier}"}

    def _execute_strong_agent(self, task: str, routing: RoutingDecision) -> dict:
        """Queue task with strong_agent protocol."""
        try:
            from .dispatcher import CognitiveDispatcher
        except ImportError:
            from dispatcher import CognitiveDispatcher

        # Load strong_agent.md and inject
        strong_agent_path = Path("/mnt/d/_CLAUDE-TOOLS/agent-boost/strong_agent.md")
        protocol = ""
        try:
            protocol = strong_agent_path.read_text()[:2000]
        except Exception:
            pass

        prompt = self._build_execution_prompt(task, routing, protocol)

        cd = CognitiveDispatcher(project=self.project)
        task_id = cd._queue_in_agent_db(
            title=f"[strong/{routing.model_tier}] {task[:70]}",
            prompt=prompt,
            priority=8,
        )
        return {"status": "queued", "task_id": task_id,
                "message": f"Queued as strong_agent/{routing.model_tier}"}

    def _execute_pipeline(self, task: str, routing: RoutingDecision,
                           context: dict) -> dict:
        """Invoke the pipeline executor."""
        import subprocess
        pipeline_dir = Path("/mnt/d/_CLAUDE-TOOLS/pipelines")
        executor = pipeline_dir / "executor.py"

        if not executor.exists():
            return {"status": "fallback", "message": "Pipeline executor not found, falling back to direct",
                    **self._execute_direct(task, routing)}

        # Determine pipeline name from context or task
        pipeline_name = context.get("pipeline", "general")
        try:
            result = subprocess.run(
                ["python3", str(executor), pipeline_name, "--task", task],
                capture_output=True, text=True, timeout=300,
                cwd=str(pipeline_dir),
            )
            return {"status": "completed" if result.returncode == 0 else "failed",
                    "output": result.stdout[:1000],
                    "error": result.stderr[:500] if result.returncode != 0 else ""}
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "message": "Pipeline execution timed out (5min)"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _execute_swarm(self, task: str, routing: RoutingDecision,
                        context: dict) -> dict:
        """Invoke the swarm engine for parallel execution."""
        swarm_dir = Path("/mnt/d/_CLAUDE-TOOLS/swarm")
        try:
            import sys
            sys.path.insert(0, str(swarm_dir))
            from swarm_engine import SwarmEngine
            swarm = SwarmEngine()

            # Plan: decompose into parallel subtasks
            plan = swarm.plan(task)
            if not plan or not plan.get("subtasks"):
                return {"status": "fallback",
                        "message": "Swarm couldn't decompose, falling back to direct",
                        **self._execute_direct(task, routing)}

            # Dispatch subtasks
            dispatch_result = swarm.dispatch(plan)
            return {"status": "dispatched",
                    "subtask_count": len(plan.get("subtasks", [])),
                    "dispatch_result": str(dispatch_result)[:500],
                    "message": f"Swarm dispatched {len(plan.get('subtasks', []))} subtasks"}
        except ImportError:
            return {"status": "fallback", "message": "Swarm engine not available",
                    **self._execute_direct(task, routing)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _build_execution_prompt(self, task: str, routing: RoutingDecision,
                                  protocol: str = "") -> str:
        """Build execution prompt with routing context."""
        parts = [f"# Task\n{task}"]

        if protocol:
            parts.append(f"\n# Execution Protocol\n{protocol[:1500]}")

        # Add enforced rules for the domain
        domain = routing.priority_signals.get("domain", "general") if routing.priority_signals else "general"
        rules = self.compiler.get_enforced_rules(domain)
        if rules:
            rule_text = "\n".join(f"- [BLOCKING] {r.get('rule', '')[:100]}" for r in rules[:10])
            parts.append(f"\n# Enforced Rules ({domain})\n{rule_text}")

        parts.append(f"\n# Routing\nFramework: {routing.framework} | "
                     f"Model: {routing.model_tier} | "
                     f"Max turns: {routing.max_turns}")

        return "\n".join(parts)

    # ── GOALS ────────────────────────────────────────────

    def set_goal(self, title: str, description: str = "",
                 project: str = None) -> str:
        """Create a persistent goal."""
        return self.reflector.set_goal(
            title, description, project or self.project
        )

    def get_goals(self) -> list:
        """Get active goals."""
        return self.reflector.get_active_goals(self.project)

    # ── STATUS ───────────────────────────────────────────

    def status(self) -> dict:
        """Get cognitive system status dashboard."""
        eval_rates = self.evaluator.get_retry_rate()
        calibration = self.evaluator.get_calibration_stats()
        routing_stats = self.router.get_stats()
        compiler_stats = self.compiler.get_stats()
        goals = self.reflector.get_active_goals(self.project)
        weekly = self.reflector.weekly_synthesis()

        return {
            "cognitive_core_version": "1.0.0",
            "project": self.project,
            "evaluation": {
                "total_evaluations": eval_rates.get("total", 0),
                "accept_rate": eval_rates.get("accept_rate", 0),
                "retry_rate": eval_rates.get("retry_rate", 0),
                "calibration_accuracy": calibration.get("mean_absolute_error", "N/A"),
            },
            "routing": {
                "total_decisions": routing_stats.get("total_decisions", 0),
                "by_framework": routing_stats.get("by_framework", {}),
                "success_rates": routing_stats.get("success_rates", {}),
            },
            "compiled_rules": {
                "total_active": compiler_stats.get("total_active_rules", 0),
                "by_level": compiler_stats.get("by_level", {}),
            },
            "goals": {
                "active": len(goals),
                "goals": [{"title": g["title"], "progress": g["progress"]}
                         for g in goals[:5]],
            },
            "weekly_summary": {
                "sessions": weekly.get("sessions", 0),
                "avg_quality": weekly.get("avg_quality", "N/A"),
                "trend": weekly.get("trend", "N/A"),
            },
        }

    def dashboard(self) -> str:
        """Generate a text dashboard."""
        s = self.status()
        lines = ["## Cognitive Core Dashboard", ""]

        # Evaluation
        ev = s["evaluation"]
        lines.append(f"**Evaluations:** {ev['total_evaluations']} total, "
                     f"{ev['accept_rate']:.0%} accept, {ev['retry_rate']:.0%} retry")

        # Routing
        rt = s["routing"]
        lines.append(f"**Routing:** {rt['total_decisions']} decisions")
        if rt["success_rates"]:
            rates = ", ".join(f"{k}: {v:.0%}" for k, v in rt["success_rates"].items())
            lines.append(f"  Success rates: {rates}")

        # Rules
        rl = s["compiled_rules"]
        lines.append(f"**Compiled Rules:** {rl['total_active']} active")

        # Goals
        gl = s["goals"]
        lines.append(f"**Active Goals:** {gl['active']}")
        for g in gl["goals"]:
            bar_len = 15
            filled = int(g["progress"] * bar_len)
            bar = "=" * filled + "-" * (bar_len - filled)
            lines.append(f"  [{bar}] {g['progress']:.0%} {g['title'][:50]}")

        # Weekly
        wk = s["weekly_summary"]
        lines.append(f"\n**This Week:** {wk['sessions']} sessions, "
                     f"avg quality {wk['avg_quality']}, trend: {wk['trend']}")

        return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Cognitive Core")
    parser.add_argument("--project", default="general")
    sub = parser.add_subparsers(dest="command")

    think_cmd = sub.add_parser("think", help="Think through a goal")
    think_cmd.add_argument("goal", help="The goal")
    think_cmd.add_argument("--create-tasks", action="store_true")

    eval_cmd = sub.add_parser("evaluate", help="Evaluate an action")
    eval_cmd.add_argument("--action", required=True)
    eval_cmd.add_argument("--result", required=True)
    eval_cmd.add_argument("--goal", required=True)

    sub.add_parser("compile", help="Compile learnings into rules")
    sub.add_parser("status", help="Cognitive dashboard")
    sub.add_parser("goals", help="Show active goals")
    sub.add_parser("weekly", help="Weekly synthesis")

    goal_cmd = sub.add_parser("goal", help="Set a persistent goal")
    goal_cmd.add_argument("title")

    args = parser.parse_args()
    brain = CognitiveCore(project=args.project)

    if args.command == "think":
        result = brain.think(args.goal)
        print(result.summary())
        if args.create_tasks:
            ids = brain.decomposer.create_board_tasks(
                result.task_tree, project=args.project
            )
            print(f"\nCreated {len(ids)} board tasks: {ids}")

    elif args.command == "evaluate":
        ev = brain.evaluate(args.action, args.result, args.goal)
        print(f"Score: {ev.score}/10 — {ev.decision}")
        print(f"Reasoning: {ev.reasoning}")

    elif args.command == "compile":
        rules = brain.compile()
        print(f"Compiled {rules.total_rules_generated} rules "
              f"from {rules.total_corrections_analyzed} corrections")

    elif args.command == "status":
        print(brain.dashboard())

    elif args.command == "goals":
        goals = brain.get_goals()
        for g in goals:
            print(f"  [{g['progress']:.0%}] {g['title']}")

    elif args.command == "goal":
        gid = brain.set_goal(args.title)
        print(f"Goal created: {gid}")

    elif args.command == "weekly":
        summary = brain.reflector.weekly_synthesis()
        for k, v in summary.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

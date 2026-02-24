#!/usr/bin/env python3
"""
Pipeline Dispatcher — orchestrates multi-stage agent pipeline for complex tasks.

Decides whether to use strong_agent (simple) or pipeline (complex).
For pipeline: runs SPEC → ARCHITECT → IMPLEMENT → REVIEW in sequence,
passing structured JSON handoffs between stages.

Usage:
    python3 pipeline_dispatcher.py "Add retry logic to RevitMCPBridge API calls"
    python3 pipeline_dispatcher.py "Fix typo in README.md" --force-simple
    python3 pipeline_dispatcher.py "Refactor the entire auth module" --force-pipeline

The dispatcher is also callable from Claude Code's Task tool — see pipeline.md.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Optional

TOOLS_DIR = Path("/mnt/d/_CLAUDE-TOOLS")
AGENT_BOOST = TOOLS_DIR / "agent-boost"
PREAMBLE_PATH = AGENT_BOOST / "agent_preamble.md"
PIPELINE_FRAMEWORK_PATH = AGENT_BOOST / "pipeline_agent.md"
STRONG_AGENT_PATH = AGENT_BOOST / "strong_agent.md"

sys.path.insert(0, str(AGENT_BOOST))
from handoff_schema import SpecOutput, DesignOutput, ImplementOutput, ReviewOutput


# ---------------------------------------------------------------------------
# Scope classifier — decides simple vs pipeline
# ---------------------------------------------------------------------------

PIPELINE_KEYWORDS = [
    "refactor", "redesign", "restructure", "rewrite", "migrate",
    "architecture", "integration", "add.*to.*and", "multiple files",
    "across.*module", "across.*class", "new.*system", "new.*service",
    "api.*change", "breaking change", "rename.*across",
]

SIMPLE_KEYWORDS = [
    "fix typo", "update comment", "rename variable", "fix.*import",
    "add.*line", "remove.*line", "single file", "one file",
]


def classify_task(task: str) -> str:
    """
    Return "simple" or "pipeline" based on task description.
    Heuristic only — user can override with --force-simple / --force-pipeline.
    """
    lower = task.lower()

    # Explicit simple signals
    for kw in SIMPLE_KEYWORDS:
        import re
        if re.search(kw, lower):
            return "simple"

    # Explicit complex signals
    for kw in PIPELINE_KEYWORDS:
        import re
        if re.search(kw, lower):
            return "pipeline"

    # Word count heuristic — longer tasks tend to be more complex
    word_count = len(task.split())
    if word_count > 30:
        return "pipeline"

    return "simple"


# ---------------------------------------------------------------------------
# Stage runner — calls claude -p with a clean prompt
# ---------------------------------------------------------------------------

def build_stage_prompt(
    stage: str,
    task: str,
    run_dir: Path,
    rejection_feedback: str = "",
) -> str:
    """Build the prompt for a specific pipeline stage."""
    preamble = PREAMBLE_PATH.read_text() if PREAMBLE_PATH.exists() else ""
    framework = PIPELINE_FRAMEWORK_PATH.read_text() if PIPELINE_FRAMEWORK_PATH.exists() else ""

    # Load handoffs from previous stages
    handoffs = {}
    for handoff_name in ["spec.json", "design.json", "implement.json"]:
        handoff_path = run_dir / handoff_name
        if handoff_path.exists():
            handoffs[handoff_name] = handoff_path.read_text()

    handoff_section = ""
    if handoffs:
        handoff_section = "\n\n## HANDOFFS FROM PREVIOUS STAGES\n\n"
        for name, content in handoffs.items():
            handoff_section += f"### {name}\n```json\n{content}\n```\n\n"

    rejection_section = ""
    if rejection_feedback:
        rejection_section = f"\n\n## REJECTION FEEDBACK (address this)\n\n{rejection_feedback}\n"

    stage_directive = {
        "spec": f"""You are executing STAGE 1: SPEC of the pipeline framework.

Your task: {task}

Run directory (write spec.json here): {run_dir}

Follow the STAGE 1: SPEC instructions in the framework below.
Write your output to: {run_dir}/spec.json
""",
        "architect": f"""You are executing STAGE 2: ARCHITECT of the pipeline framework.

Run directory: {run_dir}

Read {run_dir}/spec.json (already shown in HANDOFFS above).
Follow the STAGE 2: ARCHITECT instructions in the framework below.
Write your output to: {run_dir}/design.json
""",
        "implement": f"""You are executing STAGE 3: IMPLEMENT of the pipeline framework.

Run directory: {run_dir}

Read {run_dir}/spec.json and {run_dir}/design.json (shown in HANDOFFS above).
Follow the STAGE 3: IMPLEMENT instructions in the framework below.
Write your output to: {run_dir}/implement.json
""",
        "review": f"""You are executing STAGE 4: REVIEW of the pipeline framework.

Run directory: {run_dir}

Read {run_dir}/spec.json and {run_dir}/implement.json (shown in HANDOFFS above).
Follow the STAGE 4: REVIEW instructions in the framework below.
Write your output to: {run_dir}/review.json
""",
    }[stage]

    return f"""{preamble}

---

{stage_directive}
{handoff_section}
{rejection_section}

---

## PIPELINE FRAMEWORK (your operating instructions)

{framework}
"""


def run_stage(stage: str, task: str, run_dir: Path, rejection_feedback: str = "") -> dict:
    """
    Run one pipeline stage via claude -p.
    Returns {"success": bool, "output_path": Path, "error": str}.
    """
    prompt = build_stage_prompt(stage, task, run_dir, rejection_feedback)

    output_file_map = {
        "spec": run_dir / "spec.json",
        "architect": run_dir / "design.json",
        "implement": run_dir / "implement.json",
        "review": run_dir / "review.json",
    }
    expected_output = output_file_map[stage]

    print(f"\n{'='*60}")
    print(f"PIPELINE: Running stage {stage.upper()}")
    print(f"Run dir:  {run_dir}")
    print(f"Expecting output: {expected_output}")
    print(f"{'='*60}")

    # Write prompt to temp file to avoid shell escaping issues
    prompt_file = run_dir / f"_prompt_{stage}.txt"
    prompt_file.write_text(prompt)

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=300,  # 5 min per stage
        )

        if result.returncode != 0:
            return {
                "success": False,
                "output_path": None,
                "error": f"claude -p exited with code {result.returncode}: {result.stderr[:500]}",
            }

        # Check that the stage wrote its output file
        if not expected_output.exists():
            return {
                "success": False,
                "output_path": None,
                "error": (
                    f"Stage {stage} completed but did not write {expected_output.name}. "
                    f"claude stdout: {result.stdout[:300]}"
                ),
            }

        return {
            "success": True,
            "output_path": expected_output,
            "error": "",
            "stdout": result.stdout,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output_path": None,
            "error": f"Stage {stage} timed out after 300 seconds",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "output_path": None,
            "error": (
                "claude CLI not found. Install with: pip install claude-code or use claude -p directly. "
                "Alternatively, invoke pipeline stages manually using the pipeline_agent.md framework."
            ),
        }


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------

MAX_REJECTIONS = 2


def run_pipeline(task: str, run_dir: Path) -> dict:
    """
    Orchestrate the full 4-stage pipeline.
    Returns a summary dict with final status and artifact paths.
    """
    result = {
        "task": task,
        "run_dir": str(run_dir),
        "stages_completed": [],
        "final_status": "pending",
        "artifacts": {},
        "escalation_needed": False,
        "escalation_reason": "",
    }

    # --- STAGE 1: SPEC (with rejection retry from ARCHITECT) ---
    spec_rejections = 0
    spec_feedback = ""
    spec_output = None

    while spec_rejections <= MAX_REJECTIONS:
        spec_result = run_stage("spec", task, run_dir, rejection_feedback=spec_feedback)

        if not spec_result["success"]:
            result["final_status"] = "failed"
            result["escalation_needed"] = True
            result["escalation_reason"] = f"SPEC stage failed: {spec_result['error']}"
            return result

        try:
            spec_output = SpecOutput.from_file(run_dir / "spec.json")
            validation_errors = spec_output.validate()
            if validation_errors:
                raise ValueError(f"spec.json validation failed: {validation_errors}")
        except Exception as e:
            result["final_status"] = "failed"
            result["escalation_needed"] = True
            result["escalation_reason"] = f"SPEC output invalid: {e}"
            return result

        result["stages_completed"].append("spec")
        result["artifacts"]["spec"] = str(run_dir / "spec.json")

        # --- STAGE 2: ARCHITECT ---
        arch_result = run_stage("architect", task, run_dir)

        if not arch_result["success"]:
            result["final_status"] = "failed"
            result["escalation_needed"] = True
            result["escalation_reason"] = f"ARCHITECT stage failed: {arch_result['error']}"
            return result

        try:
            design_output = DesignOutput.from_file(run_dir / "design.json")
            validation_errors = design_output.validate()
            if validation_errors:
                raise ValueError(f"design.json validation failed: {validation_errors}")
        except Exception as e:
            result["final_status"] = "failed"
            result["escalation_needed"] = True
            result["escalation_reason"] = f"ARCHITECT output invalid: {e}"
            return result

        result["stages_completed"].append("architect")
        result["artifacts"]["design"] = str(run_dir / "design.json")

        if design_output.approved:
            break  # Proceed to IMPLEMENT

        # ARCHITECT rejected — back to SPEC
        spec_rejections += 1
        spec_feedback = design_output.rejection_feedback

        if spec_rejections > MAX_REJECTIONS:
            result["final_status"] = "escalated"
            result["escalation_needed"] = True
            result["escalation_reason"] = (
                f"ARCHITECT rejected SPEC {MAX_REJECTIONS} times. "
                f"Last rejection: {design_output.rejection_reason}\n"
                f"Feedback: {design_output.rejection_feedback}"
            )
            return result

        print(f"\nARCHITECT rejected SPEC (attempt {spec_rejections}/{MAX_REJECTIONS})")
        print(f"Reason: {design_output.rejection_reason}")
        print(f"Feedback: {design_output.rejection_feedback}")
        print("Retrying SPEC with feedback...\n")

        # Clear stale files before retry
        for stale in ["spec.json", "design.json"]:
            stale_path = run_dir / stale
            if stale_path.exists():
                stale_path.unlink()

    # --- STAGE 3: IMPLEMENT (with rejection retry from REVIEW) ---
    impl_rejections = 0
    impl_feedback = ""

    while impl_rejections <= MAX_REJECTIONS:
        impl_result = run_stage("implement", task, run_dir, rejection_feedback=impl_feedback)

        if not impl_result["success"]:
            result["final_status"] = "failed"
            result["escalation_needed"] = True
            result["escalation_reason"] = f"IMPLEMENT stage failed: {impl_result['error']}"
            return result

        try:
            impl_output = ImplementOutput.from_file(run_dir / "implement.json")
            validation_errors = impl_output.validate()
            if validation_errors:
                raise ValueError(f"implement.json validation failed: {validation_errors}")
        except Exception as e:
            result["final_status"] = "failed"
            result["escalation_needed"] = True
            result["escalation_reason"] = f"IMPLEMENT output invalid: {e}"
            return result

        if not impl_output.success:
            result["final_status"] = "failed"
            result["escalation_needed"] = True
            result["escalation_reason"] = f"IMPLEMENT reported failure: {impl_output.error}"
            return result

        result["stages_completed"].append("implement")
        result["artifacts"]["implement"] = str(run_dir / "implement.json")

        # --- STAGE 4: REVIEW ---
        review_result = run_stage("review", task, run_dir)

        if not review_result["success"]:
            result["final_status"] = "failed"
            result["escalation_needed"] = True
            result["escalation_reason"] = f"REVIEW stage failed: {review_result['error']}"
            return result

        try:
            review_output = ReviewOutput.from_file(run_dir / "review.json")
            validation_errors = review_output.validate()
            if validation_errors:
                raise ValueError(f"review.json validation failed: {validation_errors}")
        except Exception as e:
            result["final_status"] = "failed"
            result["escalation_needed"] = True
            result["escalation_reason"] = f"REVIEW output invalid: {e}"
            return result

        result["stages_completed"].append("review")
        result["artifacts"]["review"] = str(run_dir / "review.json")

        if review_output.passed:
            break  # Done

        # REVIEW rejected — back to IMPLEMENT
        impl_rejections += 1
        blockers = review_output.blockers()
        impl_feedback = (
            f"REJECTION: {review_output.rejection_reason}\n\n"
            f"BLOCKERS TO FIX:\n" +
            "\n".join(f"- [{i.file_path}] {i.description}" for i in blockers)
        )

        if impl_rejections > MAX_REJECTIONS:
            result["final_status"] = "escalated"
            result["escalation_needed"] = True
            result["escalation_reason"] = (
                f"REVIEW rejected IMPLEMENT {MAX_REJECTIONS} times. "
                f"Last rejection: {review_output.rejection_reason}\n"
                f"Blockers: {[i.description for i in blockers]}"
            )
            return result

        print(f"\nREVIEW rejected IMPLEMENT (attempt {impl_rejections}/{MAX_REJECTIONS})")
        print(f"Reason: {review_output.rejection_reason}")
        print(f"Blockers: {[i.description for i in blockers]}")
        print("Retrying IMPLEMENT with feedback...\n")

        # Clear stale implement/review files before retry
        for stale in ["implement.json", "review.json"]:
            stale_path = run_dir / stale
            if stale_path.exists():
                stale_path.unlink()

    # All stages passed
    result["final_status"] = "success"
    return result


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Pipeline dispatcher for Claude Code sub-agents")
    parser.add_argument("task", help="Task description")
    parser.add_argument("--force-simple", action="store_true", help="Force strong_agent (skip pipeline)")
    parser.add_argument("--force-pipeline", action="store_true", help="Force pipeline (skip classifier)")
    parser.add_argument("--run-dir", help="Directory for handoff files (default: /tmp/pipeline-<id>)")
    parser.add_argument("--keep-artifacts", action="store_true", help="Don't delete run dir on success")
    args = parser.parse_args()

    task = args.task
    print(f"\nTask: {task}\n")

    # Classify
    if args.force_simple:
        mode = "simple"
    elif args.force_pipeline:
        mode = "pipeline"
    else:
        mode = classify_task(task)

    print(f"Mode: {mode}")

    if mode == "simple":
        print("\nThis task classified as SIMPLE.")
        print(f"Use strong_agent.md framework: {STRONG_AGENT_PATH}")
        print("Or run manually: claude -p \"$(cat strong_agent.md)\" with your task injected.")
        sys.exit(0)

    # Pipeline mode
    run_id = f"{int(time.time())}-{uuid.uuid4().hex[:6]}"
    if args.run_dir:
        run_dir = Path(args.run_dir)
    else:
        run_dir = Path(f"/tmp/pipeline-{run_id}")

    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"Pipeline run ID: {run_id}")
    print(f"Run directory: {run_dir}\n")

    # Write run metadata
    meta = {
        "run_id": run_id,
        "task": task,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (run_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    # Run pipeline
    summary = run_pipeline(task, run_dir)

    # Report
    print("\n" + "="*60)
    print(f"PIPELINE COMPLETE — Status: {summary['final_status'].upper()}")
    print("="*60)
    print(f"Stages completed: {', '.join(summary['stages_completed'])}")

    if summary["escalation_needed"]:
        print(f"\nESCALATION REQUIRED:")
        print(summary["escalation_reason"])

    print("\nArtifacts:")
    for stage, path in summary["artifacts"].items():
        print(f"  {stage}: {path}")

    # Save summary
    summary_path = run_dir / "pipeline_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"\nFull summary: {summary_path}")

    # Cleanup on success unless --keep-artifacts
    if summary["final_status"] == "success" and not args.keep_artifacts:
        print(f"\nCleaning up run dir: {run_dir}")
        shutil.rmtree(run_dir, ignore_errors=True)

    exit_code = 0 if summary["final_status"] == "success" else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

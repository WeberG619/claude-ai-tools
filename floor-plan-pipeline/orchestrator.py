#!/usr/bin/env python3
"""
Floor Plan Pipeline Orchestrator

End-to-end automation for converting PDF floor plans to Revit models.

Pipeline stages:
1. PDF Import & Analysis
2. Wall Detection
3. Room Detection
4. Element Extraction (doors, windows)
5. Revit Model Generation
6. Quality Validation
"""

import json
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional
import urllib.request

# Configuration
REVIT_MCP_PORT = 9001
ML_FLOOR_PLAN_PORT = 9002  # If running as separate service
OUTPUT_DIR = Path("/mnt/d/_CLAUDE-TOOLS/floor-plan-pipeline/outputs")
LOG_FILE = OUTPUT_DIR / "pipeline.log"


class FloorPlanPipeline:
    """Orchestrates the complete PDF to Revit pipeline."""

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = OUTPUT_DIR / self.job_id
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.state = {
            "job_id": self.job_id,
            "pdf_path": str(self.pdf_path),
            "started_at": datetime.now().isoformat(),
            "stages": {},
            "status": "initializing",
            "errors": []
        }

    def log(self, message: str):
        """Log pipeline progress."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)

        with open(self.output_dir / "log.txt", 'a') as f:
            f.write(log_msg + "\n")

    def save_state(self):
        """Save current pipeline state."""
        with open(self.output_dir / "state.json", 'w') as f:
            json.dump(self.state, f, indent=2, default=str)

    def call_mcp(self, port: int, method: str, params: dict = None) -> dict:
        """Call an MCP server via HTTP."""
        try:
            url = f"http://127.0.0.1:{port}/api/{method}"
            data = json.dumps(params or {}).encode('utf-8')

            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header('Content-Type', 'application/json')

            with urllib.request.urlopen(req, timeout=60) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Pipeline Stages
    # =========================================================================

    def stage_1_analyze_pdf(self) -> bool:
        """Stage 1: Analyze PDF and extract floor plan image."""
        self.log("Stage 1: Analyzing PDF...")
        self.state["stages"]["analyze_pdf"] = {"status": "running"}
        self.save_state()

        try:
            # Check if PDF exists
            if not self.pdf_path.exists():
                raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

            # Call ml-floor-plan MCP for analysis
            result = self.call_mcp(ML_FLOOR_PLAN_PORT, "analyze_floor_plan", {
                "pdf_path": str(self.pdf_path),
                "output_dir": str(self.output_dir)
            })

            if not result.get("success"):
                # Fallback: Try using floor-plan-vision MCP
                self.log("ML analysis failed, trying vision fallback...")
                result = self._vision_analyze_fallback()

            if result.get("success"):
                self.state["stages"]["analyze_pdf"] = {
                    "status": "completed",
                    "output": result
                }
                self.save_state()
                return True
            else:
                raise Exception(result.get("error", "Analysis failed"))

        except Exception as e:
            self.log(f"Stage 1 FAILED: {e}")
            self.state["stages"]["analyze_pdf"] = {"status": "failed", "error": str(e)}
            self.state["errors"].append({"stage": 1, "error": str(e)})
            self.save_state()
            return False

    def _vision_analyze_fallback(self) -> dict:
        """Fallback using simpler vision analysis."""
        # This would use floor-plan-vision or other methods
        return {"success": False, "error": "Vision fallback not implemented"}

    def stage_2_detect_walls(self) -> bool:
        """Stage 2: Detect walls from floor plan."""
        self.log("Stage 2: Detecting walls...")
        self.state["stages"]["detect_walls"] = {"status": "running"}
        self.save_state()

        try:
            # Get analysis from stage 1
            analysis = self.state["stages"].get("analyze_pdf", {}).get("output", {})

            # Call wall detection
            result = self.call_mcp(ML_FLOOR_PLAN_PORT, "detect_walls", {
                "image_path": analysis.get("image_path"),
                "scale": analysis.get("scale", 1.0)
            })

            if result.get("success"):
                walls = result.get("walls", [])

                # Save walls to file
                walls_file = self.output_dir / "detected_walls.json"
                with open(walls_file, 'w') as f:
                    json.dump(walls, f, indent=2)

                self.state["stages"]["detect_walls"] = {
                    "status": "completed",
                    "wall_count": len(walls),
                    "walls_file": str(walls_file)
                }
                self.save_state()
                return True
            else:
                raise Exception(result.get("error", "Wall detection failed"))

        except Exception as e:
            self.log(f"Stage 2 FAILED: {e}")
            self.state["stages"]["detect_walls"] = {"status": "failed", "error": str(e)}
            self.state["errors"].append({"stage": 2, "error": str(e)})
            self.save_state()
            return False

    def stage_3_detect_rooms(self) -> bool:
        """Stage 3: Detect rooms and their labels."""
        self.log("Stage 3: Detecting rooms...")
        self.state["stages"]["detect_rooms"] = {"status": "running"}
        self.save_state()

        try:
            analysis = self.state["stages"].get("analyze_pdf", {}).get("output", {})

            result = self.call_mcp(ML_FLOOR_PLAN_PORT, "detect_rooms", {
                "image_path": analysis.get("image_path")
            })

            if result.get("success"):
                rooms = result.get("rooms", [])

                rooms_file = self.output_dir / "detected_rooms.json"
                with open(rooms_file, 'w') as f:
                    json.dump(rooms, f, indent=2)

                self.state["stages"]["detect_rooms"] = {
                    "status": "completed",
                    "room_count": len(rooms),
                    "rooms_file": str(rooms_file)
                }
                self.save_state()
                return True
            else:
                # Rooms are optional - continue without them
                self.log("Room detection failed, continuing without rooms")
                self.state["stages"]["detect_rooms"] = {"status": "skipped"}
                self.save_state()
                return True

        except Exception as e:
            self.log(f"Stage 3 WARNING: {e}")
            self.state["stages"]["detect_rooms"] = {"status": "skipped", "warning": str(e)}
            self.save_state()
            return True  # Continue anyway

    def stage_4_detect_elements(self) -> bool:
        """Stage 4: Detect doors, windows, and other elements."""
        self.log("Stage 4: Detecting doors and windows...")
        self.state["stages"]["detect_elements"] = {"status": "running"}
        self.save_state()

        try:
            analysis = self.state["stages"].get("analyze_pdf", {}).get("output", {})

            result = self.call_mcp(ML_FLOOR_PLAN_PORT, "detect_elements", {
                "image_path": analysis.get("image_path")
            })

            if result.get("success"):
                elements = result.get("elements", {})

                elements_file = self.output_dir / "detected_elements.json"
                with open(elements_file, 'w') as f:
                    json.dump(elements, f, indent=2)

                self.state["stages"]["detect_elements"] = {
                    "status": "completed",
                    "door_count": len(elements.get("doors", [])),
                    "window_count": len(elements.get("windows", [])),
                    "elements_file": str(elements_file)
                }
                self.save_state()
                return True
            else:
                self.log("Element detection failed, continuing without elements")
                self.state["stages"]["detect_elements"] = {"status": "skipped"}
                self.save_state()
                return True

        except Exception as e:
            self.log(f"Stage 4 WARNING: {e}")
            self.state["stages"]["detect_elements"] = {"status": "skipped", "warning": str(e)}
            self.save_state()
            return True

    def stage_5_create_revit_model(self) -> bool:
        """Stage 5: Create elements in Revit."""
        self.log("Stage 5: Creating Revit model...")
        self.state["stages"]["create_model"] = {"status": "running"}
        self.save_state()

        try:
            # Load detected data
            walls_file = self.state["stages"].get("detect_walls", {}).get("walls_file")
            if not walls_file or not Path(walls_file).exists():
                raise Exception("No walls data available")

            with open(walls_file) as f:
                walls = json.load(f)

            # Create walls in Revit
            created_walls = []
            failed_walls = []

            for i, wall in enumerate(walls):
                self.log(f"Creating wall {i+1}/{len(walls)}...")

                result = self.call_mcp(REVIT_MCP_PORT, "createWall", {
                    "start": wall.get("start", [0, 0, 0]),
                    "end": wall.get("end", [10, 0, 0]),
                    "levelId": wall.get("level_id"),
                    "height": wall.get("height", 10.0)
                })

                if result.get("success"):
                    created_walls.append({
                        "index": i,
                        "element_id": result.get("elementId")
                    })
                else:
                    failed_walls.append({
                        "index": i,
                        "wall": wall,
                        "error": result.get("error")
                    })

            # Save results
            results_file = self.output_dir / "creation_results.json"
            with open(results_file, 'w') as f:
                json.dump({
                    "created": created_walls,
                    "failed": failed_walls
                }, f, indent=2)

            if len(created_walls) > 0:
                self.state["stages"]["create_model"] = {
                    "status": "completed",
                    "created_count": len(created_walls),
                    "failed_count": len(failed_walls),
                    "results_file": str(results_file)
                }
                self.save_state()
                return True
            else:
                raise Exception("No walls were created successfully")

        except Exception as e:
            self.log(f"Stage 5 FAILED: {e}")
            self.state["stages"]["create_model"] = {"status": "failed", "error": str(e)}
            self.state["errors"].append({"stage": 5, "error": str(e)})
            self.save_state()
            return False

    def stage_6_validate(self) -> bool:
        """Stage 6: Validate the created model."""
        self.log("Stage 6: Validating model...")
        self.state["stages"]["validate"] = {"status": "running"}
        self.save_state()

        try:
            # Run BIM validator
            result = subprocess.run([
                "python3",
                "/mnt/d/_CLAUDE-TOOLS/bim-validator/background_monitor.py",
                "--validate"
            ], capture_output=True, text=True, timeout=30)

            validation = json.loads(result.stdout) if result.stdout else {}

            self.state["stages"]["validate"] = {
                "status": "completed",
                "validation": validation
            }
            self.save_state()
            return True

        except Exception as e:
            self.log(f"Stage 6 WARNING: {e}")
            self.state["stages"]["validate"] = {"status": "skipped", "warning": str(e)}
            self.save_state()
            return True

    # =========================================================================
    # Main Execution
    # =========================================================================

    def run(self) -> dict:
        """Run the complete pipeline."""
        self.log(f"Starting floor plan pipeline for: {self.pdf_path}")
        self.state["status"] = "running"
        self.save_state()

        stages = [
            ("analyze_pdf", self.stage_1_analyze_pdf),
            ("detect_walls", self.stage_2_detect_walls),
            ("detect_rooms", self.stage_3_detect_rooms),
            ("detect_elements", self.stage_4_detect_elements),
            ("create_model", self.stage_5_create_revit_model),
            ("validate", self.stage_6_validate),
        ]

        for stage_name, stage_func in stages:
            if not stage_func():
                self.log(f"Pipeline stopped at stage: {stage_name}")
                self.state["status"] = "failed"
                self.state["stopped_at"] = stage_name
                break
        else:
            self.state["status"] = "completed"
            self.log("Pipeline completed successfully!")

        self.state["completed_at"] = datetime.now().isoformat()
        self.save_state()

        # Generate summary
        summary = self.generate_summary()
        with open(self.output_dir / "summary.txt", 'w') as f:
            f.write(summary)

        return self.state

    def generate_summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            "=" * 60,
            "FLOOR PLAN PIPELINE SUMMARY",
            "=" * 60,
            f"Job ID: {self.job_id}",
            f"Input: {self.pdf_path}",
            f"Status: {self.state['status'].upper()}",
            "",
            "Stage Results:",
        ]

        for stage_name, stage_data in self.state["stages"].items():
            status = stage_data.get("status", "unknown")
            lines.append(f"  {stage_name}: {status}")

            if stage_data.get("wall_count"):
                lines.append(f"    - Walls detected: {stage_data['wall_count']}")
            if stage_data.get("created_count"):
                lines.append(f"    - Walls created: {stage_data['created_count']}")
            if stage_data.get("failed_count"):
                lines.append(f"    - Failed: {stage_data['failed_count']}")

        if self.state["errors"]:
            lines.extend(["", "Errors:"])
            for err in self.state["errors"]:
                lines.append(f"  Stage {err['stage']}: {err['error']}")

        lines.extend(["", f"Output directory: {self.output_dir}", "=" * 60])

        return "\n".join(lines)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: orchestrator.py <pdf_path>")
        print("       orchestrator.py --status <job_id>")
        sys.exit(1)

    if sys.argv[1] == "--status":
        job_id = sys.argv[2] if len(sys.argv) > 2 else None
        if job_id:
            state_file = OUTPUT_DIR / job_id / "state.json"
            if state_file.exists():
                with open(state_file) as f:
                    print(json.dumps(json.load(f), indent=2))
            else:
                print(f"Job not found: {job_id}")
        else:
            # List recent jobs
            jobs = sorted(OUTPUT_DIR.glob("*/state.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            for job in jobs[:10]:
                print(job.parent.name)
    else:
        pdf_path = sys.argv[1]
        pipeline = FloorPlanPipeline(pdf_path)
        result = pipeline.run()
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()

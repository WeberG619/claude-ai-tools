#!/usr/bin/env python3
"""
FFmpeg-based screen recorder for Revit sessions.
No OBS required - runs entirely in background.
"""

import subprocess
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Tuple
import threading

# FFmpeg path
FFMPEG_PATH = r"C:\Program Files\ffmpeg-2025-03-20-git-76f09ab647-full_build\bin\ffmpeg.exe"
SYSTEM_STATE_PATH = Path(r"D:\_CLAUDE-TOOLS\system-bridge\live_state.json")

class FFmpegRecorder:
    """Records screen using FFmpeg - no OBS required."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.process: Optional[subprocess.Popen] = None
        self.recording_file: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_flag = False

    def get_system_state(self) -> Optional[Dict]:
        """Read live system state from daemon."""
        try:
            if SYSTEM_STATE_PATH.exists():
                with open(SYSTEM_STATE_PATH) as f:
                    return json.load(f)
        except:
            pass
        return None

    def get_revit_monitor_info(self) -> Optional[Dict]:
        """Get the monitor where Revit is displayed."""
        state = self.get_system_state()
        if not state:
            return None

        apps = state.get("applications", [])
        monitors = state.get("monitors", {}).get("screens", [])

        for app in apps:
            if app.get("ProcessName") == "Revit":
                monitor_idx = app.get("MonitorIndex", 0)
                if 0 <= monitor_idx < len(monitors):
                    monitor = monitors[monitor_idx]
                    pos = app.get("Position", {})
                    return {
                        "monitor_index": monitor_idx,
                        "monitor_name": monitor.get("name"),
                        "x": monitor.get("x", 0),
                        "y": monitor.get("y", 0),
                        "width": monitor.get("width", 1920),
                        "height": monitor.get("height", 1080),
                        "revit_window": pos
                    }
        return None

    def is_revit_active(self) -> Tuple[bool, Optional[str]]:
        """Check if Revit is running. Returns (is_active, project_name)."""
        state = self.get_system_state()
        if not state:
            return False, None

        apps = state.get("applications", [])
        for app in apps:
            if app.get("ProcessName") == "Revit":
                title = app.get("MainWindowTitle", "")
                # Extract project name: "Autodesk Revit 2026.2 - [ProjectName - View]"
                if " - [" in title:
                    project = title.split(" - [")[1].split(" - ")[0]
                    return True, project
                return True, None
        return False, None

    def start_recording(self, project_name: str = "Unknown",
                       monitor_index: Optional[int] = None,
                       fps: int = 30,
                       quality: str = "medium") -> Dict:
        """
        Start recording the screen.

        Args:
            project_name: Name for the recording file
            monitor_index: Which monitor to record (None = auto-detect Revit monitor)
            fps: Frames per second (15, 30, 60)
            quality: "low", "medium", "high"
        """
        if self.process is not None:
            return {"success": False, "error": "Already recording"}

        # Get monitor info
        if monitor_index is None:
            revit_info = self.get_revit_monitor_info()
            if revit_info:
                monitor_index = revit_info["monitor_index"]
                monitor_x = revit_info["x"]
                monitor_y = revit_info["y"]
                width = revit_info["width"]
                height = revit_info["height"]
            else:
                # Default to primary monitor
                monitor_index = 0
                monitor_x = 0
                monitor_y = 0
                width = 2560
                height = 1440
        else:
            state = self.get_system_state()
            monitors = state.get("monitors", {}).get("screens", []) if state else []
            if monitor_index < len(monitors):
                m = monitors[monitor_index]
                monitor_x = m.get("x", 0)
                monitor_y = m.get("y", 0)
                width = m.get("width", 1920)
                height = m.get("height", 1080)
            else:
                monitor_x, monitor_y, width, height = 0, 0, 1920, 1080

        # Quality presets (CRF: lower = better quality, higher file size)
        quality_presets = {
            "low": {"crf": 28, "preset": "ultrafast"},
            "medium": {"crf": 23, "preset": "fast"},
            "high": {"crf": 18, "preset": "medium"}
        }
        q = quality_presets.get(quality, quality_presets["medium"])

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in project_name if c.isalnum() or c in " -_")[:50]
        self.recording_file = f"revit_{safe_name}_{timestamp}.mp4"
        output_path = self.output_dir / self.recording_file

        # Build FFmpeg command for Windows GDI capture
        # Note: For multi-monitor, we use offset to capture specific region
        cmd = [
            FFMPEG_PATH,
            "-f", "gdigrab",           # Windows screen capture
            "-framerate", str(fps),
            "-offset_x", str(abs(monitor_x)),  # Handle negative coords for left monitors
            "-offset_y", str(monitor_y),
            "-video_size", f"{width}x{height}",
            "-i", "desktop",           # Capture desktop
            "-c:v", "libx264",         # H.264 codec
            "-crf", str(q["crf"]),
            "-preset", q["preset"],
            "-pix_fmt", "yuv420p",     # Compatibility
            "-y",                       # Overwrite
            str(output_path)
        ]

        try:
            # Start FFmpeg process
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self.start_time = datetime.now()

            return {
                "success": True,
                "recording_file": self.recording_file,
                "output_path": str(output_path),
                "monitor": monitor_index,
                "resolution": f"{width}x{height}",
                "fps": fps,
                "quality": quality
            }

        except Exception as e:
            self.process = None
            return {"success": False, "error": str(e)}

    def stop_recording(self) -> Dict:
        """Stop the recording."""
        if self.process is None:
            return {"success": False, "error": "Not recording"}

        try:
            # Send 'q' to FFmpeg to stop gracefully
            self.process.stdin.write(b'q')
            self.process.stdin.flush()

            # Wait for process to finish (with timeout)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=5)

            duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            recording_file = self.recording_file
            output_path = str(self.output_dir / recording_file) if recording_file else None

            # Check if file exists and has content
            file_size = 0
            if output_path and Path(output_path).exists():
                file_size = Path(output_path).stat().st_size

            self.process = None
            self.recording_file = None
            self.start_time = None

            return {
                "success": True,
                "recording_file": recording_file,
                "output_path": output_path,
                "duration_seconds": round(duration, 1),
                "file_size_mb": round(file_size / (1024*1024), 2)
            }

        except Exception as e:
            self.process = None
            return {"success": False, "error": str(e)}

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self.process is not None and self.process.poll() is None

    def get_status(self) -> Dict:
        """Get current recording status."""
        is_revit, project = self.is_revit_active()
        revit_monitor = self.get_revit_monitor_info()

        status = {
            "is_recording": self.is_recording(),
            "recording_file": self.recording_file,
            "duration_seconds": None,
            "revit_running": is_revit,
            "revit_project": project,
            "revit_monitor": revit_monitor.get("monitor_index") if revit_monitor else None
        }

        if self.is_recording() and self.start_time:
            status["duration_seconds"] = round((datetime.now() - self.start_time).total_seconds(), 1)

        return status


# Test
if __name__ == "__main__":
    import sys

    recorder = FFmpegRecorder(Path("./recordings"))

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "start":
            result = recorder.start_recording(
                project_name=sys.argv[2] if len(sys.argv) > 2 else "Test",
                fps=30,
                quality="medium"
            )
            print(json.dumps(result, indent=2))

        elif cmd == "stop":
            result = recorder.stop_recording()
            print(json.dumps(result, indent=2))

        elif cmd == "status":
            result = recorder.get_status()
            print(json.dumps(result, indent=2))
    else:
        print("Usage: python recorder_ffmpeg.py [start|stop|status] [project_name]")

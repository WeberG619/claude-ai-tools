#!/usr/bin/env python3
"""
Session Recorder - Captures agent team sessions with audio and transcript.

Records:
1. All agent conversations (text log)
2. Audio output (combined MP3)
3. Timestamps for playback sync
4. Final artifacts produced

Usage:
    python record_session.py "Project description" --duration 30
"""

import json
import subprocess
import sys
import os
import time
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

SCRIPT_DIR = Path(__file__).parent.parent
VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")
RECORDINGS_DIR = SCRIPT_DIR / "recordings"


class SessionRecorder:
    """Records agent team sessions with audio and transcript."""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = RECORDINGS_DIR / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Files
        self.transcript_file = self.session_dir / "transcript.md"
        self.audio_list_file = self.session_dir / "audio_segments.txt"
        self.metadata_file = self.session_dir / "metadata.json"

        # State
        self.audio_segments: List[Dict] = []
        self.transcript_entries: List[Dict] = []
        self.start_time = None
        self.artifacts: List[str] = []

        # Initialize files
        self._init_files()

    def _init_files(self):
        """Initialize recording files."""
        # Transcript header
        with open(self.transcript_file, 'w') as f:
            f.write(f"# Agent Team Session: {self.project_name}\n\n")
            f.write(f"**Session ID:** {self.session_id}\n")
            f.write(f"**Started:** {datetime.now().isoformat()}\n\n")
            f.write("---\n\n")

        # Metadata
        metadata = {
            "session_id": self.session_id,
            "project": self.project_name,
            "started_at": datetime.now().isoformat(),
            "agents": ["planner", "researcher", "builder", "critic", "narrator"],
            "status": "recording"
        }
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

    def start(self):
        """Start the recording session."""
        self.start_time = time.time()
        print(f"\n{'='*60}")
        print(f"🎬 RECORDING SESSION: {self.session_id}")
        print(f"📁 Output: {self.session_dir}")
        print(f"{'='*60}\n")

    def log_turn(self, agent: str, content: str, voice: str):
        """Log a conversation turn."""
        elapsed = time.time() - self.start_time if self.start_time else 0

        entry = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "agent": agent,
            "voice": voice,
            "content": content
        }
        self.transcript_entries.append(entry)

        # Append to transcript file
        with open(self.transcript_file, 'a') as f:
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            f.write(f"## [{minutes:02d}:{seconds:02d}] {agent.upper()} ({voice})\n\n")
            f.write(f"{content}\n\n")
            f.write("---\n\n")

    def log_audio(self, audio_file: str, agent: str):
        """Log an audio segment."""
        elapsed = time.time() - self.start_time if self.start_time else 0

        segment = {
            "file": audio_file,
            "agent": agent,
            "elapsed_seconds": round(elapsed, 2)
        }
        self.audio_segments.append(segment)

        # Append to audio list
        with open(self.audio_list_file, 'a') as f:
            f.write(f"file '{audio_file}'\n")

    def log_artifact(self, artifact: str):
        """Log a produced artifact (file created, code written, etc.)."""
        self.artifacts.append(artifact)

        with open(self.transcript_file, 'a') as f:
            f.write(f"**📄 Artifact:** `{artifact}`\n\n")

    def log_discussion(self, topic: str, participants: List[str]):
        """Log a discussion/debate between agents."""
        with open(self.transcript_file, 'a') as f:
            f.write(f"### 💬 Discussion: {topic}\n")
            f.write(f"*Participants: {', '.join(participants)}*\n\n")

    def log_issue(self, issue: str, resolver: str):
        """Log an issue found and who's resolving it."""
        with open(self.transcript_file, 'a') as f:
            f.write(f"### ⚠️ Issue Found\n")
            f.write(f"**Problem:** {issue}\n")
            f.write(f"**Assigned to:** {resolver}\n\n")

    def finish(self, status: str = "complete"):
        """Finish the recording session."""
        end_time = time.time()
        duration = end_time - self.start_time if self.start_time else 0

        # Update metadata
        metadata = {
            "session_id": self.session_id,
            "project": self.project_name,
            "started_at": self.transcript_entries[0]["timestamp"] if self.transcript_entries else None,
            "ended_at": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "duration_minutes": round(duration / 60, 1),
            "total_turns": len(self.transcript_entries),
            "audio_segments": len(self.audio_segments),
            "artifacts": self.artifacts,
            "status": status
        }

        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        # Final summary in transcript
        with open(self.transcript_file, 'a') as f:
            f.write(f"\n## Session Complete\n\n")
            f.write(f"- **Duration:** {round(duration/60, 1)} minutes\n")
            f.write(f"- **Total turns:** {len(self.transcript_entries)}\n")
            f.write(f"- **Artifacts produced:** {len(self.artifacts)}\n")
            f.write(f"- **Status:** {status}\n")

        print(f"\n{'='*60}")
        print(f"🎬 RECORDING COMPLETE")
        print(f"📁 Files saved to: {self.session_dir}")
        print(f"⏱️  Duration: {round(duration/60, 1)} minutes")
        print(f"💬 Turns: {len(self.transcript_entries)}")
        print(f"{'='*60}\n")

        return self.session_dir

    def combine_audio(self) -> Optional[str]:
        """Combine all audio segments into one file using ffmpeg."""
        if not self.audio_segments:
            return None

        output_file = self.session_dir / "full_session.mp3"

        try:
            # Use ffmpeg to concatenate
            result = subprocess.run(
                ["ffmpeg", "-f", "concat", "-safe", "0",
                 "-i", str(self.audio_list_file),
                 "-c", "copy", str(output_file)],
                capture_output=True,
                timeout=120
            )
            if result.returncode == 0:
                print(f"✅ Combined audio: {output_file}")
                return str(output_file)
        except Exception as e:
            print(f"⚠️ Could not combine audio: {e}")

        return None


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Record Agent Team Session")
    parser.add_argument("project", help="Project name/description")
    parser.add_argument("--duration", type=int, default=30,
                        help="Target duration in minutes")

    args = parser.parse_args()

    recorder = SessionRecorder(args.project)
    recorder.start()

    # Demo: Log some test entries
    recorder.log_turn("planner", "Test planning message", "andrew")
    time.sleep(1)
    recorder.log_turn("researcher", "Test research message", "guy")

    recorder.finish("demo")


if __name__ == "__main__":
    main()

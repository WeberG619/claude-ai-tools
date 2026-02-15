#!/usr/bin/env python3
"""
Speech Coordinator - Ensures only ONE agent speaks at a time.

Uses a file-based lock to prevent overlapping speech across processes.
Visual status shows who currently holds the microphone.
"""

import subprocess
import sys
import time
import os
import fcntl
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False

# Lock file for cross-process synchronization
LOCK_FILE = Path("/tmp/agent_speech.lock")
STATUS_FILE = Path("/tmp/agent_speech_status.json")
VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")

# Voice mappings
VOICES = {
    "planner": "andrew",
    "researcher": "guy",
    "builder": "christopher",
    "critic": "eric",
    "narrator": "jenny",
    "andrew": "andrew",
    "guy": "guy",
    "christopher": "christopher",
    "eric": "eric",
    "jenny": "jenny",
}

AGENT_NAMES = {
    "andrew": "PLANNER",
    "guy": "RESEARCHER",
    "christopher": "BUILDER",
    "eric": "CRITIC",
    "jenny": "NARRATOR",
}


class SpeechCoordinator:
    """
    Coordinates agent speech to prevent overlap.

    Usage:
        coord = SpeechCoordinator()
        coord.speak("planner", "Hello team, let's get started.")
        coord.speak("researcher", "I found some interesting data.")
    """

    def __init__(self):
        self.lock_file = None
        self._ensure_lock_file()

    def _ensure_lock_file(self):
        """Create lock file if it doesn't exist."""
        LOCK_FILE.touch(exist_ok=True)

    @contextmanager
    def _acquire_mic(self, agent: str):
        """
        Context manager to acquire exclusive microphone access.
        Blocks until the mic is available.
        """
        voice = VOICES.get(agent.lower(), "andrew")
        role = AGENT_NAMES.get(voice, agent.upper())

        # Open lock file
        self.lock_file = open(LOCK_FILE, 'w')

        # Wait indicator
        waited = False
        start_wait = time.time()

        while True:
            try:
                # Try to acquire exclusive lock (non-blocking first check)
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if not waited:
                    print(f"  [{role}] Waiting for mic...")
                    waited = True
                time.sleep(0.1)

                # Timeout after 60 seconds
                if time.time() - start_wait > 60:
                    print(f"  [{role}] Timeout waiting for mic!")
                    raise TimeoutError("Could not acquire microphone")

        if waited:
            print(f"  [{role}] Mic acquired after {time.time() - start_wait:.1f}s")

        # Update status
        self._set_status(agent, "speaking")

        try:
            yield
        finally:
            # Release lock
            self._set_status(agent, "done")
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
            self.lock_file.close()
            self.lock_file = None

    def _set_status(self, agent: str, status: str):
        """Update the current speech status."""
        import json
        voice = VOICES.get(agent.lower(), "andrew")
        role = AGENT_NAMES.get(voice, agent.upper())

        data = {
            "agent": agent,
            "role": role,
            "voice": voice,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }

        try:
            with open(STATUS_FILE, 'w') as f:
                json.dump(data, f)
        except:
            pass

    def get_status(self) -> dict:
        """Get current speech status."""
        import json
        try:
            with open(STATUS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"status": "idle"}

    def speak(self, agent: str, text: str, rate: str = "+10%", activity: dict = None) -> bool:
        """
        Speak as an agent with exclusive microphone access.
        Keeps the speaking indicator ON for the entire duration.
        Preserves the activity for visual display (code/terminal/browser).

        Args:
            agent: Agent name (planner, researcher, builder, critic, narrator)
            text: Text to speak
            rate: Speech rate (default +10% faster)
            activity: Optional activity dict for visual display (code_write, terminal_run, browser_navigate)

        Returns:
            True if speech completed successfully
        """
        import threading
        import json

        voice = VOICES.get(agent.lower(), "andrew")
        role = AGENT_NAMES.get(voice, agent.upper())

        # Dashboard status file
        DASHBOARD_STATUS = Path("/mnt/d/_CLAUDE-TOOLS/agent-team/agent_status.json")

        # Read existing activity from status file if not provided
        if activity is None:
            try:
                if DASHBOARD_STATUS.exists():
                    with open(DASHBOARD_STATUS, "r") as f:
                        existing = json.load(f)
                        activity = existing.get("activity")
            except Exception:
                pass

        # Flag to control keep-alive thread
        speaking_active = True

        def keep_status_alive():
            """Keep updating status file so dashboard shows green light AND activity."""
            while speaking_active:
                try:
                    status = {
                        "agent": agent.lower(),
                        "speaking": True,
                        "text": text[:200],
                        "timestamp": time.time()
                    }
                    # IMPORTANT: Preserve activity for visual display!
                    if activity:
                        status["activity"] = activity
                    with open(DASHBOARD_STATUS, "w") as f:
                        json.dump(status, f)
                except Exception:
                    pass
                time.sleep(0.3)  # Update every 300ms

        with self._acquire_mic(agent):
            # Visual indicator
            print(f"\n{'━'*60}")
            print(f"🎤 {role} ({voice}) speaking...")
            print(f"{'━'*60}")
            print(f"  \"{text[:150]}{'...' if len(text) > 150 else ''}\"")
            print()

            # Start keep-alive thread BEFORE speaking
            keep_alive_thread = threading.Thread(target=keep_status_alive, daemon=True)
            keep_alive_thread.start()

            try:
                # Generate speech with edge-tts for rate control
                result = self._speak_with_edge(text, voice, rate)

                if result:
                    print(f"  ✓ {role} finished")
                    return True
                else:
                    # Fallback to standard speak.py
                    result = subprocess.run(
                        ["python3", str(VOICE_SCRIPT), text, voice],
                        capture_output=True,
                        timeout=120
                    )
                    print(f"  ✓ {role} finished (fallback)")
                    return result.returncode == 0

            except Exception as e:
                print(f"  ✗ {role} error: {e}")
                return False
            finally:
                # Stop keep-alive and clear speaking status
                speaking_active = False
                time.sleep(0.1)  # Let thread finish
                try:
                    status = {
                        "agent": agent.lower(),
                        "speaking": False,
                        "text": "",
                        "timestamp": time.time()
                    }
                    with open(DASHBOARD_STATUS, "w") as f:
                        json.dump(status, f)
                except Exception:
                    pass

    def _speak_with_edge(self, text: str, voice: str, rate: str) -> bool:
        """Generate and play speech with Edge TTS."""
        try:
            import asyncio
            import edge_tts

            EDGE_VOICES = {
                "andrew": "en-US-AndrewNeural",
                "guy": "en-US-GuyNeural",
                "christopher": "en-US-ChristopherNeural",
                "eric": "en-US-EricNeural",
                "jenny": "en-US-JennyNeural",
            }

            voice_id = EDGE_VOICES.get(voice, "en-US-AndrewNeural")

            async def generate_and_play():
                # Create temp file
                temp_file = f"/tmp/agent_speech_{voice}_{int(time.time())}.mp3"

                try:
                    # Generate audio
                    communicate = edge_tts.Communicate(text, voice_id, rate=rate)
                    await communicate.save(temp_file)

                    if not os.path.exists(temp_file) or os.path.getsize(temp_file) < 1000:
                        return False

                    # Save to Windows-accessible path (not /tmp which Windows can't read)
                    audio_dir = Path("/mnt/d/.playwright-mcp/audio")
                    audio_dir.mkdir(parents=True, exist_ok=True)
                    audio_file = audio_dir / f"agent_{voice}_{int(time.time())}.mp3"

                    # Move from temp to accessible location
                    import shutil
                    shutil.move(temp_file, str(audio_file))
                    temp_file = str(audio_file)

                    # Convert to Windows path
                    win_path = temp_file.replace('/mnt/d/', 'D:\\\\').replace('/', '\\\\')

                    # Play with PowerShell - BLOCKING until complete
                    play_script = f'''
                    $ErrorActionPreference = "SilentlyContinue"
                    Add-Type -AssemblyName presentationCore
                    $player = New-Object System.Windows.Media.MediaPlayer
                    $player.Open([Uri]"{win_path}")
                    Start-Sleep -Milliseconds 500
                    $player.Play()

                    # Wait for playback to complete
                    $timeout = 120
                    $elapsed = 0
                    while ($player.Position -lt $player.NaturalDuration.TimeSpan -and $elapsed -lt $timeout) {{
                        Start-Sleep -Milliseconds 200
                        $elapsed += 0.2
                    }}

                    $player.Stop()
                    $player.Close()
                    '''

                    if _HAS_BRIDGE:
                        _ps_bridge(play_script, timeout=120)
                    else:
                        subprocess.run(
                            ["powershell.exe", "-NoProfile", "-Command", play_script],
                            capture_output=True,
                            timeout=120
                        )

                    return True

                finally:
                    # Cleanup
                    if os.path.exists(temp_file):
                        try:
                            os.unlink(temp_file)
                        except:
                            pass

            return asyncio.run(generate_and_play())

        except ImportError:
            return False
        except Exception as e:
            print(f"    Edge TTS error: {e}")
            return False


# Global coordinator instance
_coordinator = None

def get_coordinator() -> SpeechCoordinator:
    """Get the global speech coordinator."""
    global _coordinator
    if _coordinator is None:
        _coordinator = SpeechCoordinator()
    return _coordinator


def speak(agent: str, text: str, rate: str = "+10%") -> bool:
    """Convenience function to speak with coordination."""
    return get_coordinator().speak(agent, text, rate)


# CLI interface
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python speech_coordinator.py <agent> <text> [rate]")
        print("Agents: planner, researcher, builder, critic, narrator")
        print("Rate: +0%, +10%, +20% (default: +10%)")
        print("\nThis ensures only one agent speaks at a time.")
        sys.exit(1)

    agent = sys.argv[1]
    text = sys.argv[2]
    rate = sys.argv[3] if len(sys.argv) > 3 else "+10%"

    success = speak(agent, text, rate)
    sys.exit(0 if success else 1)

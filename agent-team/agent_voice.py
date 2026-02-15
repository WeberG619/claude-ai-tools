#!/usr/bin/env python3
"""
Agent Voice Controller - Faster speech with interrupt capability.

Features:
- Adjustable speech rate (+10% to +30% faster)
- Interruptible playback (Ctrl+C stops current speech)
- No overlap protection (waits for previous speech to finish)
- Visual indicator of who's speaking
"""

import subprocess
import sys
import time
import signal
from pathlib import Path

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False

VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")

# Voice assignments
AGENT_VOICES = {
    "planner": ("andrew", "PLANNER"),
    "researcher": ("guy", "RESEARCHER"),
    "builder": ("christopher", "BUILDER"),
    "critic": ("eric", "CRITIC"),
    "narrator": ("jenny", "NARRATOR"),
    # Aliases
    "andrew": ("andrew", "PLANNER"),
    "guy": ("guy", "RESEARCHER"),
    "christopher": ("christopher", "BUILDER"),
    "eric": ("eric", "CRITIC"),
    "jenny": ("jenny", "NARRATOR"),
}

# Global for interrupt handling
current_process = None

def signal_handler(sig, frame):
    """Handle Ctrl+C to interrupt speech."""
    global current_process
    if current_process:
        current_process.terminate()
        print("\n[INTERRUPTED]")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


def speak(agent: str, text: str, rate: str = "+15%") -> bool:
    """
    Speak text as an agent with visual indicator.

    Args:
        agent: Agent name (planner, researcher, builder, critic, narrator)
        text: Text to speak
        rate: Speech rate adjustment (e.g., "+15%" for faster)

    Returns:
        True if speech completed, False if interrupted
    """
    global current_process

    voice, role = AGENT_VOICES.get(agent.lower(), ("andrew", agent.upper()))

    # Visual indicator
    print(f"\n{'─'*50}")
    print(f"🎤 {role} ({voice}) [rate: {rate}]")
    print(f"{'─'*50}")
    print(f"  \"{text[:100]}{'...' if len(text) > 100 else ''}\"")

    try:
        # Use edge-tts directly for rate control
        import asyncio
        import edge_tts
        import tempfile
        import os

        EDGE_VOICES = {
            "andrew": "en-US-AndrewNeural",
            "guy": "en-US-GuyNeural",
            "christopher": "en-US-ChristopherNeural",
            "eric": "en-US-EricNeural",
            "jenny": "en-US-JennyNeural",
        }

        voice_id = EDGE_VOICES.get(voice, "en-US-AndrewNeural")

        async def generate_and_play():
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                temp_file = f.name

            try:
                communicate = edge_tts.Communicate(text, voice_id, rate=rate)
                await communicate.save(temp_file)

                # Play with PowerShell MediaPlayer
                play_script = f'''
                Add-Type -AssemblyName presentationCore
                $player = New-Object System.Windows.Media.MediaPlayer
                $player.Open([Uri]"{temp_file.replace('/', '\\')}")
                Start-Sleep -Milliseconds 300
                $player.Play()
                while ($player.Position -lt $player.NaturalDuration.TimeSpan) {{
                    Start-Sleep -Milliseconds 100
                }}
                $player.Stop()
                $player.Close()
                '''

                global current_process
                if _HAS_BRIDGE:
                    _ps_bridge(play_script, timeout=120)
                    current_process = None
                else:
                    current_process = subprocess.Popen(
                        ["powershell.exe", "-NoProfile", "-Command", play_script],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    current_process.wait()
                    current_process = None

            finally:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

        asyncio.run(generate_and_play())
        print("  ✓ Complete")
        return True

    except KeyboardInterrupt:
        print("\n  [INTERRUPTED by user]")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        # Fallback to standard speak.py
        try:
            result = subprocess.run(
                ["python3", str(VOICE_SCRIPT), text, voice],
                timeout=120
            )
            return result.returncode == 0
        except:
            return False


def speak_fast(agent: str, text: str) -> bool:
    """Speak at +20% speed."""
    return speak(agent, text, rate="+20%")


def speak_faster(agent: str, text: str) -> bool:
    """Speak at +30% speed."""
    return speak(agent, text, rate="+30%")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python agent_voice.py <agent> <text> [rate]")
        print("Agents: planner, researcher, builder, critic, narrator")
        print("Rate: +10%, +20%, +30% (default: +15%)")
        sys.exit(1)

    agent = sys.argv[1]
    text = sys.argv[2]
    rate = sys.argv[3] if len(sys.argv) > 3 else "+15%"

    speak(agent, text, rate)

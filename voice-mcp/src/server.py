#!/usr/bin/env python3
"""
BULLETPROOF Voice MCP Server - Natural Text-to-Speech for Claude Code
Uses Microsoft Edge TTS (FREE, unlimited) with aggressive retry logic.

Features:
- IPv4 forced (fixes WSL/network issues)
- 5 retries with exponential backoff
- Audio caching for repeated phrases
- 60-second timeout per attempt
"""

import asyncio
import subprocess
import sys
import os
import socket
import hashlib
import shutil
from typing import List
from datetime import datetime
from pathlib import Path

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False

# =============================================================================
# FORCE IPv4 - Critical fix for Edge TTS connectivity
# =============================================================================
original_getaddrinfo = socket.getaddrinfo
def ipv4_only_getaddrinfo(*args, **kwargs):
    responses = original_getaddrinfo(*args, **kwargs)
    ipv4_responses = [r for r in responses if r[0] == socket.AF_INET]
    return ipv4_responses if ipv4_responses else responses
socket.getaddrinfo = ipv4_only_getaddrinfo
socket.setdefaulttimeout(30)

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    from mcp.server.stdio import stdio_server
except ImportError:
    print("MCP SDK not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

try:
    import edge_tts
except ImportError:
    print("edge-tts not installed. Run: pip install edge-tts", file=sys.stderr)
    sys.exit(1)

# =============================================================================
# CONFIGURATION
# =============================================================================
VOICES = {
    "andrew": "en-US-AndrewNeural",      # DEFAULT - Natural, warm
    "adam": "en-US-AdamMultilingualNeural",
    "guy": "en-US-GuyNeural",
    "davis": "en-US-DavisNeural",
    "jenny": "en-US-JennyNeural",
    "aria": "en-US-AriaNeural",
    "amanda": "en-US-AmandaMultilingualNeural",
    "michelle": "en-US-MichelleNeural",
}

DEFAULT_VOICE = "andrew"
AUDIO_DIR = Path("/mnt/d/.playwright-mcp/audio")
CACHE_DIR = AUDIO_DIR / "cache"
MAX_RETRIES = 5
BASE_DELAY = 1
TIMEOUT = 60

server = Server("voice")

# =============================================================================
# CACHING
# =============================================================================
def get_cache_key(text: str, voice: str) -> str:
    content = f"{voice}:{text}"
    return hashlib.md5(content.encode()).hexdigest()[:16]

def get_cached_audio(text: str, voice: str) -> str | None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = get_cache_key(text, voice)
    cache_file = CACHE_DIR / f"{cache_key}.mp3"
    if cache_file.exists() and cache_file.stat().st_size > 1000:
        return str(cache_file)
    return None

def save_to_cache(audio_file: str, text: str, voice: str) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = get_cache_key(text, voice)
    cache_file = CACHE_DIR / f"{cache_key}.mp3"
    shutil.copy2(audio_file, cache_file)
    return str(cache_file)

# =============================================================================
# AUDIO PLAYBACK
# =============================================================================
LOCK_FILE = AUDIO_DIR / ".speaking.lock"

def _run_ps(cmd, timeout=30):
    """Run a PowerShell command via bridge with subprocess fallback."""
    if _HAS_BRIDGE:
        return _ps_bridge(cmd, timeout)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, timeout=timeout)
    class _R:
        stdout = r.stdout; stderr = r.stderr; returncode = r.returncode; success = r.returncode == 0
    return _R()

def _stop_existing_playback():
    """Kill any running speech playback to prevent echo/overlap."""
    try:
        _run_ps(
            "Get-Process powershell | Where-Object {$_.Id -ne $PID} | ForEach-Object { if ((Get-WmiObject Win32_Process -Filter \"ProcessId=$($_.Id)\").CommandLine -like '*MediaPlayer*') { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue } }",
            timeout=5
        )
    except Exception:
        pass

def play_audio(audio_file: str) -> bool:
    """Play audio file (fire-and-forget, non-blocking)"""
    try:
        # Prevent overlapping playback
        _stop_existing_playback()

        win_path = str(audio_file).replace("/mnt/d", "D:")
        # Fire-and-forget: Start-Process launches a hidden powershell that plays and exits
        script = (
            "Start-Process powershell.exe -WindowStyle Hidden -ArgumentList '"
            "-NoProfile -Command "
            "Add-Type -AssemblyName PresentationCore; "
            "$p = New-Object System.Windows.Media.MediaPlayer; "
            f"$p.Open([Uri]\\\"{win_path}\\\"); "
            "Start-Sleep -Milliseconds 50; "
            "$p.Play(); "
            "while ($p.NaturalDuration.HasTimeSpan -eq $false) { Start-Sleep -Milliseconds 100 }; "
            "Start-Sleep -Seconds ($p.NaturalDuration.TimeSpan.TotalSeconds + 0.5); "
            "$p.Close()"
            "'"
        )
        _run_ps(script, timeout=5)
        return True
    except Exception as e:
        print(f"Playback error: {e}", file=sys.stderr)
        return False

# =============================================================================
# BULLETPROOF TTS
# =============================================================================
async def generate_speech(text: str, voice_id: str, output_file: str) -> bool:
    try:
        communicate = edge_tts.Communicate(text, voice_id)
        await asyncio.wait_for(communicate.save(output_file), timeout=TIMEOUT)
        return os.path.exists(output_file) and os.path.getsize(output_file) > 1000
    except asyncio.TimeoutError:
        return False
    except Exception:
        return False

async def speak_text(text: str, voice: str = DEFAULT_VOICE, rate: str = "+0%") -> str:
    """Generate and play speech with retry logic. ALWAYS tries to work."""

    # Check cache first
    cached = get_cached_audio(text, voice)
    if cached:
        play_audio(cached)
        return cached

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    voice_id = VOICES.get(voice.lower(), VOICES[DEFAULT_VOICE])
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    audio_file = str(AUDIO_DIR / f"speech_{timestamp}.mp3")

    for attempt in range(1, MAX_RETRIES + 1):
        delay = BASE_DELAY * (2 ** (attempt - 1))

        if await generate_speech(text, voice_id, audio_file):
            save_to_cache(audio_file, text, voice)
            play_audio(audio_file)
            return audio_file

        if attempt < MAX_RETRIES:
            await asyncio.sleep(delay)

    return ""

# =============================================================================
# MCP TOOLS
# =============================================================================
@server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="speak",
            description="Read text out loud using natural text-to-speech. Use this to read summaries, conclusions, or any text to the user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to speak out loud"},
                    "voice": {
                        "type": "string",
                        "enum": list(VOICES.keys()),
                        "description": "Voice to use (andrew, adam, guy, davis, jenny, aria, amanda, michelle)",
                        "default": "andrew"
                    },
                    "rate": {
                        "type": "string",
                        "description": "Speech rate adjustment (e.g., '+10%' for faster, '-10%' for slower)",
                        "default": "+0%"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="speak_summary",
            description="Speak a brief summary. Automatically formats for spoken delivery.",
            inputSchema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "The summary to speak"},
                    "voice": {"type": "string", "enum": list(VOICES.keys()), "default": "andrew"}
                },
                "required": ["summary"]
            }
        ),
        Tool(
            name="list_voices",
            description="List available voice options",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="stop_speaking",
            description="Stop any currently playing speech",
            inputSchema={"type": "object", "properties": {}}
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    try:
        if name == "speak":
            text = arguments.get("text", "")
            voice = arguments.get("voice", DEFAULT_VOICE)
            rate = arguments.get("rate", "+0%")

            if not text:
                return [TextContent(type="text", text="No text provided to speak")]

            audio_file = await speak_text(text, voice, rate)

            if audio_file:
                return [TextContent(type="text", text=f"Speaking with {voice} voice: \"{text[:100]}{'...' if len(text) > 100 else ''}\"")]
            else:
                return [TextContent(type="text", text="Speech generation failed after all retries. Check internet connection.")]

        elif name == "speak_summary":
            summary = arguments.get("summary", "")
            voice = arguments.get("voice", DEFAULT_VOICE)
            spoken_text = f"Here's the summary. {summary}"
            audio_file = await speak_text(spoken_text, voice)
            return [TextContent(type="text", text=f"Speaking summary with {voice} voice")]

        elif name == "list_voices":
            voice_list = "\n".join([f"- {name}: {voice_id}" for name, voice_id in VOICES.items()])
            return [TextContent(type="text", text=f"Available voices:\n{voice_list}")]

        elif name == "stop_speaking":
            _run_ps(
                "Get-Process | Where-Object {$_.MainWindowTitle -like '*MediaPlayer*'} | Stop-Process -Force -ErrorAction SilentlyContinue",
                timeout=10
            )
            return [TextContent(type="text", text="Stopped any playing speech")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())

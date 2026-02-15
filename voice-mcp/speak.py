#!/usr/bin/env python3
"""
Multi-Engine TTS Speech - Tries multiple engines for reliable voice output.
Usage: python speak.py "Text to speak" [voice]

Priority Order:
1. Google TTS (gTTS) - Natural voice, FREE, reliable
2. Microsoft Edge TTS - Best quality but sometimes rate-limited
3. Windows SAPI - Always works offline

This ensures you ALWAYS get voice output.
"""

import asyncio
import subprocess
import sys
import os
import socket
import hashlib
from datetime import datetime
from pathlib import Path

# PowerShell Bridge — 100x faster than subprocess.run(powershell.exe...)
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    def _run_ps(command: str, timeout: int = 30):
        """Run PowerShell via bridge (fast) with subprocess fallback."""
        return _ps_bridge(command, timeout)
except ImportError:
    def _run_ps(command: str, timeout: int = 30):
        """Fallback: direct subprocess."""
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                           capture_output=True, text=True, timeout=timeout)
        class _R:
            stdout = r.stdout; stderr = r.stderr; returncode = r.returncode; success = r.returncode == 0
        return _R()

# =============================================================================
# FORCE IPv4 - Critical fix for Edge TTS connectivity in WSL
# =============================================================================
original_getaddrinfo = socket.getaddrinfo
def ipv4_only_getaddrinfo(*args, **kwargs):
    responses = original_getaddrinfo(*args, **kwargs)
    ipv4_responses = [r for r in responses if r[0] == socket.AF_INET]
    return ipv4_responses if ipv4_responses else responses
socket.getaddrinfo = ipv4_only_getaddrinfo
socket.setdefaulttimeout(30)

# =============================================================================
# CONFIGURATION
# =============================================================================
EDGE_VOICES = {
    # Primary voices
    "andrew": "en-US-AndrewNeural",      # Male - natural, warm (Planner)
    "guy": "en-US-GuyNeural",            # Male - clear
    "christopher": "en-US-ChristopherNeural",  # Male
    "eric": "en-US-EricNeural",          # Male
    "jenny": "en-US-JennyNeural",        # Female - natural (Narrator)
    "aria": "en-US-AriaNeural",          # Female
    "michelle": "en-US-MichelleNeural",  # Female

    # Alternative male voices (more natural sounding)
    "brian": "en-US-BrianNeural",        # Male - very natural, conversational
    "roger": "en-US-RogerNeural",        # Male - mature, professional
    "steffan": "en-US-SteffanNeural",    # Male - younger, casual
    "ryan": "en-GB-RyanNeural",          # Male - British, natural
    "thomas": "en-GB-ThomasNeural",      # Male - British, warm
    "liam": "en-CA-LiamNeural",          # Male - Canadian, friendly

    # Legacy aliases for compatibility
    "adam": "en-US-ChristopherNeural",   # Fallback to Christopher
    "davis": "en-US-EricNeural",         # Fallback to Eric
}

DEFAULT_VOICE = "andrew"

# Use WSL paths for file operations, convert to Windows paths for playback
AUDIO_DIR_WSL = Path("/mnt/d/.playwright-mcp/audio")
AUDIO_DIR_WIN = r"D:\.playwright-mcp\audio"
CACHE_DIR = AUDIO_DIR_WSL / "cache"
MAX_RETRIES = 3  # Reduced since we have multiple engines
TIMEOUT = 30

def wsl_to_win_path(wsl_path: str) -> str:
    """Convert WSL path to Windows path for PowerShell playback.
    Validates against path traversal attacks."""
    # Resolve the path first to eliminate .. sequences
    resolved = str(Path(wsl_path).resolve())
    if resolved.startswith("/mnt/"):
        parts = resolved[5:].split("/", 1)
        drive = parts[0].upper()
        if not drive.isalpha() or len(drive) != 1:
            raise ValueError(f"Invalid drive letter: {drive}")
        rest = parts[1].replace('/', '\\') if len(parts) > 1 else ""
        return f"{drive}:\\" + rest
    return resolved.replace('/', '\\')

# =============================================================================
# CACHING - Reuse audio for identical text
# =============================================================================
def get_cache_key(text: str, engine: str, voice: str = "andrew") -> str:
    """Generate cache key from text, engine, AND voice"""
    content = f"{engine}:{voice}:{text}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def get_cached_audio(text: str, engine: str, voice: str = "andrew") -> str | None:
    """Check if we have cached audio for this text AND voice"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = get_cache_key(text, engine, voice)
    cache_file = CACHE_DIR / f"{cache_key}.mp3"

    if cache_file.exists() and cache_file.stat().st_size > 1000:
        return str(cache_file)
    return None


def save_to_cache(audio_file: str, text: str, engine: str, voice: str = "andrew") -> str:
    """Save audio file to cache with voice-specific key"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = get_cache_key(text, engine, voice)
    cache_file = CACHE_DIR / f"{cache_key}.mp3"

    import shutil
    shutil.copy2(audio_file, cache_file)
    return str(cache_file)


# =============================================================================
# AUDIO PLAYBACK
# =============================================================================
def get_audio_duration(audio_file: str) -> float:
    """Get audio duration in seconds using ffprobe"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception:
        pass

    # Fallback: estimate from file size (very rough: ~6KB per second for mp3)
    try:
        file_size = os.path.getsize(audio_file)
        return max(1, file_size / 6000)  # Minimum 1 second, not 5
    except:
        return 30  # Default fallback


def _stop_existing_playback():
    """Kill any running speech playback to prevent echo/overlap."""
    try:
        _run_ps("Get-Process powershell | Where-Object {$_.Id -ne $PID} | ForEach-Object { if ((Get-WmiObject Win32_Process -Filter \"ProcessId=$($_.Id)\").CommandLine -like '*MediaPlayer*') { Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue } }", timeout=5)
    except Exception:
        pass

def play_audio(audio_file: str) -> bool:
    """Play audio file using PowerShell via bridge"""
    try:
        _stop_existing_playback()
        win_path = wsl_to_win_path(audio_file)

        # Get actual audio duration
        duration = get_audio_duration(audio_file)
        wait_ms = int((duration + 0.2) * 1000)

        script = (
            'Add-Type -AssemblyName PresentationCore; '
            '$player = New-Object System.Windows.Media.MediaPlayer; '
            f'$player.Open([Uri]"{win_path}"); '
            'Start-Sleep -Milliseconds 50; '
            '$player.Play(); '
            f'Start-Sleep -Milliseconds {wait_ms}; '
            '$player.Stop(); '
            '$player.Close()'
        )

        result = _run_ps(script, timeout=int(duration) + 30)
        return result.success

    except Exception as e:
        print(f"Playback error: {e}")
        return play_audio_pygame(audio_file)


def play_audio_pygame(audio_file: str) -> bool:
    """Fallback: Play audio using pygame"""
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        pygame.mixer.quit()
        return True
    except Exception as e:
        print(f"Pygame playback error: {e}")
        return False


def play_audio_fallback(audio_file: str) -> bool:
    """Fallback: Play audio using PowerShell via bridge"""
    try:
        win_path = wsl_to_win_path(audio_file)

        play_script = (
            'Add-Type -AssemblyName presentationCore; '
            '$mediaPlayer = New-Object system.windows.media.mediaplayer; '
            f'$mediaPlayer.open("{win_path}"); '
            'Start-Sleep -Milliseconds 50; '
            '$mediaPlayer.Play(); '
            f'$fileSize = (Get-Item "{win_path}").Length; '
            '$estimatedSeconds = [math]::Max(2, [math]::Ceiling($fileSize / 16000)); '
            'Start-Sleep -Seconds $estimatedSeconds; '
            '$mediaPlayer.Stop(); '
            '$mediaPlayer.Close()'
        )

        result = _run_ps(play_script, timeout=60)
        return result.success
    except Exception as e:
        print(f"Fallback playback error: {e}")
        return False


# =============================================================================
# ENGINE 1: Google TTS (Primary - Most Reliable)
# =============================================================================
def speak_with_gtts(text: str, output_file: str) -> bool:
    """
    Google TTS - Natural voice, FREE, very reliable.
    Uses Google Translate's TTS API.
    """
    try:
        from gtts import gTTS

        print("Trying Google TTS...")
        tts = gTTS(text, lang='en', tld='com')  # US English
        tts.save(output_file)

        if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
            print("Google TTS: Success!")
            return True
        return False
    except ImportError:
        print("Google TTS: Not installed (pip install gtts)")
        return False
    except Exception as e:
        print(f"Google TTS: Failed - {e}")
        return False


# =============================================================================
# ENGINE 2: Microsoft Edge TTS (Best Quality When Available)
# =============================================================================
async def speak_with_edge_async(text: str, voice_id: str, output_file: str) -> bool:
    """
    Microsoft Edge TTS - Best neural voice quality.
    Uses edge-tts 7.2.1 which works reliably.
    """
    try:
        import edge_tts

        print(f"Trying Edge TTS ({voice_id})...")

        communicate = edge_tts.Communicate(text, voice_id)
        await asyncio.wait_for(communicate.save(output_file), timeout=TIMEOUT)

        if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
            print("Edge TTS: Success!")
            return True
        return False
    except ImportError:
        print("Edge TTS: Not installed")
        return False
    except asyncio.TimeoutError:
        print("Edge TTS: Timeout")
        return False
    except Exception as e:
        print(f"Edge TTS: Failed - {e}")
        return False


def speak_with_edge(text: str, voice: str, output_file: str) -> bool:
    """Synchronous wrapper for Edge TTS"""
    voice_id = EDGE_VOICES.get(voice.lower(), EDGE_VOICES[DEFAULT_VOICE])
    return asyncio.run(speak_with_edge_async(text, voice_id, output_file))


# =============================================================================
# ENGINE 3: Windows SAPI (Fallback - Always Works)
# =============================================================================
def speak_with_sapi(text: str) -> bool:
    """
    Windows SAPI - Built-in Windows speech.
    Not as natural, but ALWAYS works offline.
    """
    try:
        import re
        # Strip any characters that could break PowerShell string interpolation
        safe_text = re.sub(r'[^\w\s.,!?;:\-\'()/]', '', text)
        safe_text = safe_text.replace("'", "''").replace('"', '`"')

        sapi_script = (
            'Add-Type -AssemblyName System.Speech; '
            '$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
            '$synth.Rate = 0; '
            f'$synth.Speak("{safe_text}"); '
            '$synth.Dispose()'
        )

        print("Trying Windows SAPI...")
        result = _run_ps(sapi_script, timeout=120)

        if result.success:
            print("Windows SAPI: Success!")
            return True
        return False
    except Exception as e:
        print(f"Windows SAPI: Failed - {e}")
        return False


# =============================================================================
# MAIN SPEECH FUNCTION - Tries All Engines
# =============================================================================
def speak(text: str, voice: str = DEFAULT_VOICE, rate: str = "+0%") -> bool:
    """
    Speak text using the best available engine.
    Tries: Edge TTS (Andrew voice) -> Google TTS -> Windows SAPI

    Edge TTS is the PREFERRED engine for natural Andrew voice.
    Falls back to alternatives only when Edge TTS is rate-limited.
    """
    AUDIO_DIR_WSL.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    audio_file = str(AUDIO_DIR_WSL / f"speech_{timestamp}.mp3")

    # Check cache for this specific voice
    for engine in ["edge", "gtts"]:
        cached = get_cached_audio(text, engine, voice)
        if cached:
            print(f"Using cached audio ({engine}, {voice})")
            return play_audio(cached)

    # ENGINE 1: Edge TTS (PREFERRED - Best Quality, multiple voices)
    if speak_with_edge(text, voice, audio_file):
        save_to_cache(audio_file, text, "edge", voice)
        return play_audio(audio_file)

    # ENGINE 2: Google TTS (Fallback - only one voice available)
    print("Edge TTS unavailable (rate-limited). Trying Google TTS...")
    if speak_with_gtts(text, audio_file):
        save_to_cache(audio_file, text, "gtts", voice)
        return play_audio(audio_file)

    # ENGINE 3: Windows SAPI (Last Resort - Always Works)
    print("All cloud TTS failed. Using Windows SAPI fallback...")
    return speak_with_sapi(text)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python speak.py 'text' [voice]")
        print(f"Voices (for Edge TTS): {', '.join(EDGE_VOICES.keys())}")
        print("\nEngines tried in order: Google TTS -> Edge TTS -> Windows SAPI")
        sys.exit(1)

    text = sys.argv[1]
    voice = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_VOICE

    success = speak(text, voice)
    sys.exit(0 if success else 1)

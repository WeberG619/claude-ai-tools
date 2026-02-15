#!/usr/bin/env python3
"""
Live Subtitle Reader
Watches the screen for subtitles and speaks them out loud

Usage:
    python reader.py                    # Default: right monitor, Netflix style
    python reader.py --monitor 0        # Primary monitor
    python reader.py --test             # Take one screenshot and show subtitle area
"""

import sys
import time
import argparse
import subprocess
from pathlib import Path

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False


def _run_ps(cmd, timeout=30):
    if _HAS_BRIDGE:
        return _ps_bridge(cmd, timeout)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, timeout=timeout)
    class _R:
        stdout = r.stdout; stderr = r.stderr; returncode = r.returncode; success = r.returncode == 0
    return _R()

# For screenshot and OCR
try:
    from PIL import Image, ImageGrab
    import pytesseract
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

# For Windows screenshot with monitor selection
try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False


VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")


def get_monitors():
    """Get monitor info using mss"""
    if not HAS_MSS:
        return None
    with mss.mss() as sct:
        # sct.monitors[0] is the "all monitors" virtual screen
        # sct.monitors[1] is primary, [2] is second, etc.
        return sct.monitors


def capture_subtitle_region(monitor_index: int = 0, bottom_percent: float = 0.15):
    """
    Capture the bottom portion of the screen where subtitles appear.

    Args:
        monitor_index: Which monitor (0=all, 1=primary, 2=second, etc.)
        bottom_percent: What percentage of the bottom to capture (default 15%)

    Returns:
        PIL Image of the subtitle region
    """
    if HAS_MSS:
        with mss.mss() as sct:
            monitors = sct.monitors
            if monitor_index >= len(monitors):
                monitor_index = 1  # Default to primary

            mon = monitors[monitor_index]

            # Calculate subtitle region (bottom portion)
            height = mon['height']
            subtitle_top = int(height * (1 - bottom_percent))

            region = {
                'left': mon['left'],
                'top': mon['top'] + subtitle_top,
                'width': mon['width'],
                'height': int(height * bottom_percent)
            }

            screenshot = sct.grab(region)
            return Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
    else:
        # Fallback to PIL ImageGrab (primary monitor only)
        screen = ImageGrab.grab()
        width, height = screen.size
        subtitle_top = int(height * (1 - bottom_percent))
        return screen.crop((0, subtitle_top, width, height))


def extract_text(image: Image.Image) -> str:
    """Extract text from image using OCR"""
    # Preprocess for better OCR
    # Convert to grayscale
    gray = image.convert('L')

    # Increase contrast (subtitles are usually white on dark)
    # Threshold to make text clearer
    threshold = 180
    binary = gray.point(lambda x: 255 if x > threshold else 0, '1')

    # OCR
    text = pytesseract.image_to_string(binary, config='--psm 6')

    # Clean up
    text = text.strip()
    text = ' '.join(text.split())  # Normalize whitespace

    return text


def speak(text: str, voice: str = "andrew"):
    """Speak text using voice MCP"""
    if not text:
        return

    # Use the voice script
    try:
        subprocess.run(
            ["python3", str(VOICE_SCRIPT), text],
            timeout=30,
            capture_output=True
        )
    except Exception as e:
        print(f"Speech error: {e}")


def speak_windows(text: str):
    """Speak using Windows PowerShell (faster, no network)"""
    if not text:
        return

    # Escape for PowerShell
    escaped = text.replace("'", "''")

    try:
        cmd = (f"Add-Type -AssemblyName System.Speech; "
               f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
               f"$synth.Rate = 2; "
               f"$synth.Speak('{escaped}')")
        _run_ps(cmd, timeout=30)
    except Exception as e:
        print(f"Speech error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Live Subtitle Reader")
    parser.add_argument("--monitor", type=int, default=0,
                       help="Monitor index (0=all, 1=primary, 2=second, 3=third)")
    parser.add_argument("--interval", type=float, default=1.0,
                       help="Seconds between checks (default: 1.0)")
    parser.add_argument("--bottom", type=float, default=0.12,
                       help="Bottom percentage of screen to capture (default: 0.12)")
    parser.add_argument("--test", action="store_true",
                       help="Test mode: capture once and show")
    parser.add_argument("--windows-voice", action="store_true",
                       help="Use Windows built-in TTS (faster)")
    parser.add_argument("--voice", default="andrew",
                       help="Voice to use (andrew, jenny, etc.)")
    args = parser.parse_args()

    if not HAS_DEPS:
        print("Missing dependencies. Install with:")
        print("  pip install pillow pytesseract mss")
        print("\nAlso install Tesseract OCR:")
        print("  Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
        sys.exit(1)

    # Test mode
    if args.test:
        print(f"Capturing subtitle region from monitor {args.monitor}...")
        img = capture_subtitle_region(args.monitor, args.bottom)

        # Save for inspection
        test_path = Path(__file__).parent / "test_capture.png"
        img.save(test_path)
        print(f"Saved to: {test_path}")

        # Try OCR
        text = extract_text(img)
        print(f"Detected text: '{text}'")

        if text:
            print("Speaking...")
            if args.windows_voice:
                speak_windows(text)
            else:
                speak(text, args.voice)
        return

    # Main loop
    print(f"🎬 Subtitle Reader Started")
    print(f"   Monitor: {args.monitor}")
    print(f"   Interval: {args.interval}s")
    print(f"   Voice: {'Windows TTS' if args.windows_voice else args.voice}")
    print(f"   Press Ctrl+C to stop\n")

    last_text = ""
    speak_func = speak_windows if args.windows_voice else lambda t: speak(t, args.voice)

    try:
        while True:
            # Capture
            img = capture_subtitle_region(args.monitor, args.bottom)

            # OCR
            text = extract_text(img)

            # Only speak if text changed
            if text and text != last_text:
                print(f"📖 {text}")
                speak_func(text)
                last_text = text

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\n👋 Stopped")


if __name__ == "__main__":
    main()

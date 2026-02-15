#!/usr/bin/env python3
"""
Live Subtitle Reader - Windows Native Version
Uses Windows built-in OCR and TTS

Usage:
    python reader_windows.py                # Start reading from right monitor
    python reader_windows.py --test         # Test capture once
    python reader_windows.py --monitor 0    # Specific monitor (0=right, 1=center, 2=left)
"""

import sys
import time
import argparse
import subprocess
import tempfile
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

# For screenshots
try:
    import mss
    from PIL import Image
except ImportError:
    print("Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "mss", "pillow", "-q"])
    import mss
    from PIL import Image


def get_monitor_bounds(monitor_name: str = "right"):
    """Get monitor bounds based on name (left, center, right)"""
    with mss.mss() as sct:
        monitors = sct.monitors[1:]  # Skip the "all monitors" entry

        if len(monitors) == 1:
            return monitors[0]

        # Sort by x position
        sorted_mons = sorted(monitors, key=lambda m: m['left'])

        if monitor_name == "left":
            return sorted_mons[0]
        elif monitor_name == "right":
            return sorted_mons[-1]
        else:  # center
            return sorted_mons[len(sorted_mons) // 2]


def capture_subtitle_region(monitor_name: str = "right", bottom_percent: float = 0.15):
    """Capture bottom portion where subtitles appear"""
    with mss.mss() as sct:
        mon = get_monitor_bounds(monitor_name)

        height = mon['height']
        subtitle_top = int(height * (1 - bottom_percent))

        region = {
            'left': mon['left'],
            'top': mon['top'] + subtitle_top,
            'width': mon['width'],
            'height': int(height * bottom_percent)
        }

        screenshot = sct.grab(region)
        img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
        return img


def ocr_with_windows(image_path: str) -> str:
    """Use Windows built-in OCR via PowerShell"""
    ps_script = f'''
    Add-Type -AssemblyName System.Runtime.WindowsRuntime

    $null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
    $null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]

    # Async helper
    $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? {{ $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }})[0]
    Function Await($WinRtTask, $ResultType) {{
        $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
        $netTask = $asTask.Invoke($null, @($WinRtTask))
        $netTask.Wait(-1) | Out-Null
        $netTask.Result
    }}

    # Load image
    $file = [Windows.Storage.StorageFile]::GetFileFromPathAsync("{image_path}")
    $storageFile = Await $file ([Windows.Storage.StorageFile])

    $stream = $storageFile.OpenAsync([Windows.Storage.FileAccessMode]::Read)
    $randomAccessStream = Await $stream ([Windows.Storage.Streams.IRandomAccessStream])

    $decoder = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($randomAccessStream)
    $bitmapDecoder = Await $decoder ([Windows.Graphics.Imaging.BitmapDecoder])

    $bitmap = $bitmapDecoder.GetSoftwareBitmapAsync()
    $softwareBitmap = Await $bitmap ([Windows.Graphics.Imaging.SoftwareBitmap])

    # OCR
    $ocrEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    $ocrResult = Await ($ocrEngine.RecognizeAsync($softwareBitmap)) ([Windows.Media.Ocr.OcrResult])

    $ocrResult.Text
    '''

    try:
        result = _run_ps(ps_script, timeout=10)
        return result.stdout.strip()
    except Exception as e:
        return ""


def simple_ocr_tesseract(image_path: str) -> str:
    """Try Tesseract if available"""
    try:
        import pytesseract
        img = Image.open(image_path)
        # Preprocess for white text on dark background
        gray = img.convert('L')
        # Invert and threshold
        binary = gray.point(lambda x: 255 if x > 150 else 0)
        return pytesseract.image_to_string(binary, config='--psm 6').strip()
    except:
        return ""


def speak_windows(text: str, rate: int = 3):
    """Speak using Windows SAPI"""
    if not text or len(text) < 2:
        return

    # Clean text
    text = text.replace('"', "'").replace('\n', ' ').strip()
    if not text:
        return

    escaped = text.replace("'", "''")

    cmd = (f"Add-Type -AssemblyName System.Speech; "
           f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
           f"$s.Rate = {rate}; "
           f"$s.Speak('{escaped}')")
    if _HAS_BRIDGE:
        try:
            _ps_bridge(cmd, timeout=30)
        except Exception:
            pass
    else:
        subprocess.Popen([
            "powershell.exe", "-Command", cmd
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description="Live Subtitle Reader")
    parser.add_argument("--monitor", default="right", choices=["left", "center", "right"],
                       help="Which monitor (default: right)")
    parser.add_argument("--interval", type=float, default=0.8,
                       help="Seconds between checks")
    parser.add_argument("--bottom", type=float, default=0.12,
                       help="Bottom percentage to capture")
    parser.add_argument("--test", action="store_true",
                       help="Test mode: capture once")
    parser.add_argument("--rate", type=int, default=3,
                       help="Speech rate (-10 to 10, default 3)")
    args = parser.parse_args()

    # Create temp dir for images
    temp_dir = Path(tempfile.gettempdir()) / "subtitle_reader"
    temp_dir.mkdir(exist_ok=True)
    temp_img = temp_dir / "subtitle.png"

    if args.test:
        print(f"Capturing from {args.monitor} monitor...")
        img = capture_subtitle_region(args.monitor, args.bottom)

        # Save
        test_path = Path(__file__).parent / "test_subtitle.png"
        img.save(str(test_path))
        print(f"Saved: {test_path}")

        # Also save to temp for OCR
        img.save(str(temp_img))

        # Try OCR
        print("Trying Tesseract OCR...")
        text = simple_ocr_tesseract(str(temp_img))
        if text:
            print(f"Tesseract result: '{text}'")
        else:
            print("Tesseract failed, trying Windows OCR...")
            text = ocr_with_windows(str(temp_img).replace('/', '\\'))
            print(f"Windows OCR result: '{text}'")

        if text:
            print("Speaking...")
            speak_windows(text, args.rate)
        return

    # Main loop
    print(f"🎬 Subtitle Reader")
    print(f"   Monitor: {args.monitor}")
    print(f"   Interval: {args.interval}s")
    print(f"   Press Ctrl+C to stop\n")

    last_text = ""

    try:
        while True:
            # Capture
            img = capture_subtitle_region(args.monitor, args.bottom)
            img.save(str(temp_img))

            # OCR (try Tesseract first, fall back to Windows)
            text = simple_ocr_tesseract(str(temp_img))
            if not text:
                text = ocr_with_windows(str(temp_img).replace('/', '\\'))

            # Clean
            text = ' '.join(text.split())

            # Speak if changed
            if text and text != last_text and len(text) > 3:
                print(f"📖 {text}")
                speak_windows(text, args.rate)
                last_text = text

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n👋 Stopped")


if __name__ == "__main__":
    main()

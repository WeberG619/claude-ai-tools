#!/bin/bash
# Silent TTS - plays through Windows MCI, no visible windows
TEXT="$1"
VOICE="${2:-en-US-AndrewNeural}"
RATE="${3:-+5%}"
FILE="/mnt/d/demo_voice_$(date +%s%N).mp3"

# Generate audio
edge-tts --text "$TEXT" --voice "$VOICE" --rate "$RATE" --write-media "$FILE" 2>/dev/null

if [ ! -f "$FILE" ]; then
  echo "TTS generation failed"
  exit 1
fi

# Convert path for Windows
WIN_PATH=$(echo "$FILE" | sed 's|/mnt/d/|D:\\|g' | sed 's|/|\\|g')

# Play silently via MCI
powershell.exe -NoProfile -Command "
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class WinMM {
    [DllImport(\"winmm.dll\")]
    public static extern int mciSendString(string command, System.Text.StringBuilder buffer, int bufferSize, IntPtr hwnd);
}
'@
[WinMM]::mciSendString('open \"$WIN_PATH\" type mpegvideo alias dv', \$null, 0, [IntPtr]::Zero)
[WinMM]::mciSendString('play dv wait', \$null, 0, [IntPtr]::Zero)
[WinMM]::mciSendString('close dv', \$null, 0, [IntPtr]::Zero)
" 2>/dev/null

# Cleanup
rm -f "$FILE" 2>/dev/null

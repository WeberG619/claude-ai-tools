#!/bin/bash
# Quick TTS that plays through Windows speakers
TEXT="$1"
VOICE="${2:-en-US-AndrewMultilingualNeural}"
RATE="${3:-+5%}"
FILE="/mnt/d/demo_voice_$(date +%s).mp3"
edge-tts --text "$TEXT" --voice "$VOICE" --rate "$RATE" --write-media "$FILE" 2>/dev/null
WIN_FILE=$(echo "$FILE" | sed 's|/mnt/d/|D:\\|' | sed 's|/|\\|g')
powershell.exe -NoProfile -Command "Start-Process '$WIN_FILE'" 2>/dev/null
# Estimate duration: ~100ms per word
WORDS=$(echo "$TEXT" | wc -w)
SLEEP=$(( WORDS / 3 ))
[ $SLEEP -lt 2 ] && SLEEP=2
sleep $SLEEP
rm -f "$FILE" 2>/dev/null

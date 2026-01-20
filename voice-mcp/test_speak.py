#!/usr/bin/env python3
"""Test script for Edge TTS speech"""
import asyncio
import subprocess
import sys
import os
import socket

# Force IPv4 to fix connectivity issues
original_getaddrinfo = socket.getaddrinfo
def ipv4_only_getaddrinfo(*args, **kwargs):
    responses = original_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET] or responses
socket.getaddrinfo = ipv4_only_getaddrinfo

try:
    import edge_tts
except ImportError:
    print("Installing edge-tts...")
    subprocess.run([sys.executable, "-m", "pip", "install", "edge-tts"])
    import edge_tts

async def speak(text, voice="en-US-AndrewNeural"):
    audio_file = r"D:\.playwright-mcp\audio\speech_test.mp3"
    os.makedirs(os.path.dirname(audio_file), exist_ok=True)

    # Generate speech
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(audio_file)

    # Play via PowerShell
    play_cmd = f'''
    Add-Type -AssemblyName PresentationCore
    $player = New-Object System.Windows.Media.MediaPlayer
    $player.Open("{audio_file}")
    Start-Sleep -Milliseconds 300
    $player.Play()
    while ($player.NaturalDuration.HasTimeSpan -eq $false) {{ Start-Sleep -Milliseconds 100 }}
    $duration = $player.NaturalDuration.TimeSpan.TotalSeconds
    Start-Sleep -Seconds ($duration + 0.5)
    $player.Close()
    '''
    subprocess.run(["powershell.exe", "-NoProfile", "-Command", play_cmd])

if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else "Test speech working."
    asyncio.run(speak(text))

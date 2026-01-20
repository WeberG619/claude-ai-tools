"""
Minimal test to see if voice recognition is working
"""
import sys
import time
from voice_cli import VoiceCLI

print("Testing voice recognition...")
print("Say 'Claude' followed by a word or phrase")

cli = VoiceCLI(timeout=15)
result = cli.get_command()

if result:
    print(f"SUCCESS: Heard '{result}'")
else:
    print("TIMEOUT: No speech detected")
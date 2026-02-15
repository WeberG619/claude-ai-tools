#!/usr/bin/env python3
"""
Claude Voice Wrapper - Speaks all Claude responses automatically
Run this instead of 'claude' directly for voice mode
"""

import subprocess
import sys
import re
import os
import threading
import queue

# TTS script location
TTS_SCRIPT = "/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py"

def speak_async(text):
    """Speak text in background thread"""
    def _speak():
        try:
            # Clean text for speech
            text_clean = re.sub(r'```[\s\S]*?```', ' code block ', text)  # Replace code blocks
            text_clean = re.sub(r'`[^`]+`', '', text_clean)  # Remove inline code
            text_clean = re.sub(r'\[.*?\]\(.*?\)', '', text_clean)  # Remove markdown links
            text_clean = re.sub(r'[#*_~]', '', text_clean)  # Remove markdown formatting
            text_clean = re.sub(r'\n+', '. ', text_clean)  # Newlines to periods
            text_clean = re.sub(r'\s+', ' ', text_clean).strip()  # Collapse whitespace

            if len(text_clean) > 10:  # Only speak if meaningful content
                # Truncate very long responses
                if len(text_clean) > 500:
                    text_clean = text_clean[:500] + "... I've written more details in the terminal."

                subprocess.run(
                    ["python3", TTS_SCRIPT, text_clean],
                    timeout=60,
                    capture_output=True
                )
        except Exception as e:
            pass  # Silent fail for TTS

    thread = threading.Thread(target=_speak, daemon=True)
    thread.start()
    return thread


def main():
    """Run claude and speak responses"""
    print("🎤 Voice Mode Active - I'll speak my responses")
    print("-" * 50)

    # Pass through to claude with all arguments
    args = ["claude"] + sys.argv[1:]

    # Run claude interactively, capturing output
    process = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ, "FORCE_COLOR": "1"}
    )

    response_buffer = []
    in_response = False

    try:
        for line in process.stdout:
            # Print to terminal
            print(line, end='', flush=True)

            # Detect Claude's response (after user input)
            # This is heuristic - Claude responses typically follow ╭─ or similar
            if '╭─' in line or line.strip().startswith('>'):
                in_response = True
                response_buffer = []
            elif in_response:
                # Collect response text
                clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)  # Remove ANSI
                if clean_line.strip():
                    response_buffer.append(clean_line.strip())

                # Detect end of response (empty line or new prompt)
                if '╰─' in line or line.strip() == '':
                    if response_buffer:
                        full_response = ' '.join(response_buffer)
                        speak_async(full_response)
                        response_buffer = []
                    in_response = False

    except KeyboardInterrupt:
        process.terminate()

    process.wait()
    return process.returncode


if __name__ == "__main__":
    sys.exit(main())

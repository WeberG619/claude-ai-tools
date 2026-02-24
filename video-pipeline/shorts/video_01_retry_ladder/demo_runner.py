#!/usr/bin/env python3
"""
Demo Runner for Video 01: Retry Ladder
Runs a visual terminal demo of the adaptive retry system.
Timed to match voiceover segments. Start screen recording FIRST, then run this.

Timing (from audio durations):
  01_hook:        0.0s - 5.0s    "When my AI agent fails..."
  02_intro:       5.0s - 7.0s    "It runs a strategy ladder."
  03_quickfix:    7.0s - 12.0s   "First — quick fix..."
  04_refactor:   12.0s - 17.0s   "If that fails..."
  05_alternative: 17.0s - 22.0s  "Still failing?..."
  06_escalate:   22.0s - 28.0s   "And if nothing works..."
  07_result:     28.0s - 33.0s   "Four strategies..."
  08_memory:     33.0s - 38.0s   "It logs every attempt..."
  09_cta:        38.0s - 41.0s   "This is cadre-ai."
"""

import sys
import time

# ANSI colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def typed(text, delay=0.03):
    """Simulate typing effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def instant(text):
    print(text)


def pause(seconds):
    time.sleep(seconds)


def clear():
    print("\033[2J\033[H", end="")


def main():
    clear()

    # === HOOK: 0-5s ===
    instant(f"{DIM}weber@claude-code ~ ${RESET}")
    pause(0.5)
    typed(f"python3 adaptive-retry/retry_engine.py", delay=0.04)
    pause(0.8)
    instant("")
    instant(f"{BOLD}{WHITE}╔══════════════════════════════════════════════╗{RESET}")
    instant(f"{BOLD}{WHITE}║   ADAPTIVE RETRY ENGINE — Strategy Ladder    ║{RESET}")
    instant(f"{BOLD}{WHITE}╚══════════════════════════════════════════════╝{RESET}")
    instant("")
    instant(f"{RED}{BOLD}ERROR:{RESET} msbuild failed — CS0246: type 'ErrorCode' not found")
    pause(1.5)

    # === INTRO: 5-7s ===
    instant("")
    instant(f"{CYAN}Engaging retry ladder...{RESET}")
    pause(1.5)

    # === QUICK-FIX: 7-12s ===
    instant("")
    instant(f"{YELLOW}━━━ Strategy 1: QUICK-FIX (attempt 1/2) ━━━{RESET}")
    instant(f"{DIM}  → Fix the specific error. Minimal change.{RESET}")
    pause(1.2)
    instant(f"{DIM}  Adding missing using directive...{RESET}")
    pause(1.0)
    instant(f"{RED}  ✗ FAIL — CS0246: type 'ErrorCode' not found{RESET}")
    pause(0.5)

    instant("")
    instant(f"{YELLOW}━━━ Strategy 1: QUICK-FIX (attempt 2/2) ━━━{RESET}")
    instant(f"{DIM}  → Fix the specific error. Minimal change.{RESET}")
    pause(0.8)
    instant(f"{DIM}  Creating ErrorCode enum in namespace...{RESET}")
    pause(0.5)
    instant(f"{RED}  ✗ FAIL — CS0103: 'PipeRetryWrapper' does not exist{RESET}")
    pause(0.5)

    # === REFACTOR: 12-17s ===
    instant("")
    instant(f"{BLUE}━━━ Strategy 2: REFACTOR (attempt 1/1) ━━━{RESET}")
    instant(f"{DIM}  → Read more context. Refactor the approach.{RESET}")
    pause(1.0)
    instant(f"{DIM}  Reading 4 additional source files...{RESET}")
    pause(1.0)
    instant(f"{DIM}  Restructuring error handling pattern...{RESET}")
    pause(1.0)
    instant(f"{RED}  ✗ FAIL — CS0029: cannot convert 'ErrorResult' to 'string'{RESET}")
    pause(0.5)

    # === ALTERNATIVE: 17-22s ===
    instant("")
    instant(f"{MAGENTA}{BOLD}━━━ Strategy 3: ALTERNATIVE (attempt 1/1) ━━━{RESET}")
    instant(f"{DIM}  → Completely different approach.{RESET}")
    pause(1.0)
    instant(f"{DIM}  Bypassing custom error types...{RESET}")
    pause(0.8)
    instant(f"{DIM}  Using built-in Exception pattern with error codes...{RESET}")
    pause(1.0)
    instant(f"{DIM}  Building...{RESET}")
    pause(0.8)
    instant(f"{GREEN}{BOLD}  ✓ BUILD SUCCEEDED{RESET}")
    pause(0.8)

    # === RESULT: 22-28s (covering escalate explanation + result) ===
    instant("")
    instant(f"{GREEN}{'═' * 50}{RESET}")
    instant(f"{GREEN}{BOLD}  RESOLVED on strategy 'alternative' (attempt 4/5){RESET}")
    instant(f"{GREEN}{'═' * 50}{RESET}")
    instant("")
    instant(f"  {DIM}Retry Summary:{RESET}")
    instant(f"  {RED}[FAIL]{RESET} quick-fix  #1 — CS0246: type not found")
    instant(f"  {RED}[FAIL]{RESET} quick-fix  #2 — PipeRetryWrapper missing")
    instant(f"  {RED}[FAIL]{RESET} refactor   #3 — cannot convert ErrorResult")
    instant(f"  {GREEN}[ OK ]{RESET} alternative #4 — build succeeded")
    pause(3.0)

    # === MEMORY: 33-38s ===
    instant("")
    instant(f"{CYAN}Storing to memory...{RESET}")
    pause(0.8)
    instant(f"{DIM}  → \"refactor strategy failed for MSBuild CS0246,")
    instant(f"     alternative succeeded with built-in Exception pattern\"{RESET}")
    pause(1.0)
    instant("")
    instant(f"{CYAN}Next time this error occurs → skip to 'alternative'{RESET}")
    pause(2.5)

    # === CTA: 38-41s ===
    instant("")
    instant(f"{BOLD}{WHITE}github.com/WeberG619/cadre-ai{RESET}")
    pause(3.0)


if __name__ == "__main__":
    main()

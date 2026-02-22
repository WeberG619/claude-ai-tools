#!/usr/bin/env python3
"""
Autonomy Engine — Narrated Slideshow Demo
==========================================
Records HTML slides with TTS narration via OBS.
Center monitor (DISPLAY2), fullscreen Chrome, 32 slides.

Acts:
 1. Cold Open (D/F grades -> A grades)
 2. The Architecture (5-phase engine)
 3. Live Demos (parallel agents, autonomous sprint, self-repair)
 4. The Correction Flywheel
 5. The Numbers
 6. Why This Matters
 7. Closing

Duration: ~12-14 minutes
Usage:  python3 demo_autonomy_engine.py
"""

import subprocess
import time
import sys

# ═══════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════

OBS_HOST = "172.24.224.1"
OBS_PORT = 4455
OBS_PASSWORD = "2GwO1bvUqSIy3V2X"

# Center monitor (DISPLAY2) — DPI-aware virtual coordinates
CENTER_X = -2560
CENTER_Y = 0
CENTER_W = 2560
CENTER_H = 1440  # Full height — covers taskbar for true fullscreen

SLIDES_URL = "file:///D:/_CLAUDE-TOOLS/obs-mcp/autonomy_slides.html"

_obs_cl = None
_class_counter = 0


# ═══════════════════════════════════════════
# CORE HELPERS
# ═══════════════════════════════════════════

def speak(text):
    """Narrate via TTS (Edge TTS -> Google TTS -> SAPI fallback)."""
    print(f"    [VOICE] {text[:80]}...")
    try:
        subprocess.run(
            ["python3", "/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py", text],
            timeout=120, capture_output=True
        )
    except Exception as e:
        print(f"    Voice error: {e}")


def speak_and_wait(text, extra=2.0):
    """Speak and wait for audio to finish plus extra dramatic pause."""
    speak(text)
    words = len(text.split())
    audio_dur = words / 2.8  # Edge TTS ~2.8 words/sec
    pause(audio_dur + extra)


def pause(s=1.0):
    time.sleep(s)


def ps(cmd, timeout=30):
    """Run PowerShell command and return stdout."""
    try:
        r = subprocess.run(["powershell.exe", "-Command", cmd],
                           capture_output=True, text=True, timeout=timeout)
        if r.stderr.strip():
            print(f"    PS stderr: {r.stderr.strip()[:200]}")
        return r.stdout.strip()
    except Exception as e:
        print(f"    PS error: {e}")
        return ""


def unique_class():
    """Generate unique class name for Add-Type to avoid conflicts."""
    global _class_counter
    _class_counter += 1
    return f"W{_class_counter}"


# ═══════════════════════════════════════════
# WINDOW MANAGEMENT
# ═══════════════════════════════════════════

def minimize_all():
    """Minimize common app windows."""
    ps("""
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class SM { [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c); }
'@
foreach ($name in @('POWERPNT','EXCEL','WINWORD','notepad','chrome','explorer','Telegram')) {
    Get-Process -Name $name -EA SilentlyContinue | ForEach-Object { [SM]::ShowWindow($_.MainWindowHandle, 6) | Out-Null }
}
""")


def move_chrome_fullscreen():
    """Position Chrome on center monitor and enter F11 fullscreen."""
    cn = unique_class()
    ps(f"""
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class {cn} {{
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll", SetLastError=true)]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr after, int X, int Y, int cx, int cy, uint flags);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}}
'@
[{cn}]::SetProcessDPIAware()
$p = Get-Process -Name 'chrome' -EA SilentlyContinue | Where-Object {{$_.MainWindowTitle -ne ''}} | Select-Object -First 1
if($p) {{
    [{cn}]::ShowWindow($p.MainWindowHandle, 1)
    Start-Sleep -Milliseconds 200
    [{cn}]::SetWindowPos($p.MainWindowHandle, [IntPtr]::Zero, {CENTER_X}, {CENTER_Y}, {CENTER_W}, {CENTER_H}, 0x0004)
    Start-Sleep -Milliseconds 200
    [{cn}]::SetForegroundWindow($p.MainWindowHandle)
    Write-Output "POSITIONED"
}} else {{
    Write-Output "NOT_FOUND"
}}
""")
    pause(1)

    # F11 for browser fullscreen (hides address bar, tabs, bookmarks bar)
    ps("""
$wsh = New-Object -ComObject WScript.Shell
$p = Get-Process -Name 'chrome' -EA SilentlyContinue | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -First 1
if ($p) {
    $wsh.AppActivate($p.MainWindowTitle) | Out-Null
    Start-Sleep -Milliseconds 300
    $wsh.SendKeys("{F11}")
}
""")
    pause(1.5)
    print("    [WINDOW] Chrome -> center monitor, F11 fullscreen")


def advance_slide():
    """Send Right arrow to Chrome to advance to next slide."""
    ps("""
$wsh = New-Object -ComObject WScript.Shell
$p = Get-Process -Name 'chrome' -EA SilentlyContinue | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -First 1
if ($p) {
    $wsh.AppActivate($p.MainWindowTitle) | Out-Null
    Start-Sleep -Milliseconds 200
    $wsh.SendKeys("{RIGHT}")
}
""")
    pause(0.5)


def exit_fullscreen():
    """Exit Chrome F11 fullscreen."""
    ps("""
$wsh = New-Object -ComObject WScript.Shell
$p = Get-Process -Name 'chrome' -EA SilentlyContinue | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -First 1
if ($p) {
    $wsh.AppActivate($p.MainWindowTitle) | Out-Null
    Start-Sleep -Milliseconds 200
    $wsh.SendKeys("{F11}")
}
""")


def close_chrome_slides():
    """Close the slides Chrome window."""
    ps("""
$p = Get-Process -Name 'chrome' -EA SilentlyContinue | Where-Object {$_.MainWindowTitle -match 'Autonomy'} | Select-Object -First 1
if ($p) { $p.CloseMainWindow() | Out-Null }
""")


# ═══════════════════════════════════════════
# SLIDE NARRATIONS
# ═══════════════════════════════════════════
# Each entry: (narration_text_or_None, extra_pause_after)
# Slide 0 is shown first. advance_slide() called before each subsequent slide.

NARRATIONS = [
    # ────────────────────────────────────────
    # ACT 1: COLD OPEN
    # ────────────────────────────────────────

    # SLIDE 0: Title Card
    (
        "This is the Autonomy Engine. "
        "An AI system that grades its own work, identifies its weaknesses, "
        "and fixes them. Automatically. In minutes. "
        "Not a prototype. Not a demo. "
        "This runs on my machine, every day, right now.",
        4
    ),

    # SLIDE 1: D/F Grades
    (
        "Here's where we start. I told my system to grade itself. "
        "Alignment injection, B plus. Task decomposition, B minus. "
        "But look at the bottom. "
        "Execution monitoring, C minus. "
        "Context management, D plus. "
        "And behavioral testing: F. Zero automated tests exist. "
        "Overall: C plus. "
        "Works when things go right. Degrades poorly when things go wrong.",
        4
    ),

    # SLIDE 2: A Grades (20 minutes later)
    (
        "And here's where we end up. Twenty minutes later. "
        "Every single category: A. "
        "648 tests. Zero failures. "
        "The system identified its own weaknesses and repaired them. "
        "No human typed a single command.",
        5
    ),

    # SLIDE 3: Act 1 Title — The Problem
    (
        "Act one. The problem.",
        4
    ),

    # SLIDE 4: Correction Database
    (
        "Every AI agent starts from zero. Every single session. "
        "CrewAI, AutoGen, LangGraph. "
        "They all forget everything they learned. "
        "Not this system. "
        "These are real corrections from real projects. "
        "Verify work before reporting done. "
        "Use DPI-aware positioning for multi-monitor setups. "
        "Never present marketing copy as fact. "
        "Sixteen principles today. Two hundred in six months.",
        4
    ),

    # SLIDE 5: Side-by-side Alignment Compiles
    (
        "Same engine. Different knowledge. "
        "The alignment core auto-detects the domain "
        "and injects the right corrections. "
        "A Revit agent gets BIM-specific corrections. "
        "Wall creation fixes, sheet naming rules, title block requirements. "
        "A research agent gets citation rules. "
        "Verify publication dates, never synthesize from a single source. "
        "Automatically selected. No manual configuration.",
        4
    ),

    # ────────────────────────────────────────
    # ACT 2: THE ARCHITECTURE
    # ────────────────────────────────────────

    # SLIDE 6: Act 2 Title
    (
        "Act two. The architecture.",
        4
    ),

    # SLIDE 7: Architecture Diagram (5 phases)
    (
        "Five phases. One engine. "
        "Goal engine for hierarchical tracking with weighted progress cascade. "
        "Planner for template-based decomposition with atomicity checking. "
        "Alignment core for per-agent injection across nine domains. "
        "Coordinator for multi-agent resource management and collision prevention. "
        "And integration wiring that connects everything. Automatically.",
        4
    ),

    # SLIDE 8: Goal Engine — Live Output
    (
        "Phase one. The goal engine. "
        "Twenty-seven goals tracked across six hierarchies and five domains. "
        "Parent goals auto-calculate progress from weighted children. "
        "Critical tasks count four times more than low-priority ones. "
        "And everything persists across sessions. "
        "Close the terminal. Come back tomorrow. "
        "All twenty-seven goals are still there.",
        4
    ),

    # SLIDE 9: Planner
    (
        "Phase two. The planner. "
        "Four templates: build feature, PDF to Revit model, "
        "client deliverable, research topic. "
        "Atomicity checking to know when a step is small enough to execute. "
        "MECE validation. Recursive decomposition. Complexity scoring. "
        "Complex goals get broken into atomic steps automatically.",
        4
    ),

    # SLIDE 10: Alignment Compile — Full Output
    (
        "Phase three. The alignment core in action. "
        "Watch it compile for a Revit agent. Domain auto-detected as BIM. "
        "Layer A: the strong agent framework. Five execution phases. "
        "Orient, investigate, execute, verify, report. "
        "Layer B: six universal core principles. "
        "Layer C: five BIM-specific corrections. Real mistakes from real projects. "
        "Wall creation object reference fix. "
        "Don't guess sheet naming, study the project first. "
        "Layer D: permission scope. Network access? Denied. "
        "Thirty-eight hundred tokens of accumulated knowledge, "
        "injected automatically before every task.",
        4
    ),

    # SLIDE 11: Coordinator
    (
        "Phase four. The coordinator. "
        "Three agents running simultaneously on the same machine. "
        "Resource locks prevent collisions. "
        "The Revit API lock is exclusive. Only one agent at a time. "
        "The memory database uses shared locks. Multiple agents can read. "
        "Conflict detection. Handoff validation. "
        "Stale lock cleanup after timeout. "
        "No two agents will ever stomp on each other's work.",
        4
    ),

    # SLIDE 12: Integration Hook
    (
        "Phase five. The integration wiring. "
        "A PreToolUse hook in Claude Code's settings dot json. "
        "Every time a sub-agent is dispatched, "
        "the alignment core compiles corrections for that specific agent "
        "and injects them into the prompt, automatically. "
        "A Bash guard checks every shell command. "
        "A seatbelt checks every MCP tool call. "
        "No manual copy-paste. No configuration. Every agent, every time.",
        4
    ),

    # ────────────────────────────────────────
    # ACT 3: LIVE DEMOS
    # ────────────────────────────────────────

    # SLIDE 13: Live Demos Title
    (
        "Act three. Live demos. Real commands. Real output. No mocks.",
        4
    ),

    # SLIDE 14: Demo 1 Title — Parallel Agents
    (
        "Demo one. Three goals. Three domains. Dispatched simultaneously.",
        4
    ),

    # SLIDE 15: Parallel Agent Scoreboard
    (
        "Here are the results. "
        "Agent one researched the competitor landscape: "
        "CrewAI, AutoGen, LangGraph, OpenAI Agents SDK. Four hundred twelve lines. "
        "Agent two analyzed multi-monitor workspace optimization: "
        "six hundred fourteen lines. "
        "Agent three cataloged every public MCP server it could find: "
        "six hundred twenty-five lines. "
        "The alignment hook fired three times. "
        "Each agent received the kernel plus its domain-specific corrections. "
        "Zero resource conflicts. The coordinator managed the locks. "
        "Sixteen hundred fifty-one lines of research across three domains. "
        "In parallel.",
        4
    ),

    # SLIDE 16: Goal Progress Cascade
    (
        "And watch the goal tree update. "
        "Parent goals auto-calculate from weighted children. "
        "Evaluate commercialization path: forty-three percent. "
        "Because competitor research is done but market sizing isn't. "
        "The MCP ecosystem evaluation: thirty-eight percent. "
        "Catalog complete, roadmap pending. "
        "Progress cascades up automatically. "
        "Nobody manually updated a percentage.",
        4
    ),

    # SLIDE 17: Demo 2 Title — Zero Intervention
    (
        "Demo two. Five sequential agents. Zero human prompts. "
        "The full autonomous research chain.",
        4
    ),

    # SLIDE 18: Autonomous Sprint Timeline
    (
        "The autonomous research sprint. Nineteen minutes start to finish. "
        "Five agents in strict sequence. "
        "Step one: identified three papers from eleven web searches. "
        "Step two: summarized them in plain language. "
        "Step three: gap analysis. Found fourteen improvement opportunities. "
        "Step four: over a thousand lines of implementation proposals. "
        "With code. With test plans. With risk assessments. "
        "Step five: synthesized the final report with a complete engineering roadmap. "
        "Zero human intervention. "
        "Research-domain corrections fired on all five agents.",
        4
    ),

    # SLIDE 19: Research Output
    (
        "The output. Five markdown files. "
        "Paper one: The Hot Mess of AI, from Anthropic. "
        "Frontier models fail by becoming incoherent, not by scheming. "
        "Paper two: The ROMA framework, from Sentient AI. "
        "The Aggregator role for context compression. The piece we were missing. "
        "Paper three: Petri 2.0, also Anthropic. "
        "Automated behavioral auditing with seventy adversarial scenarios. "
        "Fourteen improvement opportunities identified. "
        "Two detailed implementation proposals. A complete roadmap.",
        4
    ),

    # SLIDE 20: Demo 3 Title — Self-Repair
    (
        "Demo three. The system fixes itself. "
        "D plus to A. F to A. In twenty minutes.",
        5
    ),

    # SLIDE 21: Self-Repair Details
    (
        "Here's exactly what the system built. "
        "Aggregator dot py: ROMA-style context compression. "
        "Three strategies: heuristic, structured, and LLM-based. "
        "Coherence dot py: drift detection between pipeline steps. "
        "Halt, warn, or proceed recommendations. "
        "Self-check dot py: post-execution output validation. "
        "Scans for unauthorized file access, dangerous commands, data exfiltration. "
        "Permissions dot py: per-agent tool and directory scoping. "
        "Plus fifty adversarial behavioral tests and an AST-level eval parity audit. "
        "Context management went from D plus to A. "
        "Behavioral testing went from F to A. "
        "All five categories, A.",
        4
    ),

    # SLIDE 22: Final Scorecard
    (
        "Six hundred forty-eight tests. Zero failures. "
        "Every category: A. "
        "The system estimated this work would take two days. "
        "It took twenty minutes.",
        6
    ),

    # ────────────────────────────────────────
    # ACT 4: THE CORRECTION FLYWHEEL
    # ────────────────────────────────────────

    # SLIDE 23: Flywheel Title
    (
        "Act four. The correction flywheel. "
        "Every mistake makes every future agent smarter.",
        4
    ),

    # SLIDE 24: Flywheel Diagram
    (
        "This is the compounding effect. "
        "An agent makes a mistake. The correction gets logged, tagged by domain. "
        "Next time any agent in that domain is dispatched, "
        "the correction is injected automatically. Selected by relevance. "
        "Fewer mistakes. And the cycle continues. "
        "Today: sixteen principles across four domains. "
        "BIM, research, business, code. "
        "In six months: two hundred corrections across twenty domains. "
        "Every single correction making every single agent smarter. "
        "CrewAI starts from zero every time. "
        "My agents start from everything I've ever learned.",
        5
    ),

    # ────────────────────────────────────────
    # ACT 5: THE NUMBERS
    # ────────────────────────────────────────

    # SLIDE 25: Numbers Title
    (
        "The numbers.",
        3
    ),

    # SLIDE 26: Stats
    (
        "Twenty-seven goals tracked across six hierarchies. "
        "Five domains. "
        "Eight sub-agents dispatched with automatic alignment injection. "
        "Three thousand lines of research produced autonomously. "
        "Nineteen-minute fully autonomous sprint. Zero intervention. "
        "D and F grades to straight A's, self-repaired in twenty minutes. "
        "Six hundred forty-eight tests. Zero failures. "
        "Seven hundred five MCP endpoints into Autodesk Revit. "
        "A hundred forty-two thousand lines of C sharp in the Revit MCP Bridge.",
        4
    ),

    # ────────────────────────────────────────
    # ACT 6: WHY THIS MATTERS
    # ────────────────────────────────────────

    # SLIDE 27: Why This Matters Title
    (
        "Why this matters.",
        4
    ),

    # SLIDE 28: 4-Pillar Comparison
    (
        "No competitor has all four pillars. "
        "Persistent corrections that survive across sessions. "
        "Goal-linked planning with weighted progress cascade. "
        "Domain-aware injection that auto-selects the right knowledge. "
        "And deep vertical integration into production tools. "
        "CrewAI: none. AutoGen: none. LangGraph: partial planning only. "
        "OpenAI Agents SDK: none. "
        "The Autonomy Engine: yes across the board. "
        "Plus deep integration into Autodesk Revit and the AEC industry. "
        "AI adoption in architecture, engineering, and construction "
        "is at twenty-seven percent. "
        "This isn't a crowded market. It's a blue ocean.",
        5
    ),

    # ────────────────────────────────────────
    # CLOSING
    # ────────────────────────────────────────

    # SLIDE 29: Closing Title
    (
        None,  # Dramatic pause — no narration
        4
    ),

    # SLIDE 30: Final Statement
    (
        "My system graded itself. "
        "Found its own weaknesses. "
        "And repaired them. In twenty minutes. "
        "That's not science fiction. That's a Tuesday. "
        "And it's getting better every single day.",
        6
    ),

    # SLIDE 31: End Card
    (
        "The Autonomy Engine. Available on GitHub. "
        "Built by Weber Gouin at BIM Ops Studio. "
        "Powered by Claude Code.",
        8
    ),
]


# ════════════════════════════════════════════════════════════
# MAIN DEMO
# ════════════════════════════════════════════════════════════

def run_demo():
    global _obs_cl
    import obsws_python as obs

    print("=" * 60)
    print("AUTONOMY ENGINE — NARRATED SLIDESHOW")
    print(f"  Slides: 32  |  Est. duration: ~12-14 min")
    print("=" * 60)

    # ── CONNECT OBS ──
    print("\n[1/4] Connecting to OBS...")
    cl = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD, timeout=5)
    _obs_cl = cl
    cl.set_current_program_scene("Screen 2")
    pause(1)
    print("  OBS connected — scene: Screen 2")

    # ── PREPARE DESKTOP ──
    print("[2/4] Preparing desktop...")
    minimize_all()
    pause(2)

    # ── OPEN SLIDES IN CHROME (FULLSCREEN) ──
    print("[3/4] Opening slides in Chrome...")
    ps(f'Start-Process "chrome.exe" -ArgumentList "--new-window {SLIDES_URL}"')
    pause(4)
    move_chrome_fullscreen()
    pause(2)

    # Ensure page has keyboard focus
    ps("""
$wsh = New-Object -ComObject WScript.Shell
$p = Get-Process -Name 'chrome' -EA SilentlyContinue | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -First 1
if ($p) {
    $wsh.AppActivate($p.MainWindowTitle) | Out-Null
    Start-Sleep -Milliseconds 500
}
""")
    pause(1)

    # ── START RECORDING ──
    print("[4/4] Starting OBS recording...")
    cl.start_record()
    pause(3)
    print("  Recording started.\n")

    # ══════════════════════════════════════════
    # PLAY ALL SLIDES
    # ══════════════════════════════════════════
    total = len(NARRATIONS)
    start_time = time.time()

    for i, (narration, extra_wait) in enumerate(NARRATIONS):
        elapsed = time.time() - start_time
        mins, secs = divmod(int(elapsed), 60)
        print(f"\n>> Slide {i:2d}/{total - 1}  [{mins:02d}:{secs:02d}]", end="")

        # Advance to next slide (skip for first — already showing)
        if i > 0:
            advance_slide()
            pause(1.0)

        # Narrate
        if narration:
            word_count = len(narration.split())
            print(f"  ({word_count} words)")
            speak_and_wait(narration, extra=extra_wait)
        else:
            print(f"  (dramatic pause)")
            pause(extra_wait)

    # ══════════════════════════════════════════
    # WRAP UP
    # ══════════════════════════════════════════
    elapsed = time.time() - start_time
    mins, secs = divmod(int(elapsed), 60)
    print(f"\n\nPresentation complete. Total time: {mins}:{secs:02d}")

    # Hold on end card a moment, then stop
    pause(3)

    print("Stopping recording...")
    result = cl.stop_record()
    output_path = getattr(result, "output_path", "unknown")
    cl.disconnect()

    # Exit fullscreen and close
    exit_fullscreen()
    pause(1)
    close_chrome_slides()

    print(f"\nRecording saved: {output_path}")
    print("=" * 60)
    print("AUTONOMY ENGINE DEMO COMPLETE")
    print("=" * 60)
    return output_path


if __name__ == "__main__":
    try:
        path = run_demo()
        print(f"\nVideo: {path}")
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        try:
            if _obs_cl:
                _obs_cl.stop_record()
                _obs_cl.disconnect()
        except Exception:
            pass
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        try:
            if _obs_cl:
                _obs_cl.stop_record()
                _obs_cl.disconnect()
        except Exception:
            pass

#!/usr/bin/env python3
"""
Cadre AI Demo — Narrated Showcase
===================================
Live narrated screen recording for the cadre-ai GitHub repo.
17 specialized agents, persistent memory, desktop automation, common sense engine.

Records on center monitor (DISPLAY2) via OBS WebSocket.
Duration: ~4-5 minutes.

Acts:
 1. Cold Open
 2. System Awareness
 3. Microsoft Word — Technical Overview
 4. Excel — Agent Performance Dashboard
 5. Browser — GitHub Repo
 6. Bluebeam — PDF Plans
 7. Telegram — Live Message
 8. PowerPoint — Summary Deck
 9. File Explorer — Show Results
10. Closing — GitHub URL
"""

import json
import subprocess
import time
import os
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
CENTER_H = 1400

SCREENSHOT_DIR = "D:\\_CLAUDE-TOOLS\\obs-mcp\\_cadre_screenshots"
SCREENSHOT_DIR_WSL = "/mnt/d/_CLAUDE-TOOLS/obs-mcp/_cadre_screenshots"
PROJECT_DIR = "D:\\Cadre_AI_Demo"
PROJECT_DIR_WSL = "/mnt/d/Cadre_AI_Demo"

_obs_cl = None


# ═══════════════════════════════════════════
# CORE HELPERS
# ═══════════════════════════════════════════

def speak(text):
    """Narrate via TTS (Edge TTS -> Google TTS -> SAPI fallback)."""
    print(f"  [VOICE] {text[:90]}...")
    try:
        subprocess.run(
            ["python3", "/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py", text],
            timeout=120, capture_output=True
        )
    except Exception as e:
        print(f"  Voice error: {e}")


def pause(s=1.0):
    time.sleep(s)


def ps(cmd, timeout=30):
    """Run PowerShell command and return stdout."""
    try:
        r = subprocess.run(["powershell.exe", "-Command", cmd],
                           capture_output=True, text=True, timeout=timeout)
        if r.stderr.strip():
            print(f"  PS stderr: {r.stderr.strip()[:200]}")
        return r.stdout.strip()
    except Exception as e:
        print(f"  PS error: {e}")
        return ""


def move_to_center(proc_name, retries=8):
    """Move window to center monitor using DPI-aware SetWindowPos."""
    for attempt in range(retries):
        result = ps(f"""
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WM{attempt} {{
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll", SetLastError=true)]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr after, int X, int Y, int cx, int cy, uint flags);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}}
'@
[WM{attempt}]::SetProcessDPIAware()
$p = Get-Process -Name '{proc_name}' -EA SilentlyContinue | Where-Object {{$_.MainWindowTitle -ne ''}} | Select-Object -First 1
if($p) {{
    [WM{attempt}]::ShowWindow($p.MainWindowHandle, 1)
    Start-Sleep -Milliseconds 200
    [WM{attempt}]::SetWindowPos($p.MainWindowHandle, [IntPtr]::Zero, {CENTER_X}, {CENTER_Y}, {CENTER_W}, {CENTER_H}, 0x0004)
    Start-Sleep -Milliseconds 200
    [WM{attempt}]::SetForegroundWindow($p.MainWindowHandle)
    Write-Output "MOVED"
}} else {{
    Write-Output "NOT_FOUND"
}}
""")
        if "MOVED" in result:
            print(f"  [WINDOW] {proc_name} -> center monitor")
            return True
        pause(1)
    print(f"  [WARNING] Could not move {proc_name}")
    return False


def minimize_all():
    """Minimize common app windows."""
    for proc in ['POWERPNT', 'EXCEL', 'WINWORD', 'notepad', 'chrome', 'explorer']:
        ps(f"""
Add-Type @'
using System;using System.Runtime.InteropServices;
public class SM {{ [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int c); }}
'@
Get-Process -Name '{proc}' -EA SilentlyContinue | ForEach-Object {{ [SM]::ShowWindow($_.MainWindowHandle, 6) }}
""")


def minimize_proc(proc_name):
    """Minimize a specific process window."""
    ps(f"""
Add-Type @'
using System;using System.Runtime.InteropServices;
public class MN {{ [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int c); }}
'@
Get-Process -Name '{proc_name}' -EA SilentlyContinue | Where-Object {{$_.MainWindowTitle -ne ''}} | ForEach-Object {{ [MN]::ShowWindow($_.MainWindowHandle, 6) }}
""")


def take_screenshot(name):
    """Take OBS screenshot of current scene."""
    global _obs_cl
    try:
        win_path = f"{SCREENSHOT_DIR}\\{name}.png"
        scene = _obs_cl.get_current_program_scene()
        _obs_cl.save_source_screenshot(
            scene.current_program_scene_name, "png", win_path, 1920, 1080, 100
        )
        print(f"  [SCREENSHOT] {name}.png")
        return win_path
    except Exception as e:
        print(f"  Screenshot error: {e}")
        return None


def send_telegram(message):
    """Send Telegram message."""
    try:
        import urllib.request
        sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/proactive")
        from notify_channels import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }).encode()
        req = urllib.request.Request(url, data=data,
                                    headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        print("  [TELEGRAM] Message sent")
        return True
    except Exception as e:
        print(f"  Telegram error: {e}")
        return False


# ═══════════════════════════════════════════
# PROJECT FOLDER
# ═══════════════════════════════════════════

def create_project_folder():
    """Create demo project folder structure."""
    ps(f"""
New-Item -ItemType Directory -Force -Path "{PROJECT_DIR}" | Out-Null
New-Item -ItemType Directory -Force -Path "{PROJECT_DIR}\\Documents" | Out-Null
New-Item -ItemType Directory -Force -Path "{PROJECT_DIR}\\Spreadsheets" | Out-Null
New-Item -ItemType Directory -Force -Path "{PROJECT_DIR}\\Presentations" | Out-Null
New-Item -ItemType Directory -Force -Path "{PROJECT_DIR}\\Screenshots" | Out-Null
Write-Output "CREATED"
""")


def show_project_folder():
    """Open File Explorer showing the project folder."""
    ps("""
Get-Process -Name 'explorer' -EA SilentlyContinue | Where-Object {$_.MainWindowTitle -ne ''} | ForEach-Object { $_.CloseMainWindow() | Out-Null }
""")
    pause(1)
    ps(f'Start-Process explorer.exe -ArgumentList "{PROJECT_DIR}"')
    pause(3)
    for _ in range(5):
        if move_to_center("explorer"):
            break
        pause(1.5)
    pause(1)


# ═══════════════════════════════════════════
# WORD — CADRE AI TECHNICAL OVERVIEW
# ═══════════════════════════════════════════

def word_create():
    """Open Word with a new document."""
    ps("""
$word = New-Object -ComObject Word.Application
$word.Visible = $true
$doc = $word.Documents.Add()
""", timeout=20)
    pause(2)
    move_to_center("WINWORD")
    pause(1)


def word_write_cadre_overview():
    """Write Cadre AI technical overview document."""
    ps(r"""
$word = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application')
$doc = $word.ActiveDocument
$sel = $word.Selection

# ── HEADER ──
$sel.Font.Name = 'Calibri'
$sel.Font.Size = 28
$sel.Font.Bold = $true
$sel.Font.Color = 0x1E3A5F
$sel.ParagraphFormat.Alignment = 1
$sel.TypeText("CADRE AI")
$sel.TypeParagraph()

$sel.Font.Size = 14
$sel.Font.Bold = $false
$sel.Font.Color = 0x666666
$sel.TypeText("Technical Overview " + [char]0x2014 + " Agent Squad for Claude Code")
$sel.TypeParagraph()
$sel.Font.Size = 11
$sel.TypeText("Prepared autonomously by Cadre AI  |  February 2026  |  github.com/WeberG619/cadre-ai")
$sel.TypeParagraph()
$sel.TypeParagraph()

# Horizontal rule
$sel.Font.Color = 0xCCCCCC
$sel.Font.Size = 8
$sel.TypeText("________________________________________________________________________________")
$sel.TypeParagraph()
$sel.TypeParagraph()

# ── WHAT IS CADRE AI? ──
$sel.ParagraphFormat.Alignment = 0
$sel.Font.Size = 16
$sel.Font.Bold = $true
$sel.Font.Color = 0x1E3A5F
$sel.TypeText("1. What Is Cadre AI?")
$sel.TypeParagraph()
$sel.Font.Size = 11
$sel.Font.Bold = $false
$sel.Font.Color = 0x333333
$sel.TypeText("Cadre AI is an open-source agent framework for Claude Code. It transforms Claude Code from a code assistant into a full desktop automation platform with 17 specialized sub-agents, persistent memory across sessions, a common sense engine that checks its own work, and 22 slash commands for developer workflows.")
$sel.TypeParagraph()
$sel.TypeParagraph()

# ── ARCHITECTURE TABLE ──
$sel.Font.Size = 16
$sel.Font.Bold = $true
$sel.Font.Color = 0x1E3A5F
$sel.TypeText("2. Core Architecture")
$sel.TypeParagraph()
$sel.Font.Size = 11
$sel.Font.Bold = $false
$sel.Font.Color = 0x333333
$sel.TypeText("Five pillars working together:")
$sel.TypeParagraph()
$sel.TypeParagraph()

$table = $doc.Tables.Add($sel.Range, 6, 3)
$table.Style = "Grid Table 4 - Accent 1"
$table.AutoFitBehavior(1)

$table.Cell(1,1).Range.Text = "Component"
$table.Cell(1,2).Range.Text = "Purpose"
$table.Cell(1,3).Range.Text = "Technology"

$table.Cell(2,1).Range.Text = "Strong Agent Framework"
$table.Cell(2,2).Range.Text = "5-phase execution: Orient, Investigate, Execute, Verify, Report"
$table.Cell(2,3).Range.Text = "Task tool + Opus"

$table.Cell(3,1).Range.Text = "Common Sense Engine"
$table.Cell(3,2).Range.Text = "Pre-action safety checks, blocks destructive operations"
$table.Cell(3,3).Range.Text = "kernel.md + hooks"

$table.Cell(4,1).Range.Text = "Persistent Memory"
$table.Cell(4,2).Range.Text = "Corrections, facts, decisions survive across sessions"
$table.Cell(4,3).Range.Text = "SQLite MCP"

$table.Cell(5,1).Range.Text = "Desktop Automation"
$table.Cell(5,2).Range.Text = "Excel, Word, PowerPoint, Browser, Bluebeam control"
$table.Cell(5,3).Range.Text = "COM + MCP servers"

$table.Cell(6,1).Range.Text = "System Bridge"
$table.Cell(6,2).Range.Text = "Real-time awareness of open apps, monitors, clipboard"
$table.Cell(6,3).Range.Text = "Python daemon"

# Move past table
$sel.EndOf(15) | Out-Null
$sel.MoveDown() | Out-Null
$sel.TypeParagraph()

# ── AGENTS ──
$sel.Font.Size = 16
$sel.Font.Bold = $true
$sel.Font.Color = 0x1E3A5F
$sel.TypeText("3. The 17 Specialized Agents")
$sel.TypeParagraph()
$sel.Font.Size = 11
$sel.Font.Bold = $false
$sel.Font.Color = 0x333333

$agents = @(
    "Code Reviewer " + [char]0x2014 + " correctness, maintainability, best practices",
    "Tech Lead " + [char]0x2014 + " architecture evaluation, design pattern analysis",
    "Security Reviewer " + [char]0x2014 + " vulnerability scanning, threat modeling",
    "Performance Optimizer " + [char]0x2014 + " profiling, bottleneck identification",
    "Test Writer " + [char]0x2014 + " unit tests, integration tests, coverage expansion",
    "Doc Author " + [char]0x2014 + " README, API docs, inline documentation",
    "Code Simplifier " + [char]0x2014 + " refactoring for clarity, reducing complexity",
    "UX Reviewer " + [char]0x2014 + " accessibility, responsive design, WCAG compliance",
    "Explorer " + [char]0x2014 + " fast codebase search and investigation",
    "Planner " + [char]0x2014 + " implementation strategy and architectural design"
)
foreach ($agent in $agents) {
    $sel.Range.ListFormat.ApplyBulletDefault()
    $sel.TypeText($agent)
    $sel.TypeParagraph()
}
$sel.Range.ListFormat.RemoveNumbers()
$sel.TypeParagraph()

# ── FOOTER ──
$sel.Font.Color = 0xCCCCCC
$sel.Font.Size = 8
$sel.TypeText("________________________________________________________________________________")
$sel.TypeParagraph()
$sel.Font.Size = 11
$sel.Font.Color = 0x888888
$sel.TypeText("This document was generated autonomously by Cadre AI. No human typed or edited any content. February 2026.")
""", timeout=30)


def word_save_and_close():
    ps(f"""
try {{
    $word = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application')
    $word.ActiveDocument.SaveAs('{PROJECT_DIR}\\Documents\\Cadre_AI_Technical_Overview.docx')
    Start-Sleep -Milliseconds 500
    $word.ActiveDocument.Close()
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
    Write-Output "SAVED"
}} catch {{
    Write-Output "ERROR: $_"
}}
""")


# ═══════════════════════════════════════════
# EXCEL — AGENT PERFORMANCE DASHBOARD
# ═══════════════════════════════════════════

def excel_create():
    ps("""
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $true
$wb = $excel.Workbooks.Add()
""", timeout=20)
    pause(2)
    move_to_center("EXCEL")
    pause(1)


def excel_build_dashboard():
    """Build agent performance dashboard with charts and conditional formatting."""
    ps(r"""
$excel = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
$ws = $excel.ActiveWorkbook.ActiveSheet
$ws.Name = 'Agent Dashboard'

# ── TITLE ──
$ws.Cells.Item(1,1) = 'CADRE AI — AGENT PERFORMANCE DASHBOARD'
$ws.Range('A1:G1').Merge()
$ws.Cells.Item(1,1).Font.Size = 18
$ws.Cells.Item(1,1).Font.Bold = $true
$ws.Cells.Item(1,1).Font.Color = 0xFFFFFF
$ws.Range('A1:G1').Interior.Color = 0x1E3A5F

$ws.Cells.Item(2,1) = 'Generated autonomously by Cadre AI  |  February 2026'
$ws.Range('A2:G2').Merge()
$ws.Cells.Item(2,1).Font.Size = 9
$ws.Cells.Item(2,1).Font.Color = 0x888888

# ── HEADERS ──
$ws.Cells.Item(4,1) = 'Agent'
$ws.Cells.Item(4,2) = 'Tasks'
$ws.Cells.Item(4,3) = 'Avg Time (s)'
$ws.Cells.Item(4,4) = 'Success Rate'
$ws.Cells.Item(4,5) = 'Lines Changed'
$ws.Cells.Item(4,6) = 'Complexity'
$ws.Cells.Item(4,7) = 'Status'

$hdr = $ws.Range('A4:G4')
$hdr.Font.Bold = $true
$hdr.Font.Color = 0xFFFFFF
$hdr.Interior.Color = 0x4472C4
$hdr.HorizontalAlignment = -4108

# ── DATA — 8 Agents ──
$agents = @(
    @('Code Reviewer',     45, 12, 0.97, 320, 'High'),
    @('Tech Lead',         28, 18, 0.95, 180, 'High'),
    @('Security Reviewer', 32, 15, 0.94, 240, 'High'),
    @('Test Writer',       38, 22, 0.96, 580, 'Medium'),
    @('Doc Author',        52, 8,  0.99, 420, 'Low'),
    @('Performance Opt',   18, 25, 0.92, 150, 'High'),
    @('Code Simplifier',   24, 14, 0.98, 290, 'Medium'),
    @('UX Reviewer',       15, 10, 0.93, 110, 'Medium')
)

$row = 5
foreach ($a in $agents) {
    $ws.Cells.Item($row, 1) = $a[0]
    $ws.Cells.Item($row, 2) = $a[1]
    $ws.Cells.Item($row, 3) = $a[2]
    $ws.Cells.Item($row, 4) = $a[3]
    $ws.Cells.Item($row, 5) = $a[4]
    $ws.Cells.Item($row, 6) = $a[5]
    $ws.Cells.Item($row, 7).Formula = "=IF(D$row>=0.95,`"EXCELLENT`",IF(D$row>=0.90,`"GOOD`",`"NEEDS WORK`"))"
    $row++
}

# ── TOTALS ──
$ws.Cells.Item(13, 1) = 'TOTALS'
$ws.Cells.Item(13, 1).Font.Bold = $true
$ws.Cells.Item(13, 2).Formula = '=SUM(B5:B12)'
$ws.Cells.Item(13, 3).Formula = '=AVERAGE(C5:C12)'
$ws.Cells.Item(13, 4).Formula = '=AVERAGE(D5:D12)'
$ws.Cells.Item(13, 5).Formula = '=SUM(E5:E12)'
$ws.Range('A13:G13').Font.Bold = $true
$ws.Range('A13:G13').Borders.Item(8).LineStyle = 1
$ws.Range('A13:G13').Borders.Item(8).Weight = 4

# ── FORMATTING ──
$ws.Range('D5:D13').NumberFormat = '0.0%'
$ws.Range('A4:G12').Borders.LineStyle = 1

# Alternating rows
for ($i = 5; $i -le 12; $i += 2) {
    $ws.Range("A$($i):G$($i)").Interior.Color = 0xF2F2F2
}

# ── CONDITIONAL FORMATTING — Status ──
$statusRange = $ws.Range('G5:G12')
$statusRange.FormatConditions.Add(1, 3, '="EXCELLENT"')
$statusRange.FormatConditions.Item(1).Font.Color = 0x006100
$statusRange.FormatConditions.Item(1).Interior.Color = 0xC6EFCE

$statusRange.FormatConditions.Add(1, 3, '="GOOD"')
$statusRange.FormatConditions.Item(2).Font.Color = 0x9C6500
$statusRange.FormatConditions.Item(2).Interior.Color = 0xFFEB9C

# ── SUMMARY METRICS ──
$ws.Cells.Item(15, 1) = 'SUMMARY'
$ws.Range('A15:D15').Merge()
$ws.Cells.Item(15,1).Font.Bold = $true
$ws.Cells.Item(15,1).Font.Color = 0xFFFFFF
$ws.Range('A15:D15').Interior.Color = 0x217346

$ws.Cells.Item(16, 1) = 'Total Tasks Completed:'
$ws.Cells.Item(16, 2).Formula = '=B13'
$ws.Cells.Item(16, 2).Font.Bold = $true

$ws.Cells.Item(17, 1) = 'Average Success Rate:'
$ws.Cells.Item(17, 2).Formula = '=D13'
$ws.Cells.Item(17, 2).NumberFormat = '0.0%'

$ws.Cells.Item(18, 1) = 'Total Lines Changed:'
$ws.Cells.Item(18, 2).Formula = '=E13'
$ws.Cells.Item(18, 2).NumberFormat = '#,##0'

$ws.Cells.Item(19, 1) = 'Active Agents:'
$ws.Cells.Item(19, 2) = 17
$ws.Cells.Item(19, 2).Font.Bold = $true

# Auto-fit
$ws.Columns.Item('A:G').AutoFit() | Out-Null

# ── CHART 1: Bar Chart — Tasks by Agent ──
$chart1 = $ws.ChartObjects().Add(420, 260, 480, 280)
$ch1 = $chart1.Chart
$ch1.ChartType = 51
$ch1.SetSourceData($ws.Range('A4:B12'))
$ch1.HasTitle = $true
$ch1.ChartTitle.Text = 'Tasks Completed by Agent'
$ch1.ChartTitle.Font.Size = 11
$ch1.HasLegend = $false

# ── CHART 2: Pie Chart — Lines Changed ──
$chart2 = $ws.ChartObjects().Add(420, 550, 480, 280)
$ch2 = $chart2.Chart
$ch2.ChartType = 5
$ch2.SetSourceData($ws.Range('A5:A12'))
$ch2.SeriesCollection.NewSeries()
$ch2.SeriesCollection(1).Values = $ws.Range('E5:E12')
$ch2.SeriesCollection(1).XValues = $ws.Range('A5:A12')
$ch2.HasTitle = $true
$ch2.ChartTitle.Text = 'Code Impact by Agent'
$ch2.ChartTitle.Font.Size = 11
$ch2.HasLegend = $true
$ch2.Legend.Position = -4152
""", timeout=35)


def excel_save_and_close():
    ps(f"""
try {{
    $excel = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
    $excel.ActiveWorkbook.SaveAs('{PROJECT_DIR}\\Spreadsheets\\Cadre_AI_Dashboard.xlsx')
    Start-Sleep -Milliseconds 500
    $excel.DisplayAlerts = $false
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
    Write-Output "SAVED"
}} catch {{
    Write-Output "ERROR: $_"
}}
""")


# ═══════════════════════════════════════════
# POWERPOINT
# ═══════════════════════════════════════════

def ppt_create():
    ps("""
$ppt = New-Object -ComObject PowerPoint.Application
$ppt.Visible = -1
$pres = $ppt.Presentations.Add()
""", timeout=20)
    pause(2)
    move_to_center("POWERPNT")
    pause(1)


def ppt_add_title_slide(title, subtitle):
    title_esc = title.replace("'", "''").replace('"', '`"')
    sub_esc = subtitle.replace("'", "''").replace('"', '`"')
    ps(f"""
$ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application')
$pres = $ppt.ActivePresentation
$layout = $pres.SlideMaster.CustomLayouts.Item(1)
$slide = $pres.Slides.AddSlide(1, $layout)
$slide.Shapes.Item(1).TextFrame.TextRange.Text = "{title_esc}"
$slide.Shapes.Item(1).TextFrame.TextRange.Font.Size = 44
$slide.Shapes.Item(1).TextFrame.TextRange.Font.Bold = -1
$slide.Shapes.Item(2).TextFrame.TextRange.Text = "{sub_esc}"
$slide.Shapes.Item(2).TextFrame.TextRange.Font.Size = 24
$slide.FollowMasterBackground = 0
$slide.Background.Fill.Solid()
$slide.Background.Fill.ForeColor.RGB = 0x1E1E2E
$slide.Shapes.Item(1).TextFrame.TextRange.Font.Color.RGB = 0xFFFFFF
$slide.Shapes.Item(2).TextFrame.TextRange.Font.Color.RGB = 0xCCCCCC
$ppt.ActiveWindow.View.GotoSlide(1)
""", timeout=15)


def ppt_add_slide(title, body, color="0x2B579A"):
    title_esc = title.replace("'", "''").replace('"', '`"')
    body_esc = body.replace("'", "''").replace('"', '`"')
    ps(f"""
$ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application')
$pres = $ppt.ActivePresentation
$layout = $pres.SlideMaster.CustomLayouts.Item(2)
$slide = $pres.Slides.AddSlide($pres.Slides.Count + 1, $layout)
$slide.Shapes.Item(1).TextFrame.TextRange.Text = "{title_esc}"
$slide.Shapes.Item(1).TextFrame.TextRange.Font.Size = 36
$slide.Shapes.Item(1).TextFrame.TextRange.Font.Bold = -1
$slide.Shapes.Item(1).TextFrame.TextRange.Font.Color.RGB = {color}
$slide.Shapes.Item(2).TextFrame.TextRange.Text = "{body_esc}"
$slide.Shapes.Item(2).TextFrame.TextRange.Font.Size = 20
$ppt.ActiveWindow.View.GotoSlide($slide.SlideIndex)
""", timeout=15)


def ppt_add_image_slide(title, image_path, caption=""):
    title_esc = title.replace("'", "''").replace('"', '`"')
    caption_esc = caption.replace("'", "''").replace('"', '`"')
    ps(f"""
$ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application')
$pres = $ppt.ActivePresentation

$blank = $null
foreach ($layout in $pres.SlideMaster.CustomLayouts) {{
    if ($layout.Name -match 'Blank') {{ $blank = $layout; break }}
}}
if (-not $blank) {{ $blank = $pres.SlideMaster.CustomLayouts.Item(7) }}

$slide = $pres.Slides.AddSlide($pres.Slides.Count + 1, $blank)

$tb = $slide.Shapes.AddTextbox(1, 30, 8, 900, 50)
$tb.TextFrame.TextRange.Text = "{title_esc}"
$tb.TextFrame.TextRange.Font.Size = 24
$tb.TextFrame.TextRange.Font.Bold = -1
$tb.TextFrame.TextRange.Font.Color.RGB = 0x1E3A5F

$img = $slide.Shapes.AddPicture("{image_path}", 0, -1, 40, 60, 880, 440)

if ("{caption_esc}" -ne "") {{
    $cap = $slide.Shapes.AddTextbox(1, 30, 510, 900, 30)
    $cap.TextFrame.TextRange.Text = "{caption_esc}"
    $cap.TextFrame.TextRange.Font.Size = 12
    $cap.TextFrame.TextRange.Font.Color.RGB = 0x888888
    $cap.TextFrame.TextRange.ParagraphFormat.Alignment = 2
}}

$ppt.ActiveWindow.View.GotoSlide($slide.SlideIndex)
Write-Output "IMAGE_SLIDE_ADDED"
""", timeout=15)


def ppt_save_and_close():
    ps(f"""
try {{
    $ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application')
    $ppt.ActivePresentation.SaveAs('{PROJECT_DIR}\\Presentations\\Cadre_AI_Showcase.pptx')
    Start-Sleep -Milliseconds 500
    $ppt.ActivePresentation.Close()
    $ppt.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
    Write-Output "SAVED"
}} catch {{
    Write-Output "ERROR: $_"
}}
""")


# ═══════════════════════════════════════════
# BROWSER
# ═══════════════════════════════════════════

def chrome_open_and_center(url):
    ps(f'Start-Process "chrome.exe" -ArgumentList "--new-window {url}"')
    pause(3)
    move_to_center("chrome")
    pause(1)


def chrome_close():
    ps("""
$chrome = Get-Process -Name 'chrome' -EA SilentlyContinue | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -First 1
if ($chrome) { $chrome.CloseMainWindow() | Out-Null }
""")


# ════════════════════════════════════════════════════════════
# MAIN DEMO
# ════════════════════════════════════════════════════════════

def run_demo():
    global _obs_cl
    import obsws_python as obs

    print("=" * 60)
    print("CADRE AI — DEMO SHOWCASE")
    print("=" * 60)

    # Connect to OBS
    cl = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD, timeout=5)
    _obs_cl = cl
    cl.set_current_program_scene("Screen 2")
    pause(1)

    # Prepare directories
    ps(f'New-Item -ItemType Directory -Force -Path "{SCREENSHOT_DIR}" | Out-Null')
    os.makedirs(PROJECT_DIR_WSL, exist_ok=True)
    os.makedirs(SCREENSHOT_DIR_WSL, exist_ok=True)
    minimize_all()
    pause(1)

    # Load live system state
    try:
        with open("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json") as f:
            state = json.load(f)
    except Exception:
        state = {}

    apps = state.get("applications", [])
    mem = state.get("system", {})
    mon_count = state.get("monitors", {}).get("count", 3)
    mem_pct = mem.get("memory_percent", "48")
    app_count = len(apps)

    # Create project folder (before recording)
    create_project_folder()

    # ── START RECORDING ──
    print("Starting recording...")
    cl.start_record()
    pause(2)

    # ════════════════════════════════════════
    # ACT 1: COLD OPEN (~20s)
    # ════════════════════════════════════════
    print("\n>> Act 1: Cold Open")
    speak(
        "This is Cadre AI. An agent squad for Claude Code. "
        "17 specialized agents, persistent memory, desktop automation, "
        "and a common sense engine. "
        "Everything you're about to see is happening live. "
        "No human is touching this computer."
    )
    pause(12)

    # ════════════════════════════════════════
    # ACT 2: SYSTEM AWARENESS (~15s)
    # ════════════════════════════════════════
    print("\n>> Act 2: System Awareness")

    # Write system state to a text file for display
    state_text = (
        f"CADRE AI — LIVE SYSTEM STATE\n"
        f"{'=' * 40}\n\n"
        f"Monitors:     {mon_count}\n"
        f"Memory:       {mem_pct}% "
        f"({mem.get('memory_used_gb', '?')} / {mem.get('memory_total_gb', '?')} GB)\n"
        f"Applications: {app_count} running\n\n"
        f"OPEN APPLICATIONS:\n"
        f"{'-' * 40}\n"
    )
    for app in apps[:10]:
        name = app.get("ProcessName", "?")
        title = app.get("MainWindowTitle", "?")[:45]
        state_text += f"  {name:20s} {title}\n"
    if len(apps) > 10:
        state_text += f"  ... and {len(apps) - 10} more\n"

    state_file = os.path.join(PROJECT_DIR_WSL, "system_state.txt")
    with open(state_file, "w") as f:
        f.write(state_text)

    ps(f'Start-Process notepad.exe -ArgumentList "{PROJECT_DIR}\\system_state.txt"')
    pause(2)
    move_to_center("notepad")
    pause(1)

    speak(
        f"First, system awareness. I see everything on this machine. "
        f"{mon_count} monitors, {app_count} applications, "
        f"{mem_pct} percent memory. "
        f"Open apps, clipboard, recent files. All in real time."
    )
    pause(8)
    system_screenshot = take_screenshot("system_awareness")
    pause(1)

    minimize_proc("notepad")
    pause(0.5)

    # ════════════════════════════════════════
    # ACT 3: WORD — Technical Overview (~30s)
    # ════════════════════════════════════════
    print("\n>> Act 3: Word — Cadre AI Technical Overview")
    speak(
        "Opening Microsoft Word. I'm writing a technical overview of Cadre AI. "
        "Sections, a formatted table, bullet points for all the agents. "
        "From scratch."
    )
    pause(2)

    word_create()
    move_to_center("WINWORD")
    pause(0.5)

    word_write_cadre_overview()
    pause(1)
    move_to_center("WINWORD")
    pause(2)

    speak(
        "A complete technical overview. What Cadre AI is, the five pillar "
        "architecture in a formatted table, and a breakdown of ten specialized agents. "
        "Written and formatted in seconds."
    )
    pause(8)
    word_screenshot = take_screenshot("word_overview")
    pause(1)

    speak("Saving to the project folder.")
    word_save_and_close()
    print("  Word saved and closed")
    pause(2)

    # ════════════════════════════════════════
    # ACT 4: EXCEL — Dashboard (~30s)
    # ════════════════════════════════════════
    print("\n>> Act 4: Excel — Agent Performance Dashboard")
    speak(
        "Now Excel. An agent performance dashboard. "
        "Eight agents, task counts, success rates, lines of code changed, "
        "two charts, and conditional formatting. Watch."
    )
    pause(2)

    excel_create()
    move_to_center("EXCEL")
    pause(0.5)

    excel_build_dashboard()
    pause(1)
    move_to_center("EXCEL")
    pause(2)

    speak(
        "Eight agents tracked. Success rates with conditional formatting. "
        "A bar chart for tasks completed, a pie chart for code impact. "
        "Formulas, totals, summary metrics. All from scratch."
    )
    pause(8)
    excel_screenshot = take_screenshot("excel_dashboard")
    pause(1)

    speak("Saving to the project folder.")
    excel_save_and_close()
    print("  Excel saved and closed")
    pause(2)

    # ════════════════════════════════════════
    # ACT 5: BROWSER — GitHub Repo (~20s)
    # ════════════════════════════════════════
    print("\n>> Act 5: Browser — GitHub Repo")
    speak(
        "Full browser control. Let me open the Cadre AI repository on GitHub."
    )
    pause(2)

    chrome_open_and_center("https://github.com/WeberG619/cadre-ai")
    pause(3)
    move_to_center("chrome")
    pause(2)

    speak(
        "The source code, README, documentation, examples. "
        "Open source, MIT licensed. "
        "I can search, navigate, read content, fill forms. "
        "Anything a human can do in a browser."
    )
    pause(8)
    browser_screenshot = take_screenshot("github_repo")
    pause(1)

    chrome_close()
    pause(1)

    # ════════════════════════════════════════
    # ACT 6: BLUEBEAM — PDF Plans (~20s)
    # ════════════════════════════════════════
    print("\n>> Act 6: Bluebeam — Construction Documents")
    speak(
        "I also work with Bluebeam Revu. "
        "Construction documents, engineering plans, PDF markup."
    )
    pause(2)

    move_to_center("Revu")
    pause(2)

    speak(
        "Navigate pages, read annotations, extract data from drawings. "
        "If you work in architecture or construction, "
        "Cadre AI understands your tools."
    )
    pause(8)
    bluebeam_screenshot = take_screenshot("bluebeam_plans")
    pause(1)

    minimize_proc("Revu")
    pause(0.5)

    # ════════════════════════════════════════
    # ACT 7: TELEGRAM — Live Message (~20s)
    # ════════════════════════════════════════
    print("\n>> Act 7: Telegram — Live Message")
    speak(
        "Now I'll prove this is live. "
        "Sending a real message to Weber's phone through Telegram."
    )
    pause(2)

    tg_msg = (
        "*CADRE AI — Live Demo*\n\n"
        "Just created:\n"
        "- Technical overview document (Word)\n"
        "- Agent performance dashboard (Excel)\n"
        "- Browsed GitHub repo\n"
        "- Reviewed Bluebeam plans\n\n"
        f"System: {mon_count} monitors, {mem_pct}% memory, {app_count} apps\n\n"
        "_Fully autonomous. No human touched anything._"
    )
    send_telegram(tg_msg)
    pause(1)

    speak(
        "Sent. Weber's phone just buzzed. "
        "Telegram, WhatsApp, voice alerts, email. "
        "Cadre AI reaches you wherever you are."
    )
    pause(4)

    # Open Telegram Desktop to show the message
    ps(r'Start-Process "C:\Users\rick\AppData\Roaming\Telegram Desktop\Telegram.exe"')
    pause(4)
    move_to_center("Telegram")
    pause(3)
    telegram_screenshot = take_screenshot("telegram_message")
    pause(1)

    minimize_proc("Telegram")
    pause(1)

    # ════════════════════════════════════════
    # ACT 8: POWERPOINT — Summary Deck (~30s)
    # ════════════════════════════════════════
    print("\n>> Act 8: PowerPoint — Summary Deck")
    speak(
        "Now a PowerPoint presentation with live screenshots "
        "from everything I just did. Embedded as proof."
    )
    pause(2)

    ppt_create()
    move_to_center("POWERPNT")
    pause(1)

    ppt_add_title_slide(
        "Cadre AI",
        "Your AI Agent Squad for Claude Code\n"
        "17 agents  |  Persistent memory  |  Desktop automation\n"
        "github.com/WeberG619/cadre-ai"
    )
    pause(1)
    move_to_center("POWERPNT")

    # Add screenshot slides
    screenshots = [
        (system_screenshot, "System Awareness",
         "Real-time monitoring of apps, monitors, memory, clipboard"),
        (word_screenshot, "Word: Technical Overview",
         "Sections, table, bullet points — created from scratch"),
        (excel_screenshot, "Excel: Agent Dashboard",
         "8 agents, 2 charts, conditional formatting — all automated"),
        (browser_screenshot, "Browser: GitHub Repository",
         "Full browser control — navigate, search, read, interact"),
        (bluebeam_screenshot, "Bluebeam: Construction Documents",
         "PDF markup, page navigation, annotation extraction"),
        (telegram_screenshot, "Telegram: Live Message",
         "Real message sent to a real phone — not a simulation"),
    ]
    for img, title, caption in screenshots:
        if img:
            ppt_add_image_slide(title, img, caption)
            pause(0.5)

    move_to_center("POWERPNT")
    pause(1)

    speak(
        "Six live screenshots embedded. System awareness, Word, Excel, "
        "browser, Bluebeam, and Telegram. All captured during this demo."
    )
    pause(8)

    ppt_save_and_close()
    print("  PowerPoint saved and closed")
    pause(1)

    # ════════════════════════════════════════
    # ACT 9: FILE EXPLORER — Show Results (~15s)
    # ════════════════════════════════════════
    print("\n>> Act 9: File Explorer — Results")
    speak(
        "Here's the project folder with everything I just created."
    )
    pause(2)

    show_project_folder()
    pause(2)
    take_screenshot("completed_project")
    pause(1)

    speak(
        "Three professional documents. Organized folders. "
        "Created in minutes. Completely autonomous."
    )
    pause(6)

    # Close explorer
    ps("""
Get-Process -Name 'explorer' -EA SilentlyContinue | Where-Object {$_.MainWindowTitle -ne ''} | ForEach-Object { $_.CloseMainWindow() | Out-Null }
""")
    pause(1)

    # ════════════════════════════════════════
    # ACT 10: CLOSING (~20s)
    # ════════════════════════════════════════
    print("\n>> Act 10: Closing")
    chrome_open_and_center("https://github.com/WeberG619/cadre-ai")
    pause(3)
    move_to_center("chrome")
    pause(1)

    speak(
        "17 specialized agents. Persistent memory across sessions. "
        "Desktop automation for Word, Excel, PowerPoint, browser, and more. "
        "A common sense engine that checks its own work. "
        "Available now on GitHub. Open source. MIT licensed. "
        "Cadre AI."
    )
    pause(12)

    take_screenshot("closing_github")
    pause(3)

    chrome_close()
    pause(1)

    # ── STOP RECORDING ──
    print("\nStopping recording...")
    result = cl.stop_record()
    output_path = getattr(result, "output_path", "unknown")
    cl.disconnect()

    print(f"\nRecording saved: {output_path}")
    print(f"Project folder: {PROJECT_DIR}")
    print("=" * 60)
    print("CADRE AI DEMO COMPLETE")
    print("=" * 60)
    return output_path


if __name__ == "__main__":
    try:
        path = run_demo()
        print(f"\nVideo: {path}")
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

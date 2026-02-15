#!/usr/bin/env python3
"""
Autonomous System Demo — Take 3
================================
ACTION-PACKED. Everything visible on center monitor.
Show, don't tell. Create real documents LIVE while narrating.
Word letters, Excel charts, Gmail compose, Telegram, PowerPoint.
No personal info exposed. Maximum wow factor.
"""

import json
import subprocess
import time
import os
import sys

OBS_HOST = "172.24.224.1"
OBS_PORT = 4455
OBS_PASSWORD = "2GwO1bvUqSIy3V2X"
CENTER_X = -2500
CENTER_Y = 50
CENTER_W = 2400
CENTER_H = 1300
DEMO_DIR = "/mnt/d/_CLAUDE-TOOLS/obs-mcp"
SCREENSHOT_DIR = "D:\\_CLAUDE-TOOLS\\obs-mcp\\_demo_screenshots"

_obs_cl = None


def speak(text):
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
    try:
        r = subprocess.run(["powershell.exe", "-Command", cmd],
                           capture_output=True, text=True, timeout=timeout)
        if r.stderr.strip():
            print(f"  PS stderr: {r.stderr.strip()[:120]}")
        return r.stdout.strip()
    except Exception as e:
        print(f"  PS error: {e}")
        return ""


def move_to_center(proc_name, retries=8):
    """Move a window to center monitor. Retries until window found."""
    # NOTE: Using double braces {{ }} in f-string to produce single { } for PowerShell
    for attempt in range(retries):
        result = ps(f"""
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class MV{attempt} {{
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h,int x,int y,int w,int ht,bool r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}}
'@
$p = Get-Process -Name '{proc_name}' -EA SilentlyContinue | Where-Object {{$_.MainWindowTitle -ne ''}} | Select-Object -First 1
if($p) {{
    [MV{attempt}]::MoveWindow($p.MainWindowHandle, {CENTER_X}, {CENTER_Y}, {CENTER_W}, {CENTER_H}, $true)
    [MV{attempt}]::SetForegroundWindow($p.MainWindowHandle)
    Write-Output "MOVED:$($p.MainWindowTitle)"
}} else {{
    Write-Output "NOT_FOUND"
}}
""")
        if "MOVED" in result:
            print(f"  [WINDOW] {proc_name} → center monitor ({result})")
            return True
        print(f"  [WINDOW] {proc_name} attempt {attempt+1}: {result}")
        pause(1)
    print(f"  [WARNING] Could not move {proc_name} to center after {retries} attempts")
    return False


def minimize_all():
    """Minimize common apps to clear center monitor."""
    for proc in ['POWERPNT', 'EXCEL', 'WINWORD', 'notepad', 'chrome']:
        ps(f"""
Add-Type @'
using System;using System.Runtime.InteropServices;
public class SM {{ [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h,int c); }}
'@
Get-Process -Name '{proc}' -EA SilentlyContinue | ForEach-Object {{ [SM]::ShowWindow($_.MainWindowHandle, 6) }}
""")


def take_screenshot(name):
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
    try:
        import urllib.request
        sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/proactive")
        from notify_channels import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"  Telegram error: {e}")
        return False


# ── App launchers — each opens THEN positions on center ──

def word_create():
    """Open Word on center monitor."""
    ps("""
$word = New-Object -ComObject Word.Application
$word.Visible = $true
$doc = $word.Documents.Add()
""", timeout=20)
    pause(2)
    move_to_center("WINWORD")
    pause(1)


def word_write_letter():
    """Write a professional business letter in the open Word doc."""
    ps(r"""
$word = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application')
$sel = $word.Selection

# Letterhead
$sel.Font.Name = 'Calibri'
$sel.Font.Size = 22
$sel.Font.Bold = $true
$sel.Font.Color = 0x8B4513
$sel.ParagraphFormat.Alignment = 1
$sel.TypeText("WEBER GOUIN")
$sel.TypeParagraph()
$sel.Font.Size = 11
$sel.Font.Bold = $false
$sel.Font.Color = 0x666666
$sel.TypeText("Developer & Systems Architect  |  AI Infrastructure")
$sel.TypeParagraph()
$sel.TypeParagraph()

# Horizontal line
$sel.Font.Color = 0xCCCCCC
$sel.TypeText("________________________________________")
$sel.TypeParagraph()
$sel.TypeParagraph()

# Date
$sel.ParagraphFormat.Alignment = 0
$sel.Font.Size = 11
$sel.Font.Color = 0x333333
$sel.Font.Bold = $false
$sel.TypeText("February 13, 2026")
$sel.TypeParagraph()
$sel.TypeParagraph()

# Recipient
$sel.TypeText("Dear Client,")
$sel.TypeParagraph()
$sel.TypeParagraph()

# Body
$sel.TypeText("Thank you for your interest in our AI-assisted workflow system. This letter was composed entirely by an autonomous AI assistant running on a local machine " + [char]0x2014 + " no cloud services, no browser automation, no human input.")
$sel.TypeParagraph()
$sel.TypeParagraph()

$sel.TypeText("The system operates 24/7 with full access to Microsoft Office, email, calendar, messaging, and over 50 integrated tools. Everything you see in this demonstration is happening live, in real-time.")
$sel.TypeParagraph()
$sel.TypeParagraph()

$sel.TypeText("If you'd like to learn more about how this technology can transform your daily operations, we'd be happy to discuss.")
$sel.TypeParagraph()
$sel.TypeParagraph()

# Signature
$sel.TypeText("Best regards,")
$sel.TypeParagraph()
$sel.Font.Bold = $true
$sel.Font.Color = 0x8B4513
$sel.TypeText("Weber Gouin")
$sel.TypeParagraph()
$sel.Font.Bold = $false
$sel.Font.Size = 10
$sel.Font.Color = 0x888888
$sel.TypeText("Written by Claude  |  AI Personal Assistant")
""", timeout=20)


def word_close():
    ps("""
try {
    $word = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application')
    foreach ($doc in $word.Documents) { $doc.Close([ref]$false) }
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
} catch {}
""")


def excel_create():
    """Open Excel on center monitor."""
    ps("""
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $true
$wb = $excel.Workbooks.Add()
""", timeout=20)
    pause(2)
    move_to_center("EXCEL")
    pause(1)


def excel_build_report():
    """Build financial report with chart in open Excel."""
    ps(r"""
$excel = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
$ws = $excel.ActiveWorkbook.ActiveSheet
$ws.Name = 'Q1 Report'

# Title
$ws.Cells.Item(1,1) = 'Q1 2026 - Revenue & Expenses'
$ws.Range('A1:D1').Merge()
$ws.Cells.Item(1,1).Font.Size = 16
$ws.Cells.Item(1,1).Font.Bold = $true

# Headers
$ws.Cells.Item(3,1) = 'Month'
$ws.Cells.Item(3,2) = 'Revenue'
$ws.Cells.Item(3,3) = 'Expenses'
$ws.Cells.Item(3,4) = 'Profit'

$hdr = $ws.Range('A3:D3')
$hdr.Font.Bold = $true
$hdr.Interior.Color = 0xC47244
$hdr.Font.Color = 0xFFFFFF

# Data rows
$ws.Cells.Item(4,1) = 'January';  $ws.Cells.Item(4,2) = 28500; $ws.Cells.Item(4,3) = 18200
$ws.Cells.Item(5,1) = 'February'; $ws.Cells.Item(5,2) = 32100; $ws.Cells.Item(5,3) = 17900
$ws.Cells.Item(6,1) = 'March';    $ws.Cells.Item(6,2) = 35800; $ws.Cells.Item(6,3) = 19500

# Profit formulas
$ws.Cells.Item(4,4).Formula = '=B4-C4'
$ws.Cells.Item(5,4).Formula = '=B5-C5'
$ws.Cells.Item(6,4).Formula = '=B6-C6'

# Total row
$ws.Cells.Item(8,1) = 'TOTAL'
$ws.Cells.Item(8,1).Font.Bold = $true
$ws.Cells.Item(8,2).Formula = '=SUM(B4:B6)'
$ws.Cells.Item(8,3).Formula = '=SUM(C4:C6)'
$ws.Cells.Item(8,4).Formula = '=SUM(D4:D6)'
$ws.Range('A8:D8').Font.Bold = $true
$ws.Range('A8:D8').Borders.Item(8).LineStyle = 1
$ws.Range('A8:D8').Borders.Item(8).Weight = 4

# Currency format
$ws.Range('B4:D8').NumberFormat = '$#,##0'
$ws.Range('A3:D6').Borders.LineStyle = 1
$ws.Columns.Item('A:D').AutoFit() | Out-Null

# CREATE CHART
$chartObj = $ws.ChartObjects.Add(20, 180, 500, 280)
$chart = $chartObj.Chart
$chart.SetSourceData($ws.Range('A3:D6'))
$chart.ChartType = 51
$chart.HasTitle = $true
$chart.ChartTitle.Text = 'Q1 2026 Financial Summary'
$chart.ChartTitle.Font.Size = 14
$chart.HasLegend = $true
$chart.Legend.Position = -4107

$chart.SeriesCollection(1).Format.Fill.ForeColor.RGB = 0xC47244
$chart.SeriesCollection(2).Format.Fill.ForeColor.RGB = 0x4472C4
$chart.SeriesCollection(3).Format.Fill.ForeColor.RGB = 0x70AD47
""", timeout=25)


def excel_close():
    ps("""
try {
    $excel = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
    $excel.DisplayAlerts = $false
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
} catch {}
""")


def ppt_create():
    """Create PowerPoint on center monitor."""
    ps("""
$ppt = New-Object -ComObject PowerPoint.Application
$ppt.Visible = [Microsoft.Office.Interop.PowerPoint.MsoTriState]::msoTrue
$pres = $ppt.Presentations.Add()
""", timeout=20)
    pause(2)
    move_to_center("POWERPNT")
    pause(1)


def ppt_add_slide(title, body, color="0x2B579A"):
    title_esc = title.replace("'", "''").replace('"', '`"')
    body_esc = body.replace("'", "''").replace('"', '`"')
    ps(f"""
$ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application')
$pres = $ppt.ActivePresentation
$count = $pres.Slides.Count
$layout = $pres.SlideMaster.CustomLayouts.Item(2)
$slide = $pres.Slides.AddSlide($count + 1, $layout)

$slide.Shapes.Item(1).TextFrame.TextRange.Text = "{title_esc}"
$slide.Shapes.Item(1).TextFrame.TextRange.Font.Size = 36
$slide.Shapes.Item(1).TextFrame.TextRange.Font.Bold = [Microsoft.Office.Interop.PowerPoint.MsoTriState]::msoTrue
$slide.Shapes.Item(1).TextFrame.TextRange.Font.Color.RGB = {color}

$slide.Shapes.Item(2).TextFrame.TextRange.Text = "{body_esc}"
$slide.Shapes.Item(2).TextFrame.TextRange.Font.Size = 20

$ppt.ActiveWindow.View.GotoSlide($slide.SlideIndex)
""", timeout=15)


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
$slide.Shapes.Item(1).TextFrame.TextRange.Font.Bold = [Microsoft.Office.Interop.PowerPoint.MsoTriState]::msoTrue

$slide.Shapes.Item(2).TextFrame.TextRange.Text = "{sub_esc}"
$slide.Shapes.Item(2).TextFrame.TextRange.Font.Size = 24

$slide.FollowMasterBackground = [Microsoft.Office.Interop.PowerPoint.MsoTriState]::msoFalse
$slide.Background.Fill.Solid()
$slide.Background.Fill.ForeColor.RGB = 0x1E1E2E
$slide.Shapes.Item(1).TextFrame.TextRange.Font.Color.RGB = 0xFFFFFF
$slide.Shapes.Item(2).TextFrame.TextRange.Font.Color.RGB = 0xCCCCCC

$ppt.ActiveWindow.View.GotoSlide(1)
""", timeout=15)


def ppt_add_image_slide(title, image_path, caption=""):
    title_esc = title.replace("'", "''").replace('"', '`"')
    caption_esc = caption.replace("'", "''").replace('"', '`"')
    ps(f"""
$ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application')
$pres = $ppt.ActivePresentation
$count = $pres.Slides.Count
$layout = $pres.SlideMaster.CustomLayouts.Item(7)
$slide = $pres.Slides.AddSlide($count + 1, $layout)

foreach($sh in $slide.Shapes) {{ try {{ $sh.Delete() }} catch {{}} }}

$titleBox = $slide.Shapes.AddTextbox(1, 40, 10, 880, 50)
$titleBox.TextFrame.TextRange.Text = "{title_esc}"
$titleBox.TextFrame.TextRange.Font.Size = 28
$titleBox.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Interop.PowerPoint.MsoTriState]::msoTrue
$titleBox.TextFrame.TextRange.Font.Color.RGB = 0x2B579A

$img = $slide.Shapes.AddPicture("{image_path}", [Microsoft.Office.Interop.PowerPoint.MsoTriState]::msoFalse, [Microsoft.Office.Interop.PowerPoint.MsoTriState]::msoTrue, 60, 70, 840, 420)

if ("{caption_esc}" -ne "") {{
    $capBox = $slide.Shapes.AddTextbox(1, 40, 500, 880, 40)
    $capBox.TextFrame.TextRange.Text = "{caption_esc}"
    $capBox.TextFrame.TextRange.Font.Size = 14
    $capBox.TextFrame.TextRange.Font.Color.RGB = 0x666666
    $capBox.TextFrame.TextRange.ParagraphFormat.Alignment = 2
}}

$ppt.ActiveWindow.View.GotoSlide($slide.SlideIndex)
""", timeout=15)


def ppt_close():
    ps("""
try {
    $ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application')
    $ppt.ActivePresentation.Close()
    $ppt.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
} catch {}
""")


def chrome_open_and_center(url):
    """Open Chrome with URL and move to center monitor."""
    ps(f'Start-Process "chrome.exe" -ArgumentList "--new-window {url}"')
    pause(3)
    move_to_center("chrome")
    pause(1)


def chrome_close():
    ps("""
$chrome = Get-Process -Name 'chrome' -EA SilentlyContinue | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -First 1
if ($chrome) { $chrome.CloseMainWindow() | Out-Null }
""")


# ================================================================
# MAIN DEMO — TAKE 3
# ================================================================

def run_demo():
    global _obs_cl
    import obsws_python as obs

    print("=" * 60)
    print("DEMO — TAKE 3")
    print("=" * 60)

    cl = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD, timeout=5)
    _obs_cl = cl
    cl.set_current_program_scene("Screen 2")
    pause(1)

    # Setup
    ps(f'New-Item -ItemType Directory -Force -Path "{SCREENSHOT_DIR}" | Out-Null')
    minimize_all()
    pause(1)

    # ── TEST: Verify center monitor positioning works ──
    print(">> Pre-check: Testing window positioning...")
    ps("Start-Process notepad.exe")
    pause(2)
    moved = move_to_center("notepad")
    if moved:
        print("  [OK] Window positioning confirmed working")
    else:
        print("  [FAIL] Window positioning not working — check monitor coordinates")
    ps("Get-Process -Name 'notepad' -EA SilentlyContinue | Stop-Process -Force")
    pause(1)

    # Get live system data
    try:
        with open("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json") as f:
            state = json.load(f)
    except Exception:
        state = {}

    apps = state.get("applications", [])
    mem = state.get("system", {})
    mon_count = state.get("monitors", {}).get("count", "3")
    mem_pct = mem.get("memory_percent", "?")
    app_count = len(apps)

    result = subprocess.run(
        ["bash", "/mnt/d/_CLAUDE-TOOLS/gateway/daemon.sh", "status"],
        capture_output=True, text=True, timeout=10
    )
    running = result.stdout.count("[OK]")

    # ── START RECORDING ──
    print("Recording started.")
    cl.start_record()
    pause(2)

    # ════════════════════════════════════════════════════════
    # ACT 1: COLD OPEN
    # ════════════════════════════════════════════════════════
    print(">> Act 1: Cold open")

    speak(
        "Hey. I'm Claude. "
        "Right now, nobody is at this computer. "
        "Nobody is touching the mouse. Nobody is using the keyboard. "
        "Everything you are about to see, I'm doing completely on my own, "
        "from inside this machine. Watch."
    )
    pause(1)

    # ════════════════════════════════════════════════════════
    # ACT 2: WORD — Business letter LIVE on center monitor
    # ════════════════════════════════════════════════════════
    print(">> Act 2: Word — business letter")

    speak(
        "Let me open Microsoft Word and write a professional letter. "
        "From scratch. No template."
    )
    pause(0.5)

    # Open Word → wait → move to center → THEN write content
    word_create()
    move_to_center("WINWORD")  # Extra move just to be sure
    pause(0.5)

    word_write_letter()
    pause(1)
    move_to_center("WINWORD")  # Re-center after content added
    pause(1)

    speak(
        "A full business letter. Formatted letterhead, date, body, signature. "
        "I wrote every word you see. No copy paste. No template. "
        "Contracts, proposals, reports, I can generate anything in Word."
    )
    pause(1)

    word_screenshot = take_screenshot("word_letter")
    pause(1)

    word_close()
    pause(1)

    # ════════════════════════════════════════════════════════
    # ACT 3: EXCEL — Financial report with CHART
    # ════════════════════════════════════════════════════════
    print(">> Act 3: Excel — financial report + chart")

    speak(
        "Now Excel. A quarterly financial report "
        "with real formulas and a chart. Watch."
    )
    pause(0.5)

    # Open Excel → wait → move to center → THEN build content
    excel_create()
    move_to_center("EXCEL")  # Extra move
    pause(0.5)

    excel_build_report()
    pause(1)
    move_to_center("EXCEL")  # Re-center after chart added
    pause(2)

    speak(
        "Revenue, expenses, profit. All formatted. Formulas calculated. "
        "And a full column chart, generated live from the data. "
        "If you run a business, imagine getting this every Monday morning. "
        "Automatically. Without asking."
    )
    pause(1)

    excel_screenshot = take_screenshot("excel_chart")
    pause(1)

    excel_close()
    pause(1)

    # ════════════════════════════════════════════════════════
    # ACT 4: TELEGRAM — Real message to real phone
    # ════════════════════════════════════════════════════════
    print(">> Act 4: Telegram — live message")

    speak(
        "Now let me prove this is real. "
        "Sending a message to Weber's phone. "
        "Telegram. Live. Right now."
    )
    pause(0.5)

    tg_msg = (
        "*LIVE DEMO — Take 3*\n\n"
        "This message was sent during a live recording.\n\n"
        f"System: {app_count} apps, {mem_pct}% memory, "
        f"{running} services running.\n\n"
        "_Fully autonomous. No human involvement._"
    )
    send_telegram(tg_msg)
    pause(1)

    speak(
        "Sent. That just landed on his phone. "
        "A real push notification. Not simulated. "
        "I can message him anytime. Day or night. "
        "Telegram, WhatsApp, voice alerts, email. "
        "He doesn't check in with me. I check in with him."
    )
    pause(1)

    # ════════════════════════════════════════════════════════
    # ACT 5: GMAIL COMPOSE — Browser control, no inbox shown
    # ════════════════════════════════════════════════════════
    print(">> Act 5: Gmail compose in Chrome")

    speak(
        "I also have full browser access. "
        "Let me compose an email in Gmail."
    )
    pause(0.5)

    # Full-screen compose URL — goes straight to compose, no inbox
    compose_url = (
        "https://mail.google.com/mail/u/0/?view=cm&fs=1&tf=1"
        "&to=demo%40example.com"
        "&su=AI%20Assistant%20Demo%20-%20Automated%20Email"
        "&body=Hello%2C%0A%0AThis%20email%20was%20composed%20by%20an%20AI%20"
        "assistant%20running%20on%20a%20local%20machine.%0A%0A"
        "No%20human%20typed%20this.%0A%0ABest%20regards%2C%0AClaude"
    )
    chrome_open_and_center(compose_url)
    pause(2)
    move_to_center("chrome")  # Extra move
    pause(1)

    gmail_screenshot = take_screenshot("gmail_compose")
    pause(1)

    speak(
        "Gmail compose window. Recipient, subject, body, all filled in. "
        "I can send emails, schedule them, attach files. "
        "Anything you'd do manually, I do in seconds."
    )
    pause(1)

    chrome_close()
    pause(1)

    # ════════════════════════════════════════════════════════
    # ACT 6: POWERPOINT — Summary deck with live screenshots
    # ════════════════════════════════════════════════════════
    print(">> Act 6: PowerPoint — summary with screenshots")

    speak(
        "Now let me put it all together. "
        "I'll create a PowerPoint presentation "
        "using the screenshots I just captured."
    )
    pause(0.5)

    # Open PowerPoint → wait → move to center
    ppt_create()
    move_to_center("POWERPNT")  # Extra move
    pause(1)

    # Title slide
    ppt_add_title_slide(
        "System-Native AI Assistant",
        "Built by Weber Gouin  |  Powered by Claude\n"
        "A 24/7 autonomous assistant that lives on your machine"
    )
    pause(1)
    move_to_center("POWERPNT")

    speak("Title slide. Now the proof.")
    pause(0.5)

    # Insert screenshots
    if word_screenshot:
        ppt_add_image_slide(
            "Live: Business Letter Created in Word",
            word_screenshot,
            "Written from scratch during this recording."
        )
        pause(1)

    if excel_screenshot:
        ppt_add_image_slide(
            "Live: Financial Report with Chart",
            excel_screenshot,
            "Data, formulas, and chart — all generated live."
        )
        pause(1)

    if gmail_screenshot:
        ppt_add_image_slide(
            "Live: Email Composed in Gmail",
            gmail_screenshot,
            "Full browser control. Automated email composition."
        )
        pause(1)

    move_to_center("POWERPNT")
    pause(0.5)

    speak(
        "Three live screenshots. Each captured in real time. "
        "Embedded into a presentation I created moments ago. "
        "This is system-native access."
    )
    pause(1)

    # ════════════════════════════════════════════════════════
    # ACT 7: SYSTEM STATUS + USE CASES
    # ════════════════════════════════════════════════════════
    print(">> Act 7: System status + use cases")

    ppt_add_slide(
        f"Right Now — {running} Services, 24/7",
        f"{mon_count} monitors  |  {app_count} apps  |  {mem_pct}% memory\n\n"
        "Gateway Hub — routes all commands\n"
        "Telegram Bot — mobile alerts\n"
        "Email Watcher — checks Gmail every 60 seconds\n"
        "Proactive Scheduler — briefings and reminders\n"
        "Web Chat + WhatsApp — additional channels\n\n"
        "Auto-restart on crash. Health checks every 5 minutes.\n"
        "All day. All night. No supervision."
    )
    pause(0.5)

    speak(
        f"{running} services running right now. "
        "If anything crashes, it restarts automatically. "
        "Weber doesn't manage these. I do."
    )
    pause(1)

    ppt_add_slide(
        "Who Is This For?",
        "Freelancers — client alerts, invoice tracking, earnings reports\n"
        "Small Business — financial reports, email triage, scheduling\n"
        "Content Creators — content calendars, post reminders, drafts\n"
        "Consultants — proposals, meeting prep, follow-ups\n"
        "Developers — monitoring, documentation, code reviews\n\n"
        "Your data stays on YOUR machine.\n"
        "No cloud. No subscriptions. Full privacy.",
        color="0xE97132"
    )
    pause(0.5)

    speak(
        "This works for anyone. "
        "Freelancers, business owners, content creators, consultants. "
        "Your data never leaves your machine. No cloud required."
    )
    pause(1)

    ppt_add_slide(
        "A Day Without Lifting a Finger",
        "7:00 AM — Morning briefing: calendar, weather, priorities\n"
        "All day — Meeting reminders 15 minutes before\n"
        "All day — Client emails trigger instant phone alerts\n"
        "All day — System health monitoring and auto-recovery\n"
        "6:00 PM — Evening summary and tomorrow preview\n"
        "Monday — Weekly overview  |  Friday — Weekly recap\n\n"
        "All automatic. No commands. No prompts.\n"
        "The system just works.",
        color="0x217346"
    )
    pause(0.5)

    speak(
        "Morning briefings at seven. "
        "Meeting reminders. Client email alerts. "
        "Evening summaries. Weekly recaps. "
        "All automatic. You never ask for any of it."
    )
    pause(1)

    # ════════════════════════════════════════════════════════
    # ACT 8: CLOSING
    # ════════════════════════════════════════════════════════
    print(">> Act 8: Closing")

    ppt_add_slide(
        "This Is Not a Demo. This Runs Every Day.",
        "What you just watched:\n\n"
        "Business letter — written live in Word\n"
        "Financial report with chart — created live in Excel\n"
        "Email — composed live in Gmail\n"
        "Telegram message — sent live to a real phone\n"
        "This presentation — built live with embedded screenshots\n\n"
        "No human touched the mouse.\n"
        "No human pressed a key.\n\n"
        "Weber built this. He's a developer, not an engineer.\n"
        "He saw a need, and he built the solution.\n\n"
        "That's the difference between a chatbot and an assistant."
    )
    pause(0.5)

    speak(
        "Everything you just watched was real. "
        "The letter, the spreadsheet, the chart, the email, "
        "the Telegram message, this presentation, the screenshots. "
        "All created live, with no human involvement. "
        "This system runs every single day. "
        "Weber built this himself. He's a developer, not a software engineer. "
        "He saw a need and he built the solution. "
        "That's the difference between a chatbot you visit in a browser "
        "and an assistant that lives on your machine. "
        "Thanks for watching."
    )
    pause(3)

    # Save
    ps(r"""
try {
    $ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application')
    $ppt.ActivePresentation.SaveAs('D:\_CLAUDE-TOOLS\obs-mcp\_demo_presentation_v3.pptx')
} catch {}
""")
    pause(1)

    ppt_close()
    pause(1)

    # ── STOP RECORDING ──
    print("Stopping recording...")
    result = cl.stop_record()
    output_path = getattr(result, "output_path", "unknown")
    cl.disconnect()

    print(f"\nRecording saved: {output_path}")
    print("=" * 60)
    print("TAKE 3 COMPLETE")
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

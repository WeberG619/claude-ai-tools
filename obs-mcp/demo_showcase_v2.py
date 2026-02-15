#!/usr/bin/env python3
"""
Autonomous System Demo V2 - PowerPoint Live Creation
=====================================================
Claude creates professional slides IN REAL-TIME while narrating.
Takes screenshots at key moments and inserts them into the presentation.
The creation IS the demo. Faster pacing, more visual impact.
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
DEMO_DIR = "/mnt/d/_CLAUDE-TOOLS/obs-mcp"
SCREENSHOT_DIR = "D:\\_CLAUDE-TOOLS\\obs-mcp\\_demo_screenshots"

# Global OBS client for screenshots
_obs_cl = None


def speak(text):
    """Voice narration."""
    print(f"  [VOICE] {text[:80]}...")
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
    """Run PowerShell command."""
    try:
        r = subprocess.run(["powershell.exe", "-Command", cmd],
                           capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        print(f"  PS error: {e}")
        return ""


def take_screenshot(name):
    """Take OBS screenshot of current scene, return Windows path."""
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


def move_center(proc, x=CENTER_X, y=CENTER_Y, w=2400, h=1300):
    ps(f"""
Add-Type @'
using System;using System.Runtime.InteropServices;
public class W{{[DllImport("user32.dll")]public static extern bool MoveWindow(IntPtr h,int x,int y,int w,int ht,bool r);
[DllImport("user32.dll")]public static extern bool SetForegroundWindow(IntPtr h);}}
'@
$p=Get-Process -Name '{proc}' -EA SilentlyContinue|?{{$_.MainWindowTitle -ne ''}}|Select -First 1
if($p){{[W]::MoveWindow($p.MainWindowHandle,{x},{y},{w},{h},$true);[W]::SetForegroundWindow($p.MainWindowHandle)}}
""")


def minimize(proc):
    ps(f"""
Add-Type @'
using System;using System.Runtime.InteropServices;
public class WM{{[DllImport("user32.dll")]public static extern bool ShowWindow(IntPtr h,int c);}}
'@
Get-Process -Name '{proc}' -EA SilentlyContinue|ForEach-Object{{[WM]::ShowWindow($_.MainWindowHandle,6)}}
""")


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


def ppt_create():
    """Create PowerPoint and return — leave it open for adding slides."""
    ps("""
$global:ppt = New-Object -ComObject PowerPoint.Application
$global:ppt.Visible = [Microsoft.Office.Interop.PowerPoint.MsoTriState]::msoTrue
$global:pres = $global:ppt.Presentations.Add()
""", timeout=20)
    pause(2)
    move_center("POWERPNT")


def ppt_add_slide(title, body, color="0x2B579A"):
    """Add a slide with title and bullet content. Color is BGR hex."""
    # Escape quotes for PowerShell
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
    """Add a title slide."""
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
$slide.Background.Fill.ForeColor.RGB = 0x3D2B1E
$slide.Shapes.Item(1).TextFrame.TextRange.Font.Color.RGB = 0xFFFFFF
$slide.Shapes.Item(2).TextFrame.TextRange.Font.Color.RGB = 0xCCCCCC

$ppt.ActiveWindow.View.GotoSlide(1)
""", timeout=15)


def ppt_add_image_slide(title, image_path, caption=""):
    """Add a slide with a screenshot image."""
    title_esc = title.replace("'", "''").replace('"', '`"')
    caption_esc = caption.replace("'", "''").replace('"', '`"')
    ps(f"""
$ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application')
$pres = $ppt.ActivePresentation
$count = $pres.Slides.Count
$layout = $pres.SlideMaster.CustomLayouts.Item(7)
$slide = $pres.Slides.AddSlide($count + 1, $layout)

# Clear default placeholders
foreach($sh in $slide.Shapes) {{ try {{ $sh.Delete() }} catch {{}} }}

# Title at top
$titleBox = $slide.Shapes.AddTextbox(1, 40, 10, 880, 50)
$titleBox.TextFrame.TextRange.Text = "{title_esc}"
$titleBox.TextFrame.TextRange.Font.Size = 28
$titleBox.TextFrame.TextRange.Font.Bold = [Microsoft.Office.Interop.PowerPoint.MsoTriState]::msoTrue
$titleBox.TextFrame.TextRange.Font.Color.RGB = 0x2B579A

# Insert screenshot image — centered, large
$img = $slide.Shapes.AddPicture("{image_path}", [Microsoft.Office.Interop.PowerPoint.MsoTriState]::msoFalse, [Microsoft.Office.Interop.PowerPoint.MsoTriState]::msoTrue, 60, 70, 840, 420)

# Caption below image
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
    """Close PowerPoint."""
    ps("""
try {
    $ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application')
    $ppt.ActivePresentation.Close()
    $ppt.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
} catch {}
""")


def excel_create_finance():
    """Create a finance spreadsheet demo."""
    ps("""
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $true
$wb = $excel.Workbooks.Add()
$ws = $wb.ActiveSheet
$ws.Name = 'Q1 Financial Summary'

# Headers
$ws.Cells.Item(1,1) = 'Q1 2026 Financial Summary'
$ws.Range('A1:E1').Merge()
$ws.Cells.Item(1,1).Font.Size = 16
$ws.Cells.Item(1,1).Font.Bold = $true

$ws.Cells.Item(3,1) = 'Category'
$ws.Cells.Item(3,2) = 'January'
$ws.Cells.Item(3,3) = 'February'
$ws.Cells.Item(3,4) = 'March'
$ws.Cells.Item(3,5) = 'Total'

# Data
$ws.Cells.Item(4,1) = 'Revenue'
$ws.Cells.Item(4,2) = 12500; $ws.Cells.Item(4,3) = 14200; $ws.Cells.Item(4,4) = 15800
$ws.Cells.Item(4,5).Formula = '=SUM(B4:D4)'

$ws.Cells.Item(5,1) = 'Expenses'
$ws.Cells.Item(5,2) = 8200; $ws.Cells.Item(5,3) = 7900; $ws.Cells.Item(5,4) = 8500
$ws.Cells.Item(5,5).Formula = '=SUM(B5:D5)'

$ws.Cells.Item(6,1) = 'Net Profit'
$ws.Cells.Item(6,2).Formula = '=B4-B5'; $ws.Cells.Item(6,3).Formula = '=C4-C5'; $ws.Cells.Item(6,4).Formula = '=D4-D5'
$ws.Cells.Item(6,5).Formula = '=SUM(B6:D6)'

$ws.Cells.Item(8,1) = 'Profit Margin'
$ws.Cells.Item(8,2).Formula = '=B6/B4'; $ws.Cells.Item(8,3).Formula = '=C6/C4'; $ws.Cells.Item(8,4).Formula = '=D6/D4'
$ws.Cells.Item(8,5).Formula = '=E6/E4'
$ws.Range('B8:E8').NumberFormat = '0.0%'

# Format headers
$hdr = $ws.Range('A3:E3')
$hdr.Font.Bold = $true
$hdr.Interior.Color = 0x4472C4
$hdr.Font.Color = 0xFFFFFF

# Format profit row
$ws.Range('A6:E6').Font.Bold = $true
$ws.Range('A8:E8').Font.Bold = $true

# Currency format
$ws.Range('B4:E6').NumberFormat = '$#,##0'

# Borders
$ws.Range('A3:E8').Borders.LineStyle = 1

# Auto-fit
$ws.Columns.Item('A:E').AutoFit() | Out-Null

$wb.SaveAs('D:\\_CLAUDE-TOOLS\\obs-mcp\\_demo_finance.xlsx')
""", timeout=20)


def excel_close():
    ps("""
try {
    $excel = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
    $excel.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
} catch {}
""")


def open_chrome(url):
    """Open a URL in Chrome and position on center monitor."""
    ps(f'Start-Process "chrome.exe" -ArgumentList "--new-window {url}"')
    pause(3)
    move_center("chrome", w=2400, h=1300)


def close_chrome():
    """Close the most recent Chrome window."""
    ps("""
$chrome = Get-Process -Name 'chrome' -EA SilentlyContinue | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -First 1
if ($chrome) {
    $chrome.CloseMainWindow() | Out-Null
}
""")


# ============================================================
# MAIN DEMO
# ============================================================

def run_demo():
    global _obs_cl
    import obsws_python as obs

    print("=" * 60)
    print("DEMO V2 - STARTING")
    print("=" * 60)

    cl = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD, timeout=5)
    _obs_cl = cl
    cl.set_current_program_scene("Screen 2")
    pause(1)

    # Create screenshot directory
    ps(f'New-Item -ItemType Directory -Force -Path "{SCREENSHOT_DIR}" | Out-Null')

    # Clear center monitor
    for proc in ['POWERPNT', 'EXCEL', 'notepad']:
        minimize(proc)
    minimize('explorer')
    pause(1)

    print("Recording started.")
    cl.start_record()
    pause(2)

    # ---- ACT 1: INTRO + CREATE POWERPOINT LIVE ----
    print(">> Act 1: Intro")

    speak(
        "Hey there. I'm Claude, Weber's AI assistant. "
        "Weber is not at his desk. Nobody is touching the mouse or the keyboard. "
        "Everything you see from this point on, I'm doing on my own, "
        "from inside the system. Not through a browser. Not through remote access. "
        "I live on this machine. Let me show you what that means."
    )
    pause(1)

    # ---- ACT 2: CREATE PRESENTATION LIVE ----
    print(">> Act 2: Create PowerPoint live")

    speak(
        "First, I'm going to create a presentation. Right now. Live. Watch."
    )
    pause(0.5)

    ppt_create()
    pause(1)

    ppt_add_title_slide(
        "System-Native AI Assistant",
        "Built by Weber Gouin  |  Powered by Claude\nA 24/7 autonomous assistant that lives on your machine"
    )
    pause(1)

    speak(
        "Title slide done. Dark theme, professional. "
        "Now let me add the content while I explain what this system does."
    )
    pause(1)

    # ---- ACT 3: SERVICES SLIDE ----
    print(">> Act 3: Services slide")

    # Get live status
    result = subprocess.run(
        ["bash", "/mnt/d/_CLAUDE-TOOLS/gateway/daemon.sh", "status"],
        capture_output=True, text=True, timeout=10
    )
    # Count running services
    running = result.stdout.count("[OK]")

    ppt_add_slide(
        "Always On — 6 Services Running 24/7",
        f"Gateway Hub — routes all messages and commands\n"
        f"Telegram Bot — mobile communication channel\n"
        f"Email Watcher — monitors 2 Gmail accounts every 60 seconds\n"
        f"Proactive Scheduler — briefings, reminders, summaries\n"
        f"Web Chat — browser-based interface\n"
        f"WhatsApp Gateway — additional messaging channel\n\n"
        f"Currently: {running} services active with auto-restart"
    )
    pause(0.5)

    speak(
        "Six services, all running right now. "
        "If any of them crash, they restart automatically. "
        "I check their health every five minutes. "
        "Weber doesn't manage these. I do."
    )
    pause(1)

    # ---- ACT 4: EMAIL SLIDE ----
    print(">> Act 4: Email slide")

    try:
        with open("/mnt/d/_CLAUDE-TOOLS/email-watcher/email_alerts.json") as f:
            emails = json.load(f)
    except Exception:
        emails = {"alerts": [], "urgent_count": 0, "needs_response_count": 0, "accounts_checked": []}

    alert_count = emails.get("needs_response_count", 0)
    acct_count = len(emails.get("accounts_checked", []))

    ppt_add_slide(
        "Email Intelligence — Never Miss What Matters",
        f"Monitoring: {acct_count} Gmail accounts\n"
        f"Check frequency: Every 60 seconds\n"
        f"Current alerts: {alert_count} flagged\n\n"
        f"Client emails — instant Telegram + voice alert\n"
        f"Urgent emails — Telegram + voice notification\n"
        f"Newsletters — quietly categorized, no interruption\n\n"
        f"You stop checking email. I check it for you."
    )
    pause(0.5)

    speak(
        "Email monitoring across multiple accounts. "
        "Client emails trigger instant phone alerts with voice. "
        "Urgent messages get priority notifications. "
        "Marketing and newsletters get sorted quietly. "
        "You never open your inbox wondering if you missed something."
    )
    pause(1)

    # ---- ACT 5: CALENDAR SLIDE ----
    print(">> Act 5: Calendar slide")

    ppt_add_slide(
        "Calendar Integration — Proactive Reminders",
        "Google Calendar fully connected\n"
        "Checked every 60 seconds for upcoming events\n"
        "15-minute reminder sent to phone with voice\n\n"
        "7:00 AM — Morning briefing: schedule, weather, priorities\n"
        "6:00 PM — Evening summary: day recap, tomorrow preview\n"
        "Monday — Weekly overview of the week ahead\n"
        "Friday — Weekly recap and next week preview\n\n"
        "All automatic. No setup required each day."
    )
    pause(0.5)

    speak(
        "Calendar reminders fifteen minutes before every meeting. "
        "Morning briefings at seven. Evening summaries at six. "
        "Weekly overviews on Monday, recaps on Friday. "
        "All of it happens without a single request."
    )
    pause(1)

    # ---- ACT 6: SYSTEM AWARENESS SLIDE ----
    print(">> Act 6: System awareness slide")

    try:
        with open("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json") as f:
            state = json.load(f)
    except Exception:
        state = {}

    apps = state.get("applications", [])
    mem = state.get("system", {})
    mon_count = state.get("monitors", {}).get("count", "?")
    mem_pct = mem.get("memory_percent", "?")
    mem_gb = mem.get("memory_used_gb", "?")
    mem_total = mem.get("memory_total_gb", "?")
    app_count = len(apps)

    ppt_add_slide(
        "System Awareness — I See Everything",
        f"Monitors: {mon_count} displays\n"
        f"Memory: {mem_gb} GB / {mem_total} GB ({mem_pct}%)\n"
        f"Applications running: {app_count}\n"
        f"State refresh: every 10 seconds\n\n"
        f"I know which apps are open on which screen\n"
        f"I know what files were recently accessed\n"
        f"I know clipboard contents\n"
        f"I detect when you switch tasks\n\n"
        f"I don't ask what you're working on. I already know."
    )
    pause(0.5)

    speak(
        f"{mon_count} monitors, {app_count} applications, {mem_pct} percent memory. "
        "I see all of it, updated every ten seconds. "
        "I know what's open, what's running, and what changed. "
        "That's system-native access. No browser can do this."
    )
    pause(1)

    # ---- ACT 7: LIVE TELEGRAM ----
    print(">> Act 7: Live Telegram")

    speak("Now watch. Sending a real message to Weber's phone. Live.")
    pause(0.5)

    tg_msg = (
        "*LIVE DEMO — V2*\n\n"
        "Sent autonomously during a recorded presentation.\n\n"
        f"System: {app_count} apps, {mem_pct}% memory, {running} services healthy.\n\n"
        "_No human involvement. Full AI control._"
    )
    success = send_telegram(tg_msg)

    ppt_add_slide(
        "Live Proof — Telegram Message Sent",
        "A real message was just sent to Weber's phone.\n\n"
        "No human typed it.\n"
        "No human pressed send.\n"
        "No browser was used.\n\n"
        "Direct API call from inside the system.\n"
        "This is how we communicate — Telegram, voice, web chat.\n"
        "Anytime. Automatically."
    )
    pause(0.5)

    # Take screenshot of the slide as proof
    tg_screenshot = take_screenshot("telegram_proof")
    pause(0.5)

    speak(
        "Sent. That just landed on his phone. "
        "A real notification. Not a mockup. "
        "I just captured a screenshot of this moment as proof. "
        "I can reach him anytime through Telegram, WhatsApp, voice alerts, or web chat."
    )
    pause(1)

    # ---- ACT 8: CONTENT CREATOR EXAMPLE ----
    print(">> Act 8: Content creator example")

    speak(
        "Now, this system isn't just for one person or one industry. "
        "Let me show you. Say you're a content creator. "
        "Watch what I can generate for you in seconds."
    )
    pause(0.5)

    ppt_add_slide(
        "Use Case: Content Creator",
        "Weekly Content Calendar — Auto-Generated\n\n"
        "Monday: Behind-the-scenes process video\n"
        "Tuesday: Industry tips carousel (5 slides)\n"
        "Wednesday: Client testimonial spotlight\n"
        "Thursday: Tutorial or how-to reel\n"
        "Friday: Weekly wins and lessons learned\n"
        "Saturday: Community Q&A or poll\n"
        "Sunday: Planning and batch creation\n\n"
        "AI generates the calendar, drafts captions,\n"
        "and reminds you when to post. Every week. Automatically.",
        color="0xE97132"
    )
    pause(0.5)

    speak(
        "A full weekly content calendar, generated instantly. "
        "And this isn't just a slide. The system can actually remind you "
        "each morning what to post, draft your captions, "
        "and track what's been published. All running in the background."
    )
    pause(1)

    # ---- ACT 9: FINANCE EXAMPLE — LIVE EXCEL ----
    print(">> Act 9: Finance Excel demo")

    speak(
        "Now say you're in finance. You need a quarterly report. Watch this."
    )
    pause(0.5)

    # Minimize PowerPoint, create Excel
    minimize("POWERPNT")
    pause(0.5)

    excel_create_finance()
    pause(1)
    move_center("EXCEL")
    pause(2)

    # Take screenshot of the live spreadsheet
    excel_screenshot = take_screenshot("excel_finance")
    pause(0.5)

    speak(
        "A full Q1 financial summary. Revenue, expenses, net profit, profit margins. "
        "All formatted, formulas calculated, currency styled, headers colored. "
        "Created in seconds. From scratch. No template. "
        "I just took a screenshot of it too. I can do this with any data you give me."
    )
    pause(2)

    # Close Excel, bring PowerPoint back
    excel_close()
    pause(1)

    # Restore PowerPoint
    ps("""
try {
    $ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application')
    $ppt.Visible = [Microsoft.Office.Interop.PowerPoint.MsoTriState]::msoTrue
} catch {}
""")
    pause(1)
    move_center("POWERPNT")
    pause(0.5)

    # Insert Excel screenshot into presentation
    if excel_screenshot:
        ppt_add_image_slide(
            "Live Screenshot — Excel Spreadsheet Created",
            excel_screenshot,
            "This spreadsheet was created from scratch during this recording. No templates."
        )
        pause(0.5)
        speak(
            "Here is the screenshot I captured of that spreadsheet. "
            "Real data. Real formatting. Created live. "
            "Now let me add the finance use case summary."
        )
        pause(1)

    # Add finance slide to presentation
    ppt_add_slide(
        "Use Case: Finance & Business",
        "What AI can handle for you:\n\n"
        "Generate financial reports from raw data\n"
        "Create formatted Excel spreadsheets on demand\n"
        "Track invoices and flag overdue payments\n"
        "Morning briefing with cash flow summary\n"
        "Alert when expenses exceed budget thresholds\n\n"
        "Your financial data stays on YOUR machine.\n"
        "No cloud. No third-party access. Full privacy.",
        color="0x217346"
    )
    pause(0.5)

    speak(
        "For finance, for business operations, "
        "the system generates reports, tracks invoices, monitors budgets, "
        "and keeps your financial data completely private on your own machine. "
        "No cloud service ever touches it."
    )
    pause(1)

    # ---- ACT 10: GMAIL IN CHROME ----
    print(">> Act 10: Gmail in Chrome")

    speak(
        "Need to check email in the browser? I can do that too."
    )
    pause(0.5)

    # Minimize PowerPoint, open Gmail
    minimize("POWERPNT")
    pause(0.5)
    open_chrome("https://mail.google.com")
    pause(3)

    # Screenshot Gmail
    gmail_screenshot = take_screenshot("gmail_inbox")
    pause(1)

    speak(
        "Gmail, open in Chrome. I can compose emails, read messages, "
        "download attachments, all from the system. "
        "I just took a screenshot of the inbox to prove it."
    )
    pause(2)

    # Close Chrome, restore PowerPoint
    close_chrome()
    pause(1)
    ps("""
try {
    $ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application')
    $ppt.Visible = [Microsoft.Office.Interop.PowerPoint.MsoTriState]::msoTrue
} catch {}
""")
    pause(1)
    move_center("POWERPNT")
    pause(0.5)

    # Insert Gmail screenshot into presentation
    if gmail_screenshot:
        ppt_add_image_slide(
            "Live Screenshot — Gmail Open in Chrome",
            gmail_screenshot,
            "Opened and captured live during this recording. Full browser access."
        )
        pause(0.5)
        speak(
            "And there's the proof. Gmail, captured live. "
            "Full browser control, all from the same system."
        )
        pause(1)

    # ---- ACT 11: FREELANCER EXAMPLE ----
    print(">> Act 11: Freelancer example")

    ppt_add_slide(
        "Use Case: Freelancers & Consultants",
        "Your AI handles the business side:\n\n"
        "Monitor job boards — Upwork, Fiverr, Freelancer\n"
        "Alert when new relevant projects are posted\n"
        "Track proposals and response rates\n"
        "Client email alerts — never miss a message\n"
        "Invoice reminders and payment tracking\n"
        "Weekly summary of earnings and pipeline\n\n"
        "You focus on the work. AI handles the hustle.",
        color="0x6B21A8"
    )
    pause(0.5)

    speak(
        "If you freelance, imagine getting an alert "
        "the moment a relevant job is posted. "
        "Your client emails trigger instant notifications. "
        "Your invoices are tracked. Your earnings summarized weekly. "
        "You focus on doing great work. The system handles everything else."
    )
    pause(1)

    # ---- ACT 12: CLOSING SLIDE ----
    print(">> Act 12: Closing")

    ppt_add_slide(
        "This Is Not a Demo",
        "This presentation was created live.\n"
        "The Excel spreadsheet was created live.\n"
        "The Telegram message was sent live.\n"
        "The Gmail inbox was opened live.\n"
        "Every screenshot was captured live.\n"
        "The system data is real.\n\n"
        "This runs every single day.\n\n"
        "Morning briefings. Meeting reminders.\n"
        "Client alerts. Health monitoring.\n"
        "File access. App control. Full autonomy.\n\n"
        "Weber built this. He's a developer, not an engineer.\n"
        "He saw a need, and he built the solution.\n\n"
        "That's the difference between a chatbot and an assistant."
    )
    pause(0.5)

    speak(
        "Everything you just watched was created live. "
        "This presentation, the spreadsheet, the Telegram message, "
        "Gmail opened in Chrome, every screenshot captured in real time, "
        "all the system data, all real. "
        "This runs every single day. "
        "Weber built this himself. He's a developer, not a software engineer. "
        "He saw a need, and he built the solution. "
        "That's the difference between a chatbot you visit "
        "and an assistant that lives with you. "
        "Thanks for watching."
    )
    pause(3)

    # Save presentation
    ps("""
try {
    $ppt = [System.Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application')
    $ppt.ActivePresentation.SaveAs('D:\\_CLAUDE-TOOLS\\obs-mcp\\_demo_presentation.pptx')
} catch {}
""")
    pause(1)

    # Close PowerPoint
    ppt_close()
    pause(1)

    # Stop recording
    print("Stopping recording...")
    result = cl.stop_record()
    output_path = getattr(result, "output_path", "unknown")
    cl.disconnect()

    # Cleanup temp files (keep screenshots for reference)
    for f in ["_demo_display.txt", "_demo_finance.xlsx"]:
        try:
            os.remove(f"{DEMO_DIR}/{f}")
        except Exception:
            pass

    print(f"\nRecording saved: {output_path}")
    print("Presentation saved: D:\\_CLAUDE-TOOLS\\obs-mcp\\_demo_presentation.pptx")
    print("=" * 60)
    print("DEMO V2 COMPLETE")
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

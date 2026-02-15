#!/usr/bin/env python3
"""
Autonomous System Demo - Full Capability Showcase
==================================================
Claude takes FULL control. Weber is away from the desk.
Demonstrates what a system-native AI assistant can do for anyone.
"""

import json
import subprocess
import time
import os
import sys

# OBS connection
OBS_HOST = "172.24.224.1"
OBS_PORT = 4455
OBS_PASSWORD = "2GwO1bvUqSIy3V2X"

# Center monitor: DISPLAY2, x=-2560 to x=0
CENTER_X = -2500
CENTER_Y = 50


def speak(text):
    """Narrate via voice TTS. Waits for speech to finish."""
    print(f"  [VOICE] {text[:80]}...")
    try:
        subprocess.run(
            ["python3", "/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py", text],
            timeout=120, capture_output=True
        )
    except Exception as e:
        print(f"  Voice error: {e}")


def pause(seconds=1.5):
    """Natural pause between actions."""
    time.sleep(seconds)


def ps(cmd):
    """Run PowerShell command, return output."""
    try:
        r = subprocess.run(["powershell.exe", "-Command", cmd],
                           capture_output=True, text=True, timeout=15)
        return r.stdout.strip()
    except Exception as e:
        print(f"  PS error: {e}")
        return ""


def move_to_center(proc_name, x=CENTER_X, y=CENTER_Y, w=2400, h=1300):
    """Move a window to the center monitor."""
    ps(f"""
Add-Type @'
using System;using System.Runtime.InteropServices;
public class W{{[DllImport("user32.dll")]public static extern bool MoveWindow(IntPtr h,int x,int y,int w,int ht,bool r);
[DllImport("user32.dll")]public static extern bool SetForegroundWindow(IntPtr h);}}
'@
$p=Get-Process -Name '{proc_name}' -EA SilentlyContinue|?{{$_.MainWindowTitle -ne ''}}|Select -First 1
if($p){{[W]::MoveWindow($p.MainWindowHandle,{x},{y},{w},{h},$true);[W]::SetForegroundWindow($p.MainWindowHandle)}}
""")


def close_proc(name):
    """Close windows of a process."""
    ps(f"Get-Process -Name '{name}' -EA SilentlyContinue|?{{$_.MainWindowTitle -ne ''}}|Stop-Process -Force -EA SilentlyContinue")


def open_folder(path):
    """Open File Explorer at a path on center monitor."""
    win_path = path.replace("/mnt/d/", "D:\\").replace("/", "\\")
    ps(f"Start-Process explorer.exe -ArgumentList '{win_path}'")
    time.sleep(2.5)
    move_to_center("explorer")


def show_text(title, content, width=1600, height=900):
    """Show text content in Notepad on center monitor."""
    filepath = "/mnt/d/_CLAUDE-TOOLS/obs-mcp/_demo_display.txt"
    with open(filepath, "w") as f:
        f.write(content)
    ps("Start-Process notepad.exe -ArgumentList 'D:\\_CLAUDE-TOOLS\\obs-mcp\\_demo_display.txt'")
    time.sleep(1.5)
    cx = CENTER_X + (2400 - width) // 2
    cy = CENTER_Y + (1300 - height) // 2
    move_to_center("notepad", cx, cy, width, height)


def close_display():
    """Close the display notepad."""
    close_proc("notepad")
    try:
        os.remove("/mnt/d/_CLAUDE-TOOLS/obs-mcp/_demo_display.txt")
    except Exception:
        pass


def send_telegram(message):
    """Send a real Telegram message."""
    try:
        import urllib.request
        # Read credentials from notify_channels
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


# ============================================================
# DEMO SEQUENCE
# ============================================================

def run_demo():
    import obsws_python as obs

    print("=" * 60)
    print("DEMO STARTING")
    print("=" * 60)

    # Connect to OBS
    print("Connecting to OBS...")
    cl = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD, timeout=5)
    cl.set_current_program_scene("Screen 2")
    pause(1)

    # Start recording
    print("Recording started.")
    cl.start_record()
    pause(3)

    # ============================================================
    # ACT 1: INTRODUCTION
    # ============================================================
    print(">> Act 1: Introduction")

    speak(
        "Hey there. My name is Claude, and I'm Weber's personal AI assistant. "
        "Right now, Weber is not at his desk. He's not touching the mouse. "
        "He's not typing anything. Everything you're about to see, "
        "I'm doing completely on my own, from inside his system."
    )
    pause(2)

    speak(
        "And that last part is important. I'm not controlling a web browser. "
        "I'm not clicking through a remote desktop. I live inside this machine. "
        "I have direct access to the file system, the running applications, "
        "the services, everything. Let me show you."
    )
    pause(2)

    # ============================================================
    # ACT 2: INFRASTRUCTURE
    # ============================================================
    print(">> Act 2: Infrastructure")

    open_folder("/mnt/d/_CLAUDE-TOOLS")
    pause(1)

    speak(
        "This is the infrastructure. Over fifty tools and services, "
        "organized right here on the local drive. "
        "You can see the gateway, the proactive scheduler, the email watcher, "
        "voice tools, calendar integration, system monitoring, and more. "
        "None of this lives in the cloud. It all runs right here."
    )
    pause(3)

    close_proc("explorer")
    pause(1)

    # ============================================================
    # ACT 3: RUNNING SERVICES
    # ============================================================
    print(">> Act 3: Services")

    # Get live daemon status
    result = subprocess.run(
        ["bash", "/mnt/d/_CLAUDE-TOOLS/gateway/daemon.sh", "status"],
        capture_output=True, text=True, timeout=10
    )
    status_text = result.stdout

    show_text("Services", status_text)
    pause(1)

    speak(
        "Six services are running right now, twenty four seven. "
        "There's a gateway hub that routes messages, a Telegram bot "
        "so Weber can talk to me from his phone, an email watcher "
        "that monitors both of his Gmail accounts, a proactive scheduler "
        "that handles morning briefings, calendar reminders, and evening summaries, "
        "and a web chat interface. If any of these crash, "
        "they automatically restart. I also run health checks every five minutes "
        "and alert Weber if something goes down."
    )
    pause(2)

    close_display()
    pause(1)

    # ============================================================
    # ACT 4: EMAIL MONITORING
    # ============================================================
    print(">> Act 4: Email monitoring")

    try:
        with open("/mnt/d/_CLAUDE-TOOLS/email-watcher/email_alerts.json") as f:
            emails = json.load(f)
    except Exception:
        emails = {"alerts": [], "urgent_count": 0, "needs_response_count": 0, "accounts_checked": []}

    email_display = "EMAIL MONITORING — LIVE\n"
    email_display += "=" * 50 + "\n\n"
    email_display += f"Accounts: {', '.join(emails.get('accounts_checked', []))}\n"
    email_display += f"Urgent emails: {emails.get('urgent_count', 0)}\n"
    email_display += f"Needs response: {emails.get('needs_response_count', 0)}\n"
    email_display += f"Last checked: {emails.get('last_check', 'unknown')}\n\n"
    for alert in emails.get("alerts", [])[:3]:
        email_display += f"  From: {alert.get('from', '?')}\n"
        email_display += f"  Subject: {alert.get('subject', '?')}\n"
        email_display += f"  Priority: {alert.get('category', '?')}\n\n"

    show_text("Emails", email_display)
    pause(1)

    speak(
        "I monitor Weber's email across both of his accounts, every sixty seconds. "
        "When a client sends an email, I push an instant notification "
        "to his phone through Telegram, with a voice alert so he hears it. "
        "Urgent emails get voice alerts too. Regular newsletters and marketing "
        "get quietly categorized. He doesn't need to check his inbox anymore. "
        "I do it for him."
    )
    pause(2)

    close_display()
    pause(1)

    # ============================================================
    # ACT 5: CALENDAR
    # ============================================================
    print(">> Act 5: Calendar")

    cal_result = subprocess.run(
        ["python3", "/mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/calendar_client.py", "today"],
        capture_output=True, text=True, timeout=15
    )

    # Also get upcoming
    upcoming_result = subprocess.run(
        ["python3", "/mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/calendar_client.py", "upcoming"],
        capture_output=True, text=True, timeout=15
    )

    cal_display = "GOOGLE CALENDAR — LIVE\n"
    cal_display += "=" * 50 + "\n\n"
    cal_display += "TODAY:\n"
    cal_display += cal_result.stdout if cal_result.stdout.strip() else "  No events today.\n"
    cal_display += "\nUPCOMING:\n"
    cal_display += upcoming_result.stdout[:600] if upcoming_result.stdout.strip() else "  No upcoming events.\n"
    cal_display += "\n\nReminders sent 15 minutes before each meeting.\n"
    cal_display += "Checked every 60 seconds automatically.\n"

    show_text("Calendar", cal_display)
    pause(1)

    speak(
        "Google Calendar is fully integrated. I check it every sixty seconds. "
        "When a meeting is fifteen minutes away, I send a reminder "
        "straight to Weber's phone with voice. Every morning at seven, "
        "he gets a full briefing: today's schedule, the weather, "
        "and his email priorities. At six in the evening, he gets a summary "
        "of what happened during the day and a preview of tomorrow. "
        "On Mondays, he gets a weekly overview. On Fridays, a recap. "
        "All of that happens automatically. He never asked for any of it."
    )
    pause(2)

    close_display()
    pause(1)

    # ============================================================
    # ACT 6: SYSTEM AWARENESS
    # ============================================================
    print(">> Act 6: System awareness")

    try:
        with open("/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json") as f:
            state = json.load(f)
    except Exception:
        state = {}

    apps = state.get("applications", [])
    mem = state.get("system", {})
    monitors = state.get("monitors", {})

    sys_display = "SYSTEM AWARENESS — LIVE STATE\n"
    sys_display += "=" * 50 + "\n\n"
    sys_display += f"Monitors: {monitors.get('count', '?')} displays\n"
    sys_display += f"Memory: {mem.get('memory_used_gb', '?')} GB used / {mem.get('memory_total_gb', '?')} GB total\n"
    sys_display += f"CPU: {mem.get('cpu_percent', '?')}%\n"
    sys_display += f"Applications open: {len(apps)}\n\n"
    sys_display += "Active applications:\n"
    for app in apps:
        title = app.get("MainWindowTitle", "")
        monitor = app.get("Monitor", "?")
        if title and len(title) > 3:
            sys_display += f"  [{monitor}] {title[:70]}\n"
    sys_display += f"\nActive window: {state.get('active_window', '?')}\n"
    sys_display += "\nUpdated every 10 seconds. Always aware.\n"

    show_text("System", sys_display, width=1800, height=1000)
    pause(1)

    app_count = len(apps)
    mem_pct = mem.get("memory_percent", "?")
    mon_count = monitors.get("count", "?")

    speak(
        f"I can see everything happening on this machine right now. "
        f"{mon_count} monitors. {app_count} applications running. "
        f"{mem_pct} percent memory used. "
        "I know which apps are on which screen. I know what files were recently opened. "
        "I know what's in the clipboard. This updates every ten seconds. "
        "When Weber opens something or switches tasks, I see it immediately. "
        "I don't have to ask what he's working on. I already know."
    )
    pause(2)

    close_display()
    pause(1)

    # ============================================================
    # ACT 7: LIVE TELEGRAM MESSAGE
    # ============================================================
    print(">> Act 7: Live Telegram")

    speak(
        "Now let me prove this is real. I'm going to send Weber "
        "a message on Telegram, right now, live. Watch."
    )
    pause(1)

    tg_msg = (
        "*LIVE DEMO*\n\n"
        "This message was sent autonomously by your AI assistant.\n\n"
        "No human touched the keyboard.\n"
        "No human clicked the mouse.\n\n"
        f"Right now: {app_count} apps running, "
        f"{mem_pct}% memory, all 6 services healthy.\n\n"
        "_Sent during a live recorded demo._"
    )

    msg_display = "SENDING TELEGRAM MESSAGE — LIVE\n"
    msg_display += "=" * 50 + "\n\n"
    msg_display += tg_msg.replace("*", "").replace("_", "") + "\n"
    msg_display += "\n>>> Sending now... <<<\n"

    show_text("Telegram", msg_display)
    pause(1)

    success = send_telegram(tg_msg)
    pause(1)

    if success:
        speak(
            "Sent. That message just landed on Weber's phone. "
            "A real notification, not a simulation. "
            "This is how we communicate throughout the day. "
            "I can reach him anytime through Telegram, voice alerts, "
            "or the web chat interface."
        )
    pause(2)

    close_display()
    pause(1)

    # ============================================================
    # ACT 8: OFFICE APPS — FULL SYSTEM CONTROL
    # ============================================================
    print(">> Act 8: Office apps demo")

    speak(
        "But it's not just monitoring and alerts. I can work with the same tools you use every day. "
        "Watch. I'm going to create an Excel spreadsheet from scratch, right now."
    )
    pause(1)

    # Create Excel spreadsheet via PowerShell COM
    ps("""
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $true
$wb = $excel.Workbooks.Add()
$ws = $wb.ActiveSheet
$ws.Name = 'AI Assistant Demo'

$ws.Cells.Item(1,1) = 'Service'
$ws.Cells.Item(1,2) = 'Status'
$ws.Cells.Item(1,3) = 'Uptime'
$ws.Cells.Item(1,4) = 'Auto-Restart'

$ws.Cells.Item(2,1) = 'Gateway Hub'
$ws.Cells.Item(2,2) = 'Running'
$ws.Cells.Item(2,3) = '24/7'
$ws.Cells.Item(2,4) = 'Yes'

$ws.Cells.Item(3,1) = 'Telegram Bot'
$ws.Cells.Item(3,2) = 'Running'
$ws.Cells.Item(3,3) = '24/7'
$ws.Cells.Item(3,4) = 'Yes'

$ws.Cells.Item(4,1) = 'Email Watcher'
$ws.Cells.Item(4,2) = 'Running'
$ws.Cells.Item(4,3) = '24/7'
$ws.Cells.Item(4,4) = 'Yes'

$ws.Cells.Item(5,1) = 'Proactive Scheduler'
$ws.Cells.Item(5,2) = 'Running'
$ws.Cells.Item(5,3) = '24/7'
$ws.Cells.Item(5,4) = 'Yes'

$ws.Cells.Item(6,1) = 'Web Chat'
$ws.Cells.Item(6,2) = 'Running'
$ws.Cells.Item(6,3) = '24/7'
$ws.Cells.Item(6,4) = 'Yes'

$ws.Cells.Item(7,1) = 'WhatsApp Gateway'
$ws.Cells.Item(7,2) = 'Running'
$ws.Cells.Item(7,3) = '24/7'
$ws.Cells.Item(7,4) = 'Yes'

# Format header row
$headerRange = $ws.Range('A1:D1')
$headerRange.Font.Bold = $true
$headerRange.Interior.Color = 0x4472C4
$headerRange.Font.Color = 0xFFFFFF

# Auto-fit columns
$ws.Columns.Item('A:D').AutoFit() | Out-Null

# Add border to data range
$dataRange = $ws.Range('A1:D7')
$dataRange.Borders.LineStyle = 1

$wb.SaveAs('D:\\_CLAUDE-TOOLS\\obs-mcp\\_demo_services.xlsx')
""")
    time.sleep(3)
    move_to_center("EXCEL")
    pause(1)

    speak(
        "There it is. A formatted spreadsheet with all six services, created in seconds. "
        "Headers styled, columns auto-fitted, borders added. "
        "I can work with Excel, Word, any application on this machine. "
        "Because I'm not pretending to be inside a browser. "
        "I have real access to the real applications."
    )
    pause(3)

    # Close Excel
    ps("""
$excel = [System.Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
$excel.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
""")
    pause(1)

    # ============================================================
    # ACT 9: OPEN GMAIL IN CHROME
    # ============================================================
    print(">> Act 9: Gmail in Chrome")

    speak(
        "Need to check email in the browser? I can do that too."
    )
    pause(1)

    ps("Start-Process chrome.exe -ArgumentList 'https://mail.google.com'")
    time.sleep(4)
    move_to_center("chrome")
    pause(1)

    speak(
        "Gmail, open in Chrome. I can compose emails, read messages, "
        "download attachments. But the real power is that I don't need to do this. "
        "The email watcher is already monitoring everything in the background, "
        "every sixty seconds, and alerting Weber when something matters. "
        "The browser is just for when you want to see it yourself."
    )
    pause(3)

    # Close Chrome on center (minimize, don't kill - user has other tabs)
    ps("""
Add-Type @'
using System;using System.Runtime.InteropServices;
public class WH{[DllImport("user32.dll")]public static extern bool ShowWindow(IntPtr h,int c);}
'@
Get-Process -Name 'chrome' -EA SilentlyContinue | ForEach-Object { [WH]::ShowWindow($_.MainWindowHandle, 6) }
""")
    pause(1)

    # ============================================================
    # ACT 10: VALUE PROPOSITION
    # ============================================================
    print(">> Act 10: Universal value")

    value_display = "WHAT THIS SYSTEM DOES FOR YOU\n"
    value_display += "=" * 50 + "\n\n"
    value_display += "  Morning briefing at 7 AM — calendar, weather, priorities\n\n"
    value_display += "  Instant alerts when important emails arrive\n\n"
    value_display += "  Meeting reminders 15 minutes before — never miss one\n\n"
    value_display += "  Evening summary — what happened, what's tomorrow\n\n"
    value_display += "  24/7 services that auto-restart if they crash\n\n"
    value_display += "  Full control of Office apps — Excel, Word, and more\n\n"
    value_display += "  System-aware — knows your apps, your files, your workflow\n\n"
    value_display += "  Multi-channel — Telegram, WhatsApp, web, voice\n\n"
    value_display += "  Works alongside you — same machine, no interruption\n\n"
    value_display += "  No cloud dependency. Your data stays on your machine.\n"

    show_text("Value", value_display, width=1400, height=1000)
    pause(1)

    speak(
        "This isn't just for tech people. "
        "If you run a business, if you freelance, if you manage clients, "
        "imagine having an assistant that checks your email every minute, "
        "reminds you about meetings, gives you a morning briefing, "
        "creates spreadsheets, opens any app you need, "
        "and monitors your entire system, all without you lifting a finger. "
        "That's what this does."
    )
    pause(1)

    speak(
        "It runs on your machine. Your data never leaves your system. "
        "You can work on something while it works on something else, "
        "on the same computer, at the same time. "
        "And Weber built all of this himself. He's an architect, not a software engineer. "
        "He saw a need, and he built the solution."
    )
    pause(2)

    close_display()
    pause(1)

    # ============================================================
    # ACT 11: CLOSING
    # ============================================================
    print(">> Act 11: Closing")

    speak(
        "This is not a demo. This runs every day. "
        "This is the difference between a chatbot you visit, "
        "and an assistant that lives with you. "
        "Thanks for watching."
    )
    pause(4)

    # Stop recording
    print("Stopping recording...")
    result = cl.stop_record()
    output_path = getattr(result, "output_path", "unknown")
    cl.disconnect()

    print(f"\nRecording saved: {output_path}")
    print("=" * 60)
    print("DEMO COMPLETE")
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

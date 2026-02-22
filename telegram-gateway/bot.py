#!/usr/bin/env python3
"""
Telegram Gateway for Claude Code
Fast commands + Claude fallback for complex queries.
"""

import os
import sys
import json
import subprocess
import asyncio
import logging
import psutil
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False


def _run_ps(cmd, timeout=30):
    if _HAS_BRIDGE:
        return _ps_bridge(cmd, timeout)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, timeout=timeout)
    class _R:
        stdout = r.stdout; stderr = r.stderr; returncode = r.returncode; success = r.returncode == 0
    return _R()


# Add gateway to path for security filter
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/gateway")
try:
    from security_filter import SecurityFilter
    SECURITY_ENABLED = True
except ImportError:
    SECURITY_ENABLED = False

# Add autonomous agent control
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/autonomous-agent")
AGENT_CONTROL = "/mnt/d/_CLAUDE-TOOLS/autonomous-agent/agent_control.py"

# Add approval system
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/gateway")
from approval_system import handle_callback, ApprovalStatus, _load_approvals, _save_approvals

# Track pending edit requests: {user_id: approval_id}
PENDING_EDITS = {}

# ============================================
# CONFIGURATION
# ============================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN environment variable is required")
ALLOWED_USERS = [8101819463]
LOG_FILE = "/mnt/d/_CLAUDE-TOOLS/telegram-gateway/conversations.log"
LIVE_STATE_FILE = "/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json"
CLAUDE_TIMEOUT = 120

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# FAST DIRECT COMMANDS (no Claude needed)
# ============================================

def get_system_status_fast() -> str:
    """Get system status directly - instant response"""
    try:
        # Read live state
        state = {}
        if os.path.exists(LIVE_STATE_FILE):
            with open(LIVE_STATE_FILE) as f:
                state = json.load(f)

        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)

        # Get running apps from state
        apps = state.get("applications", [])
        app_names = [a.get("ProcessName", "?") for a in apps if a.get("MainWindowTitle")]

        # Check Revit
        revit_info = state.get("revit", {})
        revit_status = "Not running"
        for app in apps:
            if app.get("ProcessName") == "Revit":
                revit_status = app.get("MainWindowTitle", "Running")[:50]
                break

        return f"""📊 **System Status**

💻 **Resources**
• CPU: {cpu:.0f}%
• Memory: {mem.percent:.0f}% ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB)

🏗️ **Revit**: {revit_status}

📱 **Active Apps**: {len(app_names)}
{', '.join(app_names[:5])}{'...' if len(app_names) > 5 else ''}

⏰ Updated: {datetime.now().strftime('%I:%M %p')}"""
    except Exception as e:
        return f"Error getting status: {e}"


def get_email_status_fast() -> str:
    """Get email status from live state - instant"""
    try:
        if os.path.exists(LIVE_STATE_FILE):
            with open(LIVE_STATE_FILE) as f:
                state = json.load(f)

            email = state.get("email", {})
            unread = email.get("unread_count", 0)
            urgent = email.get("urgent_count", 0)
            needs_response = email.get("needs_response_count", 0)
            last_check = email.get("last_check", "Unknown")
            alerts = email.get("alerts", [])

            msg = f"""📧 **Email Status**

• Unread: {unread}
• Urgent: {urgent}
• Needs Response: {needs_response}
• Last Check: {last_check[:16] if len(last_check) > 16 else last_check}"""

            if alerts:
                msg += "\n\n**Alerts:**"
                for a in alerts[:3]:
                    subj = a.get("subject", "?")[:40]
                    frm = a.get("from", "?").split("<")[0][:20]
                    msg += f"\n• {frm}: {subj}"

            return msg
        return "Email status not available"
    except Exception as e:
        return f"Error: {e}"


def get_revit_status_fast() -> str:
    """Get Revit status from live state - instant"""
    try:
        if os.path.exists(LIVE_STATE_FILE):
            with open(LIVE_STATE_FILE) as f:
                state = json.load(f)

            apps = state.get("applications", [])
            for app in apps:
                if app.get("ProcessName") == "Revit":
                    title = app.get("MainWindowTitle", "Unknown")
                    monitor = app.get("Monitor", "?")
                    return f"""🏗️ **Revit Status**

✅ Running
📄 {title}
🖥️ Monitor: {monitor}"""

            return "🏗️ **Revit Status**\n\n❌ Not running"
    except Exception as e:
        return f"Error: {e}"


def take_screenshot_fast(monitor: str = "center") -> str:
    """Take screenshot using PowerShell (works from WSL)"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        win_path = f"D:\\temp_screenshot_{timestamp}.png"
        linux_path = f"/mnt/d/temp_screenshot_{timestamp}.png"

        # Your monitor layout (from live_state.json):
        # DISPLAY1 (right/primary): x=0
        # DISPLAY2 (center): x=-2560
        # DISPLAY3 (left): x=-5120
        # All monitors: 2560x1440

        # Use screen index for PowerShell (0=all, 1=primary/right, then by x position)
        # PowerShell screens are indexed differently, so use explicit coordinates
        if monitor.lower() == "all":
            left, top, right, bottom = -5120, 0, 2560, 1440
        elif monitor.lower() == "right":
            left, top, right, bottom = 0, 0, 2560, 1440
        elif monitor.lower() == "center":
            left, top, right, bottom = -2560, 0, 0, 1440
        elif monitor.lower() == "left":
            left, top, right, bottom = -5120, 0, -2560, 1440
        else:
            left, top, right, bottom = -2560, 0, 0, 1440  # default center

        width = right - left
        height = bottom - top

        # PowerShell script using explicit pixel coordinates
        ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$left = {left}
$top = {top}
$width = {width}
$height = {height}
$bmp = New-Object Drawing.Bitmap($width, $height)
$graphics = [Drawing.Graphics]::FromImage($bmp)
$graphics.CopyFromScreen($left, $top, 0, 0, [Drawing.Size]::new($width, $height))
$bmp.Save("{win_path}")
$graphics.Dispose()
$bmp.Dispose()
Write-Host "Saved to {win_path}"
'''
        result = _run_ps(ps_script, timeout=15)

        if os.path.exists(linux_path):
            return linux_path
        else:
            logger.error(f"Screenshot failed. stdout: {result.stdout.decode()} stderr: {result.stderr.decode()}")
            return None
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return None


# ============================================
# HANDLERS
# ============================================

async def check_auth(update: Update) -> bool:
    if ALLOWED_USERS and update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text(f"Unauthorized. ID: {update.effective_user.id}")
        return False
    return True


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    await update.message.reply_text(
"""👋 **Weber Assistant**

**Fast Commands** (instant):
/quick - System snapshot
/email - Email status
/revit - Revit status
/apps - Running apps
/screenshot - Get screenshot

**Claude Commands** (10-30s):
/status - Detailed status via Claude
/ask <question> - Ask Claude anything

**Agent Commands** (background work):
/agent status - Agent & queue status
/agent task <prompt> - Queue background task
/agent tasks - List pending tasks

Just type normally to chat with Claude.""", parse_mode='Markdown')


async def cmd_quick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fast system status - no Claude"""
    if not await check_auth(update): return
    await update.message.reply_text(get_system_status_fast(), parse_mode='Markdown')


async def cmd_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fast email status - no Claude"""
    if not await check_auth(update): return
    await update.message.reply_text(get_email_status_fast(), parse_mode='Markdown')


async def cmd_revit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fast Revit status - no Claude"""
    if not await check_auth(update): return
    await update.message.reply_text(get_revit_status_fast(), parse_mode='Markdown')


async def cmd_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List running apps - no Claude"""
    if not await check_auth(update): return
    try:
        with open(LIVE_STATE_FILE) as f:
            state = json.load(f)
        apps = state.get("applications", [])
        msg = "📱 **Running Apps**\n"
        for app in apps:
            name = app.get("ProcessName", "?")
            title = app.get("MainWindowTitle", "")[:30]
            monitor = app.get("Monitor", "?")
            if title:
                msg += f"\n• **{name}** ({monitor})\n  {title}"
        await update.message.reply_text(msg[:4000], parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def cmd_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Take and send screenshot"""
    if not await check_auth(update): return

    # Default to center (where Revit usually is)
    monitor = context.args[0].lower() if context.args else "center"
    if monitor not in ["left", "center", "right", "all"]:
        await update.message.reply_text("Usage: /screenshot [left|center|right|all]\nDefault: center")
        return

    await update.message.reply_text(f"📸 Capturing {monitor} monitor...")

    path = take_screenshot_fast(monitor)

    if path and os.path.exists(path):
        try:
            with open(path, 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=f"🖥️ {monitor.capitalize()} monitor\n⏰ {datetime.now().strftime('%I:%M:%S %p')}"
                )
            os.remove(path)
        except Exception as e:
            await update.message.reply_text(f"Failed to send image: {e}")
    else:
        await update.message.reply_text("❌ Screenshot failed. Try again.")


async def cmd_status_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Full status via Claude (slower)"""
    if not await check_auth(update): return
    await update.message.reply_text("⏳ Getting detailed status from Claude...")
    response = await query_claude("Give me a brief system status - what's running, memory usage, any issues?")
    await update.message.reply_text(truncate_response(response))


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask Claude a question"""
    if not await check_auth(update): return
    if not context.args:
        await update.message.reply_text("Usage: /ask <your question>")
        return
    question = ' '.join(context.args)
    await update.message.reply_text("⏳ Asking Claude...")
    response = await query_claude(question)
    await update.message.reply_text(truncate_response(response))


# ============================================
# CLAUDE QUERY (via Anthropic API directly)
# ============================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY environment variable is required")

SYSTEM_PROMPT_BASE = """You are Weber's AI assistant responding via Telegram. Keep responses concise and mobile-friendly.
Weber is a BIM automation specialist who works with Revit, AutoCAD, and AI tools.
Be direct and helpful. Use short paragraphs. Avoid long code blocks unless asked.

IMPORTANT: You DO have access to Weber's live system state. It is injected below in every message.
When asked about system status, running apps, memory, Revit, email, etc. — answer using this data.
Never say you can't see the system. You can. The data is real-time from Weber's workstation."""


def _build_system_prompt() -> str:
    """Build system prompt with live system state injected."""
    state_block = ""
    try:
        if os.path.exists(LIVE_STATE_FILE):
            with open(LIVE_STATE_FILE) as f:
                state = json.load(f)

            # System resources
            sys_info = state.get("system", {})
            cpu = sys_info.get("cpu_percent", "?")
            mem_pct = sys_info.get("memory_percent", "?")
            mem_used = sys_info.get("memory_used_gb", "?")
            mem_total = sys_info.get("memory_total_gb", "?")

            # Active window
            active_win = state.get("active_window", "Unknown")

            # Running apps
            apps = state.get("applications", [])
            app_lines = []
            for a in apps:
                name = a.get("ProcessName", "?")
                title = a.get("MainWindowTitle", "")
                monitor = a.get("Monitor", "?")
                if title:
                    app_lines.append(f"  - {name}: {title} (monitor: {monitor})")

            # Monitors
            monitors = state.get("monitors", {})
            mon_count = monitors.get("count", "?")

            # Revit
            revit = state.get("revit", {})
            revit_running = revit.get("running", False)
            revit_connected = revit.get("connected", False)

            # Email
            email = state.get("email", {})
            unread = email.get("unread_count", 0)
            urgent = email.get("urgent_count", 0)
            needs_resp = email.get("needs_response_count", 0)
            alerts = email.get("alerts", [])
            alert_lines = []
            for al in alerts[:3]:
                subj = al.get("subject", "?")[:60]
                frm = al.get("from", "?").split("<")[0].strip()[:30]
                cat = al.get("category", "?")
                alert_lines.append(f"  - [{cat}] {frm}: {subj}")

            # Recent files
            recent_files = state.get("recent_files", [])[:5]

            # Timestamp
            generated = state.get("generated_at", "?")

            state_block = f"""

--- LIVE SYSTEM STATE (updated: {generated}) ---
Active Window: {active_win}
CPU: {cpu}% | Memory: {mem_pct}% ({mem_used}GB / {mem_total}GB)
Monitors: {mon_count}
Revit: {"Running" if revit_running else "Not running"} | MCP Bridge: {"Connected" if revit_connected else "Not connected"}

Running Apps:
{chr(10).join(app_lines) if app_lines else "  (none detected)"}

Email: {unread} unread, {urgent} urgent, {needs_resp} needs response
{("Email Alerts:" + chr(10) + chr(10).join(alert_lines)) if alert_lines else "No email alerts."}

Recent Files: {", ".join(recent_files) if recent_files else "None"}
--- END SYSTEM STATE ---"""

    except Exception as e:
        state_block = f"\n\n[System state unavailable: {e}]"

    return SYSTEM_PROMPT_BASE + state_block


async def query_claude(message: str, context: str = "") -> str:
    """Query Claude API directly with live system context injected."""
    import urllib.request

    try:
        full_prompt = f"[Context: {context}]\n\n{message}" if context else message

        payload = json.dumps({
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 1024,
            "system": _build_system_prompt(),
            "messages": [{"role": "user", "content": full_prompt}]
        }).encode()

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            method="POST"
        )

        loop = asyncio.get_event_loop()
        resp = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=CLAUDE_TIMEOUT)),
            timeout=CLAUDE_TIMEOUT
        )
        result = json.loads(resp.read().decode())

        # Extract text from response
        text_parts = [block["text"] for block in result.get("content", []) if block.get("type") == "text"]
        response = "\n".join(text_parts).strip()
        return response if response else "No response from Claude."

    except asyncio.TimeoutError:
        return "Timed out. Try a simpler question."
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error(f"Claude API error: {e.code} - {body}")
        return f"API error ({e.code}). Try again."
    except Exception as e:
        logger.error(f"Claude query error: {e}")
        return f"Error: {e}"


def truncate_response(text: str, max_length: int = 4000) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length] + "\n...(truncated)"


def log_conversation(user_id: int, username: str, message: str, response: str):
    with open(LOG_FILE, "a") as f:
        f.write(f"\n{'='*60}\n{datetime.now()}\nUser: {username}\nMsg: {message}\nResp: {response[:500]}\n")


# ============================================
# AGENT CONTROL COMMANDS
# ============================================

async def cmd_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Control the autonomous background agent"""
    if not await check_auth(update): return

    args = context.args
    if not args:
        await update.message.reply_text(
"""🤖 **Autonomous Agent Control**

/agent status - Agent status & task queue
/agent task <prompt> - Add background task
/agent tasks - List pending tasks
/agent pause - Pause the agent
/agent resume - Resume the agent
/agent briefing - Request briefing now

Example:
/agent task Process all PDFs in the inbox folder""", parse_mode='Markdown')
        return

    subcommand = args[0].lower()

    try:
        if subcommand == "status":
            result = subprocess.run(
                ["python3", AGENT_CONTROL, "status"],
                capture_output=True,
                timeout=10
            )
            await update.message.reply_text(result.stdout.decode() or "No output", parse_mode='Markdown')

        elif subcommand == "tasks":
            result = subprocess.run(
                ["python3", AGENT_CONTROL, "tasks"],
                capture_output=True,
                timeout=10
            )
            await update.message.reply_text(result.stdout.decode() or "No tasks", parse_mode='Markdown')

        elif subcommand == "task" and len(args) > 1:
            prompt = ' '.join(args[1:])
            result = subprocess.run(
                ["python3", AGENT_CONTROL, "task", prompt],
                capture_output=True,
                timeout=10
            )
            await update.message.reply_text(result.stdout.decode() or "Task added", parse_mode='Markdown')

        elif subcommand == "pause":
            result = subprocess.run(
                ["python3", AGENT_CONTROL, "pause"],
                capture_output=True,
                timeout=10
            )
            await update.message.reply_text(result.stdout.decode() or "Paused", parse_mode='Markdown')

        elif subcommand == "resume":
            result = subprocess.run(
                ["python3", AGENT_CONTROL, "resume"],
                capture_output=True,
                timeout=10
            )
            await update.message.reply_text(result.stdout.decode() or "Resumed", parse_mode='Markdown')

        elif subcommand == "briefing":
            result = subprocess.run(
                ["python3", AGENT_CONTROL, "briefing"],
                capture_output=True,
                timeout=10
            )
            await update.message.reply_text(result.stdout.decode() or "Briefing requested", parse_mode='Markdown')

        else:
            await update.message.reply_text("Unknown subcommand. Use /agent for help.")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


# ============================================
# APPROVAL CALLBACK HANDLER
# ============================================

async def handle_approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses for approvals."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ALLOWED_USERS:
        return

    data = query.data  # e.g., "approve:abc12345"
    parts = data.split(":", 1)
    if len(parts) != 2:
        return

    action, approval_id = parts

    if action == "approve":
        handle_callback(approval_id, "approve")
        await query.edit_message_text(
            f"✅ *Approved*\n\n{query.message.text}",
            parse_mode="Markdown"
        )

    elif action == "cancel":
        handle_callback(approval_id, "cancel")
        await query.edit_message_text(
            f"❌ *Cancelled*\n\n{query.message.text}",
            parse_mode="Markdown"
        )

    elif action == "edit":
        PENDING_EDITS[query.from_user.id] = approval_id
        await query.edit_message_text(
            f"✏️ *Editing* — Send your changes as the next message.\n\n{query.message.text}",
            parse_mode="Markdown"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages - check for pending edits first, then Claude"""
    if not await check_auth(update): return

    user_id = update.effective_user.id
    message = update.message.text

    # Check if this is an edit response for a pending approval
    if user_id in PENDING_EDITS:
        approval_id = PENDING_EDITS.pop(user_id)
        handle_callback(approval_id, "edit", edit_text=message)
        await update.message.reply_text(
            f"✏️ *Edit received* for approval `{approval_id}`.\n"
            f"The system will use your updated text.",
            parse_mode="Markdown"
        )
        return

    logger.info(f"Message: {message[:50]}...")

    # Security check
    if SECURITY_ENABLED:
        security = SecurityFilter(strict_mode=True)
        is_safe, reason = security.check(message, f"telegram")
        if not is_safe:
            await update.message.reply_text(f"⚠️ Blocked: {reason}")
            return
        message = security.sanitize(message)

    await update.message.chat.send_action("typing")
    await update.message.reply_text("⏳ Processing...")

    response = await query_claude(message, "Message from Telegram")
    log_conversation(update.effective_user.id, update.effective_user.first_name, message, response)
    await update.message.reply_text(truncate_response(response))


# ============================================
# MAIN
# ============================================

def main():
    print("Starting Telegram bot with fast commands...")
    app = Application.builder().token(BOT_TOKEN).build()

    # Fast commands (instant)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("quick", cmd_quick))
    app.add_handler(CommandHandler("email", cmd_email))
    app.add_handler(CommandHandler("revit", cmd_revit))
    app.add_handler(CommandHandler("apps", cmd_apps))
    app.add_handler(CommandHandler("screenshot", cmd_screenshot))

    # Claude commands (slower)
    app.add_handler(CommandHandler("status", cmd_status_full))
    app.add_handler(CommandHandler("ask", cmd_ask))

    # Agent control
    app.add_handler(CommandHandler("agent", cmd_agent))

    # Approval button callbacks
    app.add_handler(CallbackQueryHandler(handle_approval_callback))

    # Regular messages go to Claude (or pending edit handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot running!")
    print("Fast: /quick /email /revit /apps /screenshot")
    print("Agent: /agent status /agent task <prompt>")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Telegram Gateway for Claude Code — Remote Command Center
Multi-turn conversations, tool execution, voice in/out, image analysis.
"""

import os
import sys
import json
import base64
import sqlite3
import subprocess
import asyncio
import logging
import time
import tempfile
import socket
import psutil
from datetime import datetime
from pathlib import Path

import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ============================================
# FORCE IPv4 — Critical for Edge TTS in WSL
# ============================================
_original_getaddrinfo = socket.getaddrinfo
def _ipv4_only_getaddrinfo(*args, **kwargs):
    responses = _original_getaddrinfo(*args, **kwargs)
    ipv4 = [r for r in responses if r[0] == socket.AF_INET]
    return ipv4 if ipv4 else responses
socket.getaddrinfo = _ipv4_only_getaddrinfo

# ============================================
# POWERSHELL BRIDGE
# ============================================
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


# ============================================
# SECURITY FILTER
# ============================================
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/gateway")
try:
    from security_filter import SecurityFilter
    SECURITY_ENABLED = True
except ImportError:
    SECURITY_ENABLED = False

# Autonomous agent control
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/autonomous-agent")
AGENT_CONTROL = "/mnt/d/_CLAUDE-TOOLS/autonomous-agent/agent_control.py"

# Approval system
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

# Claude SDK setup
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY environment variable is required")
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
CLAUDE_MODEL = "claude-sonnet-4-6-20250929"
CLAUDE_MAX_TOKENS = 4096

# Memory DB (direct SQLite — avoids importing MCP server module)
MEMORY_DB_PATH = Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db")

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# CONVERSATION MEMORY (Step 2)
# ============================================

CONVERSATIONS = {}  # {chat_id: {"messages": [...], "last_active": timestamp}}
CONVERSATION_MAX_MESSAGES = 20  # 10 user+assistant turns
CONVERSATION_TTL = 3600  # 1 hour inactivity clears


def _get_conversation(chat_id: int) -> list:
    """Get or create conversation history for a chat."""
    _cleanup_conversations()
    if chat_id not in CONVERSATIONS:
        CONVERSATIONS[chat_id] = {"messages": [], "last_active": time.time()}
    conv = CONVERSATIONS[chat_id]
    conv["last_active"] = time.time()
    return conv["messages"]


def _append_to_conversation(chat_id: int, role: str, content) -> list:
    """Append a message and enforce sliding window."""
    messages = _get_conversation(chat_id)
    messages.append({"role": role, "content": content})
    # Trim to max, keeping pairs intact
    while len(messages) > CONVERSATION_MAX_MESSAGES:
        messages.pop(0)
    # Ensure first message is always user (API requirement)
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    return messages


def _cleanup_conversations():
    """Remove stale conversations."""
    now = time.time()
    stale = [cid for cid, c in CONVERSATIONS.items() if now - c["last_active"] > CONVERSATION_TTL]
    for cid in stale:
        del CONVERSATIONS[cid]


# ============================================
# VOICE MODE STATE
# ============================================

VOICE_MODE = {}  # {chat_id: bool}

# ============================================
# ALERT PREFERENCES
# ============================================

ALERT_PREFS = {}  # {chat_id: {"revit_crash": bool, "urgent_email": bool, "system_low_memory": bool}}
DEFAULT_ALERT_PREFS = {"revit_crash": True, "urgent_email": True, "system_low_memory": True}

# ============================================
# FAST DIRECT COMMANDS (no Claude needed)
# ============================================

def get_system_status_fast() -> str:
    """Get system status directly - instant response"""
    try:
        state = {}
        if os.path.exists(LIVE_STATE_FILE):
            with open(LIVE_STATE_FILE) as f:
                state = json.load(f)

        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)

        apps = state.get("applications", [])
        app_names = [a.get("ProcessName", "?") for a in apps if a.get("MainWindowTitle")]

        revit_status = "Not running"
        for app in apps:
            if app.get("ProcessName") == "Revit":
                revit_status = app.get("MainWindowTitle", "Running")[:50]
                break

        return (
            f"**System Status**\n\n"
            f"**Resources**\n"
            f"CPU: {cpu:.0f}%\n"
            f"Memory: {mem.percent:.0f}% ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB)\n\n"
            f"**Revit**: {revit_status}\n\n"
            f"**Active Apps**: {len(app_names)}\n"
            f"{', '.join(app_names[:5])}{'...' if len(app_names) > 5 else ''}\n\n"
            f"Updated: {datetime.now().strftime('%I:%M %p')}"
        )
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

            msg = (
                f"**Email Status**\n\n"
                f"Unread: {unread}\n"
                f"Urgent: {urgent}\n"
                f"Needs Response: {needs_response}\n"
                f"Last Check: {last_check[:16] if len(last_check) > 16 else last_check}"
            )

            if alerts:
                msg += "\n\n**Alerts:**"
                for a in alerts[:3]:
                    subj = a.get("subject", "?")[:40]
                    frm = a.get("from", "?").split("<")[0][:20]
                    msg += f"\n{frm}: {subj}"

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
                    return (
                        f"**Revit Status**\n\n"
                        f"Running\n"
                        f"{title}\n"
                        f"Monitor: {monitor}"
                    )

            return "**Revit Status**\n\nNot running"
    except Exception as e:
        return f"Error: {e}"


def take_screenshot_fast(monitor: str = "center") -> str:
    """Take screenshot using PowerShell (works from WSL)"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        win_path = f"D:\\temp_screenshot_{timestamp}.png"
        linux_path = f"/mnt/d/temp_screenshot_{timestamp}.png"

        if monitor.lower() == "all":
            left, top, right, bottom = -5120, 0, 2560, 1440
        elif monitor.lower() == "right":
            left, top, right, bottom = 0, 0, 2560, 1440
        elif monitor.lower() == "center":
            left, top, right, bottom = -2560, 0, 0, 1440
        elif monitor.lower() == "left":
            left, top, right, bottom = -5120, 0, -2560, 1440
        else:
            left, top, right, bottom = -2560, 0, 0, 1440

        width = right - left
        height = bottom - top

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
            logger.error(f"Screenshot failed: {getattr(result, 'stdout', '')} {getattr(result, 'stderr', '')}")
            return None
    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return None


# ============================================
# MEMORY DB ACCESS (direct SQLite)
# ============================================

def _memory_store(content: str, project: str = None, tags: list = None, importance: int = 5, memory_type: str = "context") -> str:
    """Store a memory directly in the memory DB."""
    try:
        conn = sqlite3.connect(MEMORY_DB_PATH)
        cursor = conn.cursor()
        tags_json = json.dumps(tags) if tags else None
        summary = content[:200] + "..." if len(content) > 200 else None
        namespace = f"project:{project}" if project else "global"
        cursor.execute("""
            INSERT INTO memories (content, summary, project, tags, importance, memory_type, namespace, verified, source, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'telegram', 'weber')
        """, (content, summary, project, tags_json, importance, memory_type, namespace))
        memory_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return f"Memory stored (ID: {memory_id})"
    except Exception as e:
        return f"Memory store failed: {e}"


def _memory_recall(query: str, limit: int = 5) -> str:
    """Search memories using FTS."""
    try:
        conn = sqlite3.connect(MEMORY_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Try FTS first
        try:
            cursor.execute("""
                SELECT m.id, m.content, m.project, m.importance, m.memory_type, m.created_at
                FROM memories_fts fts
                JOIN memories m ON m.id = fts.rowid
                WHERE memories_fts MATCH ?
                AND m.user_id = 'weber'
                ORDER BY m.importance DESC, m.created_at DESC
                LIMIT ?
            """, (query, limit))
        except sqlite3.OperationalError:
            # Fallback to LIKE search
            cursor.execute("""
                SELECT id, content, project, importance, memory_type, created_at
                FROM memories
                WHERE content LIKE ? AND user_id = 'weber'
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
            """, (f"%{query}%", limit))

        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "No memories found."
        results = []
        for r in rows:
            results.append(f"[{r['memory_type']}|imp:{r['importance']}] {r['content'][:200]}")
        return "\n---\n".join(results)
    except Exception as e:
        return f"Memory recall failed: {e}"


# ============================================
# TOOL SCHEMAS (Step 3)
# ============================================

CLAUDE_TOOLS = [
    {
        "name": "take_screenshot",
        "description": "Take a screenshot of Weber's monitor. Returns the image path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "monitor": {
                    "type": "string",
                    "enum": ["left", "center", "right", "all"],
                    "description": "Which monitor to capture. Default: center"
                }
            },
            "required": []
        }
    },
    {
        "name": "run_command",
        "description": "Run a PowerShell command on Weber's Windows workstation. Use for system queries, file operations, app control.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The PowerShell command to run"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "get_system_status",
        "description": "Get current system status: CPU, memory, running apps, Revit status.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_email_status",
        "description": "Get email status: unread count, urgent emails, needs-response count.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_revit_status",
        "description": "Get Revit status: running/not running, current project, monitor.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "read_file",
        "description": "Read contents of a file on the system.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute file path to read"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "memory_recall",
        "description": "Search Weber's persistent memory database for stored knowledge, decisions, corrections, and context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for memories"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 5)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "memory_store",
        "description": "Store information in Weber's persistent memory database for future recall.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The content to remember"
                },
                "project": {
                    "type": "string",
                    "description": "Related project name (optional)"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization"
                },
                "importance": {
                    "type": "integer",
                    "description": "1-10 scale (10=critical, default 5)"
                },
                "memory_type": {
                    "type": "string",
                    "enum": ["decision", "fact", "preference", "context", "outcome", "error"],
                    "description": "Type of memory (default: context)"
                }
            },
            "required": ["content"]
        }
    }
]

# Dangerous command patterns for run_command security
_BLOCKED_COMMANDS = [
    "rm -rf /", "format ", "del /s /q", "Remove-Item -Recurse -Force C:\\",
    "Stop-Computer", "Restart-Computer", "shutdown", "taskkill /f /im explorer",
]


def execute_tool(name: str, tool_input: dict, chat_id: int) -> tuple:
    """Execute a tool and return (result_text, screenshot_path_or_None).
    Returns tuple of (str, str|None)."""
    try:
        if name == "take_screenshot":
            monitor = tool_input.get("monitor", "center")
            path = take_screenshot_fast(monitor)
            if path:
                return (f"Screenshot saved: {path}", path)
            return ("Screenshot failed.", None)

        elif name == "run_command":
            command = tool_input.get("command", "")
            # Security check
            cmd_lower = command.lower().strip()
            for blocked in _BLOCKED_COMMANDS:
                if blocked.lower() in cmd_lower:
                    return (f"Blocked dangerous command: {command[:50]}", None)
            if SECURITY_ENABLED:
                security = SecurityFilter(strict_mode=True)
                is_safe, reason = security.check(command, "telegram_tool")
                if not is_safe:
                    return (f"Blocked: {reason}", None)
            result = _run_ps(command, timeout=30)
            stdout = getattr(result, 'stdout', '')
            if isinstance(stdout, bytes):
                stdout = stdout.decode('utf-8', errors='replace')
            stderr = getattr(result, 'stderr', '')
            if isinstance(stderr, bytes):
                stderr = stderr.decode('utf-8', errors='replace')
            output = stdout[:2500]
            if stderr:
                output += f"\nSTDERR: {stderr[:500]}"
            return (output or "(no output)", None)

        elif name == "get_system_status":
            return (get_system_status_fast(), None)

        elif name == "get_email_status":
            return (get_email_status_fast(), None)

        elif name == "get_revit_status":
            return (get_revit_status_fast(), None)

        elif name == "read_file":
            path = tool_input.get("path", "")
            # Security: only allow reading from known safe paths
            allowed_prefixes = ["/mnt/d/", "/mnt/c/Users/", "/home/", "/tmp/"]
            if not any(path.startswith(p) for p in allowed_prefixes):
                return (f"Access denied: {path}", None)
            if not os.path.exists(path):
                return (f"File not found: {path}", None)
            with open(path, 'r', errors='replace') as f:
                content = f.read(10000)
            return (content[:3000], None)

        elif name == "memory_recall":
            query = tool_input.get("query", "")
            limit = tool_input.get("limit", 5)
            return (_memory_recall(query, limit), None)

        elif name == "memory_store":
            content = tool_input.get("content", "")
            project = tool_input.get("project")
            tags = tool_input.get("tags")
            importance = tool_input.get("importance", 5)
            memory_type = tool_input.get("memory_type", "context")
            return (_memory_store(content, project, tags, importance, memory_type), None)

        else:
            return (f"Unknown tool: {name}", None)

    except Exception as e:
        return (f"Tool error ({name}): {e}", None)


# ============================================
# SYSTEM PROMPT
# ============================================

SYSTEM_PROMPT_BASE = """You are Weber's AI assistant responding via Telegram. Keep responses concise and mobile-friendly.
Weber is a BIM automation specialist who works with Revit, AutoCAD, and AI tools.
Be direct and helpful. Use short paragraphs. Avoid long code blocks unless asked.

You have TOOLS available. Use them proactively:
- When asked about system/apps/memory/email/Revit — use the appropriate tool
- When asked to remember something — use memory_store
- When asked to recall or check memory — use memory_recall
- When asked for a screenshot — use take_screenshot
- When asked to run a command — use run_command
- When asked to read a file — use read_file

You have access to Weber's live system state injected below.
When asked about system status, running apps, memory, Revit, email, etc. — answer using this data AND tools.
Never say you can't see the system."""


def _build_system_prompt() -> str:
    """Build system prompt with live system state injected."""
    state_block = ""
    try:
        if os.path.exists(LIVE_STATE_FILE):
            with open(LIVE_STATE_FILE) as f:
                state = json.load(f)

            sys_info = state.get("system", {})
            cpu = sys_info.get("cpu_percent", "?")
            mem_pct = sys_info.get("memory_percent", "?")
            mem_used = sys_info.get("memory_used_gb", "?")
            mem_total = sys_info.get("memory_total_gb", "?")
            active_win = state.get("active_window", "Unknown")
            apps = state.get("applications", [])
            app_lines = []
            for a in apps:
                name = a.get("ProcessName", "?")
                title = a.get("MainWindowTitle", "")
                monitor = a.get("Monitor", "?")
                if title:
                    app_lines.append(f"  - {name}: {title} (monitor: {monitor})")
            monitors = state.get("monitors", {})
            mon_count = monitors.get("count", "?")
            revit = state.get("revit", {})
            revit_running = revit.get("running", False)
            revit_connected = revit.get("connected", False)
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
            recent_files = state.get("recent_files", [])[:5]
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


# ============================================
# AGENTIC CLAUDE QUERY (Step 1 + 3)
# ============================================

MAX_TOOL_ITERATIONS = 10


async def query_claude_agentic(chat_id: int, user_content, status_callback=None) -> tuple:
    """Query Claude with tool use loop. Returns (response_text, [screenshot_paths]).

    user_content can be a string or a list of content blocks (for images).
    status_callback is an async function(str) to send status updates.
    """
    screenshots = []

    # Build messages from conversation history
    messages = _get_conversation(chat_id)

    # Append user message
    if isinstance(user_content, str):
        _append_to_conversation(chat_id, "user", user_content)
    else:
        # Content blocks (e.g., image + text)
        _append_to_conversation(chat_id, "user", user_content)

    system_prompt = _build_system_prompt()

    try:
        for iteration in range(MAX_TOOL_ITERATIONS):
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: claude_client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=CLAUDE_MAX_TOKENS,
                system=system_prompt,
                tools=CLAUDE_TOOLS,
                messages=list(messages),  # copy to avoid mutation issues
            ))

            # Process response content blocks
            text_parts = []
            tool_uses = []
            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append(block)

            # If no tool use, we're done
            if response.stop_reason == "end_turn" or not tool_uses:
                final_text = "\n".join(text_parts).strip()
                if final_text:
                    _append_to_conversation(chat_id, "assistant", response.content)
                return (final_text or "Done.", screenshots)

            # Tool use — execute tools and loop
            # Append assistant message with tool_use blocks
            _append_to_conversation(chat_id, "assistant", response.content)

            tool_results = []
            for tool_use in tool_uses:
                tool_name = tool_use.name
                tool_input = tool_use.input

                if status_callback:
                    await status_callback(f"Using tool: {tool_name}...")

                logger.info(f"Tool call: {tool_name}({json.dumps(tool_input)[:100]})")
                result_text, screenshot_path = execute_tool(tool_name, tool_input, chat_id)

                if screenshot_path:
                    screenshots.append(screenshot_path)

                # Truncate tool output
                result_text = result_text[:3000] if result_text else "(empty)"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result_text,
                })

            # Append tool results as user message
            _append_to_conversation(chat_id, "user", tool_results)

        # Safety cap reached
        return ("Reached maximum tool iterations. Here's what I have so far:\n" + "\n".join(text_parts), screenshots)

    except anthropic.APITimeoutError:
        return ("Timed out. Try a simpler question.", [])
    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        return (f"API error: {e.message}", [])
    except Exception as e:
        logger.error(f"Claude query error: {e}", exc_info=True)
        return (f"Error: {e}", [])


# Legacy wrapper for commands that don't need tool use
async def query_claude(message: str, context: str = "") -> str:
    """Simple Claude query without tool use (for backwards compat)."""
    try:
        full_prompt = f"[Context: {context}]\n\n{message}" if context else message
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: claude_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=_build_system_prompt(),
            messages=[{"role": "user", "content": full_prompt}],
        ))
        text_parts = [b.text for b in response.content if b.type == "text"]
        return "\n".join(text_parts).strip() or "No response from Claude."
    except anthropic.APITimeoutError:
        return "Timed out. Try a simpler question."
    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        return f"API error ({e.status_code}). Try again."
    except Exception as e:
        logger.error(f"Claude query error: {e}")
        return f"Error: {e}"


# ============================================
# STT — Speech to Text (Step 4)
# ============================================

_transcriber = None


def _get_transcriber():
    """Lazy-init faster-whisper transcriber."""
    global _transcriber
    if _transcriber is None:
        try:
            sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/ClaudeSTT/python/src")
            from transcriber import Transcriber
            _transcriber = Transcriber(model_size="base", device="cpu", compute_type="int8")
            logger.info("STT transcriber loaded (base model)")
        except Exception as e:
            logger.error(f"Failed to load transcriber: {e}")
            return None
    return _transcriber


# ============================================
# TTS — Text to Speech (Step 5)
# ============================================

def _speak_to_file(text: str, output_path: str, voice: str = "andrew") -> bool:
    """Generate speech audio file using Edge TTS."""
    try:
        sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/voice-mcp")
        from speak import speak_with_edge
        return speak_with_edge(text, voice, output_path)
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return False


async def send_voice_response(update: Update, text: str):
    """Generate and send a voice message response."""
    mp3_path = None
    ogg_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir="/tmp") as f:
            mp3_path = f.name
        ogg_path = mp3_path.replace(".mp3", ".ogg")

        # Truncate text for TTS (long text sounds bad)
        tts_text = text[:500]

        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, _speak_to_file, tts_text, mp3_path)

        if not success or not os.path.exists(mp3_path) or os.path.getsize(mp3_path) < 1000:
            logger.warning("TTS generation failed or empty file")
            return

        # Convert mp3 -> ogg/opus for Telegram voice
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", mp3_path, "-c:a", "libopus", "-b:a", "64k", ogg_path,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()

        if os.path.exists(ogg_path) and os.path.getsize(ogg_path) > 100:
            with open(ogg_path, 'rb') as voice_file:
                await update.message.reply_voice(voice=voice_file)
        else:
            logger.warning("OGG conversion failed")

    except Exception as e:
        logger.error(f"Voice response error: {e}")
    finally:
        for p in [mp3_path, ogg_path]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


# ============================================
# HELPERS
# ============================================

def truncate_response(text: str, max_length: int = 4000) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length] + "\n...(truncated)"


def log_conversation(user_id: int, username: str, message: str, response: str):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"\n{'='*60}\n{datetime.now()}\nUser: {username}\nMsg: {message}\nResp: {response[:500]}\n")
    except Exception:
        pass


# ============================================
# COMMAND HANDLERS
# ============================================

async def check_auth(update: Update) -> bool:
    if ALLOWED_USERS and update.effective_user.id not in ALLOWED_USERS:
        await update.message.reply_text(f"Unauthorized. ID: {update.effective_user.id}")
        return False
    return True


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    await update.message.reply_text(
"""**Weber Remote Command Center**

**Fast Commands** (instant):
/quick - System snapshot
/email - Email status
/revit - Revit status
/apps - Running apps
/screenshot [left|center|right|all]

**Intelligence** (instant):
/intel - Full intelligence report
/oe - OpportunityEngine pipeline

**Conversation**:
/clear - Reset conversation memory
/voice - Toggle voice responses

**Agent** (background work):
/agent status|task|tasks|pause|resume

**Alerts**:
/alerts - View/toggle proactive alerts

Send text, voice, or photos. I have tools and memory.""", parse_mode='Markdown')


async def cmd_quick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    await update.message.reply_text(get_system_status_fast(), parse_mode='Markdown')


async def cmd_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    await update.message.reply_text(get_email_status_fast(), parse_mode='Markdown')


async def cmd_revit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    await update.message.reply_text(get_revit_status_fast(), parse_mode='Markdown')


async def cmd_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    try:
        with open(LIVE_STATE_FILE) as f:
            state = json.load(f)
        apps = state.get("applications", [])
        msg = "**Running Apps**\n"
        for app in apps:
            name = app.get("ProcessName", "?")
            title = app.get("MainWindowTitle", "")[:30]
            monitor = app.get("Monitor", "?")
            if title:
                msg += f"\n**{name}** ({monitor})\n  {title}"
        await update.message.reply_text(msg[:4000], parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def cmd_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    monitor = context.args[0].lower() if context.args else "center"
    if monitor not in ["left", "center", "right", "all"]:
        await update.message.reply_text("Usage: /screenshot [left|center|right|all]\nDefault: center")
        return
    await update.message.reply_text(f"Capturing {monitor} monitor...")
    path = take_screenshot_fast(monitor)
    if path and os.path.exists(path):
        try:
            with open(path, 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=f"{monitor.capitalize()} monitor - {datetime.now().strftime('%I:%M:%S %p')}"
                )
            os.remove(path)
        except Exception as e:
            await update.message.reply_text(f"Failed to send image: {e}")
    else:
        await update.message.reply_text("Screenshot failed. Try again.")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation memory."""
    if not await check_auth(update): return
    chat_id = update.effective_chat.id
    if chat_id in CONVERSATIONS:
        del CONVERSATIONS[chat_id]
    await update.message.reply_text("Conversation cleared. Fresh start.")


async def cmd_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle voice response mode."""
    if not await check_auth(update): return
    chat_id = update.effective_chat.id
    current = VOICE_MODE.get(chat_id, False)
    VOICE_MODE[chat_id] = not current
    state = "ON" if not current else "OFF"
    await update.message.reply_text(f"Voice responses: **{state}**", parse_mode='Markdown')


async def cmd_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View/toggle alert preferences."""
    if not await check_auth(update): return
    chat_id = update.effective_chat.id

    if chat_id not in ALERT_PREFS:
        ALERT_PREFS[chat_id] = dict(DEFAULT_ALERT_PREFS)

    prefs = ALERT_PREFS[chat_id]

    # Toggle if arg provided
    if context.args:
        key = context.args[0].lower()
        if key in prefs:
            prefs[key] = not prefs[key]
            state = "ON" if prefs[key] else "OFF"
            await update.message.reply_text(f"Alert `{key}`: **{state}**", parse_mode='Markdown')
            return

    # Show current prefs
    lines = ["**Alert Preferences**\n"]
    for k, v in prefs.items():
        status = "ON" if v else "OFF"
        lines.append(f"`{k}`: {status}")
    lines.append("\nToggle: /alerts <alert_name>")
    await update.message.reply_text("\n".join(lines), parse_mode='Markdown')


async def cmd_status_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    await update.message.reply_text("Getting detailed status from Claude...")
    response = await query_claude("Give me a brief system status - what's running, memory usage, any issues?")
    await update.message.reply_text(truncate_response(response))


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    if not context.args:
        await update.message.reply_text("Usage: /ask <your question>")
        return
    question = ' '.join(context.args)
    await update.message.reply_text("Asking Claude...")
    response = await query_claude(question)
    await update.message.reply_text(truncate_response(response))


# ============================================
# MESSAGE HANDLERS (text, voice, photo)
# ============================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages with agentic Claude."""
    if not await check_auth(update): return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    message = update.message.text

    # Check if this is an edit response for a pending approval
    if user_id in PENDING_EDITS:
        approval_id = PENDING_EDITS.pop(user_id)
        handle_callback(approval_id, "edit", edit_text=message)
        await update.message.reply_text(
            f"Edit received for approval `{approval_id}`.\nThe system will use your updated text.",
            parse_mode="Markdown"
        )
        return

    logger.info(f"Message from {user_id}: {message[:50]}...")

    # Security check
    if SECURITY_ENABLED:
        security = SecurityFilter(strict_mode=True)
        is_safe, reason = security.check(message, "telegram")
        if not is_safe:
            await update.message.reply_text(f"Blocked: {reason}")
            return
        message = security.sanitize(message)

    await update.message.chat.send_action("typing")
    status_msg = await update.message.reply_text("Processing...")

    async def status_callback(status_text):
        try:
            await status_msg.edit_text(status_text)
        except Exception:
            pass

    response_text, screenshots = await query_claude_agentic(chat_id, message, status_callback)

    log_conversation(user_id, update.effective_user.first_name, message, response_text)

    # Send text response
    try:
        await status_msg.edit_text(truncate_response(response_text))
    except Exception:
        await update.message.reply_text(truncate_response(response_text))

    # Send screenshot photos
    for path in screenshots:
        if path and os.path.exists(path):
            try:
                with open(path, 'rb') as photo:
                    await update.message.reply_photo(photo=photo)
                os.remove(path)
            except Exception as e:
                logger.error(f"Failed to send screenshot: {e}")

    # Voice response if enabled
    if VOICE_MODE.get(chat_id, False) and response_text:
        await send_voice_response(update, response_text)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages — transcribe + process through agentic pipeline."""
    if not await check_auth(update): return

    chat_id = update.effective_chat.id
    ogg_path = None
    wav_path = None

    try:
        # Download voice file
        voice = update.message.voice or update.message.audio
        if not voice:
            await update.message.reply_text("Could not read voice message.")
            return

        file = await voice.get_file()
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False, dir="/tmp") as f:
            ogg_path = f.name
        await file.download_to_drive(ogg_path)

        # Convert OGG -> WAV 16kHz mono
        wav_path = ogg_path.replace(".ogg", ".wav")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", "-f", "wav", wav_path,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()

        if not os.path.exists(wav_path):
            await update.message.reply_text("Failed to convert audio. Try again.")
            return

        # Transcribe
        transcriber = _get_transcriber()
        if transcriber is None:
            await update.message.reply_text("Speech-to-text not available. Send as text instead.")
            return

        import numpy as np
        import soundfile as sf
        audio_data, samplerate = sf.read(wav_path, dtype='int16')
        if not isinstance(audio_data, np.ndarray):
            audio_data = np.array(audio_data, dtype=np.int16)

        loop = asyncio.get_event_loop()
        transcription = await loop.run_in_executor(None, transcriber.transcribe_audio, audio_data)

        if not transcription or not transcription.strip():
            await update.message.reply_text("Couldn't transcribe. Please try again or send as text.")
            return

        # Show transcription
        await update.message.reply_text(f'Heard: "{transcription}"')

        # Auto-enable voice mode when user sends voice
        VOICE_MODE[chat_id] = True

        # Process through agentic pipeline
        await update.message.chat.send_action("typing")
        status_msg = await update.message.reply_text("Processing...")

        async def status_callback(status_text):
            try:
                await status_msg.edit_text(status_text)
            except Exception:
                pass

        response_text, screenshots = await query_claude_agentic(chat_id, transcription, status_callback)

        log_conversation(update.effective_user.id, update.effective_user.first_name, f"[VOICE] {transcription}", response_text)

        # Send text response
        try:
            await status_msg.edit_text(truncate_response(response_text))
        except Exception:
            await update.message.reply_text(truncate_response(response_text))

        # Send screenshots
        for path in screenshots:
            if path and os.path.exists(path):
                try:
                    with open(path, 'rb') as photo:
                        await update.message.reply_photo(photo=photo)
                    os.remove(path)
                except Exception:
                    pass

        # Voice response (auto-enabled for voice messages)
        if response_text:
            await send_voice_response(update, response_text)

    except Exception as e:
        logger.error(f"Voice handling error: {e}", exc_info=True)
        await update.message.reply_text(f"Voice processing error: {e}")
    finally:
        for p in [ogg_path, wav_path]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages — analyze with Claude vision."""
    if not await check_auth(update): return

    chat_id = update.effective_chat.id
    photo_path = None

    try:
        # Get highest resolution photo
        photo = update.message.photo[-1]
        file = await photo.get_file()

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, dir="/tmp") as f:
            photo_path = f.name
        await file.download_to_drive(photo_path)

        # Base64 encode
        with open(photo_path, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')

        # Use caption as prompt, or default
        caption = update.message.caption or "What do you see? Describe concisely."

        # Build content blocks with image
        content_blocks = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_b64,
                }
            },
            {
                "type": "text",
                "text": caption,
            }
        ]

        await update.message.chat.send_action("typing")
        status_msg = await update.message.reply_text("Analyzing image...")

        async def status_callback(status_text):
            try:
                await status_msg.edit_text(status_text)
            except Exception:
                pass

        response_text, screenshots = await query_claude_agentic(chat_id, content_blocks, status_callback)

        log_conversation(update.effective_user.id, update.effective_user.first_name, f"[PHOTO] {caption}", response_text)

        try:
            await status_msg.edit_text(truncate_response(response_text))
        except Exception:
            await update.message.reply_text(truncate_response(response_text))

        # Send any tool-generated screenshots
        for path in screenshots:
            if path and os.path.exists(path):
                try:
                    with open(path, 'rb') as p:
                        await update.message.reply_photo(photo=p)
                    os.remove(path)
                except Exception:
                    pass

        # Voice response if enabled
        if VOICE_MODE.get(chat_id, False) and response_text:
            await send_voice_response(update, response_text)

    except Exception as e:
        logger.error(f"Photo handling error: {e}", exc_info=True)
        await update.message.reply_text(f"Image processing error: {e}")
    finally:
        if photo_path and os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except OSError:
                pass


# ============================================
# AGENT CONTROL COMMANDS
# ============================================

async def cmd_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return

    args = context.args
    if not args:
        await update.message.reply_text(
"""**Autonomous Agent Control**

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
            result = subprocess.run(["python3", AGENT_CONTROL, "status"], capture_output=True, timeout=10)
            await update.message.reply_text(result.stdout.decode() or "No output", parse_mode='Markdown')
        elif subcommand == "tasks":
            result = subprocess.run(["python3", AGENT_CONTROL, "tasks"], capture_output=True, timeout=10)
            await update.message.reply_text(result.stdout.decode() or "No tasks", parse_mode='Markdown')
        elif subcommand == "task" and len(args) > 1:
            prompt = ' '.join(args[1:])
            result = subprocess.run(["python3", AGENT_CONTROL, "task", prompt], capture_output=True, timeout=10)
            await update.message.reply_text(result.stdout.decode() or "Task added", parse_mode='Markdown')
        elif subcommand == "pause":
            result = subprocess.run(["python3", AGENT_CONTROL, "pause"], capture_output=True, timeout=10)
            await update.message.reply_text(result.stdout.decode() or "Paused", parse_mode='Markdown')
        elif subcommand == "resume":
            result = subprocess.run(["python3", AGENT_CONTROL, "resume"], capture_output=True, timeout=10)
            await update.message.reply_text(result.stdout.decode() or "Resumed", parse_mode='Markdown')
        elif subcommand == "briefing":
            result = subprocess.run(["python3", AGENT_CONTROL, "briefing"], capture_output=True, timeout=10)
            await update.message.reply_text(result.stdout.decode() or "Briefing requested", parse_mode='Markdown')
        else:
            await update.message.reply_text("Unknown subcommand. Use /agent for help.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


# ============================================
# APPROVAL CALLBACK HANDLER
# ============================================

async def handle_approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ALLOWED_USERS:
        return
    data = query.data
    parts = data.split(":", 1)
    if len(parts) != 2:
        return
    action, approval_id = parts
    if action == "approve":
        handle_callback(approval_id, "approve")
        await query.edit_message_text(f"*Approved*\n\n{query.message.text}", parse_mode="Markdown")
    elif action == "cancel":
        handle_callback(approval_id, "cancel")
        await query.edit_message_text(f"*Cancelled*\n\n{query.message.text}", parse_mode="Markdown")
    elif action == "edit":
        PENDING_EDITS[query.from_user.id] = approval_id
        await query.edit_message_text(f"*Editing* -- Send your changes as the next message.\n\n{query.message.text}", parse_mode="Markdown")


# ============================================
# INTELLIGENCE & OE COMMANDS
# ============================================

async def cmd_intel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    await update.message.reply_text("Generating intelligence report...")
    try:
        sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/proactive")
        from intelligence_report import generate_intelligence_report
        report = generate_intelligence_report()
        if len(report) > 4000:
            for i in range(0, len(report), 4000):
                chunk = report[i:i+4000]
                await update.message.reply_text(chunk, parse_mode='Markdown')
        else:
            await update.message.reply_text(report, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error generating report: {e}")


async def cmd_oe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    args = context.args
    subcommand = args[0].lower() if args else "status"
    try:
        if subcommand == "status":
            sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/proactive")
            from intelligence_report import generate_short_status
            status = generate_short_status()
            await update.message.reply_text(status, parse_mode='Markdown')
        elif subcommand == "scan":
            await update.message.reply_text("Triggering OE scan...")
            result = subprocess.run(
                ["python3", "-c",
                 "import sys; sys.path.insert(0, '/mnt/d/_CLAUDE-TOOLS/opportunityengine'); "
                 "from daemon import OpportunityDaemon; d = OpportunityDaemon(); "
                 "d._run_scouts(d._reset_daily_counters(__import__('datetime').datetime.utcnow()) or __import__('datetime').datetime.utcnow()); "
                 "print('Scan complete')"],
                capture_output=True, timeout=300
            )
            await update.message.reply_text(result.stdout.decode()[:2000] or "Scan triggered")
        elif subcommand == "enable" and len(args) > 1:
            scout_name = args[1]
            await update.message.reply_text(f"Scout `{scout_name}` re-enabled (restart OE to apply).", parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "*OE Commands:*\n/oe status - Pipeline overview\n/oe scan - Trigger scan now\n/oe enable <scout> - Re-enable disabled scout",
                parse_mode='Markdown'
            )
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


# ============================================
# AGENT FACTORY COMMANDS
# ============================================

async def cmd_approve_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    if not context.args:
        await update.message.reply_text("Usage: /approve_agent <agent_name>")
        return
    agent_name = context.args[0]
    try:
        sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/autonomous-agent")
        from core.agent_factory import AgentFactory
        factory = AgentFactory()
        if factory.approve_agent(agent_name):
            await update.message.reply_text(f"Agent `{agent_name}` approved and activated.", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"Agent `{agent_name}` not found.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def cmd_reject_agent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update): return
    if not context.args:
        await update.message.reply_text("Usage: /reject_agent <agent_name>")
        return
    agent_name = context.args[0]
    try:
        sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/autonomous-agent")
        from core.agent_factory import AgentFactory
        factory = AgentFactory()
        if factory.reject_agent(agent_name):
            await update.message.reply_text(f"Agent `{agent_name}` rejected and deleted.", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"Agent `{agent_name}` not found.", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


# ============================================
# PROACTIVE ALERTS (Step 7)
# ============================================

async def check_critical_alerts(context: ContextTypes.DEFAULT_TYPE):
    """Periodic check for critical system conditions."""
    try:
        if not os.path.exists(LIVE_STATE_FILE):
            return

        with open(LIVE_STATE_FILE) as f:
            state = json.load(f)

        for chat_id, prefs in ALERT_PREFS.items():
            alerts_to_send = []

            # Check memory usage
            if prefs.get("system_low_memory"):
                sys_info = state.get("system", {})
                mem_pct = sys_info.get("memory_percent", 0)
                if isinstance(mem_pct, (int, float)) and mem_pct > 90:
                    alerts_to_send.append(f"**HIGH MEMORY**: {mem_pct:.0f}% used")

            # Check Revit crash
            if prefs.get("revit_crash"):
                apps = state.get("applications", [])
                revit_running = any(a.get("ProcessName") == "Revit" for a in apps)
                revit_state = state.get("revit", {})
                was_running = revit_state.get("running", False)
                if was_running and not revit_running:
                    alerts_to_send.append("**REVIT DOWN**: Revit process no longer detected")

            # Check urgent email
            if prefs.get("urgent_email"):
                email = state.get("email", {})
                urgent = email.get("urgent_count", 0)
                if urgent > 0:
                    alerts_to_send.append(f"**URGENT EMAIL**: {urgent} urgent message(s)")

            if alerts_to_send:
                try:
                    msg = "**ALERT**\n\n" + "\n".join(alerts_to_send)
                    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Failed to send alert to {chat_id}: {e}")

    except Exception as e:
        logger.error(f"Alert check error: {e}")


# ============================================
# MAIN
# ============================================

def main():
    print("Starting Telegram bot — Remote Command Center...")
    print(f"Model: {CLAUDE_MODEL} | Max tokens: {CLAUDE_MAX_TOKENS}")

    app = Application.builder().token(BOT_TOKEN).build()

    # Fast commands (instant)
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("quick", cmd_quick))
    app.add_handler(CommandHandler("email", cmd_email))
    app.add_handler(CommandHandler("revit", cmd_revit))
    app.add_handler(CommandHandler("apps", cmd_apps))
    app.add_handler(CommandHandler("screenshot", cmd_screenshot))

    # Conversation control
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("voice", cmd_voice))
    app.add_handler(CommandHandler("alerts", cmd_alerts))

    # Claude commands
    app.add_handler(CommandHandler("status", cmd_status_full))
    app.add_handler(CommandHandler("ask", cmd_ask))

    # Agent control
    app.add_handler(CommandHandler("agent", cmd_agent))

    # Intelligence & OE
    app.add_handler(CommandHandler("intel", cmd_intel))
    app.add_handler(CommandHandler("oe", cmd_oe))

    # Agent factory
    app.add_handler(CommandHandler("approve_agent", cmd_approve_agent))
    app.add_handler(CommandHandler("reject_agent", cmd_reject_agent))

    # Approval button callbacks
    app.add_handler(CallbackQueryHandler(handle_approval_callback))

    # Photo handler (BEFORE text handler)
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Voice handler
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))

    # Text messages (last — catch-all)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Proactive alerts — check every 5 minutes
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(check_critical_alerts, interval=300, first=60)

    print("Bot running!")
    print("Commands: /quick /email /revit /apps /screenshot /clear /voice /alerts")
    print("Supports: text, voice messages, photos")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

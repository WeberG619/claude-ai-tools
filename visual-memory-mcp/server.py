#!/usr/bin/env python3
"""
Visual Memory MCP Server
Captures screen at intervals, indexes with OCR, enables recall.
Privacy-first design with whitelist/blocklist controls.
"""

import asyncio
import base64
import json
import os
import sqlite3
import sys
import threading
import time
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Optional
import hashlib

# Screen capture — lazy loaded for faster startup
mss = None  # Loaded on first capture
Image = None  # PIL.Image, loaded on first capture

# Window detection (Windows-specific)
import ctypes
from ctypes import wintypes
import psutil

# MCP Server
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

# OCR — lazy loaded on first use
HAS_TESSERACT = None  # None = not yet checked, True/False after first check

# ============================================================================
# Configuration
# ============================================================================

CONFIG_PATH = Path(__file__).parent / "config.json"
DB_PATH = Path(__file__).parent / "memory.db"

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}

CONFIG = load_config()

# ============================================================================
# Windows API for active window detection
# ============================================================================

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def get_active_window_info():
    """Get the currently active window's title and process name."""
    try:
        hwnd = user32.GetForegroundWindow()

        # Get window title
        length = user32.GetWindowTextLengthW(hwnd)
        title = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title, length + 1)

        # Get process name
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        try:
            process = psutil.Process(pid.value)
            process_name = process.name()
        except:
            process_name = "unknown"

        return {
            "title": title.value,
            "process": process_name,
            "pid": pid.value
        }
    except Exception as e:
        return {"title": "", "process": "", "pid": 0, "error": str(e)}

# ============================================================================
# Privacy Filter
# ============================================================================

class PrivacyFilter:
    def __init__(self, config):
        privacy = config.get("privacy", {})
        self.enabled = privacy.get("enabled", True)
        self.mode = privacy.get("mode", "whitelist")
        self.whitelist_apps = [a.lower() for a in privacy.get("whitelist_apps", [])]
        self.whitelist_titles = [t.lower() for t in privacy.get("whitelist_titles", [])]
        self.blocklist_titles = [t.lower() for t in privacy.get("blocklist_titles", [])]
        self.paused = False

    def should_capture(self, window_info: dict) -> tuple[bool, str]:
        """Check if we should capture based on privacy rules."""
        if self.paused:
            return False, "paused"

        if not self.enabled:
            return True, "privacy_disabled"

        title = window_info.get("title", "").lower()
        process = window_info.get("process", "").lower().replace(".exe", "")

        # Check blocklist first (always block these)
        for blocked in self.blocklist_titles:
            if blocked in title:
                return False, f"blocklist:{blocked}"

        # Whitelist mode: must match whitelist
        if self.mode == "whitelist":
            # Check process name
            for allowed in self.whitelist_apps:
                if allowed in process:
                    return True, f"whitelist_app:{allowed}"

            # Check title keywords
            for allowed in self.whitelist_titles:
                if allowed in title:
                    return True, f"whitelist_title:{allowed}"

            return False, "not_whitelisted"

        # Blacklist mode: capture unless blocked
        return True, "allowed"

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def toggle(self):
        self.paused = not self.paused
        return not self.paused

# ============================================================================
# OCR Engine
# ============================================================================

def extract_text(image) -> str:
    """Extract text from image using available OCR (lazy-loads pytesseract)."""
    global HAS_TESSERACT
    if not CONFIG.get("ocr", {}).get("enabled", True):
        return ""

    # Lazy check for tesseract on first call
    if HAS_TESSERACT is None:
        try:
            import pytesseract as _pt
            globals()["pytesseract"] = _pt
            HAS_TESSERACT = True
        except ImportError:
            HAS_TESSERACT = False

    try:
        if HAS_TESSERACT:
            text = pytesseract.image_to_string(image)
            return text.strip()
    except Exception:
        pass

    return ""

# ============================================================================
# Storage
# ============================================================================

class MemoryStorage:
    def __init__(self, db_path: Path, captures_path: Path):
        self.db_path = db_path
        self.captures_path = Path(captures_path)
        self.captures_path.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with FTS5 for text search."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Main captures table
        c.execute('''
            CREATE TABLE IF NOT EXISTS captures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                filepath TEXT NOT NULL,
                window_title TEXT,
                process_name TEXT,
                ocr_text TEXT,
                starred INTEGER DEFAULT 0,
                hash TEXT
            )
        ''')

        # Full-text search on OCR text and window title
        c.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS captures_fts USING fts5(
                window_title, ocr_text, content=captures, content_rowid=id
            )
        ''')

        # Triggers to keep FTS in sync
        c.execute('''
            CREATE TRIGGER IF NOT EXISTS captures_ai AFTER INSERT ON captures BEGIN
                INSERT INTO captures_fts(rowid, window_title, ocr_text)
                VALUES (new.id, new.window_title, new.ocr_text);
            END
        ''')

        c.execute('''
            CREATE TRIGGER IF NOT EXISTS captures_ad AFTER DELETE ON captures BEGIN
                INSERT INTO captures_fts(captures_fts, rowid, window_title, ocr_text)
                VALUES('delete', old.id, old.window_title, old.ocr_text);
            END
        ''')

        # Indexes
        c.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON captures(timestamp)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_process ON captures(process_name)')

        conn.commit()
        conn.close()

    def save_capture(self, image, window_info: dict, ocr_text: str) -> int:
        """Save a capture to disk and database."""
        timestamp = datetime.now()

        # Generate filename
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{window_info.get('process', 'unknown')}.jpg"
        date_folder = self.captures_path / timestamp.strftime('%Y-%m-%d')
        date_folder.mkdir(exist_ok=True)
        filepath = date_folder / filename

        # Save image
        quality = CONFIG.get("capture", {}).get("jpeg_quality", 70)
        image.save(filepath, "JPEG", quality=quality)

        # Compute hash for deduplication
        img_hash = hashlib.md5(image.tobytes()).hexdigest()[:16]

        # Save to database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO captures (timestamp, filepath, window_title, process_name, ocr_text, hash)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            timestamp.isoformat(),
            str(filepath),
            window_info.get("title", ""),
            window_info.get("process", ""),
            ocr_text,
            img_hash
        ))
        capture_id = c.lastrowid
        conn.commit()
        conn.close()

        return capture_id

    def search(self, query: str, limit: int = 20) -> list:
        """Search captures by text content."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT c.id, c.timestamp, c.filepath, c.window_title, c.process_name,
                   snippet(captures_fts, 1, '>>>', '<<<', '...', 30) as snippet
            FROM captures c
            JOIN captures_fts ON c.id = captures_fts.rowid
            WHERE captures_fts MATCH ?
            ORDER BY c.timestamp DESC
            LIMIT ?
        ''', (query, limit))
        results = c.fetchall()
        conn.close()
        return results

    def get_by_time_range(self, start: datetime, end: datetime, limit: int = 50) -> list:
        """Get captures within a time range."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT id, timestamp, filepath, window_title, process_name
            FROM captures
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (start.isoformat(), end.isoformat(), limit))
        results = c.fetchall()
        conn.close()
        return results

    def get_by_app(self, app_name: str, limit: int = 50) -> list:
        """Get captures for a specific application."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT id, timestamp, filepath, window_title, process_name
            FROM captures
            WHERE process_name LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (f'%{app_name}%', limit))
        results = c.fetchall()
        conn.close()
        return results

    def get_recent(self, minutes: int = 30, limit: int = 20) -> list:
        """Get recent captures."""
        since = datetime.now() - timedelta(minutes=minutes)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT id, timestamp, filepath, window_title, process_name
            FROM captures
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (since.isoformat(), limit))
        results = c.fetchall()
        conn.close()
        return results

    def get_capture(self, capture_id: int) -> Optional[dict]:
        """Get a specific capture by ID."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT id, timestamp, filepath, window_title, process_name, ocr_text
            FROM captures WHERE id = ?
        ''', (capture_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0],
                "timestamp": row[1],
                "filepath": row[2],
                "window_title": row[3],
                "process_name": row[4],
                "ocr_text": row[5]
            }
        return None

    def wipe_range(self, start: datetime, end: datetime) -> int:
        """Delete captures in a time range."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Get files to delete
        c.execute('''
            SELECT filepath FROM captures
            WHERE timestamp BETWEEN ? AND ?
        ''', (start.isoformat(), end.isoformat()))
        files = [row[0] for row in c.fetchall()]

        # Delete from database
        c.execute('''
            DELETE FROM captures
            WHERE timestamp BETWEEN ? AND ?
        ''', (start.isoformat(), end.isoformat()))
        deleted = c.rowcount
        conn.commit()
        conn.close()

        # Delete files
        for f in files:
            try:
                Path(f).unlink()
            except:
                pass

        return deleted

    def wipe_last(self, minutes: int) -> int:
        """Delete captures from the last N minutes."""
        end = datetime.now()
        start = end - timedelta(minutes=minutes)
        return self.wipe_range(start, end)

    def wipe_app(self, app_name: str) -> int:
        """Delete all captures from a specific app."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT filepath FROM captures WHERE process_name LIKE ?', (f'%{app_name}%',))
        files = [row[0] for row in c.fetchall()]

        c.execute('DELETE FROM captures WHERE process_name LIKE ?', (f'%{app_name}%',))
        deleted = c.rowcount
        conn.commit()
        conn.close()

        for f in files:
            try:
                Path(f).unlink()
            except:
                pass

        return deleted

    def get_stats(self) -> dict:
        """Get storage statistics."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('SELECT COUNT(*) FROM captures')
        total_captures = c.fetchone()[0]

        c.execute('SELECT MIN(timestamp), MAX(timestamp) FROM captures')
        row = c.fetchone()
        oldest = row[0]
        newest = row[1]

        c.execute('SELECT process_name, COUNT(*) FROM captures GROUP BY process_name ORDER BY COUNT(*) DESC LIMIT 10')
        by_app = c.fetchall()

        conn.close()

        # Calculate storage size
        total_size = sum(f.stat().st_size for f in self.captures_path.rglob('*.jpg'))

        return {
            "total_captures": total_captures,
            "oldest": oldest,
            "newest": newest,
            "storage_mb": round(total_size / 1024 / 1024, 2),
            "by_app": dict(by_app)
        }

# ============================================================================
# Capture Engine
# ============================================================================

class CaptureEngine:
    def __init__(self, storage: MemoryStorage, privacy: PrivacyFilter):
        self.storage = storage
        self.privacy = privacy
        self.running = False
        self.interval = CONFIG.get("capture", {}).get("interval_seconds", 10)
        self.sct = None  # Lazy init on first capture
        self.last_hash = None
        self._thread = None

    def _ensure_deps(self):
        """Lazy-load heavy dependencies (mss, PIL) on first use."""
        global mss, Image
        if mss is None:
            import mss as _mss
            mss = _mss
        if Image is None:
            from PIL import Image as _Image
            globals()["Image"] = _Image
        if self.sct is None:
            self.sct = mss.mss()

    def capture_once(self) -> Optional[int]:
        """Capture a single frame if allowed by privacy rules."""
        self._ensure_deps()
        window_info = get_active_window_info()
        should_capture, reason = self.privacy.should_capture(window_info)

        if not should_capture:
            return None

        # Capture primary monitor
        monitor = self.sct.monitors[1]  # Primary monitor
        screenshot = self.sct.grab(monitor)

        # Convert to PIL Image
        img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')

        # Skip if identical to last capture (dedupe)
        img_hash = hashlib.md5(img.tobytes()).hexdigest()[:16]
        if img_hash == self.last_hash:
            return None
        self.last_hash = img_hash

        # Resize for storage efficiency (keep readable)
        max_width = 1920
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

        # OCR
        ocr_text = extract_text(img)

        # Save
        capture_id = self.storage.save_capture(img, window_info, ocr_text)
        return capture_id

    def _capture_loop(self):
        """Background capture loop."""
        while self.running:
            try:
                self.capture_once()
            except Exception as e:
                print(f"Capture error: {e}", file=sys.stderr)
            time.sleep(self.interval)

    def start(self):
        """Start background capture."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop background capture."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=2)

# ============================================================================
# MCP Server
# ============================================================================

# Initialize components
captures_path = Path(CONFIG.get("capture", {}).get("storage_path", "/mnt/d/_CLAUDE-TOOLS/visual-memory-mcp/captures"))
storage = MemoryStorage(DB_PATH, captures_path)
privacy = PrivacyFilter(CONFIG)
engine = CaptureEngine(storage, privacy)

# Create MCP server
server = Server("visual-memory")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="memory_start_capture",
            description="Start background screen capture",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="memory_stop_capture",
            description="Stop background screen capture",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="memory_pause",
            description="Pause/resume capture (toggle)",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="memory_capture_now",
            description="Capture current screen immediately",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="memory_search",
            description="Search visual memory by text (OCR content, window titles)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="memory_recall_recent",
            description="Get recent captures from the last N minutes",
            inputSchema={
                "type": "object",
                "properties": {
                    "minutes": {"type": "integer", "default": 30},
                    "limit": {"type": "integer", "default": 10}
                }
            }
        ),
        Tool(
            name="memory_recall_app",
            description="Get captures from a specific application",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Application name (e.g., Revit, Bluebeam)"},
                    "limit": {"type": "integer", "default": 20}
                },
                "required": ["app_name"]
            }
        ),
        Tool(
            name="memory_recall_time",
            description="Get captures from a specific time range",
            inputSchema={
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "Start time (ISO format or natural like '2 hours ago')"},
                    "end": {"type": "string", "description": "End time (ISO format or 'now')"},
                    "limit": {"type": "integer", "default": 20}
                },
                "required": ["start"]
            }
        ),
        Tool(
            name="memory_view",
            description="View a specific capture by ID (returns the image)",
            inputSchema={
                "type": "object",
                "properties": {
                    "capture_id": {"type": "integer", "description": "Capture ID to view"}
                },
                "required": ["capture_id"]
            }
        ),
        Tool(
            name="memory_wipe_last",
            description="Delete captures from the last N minutes",
            inputSchema={
                "type": "object",
                "properties": {
                    "minutes": {"type": "integer", "description": "Minutes of history to delete"}
                },
                "required": ["minutes"]
            }
        ),
        Tool(
            name="memory_wipe_app",
            description="Delete all captures from a specific application",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Application name to wipe"}
                },
                "required": ["app_name"]
            }
        ),
        Tool(
            name="memory_wipe_range",
            description="Delete captures in a specific time range",
            inputSchema={
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "Start time (ISO format)"},
                    "end": {"type": "string", "description": "End time (ISO format)"}
                },
                "required": ["start", "end"]
            }
        ),
        Tool(
            name="memory_stats",
            description="Get visual memory statistics",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="memory_status",
            description="Get current capture status (running, paused, etc.)",
            inputSchema={"type": "object", "properties": {}}
        )
    ]

def parse_time(time_str: str) -> datetime:
    """Parse time string to datetime."""
    if time_str == "now":
        return datetime.now()

    # Try ISO format first
    try:
        return datetime.fromisoformat(time_str)
    except:
        pass

    # Try natural language
    time_str = time_str.lower()
    now = datetime.now()

    if "hour" in time_str:
        hours = int(''.join(filter(str.isdigit, time_str)) or 1)
        return now - timedelta(hours=hours)
    elif "minute" in time_str:
        mins = int(''.join(filter(str.isdigit, time_str)) or 30)
        return now - timedelta(minutes=mins)
    elif "day" in time_str:
        days = int(''.join(filter(str.isdigit, time_str)) or 1)
        return now - timedelta(days=days)
    elif "yesterday" in time_str:
        return now - timedelta(days=1)

    return now

@server.call_tool()
async def call_tool(name: str, arguments: dict):

    if name == "memory_start_capture":
        engine.start()
        return [TextContent(type="text", text="Visual memory capture started.")]

    elif name == "memory_stop_capture":
        engine.stop()
        return [TextContent(type="text", text="Visual memory capture stopped.")]

    elif name == "memory_pause":
        is_running = privacy.toggle()
        status = "resumed" if is_running else "paused"
        return [TextContent(type="text", text=f"Capture {status}.")]

    elif name == "memory_capture_now":
        capture_id = engine.capture_once()
        if capture_id:
            return [TextContent(type="text", text=f"Captured frame #{capture_id}")]
        else:
            window = get_active_window_info()
            return [TextContent(type="text", text=f"Capture skipped (privacy filter or duplicate). Current window: {window.get('process', 'unknown')} - {window.get('title', '')[:50]}")]

    elif name == "memory_search":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        results = storage.search(query, limit)

        if not results:
            return [TextContent(type="text", text=f"No results found for '{query}'")]

        output = f"Found {len(results)} results for '{query}':\n\n"
        for r in results:
            output += f"#{r[0]} | {r[1][:16]} | {r[4]} | {r[3][:50]}...\n"
            if r[5]:  # snippet
                output += f"   ...{r[5]}...\n"

        return [TextContent(type="text", text=output)]

    elif name == "memory_recall_recent":
        minutes = arguments.get("minutes", 30)
        limit = arguments.get("limit", 10)
        results = storage.get_recent(minutes, limit)

        if not results:
            return [TextContent(type="text", text=f"No captures in the last {minutes} minutes.")]

        output = f"Recent captures (last {minutes} min):\n\n"
        for r in results:
            output += f"#{r[0]} | {r[1][:16]} | {r[4]} | {r[3][:60]}\n"

        return [TextContent(type="text", text=output)]

    elif name == "memory_recall_app":
        app_name = arguments.get("app_name", "")
        limit = arguments.get("limit", 20)
        results = storage.get_by_app(app_name, limit)

        if not results:
            return [TextContent(type="text", text=f"No captures found for '{app_name}'")]

        output = f"Captures from {app_name}:\n\n"
        for r in results:
            output += f"#{r[0]} | {r[1][:16]} | {r[3][:60]}\n"

        return [TextContent(type="text", text=output)]

    elif name == "memory_recall_time":
        start = parse_time(arguments.get("start", "1 hour ago"))
        end = parse_time(arguments.get("end", "now"))
        limit = arguments.get("limit", 20)
        results = storage.get_by_time_range(start, end, limit)

        if not results:
            return [TextContent(type="text", text=f"No captures between {start} and {end}")]

        output = f"Captures from {start.strftime('%H:%M')} to {end.strftime('%H:%M')}:\n\n"
        for r in results:
            output += f"#{r[0]} | {r[1][:16]} | {r[4]} | {r[3][:50]}\n"

        return [TextContent(type="text", text=output)]

    elif name == "memory_view":
        capture_id = arguments.get("capture_id")
        capture = storage.get_capture(capture_id)

        if not capture:
            return [TextContent(type="text", text=f"Capture #{capture_id} not found.")]

        filepath = Path(capture["filepath"])
        if not filepath.exists():
            return [TextContent(type="text", text=f"Image file not found: {filepath}")]

        # Read and encode image
        with open(filepath, "rb") as f:
            img_data = base64.standard_b64encode(f.read()).decode("utf-8")

        return [
            TextContent(type="text", text=f"Capture #{capture_id}\nTime: {capture['timestamp']}\nWindow: {capture['window_title']}\nApp: {capture['process_name']}"),
            ImageContent(type="image", data=img_data, mimeType="image/jpeg")
        ]

    elif name == "memory_wipe_last":
        minutes = arguments.get("minutes", 5)
        deleted = storage.wipe_last(minutes)
        return [TextContent(type="text", text=f"Deleted {deleted} captures from the last {minutes} minutes.")]

    elif name == "memory_wipe_app":
        app_name = arguments.get("app_name", "")
        deleted = storage.wipe_app(app_name)
        return [TextContent(type="text", text=f"Deleted {deleted} captures from {app_name}.")]

    elif name == "memory_wipe_range":
        start = datetime.fromisoformat(arguments.get("start"))
        end = datetime.fromisoformat(arguments.get("end"))
        deleted = storage.wipe_range(start, end)
        return [TextContent(type="text", text=f"Deleted {deleted} captures between {start} and {end}.")]

    elif name == "memory_stats":
        stats = storage.get_stats()
        output = f"""Visual Memory Statistics:
Total captures: {stats['total_captures']}
Storage used: {stats['storage_mb']} MB
Oldest: {stats['oldest']}
Newest: {stats['newest']}

Captures by app:
"""
        for app, count in stats['by_app'].items():
            output += f"  {app}: {count}\n"

        return [TextContent(type="text", text=output)]

    elif name == "memory_status":
        window = get_active_window_info()
        should_capture, reason = privacy.should_capture(window)

        status = f"""Visual Memory Status:
Capture running: {engine.running}
Capture paused: {privacy.paused}
Interval: {engine.interval} seconds

Current window: {window.get('process', 'unknown')}
Window title: {window.get('title', '')[:60]}
Would capture: {should_capture} ({reason})
"""
        return [TextContent(type="text", text=status)]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    # Auto-start capture on server start
    engine.start()
    print("Visual Memory MCP Server starting...", file=sys.stderr)
    print(f"Capturing every {engine.interval} seconds", file=sys.stderr)
    print(f"Storage: {captures_path}", file=sys.stderr)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())

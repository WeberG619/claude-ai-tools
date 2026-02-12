#!/usr/bin/env python3
"""
Central Gateway Hub for Claude Assistant
Unified message routing, session management, and proactive notifications.

This is the central coordinator that:
- Routes messages from all channels (Telegram, WhatsApp, Web)
- Manages conversation sessions
- Triggers proactive notifications
- Logs all interactions

Run as a background service alongside the individual channel gateways.
"""

import asyncio
import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import websockets
from dataclasses import dataclass, asdict
import logging

# Import security filter
from security_filter import SecurityFilter, is_safe, sanitize

# ============================================
# CONFIGURATION
# ============================================

HUB_HOST = "127.0.0.1"
HUB_PORT = 18789

LOG_DIR = Path("/mnt/d/_CLAUDE-TOOLS/gateway/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Proactive notification settings
MORNING_BRIEFING_TIME = "07:00"  # 7 AM
EVENING_SUMMARY_TIME = "18:00"  # 6 PM

# ============================================
# LOGGING
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "hub.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gateway-hub")

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class Message:
    channel: str
    sender: str
    content: str
    timestamp: str
    message_id: Optional[str] = None

@dataclass
class Session:
    session_id: str
    channel: str
    sender: str
    started_at: str
    messages: List[Dict]
    last_activity: str

# ============================================
# GATEWAY HUB
# ============================================

class ClaudeGatewayHub:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.connected_channels: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.message_history: List[Dict] = []
        self.security_filter = SecurityFilter(strict_mode=True)

    async def handle_message(self, channel: str, sender: str, content: str) -> str:
        """Process incoming message from any channel"""
        timestamp = datetime.now().isoformat()

        # SECURITY CHECK - Filter incoming message
        safe, reason = self.security_filter.check(content, f"{channel}:{sender}")
        if not safe:
            logger.warning(f"BLOCKED message from {channel}:{sender}: {reason}")
            return f"⚠️ Message blocked for security: {reason}\n\nIf this was legitimate, please rephrase your request."

        # Check if confirmation required
        if reason and reason.startswith("CONFIRM_REQUIRED"):
            return f"⚠️ This action requires confirmation: {reason}\n\nPlease reply 'CONFIRM: [your original request]' to proceed."

        # Sanitize the content
        content = self.security_filter.sanitize(content)

        # Create or get session
        session_key = f"{channel}:{sender}"
        if session_key not in self.sessions:
            self.sessions[session_key] = Session(
                session_id=session_key,
                channel=channel,
                sender=sender,
                started_at=timestamp,
                messages=[],
                last_activity=timestamp
            )

        session = self.sessions[session_key]

        # Log incoming message
        message = Message(channel, sender, content, timestamp)
        session.messages.append(asdict(message))
        session.last_activity = timestamp
        self.message_history.append(asdict(message))

        logger.info(f"[{channel}] {sender}: {content[:50]}...")

        # Query Claude
        response = await self.query_claude(content, channel, sender)

        # Log response
        response_msg = Message(channel, "claude", response, datetime.now().isoformat())
        session.messages.append(asdict(response_msg))

        # Save to disk periodically
        await self.save_sessions()

        return response

    async def query_claude(self, message: str, channel: str, sender: str) -> str:
        """Query Claude Code CLI"""
        try:
            # Add context about the source
            context = f"[Message from {channel}]"

            proc = await asyncio.create_subprocess_exec(
                'claude', '-p', message, '--output-format', 'text',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=120
                )
            except asyncio.TimeoutError:
                proc.kill()
                return "Request timed out."

            response = stdout.decode().strip()
            return response if response else "No response."

        except Exception as e:
            logger.error(f"Claude query error: {e}")
            return f"Error: {str(e)}"

    async def broadcast(self, message: str, channels: List[str] = None):
        """Send message to specified channels (for proactive notifications)"""
        channels = channels or list(self.connected_channels.keys())

        for channel_name in channels:
            if channel_name in self.connected_channels:
                try:
                    ws = self.connected_channels[channel_name]
                    await ws.send(json.dumps({
                        "type": "broadcast",
                        "message": message
                    }))
                    logger.info(f"Broadcast to {channel_name}: {message[:50]}...")
                except Exception as e:
                    logger.error(f"Broadcast to {channel_name} failed: {e}")

    async def save_sessions(self):
        """Save sessions to disk"""
        sessions_file = LOG_DIR / "sessions.json"
        try:
            data = {
                "saved_at": datetime.now().isoformat(),
                "sessions": {k: asdict(v) for k, v in self.sessions.items()}
            }
            with open(sessions_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    async def load_sessions(self):
        """Load sessions from disk"""
        sessions_file = LOG_DIR / "sessions.json"
        if sessions_file.exists():
            try:
                with open(sessions_file, 'r') as f:
                    data = json.load(f)
                    for key, session_data in data.get("sessions", {}).items():
                        self.sessions[key] = Session(**session_data)
                logger.info(f"Loaded {len(self.sessions)} sessions")
            except Exception as e:
                logger.error(f"Failed to load sessions: {e}")

    def get_stats(self) -> Dict:
        """Get hub statistics"""
        return {
            "active_sessions": len(self.sessions),
            "connected_channels": list(self.connected_channels.keys()),
            "total_messages": len(self.message_history),
            "uptime": datetime.now().isoformat()
        }


# ============================================
# PROACTIVE NOTIFICATIONS
# ============================================

class ProactiveNotifier:
    def __init__(self, hub: ClaudeGatewayHub):
        self.hub = hub
        self.scheduled_tasks = []

    async def morning_briefing(self):
        """Generate and send morning briefing"""
        logger.info("Generating morning briefing...")

        prompt = """Generate a brief morning briefing for Weber:
1. Check today's calendar events (use Google Calendar)
2. Check for urgent emails
3. List any pending tasks
4. Weather outlook for Miami

Keep it concise - 3-4 bullet points max. Start with "Good morning Weber!"
"""
        try:
            response = await self.hub.query_claude(prompt, "proactive", "system")
            await self.hub.broadcast(f"☀️ Morning Briefing\n\n{response}")
        except Exception as e:
            logger.error(f"Morning briefing failed: {e}")

    async def evening_summary(self):
        """Generate and send evening summary"""
        logger.info("Generating evening summary...")

        prompt = """Generate a brief evening summary for Weber:
1. What was accomplished today (check memory for recent activities)
2. Any outstanding items
3. Tomorrow's first appointment

Keep it to 2-3 sentences.
"""
        try:
            response = await self.hub.query_claude(prompt, "proactive", "system")
            await self.hub.broadcast(f"🌙 Evening Summary\n\n{response}")
        except Exception as e:
            logger.error(f"Evening summary failed: {e}")

    async def schedule_notifications(self):
        """Run the notification scheduler.

        Note: Morning briefing and evening summary scheduling has been moved
        to proactive/scheduler.py which is the central orchestrator for all
        timed notifications. This loop is kept for future hub-specific
        notifications but currently does nothing.
        """
        while True:
            await asyncio.sleep(60)


# ============================================
# WEBSOCKET SERVER
# ============================================

hub = ClaudeGatewayHub()
notifier = ProactiveNotifier(hub)


async def websocket_handler(websocket, path):
    """Handle WebSocket connections from channel gateways"""
    channel_name = None

    try:
        # First message should be channel registration
        registration = await websocket.recv()
        reg_data = json.loads(registration)

        if reg_data.get("type") == "register":
            channel_name = reg_data.get("channel")
            hub.connected_channels[channel_name] = websocket
            logger.info(f"Channel registered: {channel_name}")

            await websocket.send(json.dumps({
                "type": "registered",
                "status": "ok"
            }))

        # Handle messages
        async for message in websocket:
            data = json.loads(message)

            if data.get("type") == "message":
                response = await hub.handle_message(
                    data.get("channel", channel_name),
                    data.get("sender"),
                    data.get("content")
                )

                await websocket.send(json.dumps({
                    "type": "response",
                    "content": response
                }))

            elif data.get("type") == "stats":
                await websocket.send(json.dumps({
                    "type": "stats",
                    "data": hub.get_stats()
                }))

    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Channel disconnected: {channel_name}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if channel_name and channel_name in hub.connected_channels:
            del hub.connected_channels[channel_name]


async def main():
    """Start the gateway hub"""
    # Load previous sessions
    await hub.load_sessions()

    # Start WebSocket server
    server = await websockets.serve(
        websocket_handler,
        HUB_HOST,
        HUB_PORT
    )

    logger.info(f"Gateway Hub started on ws://{HUB_HOST}:{HUB_PORT}")
    logger.info(f"Morning briefing scheduled for {MORNING_BRIEFING_TIME}")
    logger.info(f"Evening summary scheduled for {EVENING_SUMMARY_TIME}")

    # Start proactive notifier
    notifier_task = asyncio.create_task(notifier.schedule_notifications())

    # Keep running
    await asyncio.gather(
        server.wait_closed(),
        notifier_task
    )


if __name__ == "__main__":
    print("="*60)
    print("CLAUDE GATEWAY HUB")
    print("="*60)
    print(f"\nWebSocket: ws://{HUB_HOST}:{HUB_PORT}")
    print(f"Log directory: {LOG_DIR}")
    print("\nStarting hub...\n")

    asyncio.run(main())

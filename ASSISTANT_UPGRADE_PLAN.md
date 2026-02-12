# Personal Assistant Upgrade Plan

> **Goal:** Add general personal assistant capabilities to Weber's BIM automation system
> **Created:** 2026-02-01
> **Inspired by:** Various open-source AI assistant projects (credit where due)

---

## Feature Roadmap

| Feature | Priority | Difficulty | Status |
|---------|----------|------------|--------|
| WhatsApp messaging | HIGH | Medium | READY (deps installed, needs QR scan to activate) |
| Telegram bot | HIGH | Easy | LIVE - token configured, notifications tested |
| Web chat interface | HIGH | Easy | COMPLETE with voice |
| Voice wake word | MEDIUM | Medium | Partial (voice-assistant exists) |
| Mobile notifications | MEDIUM | Easy | LIVE - Telegram push notifications working |
| Gateway hub | MEDIUM | Medium | COMPLETE (port 18789) |
| Morning briefing | MEDIUM | Easy | LIVE - 7AM daily, pushes to Telegram + voice |
| Smart notifications | MEDIUM | Easy | LIVE - pushes to Telegram + voice |
| Security hardening | HIGH | Medium | COMPLETE |
| 24/7 Always-on daemon | HIGH | Medium | COMPLETE - daemon.sh with auto-restart |
| Auto-start at login | MEDIUM | Easy | COMPLETE - startup-daemon.bat for Task Scheduler |
| Health check / status | MEDIUM | Easy | COMPLETE - status.py + claude-daemon status |
| Status dashboard | LOW | Easy | COMPLETE |
| Discord bot | LOW | Easy | Not started |
| System tray app | LOW | Medium | Partial (voice_tray.pyw exists) |

---

## Phase 1: Messaging Channels (Week 1)

### 1.1 WhatsApp Integration

**Library:** `whatsapp-web.js` (Node.js) or `baileys`

**Location:** `/mnt/d/_CLAUDE-TOOLS/whatsapp-gateway/`

```javascript
// whatsapp-gateway/server.js
const { Client, LocalAuth } = require('whatsapp-web.js');
const { spawn } = require('child_process');

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { headless: true }
});

// Allowed phone numbers (security)
const ALLOWED_NUMBERS = [
    '1234567890@c.us',  // Weber's phone
];

client.on('message', async msg => {
    // Security: Only respond to allowed numbers
    if (!ALLOWED_NUMBERS.includes(msg.from)) {
        console.log(`Ignored message from: ${msg.from}`);
        return;
    }

    // Forward to Claude Code
    const response = await forwardToClaude(msg.body);
    await msg.reply(response);
});

async function forwardToClaude(message) {
    return new Promise((resolve, reject) => {
        // Option 1: Spawn claude CLI
        const claude = spawn('claude', ['-p', message, '--output-format', 'text']);

        let output = '';
        claude.stdout.on('data', (data) => output += data);
        claude.on('close', () => resolve(output.trim()));
    });
}

client.initialize();
```

**Setup:**
```bash
cd /mnt/d/_CLAUDE-TOOLS
mkdir whatsapp-gateway && cd whatsapp-gateway
npm init -y
npm install whatsapp-web.js qrcode-terminal
```

**First run:** Scan QR code with phone to link

---

### 1.2 Telegram Bot

**Library:** `python-telegram-bot` or `grammY` (TypeScript)

**Location:** `/mnt/d/_CLAUDE-TOOLS/telegram-gateway/`

```python
# telegram-gateway/bot.py
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

ALLOWED_USERS = [123456789]  # Your Telegram user ID
BOT_TOKEN = "YOUR_BOT_TOKEN"  # From @BotFather

async def handle_message(update: Update, context):
    if update.effective_user.id not in ALLOWED_USERS:
        return

    user_message = update.message.text

    # Forward to Claude
    result = subprocess.run(
        ['claude', '-p', user_message, '--output-format', 'text'],
        capture_output=True, text=True, timeout=120
    )

    response = result.stdout.strip() or "No response"

    # Telegram has 4096 char limit
    if len(response) > 4000:
        response = response[:4000] + "...(truncated)"

    await update.message.reply_text(response)

async def start(update: Update, context):
    await update.message.reply_text("Claude assistant ready. Send any message.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()
```

**Setup:**
```bash
cd /mnt/d/_CLAUDE-TOOLS
mkdir telegram-gateway && cd telegram-gateway
pip install python-telegram-bot
# Get token from @BotFather on Telegram
```

---

### 1.3 Web Chat Interface

**Location:** `/mnt/d/_CLAUDE-TOOLS/web-chat/`

Simple web interface accessible from phone browser.

```python
# web-chat/server.py
from flask import Flask, request, jsonify, render_template_string
import subprocess

app = Flask(__name__)

# Simple auth token
AUTH_TOKEN = "your-secret-token-here"

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Claude Assistant</title>
    <style>
        body { font-family: -apple-system, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
        #messages { height: 60vh; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; }
        .user { color: blue; }
        .claude { color: green; }
        input { width: 80%; padding: 10px; }
        button { padding: 10px 20px; }
    </style>
</head>
<body>
    <h1>Claude Assistant</h1>
    <div id="messages"></div>
    <input type="text" id="input" placeholder="Ask Claude...">
    <button onclick="send()">Send</button>
    <script>
        async function send() {
            const input = document.getElementById('input');
            const msg = input.value;
            input.value = '';

            document.getElementById('messages').innerHTML +=
                `<p class="user"><b>You:</b> ${msg}</p>`;

            const res = await fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: msg, token: '{{ token }}'})
            });
            const data = await res.json();

            document.getElementById('messages').innerHTML +=
                `<p class="claude"><b>Claude:</b> ${data.response}</p>`;

            document.getElementById('messages').scrollTop = 999999;
        }
        document.getElementById('input').addEventListener('keypress', e => {
            if (e.key === 'Enter') send();
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML, token=AUTH_TOKEN)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    if data.get('token') != AUTH_TOKEN:
        return jsonify({'error': 'Unauthorized'}), 401

    message = data.get('message', '')

    result = subprocess.run(
        ['claude', '-p', message, '--output-format', 'text'],
        capture_output=True, text=True, timeout=120
    )

    return jsonify({'response': result.stdout.strip()})

if __name__ == '__main__':
    # Use Tailscale or ngrok for remote access
    app.run(host='0.0.0.0', port=5555)
```

**Remote access options:**
1. **Tailscale** (recommended): `tailscale serve 5555`
2. **ngrok**: `ngrok http 5555`
3. **Cloudflare Tunnel**: Zero-trust access

---

## Phase 2: Central Gateway (Week 2)

### 2.1 Unified Message Hub

Extend your existing `system-bridge` to be the central gateway.

**Location:** `/mnt/d/_CLAUDE-TOOLS/gateway/`

```python
# gateway/hub.py
import asyncio
import websockets
import json
from datetime import datetime

class ClaudeGateway:
    def __init__(self):
        self.channels = {}  # whatsapp, telegram, web, cli
        self.sessions = {}
        self.message_queue = asyncio.Queue()

    async def handle_incoming(self, channel, sender, message):
        """Route incoming message from any channel"""
        # Log to brain-state
        self.log_message(channel, sender, message)

        # Forward to Claude
        response = await self.query_claude(message, channel, sender)

        # Send response back to originating channel
        await self.send_response(channel, sender, response)

        return response

    async def query_claude(self, message, channel, sender):
        """Query Claude Code with context"""
        context = f"[From {channel}] User: {sender}\n"

        proc = await asyncio.create_subprocess_exec(
            'claude', '-p', message, '--output-format', 'text',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip()

    async def send_response(self, channel, sender, response):
        """Send response back through the right channel"""
        if channel in self.channels:
            await self.channels[channel].send(sender, response)

    async def proactive_notify(self, message, channels=None):
        """Send proactive notification to specified channels"""
        channels = channels or ['whatsapp', 'telegram']
        for channel in channels:
            if channel in self.channels:
                await self.channels[channel].broadcast(message)

# WebSocket server for channel connections
async def websocket_handler(websocket, path):
    gateway = ClaudeGateway()
    async for message in websocket:
        data = json.loads(message)
        response = await gateway.handle_incoming(
            data['channel'],
            data['sender'],
            data['message']
        )
        await websocket.send(json.dumps({'response': response}))

# Run gateway
asyncio.run(websockets.serve(websocket_handler, 'localhost', 18789))
```

---

## Phase 3: Proactive Features (Week 3)

### 3.1 Morning Briefing

```python
# proactive/morning_briefing.py
import schedule
import time
from datetime import datetime

def morning_briefing():
    """Generate and send morning briefing"""
    briefing = generate_briefing()

    # Send to all channels
    gateway.proactive_notify(briefing, ['whatsapp', 'telegram'])

    # Also speak it
    speak(briefing)

def generate_briefing():
    # Query Claude for briefing
    prompt = """Generate a morning briefing for Weber:
    1. Check calendar for today's events
    2. Check email for urgent items
    3. Check active Revit projects status
    4. Weather forecast
    Keep it concise, 2-3 paragraphs."""

    return query_claude(prompt)

# Schedule for 7 AM
schedule.every().day.at("07:00").do(morning_briefing)
```

### 3.2 Smart Notifications

```python
# proactive/smart_notify.py

NOTIFICATION_RULES = [
    {
        "trigger": "email_from_client",
        "condition": lambda e: e['from'] in IMPORTANT_CLIENTS,
        "action": "notify_all",
        "message_template": "Important email from {from}: {subject}"
    },
    {
        "trigger": "revit_error",
        "condition": lambda e: "error" in e.get('status', '').lower(),
        "action": "notify_telegram",
        "message_template": "Revit issue: {status}"
    },
    {
        "trigger": "calendar_reminder",
        "condition": lambda e: e['minutes_until'] <= 15,
        "action": "notify_all",
        "message_template": "Reminder: {title} in {minutes_until} minutes"
    }
]
```

---

## Phase 4: Voice Wake Word (Week 4)

### 4.1 Always-On Voice

You already have `voice-assistant/` with voice service. Enhance it:

```python
# voice-assistant/wake_word.py
import pvporcupine
import pyaudio
import struct

# Wake words: "Hey Claude", "Jarvis", "Computer"
porcupine = pvporcupine.create(
    access_key='YOUR_PICOVOICE_KEY',
    keywords=['jarvis', 'computer']  # Or custom wake word
)

def listen_for_wake_word():
    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )

    print("Listening for wake word...")

    while True:
        pcm = stream.read(porcupine.frame_length)
        pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

        keyword_index = porcupine.process(pcm)

        if keyword_index >= 0:
            print("Wake word detected!")
            # Start listening for command
            handle_voice_command()
```

**Alternative:** Configure Wispr Flow for wake word (already running on your system)

---

## Phase 5: Mobile App (Optional)

### 5.1 PWA (Progressive Web App)

Convert web-chat to installable PWA:

```javascript
// web-chat/manifest.json
{
  "name": "Claude Assistant",
  "short_name": "Claude",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#007bff",
  "icons": [
    {"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
    {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}
  ]
}
```

Add to HTML head:
```html
<link rel="manifest" href="/manifest.json">
```

Now it's installable on iOS/Android as an "app".

---

## Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
                    │           WEBER'S SYSTEM                │
                    └─────────────────────────────────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
    ┌─────▼─────┐              ┌──────▼──────┐            ┌───────▼───────┐
    │ WhatsApp  │              │   Gateway   │            │   Telegram    │
    │  Gateway  │◄────────────►│    Hub      │◄──────────►│     Bot       │
    └───────────┘              │ (WebSocket) │            └───────────────┘
                               └──────┬──────┘
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
    ┌─────▼─────┐              ┌──────▼──────┐            ┌───────▼───────┐
    │  Web Chat │              │ Claude Code │            │     Voice     │
    │   (PWA)   │              │    CLI      │            │   Assistant   │
    └───────────┘              └──────┬──────┘            └───────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
              ┌─────▼─────┐    ┌──────▼──────┐   ┌──────▼──────┐
              │   Revit   │    │   Memory    │   │   Email     │
              │   MCP     │    │   System    │   │   Monitor   │
              └───────────┘    └─────────────┘   └─────────────┘
```

---

## Implementation Order

### Week 1: Quick Wins
1. [ ] Telegram bot (easiest, 30 min)
2. [ ] Web chat interface (1 hour)
3. [ ] Test remote access via Tailscale

### Week 2: WhatsApp
4. [ ] WhatsApp gateway setup
5. [ ] QR code linking
6. [ ] Security: allowlist your number

### Week 3: Integration
7. [ ] Central gateway hub
8. [ ] Unified message logging
9. [ ] Cross-channel responses

### Week 4: Proactive
10. [ ] Morning briefing
11. [ ] Smart notifications
12. [ ] Voice wake word

---

## Security Considerations

**CRITICAL:** Security-first approach:

1. **Allowlisting** - Only respond to your phone numbers
2. **Local-first** - Gateway runs on your machine, not cloud
3. **Auth tokens** - Web interface requires token
4. **No open pairing** - Reject unknown senders

---

## Files to Create

| Path | Purpose |
|------|---------|
| `/mnt/d/_CLAUDE-TOOLS/telegram-gateway/bot.py` | Telegram bot |
| `/mnt/d/_CLAUDE-TOOLS/whatsapp-gateway/server.js` | WhatsApp bridge |
| `/mnt/d/_CLAUDE-TOOLS/web-chat/server.py` | Web interface |
| `/mnt/d/_CLAUDE-TOOLS/gateway/hub.py` | Central message hub |
| `/mnt/d/_CLAUDE-TOOLS/proactive/morning_briefing.py` | Daily briefings |
| `/mnt/d/_CLAUDE-TOOLS/proactive/smart_notify.py` | Smart alerts |

---

## Next Step

Say "let's start with Telegram" or "set up WhatsApp" to begin implementation.

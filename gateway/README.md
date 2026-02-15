# Claude Personal Assistant - Multi-Channel Gateway

Text your AI from anywhere: WhatsApp, Telegram, or any browser.

## Quick Start

### 1. Install Everything
```batch
D:\_CLAUDE-TOOLS\gateway\INSTALL_ALL.bat
```

### 2. Configure Telegram (Required)
1. Open Telegram, message **@BotFather**
2. Send `/newbot` and follow prompts
3. Copy the bot token
4. Message **@userinfobot** to get your user ID
5. Edit `D:\_CLAUDE-TOOLS\telegram-gateway\bot.py`:
   ```python
   BOT_TOKEN = "your-token-here"
   ALLOWED_USERS = [your-user-id]
   ```

### 3. Launch Services
```batch
D:\_CLAUDE-TOOLS\gateway\START_ALL.bat
```

## Access Points

| Channel | URL/Access |
|---------|------------|
| **Web Chat** | http://localhost:5555?token=weber-claude-2026 |
| **Telegram** | Message your bot |
| **WhatsApp** | Scan QR code on first run |

## Remote Access (From Phone)

### Option A: Tailscale (Recommended)
```bash
tailscale serve 5555
```
Then access via your Tailscale device name.

### Option B: ngrok
```bash
ngrok http 5555
```
Use the generated URL.

## File Structure

```
D:\_CLAUDE-TOOLS\
├── gateway/
│   ├── hub.py              # Central message hub
│   ├── START_ALL.bat       # Launch all services
│   └── INSTALL_ALL.bat     # Install dependencies
│
├── web-chat/
│   ├── server.py           # Web chat server
│   └── start.bat
│
├── telegram-gateway/
│   ├── bot.py              # Telegram bot
│   └── start.bat
│
└── whatsapp-gateway/
    ├── server.js           # WhatsApp bridge
    ├── install.bat         # npm install
    └── start.bat
```

## Security

- **Auth Token**: Web chat requires token in URL
- **Allowlist**: Telegram/WhatsApp only respond to your numbers
- **Local-first**: Gateway runs on your machine, not cloud
- **Logging**: All conversations logged to `gateway/logs/`

## Features

### Available Now
- [x] Web chat interface (mobile-friendly)
- [x] Telegram bot integration
- [x] WhatsApp gateway
- [x] Central message hub
- [x] Conversation logging
- [x] Quick action buttons

### Proactive (Scheduled)
- [x] Morning briefing (7 AM)
- [x] Evening summary (6 PM)

## Troubleshooting

### Web chat not loading
```bash
curl http://localhost:5555/health
```
Should return `{"status":"ok"}`

### Telegram bot not responding
1. Check BOT_TOKEN is correct
2. Check your user ID is in ALLOWED_USERS
3. Check logs in telegram-gateway/

### WhatsApp QR code not appearing
1. Delete `.wwebjs_auth` folder
2. Restart `npm start`
3. Wait for puppeteer to initialize

## Architecture

```
Phone/Browser
     │
     ├── WhatsApp ──────────────────┐
     │                              │
     ├── Telegram ──────────────────┼──► Gateway Hub ──► Claude Code
     │                              │      (18789)
     └── Web Browser ───────────────┘
           (5555)                              │
                                               ▼
                                    Your 35 BIM Agents
                                    + Revit MCP
                                    + Memory System
                                    + Voice TTS
```

## Next Steps

1. Set up Telegram bot token
2. Test web chat from phone
3. Configure WhatsApp if needed
4. Set up Tailscale for secure remote access

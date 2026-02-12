# Security Hardening Guide

## Threat Model

### Attack Vectors
1. **Prompt Injection** - Malicious content in emails, files, webpages tricks AI into executing commands
2. **Unauthorized Access** - Someone gains access to your messaging channels
3. **Session Hijacking** - Token/auth theft
4. **Data Exfiltration** - AI tricked into sending sensitive data externally

### What Claude Code Already Does
- Sandboxed bash execution (can be configured)
- Permission prompts for sensitive operations
- No automatic execution of commands from file content (usually)

---

## Hardening Measures

### Level 1: Basic (Implemented)

#### Allowlisting
Only your phone numbers/user IDs can interact:
```python
# telegram-gateway/bot.py
ALLOWED_USERS = [your_telegram_id]

# whatsapp-gateway/server.js
const ALLOWED_NUMBERS = ['1234567890@c.us']
```

#### Auth Tokens
Web chat requires token:
```
http://localhost:5555?token=weber-claude-2026
```

**Change the default token!** Edit `web-chat/server.py`:
```python
AUTH_TOKEN = "your-unique-secret-token"
```

---

### Level 2: Network Security

#### Use Tailscale (Recommended)
- End-to-end encrypted
- Only your devices can connect
- No public exposure

```bash
tailscale serve 5555
```

#### Firewall Rules
Block external access to gateway ports:
```powershell
# Only allow localhost
netsh advfirewall firewall add rule name="Block Web Chat External" dir=in action=block protocol=tcp localport=5555 remoteip=any
netsh advfirewall firewall add rule name="Allow Web Chat Local" dir=in action=allow protocol=tcp localport=5555 remoteip=127.0.0.1
```

---

### Level 3: Prompt Injection Defense

#### Content Sanitization
Add to gateway hub - strip potential injection patterns:

```python
INJECTION_PATTERNS = [
    r'ignore previous instructions',
    r'ignore all previous',
    r'disregard (all|previous)',
    r'new instructions:',
    r'system prompt:',
    r'you are now',
    r'pretend to be',
    r'act as if',
    r'execute.*command',
    r'run.*shell',
    r'forward.*email',
    r'send.*to.*@',
]

def sanitize_input(text):
    import re
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return "[BLOCKED: Potential injection detected]"
    return text
```

#### Command Confirmation
For destructive operations, require confirmation:

```python
DANGEROUS_COMMANDS = ['rm ', 'del ', 'format ', 'drop ', 'delete ', 'send ', 'forward ']

def requires_confirmation(command):
    return any(dc in command.lower() for dc in DANGEROUS_COMMANDS)
```

---

### Level 4: Isolation

#### Separate Read vs Execute
Create two modes:
1. **Read-only mode** - Can only query, no modifications
2. **Execute mode** - Requires explicit confirmation

```python
# In gateway
MODE = "readonly"  # or "execute"

if MODE == "readonly":
    # Disable all write/execute tools
    pass
```

#### Docker Sandbox
Run the gateway in a container with limited permissions:

```dockerfile
FROM python:3.11-slim
# No shell access, limited filesystem
RUN rm /bin/sh /bin/bash
USER nobody
```

---

### Level 5: Monitoring & Alerting

#### Log All Commands
Already implemented - check `gateway/logs/`

#### Alert on Suspicious Activity
```python
ALERT_PATTERNS = [
    'password', 'credential', 'secret', 'token',
    'forward email', 'send to', 'exfiltrate',
    'rm -rf', 'del /f', 'format c:'
]

def check_and_alert(command):
    for pattern in ALERT_PATTERNS:
        if pattern in command.lower():
            send_alert(f"SUSPICIOUS: {command}")
            return True
    return False
```

---

## Recommended Configuration

### For Your Setup (Weber)

1. **Change default token** in web-chat/server.py
2. **Add your Telegram user ID** to ALLOWED_USERS
3. **Use Tailscale** for remote access (not ngrok/public URLs)
4. **Don't auto-read emails** - only process when you explicitly ask
5. **Review logs weekly** - check gateway/logs/ for anomalies

### What NOT to Do

- Don't expose port 5555 to the internet directly
- Don't use "ALLOW_ALL = True" in production
- Don't auto-process attachments from unknown senders
- Don't give the bot access to financial/banking sites

---

## Security Comparison: Cloud-based vs Local Setup

| Measure | Typical Cloud AI Assistant | Your Setup |
|---------|---------------------------|------------|
| Public pairing | Yes (risky) | No - allowlist |
| Cloud relay | Yes | No - local only |
| Default isolation | Minimal | Can be hardened |
| Email auto-read | Often enabled | Manual trigger |
| Audit logging | Basic | Comprehensive |

**Your local-first setup is inherently more secure than cloud-based alternatives.**

---

## The Unavoidable Risk

No AI system that can:
1. Read arbitrary content (emails, files, web)
2. Execute commands

...can be 100% safe from prompt injection. The AI might always be tricked.

**Mitigation strategy**:
- Limit what it CAN do automatically
- Require confirmation for dangerous actions
- Monitor and alert
- Don't connect it to truly sensitive systems

---

## Quick Hardening Checklist

- [ ] Change AUTH_TOKEN in web-chat/server.py
- [ ] Add Telegram user ID to ALLOWED_USERS
- [ ] Add phone number to WhatsApp ALLOWED_NUMBERS
- [ ] Use Tailscale instead of public URLs
- [ ] Don't enable ALLOW_ALL
- [ ] Review logs monthly
- [ ] Keep sensitive data off the system

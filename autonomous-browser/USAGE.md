# Autonomous Browser System

## Overview

This system gives Claude the ability to:
- **Navigate websites** without triggering bot detection
- **Store and use credentials** securely (with encryption)
- **Generate TOTP codes** for 2FA (manual or automatic)
- **Persist login sessions** across conversations
- **Log all actions** for accountability

## Quick Start

### 1. Add Your First Credential

Run from command line:
```bash
cd D:\_CLAUDE-TOOLS\autonomous-browser
python manage_vault.py add github.com
```

Or ask Claude:
> "Store my GitHub credentials - username is weberg619, password is [your password]"

### 2. Add TOTP for 2FA Sites

```bash
python manage_vault.py totp-add github.com
```

Enter the TOTP secret (the one you'd normally put in Google Authenticator).

### 3. Let Claude Log In

> "Log into GitHub for me"

Claude will:
1. Start the stealth browser
2. Navigate to github.com
3. Fill in your credentials
4. Generate TOTP code if needed
5. Complete login

## Commands

### Manage Credentials
```bash
python manage_vault.py list              # List all credentials
python manage_vault.py add <site>        # Add new credential
python manage_vault.py delete <site>     # Remove credential
python manage_vault.py totp-add <site>   # Add TOTP seed
python manage_vault.py totp-code <site>  # Generate TOTP code
python manage_vault.py totp-list         # List TOTP sites
python manage_vault.py sessions          # List saved sessions
```

## MCP Tools Available

### Browser Control
| Tool | Description |
|------|-------------|
| `browser_start` | Start stealth Chrome |
| `browser_stop` | Stop browser |
| `browser_navigate` | Go to URL |
| `browser_click` | Click element |
| `browser_type` | Type text |
| `browser_screenshot` | Take screenshot |
| `browser_scroll` | Scroll page |
| `browser_wait` | Wait for element |
| `browser_execute_js` | Run JavaScript |

### Credential Vault
| Tool | Description |
|------|-------------|
| `vault_store_credential` | Save login |
| `vault_get_credential` | Retrieve login |
| `vault_list_credentials` | List all logins |
| `vault_store_totp` | Save TOTP seed |
| `vault_get_totp` | Generate TOTP code |

### High-Level Automation
| Tool | Description |
|------|-------------|
| `auto_login` | Complete login flow |

### Logging
| Tool | Description |
|------|-------------|
| `log_get_session` | Current session log |
| `log_list_sessions` | Historical sessions |
| `log_credential_usage` | Credential audit trail |

## Auto-Login vs Manual Approval

### Auto-Login Enabled (Default)
Claude can use credentials without asking:
> "Check my GitHub notifications"

### Manual Approval Required
Set `auto_login: false` when storing:
```bash
# When adding credential, answer 'n' to auto-login question
```

Claude will ask permission before using:
> "I need to use your Bank of America credentials. Approve?"

## Session Persistence

After logging in, sessions are saved automatically. Next time:
- Claude navigates to the site
- Cookies are restored
- You're already logged in!

## Security Notes

1. **Encryption**: All credentials encrypted with AES-256
2. **Machine-Locked**: Vault only works on your computer
3. **Audit Trail**: Every credential use is logged
4. **Stealth**: Browser fingerprint avoids detection
5. **Human-Like**: Random delays, curved mouse movements

## Files Location

```
D:\_CLAUDE-TOOLS\autonomous-browser\
├── vault/
│   ├── vault.enc          # Encrypted credentials
│   └── .salt              # Encryption salt
├── sessions/
│   ├── sessions.json      # Saved sessions
│   └── chrome_profile/    # Browser profile
├── logger/
│   └── logs/              # Action logs
└── manage_vault.py        # CLI tool
```

## Troubleshooting

### Browser doesn't start
- Make sure Chrome is installed
- Check that undetected-chromedriver is installed: `pip install undetected-chromedriver`

### TOTP codes don't work
- Verify the seed with: `python manage_vault.py totp-code <site>`
- Compare with your authenticator app
- Ensure system clock is synchronized

### Getting blocked
- Try running with `headless: false` (visible browser)
- Add longer delays between actions
- Use a proxy if needed

## Examples

### Research a Topic
> "Go to Google Scholar, search for 'AI building automation', and summarize the top 5 results"

### Check Email
> "Log into my Gmail and tell me if I have any urgent emails"

### Fill Out Forms
> "Navigate to [URL], fill out the contact form with my info, and submit it"

### Monitor a Website
> "Check if there are any new job postings on [company careers page]"

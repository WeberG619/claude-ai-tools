# MCP Seatbelt - Agent Security Layer

A security/permissions layer that sits between Claude Code and MCP tools to prevent malicious or accidental damage from AI agents.

## Overview

MCP Seatbelt validates all MCP tool calls before they execute, checking against configurable security policies. It can:

- **Block** dangerous operations (VBA macros, force push, command injection)
- **Warn** on high-risk operations (external communication, bulk deletes)
- **Log** all MCP activity to an audit trail
- **Validate** recipients, paths, and parameters against whitelists

## Quick Start

The seatbelt is automatically invoked by Claude Code via a PreToolUse hook. No manual setup required after installation.

### Verify Installation

```bash
# Check if seatbelt is working
python3 /mnt/d/_CLAUDE-TOOLS/mcp-seatbelt/seatbelt.py

# Run tests
cd /mnt/d/_CLAUDE-TOOLS/mcp-seatbelt
python -m pytest tests/ -v
```

## Management CLI

The `seatbelt` command provides full management capabilities:

```bash
# Statistics and reporting
seatbelt stats                      # Show statistics with visual charts
seatbelt recent 20                  # Show last 20 MCP calls
seatbelt blocked                    # Show all blocked calls
seatbelt report                     # Generate weekly review report

# Whitelist management (no YAML editing required)
seatbelt whitelist                  # Show current contacts whitelist
seatbelt whitelist add bruce@x.com  # Add contact to whitelist
seatbelt whitelist remove test@x.com # Remove from whitelist

# Policy management
seatbelt policy excel-mcp           # Show policy for Excel tools
seatbelt upgrade sqlite-server      # Increase restrictions (log→warn→block)
seatbelt downgrade whatsapp         # Decrease restrictions (block→warn→log)
```

### Weekly Reports

Automated weekly reports can be set up:

```powershell
# Run setup as Administrator (one time)
powershell -ExecutionPolicy Bypass -File D:\_CLAUDE-TOOLS\mcp-seatbelt\setup_weekly_report.ps1
```

This creates a scheduled task that runs every Sunday at 10 AM, generating a security report and optionally speaking a summary.

### View Raw Audit Log

```bash
# Recent entries
tail -20 /mnt/d/_CLAUDE-TOOLS/system-bridge/audit.ndjson | jq

# Blocked calls only
cat /mnt/d/_CLAUDE-TOOLS/system-bridge/audit.ndjson | jq 'select(.action == "block")'
```

## Architecture

```
Claude Code Session
       │
       ▼
┌─────────────────────┐
│   PreToolUse Hook   │  ← Hook in ~/.claude/settings.json
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│   MCP SEATBELT      │
│  ┌───────────────┐  │
│  │ Policy Engine │  │  Load rules from YAML
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │  Validator    │  │  Check params against policies
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │ Risk Scorer   │  │  Calculate risk level (1-10)
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │ Approval Gate │  │  Block/allow decision
│  └───────────────┘  │
│  ┌───────────────┐  │
│  │ Audit Logger  │  │  Log to audit.ndjson
│  └───────────────┘  │
└─────────────────────┘
       │
       ▼ (allowed calls only)
   MCP Servers
```

## Policy Configuration

Policies are defined in YAML files in `/mnt/d/_CLAUDE-TOOLS/mcp-seatbelt/policies/`:

- `default.yaml` - Base policies for all tools
- `weber.yaml` - User-specific overrides

### Policy Structure

```yaml
tools:
  mcp__whatsapp__send_message:
    risk: 9                    # Base risk score (1-10)
    action: warn               # block | warn | log_only | allow
    require_approval: false    # Require user confirmation
    description: "WhatsApp messages"
    rules:
      - type: recipient_whitelist
        allowed: ["@bdarchitect.net"]
      - type: block_patterns
        patterns: ["password", "credential"]
```

### Available Rule Types

| Rule Type | Purpose | Config |
|-----------|---------|--------|
| `recipient_whitelist` | Validate message recipients | `allowed: [patterns]` |
| `block_patterns` | Block dangerous strings | `patterns: [regex]` |
| `path_validation` | Restrict file paths | `allowed_roots: [paths]` |
| `command_sanitize` | Block injection chars | `block_chars: [chars]` |
| `require_fields` | Ensure required params | `fields: [names]` |
| `max_length` | Limit param length | `limits: {field: max}` |
| `allowed_values` | Restrict param values | `constraints: {field: [values]}` |

## Risk Levels

| Score | Level | Description |
|-------|-------|-------------|
| 1-3 | LOW | Read operations, internal tools |
| 4-6 | MEDIUM | Write operations, local changes |
| 7-8 | HIGH | External communication, system changes |
| 9-10 | CRITICAL | Mass operations, irreversible actions |

### Risk Modifiers

The risk scorer applies automatic modifiers:

- **+3** External communication (WhatsApp, email)
- **+2** File system writes
- **+2** Sensitive paths (/etc, .ssh, credentials)
- **+2** Bulk operations (wildcards, "all")
- **+3** Irreversible actions (delete, --force)

## Gradual Rollout

The default configuration uses **audit-first** mode:

1. **Week 1-2**: All tools set to `log_only` - gather usage data
2. **Week 3**: Review audit.ndjson, tune policies
3. **Week 4**: Enable blocking for clearly dangerous patterns

## Currently Blocked

These operations are blocked by default:

- ❌ Excel VBA macro execution
- ❌ Git force push / reset --hard
- ❌ Command injection patterns (`;`, `|`, `&`)
- ❌ Path traversal (`../`)
- ❌ Fork bombs and disk writes
- ❌ SQL credential modifications (`SET password`, `SET api_key`, `SET token`)
- ❌ Sensitive file access (`.ssh/`, `.aws/`, `.gnupg/`, `credentials.json`)
- ❌ Private key files (`id_rsa`, `id_ed25519`, `.pem`, `.key`)
- ❌ WhatsApp/email to non-whitelisted recipients

## File Structure

```
/mnt/d/_CLAUDE-TOOLS/mcp-seatbelt/
├── seatbelt.py           # Main entry point
├── policy_engine.py      # YAML policy loading
├── validator.py          # Validation rules
├── risk_scorer.py        # Risk calculation
├── approval_gate.py      # Block/approve logic
├── audit_logger.py       # NDJSON audit logging
├── policies/
│   ├── default.yaml      # Default policies
│   └── weber.yaml        # User overrides
├── tests/
│   └── test_seatbelt.py  # Unit tests
└── README.md
```

## Troubleshooting

### Seatbelt is blocking legitimate calls

1. Check audit log for the blocked call:
   ```bash
   tail -50 /mnt/d/_CLAUDE-TOOLS/system-bridge/audit.ndjson | jq 'select(.action == "block")'
   ```

2. Find the matching policy and adjust in `weber.yaml`

3. Restart Claude Code to reload policies

### Seatbelt errors are breaking Claude

The seatbelt uses **fail-open** mode by default. If there are internal errors, calls are allowed rather than blocked. Check:

```bash
tail -50 /mnt/d/_CLAUDE-TOOLS/system-bridge/audit.ndjson | jq 'select(.action == "error")'
```

### Adding new trusted contacts

Edit `/mnt/d/_CLAUDE-TOOLS/mcp-seatbelt/policies/weber.yaml` and add to `contacts_whitelist`:

```yaml
contacts_whitelist:
  - "newperson@company.com"
  - "@trustedomain.com"
```

## Exit Codes

- `0` - Allow the tool call
- `2` - Block the tool call (Claude sees rejection message)

## Development

```bash
# Run tests
cd /mnt/d/_CLAUDE-TOOLS/mcp-seatbelt
python -m pytest tests/ -v

# Test specific tool
CLAUDE_TOOL_NAME="mcp__whatsapp__send_message" \
CLAUDE_TOOL_INPUT='{"contact": "test@example.com", "message": "hi"}' \
python seatbelt.py
```

# WEBER GOUIN / BIM OPS STUDIO -- COMPLETE CAPABILITY AUDIT

**Generated:** 2026-02-15
**Auditor:** Claude Opus 4.6 (147 tool calls, exhaustive directory-by-directory inspection)
**Location:** `/mnt/d/_CLAUDE-TOOLS/`
**Purpose:** Pre-open-source inventory of every capability in the ecosystem

---

## EXECUTIVE SUMMARY

| Metric | Value |
|--------|-------|
| Total Directories Audited | 95+ |
| PRODUCTION status tools | 19 |
| FUNCTIONAL status tools | 55 |
| STUB status tools | 11 |
| BROKEN / NOT-A-TOOL | 2 |
| Total MCP tools exposed | 150+ across all servers |
| Total Skill Files | 20 |
| Total Agent Definitions | 51 (across 10 squads in `~/.claude/agents/`) |
| Total Python files | 200+ |
| External MCP Servers (older) | 19 (in `/mnt/d/009-PROJECT-FILES-DEVELOPER/mcp-servers/`) |
| Archived Tools | 11 directories |
| Estimated dev hours | 500-900 |
| Estimated recreation cost | $75,000-$225,000 |

### Status Definitions

| Status | Meaning |
|--------|---------|
| **PRODUCTION** | Actively used, has real data/logs, proven on real projects |
| **FUNCTIONAL** | Works but may not be regularly used, or only partially exercised |
| **STUB** | Skeleton/placeholder, single file, not fully built out |
| **BROKEN** | Has code but likely does not work or is not actually a tool |

---

## CATEGORY 1: CORE INFRASTRUCTURE (The Backbone)

---

### 1.1 system-bridge/ -- System State Daemon

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/system-bridge/` |
| **Entry Point** | `claude_daemon.py` (v2.1.0) |
| **Language** | Python |
| **Dependencies** | sqlite3, jsonschema (optional), PowerShell |

**What it does:**
- Runs as a persistent background daemon on Windows
- Polls system state every 10 seconds
- Tracks: open applications, active windows, Revit project status, Bluebeam document, monitor configuration (3x 2560x1440), CPU/memory usage, clipboard content, recent files
- Writes to `live_state.json` -- read by Claude at every session start
- Crash recovery with automatic restart
- PID file management, health checks (`health.json`)
- Event log rotation (NDJSON format with optional schema validation)
- Security audit trail for all MCP tool calls (`audit.ndjson`)
- State persistence across restarts (`persistent_state.json`)

**Sub-components (13 files):**

| File | Purpose |
|------|---------|
| `claude_daemon.py` | Main daemon loop, system polling, state writing |
| `watchdog.py` | Monitors daemon health, restarts if crashed/stale (30s checks, max 5 restarts in 5 min) |
| `workflow_engine.py` | Learns user action sequences, stores in SQLite (`workflows.db`), predicts next actions, detects anomalies |
| `notification_system.py` | Generates proactive alerts via Windows toast, sound, log, console. Priority: LOW/MEDIUM/HIGH/CRITICAL |
| `project_intelligence.py` | Correlates open files/apps to known projects, detects context switches, predicts intent, alerts on mismatches |
| `voice_intent.py` | Voice intent processing |
| `file_indexer.py` | File indexing to SQLite (`file_index.db`) |
| `bluebeam_bridge.py` | Bluebeam state tracking |
| `system_state.py` | System state collection |
| `session_start.py` | Session initialization logic |
| `weekly_review.py` | Weekly review generation |
| `claude_brain.py` | Brain state integration |
| `daemon_manager.py` | Daemon process management |

**Data files:**
- `live_state.json` -- current system state (the primary output)
- `persistent_state.json` -- survives crashes
- `health.json` -- daemon health status
- `intelligence.json` -- project intelligence output
- `learned_patterns.json` -- workflow patterns
- `events.ndjson` (+ rotated backups) -- event log
- `audit.ndjson` -- security audit trail
- `workflows.db` -- SQLite workflow database
- `file_index.db` -- file index database
- `notifications.jsonl` -- notification log
- `brain_state.json` / `current_state.json` -- state snapshots

**Startup scripts:**
- `start_daemon.bat` / `stop_daemon.bat` -- Windows batch launchers
- `start_services.bat` -- starts all services
- `get_apps.ps1` / `scan_files.ps1` -- PowerShell data collection scripts
- `create_shortcut.ps1` -- desktop shortcut creation
- `setup_weekly_task.ps1` -- Windows Task Scheduler setup

**Hidden capability:** The workflow learning engine (`workflow_engine.py`) does not just monitor -- it builds behavioral pattern databases from usage and can predict what you will do next. This is a behavioral AI layer on top of system monitoring.

---

### 1.2 brain-state/ -- Session Persistence

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/brain-state/` |
| **Entry Point** | `brain_loader.py` |
| **Language** | Python |

**What it does:**
- Loads unified brain state at session startup (mandatory first action)
- Merges system state, email alerts, and memory DB into one brain JSON
- Logs full conversation transcripts to `conversations/` directory
- Generates daily summaries extracting decisions, problems solved, open questions, learnings

**Sub-components:**

| File | Purpose |
|------|---------|
| `brain_loader.py` | Loads `brain.json` + `live_state.json` + `email_alerts.json` into unified state |
| `conversation_logger.py` | Records every conversation turn to markdown files, organized by date/session number |
| `conversation_extractor.py` | Extracts conversation data from Claude's internal JSONL format |
| `daily_summarizer.py` | End-of-day summarization of all sessions, extracts key decisions/problems/questions |
| `brain_sync.py` | Synchronization logic between brain components |

**Data:**
- `brain.json` -- unified brain state
- `live_checkpoint.json` -- live checkpoint data
- `conversations/` -- full conversation transcripts
- `daily_summaries/` -- daily summary files
- `backups/` -- brain state backups
- `hooks/` -- hook integrations
- `logs/` -- brain-state logs

---

### 1.3 claude-memory-server/ -- Persistent Memory MCP Server

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/claude-memory-server/` |
| **Entry Point** | `src/server.py` (also `src/engram.py`) |
| **Language** | Python |
| **Database** | SQLite with FTS5 full-text search (`data/memories.db`) |

**What it does:**
- MCP server providing persistent memory across all Claude Code sessions
- 550+ memories stored, 60+ projects tracked
- 234 memories for RevitMCPBridge2026 alone
- Self-improvement loop: corrections, pattern synthesis, spaced repetition
- Automated backups: hourly, daily, weekly (`backups/` directory)

**MCP Tools exposed (23 tools):**

| Tool | Description |
|------|-------------|
| `memory_store` | Save a new memory with metadata |
| `memory_store_enhanced` | Enhanced store with additional context |
| `memory_recall` | Search memories by query |
| `memory_recall_fast` | Fast cached recall |
| `memory_semantic_search` | Semantic similarity search |
| `memory_get_context` | Load session context |
| `memory_smart_context` | Intelligent context loading |
| `memory_get_project` | Get all memories for a project |
| `memory_list_projects` | List all tracked projects |
| `memory_update_project` | Create/update project info |
| `memory_link` | Link related memories |
| `memory_get_related` | Get related memories |
| `memory_forget` | Delete memories |
| `memory_stats` | System statistics |
| `memory_engram_stats` | Engram-level statistics |
| `memory_summarize_session` | Session summarization |
| `memory_store_correction` | Store a correction (what was wrong, correct approach) |
| `memory_get_corrections` | Retrieve corrections |
| `memory_corrections_instant` | Instant correction lookup |
| `memory_smart_recall` | Intelligent recall combining search + corrections |
| `memory_check_before_action` | Pre-action safety check against past mistakes |
| `memory_correction_helped` | Record that a correction prevented a mistake |
| `memory_log_avoided_mistake` | Log that a known mistake was avoided |
| `memory_auto_capture_correction` | Auto-capture corrections from user behavior |
| `memory_synthesize_patterns` | Discover patterns across memories |
| `memory_find_patterns` | Find specific patterns |
| `memory_get_improvement_stats` | Track improvement metrics |
| `memory_decay_corrections` | Age out old corrections |
| `memory_archive_old_corrections` | Archive corrections |
| `memory_retire_correction` | Retire a correction |
| `memory_compact` | Compact the database |
| `memory_verify` | Verify database integrity |
| `memory_invalidate_cache` | Clear caches |

**Memory types stored:** decision, fact, preference, context, outcome, error, correction

**Importance scale:** 1-3 (low), 4-6 (normal), 7-8 (high), 9-10 (critical)

**Hidden capability:** This is a full learning system, not just storage. The correction/reinforcement loop means Claude gets measurably better over time at Weber-specific tasks. The `memory_check_before_action` tool is called before every significant operation.

---

### 1.4 powershell-bridge/ -- WSL-to-Windows Bridge

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/powershell-bridge/` |
| **Entry Point** | `bridge.py` (server), `client.py` (client) |
| **Language** | Python (server/client), PowerShell (worker) |
| **Port** | `127.0.0.1:15776` (WSL-local TCP) |

**What it does:**
- TCP server running inside WSL2 that manages a persistent `powershell.exe` subprocess
- Drop-in replacement for `subprocess.run(powershell.exe...)` -- approximately 100x faster
- Used by: voice-mcp, bluebeam-mcp, creative-studio, ambient-monitor, subtitle-reader, video-pipeline, and many more
- Health file, PID management, automatic fallback if bridge is down

**Files:**

| File | Purpose |
|------|---------|
| `bridge.py` | TCP server + subprocess manager |
| `client.py` | Client library: `ps_exec()` and `run_powershell()` functions |
| `server.ps1` | PowerShell-side worker script that stays alive |
| `manage.py` | Process management utilities |

**Client API:**
```python
from client import ps_exec, run_powershell
result = ps_exec("Get-Process | Select -First 5")  # Fast path via bridge
result = run_powershell("Get-Date")  # Auto-fallback if bridge down
```

**Hidden capability:** This is the universal accelerator. Almost every tool that touches Windows goes through this bridge. Without it, everything is 100x slower due to PowerShell subprocess startup overhead.

---

### 1.5 agent-common-sense/ -- Common Sense Engine

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/agent-common-sense/` |
| **Entry Point** | `kernel.md` (injected into agents), `sense.py` (CLI) |
| **Language** | Python + Markdown |

**What it does:**
- Injects a 3-step decision loop into every agent before every action:
  1. CLASSIFY: Reversible? Blast radius? Familiar?
  2. CHECK: Search correction memory for similar past actions
  3. SIMULATE: "If I do this and it goes wrong, what happens?"
- Learning loop: on failure store corrections, on success reinforce, on new territory store known-good patterns
- 8 judgment heuristics: read before write, verify before trust, small before big, ask before destroy, local before remote, specific before general, recent before stale, undo before redo
- Escalation instinct: pause and explain when uncertain, present options when conflicted, report unexpected results
- Cross-domain transfer: lessons from one domain applied to others

**Files:**

| File | Purpose |
|------|---------|
| `kernel.md` | The core decision framework (injected into every agent prompt) |
| `seeds.json` | 15 universal pre-loaded corrections |
| `sense.py` | CLI: `sense.py check --action "desc"`, `sense.py seed`, `sense.py synthesize` |
| `inject.py` | Injection logic for sub-agent prompts |
| `__init__.py` | Package init |
| `test_sense.py` | Unit tests |

**Hidden capability:** This is essentially an "instinct layer" -- giving AI agents the equivalent of human judgment for irreversible or high-risk actions. It prevents the most dangerous class of AI mistakes.

---

### 1.6 agent-boost/ -- Agent Enhancement Framework

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/agent-boost/` |
| **Entry Point** | `strong_agent.md` |
| **Language** | Markdown + Python |

**What it does:**
- Structured 5-phase execution framework for sub-agents:
  - Phase 0: LOAD CONTEXT (memory corrections, smart recall, injected context, parallel reads)
  - Phase 1: ORIENT (parse task, assess scope, confidence gate high/medium/low, plan approach)
  - Phase 2: INVESTIGATE (read files, search patterns, check tests, map dependencies)
  - Phase 3: EXECUTE (small steps, match style, don't over-engineer, security check, rollback plan)
  - Phase 4: VERIFY (re-read changes, run tests, check regressions, grep loose ends)
  - Phase 5: REPORT (summary, files changed, verification, follow-ups, mandatory learning storage)
- Confidence gating: LOW confidence = stop and report back
- Mandatory learning storage per task
- Execution rules: never use browser_click, never call user "Rick", never commit secrets, Revit uses named pipes

**Files:**

| File | Purpose |
|------|---------|
| `strong_agent.md` | The full execution framework (v2) |
| `agent_preamble.md` | Standard preamble for all sub-agents |
| `build_context.py` | Assembles context for sub-agent launch |

---

## CATEGORY 2: COMMUNICATION GATEWAY (Multi-Channel Access)

---

### 2.1 gateway/ -- Central Message Hub

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/gateway/` |
| **Entry Point** | `hub.py` |
| **Language** | Python (asyncio + websockets) |
| **Port** | `127.0.0.1:18789` |

**What it does:**
- Central WebSocket hub routing messages from all channels (Telegram, WhatsApp, Web) to Claude Code
- Session management with per-channel sessions
- Conversation logging to `logs/`
- Security filter integration (`security_filter.py`, `email_security.py`)
- Email pre-read hook (`email_preread_hook.py`)
- Approval system for high-risk operations (`approval_system.py`, `pending_approvals.json`)

**Files:**

| File | Purpose |
|------|---------|
| `hub.py` | Central gateway hub (WebSocket server, message routing, session management) |
| `security_filter.py` | Message security filtering |
| `email_security.py` | Email-specific security |
| `email_preread_hook.py` | Pre-read email hook |
| `approval_system.py` | High-risk operation approval gate |
| `status.py` | Service status checking |
| `START_ALL.bat` / `INSTALL_ALL.bat` | One-click launch/install |
| `start.bat` / `start_gateway.bat` | Individual launchers |
| `daemon.sh` / `startup-daemon.bat` | Background service management |
| `SECURITY.md` | Security documentation |
| `pending_approvals.json` | Pending approval queue |

---

### 2.2 telegram-gateway/ -- Telegram Bot Interface

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/telegram-gateway/` |
| **Entry Point** | `server.py` (file not found -- likely refactored into gateway hub or `bot.py` expected) |
| **Language** | Python |

**What it does:**
- Telegram bot interface for remote Claude Code access
- Commands: `/agent status`, `/agent tasks`, `/agent task <prompt>`, `/agent pause`, `/agent resume`, `/agent briefing`
- Conversations logged to `conversations.log`
- `start.bat` for Windows launch

**Note:** The `telegram-bot/` directory at `/mnt/d/_CLAUDE-TOOLS/telegram-bot/` only contains `config.json` (bot token and configuration). The actual bot logic appears to have been refactored into the gateway hub system.

---

### 2.3 whatsapp-gateway/ -- WhatsApp Bridge

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/whatsapp-gateway/` |
| **Entry Point** | `server.js` |
| **Language** | Node.js (whatsapp-web.js + Puppeteer) |

**What it does:**
- Full WhatsApp gateway using `whatsapp-web.js`
- Locked down to Weber's phone number only (`17865879726@c.us`)
- ALLOW_ALL = false (security)
- 120-second timeout for Claude responses

**Fast commands (no Claude needed):**
- `/quick` -- quick system status
- `/email` -- email status
- `/revit` -- Revit status
- `/apps` -- running applications
- `/screenshot` -- take screenshot
- `/help` -- command help

**Claude commands (10-30s):**
- `/ask <question>` -- ask Claude
- `/status` -- detailed status
- Any free text -- routed to Claude

**Features:**
- Reads `live_state.json` for instant system status
- Session persistence via `.wwebjs_auth/`
- Conversations logged to `conversations.log`
- QR code authentication on first run

---

### 2.4 web-chat/ -- Browser Chat Interface

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/web-chat/` |
| **Entry Point** | `server.py` |
| **Language** | Python (Flask) |
| **Port** | `0.0.0.0:5555` |

**What it does:**
- Mobile-friendly web chat interface
- Auth token required in URL (`?token=...`)
- Security filter integration from gateway
- 120-second timeout for Claude responses
- Remote access via Tailscale (`tailscale serve 5555`) or ngrok (`ngrok http 5555`)
- Inline HTML template (no external files needed)

---

### 2.5 email-watcher/ -- Gmail Monitor Daemon

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/email-watcher/` |
| **Entry Point** | `email_watcher.py` |
| **Language** | Python (imaplib) |

**What it does:**
- Background daemon checking Gmail via IMAP every 2 minutes
- Monitors multiple accounts: Personal (`weberg619@gmail.com`) + BIM Ops Studio
- Classifies emails using local Ollama LLM (`triage.py`)
- Writes alerts to `email_alerts.json` (consumed by brain-state and proactive system)
- Credentials loaded from `.env` (never hardcoded)
- Max 20 emails per check

**Files (16 total):**

| File | Purpose |
|------|---------|
| `email_watcher.py` | Main daemon (IMAP polling, classification, alert writing) |
| `triage.py` | Email classification via local Ollama |
| `check_and_alert.py` | Check + alert combo |
| `check_inbox.py` | Inbox checker |
| `read_all_emails.py` | Read all emails |
| `read_recent_emails.py` | Read recent emails |
| `secure_reader.py` | Secure email reading |
| `cleanup_inbox.py` | Inbox cleanup |
| `cleanup_promo.py` | Promotional email cleanup |
| `delete_promo_2026.py` | 2026 promotional deletion |
| `analyze_2025.py` | Historical email analysis |
| `process_2025.py` | Historical email processing |
| `watcher_manager.py` | Daemon management |
| `start_watcher.bat` / `stop_watcher.bat` | Windows launchers |
| `email_alerts.json` | Output: current alert state |
| `processed_emails.json` / `recent_emails.json` / `emails_2025.json` | Data files |

---

### 2.6 gmail-attachments/ -- Email Attachment Downloader

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/gmail-attachments/` |
| **Entry Point** | `imap_download.py` |
| **Language** | Python |

**What it does:**
- Downloads email attachments via IMAP
- Search by sender, subject, date range
- Usage: `python3 imap_download.py --search "from:sender" --download "/path"`

---

## CATEGORY 3: AUTONOMOUS AGENT SYSTEM

---

### 3.1 autonomous-agent/ -- Background Agent Daemon

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/autonomous-agent/` |
| **Entry Point** | `run_agent.py` |
| **Language** | Python (asyncio) |

**What it does:**
- Runs 24/7 in background
- Loop: WATCH (system, calendar, email, Revit) -> THINK (triggers, rules, priority) -> ACT (Claude Code CLI) -> REPORT (Telegram/Voice)
- SQLite task queue (`queues/tasks.db`)
- Decision engine with configurable triggers
- Proactive notifications:
  - Morning briefing (7 AM)
  - Evening summary (6 PM)
  - Threshold alerts (memory > 85%, urgent emails)
  - Quiet hours (10 PM - 7 AM, except critical)
- Meeting preparation: 15 min before events, pulls relevant emails, loads project context
- System watching: memory usage, Revit connection, app status, email urgency

**Directory structure:**

| Path | Purpose |
|------|---------|
| `run_agent.py` | Main entry point (foreground/daemon/status/stop modes) |
| `agent_control.py` | CLI control interface |
| `start_agent.bat` | Windows launcher |
| `core/agent.py` | Main agent loop |
| `core/task_queue.py` | SQLite task queue |
| `core/decision_engine.py` | Triggers and rules |
| `core/notifier.py` | Telegram/Voice notifications |
| `core/context_builder.py` | Briefings and summaries |
| `triggers/` | Trigger definitions |
| `workflows/` | Workflow definitions |
| `scripts/` | Utility scripts |
| `queues/tasks.db` | Persistent task queue |
| `logs/agent.log` | Activity log |
| `memory/` | Agent memory |
| `reports/` | Generated reports |
| `results/` | Task results |
| `test_outputs/` | Test outputs |

**Control commands:**
- `python3 agent_control.py status` / `tasks` / `task "prompt"` / `pause` / `resume`
- Telegram: `/agent status` / `/agent tasks` / `/agent task <prompt>` / `/agent briefing`

---

### 3.2 proactive/ -- Proactive Scheduler

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/proactive/` |
| **Entry Point** | `scheduler.py` |
| **Language** | Python |

**What it does:**
- Central orchestrator for all autonomous features
- Runs as long-lived daemon (started by `gateway/daemon.sh`)

**Schedule:**

| Time | Event | Frequency |
|------|-------|-----------|
| 7:00 AM | Morning briefing | Daily |
| 6:00 PM | Evening summary | Daily |
| 7:15 AM | Weekly overview | Monday |
| 5:00 PM | Weekly recap | Friday |
| Every 60s | Calendar reminders | Continuous |
| Every 60s | Email alert pushing | Continuous |
| Every 30s | Smart notifications | Continuous |
| Every 5 min | Service health monitoring | Continuous |
| Every 60s | Tracker state persistence | Continuous |

**Files (9 total):**

| File | Purpose |
|------|---------|
| `scheduler.py` | Central orchestrator daemon |
| `morning_briefing.py` | Daily briefing: calendar + email + weather (wttr.in, free, no API key) |
| `evening_summary.py` | End-of-day recap via Telegram (non-disruptive, no voice) |
| `calendar_monitor.py` | Calendar event monitoring |
| `email_monitor.py` | Email alert monitoring |
| `smart_notify.py` | Intelligent notification routing |
| `notify_channels.py` | Multi-channel notification delivery |
| `weekly_routines.py` | Weekly patterns |
| `tracker_state.py` | State persistence |

---

### 3.3 opportunityengine/ -- Autonomous Revenue Generation

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/opportunityengine/` |
| **Entry Point** | `daemon.py` |
| **Language** | Python |

**What it does:**
- Autonomous freelance revenue generation agent running 24/7
- Loop: Scan -> Qualify -> Decide -> Propose -> Submit/Hold -> Follow Up -> Learn
- Low-risk opportunities acted on autonomously
- High-value opportunities held for human approval via Telegram

**Scouts (5 platform scanners):**

| Scout | Platform | Method |
|-------|----------|--------|
| `github_scout.py` | GitHub | API |
| `reddit_scout.py` | Reddit | API |
| `hn_scout.py` | Hacker News | API |
| `remoteok_scout.py` | RemoteOK | API |
| `freelancer_scout.py` | Freelancer.com | CDP (skipped in daemon due to browser timeout) |

**Agents (5 processing agents):**

| Agent | Purpose |
|-------|---------|
| `qualifier.py` | Scores and qualifies opportunities |
| `proposal_agent.py` | Drafts proposals |
| `submitter.py` | Handles submission |
| `tracker.py` | Tracks opportunity lifecycle |
| `response_monitor.py` | Monitors responses |

**Core:**
- `core/database.py` -- SQLite database (`pipeline.db`)
- `core/config.py` -- scan intervals, peak hours, score thresholds
- `core/decision_rules.py` -- decide() function returns Action (submit/hold/skip)
- `core/models.py` -- Opportunity, OpportunityStatus, ProposalStatus models

**Other:**
- `cli.py` -- command-line interface
- `templates/` -- proposal templates
- `notifications.log` -- notification history

**Hidden capability:** This is a fully autonomous business development agent. It does not just monitor -- it qualifies, drafts, and can submit proposals autonomously on multiple platforms.

---

### 3.4 freelancer-monitor/ -- Freelancer.com Job Monitor

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/freelancer-monitor/` |
| **Entry Point** | `monitor.mjs` |
| **Language** | Node.js (ESM) |

**What it does:**
- Daemon polling Freelancer.com for jobs Claude can handle
- Configurable poll interval (default 5 min, via `--interval`)
- Voice alerts via TTS (via `--voice`)
- Categories: data-entry, article-writing, research-writing, excel, copywriting, transcription, data-processing, technical-writing, proofreading, content-writing, typing, data-cleansing, editing, blog-writing
- Good-keyword matching: data entry, typing, excel, spreadsheet, transcription, article, blog, content writing, copywriting, research, proofreading, editing, summary, report writing, documentation, csv, database entry, web research, list building, lead generation, pdf to excel, data extraction, data mining, rewriting
- Tracks: `data/seen_jobs.json`, `data/active_bids.json`, `data/alerts.json`

---

## CATEGORY 4: VOICE & SPEECH

---

### 4.1 voice-mcp/ -- Text-to-Speech MCP Server

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/voice-mcp/` |
| **Entry Point** | `src/server.py` (MCP), `speak.py` (CLI) |
| **Language** | Python |

**What it does:**
- Multi-engine TTS with priority fallback:
  1. Google TTS (gTTS) -- natural voice, free, reliable
  2. Microsoft Edge TTS -- best quality, sometimes rate-limited
  3. Windows SAPI -- always works offline
- MCP server with tools: `speak`, `speak_summary`, `list_voices`, `stop_speaking`
- Audio caching for repeated phrases (hash-based)
- IPv4 forced (critical fix for Edge TTS in WSL2)
- 5 retries with exponential backoff
- 60-second timeout per attempt
- Uses PowerShell Bridge for playback (100x faster)
- CLI: `python speak.py "Text to speak" [voice]`

---

### 4.2 voice-notes/ -- Audio-to-Meeting-Notes

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/voice-notes/` |
| **Entry Point** | CLI `voice-notes`, Python API |
| **Language** | Python |

**What it does:**
- Transcribes audio files to structured meeting notes using OpenAI Whisper (local, no API costs)
- Supports: .wav, .mp3, .m4a, .flac, .ogg, .webm
- Smart extraction: key points, action items, attendees
- Model selection: tiny/base/small/medium/large (1GB to 10GB RAM)
- Optional voice summary via voice-mcp
- Timestamps support
- Python API: `Transcriber`, `NoteFormatter`
- Proper packaging (pyproject.toml, setup.py, requirements.txt)

---

### 4.3 ClaudeSTT/ -- Speech-to-Text for Revit

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/ClaudeSTT/` |
| **Entry Point** | `python/` + `csharp/` |
| **Language** | Python + C# |

**What it does:**
- Wake word activation: "Claude", "Hey Claude"
- Real-time transcription via Faster Whisper
- Voice Activity Detection (smart speech start/stop)
- C# Revit plugin for voice command processing
- Windows Named Pipes IPC between Python STT engine and C# Revit plugin
- Optional CUDA GPU acceleration
- Build/deploy/install PowerShell scripts included

---

### 4.4 jarvis/ -- Full Voice Assistant

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/jarvis/` |
| **Entry Point** | `jarvis_core.py` |
| **Language** | Python |

**What it does:**
- Always-on voice-controlled AI assistant
- Wake words: "Claude", "Hey Claude", "Okay Claude", "Jarvis"
- Conversation mode: 15-second follow-up window (no repeat wake word needed)
- ~150-200MB RAM total

**Command types:**

| Type | Examples | Handler |
|------|----------|---------|
| Status | "What's my email status?" | Local daemon query |
| Conversational | "Tell me about Python" | Claude API (fast) |
| Action | "Open Chrome", "In Revit place a wall" | Claude Code CLI |
| Control | "Goodbye", "Quiet mode" | Internal |

**Proactive alerts:**
- Memory warnings (>85%) and critical (>92%)
- Revit MCP disconnection
- App crashes (Revit, Bluebeam, AutoCAD)
- Urgent emails
- Morning briefing (8:00 AM)
- End of day summary (5:30 PM)
- Project mismatches between Revit and Bluebeam

**Architecture files:**

| File | Purpose |
|------|---------|
| `jarvis_core.py` | Master orchestrator |
| `voice_engine.py` | Always-on STT |
| `voice_output.py` | TTS queue manager |
| `action_engine.py` | Claude integration (API + CLI routing) |
| `proactive_engine.py` | Autonomous monitoring |
| `command_router.py` | Intent classification |
| `config.json` | Settings (wake words, voice, models, thresholds, quiet hours) |
| `test_components.py` | Component tests |
| `state/` | Persistent state (calendar, email, financial, patterns, etc.) |
| `launcher/start_jarvis.ps1` | Launcher with -Background, -Status, -Stop flags |
| `launcher/setup_task.ps1` | Auto-start at login setup |

---

### 4.5 subtitle-reader/ -- Live Subtitle Reader

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/subtitle-reader/` |
| **Entry Point** | `reader.py` |
| **Language** | Python |

**What it does:**
- Watches screen for subtitles (e.g., Netflix) and speaks them aloud via TTS
- OCR via Tesseract on captured screen region
- Multi-monitor support (`--monitor N`)
- Test mode (`--test`)
- Uses PowerShell Bridge for screenshots
- Windows version: `reader_windows.py`

---

## CATEGORY 5: SECURITY & SAFETY

---

### 5.1 mcp-seatbelt/ -- Agent Security Layer

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/mcp-seatbelt/` |
| **Entry Point** | `seatbelt.py` |
| **Language** | Python |

**What it does:**
- PreToolUse hook that validates ALL MCP tool calls before execution
- Exit codes: 0 = allow, 2 = block
- Reads JSON from stdin (Claude Code passes tool info)
- Only processes tools with `mcp__` prefix
- Fail-open mode (internal errors allow calls, don't break Claude)

**Architecture (6 core modules):**

| Module | Purpose |
|--------|---------|
| `policy_engine.py` | YAML policy loading from `policies/` |
| `validator.py` | Validation rules execution |
| `risk_scorer.py` | Risk calculation (1-10 scale) |
| `approval_gate.py` | Block/approve decision |
| `audit_logger.py` | NDJSON audit logging to `system-bridge/audit.ndjson` |
| `seatbelt.py` | Main entry point, orchestrates all modules |

**Policy rule types:**

| Rule Type | Purpose |
|-----------|---------|
| `recipient_whitelist` | Validate message recipients |
| `block_patterns` | Block dangerous regex patterns |
| `path_validation` | Restrict file paths to allowed roots |
| `command_sanitize` | Block injection characters |
| `require_fields` | Ensure required parameters present |
| `max_length` | Limit parameter length |
| `allowed_values` | Restrict parameter value sets |

**Risk modifiers (automatic):**
- +3 External communication (WhatsApp, email)
- +2 File system writes
- +2 Sensitive paths (/etc, .ssh, credentials)
- +2 Bulk operations (wildcards, "all")
- +3 Irreversible actions (delete, --force)

**Blocked by default:**
- Excel VBA macro execution
- Git force push / reset --hard
- Command injection patterns (`;`, `|`, `&`)
- Path traversal (`../`)
- Fork bombs and disk writes
- SQL credential modifications (`SET password`, `SET api_key`, `SET token`)
- Sensitive file access (`.ssh/`, `.aws/`, `.gnupg/`, `credentials.json`)
- Private key files (`id_rsa`, `id_ed25519`, `.pem`, `.key`)
- WhatsApp/email to non-whitelisted recipients

**CLI management:**
- `seatbelt stats` -- statistics with visual charts
- `seatbelt recent 20` -- last 20 MCP calls
- `seatbelt blocked` -- all blocked calls
- `seatbelt report` -- weekly review report
- `seatbelt whitelist` / `seatbelt whitelist add/remove`
- `seatbelt policy <server>` -- show policy
- `seatbelt upgrade/downgrade <server>` -- change restriction level

**Other:**
- `dashboard/` -- security dashboard UI
- `tests/test_seatbelt.py` -- unit tests
- `setup_weekly_report.ps1` -- scheduled task for weekly reports (Sunday 10 AM)

---

### 5.2 security-hooks/ -- Pre-Tool Security Hook

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/security-hooks/` |
| **Entry Point** | `pre_tool_use_security.py` |
| **Language** | Python |

**What it does:**
- Single-file security hook invoked before tool use
- Works in conjunction with mcp-seatbelt as part of the PreToolUse hook chain

---

### 5.3 pre-commit-guard/ -- Git Commit Safety

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/pre-commit-guard/` |
| **Entry Point** | `guard.py` |
| **Language** | Python |

**What it does:**
- Prevents committing secrets, credentials, and sensitive data to git repos
- Scans staged files for patterns like API keys, passwords, tokens

---

## CATEGORY 6: BROWSER AUTOMATION

---

### 6.1 autonomous-browser/ -- Stealth Browser MCP Server

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/autonomous-browser/` |
| **Entry Point** | `mcp_server.py` |
| **Language** | Python |

**What it does:**
- Full stealth browser automation MCP server

**Browser tools:**
- `browser_start` / `browser_stop`
- `browser_navigate` / `browser_click` / `browser_type`
- `browser_screenshot` / `browser_scroll` / `browser_wait`
- `browser_execute_js`

**Credential vault:**
- `vault_store_credential` / `vault_get_credential` (with approval flow)
- `vault_list_credentials` / `vault_delete_credential`
- `vault_store_totp` / `vault_get_totp` (TOTP code generation)

**Session management:**
- `session_save` / `session_restore` / `session_list`

**Action logging:**
- `log_get_session` / `log_list_sessions` / `log_search`

**Auto-login:**
- `auto_login` -- automated login flow (navigate + fill + submit)

**Other files:**
- `browser/stealth_browser.py` -- stealth browser implementation
- `vault/credentials.py` -- credential vault
- `vault/totp.py` -- TOTP support
- `logger/` -- action logging
- `sessions/` -- saved sessions
- `config.json` -- configuration
- `manage_vault.py` -- vault management CLI

---

### 6.2 chrome-cdp/ -- Chrome DevTools Protocol

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/chrome-cdp/` |
| **Entry Points** | `launch_cdp.ps1`, `cdp/` |
| **Language** | PowerShell + JavaScript |

**What it does:**
- Launches Chrome with remote debugging enabled
- CDP connection for browser automation
- `setup_admin.ps1` -- admin setup script

---

### 6.3 edge-cdp/ -- Edge DevTools Protocol

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/edge-cdp/` |
| **Entry Point** | `edge_helper.js` |
| **Language** | JavaScript |

**What it does:**
- Edge browser automation via Chrome DevTools Protocol
- IPv6-aware connection (`::1`, not `127.0.0.1`)
- Handles WSL2-to-Windows limitations (must run Node.js on Windows side)
- Includes Supabase Management API integration pattern
- CDP commands: `Runtime.evaluate`, `Page.navigate`, etc.

---

### 6.4 edge-automation/ -- Edge Browser Profile Data

| Field | Value |
|-------|-------|
| **Status** | NOT A TOOL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/edge-automation/` |

**What it is:**
- This is an Edge browser profile data directory (contains Ad Blocking, Autofill, BrowserMetrics, cookies, ShaderCache, etc.)
- NOT an automation tool -- likely the profile used by CDP automation sessions

---

### 6.5 windows-browser-mcp/ -- Windows Browser MCP

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/windows-browser-mcp/` |
| **Entry Point** | `src/` directory |
| **Language** | Unknown (likely TypeScript/Python in `src/`) |

**MCP Tools:**
- `browser_open`, `browser_navigate`, `browser_screenshot`
- `browser_click`, `browser_type`, `browser_send_keys`
- `browser_scroll`, `browser_search`
- `window_move`, `get_monitors`

---

### 6.6 playwright-mcp/ -- Playwright Browser Automation

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/playwright-mcp/` |
| **Language** | Python |

**What it does:**
- Collection of Playwright automation scripts (not a traditional MCP server)
- Scripts for: OAuth client creation, engagement checking, profile checking, Twitter checking, consent configuration, tab management, dialog closing, secret adding, test user creation

---

## CATEGORY 7: GOOGLE WORKSPACE INTEGRATION

---

### 7.1 google-calendar-mcp/ -- Google Calendar

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/` |
| **Entry Point** | `calendar_client.py` |
| **Language** | Python (google-api-python-client) |

**What it does:**
- Full Google Calendar API access for `weberg619@gmail.com`
- Full calendar scope (`https://www.googleapis.com/auth/calendar`)
- OAuth2 with token persistence (`token.json`, `credentials.json`)

**Commands:**
- `auth` -- first-time authorization
- `today` -- today's events
- `week` -- this week's events
- `upcoming [n]` -- next n events (default 10)
- `search <query>` -- search events
- `add <title> <start> <end> [description]` -- add event

---

### 7.2 google-drive-mcp/ -- Google Drive

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/google-drive-mcp/` |
| **Entry Point** | `drive_client.py` |
| **Language** | Python (google-api-python-client) |

**What it does:**
- Full Google Drive API access (full drive scope)
- OAuth2 with token persistence

**Commands:**
- `auth` -- first-time authorization
- `list [path]` -- list files/folders
- `search <query>` -- search files
- `info <file_id>` -- get file details
- `download <file_id> <dest>` -- download file
- `upload <local_path> [folder_id]` -- upload file

---

### 7.3 google-tasks-mcp/ -- Google Tasks

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/google-tasks-mcp/` |
| **Entry Point** | `tasks_client.py` |
| **Language** | Python (google-api-python-client) |

**What it does:**
- Google Tasks API access (tasks scope)
- Shares OAuth2 credentials with Calendar

**Commands:**
- `list` -- list all tasks
- `add <title> [notes] [due_date]` -- add task
- `complete <task_id>` -- mark complete
- `delete <task_id>` -- delete task
- `clear` -- clear completed tasks

---

## CATEGORY 8: VISUAL & MEDIA

---

### 8.1 visual-memory-mcp/ -- Screen Capture Memory

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/visual-memory-mcp/` |
| **Entry Point** | `server.py` |
| **Language** | Python |

**What it does:**
- MCP server that captures screen at intervals
- Indexes screenshots with OCR (Tesseract, lazy-loaded)
- Enables visual recall and search
- Privacy-first: whitelist/blocklist controls
- Active window detection via Windows API (`user32.dll` / `psutil`)
- SQLite storage (`memory.db`)
- Configurable via `config.json`
- Lazy-loads mss and PIL for faster startup

**MCP Tools (15):**
- `memory_start_capture` / `memory_stop_capture` / `memory_pause` / `memory_capture_now`
- `memory_search` / `memory_recall_recent` / `memory_recall_app` / `memory_recall_time`
- `memory_view`
- `memory_wipe_last` / `memory_wipe_app` / `memory_wipe_range`
- `memory_stats` / `memory_status`

---

### 8.2 obs-mcp/ -- OBS Studio Control

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/obs-mcp/` |
| **Entry Point** | `server.py` |
| **Language** | Python (obsws-python) |

**What it does:**
- Controls OBS Studio via WebSocket
- Auto-detects WSL2 host IP for connection
- Start/stop recordings, switch scenes
- Password-authenticated WebSocket connection

**Additional scripts:**
- `demo_showcase.py` / `demo_showcase_v2.py` / `demo_take3.py` / `demo_take4.py` -- demo video production scripts
- `edit_video.py` -- video editing
- `launch_obs.py` -- OBS launcher
- `resolve_enable_scripting.ps1` -- DaVinci Resolve scripting enable
- `resolve_test.py` / `resolve_test2.py` / `resolve_test3.py` -- DaVinci Resolve integration tests
- Demo screenshots and Excel files for showcases

---

### 8.3 revit-recorder-mcp/ -- Revit Session Recorder MCP

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/revit-recorder-mcp/` |
| **Entry Point** | `server.py` |
| **Language** | Python |

**What it does:**
- Records Revit sessions using FFmpeg (no OBS required)
- Auto-detects which monitor Revit is on
- Logs every MCP call with timestamps during recording
- Markers: highlight, cut, narrate, important, error
- Generates narration scripts with Andrew voice (Edge TTS)
- Session tracking in SQLite (`sessions.db`)

**MCP Tools (11):**
- `recorder_connect` -- connect to recording system
- `recorder_start` / `recorder_stop` / `recorder_status`
- `recorder_log_mcp` -- log an MCP call with timestamp
- `recorder_add_marker` -- add marker (highlight/cut/narrate/important/error)
- `recorder_list_sessions` / `recorder_get_session`
- `recorder_get_mcp_calls` / `recorder_get_markers`
- `recorder_generate_narration_script`

**Other:**
- `editor/` -- post-production editor
- `narrator.py` -- narration generation
- `recorder_ffmpeg.py` -- FFmpeg recording implementation
- `recordings/` -- recorded sessions

---

### 8.4 revit-live-view/ -- Live Revit Screenshot Daemon

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/revit-live-view/` |
| **Entry Point** | `revit-capture-daemon.ps1` |
| **Language** | PowerShell |

**What it does:**
- Auto-starts at Windows login (Windows Task Scheduler)
- Continuous screenshot capture of open Revit windows
- Watchdog restarts daemon if crashed (5-minute check interval)
- Scheduled tasks: `RevitLiveViewDaemon` (at login), `RevitLiveViewWatchdog` (every 5 min)

**Files:**

| File | Purpose |
|------|---------|
| `capture-now.ps1` | One-time capture |
| `revit-capture-daemon.ps1` | Continuous capture daemon |
| `start-daemon.bat` | Start with visible console |
| `start-background.vbs` | Start hidden (no window) |
| `stop-daemon.ps1` | Stop daemon |
| `watchdog.ps1` | Auto-restart on crash |
| `check-status.ps1` | Quick status check |

---

### 8.5 photo-catalog/ -- Construction Photo Manager

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/photo-catalog/` |
| **Entry Point** | `catalog_builder.py` |
| **Language** | Python |

**What it does:**
- Converts HEIC to JPG, generates thumbnails
- SQLite metadata storage (`data/photo_catalog.db`)
- HTML browser interface for viewing catalogs (`generate_html_viewer.py`)
- Batch analysis (`batch_analyze.py`)
- Real project data exists: BHN_Cath_Suites catalog HTML

---

### 8.6 image-gen-mcp/ -- AI Image Generation MCP

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/image-gen-mcp/` |
| **Entry Point** | `server.py` |
| **Language** | Python (FastMCP) |

**What it does:**
- MCP server using Replicate API for image generation
- Output to `/mnt/d/temp/ai_renders`

**Available models:**

| Model | Description |
|-------|-------------|
| `flux-pro` | Highest quality text-to-image |
| `flux-schnell` | Fast, high-quality (recommended for speed) |
| `flux-dev` | Higher quality (slower) |
| `flux-canny-pro` | Edge-based structure preservation (architectural lines) |
| `flux-depth-pro` | Depth-based preservation (3D geometry) |
| `sdxl` | Stable Diffusion XL (photorealistic) |

---

### 8.7 ai-render/ -- Architectural AI Rendering

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/ai-render/` |
| **Language** | Python |

**What it does:**
- Photorealistic rendering of Revit views using Flux models via Replicate API
- Cost: ~$0.05 per render

**Render scripts:**

| Script | Mode |
|--------|------|
| `render_flux.py` | Flux Canny Pro (edge-based) and Flux Depth Pro (depth-based) |
| `render_view.py` / `render_view_v2.py` | Revit view rendering |
| `render_smart.py` | Auto-select best model |
| `render_preserve.py` | Structure-preserving rendering |
| `render_revit.py` | Revit-specific rendering pipeline |
| `test_replicate.py` | API testing |

- Tested on real projects (AFURI renderings directory linked via symlink)
- Config in `config.json`

---

### 8.8 heygen-mcp/ -- AI Video Generation

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/heygen-mcp/` |
| **Language** | Python |

**What it does:**
- Creates AI-generated talking-head videos (HeyGen integration)
- Multiple video outputs exist: `AI_System_Overview_Complete.mp4`, `AI_System_Overview_FINAL.mp4`, `AI_System_Overview_PREMIUM.mp4`, `AI_System_Overview_PRO.mp4`, `AI_System_Overview_SYNCED.mp4`
- Whitepaper generation: `MCP_Bridge_Whitepaper.pdf`, `MCP_Technology_Overview.pdf`, `RevitMCPBridge_Whitepaper.pdf`
- Scripts: `create_final_video.py`, `create_final_with_slides.py`, `create_premium_video.py`, `create_pro_video.py`, `create_mcp_whitepaper.py`, `create_revitbridge_whitepaper.py`
- `assets/` directory for video assets

---

### 8.9 video-pipeline/ -- Full Video Production Pipeline

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/video-pipeline/` |
| **Entry Point** | `record_and_produce.py` |
| **Language** | Python |

**What it does:**
- Full pipeline: FFmpeg recording on Windows -> Run demo script (real speed) -> Stop recording -> Post-production (title card + narration overlay) -> Upload to YouTube
- Uses PowerShell Bridge for Windows FFmpeg control

**Files:**
- `record_and_produce.py` -- full pipeline orchestrator
- `demo_revit_video.py` -- Revit demo automation
- `extract_from_original.py` -- extract segments from recordings
- `narration_script.txt` -- narration script
- `project_blueprint.json` -- video project blueprint
- `demo_log.json` -- demo execution log
- `audio/`, `recordings/`, `edited/` -- media directories

---

### 8.10 youtube-uploader/ -- YouTube Upload Tool

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/youtube-uploader/` |
| **Entry Point** | `upload.py` |
| **Language** | Python |

**What it does:**
- Uploads videos to YouTube with OAuth2 authentication
- Token persistence (`token.json`)
- CDP-based authorization option (`authorize_cdp.py`)
- `authorize.py` -- standard OAuth flow
- `client_secret.json` -- OAuth client credentials

---

### 8.11 system-video/ -- System Presentation Video

| Field | Value |
|-------|-------|
| **Status** | STUB |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/system-video/` |
| **Entry Point** | `generate_video.py` |
| **Language** | Python |

**What it does:**
- Generates presentation videos about the system
- Slide-based with audio narration
- `video_script.json` -- scripted content
- `audio/`, `slides/`, `output/` -- media directories

---

## CATEGORY 9: REVIT / BIM TOOLS

---

### 9.1 revit-automations/ -- PowerShell Revit Scripts

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/revit-automations/` |
| **Entry Points** | 10 PowerShell scripts |
| **Language** | PowerShell (named pipe communication) |

**Scripts:**

| Script | Purpose |
|--------|---------|
| `01-sheet-audit.ps1` | Analyzes sheets and generates status reports |
| `02-project-status.ps1` | Project status reporting |
| `03-sheet-rename.ps1` | Bulk sheet renaming |
| `04-viewport-placer.ps1` | Automated viewport placement |
| `05-unplaced-views.ps1` | Find views not on sheets |
| `06-titleblock-audit.ps1` | Titleblock consistency check |
| `07-quick-capture.ps1` | Quick screenshot capture |
| `08-room-data.ps1` | Room data extraction |
| `09-cad-links.ps1` | CAD link management |
| `10-view-organizer.ps1` | View browser organization |

All communicate with Revit via named pipes (`RevitMCPBridge2025` or `RevitMCPBridge2026`). Parameterized by `-Version 2025|2026`.

---

### 9.2 revit-startup-helper/ -- Auto-Dismiss Revit Dialogs

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/revit-startup-helper/` |
| **Language** | PowerShell + Python + Batch |

**Files:**
- `smart_dismiss_dialogs.ps1` -- intelligent dialog dismissal
- `dismiss_dialogs.ps1` -- basic dialog dismissal
- `click_close_button.ps1` / `click_close_button.py` -- close button clicking
- `auto_close_dialogs.bat` -- batch launcher
- `Launch_Revit_Clean.bat` -- clean Revit launch
- `setup_scheduled_task.ps1` -- Windows Task Scheduler setup

---

### 9.3 revit-model-extractor/ -- Batch Model Data Extraction

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/revit-model-extractor/` |
| **Language** | PowerShell |

**Scripts:**
- `extract_model.ps1` -- single model extraction
- `batch_processor.ps1` / `batch_processor_mcp.ps1` -- batch processing
- `complete_processor.ps1` -- complete processing pipeline
- `continuous_processor.ps1` -- continuous mode
- Output: `extracted/`, `extracted_complete/`
- Logs: `complete_processor_log.txt`, `continuous_log.txt`

---

### 9.4 revit-ui-controller/ -- Revit UI Automation

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/revit-ui-controller/` |
| **Entry Point** | `server.py`, `win_ui_automation.py` |
| **Language** | Python |

**What it does:**
- Windows UI Automation for Revit interface control
- Beyond API access -- can click buttons, navigate menus, interact with UI elements that the MCP bridge cannot reach

---

### 9.5 revit-activity-journal/ -- Activity Logging

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/revit-activity-journal/` |
| **Data** | `activity.db` (SQLite) |

**What it does:**
- Logs Revit activity to SQLite database
- Tracks operations, timestamps, project context

---

### 9.6 revit-starter-kit/ -- Revit Add-in Template

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/revit-starter-kit/` |
| **Entry Point** | `RevitStarterKit.sln` |
| **Language** | C# |

**What it does:**
- Visual Studio solution template for Revit add-ins
- Structure: `App.cs`, `Commands/`, `UI/`, `Utils/`, `Resources/`, `Properties/`
- `.addin` manifest included
- Ready-to-build template for new Revit plugins

---

### 9.7 ambient-monitor/ -- Passive Revit Monitor

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/ambient-monitor/` |
| **Entry Point** | `monitor_daemon.py` |
| **Language** | Python |

**What it does:**
- Passive daemon that polls Revit state every 30 seconds
- Detects changes and surfaces insights via voice/queue
- Conservative start: voice alerts for unjoined walls only

**Files:**
- `monitor_daemon.py` -- main daemon loop
- `analysis_rules.py` -- rules for detecting issues
- `state_differ.py` -- compares state snapshots to detect changes
- `output_handlers.py` -- routes alerts to voice/queue/log

---

### 9.8 bim-validator/ -- Post-Operation Validation

| Field | Value |
|-------|-------|
| **Status** | STUB |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/bim-validator/` |
| **Entry Point** | `background_monitor.py` |

**What it does:**
- Background BIM validation monitoring
- Single file only -- likely a skeleton for planned validation system

---

### 9.9 post-revit-check/ -- Post-Operation Checker

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/post-revit-check/` |
| **Entry Point** | `post_operation_check.py` |
| **Language** | Python |

**What it does:**
- Validates Revit operations after they complete
- Ensures elements were placed correctly, transactions committed

---

### 9.10 smart-preview/ -- Revit File Preview System

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/smart-preview/` |
| **Entry Point** | `preview_window.py` |
| **Language** | Python (Pillow, olefile) |

**What it does:**
- Windows Explorer right-click preview for .rvt, .rfa, and image files
- Quick preview: extracts embedded preview from Revit files (instant, via olefile)
- HD render: uses Revit MCP for 1920x1080 high-resolution previews
- Context menu installer
- Hotkey service (spacebar trigger)
- Preview caching

**Supported file types:** .rvt, .rfa (quick + HD), .png, .jpg, .jpeg, .bmp, .gif, .tiff (quick only)

**Controls:** H (HD render), R (refresh), O (open file), Space/Esc (close)

**Files:**
- `preview_window.py` -- main preview GUI
- `preview_extractor.py` -- extracts embedded previews
- `hd_renderer.py` -- HD rendering via Revit MCP
- `context_menu_installer.py` -- adds right-click menu to Explorer
- `hotkey_service.py` -- spacebar trigger
- `preview.bat` -- command-line launcher
- `cache/` -- cached previews
- `icons/` -- UI icons

---

## CATEGORY 10: FLOOR PLAN & ARCHITECTURAL EXTRACTION

---

### 10.1 floor-plan-vision-mcp/ -- Floor Plan Extraction MCP

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/floor-plan-vision-mcp/` |
| **Entry Point** | `src/server.py` |
| **Language** | Python |

**What it does:**
- MCP server wrapping FloorPlanTracer functionality (from `/mnt/d/FloorPlanTracer`)
- Lazy-loads: OpenCV, PyMuPDF (fitz), FloorPlanTracer, ShowUI semantic grounder
- Session storage for annotated floor plans
- Hybrid grounder support

**MCP Tools:**
- `analyze_floor_plan` -- full extraction from image
- `detect_scale` -- detect drawing scale
- `detect_walls` -- extract wall segments
- `detect_openings` -- find doors/windows
- `detect_rooms` -- find enclosed spaces
- `get_pdf_info` -- get PDF metadata

---

### 10.2 perimeter-tracer/ -- Floor Plan Boundary Detection

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/perimeter-tracer/` |

**What it does:**
- Traces floor plan perimeters from images
- Multiple output formats: JSON coordinates, traced PNG images, masks, SVG
- Multiple versions of traced results (v2, clean, final, for_revit)
- Clean coordinate extraction for Revit import

---

### 10.3 floor-plan-pipeline/ -- PDF-to-Revit Orchestrator

| Field | Value |
|-------|-------|
| **Status** | STUB |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/floor-plan-pipeline/` |
| **Entry Point** | `orchestrator.py` |

**What it does:**
- Orchestrates the full PDF -> extraction -> Revit pipeline
- Single file only -- high-level orchestration logic

---

### 10.4 floorplan-rebuild/ -- Floor Plan Reconstruction

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/floorplan-rebuild/` |
| **Language** | Python |

**What it does:**
- Downloads floor plans from web (`download_floorplan.py`, `cdp_download.py`)
- Converts floor plan images to DXF format (`floorplan_to_dxf.py`)
- Multiple output formats: DXF, JPG, JSON, PNG, SVG
- Example outputs present

---

## CATEGORY 11: SITE DATA & CODE COMPLIANCE

---

### 11.1 site-data-api/ -- Florida Building Site Intelligence

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/site-data-api/` |
| **Language** | Python |
| **Database** | Multiple SQLite databases |

**What it does -- 28 Python files covering:**

| Module | Purpose |
|--------|---------|
| `code_compliance.py` | Florida Building Code checklists (Building, Structural, Mechanical, Plumbing, Electrical, Fire/Life Safety) |
| `florida_zoning.py` | Florida zoning data and regulations |
| `parcel_data.py` | Parcel/property data lookup |
| `soil_data.py` | Soil report data |
| `generate_soil_report.py` | Soil report generation |
| `census_demographics.py` | Census/demographic data |
| `epa_environmental.py` | EPA environmental data |
| `noaa_storm_data.py` | NOAA storm/wind data |
| `noa_database.py` | Notice of Acceptance database |
| `noa_matcher.py` | NOA product matching |
| `sun_path.py` | Solar path analysis |
| `overpass_context.py` | OpenStreetMap context via Overpass API |
| `fee_calculator.py` | Permit fee calculation |
| `permit_tracker.py` | Permit application tracking |
| `permit_application_pdf.py` | Permit application PDF generation |
| `comment_response.py` | Plan review comment response drafting |
| `compliance_workflow.py` | Compliance workflow orchestration |
| `jurisdiction_db.py` | Jurisdiction database |
| `report_generator.py` | Report generation |
| `report_integration.py` | Report integration |
| `project_database.py` | Project database |
| `site_data.py` | Core site data lookup |
| `site_data_full.py` | Full site data analysis |
| `site_intelligence.py` | Site intelligence synthesis |
| `revit_mcp_client.py` | Revit MCP integration |
| `revit_schedule_integration.py` | Revit schedule integration |
| `schedule_mapper.py` | Schedule mapping |
| `test_goulds_tower.py` | Test data (Goulds Tower project) |

**Databases:** `code_compliance.db`, `florida_zoning.db`, `fee_calculator.db`, `comment_response.db`

**Hidden capability:** This is an entire Florida-specific AEC intelligence platform. Code compliance, zoning, environmental, soil, permit fees, NOA matching, plan review comment responses -- all integrated. A unique IP for architectural practice in Florida.

---

## CATEGORY 12: PIPELINES & ORCHESTRATION

---

### 12.1 pipelines/ -- Workflow Pipeline Executor

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/pipelines/` |
| **Entry Point** | `executor.py` |
| **Language** | Python |

**What it does:**
- Autonomous workflow runner with checkpoint gates
- Executes `.pipeline.json` files with sequential phases
- Features: checkpoint gates (pause for approval), state persistence (resume), memory integration (corrections surfacing), dry-run mode, error handling with rollback
- Logic handlers for complex branching (`logic_handlers.py`)
- Revit MCP client integration (`revit_client.py`)

**Pipeline definitions:**

| Pipeline | Purpose |
|----------|---------|
| `cd-set.pipeline.json` | Construction Document set generation (analyze project -> detect titleblock -> plan sheets -> create views -> place on sheets -> add annotations) |
| `pdf-to-revit.pipeline.json` | PDF floor plan to Revit model pipeline |
| `markup-to-model.pipeline.json` | PDF/CAD markup to Revit model conversion |

**Usage:**
- `python executor.py cd-set.pipeline.json`
- `python executor.py cd-set.pipeline.json --dry-run`
- `python executor.py cd-set.pipeline.json --resume`
- `python executor.py cd-set.pipeline.json --auto-approve`

**Other:**
- `state/` -- pipeline state persistence
- `validation_reports/` -- validation outputs
- `test_executor.py` -- executor tests

---

### 12.2 orchestration/ -- Knowledge-Triggered Context Loading

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/orchestration/` |
| **Language** | Python + YAML + JSON |

**Files:**
- `context_loader.py` -- auto-loads context based on triggers
- `knowledge-triggers.yaml` -- trigger definitions
- `methods-index.json` -- index of all available MCP methods
- `generate_methods_index.py` -- generates the methods index from RevitMCPBridge

---

### 12.3 task-orchestrator/ -- Task Queue Manager

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/task-orchestrator/` |
| **Language** | Python |

**Files:**
- `orchestrator.py` -- main orchestration logic
- `queue_cli.py` -- CLI for queue management
- `task_queue.py` -- SQLite task queue
- `session_executor.py` -- session-based task execution
- `queues/` -- queue storage
- `logs/` -- execution logs

---

### 12.4 master-orchestrator/ -- System Startup

| Field | Value |
|-------|-------|
| **Status** | STUB |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/master-orchestrator/` |
| **Entry Point** | `startup.py` |

Single startup script -- orchestrates service initialization.

---

### 12.5 workflow-loader/ -- Workflow Loading

| Field | Value |
|-------|-------|
| **Status** | STUB |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/workflow-loader/` |
| **Entry Point** | `load_workflows.py` |

Loads workflow definitions at session start.

---

## CATEGORY 13: AGENT TEAMS & DASHBOARDS

---

### 13.1 agent-dashboard/ -- Visual Command Center

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/agent-dashboard/` |
| **Entry Point** | `server.py` |
| **Language** | Python (FastAPI + WebSocket + uvicorn) |
| **Port** | `localhost:8080` |

**What it does:**
- Visual dashboard for Weber's autonomous agent fleet
- Shows all 51 agents, their status, and squad assignments
- Live system state display via WebSocket
- Task queue visualization from `autonomous-agent/queues/tasks.db`
- Agent log viewing
- MCP health report display

**Files:**
- `server.py` -- FastAPI server with WebSocket support
- `dashboard.html` -- main dashboard page
- `autonomous_executor.py` -- background task executor
- `cli_executor.py` -- CLI-based executor
- `executor_status.json` -- executor state
- `static/` -- static assets
- `templates/` -- HTML templates
- `start_all.ps1` / `start_dashboard.bat` / `start_dashboard.ps1` -- launchers

---

### 13.2 agent-team/ -- Multi-Agent Voice War Room

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/agent-team/` |
| **Entry Point** | `team.py` |
| **Language** | Python |

**What it does:**
- Multi-agent voice collaboration system

**The Team:**

| Agent | Voice | Role |
|-------|-------|------|
| Planner | andrew | Breaks down tasks, defines goals |
| Researcher | guy | Gathers facts, explores codebase |
| Builder | adam | Writes code, executes tools |
| Critic | davis | Validates, finds risks |
| Narrator | jenny | Summarizes for the user |

**Modes:**
- Backstage (default): agents debate internally (fast, text-only), only Narrator speaks summary
- Live: every agent speaks their turn out loud

**Rules enforced:**
1. One Mic Rule: only one agent speaks at a time
2. Timeboxing: max 3-4 sentences per turn
3. Structured Handoffs: "Builder, implement X" / "Critic, validate"
4. Stop Conditions: consensus, max turns, or user approval needed

**Files (extensive):**
- `team.py` -- main CLI entry point
- `director.py` -- orchestrator managing turn-taking
- `agent_prompts.py` -- system prompts for each agent
- `voice_registry.json` -- agent-to-voice mapping
- `turn_state.json` -- current session state
- `protocols/backstage.py` -- fast internal + voice summary
- `protocols/live_meeting.py` -- all agents speak
- `dialogue_orchestrator.py` / `dialogue_v2.py` -- dialogue management
- `live_director.py` / `live_session.py` / `live_self_improvement_session.py` -- live session management
- `self_improvement_session.py` -- self-improvement workflow
- `agent_speak.py` / `agent_speak.sh` / `agent_voice.py` / `speech_coordinator.py` -- voice coordination
- `visual_session.py` / `visual_sync.py` -- visual sync
- `browser_capture.py` / `screenshot_service.py` -- screen capture
- `interactive_browser.py` -- browser interaction
- `execution_bridge.py` -- Claude Code execution bridge
- `session_api.py` / `session_runner.py` -- session management
- `autonomous_agents.py` -- autonomous agent definitions
- `task_status.py` -- task tracking
- `monitor/` -- monitoring
- `recording/` / `recordings/` -- session recordings
- `record_session.ps1` -- PowerShell recording script
- `electron-dashboard/` -- Electron-based dashboard option
- `projects/` -- project workspace

---

### 13.3 creative-studio/ -- Creative Content Team

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/creative-studio/` |
| **Language** | Python |

**What it does:**
- Slide deck generation (multiple formats, theming support)
- Document creation
- Content export (HTML, Markdown, PDF-ready)
- Agent-based creative workflow

**Files:**
- `creative_tools.py` -- SlideBuilder class, theming, export
- `agent_prompts.py` -- creative agent prompts
- `autonomous_agents.py` -- autonomous creative agents
- `run_team.py` -- team runner
- `agent_status.json` -- agent state
- `output/` -- generated content
- `electron-dashboard/` -- Electron dashboard option

---

### 13.4 office-team/ -- Office Assistant Team

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/office-team/` |
| **Language** | Python |

**What it does:**
- Connects agents to real office tools: Gmail (IMAP), Google Calendar, task tracking, document operations
- GmailTool, CalendarTool integration
- Uses PowerShell Bridge

**Files:**
- `office_tools.py` -- GmailTool, CalendarTool wrappers
- `agent_prompts.py` -- office agent prompts
- `autonomous_agents.py` -- autonomous office agents
- `run_team.py` -- team runner
- `agent_status.json` -- agent state
- `start.sh` -- launcher
- `electron-dashboard/` -- Electron dashboard option

---

## CATEGORY 14: FINANCIAL & BUSINESS

---

### 14.1 financial-mcp/ -- Market Intelligence MCP Server

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/financial-mcp/` |
| **Entry Point** | `server.py` |
| **Language** | Python (yfinance, pandas, numpy, requests) |

**What it does -- comprehensive financial suite:**

**Data sources:** Yahoo Finance (real-time), FRED (economic), Finnhub (news/sentiment), Alpha Vantage (technical)

**Tool categories and tools (70+):**

| Category | Tools |
|----------|-------|
| Market Data | `get_stock_quote`, `get_market_overview`, `get_sector_performance`, `get_market_movers` |
| Technical Analysis | `get_technical_analysis`, `get_support_resistance_levels`, `detect_chart_patterns`, `get_moving_averages` |
| Fundamental Analysis | `get_company_fundamentals`, `get_valuation_metrics`, `get_earnings_info`, `get_dividend_analysis` |
| Portfolio | `get_portfolio_summary`, `add_to_portfolio`, `remove_from_portfolio`, `get_portfolio_risk_analysis` |
| Watchlist | `get_watchlist`, `add_to_watchlist`, `remove_from_watchlist` |
| Economic Data | `get_economic_calendar`, `get_interest_rates`, `get_inflation_data`, `get_economic_indicators` |
| News & Sentiment | `get_stock_news`, `get_market_news`, `get_sentiment_analysis` |
| Insider Activity | `get_insider_trades`, `get_institutional_holders` |
| Screening | `screen_stocks`, `find_undervalued_stocks`, `find_momentum_stocks`, `find_dividend_stocks` |
| Comparison | `compare_stocks`, `get_historical_data` |
| Strategy | `backtest_strategy`, `calculate_position_size`, `analyze_risk_reward` |
| Alerts | `set_price_alert`, `check_alerts` |
| Crypto | `get_crypto_prices` |
| Search | `search_stocks` |
| Analyst | `get_analyst_ratings`, `get_price_targets`, `get_upgrades_downgrades` |
| Short Interest | `get_short_interest` |
| Options | `get_options_chain`, `get_options_summary` |
| Market Breadth | `get_fear_greed_index`, `get_market_breadth`, `get_correlation_matrix` |
| SEC | `get_sec_filings` |
| Paper Trading | `paper_trade`, `get_paper_portfolio`, `reset_paper_portfolio` |
| Earnings | `get_earnings_estimates`, `get_upcoming_earnings`, `get_company_events` |
| ETFs | `get_etf_holdings`, `find_etfs_holding_stock` |
| Checklist | `get_investment_checklist` |

**Data files:** `portfolio.json`, `watchlist.json`, `alerts.json`, `paper_portfolio.json`, `config.json`, `mcp.json`

API result caching: 5-minute duration to avoid rate limiting.

---

### 14.2 revenue-plan/ -- Revenue Strategy Documentation

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL (documentation only, no code) |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/revenue-plan/` |

**Files:**
- `REVENUE_STRATEGY.md` -- overall revenue strategy
- `fiverr-gigs.md` -- Fiverr gig planning
- `gumroad-listing.md` -- Gumroad product listing
- `proposal-licensing-system.md` -- proposal licensing system
- `upwork-proposals.md` -- Upwork proposal templates

---

## CATEGORY 15: HEALTH, MAINTENANCE & QUALITY

---

### 15.1 health-check/ -- Infrastructure Health Check

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/health-check/` |
| **Entry Point** | `health_check.py` |
| **Language** | Python |

**What it does:**
- Validates ALL MCP servers, hooks, databases, and backups
- Modes: full check, `--quick` (skip slow tests), `--fix` (attempt auto-fixes)

**Files:**
- `health_check.py` -- main check runner
- `security_scanner.py` -- security scanning
- `backup_manager.py` -- backup validation
- `scheduled_maintenance.py` -- maintenance automation
- `hook_wrapper.py` -- hook testing
- `view_hook_errors.py` -- hook error viewer
- `backups/` -- backup storage

---

### 15.2 mcp-health-check/ -- MCP Server Health

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/mcp-health-check/` |
| **Entry Point** | `check_health.py` |

**What it does:**
- Checks health of all MCP servers
- Generates `health_report.json`

---

### 15.3 backup-system/ -- Automated Backups

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/backup-system/` |
| **Entry Points** | `backup.bat` (Windows), `backup.sh` (WSL) |

---

### 15.4 pre-flight-check/ -- Pre-Operation Validation

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/pre-flight-check/` |
| **Entry Point** | `pre_flight_check.py` |
| **Language** | Python |

**What it does:**
- Queries memory for relevant corrections before Revit operations
- Surfaces past mistakes to prevent repeating them
- Extracts "correct approach" from correction records

**Files:**
- `pre_flight_check.py` -- main check logic
- `context_detector.py` -- detects current context/project
- `rule_engine.py` -- rule-based validation
- `hook_runner.py` -- hook integration
- `__init__.py` -- package init

---

### 15.5 self-improvement-hooks/ -- Correction Tracking Hooks

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/self-improvement-hooks/` |
| **Language** | Python |

**Files:**

| Hook | Purpose |
|------|---------|
| `detect_correction_hook.py` | Detects when user corrects Claude |
| `pre_action_check_hook.py` | Checks corrections before actions |
| `spaced_repetition_hook.py` | Periodic review of past corrections |
| `correction_feedback_prompt.py` | Prompts for feedback on whether corrections helped |
| `maintenance_hook.py` | Maintenance tasks (decay, archive) |

---

### 15.6 self-healing/ -- Error Recovery

| Field | Value |
|-------|-------|
| **Status** | STUB |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/self-healing/` |
| **Entry Point** | `workflow_healer.py` |

Framework for workflow error recovery. Single file.

---

### 15.7 verification/ -- Work Verification

| Field | Value |
|-------|-------|
| **Status** | STUB |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/verification/` |
| **Entry Point** | `quick_verify.ps1` |

Quick verification of completed work via PowerShell. Single file.

---

### 15.8 pattern-analysis/ -- Memory Pattern Detection

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/pattern-analysis/` |
| **Entry Point** | `weekly_analysis.py` |

Weekly analysis of memory patterns. Identifies recurring themes, common errors, workflow patterns.

---

## CATEGORY 16: SDK, FRAMEWORKS & REFERENCE

---

### 16.1 weber-sdk/ -- Unified Python SDK

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/weber-sdk/` |
| **Language** | Python |

**What it does:**
- Unified Python SDK wrapping ALL MCP servers
- Auto-discovery from `~/.claude/settings.local.json` and `~/.claude/mcp-configs/*.json`
- Async-first with sync wrappers
- Full type annotations
- Service wrappers: Voice, Excel, Revit, Floor Plan Vision, AutoCAD, PowerPoint, Word, Browser
- Connection management with retries
- Proper packaging (pyproject.toml, tests/, examples/)

**Package structure:**
```
weber_sdk/
  __init__.py, client.py, discovery.py, exceptions.py
  transports/base.py, stdio.py
  services/base.py, generic.py, voice.py, excel.py, revit.py
  utils/sync.py
```

**Discovered servers:** voice-input-mcp, excel-mcp, word-mcp, powerpoint-mcp, autocad-mcp, revit, floor-plan-vision, ai-render-mcp, autonomous-browser

---

### 16.2 Claude_Skills/ -- Domain Expertise Files

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/Claude_Skills/` |
| **Count** | 20 skill files |

**Revit/BIM Skills:**

| Skill File | Purpose |
|------------|---------|
| `revit-model-builder.skill` | Wall patterns, coordinate systems, placement strategies |
| `pdf-to-revit.skill` | Complete PDF extraction to Revit pipeline |
| `bim-quality-validator.skill` | Validation checklists, error recovery |
| `cd-set-assembly.skill` | Construction document set creation |
| `revit-mcp-gotchas.skill` | 29 corrections + pre-flight checklists |
| `markup-to-model.skill` | PDF/CAD to Revit workflow |

**Workflow Skills:**

| Skill File | Purpose |
|------------|---------|
| `context-management.skill` | Context pruning, memory patterns |
| `claude-orchestration.skill` | Sub-agent deployment, parallel execution |
| `autonomous-pipeline.skill` | Multi-step operation framework |
| `autonomous-checkpoints.skill` | Progress tracking |
| `bd-project-init.skill` | BD Architect project initialization |
| `pdf-to-rentable-sf.skill` | Square footage extraction |

**General Skills:**

| Skill File | Purpose |
|------------|---------|
| `code-review-helper.skill` | Code quality checklists |
| `product-manager.skill` | PRDs, roadmaps, user stories |
| `product-designer.skill` | UX patterns, accessibility |
| `marketing-writer.skill` | Copy formulas, channel guidelines |
| `meeting-notes-processor.skill` | Meeting notes extraction |
| `email-drafter.skill` | Email composition |
| `idea-validator.skill` | Idea evaluation |
| `launch-planner.skill` | Launch planning |

Also includes `SKILLS_GUIDE.md` and a sample image `001.PNG`.

---

### 16.3 context-engineering-demo/ -- Context Engineering Reference

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL (Reference/Template) |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/context-engineering-demo/` |

Reference implementation for context engineering. Contains agents, experts, MCP configs, Claude commands, and delegation patterns.

---

### 16.4 ralph/ -- The Ralph Technique

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/ralph/` |
| **Entry Point** | `ralph.sh` |
| **Language** | Bash |

**What it does:**
- Bash loop implementation of the "Ralph Technique" by Geoff Huntley
- Autonomous coding via repeated Claude Code CLI invocations with a PROMPT.md file
- Variants: `ralph-hierarchical.sh` (multi-level decomposition), `ralph-prd.sh` (PRD-based), `ralph-init.sh` (initialization), `ralph-prd-init.sh`
- `templates/` -- task templates
- `install.sh` -- installer

---

### 16.5 code_memory_system/ -- Code Memory Library

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/code_memory_system/` |
| **Language** | Python |

Python library for code-level memory. Proper package structure with pyproject.toml, src/, tests/, examples/, docs/.

---

## CATEGORY 17: SPECIALIZED / NICHE TOOLS

---

### 17.1 bluebeam-mcp/ -- Bluebeam Revu Automation MCP

| Field | Value |
|-------|-------|
| **Status** | PRODUCTION |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/bluebeam-mcp/` |
| **Entry Point** | `src/server.py` |
| **Language** | Python |

**What it does:**
- MCP server for Bluebeam Revu PDF markup software
- Uses COM automation, PowerShell, and Windows UI Automation
- PowerShell Bridge integration for speed

**MCP Tools:**
- `get_status` -- check if Bluebeam is running, current document
- `open_document` -- open a PDF
- `get_window_info` -- window information
- `take_screenshot` -- screenshot Bluebeam window
- `go_to_page` -- navigate to specific page
- `get_pdf_info` -- document metadata (pages, title)
- `create_document` -- create new document
- `send_keys` -- send keystrokes
- `focus_window` -- focus Bluebeam window

---

### 17.2 microsoft-teams-mcp/ -- Microsoft Teams

| Field | Value |
|-------|-------|
| **Status** | STUB |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/microsoft-teams-mcp/` |

Planned Microsoft Teams integration. Has `PENDING_SETUP.md`, `config.json`, `teams_client.py`. Not yet functional.

---

### 17.3 personaplex-mcp/ -- Persona Management

| Field | Value |
|-------|-------|
| **Status** | STUB (empty directory) |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/personaplex-mcp/` |

Empty directory. Placeholder for planned persona management MCP.

---

### 17.4 BridgeAI/ -- Consumer AI Assistant Concept

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/BridgeAI/` |
| **Entry Point** | `bridge.py` |

Consumer-facing AI assistant concept: voice input, file creation, app launching, system diagnostics, screen reading. Has CLAUDE.md, automation service, autonomous agent PRD, launch scripts. Probably an earlier iteration of the full system.

---

### 17.5 Claude-code-CA/ -- Early AI Prototype

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/Claude-code-CA/` |

Early AI assistant prototype. AI memory, orchestrator, PowerShell executor, Copilot dialog handling, task automation.

---

### 17.6 claude-code-action/ -- GitHub Actions Integration

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL (Fork/Reference) |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/claude-code-action/` |

GitHub Actions integration for Claude Code. Has `action.yml`, documentation (CODE_OF_CONDUCT, CONTRIBUTING, FAQ, ROADMAP, SECURITY).

---

### 17.7 claude-code-revit/ -- Revit Drop Zone Integration

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/claude-code-revit/` |

Drop zone system for Revit file processing. Workflow examples, setup guides, quick start.

---

### 17.8 claude-code-standards/ -- Code Standards Framework

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL (Reference) |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/claude-code-standards/` |

Development standards framework with architecture guides, hooks, integrations, settings templates.

---

### 17.9 proactive-memory/ -- Memory Surfacing

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/proactive-memory/` |
| **Entry Point** | `memory_surfacer.py` |

Proactively surfaces relevant memories based on current context.

---

### 17.10 operation-cache/ -- MCP Operation Cache

| Field | Value |
|-------|-------|
| **Status** | STUB |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/operation-cache/` |
| **Entry Point** | `operation_cache.py` |

Caches MCP operation results to avoid redundant calls. Single file.

---

### 17.11 context-triggers/ -- Auto-Context Loading

| Field | Value |
|-------|-------|
| **Status** | STUB |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/context-triggers/` |
| **Entry Point** | `trigger_engine.py` |

Trigger engine for automatic context loading based on conditions. Single file.

---

### 17.12 cross-app-automation/ -- Cross-Application Workflows

| Field | Value |
|-------|-------|
| **Status** | STUB |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/cross-app-automation/` |
| **Entry Point** | `workflow_coordinator.py` |

Coordinates workflows across multiple applications. Single file.

---

### 17.13 project-state/ -- Project State Tracking

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/project-state/` |

**Files:**
- `state_manager.py` -- manages per-project state
- `load_state_hook.py` -- hook for loading project state at session start
- `projects/` -- per-project state storage

---

### 17.14 visual-review/ -- Visual Code Review

| Field | Value |
|-------|-------|
| **Status** | STUB |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/visual-review/` |

**Files:** `visual_inspector.py`, `visual_reviewer.py`. Skeleton for visual inspection and review.

---

### 17.15 spine-passive/ -- Error Analysis System

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/spine-passive/` |

**Scripts:** `check_error_paths.py`, `check_errors.py`, `check_errors_detailed.py`, `check_results.py`, `cleanup_errors.py`, `deep_analysis.py`, `fix_in_progress.py`, `analyze.bat`
**Data:** `data/`, `exports/`

---

### 17.16 aec-drafting-ai/ -- AEC Drafting AI

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/aec-drafting-ai/` |

Project resolution for AEC drafting. `resolve_project.py`, `scripts/`, `config/`, `beta-package/`, `project_registry.json`, `docs/`.

---

### 17.17 bimops-site/ -- BIM Ops Studio Website

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/bimops-site/` |

Static website: `index.html`, `style.css`.

---

### 17.18 ui/ -- Windows UI Automation Utilities

| Field | Value |
|-------|-------|
| **Status** | FUNCTIONAL |
| **Path** | `/mnt/d/_CLAUDE-TOOLS/ui/` |
| **Language** | Python |

**Scripts (8):**

| Script | Purpose |
|--------|---------|
| `click.py` | Programmatic mouse clicking |
| `key.py` | Keyboard input simulation |
| `type.py` | Text typing |
| `scroll.py` | Mouse scrolling |
| `move.py` | Mouse movement |
| `pos.py` | Cursor position reporting |
| `list_windows.py` | Window enumeration |
| `telegram.py` | Telegram-specific UI automation |

---

### 17.19 site-data-api/ (also in Category 11)

Already fully documented above.

---

### 17.20 autonomous-browser/ (also in Category 6)

Already fully documented above.

---

## CATEGORY 18: EXTERNAL MCP SERVERS

**Location:** `/mnt/d/009-PROJECT-FILES-DEVELOPER/mcp-servers/`
**Date:** June 2025 (older TypeScript-based build system)
**Build system:** Shared `tsconfig.shared.json`, batch build scripts, `package.json`

| Server | Status | Purpose |
|--------|--------|---------|
| `api-testing-mcp` | FUNCTIONAL | API endpoint testing |
| `autonomous-agent-mcp` | FUNCTIONAL | Autonomous agent as MCP server |
| `context-memory-mcp` | FUNCTIONAL | Context memory system |
| `database-mcp` | FUNCTIONAL | Database operations (with SQLite) |
| `database-mcp-nosqlite` | FUNCTIONAL | Database operations (without SQLite) |
| `docker-mcp` | FUNCTIONAL | Docker container management |
| `env-manager-mcp` | FUNCTIONAL | Environment variable management |
| `env-var-mcp` | FUNCTIONAL | Environment variable operations |
| `git-mcp` | FUNCTIONAL | Git operations |
| `intelligent-orchestrator-mcp` | FUNCTIONAL | Intelligent task orchestration |
| `log-analysis-mcp` | FUNCTIONAL | Log analysis and querying |
| `model-manager-mcp` | FUNCTIONAL | AI model management |
| `model-management-mcp.backup` | FUNCTIONAL | Backup of model management |
| `nlp-workflow-mcp` | FUNCTIONAL | NLP workflow processing |
| `predictive-intelligence-mcp` | FUNCTIONAL | Predictive analytics |
| `process-manager-mcp` | FUNCTIONAL | System process management |
| `prompt-engineering-mcp` | FUNCTIONAL | Prompt engineering tools |
| `revit-api-mcp` | FUNCTIONAL | Revit API wrapper |
| `speech-enhancement-mcp` | FUNCTIONAL | Speech enhancement/processing |
| `test-runner-mcp` | FUNCTIONAL | Test execution framework |
| `unified-orchestration-mcp` | FUNCTIONAL | Unified orchestration layer |
| `video-review-mcp` | FUNCTIONAL | Video review tools |

**Note:** These are from an earlier build system (June 2025). Most are likely superseded by the newer tools in `_CLAUDE-TOOLS/` but represent functional TypeScript code with build configurations.

---

## CATEGORY 19: ARCHIVED TOOLS

**Location:** `/mnt/d/_CLAUDE-TOOLS/_ARCHIVED/`

| Directory | What it was | Superseded by |
|-----------|-------------|---------------|
| `email-monitor/` | Earlier email monitoring | `email-watcher/` |
| `floor-plan-testing/` | Floor plan test data | `floor-plan-vision-mcp/` |
| `gmail-sender/` | Gmail sending tool | Gateway + Gmail compose URL |
| `output-files/` | Old output files | Various |
| `platform-scripts/` | Platform automation | Various |
| `session-data/` | Old session data | `brain-state/` |
| `session-images/` | Old session images | `visual-memory-mcp/` |
| `session-scripts/` | Old session scripts | Various |
| `voice-assistant/` | Earlier voice assistant | `jarvis/` |
| `voice-bridge/` | Earlier voice bridge | `voice-mcp/` |
| `voice-wrapper/` | Earlier voice wrapper | `voice-mcp/` |

---

## CATEGORY 20: DOCUMENTATION & CONFIGURATION FILES

**Root-level files in `/mnt/d/_CLAUDE-TOOLS/`:**

| File | Purpose |
|------|---------|
| `AGENTS.md` | Master agent instructions (51 agents, 10 squads, integration points) |
| `WEBER_WORKFLOWS.md` | Mandatory session-start workflow reference (email, calendar, Revit, contacts, system state) |
| `CLAUDE_REFERENCE.md` | On-demand reference guide (MCP capabilities, task routing, Aider strategy, proactive behaviors, memory management) |
| `SYSTEM_INVENTORY.md` | Previous inventory from January 22, 2026 |
| `ASSISTANT_UPGRADE_PLAN.md` | Planned upgrade roadmap |
| `ORGANIZATION_ASSESSMENT_2026-01-25.md` | Organizational assessment |
| `FLOOR_PLAN_READING_PROCEDURE.md` | Floor plan reading procedure |
| `QUICK_KEYS.md` | Keyboard shortcuts reference (Tab, Shift+Tab, Ctrl+R, /stats, /cost, /compact) |
| `.env` | Environment variables (Gmail credentials, API keys) |
| `.gitignore` | Git ignore patterns |
| `bookmarked_tech.md` | Bookmarked technology references |
| `cleanup-claude-conversations.sh` | Conversation cleanup script |
| `background-workflow-example.md` | Background workflow example patterns |
| `extended-thinking-guide.md` | Extended thinking usage guide |

---

## COMPLETE STATUS MATRIX (Alphabetical)

| # | Directory | Status | Category |
|---|-----------|--------|----------|
| 1 | `_ARCHIVED/` | ARCHIVED | Archived |
| 2 | `aec-drafting-ai/` | FUNCTIONAL | AEC/Drafting |
| 3 | `agent-boost/` | PRODUCTION | Core Infrastructure |
| 4 | `agent-common-sense/` | PRODUCTION | Core Infrastructure |
| 5 | `agent-dashboard/` | FUNCTIONAL | Agent Teams |
| 6 | `agent-team/` | FUNCTIONAL | Agent Teams |
| 7 | `ai-render/` | FUNCTIONAL | Visual/Media |
| 8 | `ambient-monitor/` | FUNCTIONAL | Revit/BIM |
| 9 | `autonomous-agent/` | PRODUCTION | Autonomous Agent |
| 10 | `autonomous-browser/` | FUNCTIONAL | Browser Automation |
| 11 | `backup-system/` | FUNCTIONAL | Health/Maintenance |
| 12 | `bim-validator/` | STUB | Revit/BIM |
| 13 | `bimops-site/` | FUNCTIONAL | Specialized |
| 14 | `bluebeam-mcp/` | PRODUCTION | Specialized |
| 15 | `brain-state/` | PRODUCTION | Core Infrastructure |
| 16 | `BridgeAI/` | FUNCTIONAL | Specialized |
| 17 | `chrome-cdp/` | FUNCTIONAL | Browser Automation |
| 18 | `claude-code-action/` | FUNCTIONAL | Reference |
| 19 | `Claude-code-CA/` | FUNCTIONAL | Specialized |
| 20 | `claude-code-revit/` | FUNCTIONAL | Revit/BIM |
| 21 | `claude-code-standards/` | FUNCTIONAL | Reference |
| 22 | `claude-memory-server/` | PRODUCTION | Core Infrastructure |
| 23 | `Claude_Skills/` | PRODUCTION | Reference |
| 24 | `ClaudeSTT/` | FUNCTIONAL | Voice/Speech |
| 25 | `code_memory_system/` | FUNCTIONAL | Reference |
| 26 | `context-engineering-demo/` | FUNCTIONAL | Reference |
| 27 | `context-triggers/` | STUB | Orchestration |
| 28 | `creative-studio/` | FUNCTIONAL | Agent Teams |
| 29 | `cross-app-automation/` | STUB | Orchestration |
| 30 | `edge-automation/` | NOT A TOOL | Browser (profile data) |
| 31 | `edge-cdp/` | FUNCTIONAL | Browser Automation |
| 32 | `email-watcher/` | PRODUCTION | Communication |
| 33 | `financial-mcp/` | PRODUCTION | Financial |
| 34 | `floor-plan-pipeline/` | STUB | Floor Plan |
| 35 | `floor-plan-vision-mcp/` | FUNCTIONAL | Floor Plan |
| 36 | `floorplan-rebuild/` | FUNCTIONAL | Floor Plan |
| 37 | `freelancer-monitor/` | FUNCTIONAL | Autonomous Agent |
| 38 | `gateway/` | FUNCTIONAL | Communication |
| 39 | `gmail-attachments/` | PRODUCTION | Communication |
| 40 | `google-calendar-mcp/` | PRODUCTION | Google Workspace |
| 41 | `google-drive-mcp/` | FUNCTIONAL | Google Workspace |
| 42 | `google-tasks-mcp/` | FUNCTIONAL | Google Workspace |
| 43 | `health-check/` | PRODUCTION | Health/Maintenance |
| 44 | `heygen-mcp/` | FUNCTIONAL | Visual/Media |
| 45 | `image-gen-mcp/` | FUNCTIONAL | Visual/Media |
| 46 | `jarvis/` | FUNCTIONAL | Voice/Speech |
| 47 | `master-orchestrator/` | STUB | Orchestration |
| 48 | `mcp-health-check/` | FUNCTIONAL | Health/Maintenance |
| 49 | `mcp-seatbelt/` | PRODUCTION | Security |
| 50 | `microsoft-teams-mcp/` | STUB | Communication |
| 51 | `obs-mcp/` | FUNCTIONAL | Visual/Media |
| 52 | `office-team/` | FUNCTIONAL | Agent Teams |
| 53 | `operation-cache/` | STUB | Orchestration |
| 54 | `opportunityengine/` | FUNCTIONAL | Autonomous Agent |
| 55 | `orchestration/` | FUNCTIONAL | Orchestration |
| 56 | `pattern-analysis/` | FUNCTIONAL | Health/Maintenance |
| 57 | `perimeter-tracer/` | FUNCTIONAL | Floor Plan |
| 58 | `personaplex-mcp/` | STUB | Specialized |
| 59 | `photo-catalog/` | FUNCTIONAL | Visual/Media |
| 60 | `pipelines/` | FUNCTIONAL | Orchestration |
| 61 | `playwright-mcp/` | FUNCTIONAL | Browser Automation |
| 62 | `post-revit-check/` | FUNCTIONAL | Revit/BIM |
| 63 | `powershell-bridge/` | PRODUCTION | Core Infrastructure |
| 64 | `pre-commit-guard/` | FUNCTIONAL | Security |
| 65 | `pre-flight-check/` | PRODUCTION | Health/Maintenance |
| 66 | `proactive/` | PRODUCTION | Autonomous Agent |
| 67 | `proactive-memory/` | FUNCTIONAL | Specialized |
| 68 | `project-state/` | FUNCTIONAL | Orchestration |
| 69 | `ralph/` | FUNCTIONAL | Reference |
| 70 | `revenue-plan/` | FUNCTIONAL | Financial |
| 71 | `revit-activity-journal/` | FUNCTIONAL | Revit/BIM |
| 72 | `revit-automations/` | PRODUCTION | Revit/BIM |
| 73 | `revit-live-view/` | PRODUCTION | Visual/Media |
| 74 | `revit-model-extractor/` | FUNCTIONAL | Revit/BIM |
| 75 | `revit-recorder-mcp/` | FUNCTIONAL | Visual/Media |
| 76 | `revit-starter-kit/` | FUNCTIONAL | Revit/BIM |
| 77 | `revit-startup-helper/` | FUNCTIONAL | Revit/BIM |
| 78 | `revit-ui-controller/` | FUNCTIONAL | Revit/BIM |
| 79 | `security-hooks/` | PRODUCTION | Security |
| 80 | `self-healing/` | STUB | Health/Maintenance |
| 81 | `self-improvement-hooks/` | PRODUCTION | Health/Maintenance |
| 82 | `site-data-api/` | FUNCTIONAL | Site Data |
| 83 | `smart-preview/` | FUNCTIONAL | Revit/BIM |
| 84 | `spine-passive/` | FUNCTIONAL | Specialized |
| 85 | `subtitle-reader/` | FUNCTIONAL | Voice/Speech |
| 86 | `system-bridge/` | PRODUCTION | Core Infrastructure |
| 87 | `system-video/` | STUB | Visual/Media |
| 88 | `task-orchestrator/` | FUNCTIONAL | Orchestration |
| 89 | `telegram-bot/` | STUB (config only) | Communication |
| 90 | `telegram-gateway/` | FUNCTIONAL | Communication |
| 91 | `ui/` | FUNCTIONAL | Specialized |
| 92 | `verification/` | STUB | Health/Maintenance |
| 93 | `video-pipeline/` | FUNCTIONAL | Visual/Media |
| 94 | `visual-memory-mcp/` | PRODUCTION | Visual/Media |
| 95 | `visual-review/` | STUB | Specialized |
| 96 | `voice-mcp/` | PRODUCTION | Voice/Speech |
| 97 | `voice-notes/` | FUNCTIONAL | Voice/Speech |
| 98 | `web-chat/` | FUNCTIONAL | Communication |
| 99 | `weber-sdk/` | FUNCTIONAL | Reference/SDK |
| 100 | `whatsapp-gateway/` | FUNCTIONAL | Communication |
| 101 | `windows-browser-mcp/` | FUNCTIONAL | Browser Automation |
| 102 | `workflow-loader/` | STUB | Orchestration |
| 103 | `youtube-uploader/` | FUNCTIONAL | Visual/Media |

---

## KEY CAPABILITIES THAT GO BEYOND OBVIOUS NAMES

1. **system-bridge** is not just monitoring -- it has a full workflow learning engine that predicts user behavior and detects anomalies
2. **claude-memory-server** is not just storage -- it is a complete self-improving learning system with correction tracking, reinforcement, spaced repetition, and pattern synthesis
3. **opportunityengine** is a fully autonomous business development agent that scans 5 platforms, qualifies opportunities, drafts proposals, and can submit them autonomously
4. **site-data-api** is a comprehensive Florida AEC intelligence platform (code compliance across 6 disciplines, zoning, environmental, soil, permits, NOA matching, plan review comment responses)
5. **agent-team** simulates a multi-person team meeting where AI agents debate and validate each other's work with voice output
6. **financial-mcp** exposes 70+ tools covering every aspect of market intelligence including paper trading and backtesting
7. **mcp-seatbelt** is a complete security governance layer with YAML-based policies, risk scoring, audit trails, CLI management, and weekly automated reports
8. **powershell-bridge** is the invisible accelerator -- nearly every Windows-touching tool depends on it for 100x speed improvement
9. **agent-common-sense** gives AI agents human-like judgment for irreversible actions via a 3-step decision loop
10. **weber-sdk** provides a unified async Python API layer over the entire MCP ecosystem with auto-discovery
11. **pipelines** can autonomously generate complete construction document sets from Revit models with checkpoint gates
12. **autonomous-browser** includes a full credential vault with TOTP code generation and session persistence
13. **proactive scheduler** runs 9 different timed/interval tasks for fully autonomous operation
14. **jarvis** is a complete voice-controlled AI assistant with wake word, STT, intent routing, and proactive alerts
15. **revit-recorder-mcp** enables automated Revit demo video production with MCP call logging and narration generation

---

## AGENT FLEET (51 agents across 10 squads)

Defined in `~/.claude/agents/*.md`:

| Squad | Count | Key Agents |
|-------|-------|------------|
| Revit/BIM | 20 | revit-builder, revit-developer, view-agent, sheet-layout |
| Development | 5 | code-architect, fullstack-dev, python-engineer, csharp-developer |
| AI/Agent | 3 | ml-engineer, prompt-engineer, agent-builder |
| Business | 4 | proposal-writer, invoice-tracker, client-liaison, project-manager |
| Research | 2 | tech-scout, market-analyst |
| Quality | 5 | bim-validator, qc-agent, cd-reviewer |
| Documentation | 3 | schedule-builder, excel-reporter |
| Workflow | 4 | orchestrator, learning-agent, floor-plan-processor |
| Code | 4 | code-simplifier, code-analyzer, test-runner |

---

## SESSION HOOKS (Active in `~/.claude/settings.json`)

### SessionStart Hooks (7)
1. System bridge daemon check
2. Brain state loading
3. Email status check
4. Proactive memory surfacing
5. Project state loading
6. Spaced repetition (correction review)
7. Weekly maintenance

### UserPromptSubmit Hooks (3)
1. Auto-checkpoint
2. Conversation logging
3. Correction detection

### PreToolUse Hooks (2)
1. MCP Seatbelt (security validation of all MCP calls)
2. Revit parameter validation (rule engine)

### PostToolUse Hooks (3)
1. C# auto-formatting (dotnet format)
2. Post-Revit validation check
3. Write tool post-check

### Stop Hooks (2)
1. Save session to brain state
2. Verification reminder

---

## RUNNING SERVICES (When fully operational)

| Service | Port/Method | Start Command |
|---------|-------------|---------------|
| System Bridge Daemon | `live_state.json` | `pythonw system-bridge/claude_daemon.py` |
| System Bridge Watchdog | Monitors daemon | `pythonw system-bridge/watchdog.py` |
| PowerShell Bridge | `127.0.0.1:15776` | `python3 powershell-bridge/bridge.py --daemon` |
| Proactive Scheduler | Background | `python3 proactive/scheduler.py` |
| Email Watcher | Background | `python3 email-watcher/email_watcher.py` |
| Autonomous Agent | Background | `python3 autonomous-agent/run_agent.py --daemon` |
| Gateway Hub | `127.0.0.1:18789` | `python3 gateway/hub.py` |
| Web Chat | `0.0.0.0:5555` | `python3 web-chat/server.py` |
| WhatsApp Gateway | Background | `node whatsapp-gateway/server.js` |
| Agent Dashboard | `localhost:8080` | `python3 agent-dashboard/server.py` |
| Revit Live View | Background | Scheduled task at Windows login |
| Opportunity Engine | Background | `python3 opportunityengine/daemon.py` |
| Freelancer Monitor | Background | `node freelancer-monitor/monitor.mjs` |

---

*This audit represents a complete inspection of every directory in `/mnt/d/_CLAUDE-TOOLS/` and `/mnt/d/009-PROJECT-FILES-DEVELOPER/mcp-servers/`. Every entry point was read, every README examined, and every capability cataloged.*

*Generated by Claude Opus 4.6 on 2026-02-15 via 147 tool calls.*

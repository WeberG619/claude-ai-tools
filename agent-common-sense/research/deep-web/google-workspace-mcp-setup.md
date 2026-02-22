# Google Workspace MCP Server Setup Guide

> **Researched:** 2026-02-21
> **Purpose:** Connect Claude Code to Gmail, Google Drive, Google Docs, Google Sheets, and Google Calendar via MCP
> **Status:** Production-ready options available

---

## Overview

Model Context Protocol (MCP) servers for Google Workspace allow Claude Code to directly access your Google account data -- email history, documents, spreadsheets, calendar events, and file storage. This turns Claude from a tool that only sees what you paste into it, into one that can search years of email threads, read project specifications from Drive, pull data from Sheets, and check your calendar -- all through natural language.

Multiple MCP servers exist for Google Workspace, ranging from the official Anthropic reference server (Drive-only) to comprehensive community servers covering all Google services. This guide evaluates the options and provides a complete setup walkthrough.

---

## Available MCP Servers (Comparison)

| Server | Stars | Services | Language | Transport | Key Differentiator |
|--------|-------|----------|----------|-----------|-------------------|
| [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp) | ~1,500 | Gmail, Drive, Calendar, Docs, Sheets, Slides, Forms, Tasks, Chat, Contacts, Search | Python | stdio, HTTP | Most comprehensive; 100+ tools, tool tiers, OAuth 2.1, DXT installer |
| [ngs/google-mcp-server](https://github.com/ngs/google-mcp-server) | ~46 commits | Gmail, Drive, Calendar, Docs, Sheets, Slides | Go | stdio | Multi-account, Markdown-to-Slides, compiled binary |
| [aaronsb/google-workspace-mcp](https://github.com/aaronsb/google-workspace-mcp) | ~120 | Gmail, Calendar, Drive, Contacts | TypeScript | stdio (Docker) | Docker-first, multi-account, security-focused |
| [dguido/google-workspace-mcp](https://github.com/dguido/google-workspace-mcp) | ~36 | Gmail, Drive, Docs, Sheets, Slides, Calendar, Contacts | Python | stdio | TOON format (20-50% fewer tokens), PKCE security |
| [modelcontextprotocol/server-gdrive](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/gdrive) | Official | Drive only | TypeScript | stdio | Anthropic reference implementation; read-only |
| [epaproditus/google-workspace-mcp-server](https://github.com/epaproditus/google-workspace-mcp-server) | Community | Gmail, Calendar | TypeScript | stdio | Minimal, focused on email and calendar only |
| [a-bonus/google-docs-mcp](https://github.com/a-bonus/google-docs-mcp) | Community | Docs, Sheets, Drive | TypeScript | stdio | Full Docs formatting and editing |

---

## Best Option: taylorwilsdon/google_workspace_mcp

**Recommended for most users.** Reasoning:

1. **Most complete coverage** -- all 12 Google Workspace services with 100+ tools
2. **Most active development** -- 1,500+ stars, 450+ forks, regular updates
3. **Flexible tool loading** -- use `--tool-tier core` for lightweight operation or `--tools gmail drive` for selective loading
4. **Multiple installation paths** -- uvx (zero install), DXT one-click, Docker, source
5. **OAuth 2.1 support** -- modern auth standard with multi-user capability
6. **Read-only mode** -- `--read-only` flag for safety when you only need to search/read
7. **CLI mode** -- can be used standalone outside of Claude Code
8. **PyPI package** -- `workspace-mcp` on PyPI for standard pip/uvx installation

**Runner-up: ngs/google-mcp-server** -- if you prefer a compiled Go binary with no Python dependency, multi-account support, and excellent Slides/presentation handling.

**Runner-up: dguido/google-workspace-mcp** -- if token efficiency matters (TOON format saves 20-50% on tokens) and you want PKCE-secured OAuth.

---

## Prerequisites

Before starting, you need:

1. **Python 3.10+** (3.11+ recommended)
2. **uv** (Astral's Python package manager) -- install via `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. **A Google account** (free Gmail or Google Workspace)
4. **Access to Google Cloud Console** -- https://console.cloud.google.com/

---

## Installation

### Option A: uvx (Recommended -- Zero Install)

```bash
# Run directly without installing
uvx workspace-mcp --tool-tier core

# Or with specific services only
uvx workspace-mcp --tools gmail drive calendar
```

### Option B: pip Install

```bash
pip install workspace-mcp
workspace-mcp --tool-tier core
```

### Option C: From Source

```bash
git clone https://github.com/taylorwilsdon/google_workspace_mcp.git
cd google_workspace_mcp
uv run main.py --transport stdio
```

### Option D: Docker

```bash
docker build -t workspace-mcp .
docker run -p 8000:8000 workspace-mcp
```

### Option E: DXT One-Click (Claude Desktop Only)

1. Download `google_workspace_mcp.dxt` from [Releases](https://github.com/taylorwilsdon/google_workspace_mcp/releases)
2. Double-click the file
3. Claude Desktop prompts to install
4. Enter OAuth credentials in Settings > Extensions

---

## OAuth Setup (Step by Step)

This is the most involved part. Follow carefully.

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown in the top navigation bar
3. Click **New Project**
4. Enter a project name (e.g., "Claude MCP Integration")
5. Click **Create**
6. Wait for the project to be created, then select it from the dropdown

### Step 2: Enable Required APIs

Navigate to **APIs & Services > Library** and enable each of these APIs:

| API | URL |
|-----|-----|
| Gmail API | https://console.cloud.google.com/apis/library/gmail.googleapis.com |
| Google Drive API | https://console.cloud.google.com/apis/library/drive.googleapis.com |
| Google Calendar API | https://console.cloud.google.com/apis/library/calendar-json.googleapis.com |
| Google Docs API | https://console.cloud.google.com/apis/library/docs.googleapis.com |
| Google Sheets API | https://console.cloud.google.com/apis/library/sheets.googleapis.com |
| Google Slides API | https://console.cloud.google.com/apis/library/slides.googleapis.com |
| People API (Contacts) | https://console.cloud.google.com/apis/library/people.googleapis.com |
| Tasks API | https://console.cloud.google.com/apis/library/tasks.googleapis.com |

For each: click the API name, then click **Enable**.

### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services > OAuth consent screen**
2. Select **External** user type (unless you have a Google Workspace org and want Internal)
3. Click **Create**
4. Fill in required fields:
   - **App name:** "Claude MCP" (or whatever you prefer)
   - **User support email:** your email
   - **Developer contact information:** your email
5. Click **Save and Continue**
6. On the **Scopes** page, click **Add or Remove Scopes**
7. Add the scopes you need (see Scopes Reference below)
8. Click **Save and Continue**
9. On the **Test users** page, click **Add Users**
10. Enter your Google email address
11. Click **Save and Continue**

### Step 4: Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **+ Create Credentials > OAuth client ID**
3. Select **Desktop application** as the application type
4. Enter a name (e.g., "Claude Code MCP")
5. Click **Create**
6. A dialog shows your **Client ID** and **Client Secret** -- copy both
7. Optionally click **Download JSON** to save the credentials file

### Step 5: Set Environment Variables

```bash
export GOOGLE_OAUTH_CLIENT_ID="your-client-id-here.apps.googleusercontent.com"
export GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret-here"
```

Or create a `.env` file in the server directory:

```
GOOGLE_OAUTH_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret-here
```

### Step 6: Authenticate

On first run, the server will:
1. Open your default browser to Google's OAuth consent page
2. Ask you to sign in and authorize access
3. Redirect back to localhost with an authorization code
4. Exchange the code for access and refresh tokens
5. Store the tokens locally for future use

### Critical: Avoid the 7-Day Token Expiry

**If your OAuth consent screen is in "Testing" mode**, Google refresh tokens expire after 7 days. This means you will need to re-authenticate weekly.

**To fix this permanently:**
1. Go to **APIs & Services > OAuth consent screen**
2. Click **Publish App** to move from Testing to Production
3. For personal use, Google does not require verification for apps with fewer than 100 users
4. **Important:** After publishing, create NEW OAuth credentials (the old ones will still use the testing token lifetime)
5. Update your environment variables with the new Client ID and Secret

---

## OAuth Scopes Reference

### Full Access Scopes (Read + Write)

| Service | Scope | Permission |
|---------|-------|------------|
| Gmail | `https://mail.google.com/` | Full email access (read, send, delete) |
| Gmail | `https://www.googleapis.com/auth/gmail.modify` | Read, compose, send (no delete) |
| Gmail | `https://www.googleapis.com/auth/gmail.compose` | Manage drafts and send |
| Gmail | `https://www.googleapis.com/auth/gmail.labels` | Manage labels |
| Gmail | `https://www.googleapis.com/auth/gmail.settings.basic` | Manage settings and filters |
| Drive | `https://www.googleapis.com/auth/drive` | Full Drive access |
| Docs | `https://www.googleapis.com/auth/documents` | Full Docs access |
| Sheets | `https://www.googleapis.com/auth/spreadsheets` | Full Sheets access |
| Calendar | `https://www.googleapis.com/auth/calendar` | Full Calendar access |

### Read-Only Scopes (Safer)

| Service | Scope | Permission |
|---------|-------|------------|
| Gmail | `https://www.googleapis.com/auth/gmail.readonly` | View emails only |
| Gmail | `https://www.googleapis.com/auth/gmail.metadata` | View headers and labels only |
| Drive | `https://www.googleapis.com/auth/drive.readonly` | View files only |
| Calendar | `https://www.googleapis.com/auth/calendar.readonly` | View events only |
| Calendar | `https://www.googleapis.com/auth/calendar.events.readonly` | View event details only |

**Recommendation:** Start with read-only scopes. Upgrade to full access only after verifying the setup works and you trust the workflow. Use `--read-only` flag with workspace-mcp to enforce this at the server level.

---

## Available Tools (taylorwilsdon/google_workspace_mcp)

### Gmail Tools
- `search_gmail_messages` -- Search emails by query (sender, subject, label, date, keywords)
- `get_gmail_message` -- Retrieve full email content by ID
- `send_gmail_message` -- Compose and send emails with CC/BCC
- `create_gmail_draft` -- Create email drafts
- `list_gmail_labels` -- List all labels/folders
- `manage_gmail_labels` -- Create, update, delete labels
- `modify_gmail_message` -- Archive, trash, mark read/unread
- `get_gmail_attachment` -- Download email attachments

### Google Drive Tools
- `search_drive_files` -- Search files by name, content, type, date
- `get_drive_file` -- Read file content (auto-converts Docs to Markdown, Sheets to CSV)
- `list_drive_files` -- List files in a folder
- `create_drive_file` -- Create new files
- `update_drive_file` -- Update existing files
- `upload_drive_file` -- Upload files with format conversion
- `move_drive_file` -- Move files between folders
- `copy_drive_file` -- Copy files
- `delete_drive_file` -- Delete or trash files
- `create_drive_folder` -- Create folders
- `share_drive_file` -- Manage sharing permissions

### Google Calendar Tools
- `list_calendar_events` -- List events with date range filtering
- `get_calendar_event` -- Get event details
- `create_calendar_event` -- Create events with attendees, location, reminders
- `update_calendar_event` -- Modify existing events
- `delete_calendar_event` -- Delete events
- `find_free_time` -- Check availability across calendars

### Google Docs Tools
- `create_doc` -- Create new documents
- `get_doc_content` -- Read document content (as Markdown)
- `update_doc` -- Append or replace content
- `insert_text` -- Insert text at specific positions
- `add_comment` -- Add comments to documents

### Google Sheets Tools
- `get_spreadsheet` -- Get spreadsheet metadata
- `get_sheet_values` -- Read cell ranges
- `update_sheet_values` -- Write to cell ranges
- `create_spreadsheet` -- Create new spreadsheets
- `add_sheet` -- Add worksheets
- `format_cells` -- Apply formatting

### Google Slides Tools
- `create_presentation` -- Create new presentations
- `get_presentation` -- Read presentation content
- `add_slide` -- Add slides
- `update_slide` -- Modify slide content
- `add_text_box` -- Add text elements
- `add_image` -- Insert images

### Tool Tiers

| Tier | What It Includes | When to Use |
|------|-----------------|-------------|
| `core` | Essential read/search tools for each service | Daily use, lightweight, fewer tokens |
| `extended` | Core + create/update tools | General-purpose work |
| `complete` | All tools including admin/settings | Full automation workflows |

---

## Claude Code Integration Config

### Method 1: claude mcp add (Recommended for Claude Code)

```bash
# Add with environment variables inline
claude mcp add google-workspace \
  -e GOOGLE_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com" \
  -e GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret" \
  -- uvx workspace-mcp --tool-tier core
```

Or with specific services only:

```bash
claude mcp add google-workspace \
  -e GOOGLE_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com" \
  -e GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret" \
  -- uvx workspace-mcp --tools gmail drive calendar docs sheets
```

### Method 2: Manual JSON Config

Add to `~/.claude/settings.json` (global) or `.claude/settings.json` (project):

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "uvx",
      "args": ["workspace-mcp", "--tool-tier", "core"],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

### Method 3: Selective Services (Lean Config)

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "uvx",
      "args": ["workspace-mcp", "--tools", "gmail", "drive", "calendar"],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

### Method 4: Read-Only Mode (Maximum Safety)

```json
{
  "mcpServers": {
    "google-workspace": {
      "command": "uvx",
      "args": ["workspace-mcp", "--tool-tier", "core", "--read-only"],
      "env": {
        "GOOGLE_OAUTH_CLIENT_ID": "your-client-id.apps.googleusercontent.com",
        "GOOGLE_OAUTH_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

### Method 5: Official Anthropic Drive-Only Server

If you only need Google Drive access (no Gmail, Calendar, etc.):

```json
{
  "mcpServers": {
    "gdrive": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-gdrive"],
      "env": {
        "GDRIVE_CREDENTIALS_PATH": "/path/to/.gdrive-server-credentials.json"
      }
    }
  }
}
```

### Method 6: ngs/google-mcp-server (Go Binary)

```bash
# Install via Homebrew
brew tap ngs/tap && brew install google-mcp-server

# Add to Claude Code
claude mcp add google -- /opt/homebrew/bin/google-mcp-server
```

Or manually:

```json
{
  "mcpServers": {
    "google": {
      "command": "/opt/homebrew/bin/google-mcp-server"
    }
  }
}
```

---

## What Deep Web Data Becomes Accessible

Once connected, Claude Code can search and retrieve data that is completely invisible to web search engines -- your private, authenticated Google Workspace data. For an AEC (Architecture, Engineering, Construction) professional, this is transformative:

### Email (Gmail)
- **Years of email history** -- search across your entire inbox by sender, subject, date range, keywords, labels
- **Client communications** -- find every email thread with a specific client, contractor, or consultant
- **RFI/RFP chains** -- search for Requests for Information, proposals, bid documents
- **Project correspondence** -- locate specific discussions about design changes, approvals, submittals
- **Attachment retrieval** -- access PDFs, drawings, specs attached to emails
- **Sent mail search** -- find what you said to whom, and when

### Documents (Google Drive + Docs)
- **Project specifications** -- search and read spec documents stored in Drive
- **Meeting notes** -- access notes from project meetings, design reviews, OAC meetings
- **Proposals and contracts** -- find and read proposal documents, fee letters, contracts
- **Design narratives** -- access design intent documents, basis of design documents
- **Shared documents** -- access files shared with you by clients, consultants, and team members
- **Folder hierarchy** -- navigate your entire Drive file structure

### Spreadsheets (Google Sheets)
- **Project trackers** -- read issue logs, RFI logs, submittal logs
- **Cost estimates** -- access fee proposals, budget spreadsheets
- **Schedules** -- read project schedules maintained in Sheets
- **Contact lists** -- access project directories, consultant databases
- **Data analysis** -- read and write to data-heavy spreadsheets

### Calendar
- **Meeting history** -- see what meetings occurred on specific dates
- **Upcoming schedule** -- check availability before committing to deadlines
- **Attendee lists** -- see who was in specific meetings
- **Meeting notes in events** -- access descriptions and attachments in calendar events
- **Recurring meetings** -- find patterns in project meeting cadences

### Cross-Service Queries
The real power is in cross-referencing:
- "Find all emails from [client] about [project] in the last 6 months, then find related documents in Drive"
- "Check my calendar for last Tuesday's meeting with [consultant], find the follow-up email I sent, and pull the spreadsheet I referenced"
- "Search Drive for all files related to [project number] and summarize what documents exist"

---

## Privacy & Security Considerations

### What Data Is Exposed

When you connect Google Workspace via MCP, Claude Code can access:
- **All emails** in your Gmail account (or scoped to read-only)
- **All files** in your Google Drive (including files shared with you)
- **All calendar events** (including attendees, descriptions, locations)
- **All contacts** in your Google Contacts

Claude processes this data to respond to your queries. The data is sent to Anthropic's API for processing.

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| OAuth token theft | High | Tokens stored locally in plaintext; encrypt disk, restrict file permissions |
| Overly broad scopes | Medium | Use read-only scopes initially; use `--read-only` flag |
| Prompt injection via email | High | Malicious emails could contain hidden instructions; be cautious with email content |
| Accidental data exposure | Medium | Claude may include sensitive data in responses; review output before sharing |
| Token persistence | Medium | Refresh tokens persist until revoked; revoke via Google Account settings |
| Unintended email sending | High | Full Gmail scope allows sending as you; use compose-only or read-only scopes |
| Organizational policy violation | High | Corporate Google Workspace admins may prohibit third-party OAuth apps |

### Security Best Practices

1. **Start read-only.** Use `--read-only` mode and read-only scopes until you trust the workflow.
2. **Limit services.** Only enable the Google services you actually need (`--tools gmail drive`).
3. **Use tool tiers.** Start with `--tool-tier core` to minimize the attack surface.
4. **Review token storage.** Know where tokens are stored on disk and ensure the directory has restricted permissions.
5. **Publish your OAuth app** to avoid 7-day token expiry, but understand this means the app is technically "in production."
6. **Revoke access when done.** Go to https://myaccount.google.com/permissions to revoke the OAuth app's access at any time.
7. **Watch for prompt injection.** Be cautious when Claude reads emails -- a carefully crafted email could attempt to hijack Claude's behavior. Never blindly trust email content as instructions.
8. **Do not use with shared machines.** OAuth tokens stored locally give full access to anyone who can read the token file.
9. **Separate personal and work.** Consider using a dedicated Google account for MCP integration rather than your primary work account.
10. **Check with IT.** If you are on a corporate Google Workspace, your admin may restrict third-party OAuth apps. Verify before setting up.

### Data Flow

```
Your Query --> Claude Code --> MCP Server (local) --> Google APIs --> Your Google Account
                  |
                  v
           Anthropic API (processes query + retrieved data)
```

All Google API calls happen locally on your machine via the MCP server. The MCP server sends data to Claude (via Anthropic's API) for processing. Anthropic's data retention policies apply to the data processed through the API.

---

## Limitations

1. **OAuth consent screen in Testing mode** -- refresh tokens expire every 7 days; must publish to Production for persistent tokens
2. **API rate limits** -- Google APIs have per-user and per-project rate limits; heavy automation may hit these
3. **No real-time sync** -- MCP servers query on demand, not continuously; no push notifications
4. **Large file handling** -- very large files or many results may exceed Claude's context window
5. **Google Workspace admin restrictions** -- organizational admins can block third-party OAuth apps entirely
6. **Token storage security** -- tokens are stored in plaintext JSON files on disk by default
7. **Single-user limitation (stdio mode)** -- standard MCP stdio transport supports one authenticated user at a time
8. **No offline access** -- requires active internet connection to Google APIs
9. **Sensitive scope verification** -- if you use sensitive scopes (like full Gmail access) and want more than 100 users, Google requires app verification (security review)
10. **Format conversion limitations** -- Google Docs converted to Markdown may lose complex formatting; Sheets converted to CSV may lose formulas and formatting
11. **Attachment handling** -- email attachments can be retrieved but binary files (PDFs, images) may not be directly usable by Claude beyond metadata
12. **Calendar write operations** -- creating/modifying events on behalf of a user can cause confusion if attendees receive automated invites

---

## Troubleshooting

### "Token has been expired or revoked"
- Your OAuth consent screen is likely in Testing mode (7-day token expiry)
- Fix: Publish your app to Production, then create new OAuth credentials

### "Access blocked: This app's request is invalid"
- Redirect URI mismatch or missing scopes
- Fix: Ensure your OAuth client type is "Desktop application" (not Web application)

### MCP server won't start
- Python version too old (need 3.10+)
- uvx not installed
- Fix: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### "Insufficient Permission" errors
- Required API not enabled in Google Cloud Console
- Fix: Enable all required APIs (see Step 2 above)

### Claude Code doesn't show Google tools
- MCP server not configured correctly
- Fix: Run `claude mcp list` to verify the server is registered; restart Claude Code after config changes

### Rate limit exceeded
- Too many API calls in a short period
- Fix: Add delays between operations; use more specific queries to reduce API calls

---

## Quick Reference Card

```
# Add to Claude Code (one command)
claude mcp add google-workspace \
  -e GOOGLE_OAUTH_CLIENT_ID="YOUR_ID" \
  -e GOOGLE_OAUTH_CLIENT_SECRET="YOUR_SECRET" \
  -- uvx workspace-mcp --tools gmail drive calendar docs sheets --tool-tier core

# Verify it works
claude mcp list

# Test in Claude Code
> Search my Gmail for emails from [client name] about [project]
> Find documents in my Drive related to [project number]
> What meetings do I have next week?
> Read the spreadsheet at [Sheet URL]
```

---

## References

- [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp) -- Primary recommended server
- [Workspace MCP Official Site](https://workspacemcp.com/) -- Quick start and documentation
- [ngs/google-mcp-server](https://github.com/ngs/google-mcp-server) -- Go-based alternative
- [aaronsb/google-workspace-mcp](https://github.com/aaronsb/google-workspace-mcp) -- Docker-based alternative
- [dguido/google-workspace-mcp](https://github.com/dguido/google-workspace-mcp) -- Token-efficient alternative
- [modelcontextprotocol/server-gdrive](https://github.com/modelcontextprotocol/servers-archived/tree/main/src/gdrive) -- Official Anthropic Drive-only server
- [Google OAuth 2.0 Scopes](https://developers.google.com/identity/protocols/oauth2/scopes) -- Complete scope reference
- [Google Cloud Console](https://console.cloud.google.com/) -- Project and API management
- [Claude Code MCP Docs](https://code.claude.com/docs/en/mcp) -- Official MCP integration guide
- [MCP Security Risks](https://www.pillar.security/blog/the-security-risks-of-model-context-protocol-mcp) -- Security analysis
- [Google OAuth Token Expiry Policy](https://developers.google.com/identity/protocols/oauth2) -- Token lifetime documentation

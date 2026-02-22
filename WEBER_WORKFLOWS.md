# WEBER GOUIN - MASTER WORKFLOW REFERENCE
# THIS FILE MUST BE READ AT EVERY SESSION START

**User:** Weber Gouin (NEVER "Rick")
**Primary Email:** weberg619@gmail.com
**Browser:** Chrome (NEVER Edge or other)
**Business:** BIM Ops Studio + WG Design Drafting

---

## 📧 EMAIL (Gmail)

### SENDING an Email
**Always use Chrome + Gmail. NEVER Outlook.**

```powershell
Start-Process "chrome.exe" -ArgumentList "https://mail.google.com/mail/u/0/?view=cm&fs=1&to=EMAIL&su=SUBJECT&body=BODY"
```

| Account | URL Path | Use For |
|---------|----------|---------|
| weberg619@gmail.com | `/mail/u/0/` | Primary - use this by default |
| (secondary) | `/mail/u/1/` | Ask if needed |

**URL Encoding:** space=%20, newline=%0A, &=%26

### DOWNLOADING Attachments
```bash
python3 /mnt/d/_CLAUDE-TOOLS/gmail-attachments/imap_download.py --search "from:sender" --download "/path"
```

### Common Contacts (Auto-extracted from Gmail)
| Name | Email | Company/Notes |
|------|-------|---------------|
| M Isa Fantal | ifantal@lesfantal.com | Fantal Consulting / Les Fantal |
| Fantal Management | fantalconsulting@lesfantal.com | Fantal Consulting |
| Bernardo Rieber | bernardorieber@gmail.com | Client |
| Arky | info.arky@gmail.com | Client |
| Bruce Davis | bruce@bdarchitect.net | BD Architect |
| KRM Designs | krmdesigns19@gmail.com | Client |
| Eduardo Roman | eduardo@ara-engineering.com | ARA Engineering |
| Eddie Roman | eddie@ara-engineering.com | ARA Engineering |
| Gleinys Martinez | gleinys@bartholemewpartners.com | Bartholemew Partners |
| Fernando Rodriguez | fernando@bartholemewpartners.com | Bartholemew Partners |
| Paola Gomez | paola@bdarchitect.net | BD Architect |
| Laurie Vincent | laurievincent55@hotmail.com | Personal |
| Moricia Davis | moricia@bdarchitect.net | BD Architect |
| Rachelle Sylvain-Spence | rachelle@afuriaesthetics.com | Afuri Aesthetics |
| Michelle Sweetland | msweetland25@gmail.com | Contact |
| Arnold Vincent | arnoldvincent17@gmail.com | Personal |
| Danny Haymond | danny.haymondbrothers@gmail.com | Haymond Brothers |
| Noel Epelboim | noel@vitalistower.com | Vitalis Tower |
| Bryant Baxter | bbaxter117@gmail.com | Contact |
| Amy Baxter | amybaxter06@gmail.com | Contact |
| Carlos Cadet | carlosmcadet@hotmail.com | Contact |

### Weber's Own Emails
| Email | Use For |
|-------|---------|
| weberg619@gmail.com | Primary personal |
| weber@bdarchitect.net | BD Architect work |
| weber@bimopsstudio.com | BIM Ops Studio |
| weber@wgdesigndrafting.com | WG Design Drafting |

---

## 📅 CALENDAR (Google Calendar)

**Tool:** `/mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/calendar_client.py`
**Weber's Timezone:** Pacific (3 hours behind ET)

```bash
# View today's events
python3 /mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/calendar_client.py today

# View this week
python3 /mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/calendar_client.py week

# Add event (times in ET for the API)
python3 /mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/calendar_client.py add "Meeting" "2026-01-27T17:00:00" "2026-01-27T18:00:00" "Description"

# Search
python3 /mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/calendar_client.py search "keyword"
```

**Time Conversion:** When Weber says "2 PM my time" = 5 PM ET

---

## 🏗️ REVIT (MCP Bridge)

### Connection Method: NAMED PIPES (NOT HTTP)

| Version | Pipe Name |
|---------|-----------|
| Revit 2025 | `\\.\pipe\RevitMCPBridge2025` |
| Revit 2026 | `\\.\pipe\RevitMCPBridge2026` |

```powershell
$pipe = New-Object System.IO.Pipes.NamedPipeClientStream('.', 'RevitMCPBridge2025', [System.IO.Pipes.PipeDirection]::InOut)
$pipe.Connect(10000)
$writer = New-Object System.IO.StreamWriter($pipe)
$reader = New-Object System.IO.StreamReader($pipe)
$writer.AutoFlush = $true
$request = @{method='getLevels'; parameters=@{}} | ConvertTo-Json -Compress
$writer.WriteLine($request)
$response = $reader.ReadLine()
$pipe.Close()
```

### Check Which Revit is Open
Read `/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json` - look for Revit in applications list

---

## 📁 GOOGLE DRIVE

**Access:** Via browser or API
```powershell
# Open Google Drive in Chrome
Start-Process "chrome.exe" -ArgumentList "https://drive.google.com"
```

---

## 📝 MICROSOFT WORD

**Opening a Word document:**
```powershell
Start-Process "path\to\document.docx"
```

**Recent files location:** Check live_state.json for recent_files

---

## 📊 MICROSOFT EXCEL

**Launch via COM (required for MCP control):**
```powershell
$excel = New-Object -ComObject Excel.Application
$excel.Visible = $true
$wb = $excel.Workbooks.Add()
```

**NEVER use `Start-Process excel.exe`** — COM binding won't work reliably.

**Open existing file:**
```powershell
Start-Process "path\to\spreadsheet.xlsx"
```

**Position on monitor:** See `/mnt/d/_CLAUDE-TOOLS/WINDOW_MANAGEMENT.md`

---

## 🔵 BLUEBEAM

**Check what's open:** Read live_state.json → bluebeam.document
**MCP Tools:** `mcp__bluebeam__*` functions available

---

## 🔊 VOICE (Text-to-Speech)

**ALWAYS speak summaries after completing tasks:**
```bash
python3 /mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py "Summary text here"
```

Or use MCP:
```
mcp__voice__speak(text="Summary", voice="andrew")
```

---

## 🧠 MEMORY

### Session Start
```
mcp__claude-memory__memory_smart_context(current_directory="/mnt/d/...")
```

### Store Corrections (CRITICAL)
When Weber corrects me:
```
mcp__claude-memory__memory_store_correction(
    what_claude_said="...",
    what_was_wrong="...",
    correct_approach="..."
)
```

---

## 📂 PROJECT FOLDER MAPPINGS

| Client/Project | Path |
|----------------|------|
| Fantal Consulting | `/mnt/d/001 - PROJECTS/01 - CLIENT PROJECTS/04 - FANTAL CONSULTING/` |
| Afuri Aesthetics | `/mnt/d/001 - PROJECTS/01 - CLIENT PROJECTS/04 - FANTAL CONSULTING/AFURI - 6365 W Sample Rd/Client/` |
| South Gulf Cove | (ask for path) |
| RevitMCPBridge2025 | `/mnt/d/RevitMCPBridge2025/` |
| RevitMCPBridge2026 | `/mnt/d/RevitMCPBridge2026/` |

---

## 🖥️ SYSTEM STATE

**Live state file:** `/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json`
- Shows open applications
- Shows which monitors
- Shows recent files
- Shows Revit/Bluebeam status

**ALWAYS check this at session start to know what Weber is working on.**

---

## 🖥️ WINDOW MANAGEMENT (Multi-Monitor + DPI)

**Full guide:** `/mnt/d/_CLAUDE-TOOLS/WINDOW_MANAGEMENT.md`

**Quick rules:**
- 3 monitors, all 2560x1440 virtual (3840x2160 physical, 150% DPI)
- Center monitor = DISPLAY2, x=-2560 (Weber's preferred demo monitor)
- **MUST call `SetProcessDPIAware()` before any `SetWindowPos`**
- **NEVER use `ShowWindow(SW_MAXIMIZE)`** — spans monitors
- **NEVER use `window_move` MCP tool** — not DPI-aware
- Use `SetWindowPos(hwnd, 0, -2560, 0, 2560, 1400, 0x0004)` for center monitor

---

## ❌ COMMON MISTAKES - NEVER DO THESE

| Wrong | Correct |
|-------|---------|
| Open Outlook | Open Gmail in Chrome |
| Use Edge browser | Use Chrome |
| Sign as "Rick" | Sign as "Weber Gouin" |
| HTTP to Revit ports | Use named pipes |
| Guess paths | Check system state or ask |
| Skip reading workflows | Always read this file first |
| Use `window_move` MCP tool | Use DPI-aware `SetWindowPos` pattern |
| Use `ShowWindow(SW_MAXIMIZE)` | Use `SetWindowPos` to fill monitor |
| Use `Start-Process excel.exe` | Use `New-Object -ComObject Excel.Application` |
| Send keys without verifying focus | `SetForegroundWindow` + screenshot first |

---

## 🏛️ PERMIT & PROPERTY RESEARCH

### eTRAKiT Permit Tracking
**MCP Server:** `mcp__etrakit-mcp__*`
**Path:** `/mnt/d/_CLAUDE-TOOLS/etrakit-mcp/`

Scrapes CentralSquare eTRAKiT permit portals (Broward County cities). Uses CDP browser automation with 30-minute cache.

```
mcp__etrakit-mcp__search_permits(city="...", permit_number="...")
mcp__etrakit-mcp__get_permit_details(city="...", permit_number="...")
```

### Property Appraiser
**MCP Server:** `mcp__property-appraiser-mcp__*`
**Path:** `/mnt/d/_CLAUDE-TOOLS/property-appraiser-mcp/`

Scrapes Broward County (BCPA) and Miami-Dade County property appraiser data. 7-day cache TTL.

```
mcp__property-appraiser-mcp__search_property(county="broward", address="...")
mcp__property-appraiser-mcp__get_property_details(folio="...")
```

### Government Data
**MCP Server:** `mcp__govdata-mcp__*`
**Path:** `/mnt/d/_CLAUDE-TOOLS/govdata-mcp/`

Building permits, code violations, zoning data from government open data portals.

---

## 🔬 RESEARCH TOOLS

### Academic Research
**MCP Server:** `mcp__research-mcp__*`
**Path:** `/mnt/d/_CLAUDE-TOOLS/research-mcp/`

Literature discovery and analysis from academic sources.

### HuggingFace Datasets
**MCP Server:** `mcp__datasets-mcp__*`
**Path:** `/mnt/d/_CLAUDE-TOOLS/datasets-mcp/`

Search, explore, preview, and download HuggingFace Hub datasets.

---

## 👁️ VISUAL MEMORY

**MCP Server:** `mcp__visual-memory__*`
**Path:** `/mnt/d/_CLAUDE-TOOLS/visual-memory-mcp/`

Captures screen at intervals, indexes with OCR, enables visual recall. Privacy-first with whitelist/blocklist controls.

```
mcp__visual-memory__memory_start_capture()   # Start capturing
mcp__visual-memory__memory_search(query="...") # Search by text in screenshots
mcp__visual-memory__memory_recall_recent()    # Get recent captures
mcp__visual-memory__memory_recall_app(app="...") # Get captures from specific app
```

---

## ✅ SESSION START CHECKLIST

1. [ ] Read this file: `/mnt/d/_CLAUDE-TOOLS/WEBER_WORKFLOWS.md`
2. [ ] Read system state: `/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json`
3. [ ] Load memory context: `memory_smart_context`
4. [ ] Note what apps are open
5. [ ] Acknowledge to Weber what you see

---

*Last Updated: 2026-02-22*
*Add new workflows here as they are established*

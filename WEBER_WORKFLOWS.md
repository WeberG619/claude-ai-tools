# WEBER GOUIN - WORKFLOW REFERENCE
# Load when you need contacts, email, calendar, Revit pipes, or project paths.

**User:** Weber Gouin
**Primary Email:** weberg619@gmail.com
**Browser:** Chrome
**Business:** BIM Ops Studio + WG Design Drafting

---

## EMAIL (Gmail)

### Sending an Email
```powershell
Start-Process "chrome.exe" -ArgumentList "https://mail.google.com/mail/u/0/?view=cm&fs=1&to=EMAIL&su=SUBJECT&body=BODY"
```

| Account | URL Path | Use For |
|---------|----------|---------|
| weberg619@gmail.com | `/mail/u/0/` | Primary - use this by default |
| (secondary) | `/mail/u/1/` | Ask if needed |

**URL Encoding:** space=%20, newline=%0A, &=%26

### Downloading Attachments
```bash
python3 /mnt/d/_CLAUDE-TOOLS/gmail-attachments/imap_download.py --search "from:sender" --download "/path"
```

### Common Contacts
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

## CALENDAR (Google Calendar)

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

## REVIT (MCP Bridge)

### Connection: Named Pipes

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
Read `/mnt/d/_CLAUDE-TOOLS/system-bridge/live_state.json` — look for Revit in applications list

---

## GOOGLE DRIVE

```powershell
Start-Process "chrome.exe" -ArgumentList "https://drive.google.com"
```

---

## MICROSOFT WORD

```powershell
Start-Process "path\to\document.docx"
```

Recent files: check live_state.json

---

## MICROSOFT EXCEL

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

**Window positioning:** Load `/mnt/d/_CLAUDE-TOOLS/DESKTOP.md`

---

## BLUEBEAM

**Check what's open:** Read live_state.json
**MCP Tools:** `mcp__bluebeam__*` functions available

---

## VOICE (Text-to-Speech)

```
mcp__voice__speak(text="Summary", voice="andrew")
```

---

## MEMORY

### Session Start
```
mcp__claude-memory__memory_smart_context(current_directory="/mnt/d/...")
```

### Store Corrections
```
mcp__claude-memory__memory_store_correction(
    what_claude_said="...",
    what_was_wrong="...",
    correct_approach="..."
)
```

---

## PROJECT FOLDER MAPPINGS

| Client/Project | Path |
|----------------|------|
| Fantal Consulting | `/mnt/d/001 - PROJECTS/01 - CLIENT PROJECTS/04 - FANTAL CONSULTING/` |
| Afuri Aesthetics | `/mnt/d/001 - PROJECTS/01 - CLIENT PROJECTS/04 - FANTAL CONSULTING/AFURI - 6365 W Sample Rd/Client/` |
| South Gulf Cove | (ask for path) |
| RevitMCPBridge2025 | `/mnt/d/RevitMCPBridge2025/` |
| RevitMCPBridge2026 | `/mnt/d/RevitMCPBridge2026/` |

---

## PERMIT & PROPERTY RESEARCH

### eTRAKiT Permit Tracking
**MCP Server:** `mcp__etrakit-mcp__*`

```
mcp__etrakit-mcp__search_permits(city="...", permit_number="...")
mcp__etrakit-mcp__get_permit_details(city="...", permit_number="...")
```

### Property Appraiser
**MCP Server:** `mcp__property-appraiser-mcp__*`

```
mcp__property-appraiser-mcp__search_property(county="broward", address="...")
mcp__property-appraiser-mcp__get_property_details(folio="...")
```

### Government Data
**MCP Server:** `mcp__govdata-mcp__*` — Building permits, code violations, zoning data.

---

## RESEARCH TOOLS

### Academic Research
**MCP Server:** `mcp__research-mcp__*`

### HuggingFace Datasets
**MCP Server:** `mcp__datasets-mcp__*`

---

## VISUAL MEMORY

**MCP Server:** `mcp__visual-memory__*`

```
mcp__visual-memory__memory_start_capture()
mcp__visual-memory__memory_search(query="...")
mcp__visual-memory__memory_recall_recent()
mcp__visual-memory__memory_recall_app(app="...")
```

---

*Last Updated: 2026-02-23*

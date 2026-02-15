# Ralph's AI-Augmented Architect Workstation
## Complete System Inventory
**Generated:** January 22, 2026

---

## EXECUTIVE SUMMARY

| Category | Count | Status |
|----------|-------|--------|
| **MCP Servers (Active)** | 12+ | Running |
| **RevitMCPBridge Methods** | 449 | Production |
| **Custom Tools/Scripts** | 50+ | Active |
| **Skill Files** | 20 | Documented |
| **Memory Entries** | 550+ | Accumulated |
| **Projects Tracked** | 60+ | In Memory |
| **Session Hooks** | 12 | Configured |

---

## PART 1: CORE INFRASTRUCTURE

### 1.1 RevitMCPBridge (Crown Jewel)

| Version | Location | Status | Methods |
|---------|----------|--------|---------|
| **RevitMCPBridge2026** | `/mnt/d/RevitMCPBridge2026/` | Active | 449 endpoints |
| **RevitMCPBridge2025** | `/mnt/d/RevitMCPBridge2025/` | Active | Legacy support |

**Capabilities (234 memories documented):**
- Wall creation (single, batch, polyline)
- Door/window placement with host detection
- Room creation and numbering
- View management (floor plans, sections, elevations, 3D)
- Sheet creation with auto-titleblock detection
- Viewport placement and alignment
- Text notes, dimensions, annotations
- Family loading and placement
- Schedule creation
- PDF/image export
- CAD linking
- Autonomous measurement (distances, corridors, room areas)
- Zoom control (grid intersection, region, element)
- Change tracking and validation

**Key Innovations:**
- WarningSwallower pattern (prevents transaction rollback)
- Multi-firm standards detection via titleblock
- Sheet pattern detection and suggestion
- Self-expanding capability system

### 1.2 System Bridge Daemon

**Location:** `/mnt/d/_CLAUDE-TOOLS/system-bridge/`

**Status:** Running since Dec 4, 2025 (49 days, 0 errors)

**What it tracks (every 10 seconds):**
- Open applications and window titles
- Which Revit project is active
- Bluebeam document status
- Monitor configuration (3x 2560x1440)
- CPU/memory usage
- Clipboard content
- Recent files accessed
- App open/close events

**Output:** `live_state.json` - Read by Claude at session start

### 1.3 Memory System (claude-memory MCP)

**Location:** `/mnt/d/_CLAUDE-TOOLS/claude-memory-server/`

**Current Stats:**
- 550+ total memories
- 60+ projects tracked
- 234 memories for RevitMCPBridge2026 alone
- Self-improvement loop with correction tracking

**Memory Types Stored:**
- Decisions (architectural patterns, workflow choices)
- Facts (API quirks, parameter formats, dimensions)
- Outcomes (what worked, what didn't)
- Errors (bugs encountered, solutions found)
- Corrections (mistakes Claude made, how to avoid)
- Preferences (your text sizes, grid patterns, layout rules)

---

## PART 2: MCP SERVERS

### 2.1 Active MCP Servers

| Server | Location | Purpose |
|--------|----------|---------|
| **claude-memory** | `_CLAUDE-TOOLS/claude-memory-server/` | Persistent memory with self-improvement |
| **voice-mcp** | `_CLAUDE-TOOLS/voice-mcp/` | Text-to-speech (Edge TTS) |
| **bluebeam-mcp** | `_CLAUDE-TOOLS/bluebeam-mcp/` | Bluebeam Revu automation |
| **floor-plan-vision** | `_CLAUDE-TOOLS/floor-plan-vision-mcp/` | PDF floor plan extraction |
| **windows-browser** | `_CLAUDE-TOOLS/windows-browser-mcp/` | Browser automation |
| **ai-render-mcp** | `_MCP-SERVERS/ai-render-mcp/` | Stable Diffusion rendering |
| **autocad-mcp** | `_MCP-SERVERS/autocad-mcp/` | AutoCAD automation |
| **sqlite-server** | (npm package) | Database operations |
| **aider-mcp (x3)** | (quasar/ollama/llama4) | AI code editing |

### 2.2 Archived/Experimental MCP Servers

| Server | Purpose | Status |
|--------|---------|--------|
| email-ops-mcp | Email operations | Archived |
| git-mcp | Git operations | Available |
| postgres-inspect-mcp | Database inspection | Available |
| pdf-summarizer-mcp | PDF analysis | Available |
| ollama-orchestrator-mcp | Local LLM orchestration | Available |
| web-scraper-mcp | Web scraping | Available |
| heygen-mcp | Video generation | Experimental |
| video-mcp | Video processing (SadTalker) | Experimental |

---

## PART 3: CUSTOM TOOLS

### 3.1 Revit Automation Tools

| Tool | Location | Purpose |
|------|----------|---------|
| **revit-startup-helper** | `_CLAUDE-TOOLS/revit-startup-helper/` | Auto-dismiss Revit dialogs |
| **revit-live-view** | `_CLAUDE-TOOLS/revit-live-view/` | Live viewport capture |
| **revit-model-extractor** | `_CLAUDE-TOOLS/revit-model-extractor/` | Extract model data |
| **revit-ui-controller** | `_CLAUDE-TOOLS/revit-ui-controller/` | UI automation |
| **revit-activity-journal** | `_CLAUDE-TOOLS/revit-activity-journal/` | Activity logging |
| **perimeter-tracer** | `_CLAUDE-TOOLS/perimeter-tracer/` | Floor plan boundary detection |
| **bim-validator** | `_CLAUDE-TOOLS/bim-validator/` | Post-operation validation |

### 3.2 Workflow Automation Tools

| Tool | Location | Purpose |
|------|----------|---------|
| **brain-state** | `_CLAUDE-TOOLS/brain-state/` | Session persistence, checkpoints |
| **email-monitor** | `_CLAUDE-TOOLS/email-monitor/` | Gmail monitoring |
| **email-watcher** | `_CLAUDE-TOOLS/email-watcher/` | Email alerts |
| **inbox-filer** | `_CLAUDE-TOOLS/inbox-filer/` | Auto-file emails to projects |
| **gmail-sender** | `_CLAUDE-TOOLS/gmail-sender/` | Send emails |
| **pipelines** | `_CLAUDE-TOOLS/pipelines/` | Formal workflow execution |
| **project-state** | `_CLAUDE-TOOLS/project-state/` | Project state tracking |

### 3.3 AI Enhancement Tools

| Tool | Location | Purpose |
|------|----------|---------|
| **ai-render** | `_CLAUDE-TOOLS/ai-render/` | Architectural rendering |
| **video-learning-pipeline** | `_CLAUDE-TOOLS/video-learning-pipeline/` | Learn from YouTube (70.1% complete) |
| **pattern-analysis** | `_CLAUDE-TOOLS/pattern-analysis/` | Memory pattern detection |
| **self-improvement-hooks** | `_CLAUDE-TOOLS/self-improvement-hooks/` | Correction tracking |
| **proactive-memory** | `_CLAUDE-TOOLS/proactive-memory/` | Memory surfacing |

### 3.4 System Tools

| Tool | Location | Purpose |
|------|----------|---------|
| **system-bridge** | `_CLAUDE-TOOLS/system-bridge/` | Windows state monitoring |
| **backup-system** | `_CLAUDE-TOOLS/backup-system/` | Automated backups |
| **verification** | `_CLAUDE-TOOLS/verification/` | Work verification |
| **pre-flight-check** | `_CLAUDE-TOOLS/pre-flight-check/` | Pre-operation validation |
| **post-revit-check** | `_CLAUDE-TOOLS/post-revit-check/` | Post-Revit validation |
| **self-healing** | `_CLAUDE-TOOLS/self-healing/` | Error recovery |

---

## PART 4: SKILL FILES

### 4.1 Revit/BIM Skills

| Skill | Purpose |
|-------|---------|
| `revit-model-builder.skill` | Wall patterns, coordinate systems |
| `pdf-to-revit.skill` | PDF extraction pipeline |
| `bim-quality-validator.skill` | Validation checklists |
| `revit-mcp-gotchas.skill` | Known issues and fixes |
| `cd-set-assembly.skill` | Construction document production |
| `markup-to-model.skill` | PDF/CAD to Revit workflow |

### 4.2 Workflow Skills

| Skill | Purpose |
|-------|---------|
| `context-management.skill` | Context window optimization |
| `claude-orchestration.skill` | Sub-agent deployment |
| `autonomous-pipeline.skill` | Autonomous execution |
| `autonomous-checkpoints.skill` | Progress tracking |
| `bd-project-init.skill` | Project initialization |
| `pdf-to-rentable-sf.skill` | Square footage extraction |

### 4.3 General Skills

| Skill | Purpose |
|-------|---------|
| `code-review-helper.skill` | Code quality |
| `product-manager.skill` | PRDs, roadmaps |
| `product-designer.skill` | UX patterns |
| `marketing-writer.skill` | Copy writing |
| `meeting-notes-processor.skill` | Meeting notes |
| `email-drafter.skill` | Email composition |
| `idea-validator.skill` | Idea evaluation |
| `launch-planner.skill` | Launch planning |

---

## PART 5: SESSION HOOKS (Automation)

### 5.1 SessionStart Hooks (7 hooks)
1. System bridge daemon check
2. Brain state loading
3. Email status check
4. Proactive memory surfacing
5. Project state loading
6. Spaced repetition (correction review)
7. Weekly maintenance

### 5.2 UserPromptSubmit Hooks (3 hooks)
1. Auto-checkpoint
2. Conversation logging
3. Correction detection

### 5.3 PreToolUse Hooks (2 hooks)
1. Revit parameter validation (rule engine)
2. Correction check before action

### 5.4 PostToolUse Hooks (3 hooks)
1. C# auto-formatting (dotnet format)
2. Post-Revit validation check
3. (Same for Write tool)

### 5.5 Stop Hooks (2 hooks)
1. Save session to brain state
2. Verification reminder

---

## PART 6: ACTIVE PROJECTS IN MEMORY

### Client Projects
- R25 SMH ELEV 1 AND 2_ARCH (current)
- AVENTURA ECO OFFICES
- BHN CATH SUITES PHASE 2
- GOULDS-TOWER-1
- 6041 NW 84 TER

### Development Projects
- RevitMCPBridge2026 (234 memories)
- RevitMCPBridge2025 (26 memories)
- FloorPlanML (37 memories)
- FloorPlanTracer (13 memories)
- Claude-Code-Workflow (29 memories)
- site-data-api (5 memories)

### Reference Projects (Extracted)
- 512 Clematis (5-story multi-family)
- Avon Park Single Family
- Hilaire Residential Duplex
- South Golf Cove Residence
- Snowdon Towers (Arch, Struct, MEP)

---

## PART 7: WHAT WORKS (Proven Capabilities)

### Tested and Reliable
- [x] Wall creation (single, batch, polyline)
- [x] Door/window placement
- [x] Room creation and numbering
- [x] Sheet creation with correct titleblock
- [x] Viewport placement and alignment
- [x] Text notes and annotations
- [x] View export (PNG/PDF)
- [x] CAD linking
- [x] Family loading from library
- [x] Email monitoring and response
- [x] System state awareness
- [x] Memory persistence across sessions
- [x] Correction tracking and learning

### Works But Needs Refinement
- [ ] PDF-to-Revit wall extraction (6-8 months)
- [ ] Dimension reading from PDFs
- [ ] Family editing automation
- [ ] Detail library management
- [ ] Autonomous CD production

### Planned/Skeleton Only
- [ ] BIMobject family search
- [ ] Full autonomy (Level 5)
- [ ] Multi-project orchestration

---

## PART 8: KEY LEARNINGS (Top Corrections)

1. **Use `params` not `parameters`** in MCP calls
2. **Titleblock determines firm** - not folder structure
3. **Wait after openDocument** before querying
4. **WarningSwallower required** for all transactions
5. **CMU insertion at BOTTOM-LEFT** not center
6. **Pipe names include "Bridge"** - RevitMCPBridge2026
7. **Copied views can't be placed** on sheets (API limitation)
8. **Check coordinate units** from external sources
9. **Always verify after placement** - element may roll back
10. **Never estimate wall positions** - extract actual coordinates

---

## ESTIMATED VALUE

| Metric | Value |
|--------|-------|
| Development hours | 500-900 |
| Cost to recreate | $75,000-$225,000 |
| Unique IP | RevitMCPBridge (no competitor) |
| Production tested | 4+ real client projects |
| Market potential | $50,000-$150,000/year enterprise |

---

*This inventory represents 6+ months of continuous development and testing on real architectural projects.*

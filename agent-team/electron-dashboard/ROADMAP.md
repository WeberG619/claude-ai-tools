# Agent Team Dashboard - Capability Roadmap

## Current Capabilities ✓
- [x] Agent speaking indicators (green glow)
- [x] Voice synthesis (5 unique voices)
- [x] Live browser view (any website)
- [x] Terminal output display
- [x] Code display with syntax highlighting
- [x] Real-time status synchronization

---

## Phase 1: File Viewing (High Priority)

### PDF Viewing
- Use **pdf.js** (Mozilla's PDF renderer)
- Render PDFs directly in the main content area
- Agent can "open" a PDF and it displays live
- Support page navigation, zoom

### Word Documents (.docx)
- Use **mammoth.js** to convert Word → HTML
- Display formatted documents in the view
- Preserve formatting, tables, images

### Excel Spreadsheets (.xlsx)
- Use **SheetJS** to parse Excel files
- Render as interactive table in the view
- Show formulas, charts if possible

### Images & Diagrams
- Native image display
- Support PNG, JPG, SVG, diagrams
- Zoom and pan capabilities

### Implementation:
```javascript
// In main.js - add file viewer protocols
function showFile(filePath) {
    const ext = path.extname(filePath).toLowerCase();

    switch(ext) {
        case '.pdf':
            // Load PDF.js viewer with file
            mainWindow.loadURL(`file://${__dirname}/viewers/pdf.html?file=${filePath}`);
            break;
        case '.docx':
            // Convert with mammoth, display HTML
            convertAndDisplay(filePath);
            break;
        case '.xlsx':
            // Parse with SheetJS, render table
            renderSpreadsheet(filePath);
            break;
    }
}
```

---

## Phase 2: Interactive Browser (Medium Priority)

### Playwright Integration
- Replace passive BrowserView with Playwright-controlled browser
- Agents can actually click, type, navigate
- Can log into websites (with stored credentials)
- Can fill forms, download files

### Use Cases:
- Researcher logs into documentation sites
- Builder interacts with GitHub (create issues, PRs)
- Agents can use web tools (Figma, Google Docs, etc.)

---

## Phase 3: File System Access (Medium Priority)

### File Browser Panel
- Tree view of project directories
- Click to open files in main view
- Show recently accessed files

### File Operations
- Create new files (shown live)
- Edit existing files
- Delete/rename with confirmation

### Drag & Drop
- Drop files onto dashboard to open
- Drop to specific agent to "give" them a file

---

## Phase 4: Multi-View Layout (Nice to Have)

### Split Screen
- Research on left, code on right
- Browser + terminal side by side
- Compare two files

### Tabs
- Multiple browser tabs visible
- Switch between open files
- Tab history

---

## Phase 5: Real Agent Autonomy (Advanced)

### Claude API Integration
- Agents call Claude API for actual reasoning
- Real decisions, not scripted responses
- Can handle unexpected situations

### Tool Use
- Agents have access to MCP tools
- Can read/write files
- Can run commands
- Can search the web

### Memory & Learning
- Agents remember previous sessions
- Learn from mistakes
- Improve over time

---

## Technical Requirements

### For File Viewing:
```bash
npm install pdfjs-dist mammoth xlsx
```

### For Playwright Integration:
```bash
npm install playwright
```

### For File System:
- Already have Node.js fs access
- Need UI components for file browser

---

## Priority Order

1. **PDF Viewing** - Most requested, high impact
2. **Word Documents** - Common business use case
3. **Interactive Browser** - Enables real work
4. **File Browser Panel** - Better UX
5. **Excel Support** - Business use case
6. **Split Views** - Power user feature
7. **Real Autonomy** - Long-term goal

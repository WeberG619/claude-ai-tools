# PDF Markup Analyzer - Implementation Plan
**Planner: ANDREW**
**Date: 2026-02-03**

## Executive Summary

Build a Python tool that extracts markups from Bluebeam PDFs, categorizes them (RFI, ASI, correction, question), converts them to actionable tasks with priority/location, and generates punch lists in multiple formats.

---

## Architecture Overview

```
pdf_markup_analyzer/
├── src/
│   ├── __init__.py
│   ├── extractor.py          # PDF annotation extraction (PyMuPDF/fitz)
│   ├── parser.py             # Parse markup content (text, geometry)
│   ├── categorizer.py        # ML/rule-based categorization
│   ├── task_generator.py     # Convert to actionable tasks
│   ├── tracker.py            # Track addressed/pending markups
│   ├── exporters/
│   │   ├── __init__.py
│   │   ├── json_exporter.py
│   │   ├── csv_exporter.py
│   │   └── markdown_exporter.py
│   └── models/
│       ├── __init__.py
│       ├── markup.py         # Markup dataclass
│       └── task.py           # Task dataclass
├── cli.py                    # Command-line interface
├── server.py                 # MCP server (optional)
├── requirements.txt
└── tests/
    ├── test_extractor.py
    ├── test_categorizer.py
    └── sample_pdfs/
```

---

## Phase 1: PDF Annotation Extraction

### 1.1 Core Extraction (PyMuPDF/fitz)

**Why PyMuPDF**: Native Python, handles both standard PDF annotations AND Bluebeam's proprietary markup format via the `/Annots` array.

```python
# Key extraction targets from PDF structure:
- /Annots array on each page
- Annotation types: /Text, /Highlight, /FreeText, /Ink, /Polygon (clouds), /Line, /Square, /Circle
- Bluebeam-specific: /BS (border style), /Subj (subject field), /RC (rich content)
- FDF/XFDF export if available (Bluebeam Studio export)
```

**Extraction Algorithm**:
1. Open PDF with `fitz.open()`
2. Iterate pages: `for page in doc:`
3. Get annotations: `page.annots()`
4. For each annotation extract:
   - Type (`annot.type`)
   - Content (`annot.info['content']`)
   - Subject (`annot.info['subject']`) - Bluebeam uses this for tool name
   - Author (`annot.info['author']`)
   - Creation date (`annot.info['creationDate']`)
   - Rect (bounding box for location)
   - Color/appearance for categorization hints

### 1.2 Bluebeam-Specific Handling

Bluebeam markups have additional metadata:
- **Subject field**: Contains markup tool name (Cloud, Callout, Text Box, etc.)
- **Custom status**: Check/approval state
- **Layer info**: Which layer the markup is on

**XFDF Alternative**: If PDF direct extraction fails:
```bash
# Export from Bluebeam: Document > Export > Markup Summary (XFDF)
# Then parse the XML structure
```

---

## Phase 2: Content Parsing

### 2.1 Text Extraction

From annotation content and appearance streams:
```python
def parse_markup_text(annot):
    # Primary: content field
    text = annot.info.get('content', '')

    # Fallback: rich content (RC field)
    if not text:
        text = extract_from_rich_content(annot)

    # Callouts: text may be in appearance stream
    if annot.type == fitz.PDF_ANNOT_FREE_TEXT:
        text = annot.get_text()

    return text.strip()
```

### 2.2 Location Mapping

Convert PDF coordinates to construction coordinates:
```python
def map_location(rect, page, scale_factor):
    """
    rect: [x0, y0, x1, y1] in PDF points (72 per inch)
    page: page number
    scale_factor: drawing scale (e.g., 48 for 1/4"=1'-0")

    Returns: {sheet, gridlines, room_near, x_ft, y_ft}
    """
    # Calculate center point
    center_x = (rect.x0 + rect.x1) / 2
    center_y = (rect.y0 + rect.y1) / 2

    # Convert to real-world feet based on scale
    x_ft = (center_x / 72) * scale_factor
    y_ft = (center_y / 72) * scale_factor

    # Try to find nearby gridlines or room names
    # (requires OCR of drawing or linked CAD data)
```

---

## Phase 3: Categorization Engine

### 3.1 Rule-Based Categorization

**Category Definitions**:

| Category | Triggers | Priority Base |
|----------|----------|---------------|
| RFI | "RFI", "clarify", "confirm", "?" | Medium |
| ASI | "ASI", "revision", "change", "per ASI" | High |
| Correction | "correct", "fix", "error", "wrong", strikethrough | High |
| Question | "?", "verify", "check" | Medium |
| Note | "note:", "NIC", "typ", informational | Low |
| Add | "add", "+", cloud with no text | Medium |
| Delete | "delete", "remove", "x", strikethrough | Medium |

### 3.2 Pattern Matching

```python
CATEGORY_PATTERNS = {
    'RFI': [
        r'\bRFI\s*#?\d*',
        r'\bclarify\b',
        r'\bconfirm\b',
        r'.*\?$'  # Ends with question mark
    ],
    'ASI': [
        r'\bASI\s*#?\d+',
        r'\brevision\s*#?\d*',
        r'\bper\s+ASI\b'
    ],
    'CORRECTION': [
        r'\bcorrect\b',
        r'\bfix\b',
        r'\bshould\s+be\b',
        r'\bchange\s+to\b'
    ]
}
```

### 3.3 Visual Cues

- **Red markups**: Usually corrections/errors
- **Clouds**: Action items, areas of concern
- **Strikethrough**: Deletions
- **Arrows**: Relocations
- **Checkmarks/stamps**: Approved/reviewed

---

## Phase 4: Task Generation

### 4.1 Task Model

```python
@dataclass
class MarkupTask:
    id: str                    # Unique identifier
    source_markup_id: str      # Reference to original markup
    category: str              # RFI, ASI, CORRECTION, etc.
    priority: str              # HIGH, MEDIUM, LOW

    # Location
    sheet: str                 # Sheet number/name
    page: int                  # PDF page
    location_desc: str         # "Near gridline A-3" or "Room 101"
    coordinates: tuple         # (x, y) in drawing units

    # Content
    description: str           # What needs to be done
    original_text: str         # Raw markup text
    assigned_to: Optional[str] # Who should handle

    # Tracking
    status: str                # PENDING, IN_PROGRESS, COMPLETE
    created_date: datetime
    due_date: Optional[datetime]
    completed_date: Optional[datetime]
    notes: List[str]
```

### 4.2 Priority Assignment

```python
def calculate_priority(markup: Markup) -> str:
    score = 0

    # Category weight
    if markup.category in ['CORRECTION', 'ASI']:
        score += 30
    elif markup.category in ['RFI', 'ADD', 'DELETE']:
        score += 20
    else:
        score += 10

    # Author weight (architect comments > contractor)
    if markup.author in PRIORITY_AUTHORS:
        score += 20

    # Color weight
    if markup.color == 'red':
        score += 15

    # Keyword boosters
    if any(word in markup.text.lower() for word in ['urgent', 'asap', 'critical']):
        score += 25

    return 'HIGH' if score >= 50 else 'MEDIUM' if score >= 25 else 'LOW'
```

---

## Phase 5: Export Formats

### 5.1 JSON Export

```json
{
  "document": "2118_BHN_Corrections_2026-01-15.pdf",
  "extracted_date": "2026-02-03T10:30:00",
  "total_markups": 47,
  "summary": {
    "high_priority": 12,
    "medium_priority": 23,
    "low_priority": 12
  },
  "tasks": [
    {
      "id": "TASK-001",
      "category": "CORRECTION",
      "priority": "HIGH",
      "sheet": "A-101",
      "location": "Grid B-4, Room 102",
      "description": "Change wall type from W1 to W2 per structural",
      "status": "PENDING"
    }
  ]
}
```

### 5.2 CSV Export

```csv
ID,Category,Priority,Sheet,Location,Description,Status,Due Date
TASK-001,CORRECTION,HIGH,A-101,"Grid B-4, Room 102","Change wall type W1 to W2",PENDING,2026-02-10
```

### 5.3 Markdown Export (Punch List)

```markdown
# Punch List: 2118_BHN_Corrections
Generated: 2026-02-03

## HIGH Priority (12 items)

### Sheet A-101
- [ ] **TASK-001** [CORRECTION] Grid B-4, Room 102: Change wall type W1 to W2
- [ ] **TASK-002** [ASI #3] Grid C-2: Add fire damper at duct penetration

### Sheet A-201
- [ ] **TASK-003** [CORRECTION] Wall section: Fix ceiling height dimension
```

---

## Phase 6: Tracking System

### 6.1 SQLite Database Schema

```sql
CREATE TABLE markups (
    id TEXT PRIMARY KEY,
    pdf_path TEXT,
    page INTEGER,
    annot_index INTEGER,
    category TEXT,
    content TEXT,
    author TEXT,
    created_date TEXT,
    rect_x REAL, rect_y REAL, rect_w REAL, rect_h REAL
);

CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    markup_id TEXT REFERENCES markups(id),
    priority TEXT,
    status TEXT DEFAULT 'PENDING',
    assigned_to TEXT,
    due_date TEXT,
    completed_date TEXT,
    notes TEXT
);

CREATE TABLE status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT REFERENCES tasks(id),
    old_status TEXT,
    new_status TEXT,
    changed_by TEXT,
    changed_date TEXT
);
```

### 6.2 CLI Commands

```bash
# Extract and analyze
python cli.py analyze /path/to/markup.pdf --output punch_list.json

# Update status
python cli.py update TASK-001 --status COMPLETE --notes "Fixed per ASI #3"

# Generate report
python cli.py report --format markdown --filter "status=PENDING,priority=HIGH"

# Compare two versions (what's new/resolved)
python cli.py diff old_extract.json new_extract.json
```

---

## Phase 7: Integration Points

### 7.1 Existing Weber Tools

| Tool | Integration |
|------|-------------|
| Bluebeam MCP | Alternative extraction via `take_screenshot` + vision |
| RevitMCPBridge | Apply corrections directly to Revit |
| markup-to-model pipeline | Task generation feeds into model updates |
| claude-memory | Store extraction results, track patterns |

### 7.2 MCP Server (Optional)

```python
# server.py - Expose as MCP tools
@server.list_tools()
async def list_tools():
    return [
        Tool(name="extract_markups", ...),
        Tool(name="categorize_markup", ...),
        Tool(name="generate_punch_list", ...),
        Tool(name="update_task_status", ...),
        Tool(name="get_pending_tasks", ...)
    ]
```

---

## Research Questions for GUY

1. **Bluebeam SDK**: Does Bluebeam expose a COM API or .NET SDK for direct markup access? (More reliable than PDF parsing)

2. **XFDF vs Direct**: Which is more complete - Bluebeam's XFDF export or direct PDF annotation parsing?

3. **Coordinate Reference**: Best practices for mapping PDF coordinates to construction gridlines/rooms?

4. **NLP Categorization**: Any lightweight NLP models for AEC-specific text classification?

5. **Existing Tools**: Are there commercial tools doing this we can learn from (e.g., Newforma, BIM 360 Issues)?

---

## Implementation Order

1. **Week 1**: Core extraction (`extractor.py`) + basic parsing
2. **Week 2**: Categorization engine + task generation
3. **Week 3**: Export formats + CLI
4. **Week 4**: SQLite tracking + status management
5. **Week 5**: MCP integration + testing with real PDFs

---

## Success Criteria

- [ ] Extract 95%+ of Bluebeam markups from test PDFs
- [ ] Correctly categorize 80%+ of markups automatically
- [ ] Generate valid punch lists in all 3 formats
- [ ] Track status changes with full audit trail
- [ ] Process 100-page PDF in under 30 seconds

---

*Handoff to GUY the Researcher for validation and additional research.*

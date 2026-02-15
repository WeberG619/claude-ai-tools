# Revit Automation Tools

PowerShell scripts for automating Revit tasks via RevitMCPBridge.

## Requirements

- Revit 2025 or 2026 with RevitMCPBridge add-in loaded
- PowerShell 5.1+
- Named pipe connection active (RevitMCPBridge2025 or RevitMCPBridge2026)

## Usage

All scripts require `-Version` parameter (2025 or 2026):

```powershell
.\01-sheet-audit.ps1 -Version 2026
```

## Tools (15 total)

### Document Analysis

| # | Script | Purpose |
|---|--------|---------|
| 01 | `sheet-audit.ps1` | Analyze sheets - find empty and generic-named sheets |
| 02 | `project-status.ps1` | Dashboard showing sheets, views, levels, wall types |
| 05 | `unplaced-views.ps1` | Find views not placed on any sheet |
| 06 | `titleblock-audit.ps1` | Show titleblock families and usage counts |
| 10 | `view-organizer.ps1` | Views by type with placement status |

### Element Data

| # | Script | Purpose |
|---|--------|---------|
| 08 | `room-data.ps1` | Export room schedule (name, number, area, level) |
| 11 | `wall-audit.ps1` | Wall types with instance counts |
| 13 | `level-info.ps1` | Levels with elevations and floor-to-floor heights |
| 14 | `door-schedule.ps1` | Door schedule export |
| 15 | `family-count.ps1` | Count elements by category |

### Sheet Operations

| # | Script | Purpose |
|---|--------|---------|
| 03 | `sheet-rename.ps1` | Batch rename sheets from JSON file |
| 04 | `viewport-placer.ps1` | Place views on sheets with layout patterns |
| 12 | `sheet-creator.ps1` | Create new sheets (single or batch) |

### Export/Capture

| # | Script | Purpose |
|---|--------|---------|
| 07 | `quick-capture.ps1` | Capture active view to image |

### CAD Integration

| # | Script | Purpose |
|---|--------|---------|
| 09 | `cad-links.ps1` | List CAD imports and links |

## Common Options

- `-DryRun` - Preview changes without executing (03, 04, 12)
- `-ExportJson` - Export results to JSON file (08)
- `-ExportCsv` - Export results to CSV file (14)
- `-ViewType` - Filter by view type (05, 10)

## Examples

```powershell
# Get project overview
.\02-project-status.ps1 -Version 2026

# Find unplaced floor plans
.\05-unplaced-views.ps1 -Version 2026 -ViewType FloorPlan

# Batch rename sheets (preview)
.\03-sheet-rename.ps1 -Version 2026 -MappingFile "renames.json" -DryRun

# Export room data to JSON
.\08-room-data.ps1 -Version 2026 -ExportJson

# Capture current view
.\07-quick-capture.ps1 -Version 2026 -OutputPath "D:\screenshot.png"

# Create new sheet (preview)
.\12-sheet-creator.ps1 -Version 2026 -SheetNumber "A1.0" -SheetName "FLOOR PLAN" -DryRun

# Count all elements
.\15-family-count.ps1 -Version 2026
```

## JSON File Formats

### Sheet Renames (03-sheet-rename.ps1)
```json
{
  "renames": [
    { "sheetNumber": "A1.0", "newName": "FLOOR PLAN - LEVEL 1" }
  ]
}
```

### New Sheets (12-sheet-creator.ps1)
```json
{
  "sheets": [
    { "sheetNumber": "A1.0", "sheetName": "FLOOR PLAN" }
  ]
}
```

## Notes

- Scripts connect via named pipes (not HTTP)
- Revit must have the MCP bridge add-in loaded
- Some data fields depend on what the API exposes
- Use `-DryRun` to preview changes before executing

---
Created: 2026-01-29 | Updated: 2026-01-29

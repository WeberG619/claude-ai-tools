# 2-144 MSMC Miami Shores Physician Practice - Project State

> **Last Updated:** 2026-02-20 10:15
> **Phase:** 60% CD (per Paola's markups)
> **Revit File:** R25 MSMC MIAMI SHORES (Revit 2025)
> **Markups PDF:** 2026.02.16 MIAMI SHORES_ARCH_MARKUPS-DESKTOP-01CMLA9.pdf

---

## RESUME POINT

**Last session (2026-02-20):** Implemented bulk view cleanup operations via MCP - hidden equipment/dimensions across multiple views, placed wall tags in A102-A/B, set wall Type Marks, dimensioned toilet rooms, named Room 116, hidden elevations in A102-B.

**Next step:** Continue with keynote placement (manual - needs element identification), elevation work (A201), partition details (A501), and schedule updates (A801). Scope boxes require manual VG override in Revit UI.

---

## MARKUP TRACKER (391 annotations across 30 pages, by Paola Gomez)

### Status Key: [ ] = TODO, [~] = In Progress, [x] = Done, [!] = Manual (can't automate via MCP)

### A000 - Cover (7 markups)
- [ ] Add Reliance Engineering info
- [ ] Update date to 02/20/26 (typ all sheets)
- [ ] Mark as 60% CD
- [ ] Show consultant info on all pages

### A001 - General Notes (4 markups)
- [ ] Coordinate w/ consultants drawings, update to 03/09/26
- [ ] Add consultants typ. all pages

### A002 - Accessibility (Clean)

### A100 - Floor Plan Demolition (5 markups)
- [ ] Update per Life Safety markups (ref: CODE REVIEW folder)
- [ ] Hide elements per markup

### SD-101 - SD Plan (Clean)

### A101 - Roof Plan Demolition (3 markups)
- [ ] Add keynote 121: Remove portion of existing roof for future roof hatch
- [ ] Show existing to remain roof drains

### A102 - Floor Plan New Work Overall (51 markups)
- [x] Hide dimensions typ. (filter "HIDE - Dimensions" applied, filterId 2007518)
- [x] Hide equipment/Generic Models (8 elements hidden)
- [ ] Show elevations (add elevation references)
- [ ] Add elevation markers
- [ ] Hide miscellaneous elements per redlines

### A102-A - Floor Plan New Work Area A (80 markups) **HEAVIEST**
- [!] Add keynote 201: Seal existing exterior door (keynote file has entry, needs manual placement)
- [!] Add keynote 203: Provide window shade (keynote file has entry, needs manual placement)
- [ ] Continuous line dimensions
- [x] Hide phone and equipment (23 Generic Models hidden - Philips monitors, diagnostic sets, scale)
- [ ] Partition type note: "All partitions type ___ U.N.O."
- [ ] Update per new site specific
- [ ] ALIGN callouts (x7) - align walls/elements
- [x] Wall type tags throughout (~106 tags placed via tagAllByCategory)

### A102-B - Floor Plan New Work Area B (53 markups)
- [!] Add keynotes 201, 202, 203 (keynote file has entries, needs manual placement)
- [!] Keynote 202: Roof access ladder (keynote file has entry)
- [x] Hide elevations in this view (19 elevation markers hidden)
- [x] Hide equipment (25 elements hidden - Generic Models + Furniture Systems)
- [ ] Partition note: Only partitions with drywall to deck, all others 6" above ceiling
- [x] Wall type tags throughout (~118 tags placed via tagAllByCategory)

### A103 - Roof Plan New Work (12 markups)
- [!] Keynote 301: New RTU on existing roof curb (x6 locations) - needs manual placement
- [!] Keynote 302: Clean up existing to remain roof drains - needs manual placement
- [ ] Show existing to remain roof drains in demo plan
- [ ] Call out to roof hatch detail

### A104 - Reflected Ceiling Plan (11 markups)
- [ ] Coordinate with site specific drawings
- [ ] 3x proposed sign locations
- [!] Hide scope box typ. (cannot hide via API - requires manual VG override)

### A104-A/B - RCP Enlarged (Clean)

### A105 - Finishes Plan (16 markups)
- [ ] Hide cubicles (no cubicle elements found in view - may not be modeled yet)
- [x] Hide phones and equipment (19 Generic Models hidden)
- [ ] CG notation

### A105-A - Finishes Plan Area A (3 markups)
- [x] Hide phones and equipment (24 Generic Models hidden)

### A105-B - Finishes Plan Area B (12 markups)
- [ ] Hide cubicles (no cubicle elements found - may not be modeled)
- [x] Hide various elements (17 Generic Models hidden)

### A106 - Equipment Plan (4 markups)
- [x] Hide all dimensions (filter applied, 0 dims found = already hidden)
- [ ] Update equipment per new pods layout

### A106-A/B - Equipment Enlarged (0-2 markups, minor)

### A201 - Building Elevations (73 markups) **VERY HEAVY**
- [!] Hide scope boxes typ. (cannot hide via API - requires manual VG override)
- [ ] Add elevation to door/window legend & schedule
- [!] Keynotes 401-404 (keynote file has all entries, needs manual placement):
  - 401: Seal existing exterior door, caulk sealant
  - 402: Existing fabric awning (multiple locations)
  - 403: Full height frosted window film
  - 404: Frosted window film first 48" AFF
- [ ] Show signage with power connection (2 locations)
- [ ] Add west elevation to show signage
- [ ] Show sidewalk line
- [ ] Show unit tags (Units 1-8)
- [ ] Level markers

### A401-A402 - Enlarged Floor Plans (Clean)

### A403 - Internal Elevations (9 markups)
- [ ] Make hatch lighter
- [ ] Add section detail ref MSOP 220

### A404 - Internal Elevations (10 markups)
- [ ] Add bench detail
- [ ] Add handle
- [ ] Tags

### A405 - Enlarged Toilet Plans (25 markups)
- [x] Dimension toilet rooms (batchDimensionWalls completed for 3 toilet views)
- [ ] Tag toilet accessories typ. (x3 rooms)
- [x] Show dimensions typ. (dims placed via batchDimensionWalls)

### A501 - Partition Types (31 markups) **HEAVY**
- [ ] Add shielding report
- [ ] Partition A1: typical with drywall up to 6" above ceiling level
- [ ] Update lead-lined partition detail to show drywall ends 6" above ceiling level (x3 details)

### A502 - Details (Clean)

### A601 - Details (10 markups)
- [x] Add new sheet A503 (already exists in model)
- [ ] Add roof ladder access detail (ref: CODE REVIEW/DETAIL REFERENCE/ACCESS LADDER)

### A801 - Millwork/Schedules (14 markups)
- [ ] Slide over and update door schedule
- [ ] Update schedules
- [ ] W2 markup

### A801 (cont) - Millwork (2 markups)
- [ ] Add bench detail

---

## COMPLETED VIA MCP (this session)

| Action | View(s) | Elements | Method |
|--------|---------|----------|--------|
| Set wall Type Marks | All | 9 wall types (A3, B3, B6, C, B1, C1, F0) | setParametersBatch |
| Wall tags A102-A | 1365473 | ~106 wall tags | tagAllByCategory |
| Wall tags A102-B | 1365701 | ~118 wall tags | tagAllByCategory |
| Hide equipment A102 | 1193010 | 8 Generic Models | hideElementsInView |
| Hide equipment A102-A | 1365473 | 23 Generic Models | hideElementsInView |
| Hide equip+furn A102-B | 1365701 | 25 elements | hideElementsInView |
| Hide equipment A105 | 1818424 | 19 Generic Models | hideElementsInView |
| Hide equipment A105-A | 1822106 | 24 Generic Models | hideElementsInView |
| Hide equipment A105-B | 1822345 | 17 Generic Models | hideElementsInView |
| Hide elevations A102-B | 1365701 | 19 markers | hideElementsInView |
| Dim filter A102 | 1193010 | Filter 2007518 | createViewFilter + applyFilterToView |
| Dim filter A106 | 1356498 | Filter 2007518 | applyFilterToView |
| Toilet dims (3 views) | 1685534, 1686271, 1686450 | 6 dim strings | batchDimensionWalls |
| Name Room 116 | - | EXAM 116 (ID 2003575) | setParametersBatch |
| Sheet A503 | - | Already existed | createSheet (verified) |

---

## REQUIRES MANUAL REVIT WORK

| Item | Reason |
|------|--------|
| Scope box hiding (A104, A201) | SetCategoryHidden API doesn't support scope boxes |
| Keynote placement (201-203, 301-302, 401-404) | Need visual element identification for tag locations |
| Elevation marker addition (A102, A102-A) | Need specific viewport references |
| West elevation creation (A201) | Requires new view creation + placement |
| Partition detail updates (A501) | Detail drawing modifications |
| Schedule updates (A801) | Complex schedule editing |
| Cover/Notes updates (A000, A001) | Text block content changes |
| Bench details, roof hatch details | New detail drawings |
| Cubicle hiding (A105, A105-B) | No cubicle elements found in model |

---

## REVIT MODEL INVENTORY (as of 2026-02-20)

| Element | Count | Notes |
|---------|-------|-------|
| Rooms | 48 | All on First Floor, Room 116 = EXAM 116 |
| Walls | 251 | 15 of 47 types in use, 9 Type Marks set |
| Doors | 71 | 47 Single-Flush, 16 Storefront, already tagged |
| Windows | 2 | Interior fixed only |
| Ceilings | 56 | 44 ACT, 10 GWB Furring |
| Floors | 38 | All Concrete Slab 6" |
| Sheets | 74 | Full arch + MEP placeholder set (A503 exists) |
| Grids | 12 | 1-10 + A, B, C |
| Wall Tags | ~224 | A102-A (~106) + A102-B (~118) |
| View Filters | 3 | HIDE-Dimensions, HIDE-CommDevices, HIDE-FurnitureSystems |

---

## KEY VIEW IDS

| View | ID | Sheet |
|------|-----|-------|
| LEVEL 1 - FLOOR PLAN - NEW WORK | 1193010 | A102 |
| LEVEL 1 - FLOOR PLAN - NEW WORK - AREA A | 1365473 | A102-A |
| NEW WORK FLOOR PLAN- AREA B | 1365701 | A102-B |
| LEVEL 1 - FLOOR PLAN - EQUIPMENT | 1356498 | A106 |
| LEVEL 1 - RCP | 940887 | A104 |
| LEVEL 1 - FINISHES PLAN | 1818424 | A105 |
| LEVEL 1 - FINISHES PLAN - AREA A | 1822106 | A105-A |
| LEVEL 1 - FINISHES PLAN- AREA B | 1822345 | A105-B |
| ENLARGED FLOOR PLAN PATIENT TOILET | 1685534 | A405 |
| ENLARGED FLOOR PLAN PAT TOILET 141/142 | 1686271 | A405 |
| ENLARGED FLOOR PLAN STAFF TOILET | 1686450 | A405 |

---

## WALL TYPE MARKS

| Type ID | Type Name | Mark |
|---------|-----------|------|
| 795559 | Generic - 5" - A3 | A3 |
| 795467 | Generic - 5" - B3 | B3 |
| 795603 | Generic - 6.75" - B6 | B6 |
| 814741 | Generic - 4" - C | C |
| 790342 | 0_B3_ONE LAYER GYP... | B3 |
| 961795 | 0_A3_ONE LAYER GYP... | A3 |
| 1272596 | MS 3 5/8" + GWB + GWB... | B1 |
| 1337126 | MS 3 5/8" + GWB + CP... | C1 |
| 790346 | 0_F0 - GYP + HAT CHANNEL... | F0 |

---

## PRIORITY ORDER FOR REMAINING WORK

1. **Keynotes** (manual - needs element identification for tag placement)
2. **Elevations** (A201 signage/units, add west elevation, elevation markers)
3. **Partition details** (A501 lead-lined updates, 6" above ceiling)
4. **Schedules** (door schedule update)
5. **Details** (bench detail, roof hatch, ladder access)
6. **Cover/Notes** (A000/A001 date and consultant updates)
7. **Scope boxes** (manual VG override in Revit UI)
8. **Continuous line dimensions** (A102-A)

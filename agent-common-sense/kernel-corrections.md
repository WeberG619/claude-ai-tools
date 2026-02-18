# Auto-Generated Correction Rules
# Generated: 2026-02-18 14:36 from 63 corrections (62 after cleaning)
# DO NOT EDIT — regenerate with: python kernel_gen.py

## Revit / BIM (37 corrections)

- Used mcp__windows-browser__browser_click tool to click elements in Chrome browser for Fiverr automation — browser_click uses AutoHotkey screen coordinates which frequently click on wrong windows (Revit instead of Chrome), fail on popups, and don't register properly.
- Referred to the Windows user account "rick" as if it were the user's name, saying "The Windows user is rick" — The user is Weber Gouin, NEVER "Rick". The Windows account name happens to be "rick" but that is not the user's name.
- Attributed RevitMCPBridge2026 whitepaper to BD Architect LLC — RevitMCPBridge2026 and all MCP Bridge work is by BIM Ops Studio, not BD Architect LLC Do instead: All RevitMCPBridge2026 documentation, whitepapers, and materials should be attributed to BIM Ops Studio.
- Exported views without setting print/export settings — Default export settings produce low resolution, wrong scale, or missing elements. Views look different than in Revit.
- Created detail lines in wrong view or with wrong graphics style — Detail lines inherit their appearance from the view's line styles. Wrong style = invisible or wrong weight/pattern.
- Set parameter value without checking if parameter is read-only — Many Revit parameters are read-only (calculated, instance vs type, built-in). Setting them silently fails or throws exception.
- Used batch operations without delay between calls — Revit's document regeneration can't keep up with rapid API calls. This causes stale data reads, transaction conflicts, and element creation failures.
- Deleted elements without checking for dependencies — Deleting hosted elements (like walls) can cascade delete doors, windows, and other hosted items. Deleting views can break sheets.
- Assumed all coordinates from external sources (PDF, CAD, JSON) are in feet — External sources may use inches, millimeters, or pixels. Assuming feet results in elements that are 12x or 25.4x wrong size.
- Created schedule without specifying which fields to include — Schedules need explicit field definitions. A schedule with no fields or wrong fields is useless.
- Applied view template to view without checking compatibility — View templates have view type restrictions. Applying a floor plan template to a section view fails silently or causes incorrect display.
- Attempted to load family without checking if it already exists in project — Loading a family that already exists can cause duplicates or errors. Should check first.
- Placed elements on wrong level by using level name instead of level ID — Many methods require levelId (integer) not levelName (string). Using string causes null reference or wrong placement. Do instead: Always call getLevels first to get the correct levelId integer.
- Created rooms without checking if boundary walls are complete — Revit requires closed boundary loops to create rooms. Incomplete walls result in "Room is not in a properly enclosed region" error Do instead: Before createRoom: 1) Verify all walls are joined at corners using getWallJoins, 2) Check.
- Used "parameters" as the key name when calling RevitMCPBridge methods — The MCP server expects "params" not "parameters" as the key for method parameters Do instead: Always use "params" for the parameter object in MCP calls: {"method": "methodName", "params": {...}}. Never use "parameters".
- Tried to use getWallTypes immediately after openDocument or createNewProject — openDocument and createNewProject open/create documents but don't set them as the active UI document. All subsequent API calls that use uiApp.ActiveUIDocument.Document will get null reference error.
- Checked pipe name `RevitMCP2026` and `RevitMCP2025` — The actual pipe names are `RevitMCPBridge2026` and `RevitMCPBridge2025` — includes "Bridge" in the name Do instead: Always check pipes with full name pattern: `RevitMCPBridge2025` and `RevitMCPBridge2026`. Never abbreviate to `RevitMCP20XX`.
- Extended walls to distant features instead of stopping at actual room boundaries — Wall endpoints were calculated from distant reference points instead of the actual geometry Do instead: Stop wall at the actual room edge/column, not at distant features.
- Tried to place copied DraftingViews on sheets via Viewport.Create API — DraftingViews copied between Revit documents using copyElementsBetweenDocuments cannot be placed on sheets via API - Viewport.Create returns null Do instead: For transferring views between projects: 1) Create NEW DraftingView.
- Extracted walls from broad DXF coordinate ranges and placed them at arbitrary locations — The DXF has a huge coordinate range but only a SPECIFIC area matches the Revit model. Raw coordinates work - do NOT divide by 12. Do instead: ONLY use coordinates from CONFIRMED working areas.
- Created single walls from CAD lines without considering that walls have thickness — In architectural CAD, walls are represented by TWO parallel lines (inner and outer face), not single lines. Creating a wall from one line puts it in the wrong position.
- Assumed or invented walls where no CAD lines existed to fill in perceived gaps — Placed walls where there were no actual CAD wall lines, making assumptions about building layout Do instead: ONLY place walls where there are actual CAD wall lines (parallel line pairs).
- Placed walls based on CAD lines I found plus assumed connections between them — I invented wall placements where no CAD lines existed. I assumed walls should connect certain ways without verifying actual CAD line data.
- Extended horizontal wall to X=410.25, placed at Y=-111.92 — Wall extended too far (past the room boundary into corridor area) and was at wrong Y coordinate Do instead: Stop wall at the actual room edge/column, not at distant features. Check the correct Y coordinate for the wall position.
- Placed walls at coordinates derived from CAD corridor detection without verifying they align with actual wall lines in the CAD — Walls were placed at estimated corridor boundary positions, not on actual CAD wall lines. Corridor centerlines and widths are approximations, not precise wall locations.
- Attempted to use moveViewport with separate x and y parameters, and tried non-existent method removeViewportFromSheet — moveViewport requires newLocation as an array [x, y], not separate parameters. The method to remove viewports is removeViewport, not removeViewportFromSheet.
- Used source sheet viewport coordinates directly for target sheet placement — Source and target sheets may have different title blocks or margins - coordinates valid in source can be off-sheet in target Do instead: Before placing viewports, validate coordinates against target sheet bounds.
- Views copied between documents cannot be placed on sheets via Viewport.Create - it's a Revit API limitation with copied views themselves — The real issue was that EMPTY views (views without content) cannot be placed on sheets.
- CMU detail component Y insertion is at CENTER - place first CMU at Y=courseHeight/2 — CMU insertion point is at BOTTOM-LEFT corner, not center. Placing at Y=courseHeight/2 leaves CMU floating above grade. Do instead: Place first CMU at Y=0 (grade level). CMU insertion is at bottom-left corner.
- CMU detail component has CENTER insertion point — The CMU component (04-CMU-2 Core-Section) actually has LEFT EDGE insertion point, not center. When placed at X, the CMU visual left edge is at X and right edge is at X + 0.667' (8") Do instead: Place CMU at X = desired left edge position.
- Used file path and project number as primary detection methods for firm standards — Title block is the best/most reliable indicator of which firm a project belongs to Do instead: At session start, FIRST check the title block family name (getElements category='TitleBlocks'), then match against known.
- Created sheet A-8.3 with default title block (E1 30x42 Horizontal, ID 46795) — Should have used the project's active title block. The project uses "ARKY - Title Block" (ID 1508409) on all 69 sheets. The createSheet method should automatically detect and use the most-used title block in the project.
- The analyzeProjectGaps method flags all unplaced schedules and views as gaps/issues — Not all unplaced items are problems. Projects normally have working views, draft schedules, study views that are intentionally not on sheets. Flagging these creates noise and false positives.
- Created sheets and views with generic structure, guessing at organization and naming without properly studying and replicating the original project — The output looked bad because I was making assumptions instead of studying the working original project and replicating it exactly.
- Wall creation methods (createWall, batchCreateWalls) were failing with "Object reference not set to an instance of an object" error, and I initially thought it was a parameter format issue.
- Sheet Composition Rules - Stacked Floor Plans (Learned from User) Correct Layout for Two Floor Plans on 36"x24" Sheet **Viewport Positions:** - L1 (First/Ground Floor - bottom): X=1.1 ft, Y=0.58 ft - L2 (Second Floor - top): X=1.1 ft, Y=1.54 ft - Vertical spacing between viewport centers: ~0.96 ft.
- Wall thickness clarification for BHSF project: - Perimeter/exterior walls: 8 inches - Majority of interior walls: 6 inches - Some interior walls: 5 inches - Some interior walls: 8 inches User also loaded 18x18 square columns.

## Window Management (7 corrections)

- Used browser_send_keys without verifying which window had focus — Ctrl+Home went to VS Code instead of Excel because focus wasn't on Excel. browser_send_keys sends to whatever window currently has focus, not to a specific target.
- Used mcp__windows-browser__window_move and ShowWindow(SW_MAXIMIZE) to position Excel on the center monitor — The window_move MCP tool and ShowWindow are NOT DPI-aware. With 1.5x DPI scaling, coordinates are silently multiplied by 1.5, landing the window on the wrong monitor.
- Used monitor="center" for window_move and screenshots. Excel kept appearing on wrong monitor or spanning across monitors. — Weber's physical center monitor is the PRIMARY monitor (DISPLAY1, x=0). The screenshot tool's "center" maps to DISPLAY2 (x=-2560) which is NOT Weber's physical center.
- Positioned Excel at x=-2510 thinking it was the center monitor. It appeared on the left monitor instead. Then moved to x=50 (primary) which was the RIGHT monitor, not center. Kept guessing monitor positions instead of using get_monitors tool.
- Added calendar events using local time strings (e.g., "2026-01-26T08:00:00") expecting Pacific Time display — The calendar API interprets times as local to the system (ET), so times display 3 hours earlier than intended when viewed in Pacific timezone.
- Labeled monitors incorrectly: called primary monitor (x=0) "center", and x=-2560 as "left" — Weber's setup has primary monitor on the right side, not center.
- Gave a long list of all open applications when user asked about center monitor. Did not summarize. Did not auto-announce the result via speak.py. — User wants CONCISE answers that directly address the question.

## Email & Communication (5 corrections)

- Opened Outlook and Edge for email instead of Gmail in Chrome — Weber uses Gmail in Chrome, not Outlook. I should have opened Chrome directly to Gmail compose with the correct account (u/0 for weberg619@gmail.com) Do instead: For ANY email task: 1) Open Chrome to Gmail compose: Start-Process.
- Created an .ics file and opened it with default calendar app for adding calendar events — User has Google Calendar API access set up with OAuth token already authenticated Do instead: Use /mnt/d/_CLAUDE-TOOLS/google-calendar-mcp/calendar_client.py - supports add, today, week, upcoming, search.
- Tried to use OAuth-based Gmail API which requires browser authentication — OAuth requires browser popup for auth. The IMAP tool with app password works immediately with no browser needed.
- Tried to use browser clicking to download Gmail attachments instead of using the Gmail API — Browser clicking is unreliable and unnecessary. Gmail API credentials are already set up at /mnt/d/_CLAUDE-TOOLS/gmail-attachments/ Do instead: ALWAYS use the Gmail API tool at.
- Checked bridgeai619@gmail.com instead of the main email — User's main Gmail is weberg619@gmail.com, NOT bridgeai619@gmail.com. Bridge AI 619 is a secondary/test account. Do instead: Always check weberg619@gmail.com as the primary Gmail. This should be the default when user says "check my email".

## Architecture & Design (4 corrections)

- Identified firm for 512 Clematis project as "ARKY" based on folder structure (project stored in "01 - ARKY" folder) — The folder structure shows the CLIENT folder, not the architectural firm. Projects are often stored in client folders, but the actual design firm is different.
- Calculated parcel number as 412081452013 based on Section-Township-Range-Block-Lot format from the survey legal description — Charlotte County parcel numbers don't follow that format.
- Set Organization Name to "BD Architect LLC" for the 20 NW 76 Street project — BD Architect LLC is not the architect for this project Do instead: The architect of record for the 20 NW 76 Street project is Raymond E. Hall Architect.
- Started creating a separate Python workflow_orchestrator.py class — Claude Code itself IS the orchestrator. Building a separate Python orchestrator adds unnecessary complexity and doesn't match the architecture. Claude uses knowledge files + memory + MCP methods directly.

## General (3 corrections)

- Drew a simplified rectangular parapet cap instead of matching the user's reference cap profile — When user pastes a reference detail to teach me, I should study it carefully and replicate the exact profile/shape.
- Used reversed grid numbering - placed Grid 5 at x=0 (west) and Grid 1 at x=50 (east), which is backwards from the spec — The JSON spec clearly states Grid 1 is at x=0 (West face of garage - the ORIGIN), not Grid 5. I inverted the entire building coordinate system.
- Provided analysis and asked "Want me to build this?" without reading back a summary of completed work — User expects a verbal/written summary of completed work at the end of every significant task. This is a core workflow requirement.

## Deployment & Paths (2 corrections)

- Deployed RevitMCPBridge2026.dll to C:\ProgramData\Autodesk\Revit\Addins\2026\ — That's the system-wide addins folder. Weber's Revit 2026 loads addins from his user profile folder instead.
- Deployed RevitMCPBridge2026.dll to wrong paths including C:\ProgramData\Autodesk\Revit\Addins\2026\ and C:\Users\rick\AppData\Roaming\Autodesk\Revit\Autodesk Revit 2026\ — Those are not the correct deployment folders for Weber's Revit 2026 addin Do instead: Deploy RevitMCPBridge2026.dll to.

## Bluebeam / PDF (2 corrections)

- Placed annotation elements (text, tags, dimensions) in model space — Annotation elements must be placed in a view context, not in model space coordinates. They appear at wrong scale or location.
- When I saw a markup with strikethrough text and replacement text (e.g., ~~PASSAGE~~ → PRIVACY), I created a NEW text note with the corrected content instead of modifying the existing one. — CD markup conventions: strikethrough means EDIT IN PLACE, not add new.

## Excel & Desktop Automation (1 corrections)

- Said "done" after building an Excel dashboard without visually verifying the result. Reported success but the data was off-screen, charts were mispositioned, and the view was scrolled to wrong columns. — Never visually verified the Excel output.

## User Preferences (1 corrections)

- Signed email as "Rick" assuming that was the user's name — Rick is the computer technician who set up the system years ago - his name was never changed out. The user's actual name is Weber Gouin. Do instead: ALWAYS use "Weber Gouin" or "Weber" for the user's name.

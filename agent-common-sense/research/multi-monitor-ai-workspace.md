# Multi-Monitor Layouts for AI-Assisted Development Workflows

> **Research Date:** February 18, 2026
> **Target User:** Power user running Claude Code, VS Code, Revit, Excel, and browser simultaneously

---

## Table of Contents

1. [Monitor Configurations](#1-monitor-configurations)
2. [Window Layout for AI-Assisted Coding](#2-window-layout-for-ai-assisted-coding)
3. [Specific Layouts for AI + BIM Workflows](#3-specific-layouts-for-ai--bim-workflows)
4. [Ergonomics and Productivity Research](#4-ergonomics-and-productivity-research)
5. [Software Tools for Window Management](#5-software-tools-for-window-management)
6. [Recommended Configurations with Pricing](#6-recommended-configurations-with-pricing)
7. [Final Recommendation](#7-final-recommendation)

---

## 1. Monitor Configurations

### 1.1 Configuration Comparison

| Configuration | Pros | Cons | Best For |
|---|---|---|---|
| **Triple 27" 4K** | Independent positioning, one can go portrait, matched pixel density | Bezels between screens, more cables, wider desk needed | Developers who want a vertical code monitor |
| **34" Ultrawide + 27" Side** | Seamless center workspace, side monitor for reference | Mismatched sizes feel uneven, limited vertical pixels on ultrawide (1440p) | General dev work with reference material |
| **49" Super-Ultrawide + 27" Side** | Replaces two monitors seamlessly, massive center workspace | Expensive, curved screens can distort straight lines at edges, 1440p vertical limit | Multi-window workflows, side-by-side code comparisons |
| **Dual 27" 4K + 27" Portrait** | Excellent vertical space for code, two landscape for apps | Three monitors total, moderate desk space needed | AI-assisted coding (portrait for terminal/AI, landscape for code + app) |
| **34" Ultrawide + 2x 27" 4K** | Best of both worlds, massive total real estate | Expensive, very wide desk, GPU strain | BIM + AI + reference workflows (the power user layout) |

### 1.2 Resolution and Size Analysis

**27" 4K (3840x2160) -- The Developer Standard**
- 163 PPI: text is razor-sharp at 150% scaling
- At 150% scaling, effective resolution is 2560x1440 -- ample for VS Code with sidebars
- Sweet spot for price/performance ($250-$400)
- Lightweight enough for any monitor arm

**32" 4K (3840x2160)**
- 137 PPI: still sharp, but noticeably less crisp than 27" at same distance
- Better at 125% scaling for those who want more screen real estate
- Requires deeper desk or longer arm reach (optimal viewing at 28-32")
- Heavier, needs sturdier arms

**34" Ultrawide WQHD (3440x1440)**
- 110 PPI: acceptable but noticeably less sharp than 4K
- Only 1440 vertical pixels -- less vertical code visible than 4K at 150% scaling
- Seamless multi-window without bezels
- Good for side-by-side code + terminal workflows

**49" Super-Ultrawide DQHD (5120x1440)**
- Effectively two 27" QHD monitors fused together
- 1440 vertical pixel limitation is the main downside for coding
- Built-in PBP (Picture-by-Picture) mode can split into two virtual monitors
- Excellent for eliminating bezels in your primary workspace

**28" 3:2 Aspect (3840x2560) -- BenQ RD280U**
- The emerging developer-specific format
- 2560 vertical pixels gives 78% more vertical space than standard WQHD
- Purpose-built for code with specialized coding display modes
- Premium price (~$600)

### 1.3 Vertical vs. Horizontal Orientation

**Portrait (Vertical) Mode Benefits for Code:**
- A 27" monitor in portrait shows ~50% more lines of code than landscape
- Natural match for scrolling code, logs, terminal output, and AI chat
- University of California Irvine study: participants completed tasks 10% faster on vertical monitors
- Aligns with the eye's natural vertical scanning pattern

**Portrait Mode Drawbacks:**
- Screen sharing in video calls looks terrible (pillarboxed in 16:9 streams)
- Some applications render poorly in narrow-width windows
- Revit, Excel, and browser are suboptimal in portrait

**Recommendation:** Use ONE monitor in portrait for your AI terminal (Claude Code) and code reference. Keep the others landscape.

### 1.4 What Top Developers and AI Researchers Actually Use

**Scott Hanselman (Microsoft):** After 8+ years experimenting with 2 to 5 monitors, settled on **three monitors** as "the real sweet spot for productivity -- any more is overkill and any less cramps my brain." Layout: center for IDE, left for running app, right for docs/API reference.

**Zack Proser (AI Engineer, 2025):** Shifted to a single MacBook Pro with AI tools, reporting higher productivity from mental clarity over screen real estate. Argues that when AI handles context (docs, search, code generation), you need less visual space.

**Common Pattern in AI Developer Community:** The trend is splitting between two camps:
1. **Maximalists:** Triple monitor or ultrawide + side for keeping AI chat visible alongside code
2. **Minimalists:** Single high-res screen with AI tools that reduce the need for reference windows

**The emerging consensus for AI-assisted work:** You need at least two distinct visual zones -- one for your primary work and one for AI interaction. Whether that's two monitors or one ultrawide with tiling is a matter of preference.

---

## 2. Window Layout for AI-Assisted Coding

### 2.1 Where Should the AI Chat/Terminal Go?

**Option A: Dedicated Monitor (Recommended for power users)**
- Claude Code terminal on a dedicated portrait monitor
- Always visible, no context-switching cost
- Can see AI output while typing in editor
- Best for frequent AI interaction (which is the norm with Claude Code)

**Option B: VS Code Integrated Terminal (Split Pane)**
- Claude Code runs in the VS Code integrated terminal
- Code above, AI below (or side-by-side split)
- Everything in one window -- simpler but cramped on <32" monitors
- Works well on a single ultrawide

**Option C: Floating/Overlay Terminal**
- Terminal overlays on top of editor (e.g., Quake-style dropdown)
- Saves screen space but obscures code when active
- Not recommended for Claude Code, which has long-running outputs

**Recommendation:** Dedicated monitor in portrait orientation for Claude Code. The AI agent produces substantial output (code diffs, explanations, file trees) that benefits from persistent visibility.

### 2.2 Optimal Relative Positioning

```
RECOMMENDED LAYOUT: Triple Monitor (AI-Focused Development)

   [Portrait 27"]     [Landscape 27" 4K]     [Landscape 27" 4K]
   +-----------+    +-------------------+    +-------------------+
   |           |    |                   |    |                   |
   | Claude    |    |    VS Code        |    |  Browser / Docs   |
   | Code      |    |    (Primary       |    |  Revit / Excel    |
   | Terminal  |    |     Editor)       |    |  (Secondary App)  |
   |           |    |                   |    |                   |
   | Git log   |    |                   |    |                   |
   | AI output |    |                   |    |                   |
   |           |    |                   |    |                   |
   +-----------+    +-------------------+    +-------------------+
      LEFT              CENTER                   RIGHT
   (AI Zone)        (Primary Work)          (Reference/Apps)
```

**Why This Layout Works:**
- **Center monitor** is directly ahead -- your primary focus (code editor)
- **Left portrait** keeps AI visible in peripheral vision; glance left to check output
- **Right monitor** is the "context" screen -- swap between browser, Revit, Excel as needed
- Natural left-to-right flow: AI suggests -> you code -> you verify in app

### 2.3 Alternative: Ultrawide Center Layout

```
ALTERNATIVE LAYOUT: 49" Ultrawide + Side Monitor

+---------------------------------------------+    +-----------+
|                                             |    |           |
|  [Claude Code]  |  [VS Code]  | [Browser]  |    |  Revit    |
|   Terminal       |   Editor    |  Docs      |    |  (Full    |
|   1/4 width     |  1/2 width  | 1/4 width  |    |   Screen) |
|                  |             |            |    |           |
+---------------------------------------------+    +-----------+
         49" Super-Ultrawide (Center)               27" Side
```

### 2.4 Handling Reference Material

**For AI-Assisted Workflows, Reference Needs Are Changing:**
- Traditional dev: browser open for Stack Overflow, MDN, API docs
- AI-assisted dev: Claude Code handles most lookups internally
- You still need: design specs, Jira/GitHub issues, review PRs, Revit models

**Practical Approach:**
1. Dedicate ONE zone to "reference" that you swap between browser/Excel/Revit
2. Use browser tabs heavily rather than multiple browser windows
3. Let the AI terminal be your "documentation" -- ask Claude Code instead of googling
4. Keep a browser pinned for things AI cannot access (internal tools, authenticated pages)

### 2.5 Tiling vs. Manual Arrangement

**For multi-monitor setups with dedicated zones, tiling is essential.** Manual arrangement wastes time every time you reboot or disconnect a monitor.

Use **PowerToys FancyZones** at minimum (see Section 5 for full comparison). Define zones per monitor and save layouts.

---

## 3. Specific Layouts for AI + BIM Workflows

### 3.1 Revit's Screen Real Estate Needs

Revit is one of the most monitor-hungry applications:
- **3D View:** Needs maximum area for model navigation
- **Properties Panel:** Docked right, ~300px wide
- **Project Browser:** Docked left, ~250px wide
- **Ribbon:** Consumes ~120px of vertical space at the top
- **View tabs:** Multiple views open simultaneously (plans, sections, 3D, schedules)

Since Revit 2019, you can drag views to separate monitors. This is a game-changer:
- Keep **floor plans** on one monitor
- Keep **3D views and sections** on another
- Drag the **Properties and Project Browser** panels to a secondary screen

### 3.2 Recommended BIM + AI Layout

```
LAYOUT: BIM-Focused AI Workflow (Triple Monitor)

   [Portrait 27"]     [Landscape 27" 4K]     [Landscape 27" 4K]
   +-----------+    +-------------------+    +-------------------+
   |           |    |                   |    |                   |
   | Claude    |    |    Revit          |    |  Revit 3D View    |
   | Code      |    |    (Main View    |    |  OR               |
   | Terminal  |    |     + Ribbon)     |    |  Excel Dashboard  |
   |           |    |                   |    |  OR               |
   | Properties|    |                   |    |  Browser/Specs    |
   | Panel     |    |                   |    |                   |
   | (Revit)   |    |                   |    |                   |
   +-----------+    +-------------------+    +-------------------+
      LEFT              CENTER                   RIGHT
```

**BIM-Specific Tips:**
- **Revit main canvas** on the center monitor (largest unobstructed area)
- **Detach the Properties panel and Project Browser** to the left portrait monitor, below the AI terminal
- **3D perspective view** on the right monitor for real-time visual feedback
- When switching to schedule/Excel work, right monitor becomes the data screen
- AI terminal stays visible for Revit API questions, Dynamo scripting, or general queries

### 3.3 Keeping AI Visible During BIM Work

The challenge: Revit demands full attention on its canvas, but you also want AI agent visibility for:
- Asking questions about Revit API/Dynamo
- Having the AI generate family parameters or schedule formulas
- Reviewing AI-generated code for Revit plugins

**Solutions:**
1. **Portrait monitor for AI** (recommended) -- always visible, never covered by Revit
2. **Revit on ultrawide, AI in side split** -- works but reduces Revit canvas
3. **Hotkey toggle** -- use a FancyZones shortcut to quickly show/hide AI terminal overlay (worst option; breaks flow)

### 3.4 Excel Alongside Revit

Common scenario: comparing Revit schedules with Excel budget spreadsheets.

```
LAYOUT: Revit + Excel Side-by-Side

   [Portrait 27"]     [Landscape 27" 4K]     [Landscape 27" 4K]
   +-----------+    +-------------------+    +-------------------+
   |           |    |                   |    |                   |
   | Claude    |    |    Revit          |    |  Excel            |
   | Code      |    |    (Plan View)    |    |  (Budget Sheet    |
   |           |    |                   |    |   or Schedule     |
   | Revit     |    |                   |    |   Comparison)     |
   | Project   |    |                   |    |                   |
   | Browser   |    |                   |    |                   |
   +-----------+    +-------------------+    +-------------------+
```

This lets you cross-reference Revit model data with Excel calculations while the AI agent remains available for questions about either application.

---

## 4. Ergonomics and Productivity Research

### 4.1 Multi-Monitor Productivity Studies

| Study / Source | Finding |
|---|---|
| **Jon Peddie Research** | Multi-monitor users are up to 42% more productive |
| **University of Utah (NEC-sponsored)** | Dual monitors: tasks completed 44% faster for text editing, 29% faster for spreadsheet work |
| **Wichita State University** | Triple monitors improved task speed by 35.5% over single monitors |
| **Darrell Norton research** | Developers produced 10% more lines of code daily and had 26% fewer defects with multiple monitors |
| **Microsoft Research** | Large display space reduces time for tasks requiring multiple windows; users preferred configurations with more space |
| **Journal of Usability Studies** | Moderate evidence that multiple monitors increase task efficiency with decreased desktop interaction |

**Key Insight:** The productivity gain is real but comes with diminishing returns. The jump from 1 to 2 monitors is dramatic (~30-40%). The jump from 2 to 3 is meaningful (~10-15%). Beyond 3, gains are marginal and may cause cognitive overload.

### 4.2 Eye Strain Considerations

**Risk Factors with 3+ Monitors:**
- **Lateral eye movement:** Side monitors beyond 35 degrees from center cause increased eye fatigue
- **Brightness mismatch:** If monitors have different brightness/color temperature, eyes constantly readjust
- **Blue light exposure:** More screen surface = more total blue light
- **Focus distance variation:** If monitors are at different depths, eyes constantly refocus

**Mitigation Strategies:**
1. **Match all monitors** -- same brand/model if possible, or at minimum same resolution and brightness
2. **Calibrate color temperature** -- use Windows Night Light or f.lux across all monitors, set to same warmth
3. **20-20-20 rule** -- every 20 minutes, look at something 20 feet away for 20 seconds
4. **Ambient lighting** -- never work in a dark room with bright monitors; use bias lighting behind monitors
5. **Consider monitor light bars** (e.g., BenQ ScreenBar) to reduce contrast between screen and surroundings

### 4.3 Optimal Viewing Distances and Angles

**Distance Guidelines:**

| Monitor Size | Optimal Distance |
|---|---|
| 24" | 20-26 inches (50-65 cm) |
| 27" | 24-30 inches (60-75 cm) |
| 32" | 28-35 inches (70-90 cm) |
| 34" Ultrawide | 28-35 inches (70-90 cm) |
| 49" Super-Ultrawide | 32-40 inches (80-100 cm) |

**Angle Guidelines:**
- **Vertical:** Top of center monitor should be at or slightly below eye level (4-8 cm below for large monitors)
- **Horizontal:** Side monitors angled 30-35 degrees inward, creating a wrap-around arc
- **Tilt:** Slight backward tilt of 10-20 degrees reduces glare and aligns with downward gaze
- **Primary viewing zone:** Keep most-used content within 30 degrees of center to minimize neck rotation

**Triple Monitor Positioning:**
- Center monitor: directly ahead, perpendicular to line of sight
- Side monitors: angled inward at 30 degrees
- All three at identical height
- Side monitors slightly further back to maintain consistent focal distance
- The arc should feel like sitting inside a gentle curve, not a flat wall

### 4.4 Monitor Arm Recommendations

**Premium: Ergotron**
- **Ergotron LX (single):** $130-$180. Gold standard for single monitor arms. Supports up to 34" / 25 lbs. 10-year cycle tested.
- **Ergotron HX (heavy-duty single):** $230-$280. For 32"-49" monitors up to 42 lbs. Required for ultrawide monitors.
- **Ergotron LX Triple Arm:** $350-$450. Three monitors up to 40" / 14 lbs each. Single pole mount.
- **Ergotron HX + Triple Bow Kit:** $500-$600. For three heavier monitors. Most robust option.

**Mid-Range: Mount-It! / Humanscale**
- **Mount-It! MI-2753:** $80-$100. Solid triple monitor arm for monitors up to 27" / 17.6 lbs each.
- **Humanscale M8.1:** $300-$400. Premium feel, excellent cable management.

**Budget: Amazon Basics / VIVO**
- **Amazon Basics Single Monitor Arm:** $30-$40. Gets the job done for lighter monitors.
- **VIVO Triple Monitor Stand (V003T):** $45-$60. Freestanding, no clamp needed. Good for desks that cannot be clamped.

**Desk Requirements:**
- Minimum desk depth: 30 inches (deeper is better for pushing monitors back)
- Desk edge must be 1-3 inches thick for C-clamp arms
- Grommet mount preferred for stability with triple arms
- Ensure desk surface can handle the weight and torque

---

## 5. Software Tools for Window Management

### 5.1 Comparison Matrix

| Tool | Price | Multi-Monitor | Custom Zones | Hotkeys | Auto-Tiling | Best For |
|---|---|---|---|---|---|---|
| **PowerToys FancyZones** | Free | Yes | Yes | Yes | No (manual snap) | Most Windows users |
| **GlazeWM** | Free | Yes | Config-based | Yes (i3-style) | Yes (automatic) | Linux converts, keyboard purists |
| **Komorebi** | Free | Yes | Config-based | Yes (via whkd) | Yes (automatic) | Advanced users wanting modular setup |
| **DisplayFusion** | $29 | Yes | Yes | Yes | No | Multi-monitor customization |
| **AquaSnap** | Free / $18 Pro | Yes (Pro) | Yes | Yes | No | Lightweight snapping enhancement |
| **Divvy** | $14 | Yes | Grid-based | Yes | No | Quick grid-based resizing |

### 5.2 PowerToys FancyZones (Recommended Starting Point)

**Why FancyZones for This Workflow:**
- Free and maintained by Microsoft
- Define different zone layouts per monitor
- Save templates: one for "AI Coding" mode, another for "BIM" mode, another for "Review" mode
- Drag windows into zones by holding Shift while dragging
- Keyboard shortcuts to move windows between zones

**Suggested FancyZones Configuration:**
```
Monitor 1 (Portrait - Left):
  Zone 1: Top 60% - Claude Code terminal
  Zone 2: Bottom 40% - Revit Properties / Git GUI

Monitor 2 (Landscape Center):
  Zone 1: Full screen - VS Code or Revit (single zone, app gets full monitor)

Monitor 3 (Landscape Right):
  Zone 1: Top 50% - Browser
  Zone 2: Bottom 50% - Excel / secondary app
  -- OR --
  Zone 1: Full screen - Revit 3D View
```

### 5.3 GlazeWM (For Power Users Who Want Automatic Tiling)

GlazeWM is inspired by i3wm (the popular Linux tiling window manager) and provides:
- Automatic window tiling -- new windows split the current space
- Workspaces (virtual desktops) per monitor
- YAML configuration at `%userprofile%\.glzr\glazewm\config.yaml`
- Companion status bar (Zebar) with system info
- Keyboard-first workflow -- rarely touch the mouse for window management

**Why Consider GlazeWM Over FancyZones:**
- If you open/close many windows frequently, automatic tiling saves time
- Workspaces let you have different "modes" (coding, BIM, review) on each monitor
- i3-like keybindings are muscle memory for anyone who has used Linux tiling WMs

**Installation:** `winget install glzr-io.glazewm`

### 5.4 DisplayFusion (For Multi-Monitor Customization Beyond Window Tiling)

DisplayFusion goes beyond window tiling:
- **Taskbar per monitor** with independent window lists
- **Monitor profiles** -- save and restore monitor arrangements for docking/undocking
- **Wallpaper management** per monitor
- **Window snapping** with customizable grid
- **Triggers and scripting** -- automate window placement based on application launch

Best if you frequently change monitor configurations (e.g., laptop docking) or want per-monitor taskbars.

### 5.5 What the AI Coding Community Actually Uses

Based on forum discussions, developer blogs, and Reddit threads:

1. **Most common:** PowerToys FancyZones + manual arrangement (80% of Windows developers)
2. **Growing fast:** GlazeWM among developers coming from Linux or wanting more automation
3. **VS Code users:** Many rely on VS Code's built-in terminal split and panel system, supplemented by FancyZones for non-VS Code windows
4. **Claude Code / AI terminal users:** Prefer a dedicated monitor or half-screen for the AI terminal, with hotkeys to quickly resize/reposition

### 5.6 Custom Hotkey Recommendations

Set these up in FancyZones or GlazeWM:

| Hotkey | Action | Purpose |
|---|---|---|
| `Win+1` | Move window to Monitor 1 (Portrait/AI) | Quick-send to AI zone |
| `Win+2` | Move window to Monitor 2 (Center) | Send to primary workspace |
| `Win+3` | Move window to Monitor 3 (Right) | Send to reference zone |
| `Win+Shift+Enter` | Toggle current window fullscreen | Maximize Revit or VS Code |
| `Win+H` | Tile left half of current monitor | Side-by-side split |
| `Win+L` | Tile right half of current monitor | Side-by-side split |
| `Ctrl+Alt+T` | Launch/focus terminal | Quick access to Claude Code |

---

## 6. Recommended Configurations with Pricing

### 6.1 Budget Configuration ($500-$1,000)

**The "Smart Dual + Portrait" Setup**

| Component | Model | Price (est.) |
|---|---|---|
| Center Monitor | Dell S2722QC 27" 4K USB-C | $280 |
| Side Monitor (Portrait) | LG 27UP600-W 27" 4K IPS | $250 |
| Monitor Arms (2x) | Amazon Basics Single Arm (x2) | $70 |
| Window Manager | PowerToys FancyZones | Free |
| **Total** | | **~$600** |

**Layout:**
- Center 27" 4K landscape: VS Code / Revit
- Left 27" 4K portrait: Claude Code terminal + reference
- Window management: FancyZones with saved zones

**Pros:** Excellent pixel density on both screens, portrait mode for AI terminal, affordable.
**Cons:** Only two monitors -- must switch apps on the center screen between VS Code and Revit.

### 6.2 Mid-Range Configuration ($1,000-$2,000)

**The "Triple 27" 4K" Setup (Recommended)**

| Component | Model | Price (est.) |
|---|---|---|
| Center Monitor | Dell UltraSharp U2723QE 27" 4K | $380 |
| Left Monitor (Portrait) | Dell UltraSharp U2723QE 27" 4K | $380 |
| Right Monitor | Dell UltraSharp U2723QE 27" 4K | $380 |
| Monitor Arm | Ergotron LX Triple Monitor Arm | $400 |
| Window Manager | PowerToys FancyZones + GlazeWM | Free |
| **Total** | | **~$1,540** |

**Why Matching Dell UltraSharps:**
- Identical color/brightness across all three (no eye strain from mismatch)
- USB-C daisy-chaining reduces cable clutter
- IPS Black panels have excellent contrast for code readability
- Factory-calibrated color accuracy (Delta E < 2)
- Excellent build quality and adjustable stand (as backup to arms)

**Layout:**
- Left 27" portrait: Claude Code + Revit Properties panel
- Center 27" landscape: VS Code or Revit main canvas
- Right 27" landscape: Browser, Excel, Revit 3D view

**Alternative Mid-Range: Ultrawide + Side**

| Component | Model | Price (est.) |
|---|---|---|
| Center Monitor | Gigabyte G34WQC2 34" WQHD 144Hz | $350 |
| Side Monitor | Dell S2722QC 27" 4K | $280 |
| Monitor Arms | Ergotron HX (ultrawide) + LX (27") | $410 |
| **Total** | | **~$1,040** |

### 6.3 Ideal Configuration ($2,000-$3,000)

**The "BIM Power Station" Setup**

| Component | Model | Price (est.) |
|---|---|---|
| Center Monitor | Dell UltraSharp U3223QE 32" 4K | $520 |
| Left Monitor (Portrait) | BenQ RD280U 28" 3:2 (3840x2560) | $600 |
| Right Monitor | Dell UltraSharp U2723QE 27" 4K | $380 |
| Triple Monitor Arm | Ergotron HX + Triple Bow Kit | $550 |
| Monitor Light Bar | BenQ ScreenBar Halo (x2) | $220 |
| Window Manager | GlazeWM + PowerToys | Free |
| **Total** | | **~$2,270** |

**Why This Configuration:**
- **32" 4K center** gives Revit maximum canvas at readable scale (125% scaling, effective 3072x1728)
- **28" 3:2 portrait** left is purpose-built for code -- 2560 vertical pixels shows ~80 lines more than a standard 27" in portrait
- **27" 4K right** for browser, Excel, 3D views
- **BenQ ScreenBar Halo** eliminates contrast strain with ambient backlighting
- Total horizontal resolution at work: approximately 10,240 pixels of usable workspace

**Layout:**
```
   [BenQ 28" 3:2     [Dell 32" 4K         [Dell 27" 4K
    Portrait]          Landscape]            Landscape]
   +------------+   +---------------------+   +-----------------+
   |            |   |                     |   |                 |
   | Claude     |   |                     |   |  Browser        |
   | Code       |   |   Revit Main        |   |  (top half)     |
   | Terminal   |   |   Canvas            |   |                 |
   | (top 55%)  |   |   OR                |   +-----------------+
   |            |   |   VS Code           |   |  Excel          |
   +------------+   |   (Full 32")        |   |  (bottom half)  |
   | Revit      |   |                     |   |                 |
   | Props +    |   |                     |   |                 |
   | Browser    |   |                     |   |                 |
   | (bot 45%)  |   |                     |   |                 |
   +------------+   +---------------------+   +-----------------+
```

### 6.4 Alternative Ideal: Super-Ultrawide Focused

| Component | Model | Price (est.) |
|---|---|---|
| Center Monitor | Samsung Odyssey OLED G9 49" DQHD | $1,300 |
| Side Monitor | Dell UltraSharp U2723QE 27" 4K (Portrait) | $380 |
| Arms | Ergotron HX (49") + Ergotron LX (27") | $410 |
| Monitor Light Bar | BenQ ScreenBar Halo | $110 |
| **Total** | | **~$2,200** |

**Caution:** OLED burn-in risk with static UI elements (VS Code sidebars, Revit ribbon). Use pixel-shift features and vary your layout. For heavy static UI use, prefer the IPS-based Dell U4924DW ($1,200) instead.

### 6.5 Specific Monitor Model Quick Reference

| Use Case | Model | Size | Resolution | Price | Notes |
|---|---|---|---|---|---|
| Budget 4K | Samsung ViewFinity S70D (LS27D700) | 27" | 4K | ~$230 | Great value |
| Mid-Range 4K | Dell UltraSharp U2723QE | 27" | 4K | ~$380 | USB-C hub, IPS Black |
| Large 4K | Dell UltraSharp U3223QE | 32" | 4K | ~$520 | Best 32" for productivity |
| Developer Special | BenQ RD280U | 28" | 3840x2560 (3:2) | ~$600 | Built for code |
| Budget Ultrawide | Gigabyte G34WQC2 | 34" | 3440x1440 | ~$350 | Good value VA panel |
| Premium Ultrawide | Alienware AW3423DWF | 34" | 3440x1440 | ~$800 | QD-OLED, stunning |
| Super-Ultrawide | Dell U4924DW | 49" | 5120x1440 | ~$1,200 | IPS Black, no burn-in |
| Super-UW OLED | Samsung Odyssey OLED G9 | 49" | 5120x1440 | ~$1,300 | Best image quality |

---

## 7. Final Recommendation

### For Your Specific Workflow (Claude Code + VS Code + Revit + Excel + Browser)

**Best Overall: Triple 27" 4K with one in portrait ($1,500-$1,600)**

This is the optimal balance of cost, flexibility, and ergonomics for your specific application mix:

1. **Left monitor (Portrait 27" 4K):** Claude Code terminal (top 60%) + Revit Properties/Project Browser (bottom 40%). The portrait orientation gives Claude Code's verbose output the vertical space it needs.

2. **Center monitor (Landscape 27" 4K):** Your primary work surface. VS Code when coding, Revit when doing BIM work. This gets your full attention and is directly ahead.

3. **Right monitor (Landscape 27" 4K):** Context and reference. Browser (top) + Excel (bottom) when coding. Revit 3D view when doing BIM work. This is your "glance" monitor.

**Why not ultrawide for center?** Revit benefits from maximum vertical pixels for its ribbon-heavy UI. A 27" 4K at 150% scaling gives you 1440 effective vertical pixels, same as an ultrawide's native 1440, but with sharper text. A 32" 4K at 125% gives you even more (1728 effective vertical) -- upgrade the center to 32" if budget allows.

**Why not a super-ultrawide?** The 1440 vertical pixel limitation hurts both VS Code and Revit. You lose the ability to put one monitor in portrait for AI output. And the cost of a good 49" equals two 27" 4K monitors.

**Why portrait for AI?** Claude Code outputs long code blocks, diffs, file trees, and explanations. Vertical space is more valuable than horizontal width for terminal output. A 27" 4K in portrait gives you roughly 3840 pixels of vertical space (scaled to ~2560 effective) -- enough to see an entire function's diff without scrolling.

### Essential Software Stack

1. **PowerToys FancyZones** -- define your zones, save per-monitor layouts
2. **GlazeWM** (optional upgrade) -- if you want automatic tiling and workspaces
3. **Windows Terminal** with profiles for Claude Code, Git, and system shells
4. **f.lux or Windows Night Light** -- consistent color temperature across all monitors
5. **BenQ ScreenBar or similar** -- reduce eye strain from brightness contrast

### The One Change That Makes the Biggest Difference

If you currently use dual monitors in landscape, **rotate one to portrait and dedicate it to your AI terminal.** This single change:
- Eliminates the biggest friction in AI-assisted coding (alt-tabbing to see AI output)
- Gives you 50% more visible lines of AI output
- Creates a clear mental separation between "AI zone" and "work zone"
- Costs $0 if your current monitor supports VESA rotation

---

## Sources

- [Plugable: Productivity Impact of Multiple Monitors](https://plugable.com/blogs/news/productivity-impact-of-multiple-monitors)
- [Arzopa: Maximizing Code Efficiency with Triple Monitor Setup](https://www.arzopa.com/blogs/guide/3-monitor-setup-coding)
- [Scott Hanselman: The Sweet Spot of Multiple Monitor Productivity](https://www.hanselman.com/blog/the-sweet-spot-of-multiple-monitor-productivity-that-magical-third-monitor)
- [Zack Proser: My 2025 AI Engineer Setup](https://zackproser.com/blog/2025-ai-engineer-setup)
- [RTINGS: Best Monitors for Programming 2026](https://www.rtings.com/monitor/reviews/best/by-usage/programming-and-coding)
- [CCOHS: Office Ergonomics - Monitor Positioning](https://www.ccohs.ca/oshanswers/ergonomics/office/monitor_positioning.html)
- [OSHA: Computer Workstation Monitor Guidelines](https://www.osha.gov/etools/computer-workstations/components/monitors)
- [Eureka Ergonomic: 3-Monitor Desk Ergonomics](https://eurekaergonomic.com/blogs/eureka-ergonomic-blog/3-monitor-desk-ergonomics-creators)
- [Eureka Ergonomic: Vertical Monitor Setup for Coders](https://eurekaergonomic.com/blogs/eureka-ergonomic-blog/vertical-monitor-setup-coders)
- [Arzopa: Portrait Mode Monitors for Developers](https://www.arzopa.com/blogs/guide/portrait-mode-monitors-for-developers)
- [BenQ: Vertical Monitor for Coding](https://www.benq.com/en-us/knowledge-center/knowledge/portrait-mode-monitors-for-developers.html)
- [ScienceDirect: Workstation Ergonomics in Multi-Monitor Era](https://www.sciencedirect.com/science/article/abs/pii/S0169814125001696)
- [PubMed: Multiple Computer Monitors and User Experience](https://pubmed.ncbi.nlm.nih.gov/31809202/)
- [Microsoft Research: Productivity Benefits of Large Displays](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/interact2003-productivitylargedisplays.pdf)
- [Herman Miller: Effects of Multiple Monitor Arms](https://www.hermanmiller.com/research/categories/white-papers/seeing-double-the-effects-of-multiple-monitor-arms/)
- [Microsoft: PowerToys FancyZones](https://learn.microsoft.com/en-us/windows/powertoys/fancyzones)
- [GlazeWM: Tiling Window Manager for Windows](https://glazewm.com/)
- [GitHub: Komorebi Tiling Window Manager](https://github.com/LGUG2Z/komorebi)
- [Autodesk: Display Revit Model Views on Dual Monitors](https://knowledge.autodesk.com/support/revit-products/learn-explore/caas/sfdcarticles/sfdcarticles/Display-Revit-model-views-on-dual-monitors.html)
- [Autodesk Community: Dual Monitor Setup for Revit](https://forums.autodesk.com/t5/revit-architecture-forum/dual-monitor-setup-for-revit/td-p/3290495)
- [Revit Forum: Preferred Monitor Setup Discussion](https://www.revitforum.org/forum/revit-architecture-forum-rac/architecture-and-general-revit-questions/45426-what-s-your-preferred-monitor-setup)
- [Ergotron: LX Triple Monitor Arm](https://www.ergotron.com/en-us/products/product-details/lx-pro-desk-triple-monitor-arm)
- [Ergotron: HX Triple Monitor Arm](https://www.ergotron.com/en-us/products/product-details/hxdesktriplemonitorarm)
- [PCWorld: Best 4K Monitors 2026](https://www.pcworld.com/article/813361/best-4k-monitors.html)
- [PCWorld: Best Ultrawide Monitors 2026](https://www.pcworld.com/article/1470449/best-ultrawide-monitors.html)
- [PCWorld: Dell UltraSharp U4924DW Review](https://www.pcworld.com/article/1813208/dell-ultrasharp-u4924dw-review.html)
- [XDA Developers: Window Managers for Windows](https://www.xda-developers.com/window-managers-make-multitasking-easier-windows/)
- [Windows Forum: Tiling Window Managers for Power Users](https://windowsforum.com/threads/windows-tiling-window-managers-four-standout-options-for-power-users.380077/)

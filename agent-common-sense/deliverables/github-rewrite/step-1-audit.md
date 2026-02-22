# GitHub Documentation Audit Report

**Date:** 2026-02-21
**Auditor:** Claude Opus 4.6
**Repos Audited:** 2

---

## Executive Summary

Both repositories have significant documentation gaps that undermine their public perception relative to their actual engineering quality.

**Autonomy Engine (agent-common-sense)** is the worse case: a sophisticated system with 18,748 lines of Python, 663 tests, 8 domain correction packs, and a novel architecture -- with zero public-facing documentation. No README. No LICENSE. No CONTRIBUTING. No CHANGELOG. A visitor landing on this repo sees raw Python files and leaves. The code speaks for itself internally (good docstrings, clear module headers), but no one will read that far without a README pulling them in.

**RevitMCPBridge2026** is the opposite problem: documentation exists and is functional, but it reads like internal project notes rather than a public open-source showcase. The README is a flat feature list without emotional hook, visual proof, or competitive positioning. It undersells what is genuinely the first open-source AI-to-Revit bridge -- a category-defining project -- by presenting it like a utility library. The 705 endpoints, 113 knowledge files, and 5 autonomy levels deserve a README that makes someone stop scrolling.

**Bottom line:** Both repos are undervalued by their GitHub presentations. The code quality is 8-9/10. The documentation quality is 1/10 (Autonomy Engine) and 5/10 (RevitMCPBridge2026).

---

## Repo 1: Autonomy Engine (agent-common-sense)

**GitHub:** https://github.com/WeberG619/claude-ai-tools (submodule)
**Location:** `/mnt/d/_CLAUDE-TOOLS/agent-common-sense/`

### Inventory of What Exists

| Asset | Status |
|-------|--------|
| README.md | Does not exist |
| LICENSE | Does not exist |
| CONTRIBUTING.md | Does not exist |
| CHANGELOG.md | Does not exist |
| .gitignore | Not verified |
| Python modules | 22 modules (18,748 LOC) |
| Test files | 11 files (6,690 LOC, 663 tests) |
| Kernel docs | 3 markdown files (467 LOC) |
| Domain packs | 8 JSON files in domains/ |
| REST API | api.py with 12 endpoints |
| CLI interfaces | goals.py, planner.py, alignment.py, coordinator.py, inject.py, domains.py, sense.py |

### Audit Ratings

| # | Dimension | Rating | Notes |
|---|-----------|--------|-------|
| 1 | Value Proposition | **Missing** | No README exists. A visitor cannot determine what this project does without reading source code. |
| 2 | One-Line Hook | **Missing** | No tagline anywhere. The closest is the docstring in sense.py: "Gives any agent experiential judgment through accumulated corrections." That is buried in source. |
| 3 | Problem Statement | **Missing** | The "why" is completely absent. Why do agents need common sense? What goes wrong without it? No framing. |
| 4 | Architecture Overview | **Missing** | The system has 5 distinct subsystems (sense engine, goal engine, planner, alignment core, coordinator) that interact in non-obvious ways. No diagram. No explanation. The CLAUDE.md reference file hints at the architecture but is a private config file, not public docs. |
| 5 | Installation / Quick Start | **Missing** | No instructions for pip install, dependency list, or "hello world" example. The module docstrings have usage examples, but they are scattered across 7 files. |
| 6 | Demo / Examples | **Missing** | No standalone examples. The docstrings in goals.py, planner.py, alignment.py, and coordinator.py each contain usage snippets, but these are not consolidated or runnable. |
| 7 | Architecture Diagram | **Missing** | Nothing. This is a system that badly needs one -- the decision loop, verify loop, learning loop, and how they connect to goals/plans/alignment/coordination. |
| 8 | Stats / Social Proof | **Missing** | 663 tests, 8 domain packs, 22 modules -- none of this is surfaced. |
| 9 | Badges | **Missing** | No badges of any kind. |
| 10 | Screenshots / GIFs | **Missing** | No visual evidence. A before/after of an agent with and without common sense would be compelling. |
| 11 | Before / After | **Missing** | This is the single highest-impact missing element. The entire value proposition is "agents make fewer mistakes." Show it. |
| 12 | Contributing Guide | **Missing** | No guidance for contributors. |
| 13 | License | **Missing** | No LICENSE file. This means the code is technically "all rights reserved" by default, which contradicts being on a public GitHub. |
| 14 | Professional Polish | **Missing** | Zero polish. Raw files in a directory. No project metadata, no pyproject.toml, no setup.py. |
| 15 | Cross-linking | **Missing** | No references to RevitMCPBridge2026 or any other project that uses this engine. |

### Specific Gaps

**1. No README.md**
This is the single most damaging gap. GitHub repos without READMEs get closed immediately by visitors. The repo has 22 Python modules with excellent inline docstrings, but none of that is visible on the landing page.

**2. No LICENSE file**
Without a license, no one can legally use, fork, or contribute to this code. This must be fixed before any other documentation work.

**3. The kernel.md is internal, not public-facing**
The kernel.md file is the intellectual core of the project -- the Decision Loop, Verify Loop, and Learning Loop are genuinely novel. But it reads as an injection prompt, not as documentation. It needs a public-facing explanation of what these loops do and why they matter.

**4. No pyproject.toml or setup.py**
The project cannot be installed via pip. There is no dependency declaration. The `api.py` imports FastAPI/uvicorn but these are not listed anywhere.

**5. The REST API is undocumented publicly**
api.py has 12 endpoints. This should be documented in a way that someone could stand up the server and integrate it into their own agent framework.

**6. Domain packs are invisible**
The 8 domain correction packs (data, deployment, execution, filesystem, git, identity, network, scope) are a key differentiator. They represent curated experiential knowledge. No one knows they exist.

**7. No test coverage reporting**
663 tests across 11 files is strong. But there is no CI, no badge, no way for a visitor to know the tests pass.

---

## Repo 2: RevitMCPBridge2026

**GitHub:** https://github.com/WeberG619/RevitMCPBridge2026
**Location:** `/mnt/d/RevitMCPBridge2026/`

### Inventory of What Exists

| Asset | Status |
|-------|--------|
| README.md | Exists (318 lines) |
| LICENSE | Exists (MIT) |
| CONTRIBUTING.md | Exists (54 lines) |
| CHANGELOG.md | Exists (98 lines) |
| CLAUDE.md | Exists (internal config) |
| Architecture doc | docs/ARCHITECTURE.md |
| API reference | docs/api/METHODS.md (859 lines) |
| Quick start | docs/QUICKSTART.md |
| Usage guide | docs/guides/USAGE_GUIDE.md |
| Example scripts | 3 Python scripts in docs/examples/ |
| Workflow templates | 5 JSON files in docs/workflows/ |
| Knowledge base | 113 files in knowledge/ |
| C# source | 146 files (179,933 LOC) |
| Unit tests | 68 tests with NUnit |
| Screenshots | 20+ PNG files in root (renders, views) |
| Guide docs | 15+ guide files in docs/guides/ |

### Audit Ratings

| # | Dimension | Rating | Notes |
|---|-----------|--------|-------|
| 1 | Value Proposition | **Weak** | The first line is "A Revit 2026 Add-in that exposes the Revit API through the Model Context Protocol (MCP), enabling AI-assisted automation of Revit tasks." This is accurate but not compelling. It describes the mechanism, not the value. Compare: "Talk to Revit in plain English. Create walls, place doors, generate sheets -- all through natural language." |
| 2 | One-Line Hook | **Weak** | No dedicated tagline. The repo title is just the project name. No subtitle or description on GitHub. |
| 3 | Problem Statement | **Missing** | Nowhere does the README explain what problem this solves. Why do architects need AI in Revit? What is painful about the current workflow? What does this enable that was impossible before? |
| 4 | Architecture Overview | **Adequate** | docs/ARCHITECTURE.md exists with an ASCII diagram. The README has a project structure tree. The named pipe architecture is mentioned. However, the architecture doc still says "437+ methods" (outdated; it is 705+), and the diagram does not show the autonomy levels or knowledge base integration. |
| 5 | Installation / Quick Start | **Adequate** | Both automated (PowerShell script) and manual installation are documented. A Python verification script is included. The prereqs are listed. However, the verification example uses socket connection (port 8765) which conflicts with the named pipe architecture described elsewhere -- this is confusing and likely a legacy artifact. |
| 6 | Demo / Examples | **Weak** | Three example scripts exist in docs/examples/ but the README only shows system method calls (getVersion, healthCheck). No example of the compelling use case: "create a wall," "place a door," "generate a sheet set." The README shows the boring parts and hides the exciting parts. |
| 7 | Architecture Diagram | **Weak** | ASCII art exists in ARCHITECTURE.md but it is not in the README. No visual diagram (PNG/SVG). For a visual profession (architecture), the documentation is entirely text-based. |
| 8 | Stats / Social Proof | **Weak** | The numbers are mentioned (705+ methods, 113 knowledge files, 68 tests) but presented as a flat bullet list. They do not land with impact. No comparison to alternatives. No "this is the first..." framing despite it literally being the first open-source AI-to-Revit bridge. |
| 9 | Badges | **Missing** | No badges at all. No build status, no version badge, no license badge, no language badge. |
| 10 | Screenshots / GIFs | **Missing** | There are 20+ PNG files in the repo root (renders, building views, floor plans) but NONE are referenced in the README. The most powerful proof -- visual output from AI-controlled Revit -- is sitting in the repo unused. This is the single biggest missed opportunity. |
| 11 | Before / After | **Missing** | No before/after comparison. A side-by-side of "manual Revit workflow" vs "AI-assisted workflow" would be extremely compelling for the target audience. |
| 12 | Contributing Guide | **Adequate** | CONTRIBUTING.md exists with fork/PR workflow, code style notes, and testing instructions. It is thin but functional. |
| 13 | License | **Strong** | MIT License, clearly attributed, linked from README. |
| 14 | Professional Polish | **Weak** | The README is functional but has no visual hierarchy. No logo, no banner, no badges. The table formatting is basic. The "Acknowledgments" section buries the most important claim ("first open-source bridge connecting Claude AI to Autodesk Revit") at the very bottom where no one reads. |
| 15 | Cross-linking | **Missing** | No reference to the Autonomy Engine. No reference to the broader BIM Ops Studio ecosystem. No link to blog posts, demos, or presentations. |

### Specific Gaps

**1. The hook is buried**
The statement "This project represents the first open-source bridge connecting Claude AI to Autodesk Revit" is in the Acknowledgments section at line 310. It should be the first thing anyone reads. This is a category-defining claim.

**2. No screenshots in README**
The repo contains rendering outputs (building_render_v2.png, building_render_v3.png), captured views, and floor plan extractions. None are in the README. For a tool that controls a visual application (Revit), showing visual output is essential.

**3. Verification example uses wrong protocol**
The "Verify Installation" section shows a socket connection to localhost:8765. The actual architecture uses named pipes (`\\.\pipe\RevitMCPBridge2026`). This is confusing and suggests the docs were not updated after the protocol change.

**4. Autonomy levels are underexplained**
The 5 autonomy levels are a major differentiator. The README gives them each one sentence. Level 5 (Full Autonomy with self-healing) is a significant capability that deserves a compelling example showing input -> AI reasoning -> Revit output.

**5. Knowledge base is invisible**
113 domain knowledge files covering building codes, construction types, MEP systems, accessibility -- this is a massive asset. The README mentions it once as a bullet point. No visitor understands the depth of this.

**6. No competitive positioning**
There are other Revit automation tools (pyRevit, Dynamo, Rhino.Inside). The README does not explain how this is different. The MCP protocol, natural language interface, and autonomy levels are the differentiators, but they are not positioned against alternatives.

**7. API categories table is dry**
The API categories table lists method counts but gives no sense of what you can actually do. "Walls: 11 methods" means nothing. "Create, modify, join, split, query walls by type, location, or intersection" tells a story.

**8. Inconsistency: method count**
README says 705+. ARCHITECTURE.md says 437+. CHANGELOG says 443+. The CLAUDE.md says 705. Pick one number and update everything.

**9. Root directory clutter**
20+ PNG files, 50+ PowerShell test scripts, and various temp files are in the root directory. This makes the repo look messy on GitHub. These should be in subdirectories or .gitignored.

---

## Comparative Analysis: What Top Open Source Projects Do

### Projects studied for comparison:
- **LangChain** (130k+ stars): Problem statement in first paragraph, architecture diagram, badges, GIF demos, extensive examples
- **FastAPI** (80k+ stars): One-line hook ("high performance, easy to learn"), performance benchmarks, side-by-side code comparisons
- **Ollama** (120k+ stars): Clean install command, immediate "try it" example, model library showcase
- **Home Assistant** (75k+ stars): Screenshot-heavy, "what you can do" framing, integration count as social proof
- **pyRevit** (3k+ stars): Revit-specific, animated GIFs of features, installation wizard, clear "what is this" section

### What they all share that these repos lack:

| Element | Industry Standard | Autonomy Engine | RevitMCPBridge |
|---------|-------------------|-----------------|----------------|
| Hero section with hook | Yes | No | No |
| Problem framing | Yes | No | No |
| Visual proof (screenshot/GIF) | Yes | No | No (despite having assets) |
| Badges row | Yes | No | No |
| "Get started in 30 seconds" | Yes | No | Partial |
| Before/after or comparison | Common | No | No |
| Architecture diagram in README | Common | No | No (exists in separate file) |
| Stats as social proof | Common | No | Weak |
| Logo or banner image | Very common | No | No |
| Cross-project links | Common | No | No |

---

## Priority-Ranked Action Items

### Tier 1: Critical (do first)

| # | Repo | Action | Impact |
|---|------|--------|--------|
| 1 | Autonomy Engine | Create README.md | Without this, the repo is invisible. |
| 2 | Autonomy Engine | Add LICENSE file (MIT) | Without this, the repo is legally unusable. |
| 3 | RevitMCPBridge | Rewrite README hero section | The first 10 lines determine if someone reads further. |
| 4 | RevitMCPBridge | Add screenshots to README | Visual proof for a visual tool. Use existing render PNGs. |
| 5 | RevitMCPBridge | Fix verification example (socket vs named pipe) | Current example is misleading/broken. |

### Tier 2: High Impact (do second)

| # | Repo | Action | Impact |
|---|------|--------|--------|
| 6 | Autonomy Engine | Write architecture overview with diagram | The 5-subsystem design is the technical differentiator. |
| 7 | Autonomy Engine | Add quick start with pip install | Adoption requires frictionless onboarding. |
| 8 | RevitMCPBridge | Add problem statement section | "Why does this exist?" must be answered. |
| 9 | RevitMCPBridge | Move "first open-source bridge" claim to top | The most important positioning is buried at bottom. |
| 10 | RevitMCPBridge | Expand autonomy levels with examples | The 5-level system is unique. Show input/output for each. |
| 11 | Both | Add badges (license, language, tests, version) | Instant visual credibility signal. |

### Tier 3: Polish (do third)

| # | Repo | Action | Impact |
|---|------|--------|--------|
| 12 | Autonomy Engine | Add CONTRIBUTING.md | Enable community participation. |
| 13 | Autonomy Engine | Add CHANGELOG.md | Show project velocity. |
| 14 | Autonomy Engine | Create pyproject.toml | Make the project installable. |
| 15 | RevitMCPBridge | Create before/after comparison | Show the workflow improvement. |
| 16 | RevitMCPBridge | Normalize method count across all docs | Consistency = credibility. |
| 17 | RevitMCPBridge | Clean up root directory | Move PNGs and temp scripts to subdirectories. |
| 18 | Both | Cross-link repos | Each project validates the other. |
| 19 | RevitMCPBridge | Competitive positioning section | Explain why MCP vs Dynamo vs pyRevit. |
| 20 | Autonomy Engine | Document REST API publicly | 12 endpoints need a public reference. |

---

## Summary Scores

| Dimension | Autonomy Engine | RevitMCPBridge |
|-----------|----------------|----------------|
| Value Proposition | 0/10 | 4/10 |
| One-Line Hook | 0/10 | 3/10 |
| Problem Statement | 0/10 | 1/10 |
| Architecture Overview | 0/10 | 6/10 |
| Installation / Quick Start | 0/10 | 6/10 |
| Demo / Examples | 0/10 | 4/10 |
| Architecture Diagram | 0/10 | 4/10 |
| Stats / Social Proof | 0/10 | 3/10 |
| Badges | 0/10 | 0/10 |
| Screenshots / GIFs | 0/10 | 0/10 |
| Before / After | 0/10 | 0/10 |
| Contributing Guide | 0/10 | 6/10 |
| License | 0/10 | 9/10 |
| Professional Polish | 0/10 | 4/10 |
| Cross-linking | 0/10 | 0/10 |
| **Overall** | **0/150** | **50/150** |

The code quality in both repos is genuinely strong. The documentation does not reflect this. The gap between internal quality and external perception is the core problem this rewrite must solve.

---

*Report generated 2026-02-21. Next step: Step 2 -- write the README drafts.*

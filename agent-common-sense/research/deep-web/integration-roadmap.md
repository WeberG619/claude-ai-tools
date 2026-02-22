# Deep Web Integration Roadmap: Autonomy Engine MCP Ecosystem

> **Created:** 2026-02-21
> **Author:** Weber Gouin / Claude Opus 4.6
> **Status:** Active execution plan
> **Last Updated:** 2026-02-21

---

## Executive Summary

The Autonomy Engine currently connects to Autodesk Revit via 705+ MCP endpoints (RevitMCPBridge). This roadmap maps every valuable data silo worth connecting, organized into four priority tiers. The goal: transform the agent from one that operates Revit well into one that can autonomously navigate the entire AEC data landscape -- permits, emails, documents, code repositories, building codes, cost databases, property records, and construction management platforms.

**Current state:** 1 deep integration (Revit) + ~14 utility MCP servers (Excel, Word, PowerPoint, voice, browser, etc.)
**Target state:** 25+ deep integrations spanning productivity, government data, AEC-specific platforms, and market intelligence.

**Estimated timeline to full ecosystem:** 16-20 weeks (4-5 months) for a single developer working part-time.

---

## Summary Table: All Data Sources Ranked

| Rank | Source | Tier | Value | Complexity | V/C Ratio | Est. Effort | Status |
|------|--------|------|-------|------------|-----------|-------------|--------|
| 1 | GitHub MCP (Official) | 1 | 9 | 1 | 9.0 | 30 min | Ready to connect |
| 2 | Google Workspace MCP | 1 | 10 | 3 | 3.3 | 2-3 hours | Ready to connect |
| 3 | Autodesk APS MCP Server | 1 | 9 | 3 | 3.0 | 1-2 hours | Ready to connect |
| 4 | SQLite MCP (Reference) | 1 | 7 | 1 | 7.0 | 15 min | Already available (deferred tool) |
| 5 | Filesystem MCP (Reference) | 1 | 6 | 1 | 6.0 | 15 min | Ready to connect |
| 6 | Slack MCP | 2 | 7 | 2 | 3.5 | 1-2 hours | Existing server |
| 7 | Notion MCP | 2 | 6 | 2 | 3.0 | 1-2 hours | Existing server |
| 8 | Miami-Dade ArcGIS Permits | 2 | 9 | 4 | 2.3 | 1-2 weeks | Custom build (API exists) |
| 9 | IFC/BIM MCP Server | 2 | 8 | 4 | 2.0 | 2-3 days | Existing server (ifcMCP) |
| 10 | Weather/NOAA MCP | 2 | 6 | 2 | 3.0 | 1 hour | Existing server |
| 11 | Linear MCP | 2 | 5 | 2 | 2.5 | 1 hour | Existing server |
| 12 | ICC Code Connect (Building Codes) | 3 | 10 | 6 | 1.7 | 2-3 weeks | Custom build (API exists) |
| 13 | Broward County Permits | 3 | 8 | 7 | 1.1 | 3-4 weeks | Custom build (scraping) |
| 14 | Property Appraiser (MDC) | 3 | 8 | 6 | 1.3 | 2-3 weeks | Custom build (hybrid) |
| 15 | Property Appraiser (BCPA) | 3 | 7 | 7 | 1.0 | 2-3 weeks | Custom build (scraping) |
| 16 | Contractor License (DBPR) | 3 | 7 | 4 | 1.8 | 1 week | Custom build (API exists) |
| 17 | Shovels.ai (Permit Aggregator) | 3 | 7 | 3 | 2.3 | 3-5 days | Custom build (API exists) |
| 18 | Procore MCP | 4 | 8 | 5 | 1.6 | 1-2 weeks | Existing server (Zapier/custom) |
| 19 | Autodesk Build MCP | 4 | 8 | 5 | 1.6 | 1-2 weeks | Existing server |
| 20 | RS Means / Cost Data | 4 | 9 | 8 | 1.1 | 4-6 weeks | Custom build |
| 21 | Real Estate APIs (Zillow/Redfin) | 4 | 6 | 5 | 1.2 | 2-3 weeks | Custom build |
| 22 | Manufacturer BIM Libraries | 4 | 7 | 7 | 1.0 | 4-6 weeks | Custom build |
| 23 | CoStar / Commercial RE | 4 | 7 | 8 | 0.9 | Unknown | API access unclear |
| 24 | Utility Company Data (FPL) | 4 | 5 | 8 | 0.6 | Unknown | No known API |
| 25 | Accela API (Ft. Lauderdale) | 3 | 6 | 5 | 1.2 | 1-2 weeks | Custom build (API exists) |

---

## The Correction Flywheel Advantage

Every new data silo connected to the Autonomy Engine does not just add data -- it makes the *entire system* smarter through the correction flywheel:

**How it works:**
1. Agent makes a mistake (e.g., references wrong permit number, misreads building code, uses outdated contractor info)
2. User corrects the agent
3. Correction is stored in persistent memory with domain tags
4. Next time ANY agent encounters a similar situation, the correction is surfaced via `memory_check_before_action`
5. The correction applies cross-domain: a lesson from permit research helps with property lookups

**Multiplier effect of each new silo:**
- **GitHub MCP** -- corrections about code patterns in RevitMCPBridge apply when the agent searches other repos. Lessons about PR review quality transfer across all projects.
- **Google Workspace** -- corrections about how to search Gmail effectively (date ranges, label queries) persist. Once the agent learns that "Weber uses label:PROJECT-X for project emails," it never forgets.
- **Permit databases** -- corrections about permit number formats (e.g., "Miami-Dade uses PROCNUM format, Broward uses BCS-XXXXXX") become permanent knowledge that prevents future errors.
- **Building codes** -- corrections about code interpretation (e.g., "FBC 7th Ed section 1612 was updated in 8th Ed") build institutional knowledge that no single human could maintain.
- **Cost databases** -- corrections about cost estimation approaches (e.g., "RS Means data for South Florida needs 1.05x locality factor") become reusable knowledge.

**Cross-silo intelligence examples:**
- Agent learns from Gmail that a client prefers a specific HVAC manufacturer, then references that preference when specifying in Revit
- Agent discovers a permit was denied for a particular building code violation, stores the correction, and proactively flags the same issue in future Revit models
- Agent finds a contractor's license has lapsed (DBPR lookup), cross-references with active permits (Miami-Dade ArcGIS), and flags the discrepancy

---

## Tier 1 -- Connect This Week

These are production-ready MCP servers that require only configuration, not development. Each can be connected in under 3 hours.

---

### 1.1 GitHub MCP Server (Official)

**Source:** [github/github-mcp-server](https://github.com/github/github-mcp-server) | 27.1K stars
**What data becomes accessible:**
- All private repository code, commit history, and branch structure
- Issue discussions, PR review threads, and code review feedback
- GitHub Actions workflow runs, logs, and failure analysis
- Security alerts (code scanning, secret scanning, Dependabot)
- Cross-repo code search across all WeberG619 repositories
- Notification stream (mentions, review requests, assignments)

**Integration approach:** Remote hosted server (GitHub-managed, zero maintenance)
**Estimated effort:** 30 minutes
**Value score:** 9/10 -- all RevitMCPBridge development history, code decisions, and team discussions become searchable
**Complexity score:** 1/10 -- single CLI command, reuse existing `gh` auth token
**Priority rank:** 9.0 (highest)
**Dependencies:** GitHub PAT with appropriate scopes (existing `gho_` token from `gh` CLI works)

**Setup command:**
```bash
claude mcp add-json github "{\"type\":\"http\",\"url\":\"https://api.githubcopilot.com/mcp/x/all\",\"headers\":{\"Authorization\":\"Bearer $(gh auth token)\"}}" --scope user
```

**Correction flywheel angle:** Every code review comment, every issue discussion, every commit message becomes searchable context. When the agent encounters a similar code pattern, it can reference past decisions. "We tried approach X in PR #42 and reverted it because Y" becomes available knowledge.

---

### 1.2 Google Workspace MCP Server

**Source:** [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp) | ~1,500 stars
**What data becomes accessible:**
- **Gmail:** Years of email history -- client communications, RFI chains, submittal discussions, contractor correspondence, project approvals
- **Google Drive:** Project specifications, meeting notes, proposals, contracts, design narratives, shared consultant files
- **Google Sheets:** Project trackers, issue logs, RFI logs, cost estimates, contact lists
- **Google Calendar:** Meeting history, upcoming schedule, attendee lists, meeting context
- **Google Docs:** Specifications, meeting minutes, design documents
- **Google Slides:** Presentations, client decks

**Integration approach:** Python MCP server via `uvx` (taylorwilsdon/google_workspace_mcp)
**Estimated effort:** 2-3 hours (mostly OAuth setup in Google Cloud Console)
**Value score:** 10/10 -- the single highest-value integration. Years of professional correspondence, documents, and schedules become agent-searchable
**Complexity score:** 3/10 -- well-documented, but OAuth consent screen setup is multi-step
**Priority rank:** 3.3
**Dependencies:**
1. Google Cloud Console project with APIs enabled (Gmail, Drive, Calendar, Docs, Sheets)
2. OAuth 2.0 client credentials (Desktop application type)
3. Publish OAuth app to Production to avoid 7-day token expiry
4. Python 3.10+ and `uv` installed

**Setup command:**
```bash
claude mcp add google-workspace \
  -e GOOGLE_OAUTH_CLIENT_ID="YOUR_CLIENT_ID" \
  -e GOOGLE_OAUTH_CLIENT_SECRET="YOUR_SECRET" \
  -- uvx workspace-mcp --tools gmail drive calendar docs sheets --tool-tier core
```

**Security considerations:**
- Start with `--read-only` mode and read-only OAuth scopes
- Only enable write access after verifying the workflow
- Be cautious of prompt injection via email content
- Store OAuth tokens with restricted file permissions

**Correction flywheel angle:** The agent learns how Weber organizes his email (labels, naming conventions, which clients use which email addresses). Corrections like "search for John Smith emails under label:PROJECTX, not inbox" persist permanently. The agent also learns document naming conventions, folder structures, and which Drive locations contain which types of documents.

---

### 1.3 Autodesk APS MCP Server

**Source:** [autodesk-platform-services/aps-mcp-server-nodejs](https://github.com/autodesk-platform-services/aps-mcp-server-nodejs) | Official Autodesk
**What data becomes accessible:**
- **AEC Data Model:** Query Revit/BIM models hosted on Autodesk Construction Cloud via natural language
- **3D Viewer integration:** Interactive visualization of 70+ file formats
- **Model data:** Volumes, areas, element counts, properties, relationships
- **Construction Cloud documents:** Files, sheets, drawings stored in ACC/BIM 360
- **Cross-model queries:** Compare versions, track changes across model iterations

**Integration approach:** Node.js MCP server with Secure Service Accounts
**Estimated effort:** 1-2 hours (requires Autodesk Platform Services credentials)
**Value score:** 9/10 -- extends RevitMCPBridge capabilities to cloud-hosted models and multi-format support
**Complexity score:** 3/10 -- official Autodesk server with documentation
**Priority rank:** 3.0
**Dependencies:**
1. Autodesk Platform Services account (free tier available)
2. APS Client ID and Secret
3. Node.js installed
4. Models uploaded to Autodesk Construction Cloud or BIM 360

**Correction flywheel angle:** Corrections about model navigation (e.g., "in this project, HVAC families are under Mechanical > Equipment, not Mechanical > HVAC") transfer across all APS-connected models. The agent builds project-specific knowledge about model organization.

---

### 1.4 SQLite MCP Server (Reference Implementation)

**Source:** [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | Official reference
**What data becomes accessible:**
- Local SQLite databases (correction memory, project data, cached permit results)
- Direct SQL queries against any `.db` file
- Schema inspection and data analysis

**Integration approach:** Already available as deferred tool in current session
**Estimated effort:** 15 minutes (already loaded, just needs formal configuration)
**Value score:** 7/10 -- foundational for caching and local data management
**Complexity score:** 1/10 -- reference implementation, zero configuration
**Priority rank:** 7.0
**Dependencies:** None

**Note:** This server is already available as `mcp__sqlite-server` in the current deferred tools. Formalizing it as a permanent MCP server ensures it's always available.

**Correction flywheel angle:** The correction database itself is SQLite. Direct SQL access allows the agent to query correction patterns, analyze which corrections are most frequently surfaced, and optimize the flywheel.

---

### 1.5 Filesystem MCP Server (Reference Implementation)

**Source:** [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | Official reference
**What data becomes accessible:**
- Structured file operations with access controls
- Directory listing, file search, file content reading across configured paths
- Safer than raw bash for file operations

**Integration approach:** Node.js reference server
**Estimated effort:** 15 minutes
**Value score:** 6/10 -- provides structured file access beyond bash
**Complexity score:** 1/10 -- trivial setup
**Priority rank:** 6.0
**Dependencies:** Node.js installed

**Correction flywheel angle:** Minimal direct flywheel impact, but provides a safer foundation for file operations that other integrations depend on.

---

## Tier 2 -- Connect This Month

These require some setup work -- either configuring existing servers with specific credentials, or building lightweight wrappers around well-documented APIs.

---

### 2.1 Slack MCP Server

**Source:** [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) or community alternatives
**What data becomes accessible:**
- Channel messages and threads across all workspaces
- Direct messages (with appropriate permissions)
- File sharing history
- Channel membership and workspace structure
- Real-time notifications and responses

**Integration approach:** Existing MCP server (official reference or community)
**Estimated effort:** 1-2 hours (Slack app creation + OAuth)
**Value score:** 7/10 -- high if team communication happens in Slack; captures project discussions, quick decisions, and informal knowledge that never makes it to email or documents
**Complexity score:** 2/10 -- well-documented Slack API
**Priority rank:** 3.5
**Dependencies:**
1. Slack workspace admin access (or permission to create apps)
2. Slack Bot Token with appropriate scopes
3. Channel access permissions

**Correction flywheel angle:** Slack contains the most informal, decision-rich communication. Corrections about how to interpret Slack discussions (e.g., "when Weber says 'approved' in #project-x, that's not a formal approval -- check email for the signed version") become institutional knowledge.

---

### 2.2 Notion MCP Server

**Source:** [makenotion/notion-mcp-server](https://github.com/makenotion/notion-mcp-server) or [suekou/mcp-notion-server](https://github.com/suekou/mcp-notion-server)
**What data becomes accessible:**
- Notion databases (project trackers, contact lists, resource libraries)
- Wiki pages and knowledge bases
- Task boards and project management data
- Meeting notes and documentation
- Linked database relationships

**Integration approach:** Existing MCP server
**Estimated effort:** 1-2 hours (Notion integration API key)
**Value score:** 6/10 -- depends on how much project data lives in Notion
**Complexity score:** 2/10 -- straightforward API key setup
**Priority rank:** 3.0
**Dependencies:**
1. Notion account with API access
2. Notion integration token
3. Pages/databases shared with the integration

**Correction flywheel angle:** Notion often serves as a knowledge base. Corrections about how information is organized in Notion (database structures, property names, linked relations) make future queries faster and more accurate.

---

### 2.3 Miami-Dade ArcGIS Permit Data (Custom MCP Server)

**Source:** Miami-Dade County Open Data Hub via ArcGIS REST API
**What data becomes accessible:**
- **181,333+ building permits** (last 3 years) with full field data
- Permit number, type, status, address, folio, issue date, inspection dates
- Estimated construction values, contractor names and numbers
- Certificate of completion dates, property use codes
- **Code enforcement cases** (Energov system) -- open and closed
- **Building code violations** -- open, closed (1yr and 5yr), with liens
- **Parcel boundaries** and building footprints linked to folio numbers
- **Address point data** for geocoding

**Integration approach:** Custom Python MCP server wrapping ArcGIS REST API
**API base:** `https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/`
**Estimated effort:** 1-2 weeks
**Value score:** 9/10 -- direct access to the county permit database is transformative for any South Florida AEC professional
**Complexity score:** 4/10 -- well-documented ArcGIS REST API, no authentication required, standard JSON responses
**Priority rank:** 2.3
**Dependencies:**
1. Python MCP server framework (FastMCP or similar)
2. SQLite cache layer for results (permits update weekly)
3. No API key needed -- public data

**Proposed tools:**
- `search_permits(address, folio, permit_number, status, date_range, permit_type)`
- `get_permit_details(permit_number)`
- `search_violations(address, folio, status)`
- `get_violation_details(case_number)`
- `search_parcels(address, lat_lng, radius)`
- `get_permit_activity_summary(zip_code, period_months)`
- `find_large_projects(min_value, county, limit)`

**Correction flywheel angle:** This is where the flywheel shines brightest. Every correction about permit data interpretation (e.g., "STATUS='FIN' means finaled, not finished," "PROPUSE code 0100 is single-family residential") becomes permanent AEC domain knowledge. The agent builds an ever-growing understanding of South Florida permit systems.

---

### 2.4 IFC/BIM MCP Server (ifcMCP)

**Source:** [smartaec/ifcMCP](https://github.com/smartaec/ifcMCP) or [bonsai-bim MCP](https://github.com/JotaDeRodriguez/bonsai-blender-ifc)
**What data becomes accessible:**
- IFC file content (Industry Foundation Classes -- the open BIM standard)
- Building element properties, quantities, and relationships
- Spatial hierarchy (site > building > story > space > element)
- Material assignments and classifications
- Quantity takeoffs from IFC models
- Cross-model comparison

**Integration approach:** Existing Python MCP server (ifcMCP or Bonsai BIM)
**Estimated effort:** 2-3 days (Python setup, IfcOpenShell dependency)
**Value score:** 8/10 -- extends BIM capabilities beyond Revit to the open IFC standard. Essential for interoperability with consultants using non-Revit BIM software (ArchiCAD, Tekla, Allplan)
**Complexity score:** 4/10 -- existing server, but IfcOpenShell can be finicky to install on Windows
**Priority rank:** 2.0
**Dependencies:**
1. Python 3.10+
2. IfcOpenShell library
3. IFC files to query (from project exports or consultant deliverables)

**Correction flywheel angle:** Corrections about IFC schema interpretation (e.g., "IfcWallStandardCase is a wall with material layers, IfcWall is more generic") build deep BIM interoperability knowledge.

---

### 2.5 Weather / NOAA MCP Server

**Source:** [weather-mcp/weather-mcp](https://github.com/weather-mcp/weather-mcp) | 12 weather tools, no API key required
**What data becomes accessible:**
- Current weather conditions and forecasts (global)
- Historical weather data (1940-present)
- NOAA weather alerts for project locations
- Air quality index
- Marine conditions (tides, currents) -- relevant for waterfront projects
- Lightning detection (construction site safety)
- River/flood monitoring
- Wildfire tracking
- Radar imagery

**Integration approach:** Existing MCP server (npm package)
**Estimated effort:** 1 hour
**Value score:** 6/10 -- directly relevant for construction scheduling, site safety, and resilient design decisions
**Complexity score:** 2/10 -- no API key, npm install
**Priority rank:** 3.0
**Dependencies:** Node.js

**Correction flywheel angle:** Corrections about weather data interpretation for construction (e.g., "for concrete pours in Miami, check both temperature AND humidity -- not just temperature") become construction-specific safety knowledge.

---

### 2.6 Linear MCP Server

**Source:** [linear/linear-mcp-server](https://github.com/linear/linear-mcp-server) or community alternatives
**What data becomes accessible:**
- Issue tracking across projects (bugs, features, tasks)
- Sprint/cycle progress and velocity
- Team workload and assignments
- Project roadmaps and milestones

**Integration approach:** Existing MCP server
**Estimated effort:** 1 hour
**Value score:** 5/10 -- high if using Linear for project management; lower if not
**Complexity score:** 2/10 -- API key setup
**Priority rank:** 2.5
**Dependencies:** Linear account and API key

**Correction flywheel angle:** Corrections about task management workflows (priority conventions, label meanings, team assignment rules) persist across sessions.

---

## Tier 3 -- Build This Quarter

These require custom MCP server development -- either wrapping existing APIs with MCP tooling or building scrapers for portals without APIs.

---

### 3.1 ICC Code Connect -- Florida Building Code API

**Source:** [ICC Code Connect API](https://solutions.iccsafe.org/codeconnect)
**What data becomes accessible:**
- **Complete Florida Building Code** (8th Edition, 2023) -- full text of every section
- **Historical code editions** (7th, 6th, etc.) for existing building analysis
- **International Building Code (IBC)** and all ICC model codes
- Subsection-level content retrieval in JSON format
- Chapter-by-chapter navigation
- Cross-references between code sections

**Integration approach:** Custom MCP server wrapping ICC Code Connect REST API
**Estimated effort:** 2-3 weeks (API subscription, server development, code parsing logic)
**Value score:** 10/10 -- having the Florida Building Code directly queryable by an AI agent is the single most transformative integration for AEC work. "What does FBC 2023 Section 1612 require for flood-resistant construction?" gets an authoritative answer.
**Complexity score:** 6/10 -- API is well-documented but requires paid subscription; code content parsing needs careful structuring
**Priority rank:** 1.7
**Dependencies:**
1. ICC Code Connect API subscription (pricing not public -- contact ICC)
2. Understanding of code structure (chapters, sections, subsections)
3. JSON parsing for code content
4. Local caching (code content changes only at edition cycles)

**Proposed tools:**
- `search_building_code(query, code="FBC2023", scope="building")`
- `get_code_section(code, section_number)` -- e.g., "FBC2023 Section 1612"
- `get_code_chapter(code, chapter_number)`
- `compare_code_editions(section, edition_a, edition_b)` -- track code changes
- `find_related_sections(section)` -- follow cross-references

**Correction flywheel angle:** This is where the flywheel becomes a genuine competitive advantage. Every correction about code interpretation (e.g., "Section 1612.4 applies to buildings in flood zones AE, not zone X -- the 8th edition changed this from the 7th") becomes permanent institutional knowledge. Over time, the agent develops building code expertise that rivals a plans examiner.

---

### 3.2 Broward County Permits (Scraping-Based MCP Server)

**Source:** Broward County BCS Portal (`dpepp.broward.org/BCS/`)
**What data becomes accessible:**
- Permit applications, statuses, and inspection results for unincorporated Broward County
- Contractor information on permits
- Certificate of Use records
- Master permit tracking
- Address-based and permit-number-based search

**Integration approach:** Custom Python MCP server with Playwright scraper
**Estimated effort:** 3-4 weeks (scraper development, error handling, rate limiting, MCP server shell)
**Value score:** 8/10 -- essential for any project in Broward County
**Complexity score:** 7/10 -- legacy POSSE ASP.NET WebForms portal, no API, server-side rendering, fragile DOM structure
**Priority rank:** 1.1
**Dependencies:**
1. Playwright Python library
2. Robust error handling for portal downtime
3. SQLite cache (avoid re-scraping same data)
4. Rate limiting (2-5 second delays between requests)
5. User agent rotation

**Correction flywheel angle:** Corrections about Broward County permit conventions (e.g., "Broward uses different permit type codes than Miami-Dade," "BCS portal sometimes shows 'EXPIRED' for permits that are actually 'FINALED'") become county-specific institutional knowledge.

---

### 3.3 Miami-Dade Property Appraiser (Hybrid MCP Server)

**Source:** Miami-Dade Property Appraiser (`miamidade.gov/Apps/PA/propertysearch/`) + ArcGIS layers
**What data becomes accessible:**
- **Property ownership** (current and historical chain of title)
- **Assessed values** (land, building, total) and historical trends
- **Building characteristics** (year built, sq ft, bedrooms, baths, stories, construction type)
- **Sales history** (dates, prices, qualified/unqualified sales)
- **Exemptions** (homestead, senior, veteran, etc.)
- **Zoning and land use codes**
- **Tax roll data**
- **Legal descriptions**

**Integration approach:** Hybrid -- ArcGIS REST for parcel geometry + Playwright scraping for full property details
**Estimated effort:** 2-3 weeks
**Value score:** 8/10 -- property data is foundational for site analysis, feasibility studies, and project due diligence
**Complexity score:** 6/10 -- ArcGIS part is easy; web scraper for full details is moderate
**Priority rank:** 1.3
**Dependencies:**
1. ArcGIS REST client (from Miami-Dade permit server -- shared code)
2. Playwright for web portal scraping
3. SQLite cache (property data changes slowly -- cache for 7 days)
4. Folio number lookup logic

**Proposed tools:**
- `search_property(address, folio, owner_name)`
- `get_property_details(folio)` -- full assessment, building characteristics, exemptions
- `get_sales_history(folio)` -- all recorded sales
- `get_property_permits(folio)` -- cross-reference with permit server
- `search_properties_in_area(lat, lng, radius, filters)`
- `compare_property_values(folio_list)` -- comp analysis

**Correction flywheel angle:** Corrections about property data interpretation (e.g., "assessed value in Miami-Dade is NOT market value -- it's capped by Save Our Homes," "CLUC code 0100 means single-family residential") become permanent real estate knowledge.

---

### 3.4 Broward County Property Appraiser (BCPA)

**Source:** BCPA (`web.bcpa.net/BcpaClient/`)
**What data becomes accessible:**
- Same categories as Miami-Dade PA but for Broward County
- Property ownership, values, characteristics, sales history, exemptions, tax data

**Integration approach:** Custom Playwright scraper wrapped in MCP server
**Estimated effort:** 2-3 weeks
**Value score:** 7/10 -- essential for Broward County projects
**Complexity score:** 7/10 -- legacy web interface, no API
**Priority rank:** 1.0
**Dependencies:** Same as Miami-Dade PA server (shared Playwright infrastructure)

**Correction flywheel angle:** Same as MDC PA, but corrections are county-specific (different assessment methods, different exemption types, different data formats).

---

### 3.5 Florida DBPR Contractor License Verification

**Source:** MyFloridaLicense.com / Contractor-Verify API (`contractor-verify.com`)
**What data becomes accessible:**
- **365,000+ Florida contractor licenses**
- License status (active, inactive, suspended, revoked)
- License type and classification
- Disciplinary actions and complaints
- Insurance and bond information
- Qualifier information

**Integration approach:** Custom MCP server wrapping Contractor-Verify API (or direct DBPR scraping)
**Estimated effort:** 1 week
**Value score:** 7/10 -- contractor verification is a frequent need for project managers and owners
**Complexity score:** 4/10 -- Contractor-Verify has a free API; DBPR scraping is moderate
**Priority rank:** 1.8
**Dependencies:**
1. Contractor-Verify free account (or Playwright for direct DBPR access)
2. License number or contractor name for lookups

**Proposed tools:**
- `verify_license(license_number)`
- `search_contractor(name, license_type, county)`
- `get_disciplinary_history(license_number)`
- `check_insurance_status(license_number)`

**Correction flywheel angle:** Corrections about contractor licensing conventions (e.g., "CGC means General Contractor, CBC means Building Contractor -- different scopes," "Broward County requires separate local registration beyond the state license") become permanent compliance knowledge.

---

### 3.6 Shovels.ai National Permit Data

**Source:** [Shovels.ai API](https://docs.shovels.ai/api-reference/)
**What data becomes accessible:**
- **180 million building permits** across all 48 continental states
- **3 million contractor profiles** with work history
- Permit search by value, type, status, geography, property characteristics
- Contractor intelligence (specialties, license types, activity history)
- Market analytics (permit volumes, values by area)

**Integration approach:** Custom MCP server wrapping Shovels.ai REST API
**Estimated effort:** 3-5 days
**Value score:** 7/10 -- excellent for national scope and competitor analysis; supplements county-specific data
**Complexity score:** 3/10 -- modern REST API with good documentation
**Priority rank:** 2.3
**Dependencies:**
1. Shovels.ai API subscription (contact sales for pricing)
2. API key

**Correction flywheel angle:** Corrections about how to interpret Shovels data vs. direct county data (e.g., "Shovels.ai may lag county data by 2-4 weeks," "use county data for current status, Shovels for historical analysis") teach the agent when to use which source.

---

### 3.7 Accela API (Fort Lauderdale and Other Broward Cities)

**Source:** [Accela Developer Portal](https://developer.accela.com/)
**What data becomes accessible:**
- Permit records for municipalities using Accela (Fort Lauderdale, Hollywood, Pompano Beach, etc.)
- Inspection schedules and results
- Address and parcel search
- Property owner information

**Integration approach:** Custom MCP server wrapping Accela REST API with OAuth 2.0
**Estimated effort:** 1-2 weeks
**Value score:** 6/10 -- covers major Broward cities individually; less comprehensive than a county-wide solution
**Complexity score:** 5/10 -- good API but each municipality requires separate credentials and configuration
**Priority rank:** 1.2
**Dependencies:**
1. Accela developer account
2. OAuth credentials per agency
3. Agency name and environment from Accela support

**Correction flywheel angle:** Corrections about municipality-specific permit conventions (e.g., "Fort Lauderdale uses different inspection types than Miami-Dade," "Hollywood FL permit numbers start with BLD-") build multi-jurisdiction expertise.

---

## Tier 4 -- Strategic / Future

These are high-value but require significant effort, paid subscriptions, or API access that may not yet exist. Plan for these after the foundation is built.

---

### 4.1 Procore MCP Server (Construction Management)

**Source:** [Procore MCP](https://mcpmarket.com/server/procore) | Zapier MCP integration also available
**What data becomes accessible:**
- Project directory and company information
- RFIs (Requests for Information) -- full threads with responses
- Submittals -- shop drawings, product data, tracking
- Daily logs -- field reports, weather, manpower, activities
- Punch lists -- deficiency items with photos and status
- Change orders -- cost impacts, approval chains
- Drawing sets -- revisions, markups, distribution
- Schedule milestones and updates

**Integration approach:** Existing MCP server (Zapier connector or custom via Procore API)
**Estimated effort:** 1-2 weeks
**Value score:** 8/10 -- Procore is the dominant construction management platform. Access to RFIs, submittals, and daily logs is enormously valuable for project coordination.
**Complexity score:** 5/10 -- Procore API is well-documented; Zapier MCP connector provides a quick path
**Priority rank:** 1.6
**Dependencies:**
1. Procore account with API access
2. OAuth app registration in Procore
3. Project-level permissions

**Correction flywheel angle:** Corrections about construction management conventions (RFI numbering, submittal coding, daily log expectations) become reusable project management knowledge.

---

### 4.2 Autodesk Build MCP Server (Construction Cloud)

**Source:** [samuraibuddha/autodesk-build-mcp](https://lobehub.com/mcp/samuraibuddha-autodesk-build-mcp)
**What data becomes accessible:**
- Construction documents and sheet sets
- Issues and deficiencies
- RFIs within Autodesk ecosystem
- Cost management data
- Model coordination clash results
- Photo documentation

**Integration approach:** Existing community MCP server or via APS MCP server (Tier 1.3)
**Estimated effort:** 1-2 weeks
**Value score:** 8/10 -- direct competitor integration to Procore; many firms use Autodesk Build
**Complexity score:** 5/10 -- Autodesk API authentication can be complex
**Priority rank:** 1.6
**Dependencies:**
1. Autodesk Construction Cloud subscription
2. APS credentials (may share with Tier 1.3)
3. Project access permissions

**Correction flywheel angle:** Corrections about Autodesk Build vs. Procore differences (workflow conventions, field naming, permission models) help the agent navigate multi-platform projects.

---

### 4.3 RS Means / Construction Cost Database

**Source:** [RSMeans Data](https://www.rsmeans.com/) (Gordian)
**What data becomes accessible:**
- **92,000+ unit cost line items** spanning all construction work types
- Material, labor, and equipment costs per unit of work
- Productivity rates (labor-hours per unit)
- Locality adjustment factors (including South Florida)
- Assembly cost models (composite costs for common assemblies)
- Historical cost trends and escalation factors

**Integration approach:** Custom MCP server -- likely requires RSMeans Online API access or data export parsing
**Estimated effort:** 4-6 weeks (API access negotiation + server development)
**Value score:** 9/10 -- cost estimation integrated into the design workflow is transformative
**Complexity score:** 8/10 -- RS Means API access is expensive and restrictive; may need to work with CSV/Excel exports instead
**Priority rank:** 1.1
**Dependencies:**
1. RSMeans Online subscription (enterprise pricing)
2. API access (contact Gordian for developer access)
3. Locality factor data for South Florida
4. Understanding of cost estimation methodology

**Alternative approaches:**
- **NIST CostLab** -- free construction cost data from the National Institute of Standards
- **Open cost databases** -- community-maintained construction cost data
- **Local supplier pricing** -- integrate with local material supplier catalogs

**Correction flywheel angle:** This is where the flywheel creates genuine cost estimation expertise. Corrections like "RS Means assembly B2010 110 for CMU walls does not include reinforcement in South Florida -- add 15% for hurricane compliance" become permanent cost knowledge that improves every future estimate.

---

### 4.4 Real Estate Data APIs (Zillow/Redfin/MLS)

**Source:** Various -- Zillow Group API, Redfin API, SimplyRETS, RealEstateAPI.com
**What data becomes accessible:**
- Property listings (active, pending, sold)
- Market comparable sales (comps)
- Price history and trends by neighborhood
- Neighborhood demographics and school ratings
- Rental estimates
- Market heat indices

**Integration approach:** Custom MCP server wrapping one or more real estate APIs
**Estimated effort:** 2-3 weeks
**Value score:** 6/10 -- useful for feasibility studies and site selection, but not core AEC workflow
**Complexity score:** 5/10 -- multiple API providers, each with different access requirements. MLS data access requires brokerage affiliation.
**Priority rank:** 1.2
**Dependencies:**
1. API subscription(s)
2. MLS feed access (if direct MLS data needed -- requires licensed broker partnership)
3. Compliance with data redistribution terms

**Correction flywheel angle:** Corrections about real estate data interpretation (e.g., "Zillow Zestimate is often 10-15% off in South Florida luxury market," "use Redfin for more accurate recent sales data") build market analysis expertise.

---

### 4.5 Manufacturer BIM Libraries / Product Data

**Source:** Various -- BIMobject, Sweets/Dodge, manufacturer websites
**What data becomes accessible:**
- Product specifications and technical data sheets
- BIM families (Revit .rfa files, IFC objects)
- Material properties (thermal, structural, fire-rated)
- Certifications and code compliance data
- Pricing and availability
- Installation instructions

**Integration approach:** Custom MCP server aggregating multiple manufacturer data sources
**Estimated effort:** 4-6 weeks (multiple data sources, varying formats)
**Value score:** 7/10 -- specification writing and product selection are time-consuming tasks that AI could accelerate
**Complexity score:** 7/10 -- no single API; data is scattered across hundreds of manufacturer websites and catalogs
**Priority rank:** 1.0
**Dependencies:**
1. BIMobject API access (free for basic use)
2. Manufacturer API partnerships (case by case)
3. Product data standardization logic

**Correction flywheel angle:** Corrections about product specifications (e.g., "Owens Corning R-30 fiberglass batt is 9.25 inches, not 10 inches," "Andersen 200 Series windows are NOT impact-rated for South Florida HVHZ") become specification knowledge that prevents costly errors.

---

### 4.6 CoStar / Commercial Real Estate Data

**Source:** [CoStar Group](https://www.costar.com/)
**What data becomes accessible:**
- Commercial property listings and lease rates
- Market analytics (vacancy rates, absorption, cap rates)
- Property ownership and transaction history
- Tenant information
- Development pipeline tracking
- Comparable sales for commercial properties

**Integration approach:** Custom MCP server -- would require CoStar API access
**Estimated effort:** Unknown -- CoStar's API is not publicly documented; access requires enterprise subscription
**Value score:** 7/10 -- CoStar is the gold standard for commercial real estate data
**Complexity score:** 8/10 -- expensive, restrictive API access, complex data model
**Priority rank:** 0.9
**Dependencies:**
1. CoStar enterprise subscription ($$$)
2. API access (negotiated separately from data subscription)
3. Legal compliance with CoStar's data terms

**Correction flywheel angle:** Corrections about commercial real estate metrics (cap rate interpretation, market cycle indicators) build investment analysis expertise.

---

### 4.7 Utility Company Data (FPL, Miami-Dade Water, etc.)

**Source:** Florida Power & Light, Miami-Dade Water and Sewer, etc.
**What data becomes accessible:**
- Service availability by address
- Utility capacity for new connections
- Rate schedules and load calculations
- Outage history
- Infrastructure locations (overhead vs. underground power)

**Integration approach:** Scraping-based or manual data integration -- no known public APIs
**Estimated effort:** Unknown -- heavily depends on what data is accessible
**Value score:** 5/10 -- useful for site analysis but not frequently needed
**Complexity score:** 8/10 -- no APIs, inconsistent data access
**Priority rank:** 0.6
**Dependencies:** Portal access, possibly account authentication

**Correction flywheel angle:** Corrections about utility requirements (e.g., "FPL requires 15-foot easement for new underground service in Miami-Dade," "MDWS impact fees are calculated differently for renovation vs. new construction") become infrastructure planning knowledge.

---

## Cross-Silo Query Examples

The real power of the Autonomy Engine emerges when agents can query across multiple data silos in a single workflow. Here are concrete examples:

### Example 1: Comprehensive Project Due Diligence
**User query:** "Run a full due diligence report on the property at 1200 Brickell Bay Drive, Miami"

**Agent workflow:**
1. **Miami-Dade ArcGIS** -> Search permits by address -> find all historical permits
2. **Miami-Dade Property Appraiser** -> Get assessed value, ownership, building characteristics, sales history
3. **Miami-Dade ArcGIS (violations)** -> Check for open code violations or liens
4. **Google Drive** -> Search for any existing documents about this property or neighborhood
5. **Gmail** -> Search for any past correspondence about this address
6. **Weather/NOAA** -> Check flood zone status, historical weather events
7. **Zillow/Redfin** -> Get current market value estimate and comparables
8. **Building Code (ICC)** -> What code edition was in effect when the building was constructed?

**Output:** A comprehensive due diligence report combining public records, personal history, and market data.

### Example 2: Cross-Platform Decision Tracking
**User query:** "Find every decision about the HVAC system for the Coral Gables project"

**Agent workflow:**
1. **Gmail** -> Search emails containing "HVAC" AND "Coral Gables" -> meeting summaries, consultant recommendations, client approvals
2. **Google Drive** -> Search for specifications, design narratives, and basis of design documents mentioning HVAC
3. **GitHub** -> Search issues and PRs in the project repo for HVAC-related changes
4. **Revit (RevitMCPBridge)** -> Query current HVAC families, parameters, and schedules in the model
5. **Slack** -> Search #coral-gables channel for HVAC discussions
6. **Notion** -> Search project wiki for HVAC meeting notes
7. **Procore** -> Search RFIs and submittals related to HVAC

**Output:** A chronological decision log showing how the HVAC system evolved from concept to current state, with sources linked.

### Example 3: Contractor Vetting
**User query:** "Is ABC Mechanical a good choice for the HVAC package on our next project?"

**Agent workflow:**
1. **DBPR License Verification** -> Verify active license, check for complaints or disciplinary actions
2. **Miami-Dade ArcGIS** -> Search all permits pulled by ABC Mechanical -> project size, type, frequency
3. **Shovels.ai** -> Get national profile, work history, specialties
4. **Gmail** -> Search for any past correspondence with ABC Mechanical
5. **Google Drive** -> Search for any past proposals or contracts from ABC Mechanical
6. **Procore** -> Check if ABC Mechanical has been on any past projects -> performance data

**Output:** A contractor intelligence report with license verification, project history, and any past relationship data.

### Example 4: Code Compliance Check
**User query:** "Does our hurricane protection design meet FBC 2023 requirements?"

**Agent workflow:**
1. **ICC Code Connect** -> Pull FBC 2023 Section 1609 (Wind Loads) and Section 1626 (Hurricane Protection)
2. **Revit (RevitMCPBridge)** -> Query window and door schedules, impact-rated specifications
3. **Weather/NOAA** -> Get design wind speed for the project location
4. **Google Drive** -> Find the structural engineer's wind analysis report
5. **Manufacturer Data** -> Verify specified products are approved for the required wind zone

**Output:** A compliance checklist mapping code requirements to actual design specifications with gap analysis.

---

## Security and Privacy Framework

### Data Classification

| Classification | Examples | Handling Rules |
|---------------|----------|----------------|
| **Public** | Permit records, property assessments, building code text, weather data | No restrictions. Cache freely. |
| **Professional Confidential** | Client emails, project documents, cost estimates, specifications | Process but do not cache indefinitely. Obey Anthropic data policies. Never include in external outputs without user approval. |
| **Sensitive Personal** | Financial data (cost databases), personal contact info, calendar entries | Process on demand only. Do not cache. Clear from context after task completion. |
| **Restricted** | OAuth tokens, API keys, passwords, security alerts | Never display in responses. Store only in environment variables. Never include in memory/corrections. |

### Access Control Principles

1. **Principle of least privilege:** Each MCP server should use the minimum scopes/permissions needed
2. **Read-first approach:** Start with read-only access for all new integrations; add write access only when proven safe
3. **Token isolation:** Each MCP server gets its own credentials; never share tokens between servers
4. **Cache hygiene:** Set TTLs for cached data (permits: 24h, property: 7d, code: 90d, weather: 1h)
5. **Audit logging:** Log all MCP server calls for security review (already implemented via `mcp-seatbelt`)

### Data Flow Security

```
User Query
    |
    v
Claude Code (Anthropic API)
    |
    v
MCP Seatbelt Hook (PreToolUse) -- validates call is safe
    |
    v
MCP Server (local process)
    |
    +---> Public APIs (ArcGIS, NOAA, ICC) -- no credentials needed
    +---> Authenticated APIs (GitHub, Google, Procore) -- OAuth/PAT stored in env vars
    +---> Scrapers (Playwright) -- rate-limited, cached results
    |
    v
Response returned to Claude (processed by Anthropic)
```

### Prompt Injection Mitigation

When MCP servers retrieve content from external sources (especially email and user-generated content), prompt injection is a real risk:

1. **Email content:** Gmail messages could contain hidden instructions. Treat all email content as untrusted data, not instructions.
2. **GitHub issues/PRs:** Public repositories could contain adversarial content. The agent should treat repository content as data, not commands.
3. **Scraped web pages:** Government portals could be compromised. Validate data against expected schemas.

**Mitigation:** The existing `mcp-seatbelt` PreToolUse hook provides a checkpoint for every MCP call. Consider extending it to flag suspicious content patterns in responses.

---

## Execution Timeline

### Week 1-2: Foundation (Tier 1)
- [ ] **Day 1:** Connect GitHub MCP Server (remote hosted, 30 min)
- [ ] **Day 1:** Formalize SQLite MCP server (15 min)
- [ ] **Day 2-3:** Set up Google Cloud Console project, configure OAuth, connect Google Workspace MCP
- [ ] **Day 4:** Connect Autodesk APS MCP server (if APS credentials are available)
- [ ] **Day 5:** Connect Filesystem MCP server
- [ ] **Day 5:** Test all Tier 1 integrations end-to-end
- [ ] **Day 5:** Run cross-silo query test: "Find all emails and GitHub issues related to RevitMCPBridge in the last month"

### Week 3-4: Productivity + First Custom Build (Tier 2 start)
- [ ] **Week 3:** Connect Slack MCP (if using Slack)
- [ ] **Week 3:** Connect Notion MCP (if using Notion)
- [ ] **Week 3:** Connect Weather/NOAA MCP (1 hour)
- [ ] **Week 3:** Install and test ifcMCP / BIM server
- [ ] **Week 4:** Begin Miami-Dade ArcGIS MCP server development
  - Build ArcGIS REST client
  - Implement permit search, violation search, parcel search tools
  - Build SQLite caching layer

### Week 5-6: Miami-Dade Permit Server Complete
- [ ] **Week 5:** Complete ArcGIS MCP server with all proposed tools
- [ ] **Week 5:** Testing with real queries against Miami-Dade data
- [ ] **Week 6:** Add EPS Portal scraper (plan review status -- Playwright)
- [ ] **Week 6:** Integration testing: cross-reference permits with property data

### Week 7-10: Property + Contractor Data (Tier 3)
- [ ] **Week 7-8:** Build Miami-Dade Property Appraiser MCP server (ArcGIS + scraper hybrid)
- [ ] **Week 9:** Build DBPR contractor license verification MCP server
- [ ] **Week 10:** Build Shovels.ai MCP server (if subscription acquired)

### Week 11-14: Building Codes + Broward County (Tier 3 continued)
- [ ] **Week 11-12:** Build ICC Code Connect MCP server (Florida Building Code)
- [ ] **Week 13-14:** Build Broward County BCS permit scraper MCP server
- [ ] **Week 14:** Build Broward BCPA property appraiser scraper

### Week 15-16: Integration + Testing
- [ ] **Week 15:** Cross-silo integration testing
- [ ] **Week 15:** Performance optimization (caching, rate limiting, error handling)
- [ ] **Week 16:** Documentation, user guide, correction seeding
- [ ] **Week 16:** Run full due diligence test (Example 1 above)

### Week 17+: Tier 4 (Ongoing)
- Evaluate Procore / Autodesk Build based on project needs
- Research RS Means API access
- Explore manufacturer BIM library integration
- Monitor for new MCP servers in the AEC space

---

## Metrics and Success Criteria

### Integration Health Dashboard

Track these metrics for each connected MCP server:

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Uptime** | >99% during business hours | MCP server health checks |
| **Response time** | <5s for API calls, <30s for scrapers | Log response times |
| **Cache hit rate** | >60% for permit/property data | SQLite cache stats |
| **Correction rate** | Decreasing over time per domain | Memory database queries |
| **Cross-silo queries** | >5 per week | Log multi-server tool chains |

### Success Milestones

1. **Week 2:** Agent can answer "What are my GitHub notifications and unread emails?" in a single conversation
2. **Week 6:** Agent can run a basic property due diligence report for any Miami-Dade address
3. **Week 10:** Agent can verify a contractor's license and pull their permit history
4. **Week 14:** Agent can answer building code questions with authoritative citations
5. **Week 16:** Agent can execute a full cross-silo due diligence workflow (5+ data sources)

---

## Appendix A: Current MCP Server Inventory

The following MCP servers are already connected or available in the Autonomy Engine (as of 2026-02-21):

### Active MCP Servers (in settings.json permissions)
| Server | Domain | Status |
|--------|--------|--------|
| `claude-memory` | Correction flywheel, persistent memory | Active |
| `bluebeam` | PDF markup and review | Active |
| `voice` | Text-to-speech | Active |
| `visual-memory` | Screenshot capture and recall | Active |
| `excel-mcp` | Excel COM automation | Active |
| `word-mcp` | Word COM automation | Active |
| `powerpoint-mcp` | PowerPoint COM automation | Active |
| `autocad-mcp` | AutoCAD automation | Active |
| `youtube-mcp` | YouTube video analysis | Active |
| `financial-mcp` | Stock/market data | Active |
| `whatsapp` | WhatsApp messaging | Active |
| `voice-input-mcp` | Voice transcription | Active |
| `floor-plan-vision` | Floor plan analysis | Active |
| `ai-render` | AI image rendering | Active |
| `revit-ui` | Revit UI automation | Active |
| `revit-recorder` | Revit operation recording | Active |
| `playwright` / `cdp-browser` | Browser automation | Active |
| `obs` | OBS Studio control | Active |

### Local MCP Server Repos (in /mnt/d/_MCP-SERVERS/)
| Server | Purpose | Status |
|--------|---------|--------|
| `ai-render-mcp` | AI image generation | Deployed |
| `autocad-mcp` | AutoCAD COM automation | Deployed |
| `excel-mcp` | Excel COM automation | Deployed |
| `powerpoint-mcp` | PowerPoint automation | Deployed |
| `word-mcp` | Word automation | Deployed |
| `voice-mcp` | TTS | Deployed |
| `youtube-mcp` | YouTube analysis | Deployed |
| `whatsapp-mcp` | WhatsApp | Deployed |
| `web-scraper-mcp` | General web scraping | Deployed |
| `git-mcp` | Git operations | Deployed |
| `ollama-orchestrator-mcp` | Local LLM orchestration | Deployed |
| `pdf-summarizer-mcp` | PDF analysis | Deployed |
| `postgres-inspect-mcp` | PostgreSQL inspection | Deployed |
| `revit-mcp-wrapper` | Revit bridge wrapper | Deployed |

### Deferred Tools (available but not permanently configured)
| Tool | Purpose |
|------|---------|
| `mcp__sqlite-server` | SQLite database queries |
| `mcp__aider-mcp-server-*` | AI code editing (Llama4, Ollama, Quasar) |

---

## Appendix B: MCP Server Development Template

For custom builds (Tiers 2-3), use this pattern:

```
project-name-mcp/
  src/
    server.py              # MCP server entry point (FastMCP)
    tools/
      __init__.py
      search.py            # Primary search tools
      details.py           # Detail retrieval tools
      analysis.py          # Aggregation/analysis tools
    providers/
      __init__.py
      api_client.py        # REST API client
      scraper.py           # Playwright scraper (if needed)
      cache.py             # SQLite cache manager
    models/
      __init__.py
      schemas.py           # Pydantic response models
    config.py              # Configuration and environment variables
  tests/
    test_tools.py
    test_providers.py
  pyproject.toml
  README.md
```

**Key design principles:**
1. Every tool returns structured Pydantic models, not raw JSON
2. Every provider has a cache layer with configurable TTL
3. Every scraper has rate limiting and retry logic built in
4. Every server supports `--read-only` mode
5. Every server logs to a standard location for debugging

---

## Appendix C: References

### Research Documents (This Project)
- [GitHub MCP Setup Guide](/mnt/d/_CLAUDE-TOOLS/agent-common-sense/research/deep-web/github-mcp-setup.md)
- [Google Workspace MCP Setup Guide](/mnt/d/_CLAUDE-TOOLS/agent-common-sense/research/deep-web/google-workspace-mcp-setup.md)
- [South Florida Permit Database Access](/mnt/d/_CLAUDE-TOOLS/agent-common-sense/research/deep-web/permit-database-access.md)

### MCP Server Repositories
- [github/github-mcp-server](https://github.com/github/github-mcp-server) -- Official GitHub MCP (27.1K stars)
- [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp) -- Google Workspace MCP (~1,500 stars)
- [autodesk-platform-services/aps-mcp-server-nodejs](https://github.com/autodesk-platform-services/aps-mcp-server-nodejs) -- Official Autodesk APS MCP
- [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) -- Reference implementations (SQLite, Filesystem, etc.)
- [smartaec/ifcMCP](https://github.com/smartaec/ifcMCP) -- IFC BIM MCP Server
- [weather-mcp/weather-mcp](https://github.com/weather-mcp/weather-mcp) -- Weather/NOAA MCP (12 tools, no API key)
- [wong2/awesome-mcp-servers](https://github.com/wong2/awesome-mcp-servers) -- Curated MCP server directory

### AEC-Specific APIs and Data Sources
- [ICC Code Connect API](https://solutions.iccsafe.org/codeconnect) -- Building code API
- [Florida Building Code (ICC Digital Codes)](https://codes.iccsafe.org/codes/florida) -- FBC online access
- [Autodesk APS Blog: Talk to Your BIM](https://aps.autodesk.com/blog/talk-your-bim-exploring-aec-data-model-mcp-server-claude)
- [Autodesk MCP Servers](https://www.autodesk.com/solutions/autodesk-ai/autodesk-mcp-servers) -- Official Autodesk MCP ecosystem
- [Shovels.ai API Reference](https://docs.shovels.ai/api-reference/) -- National permit data
- [Accela Developer Portal](https://developer.accela.com/) -- Municipal permit API
- [Contractor-Verify API](https://contractor-verify.com/) -- Florida contractor license lookup

### Miami-Dade County Data Sources
- [ArcGIS Services Directory](https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/) -- All feature services
- [Open Data Hub](https://gis-mdc.opendata.arcgis.com/) -- GIS datasets
- [Building Permit Dataset](https://gis-mdc.opendata.arcgis.com/datasets/MDC::building-permit) -- 181K+ permits
- [Property Appraiser Search](https://www.miamidade.gov/Apps/PA/propertysearch/)

### Broward County Data Sources
- [BCS Permit Search](https://dpepp.broward.org/BCS/) -- POSSE-based permit portal
- [GeoHub](https://geohub-bcgis.opendata.arcgis.com/) -- Open GIS data
- [BCPA Property Search](https://web.bcpa.net/BcpaClient/)

### MCP Server Directories and Guides
- [Awesome MCP Servers (1200+)](https://mcp-awesome.com/) -- Comprehensive directory
- [MCPServers.org](https://mcpservers.org/) -- Curated directory
- [Best MCP Servers for 2026](https://www.builder.io/blog/best-mcp-servers-2026) -- Builder.io guide
- [22 Best MCP Servers](https://desktopcommander.app/blog/2025/11/25/best-mcp-servers/) -- Desktop Commander guide
- [Composio Top 10 MCP Servers](https://composio.dev/blog/10-awesome-mcp-servers-to-make-your-life-easier)

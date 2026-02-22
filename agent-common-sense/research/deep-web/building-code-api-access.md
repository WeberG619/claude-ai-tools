# Building Code Programmatic Access - Feasibility Report

> **Research Date:** February 21, 2026
> **Purpose:** Evaluate all available paths to programmatic building code data for an MCP server integration

---

## Overview

Building codes in the United States are primarily developed by two organizations: the **International Code Council (ICC)** and the **National Fire Protection Association (NFPA)**. These model codes are then adopted (often with amendments) by states, counties, and municipalities. The key challenge for programmatic access is that building codes are copyrighted works that become law when adopted -- creating a legal gray area that has been actively litigated.

This report evaluates every available path to structured building code data, from official APIs to open-source alternatives, and recommends the most feasible approach for building an MCP server for AI-assisted code compliance.

---

## 1. ICC Digital Codes & Code Connect API

### API Status: AVAILABLE (Commercial License Required)

The ICC has made a significant investment in digital infrastructure and now offers **three separate APIs**:

### 1a. ICC Code Connect API (v1.0.1)

- **Endpoint:** `https://api.iccsafe.org/`
- **Authentication:** OAuth 2.0 SSO
- **Data Format:** JSON
- **Documentation:** https://developer.ecode360.com/

**Three sub-APIs:**
| API | Purpose |
|-----|---------|
| **Structure API** | Describes how code content is organized (titles, chapters, sections, hierarchy) |
| **Search API** | Full-text search across available code titles (same engine as eCode360) |
| **Content API** | Retrieves actual code text -- sections, tables, figures -- from subsections up to entire chapters in a single request |

**Available Content (confirmed):**
- 2021 I-Codes (IBC, IRC, IPC, IMC, IFGC, IECC, IFC, IEBC, ISPSC, IWUIC, IPSDC, IZC)
- 2018 I-Codes
- 2024 I-Codes (likely available, as ICC publishes on 3-year cycle)
- 2020 New York State Codes
- 2018 New Jersey Codes
- 2017 Ohio Codes
- eCode360 municipal codes (for participating jurisdictions)
- Historical versions of all titles

**Pricing Model:**
- **Implementation Fee:** One-time fee covering integration support and SLA-level terms
- **Content License:** Annual subscription, priced by:
  - *Jurisdictions:* Population size x number of titles
  - *Vendors/Companies:* Employee count x number of titles
- **Contact:** Phil Anthony at panthony@iccsafe.org
- **No public pricing disclosed** -- appears to be enterprise-level negotiation
- **Estimated range:** Likely $5,000-$50,000+/year based on company size (this is an educated estimate; ICC does not publish rates)

**Approved Integration Partners:**
- GovPilot (government management software)
- Archistar/eCheck (AI plan review -- ICC is "Premier Platinum Reseller")
- CivicPlus (community development software)
- Tyler Tech, Streamline AS, ESO, Spatial Data Logic
- Emergency Networking, Emergent, CDS/Municity

### 1b. ICC Code Adoption Database API

- **Endpoint:** `https://adoptions-api.iccsafe.org/api/doc`
- **Authentication:** Bearer Token (JWT) via `POST /api/v1/getToken` with clientId and secretKey
- **Data Format:** JSON
- **Status:** LIVE and documented

**Endpoints:**
| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/adoptionlabel` | Published adoption label listings |
| `GET /api/v1/adoptionlist` | General adoption records (paginated) |
| `GET /api/v1/adoptions/state` | State-level adoption data |
| `GET /api/v1/adoptions/county` | County-level adoption data |
| `GET /api/v1/adoptions/jurisdiction` | Jurisdiction-level adoption records |
| `GET /api/v1/adoptions/township` | Township-level adoption data |
| `GET /api/v1/codebooks` | All published code books |
| `GET /api/v1/codeyears` | Available code years |
| `GET /api/v1/searchLocations` | Search across all location types |

**Value:** This API answers the critical question "Which code edition has this jurisdiction adopted?" -- essential for any compliance tool. Supports filtering by code title, adoption label, and status.

### 1c. eCode360 API (General Code / Municipal Codes)

- **Endpoint:** `https://developer.ecode360.com/`
- **Type:** RESTful API
- **Purpose:** Access municipality-specific code data for jurisdictions using the eCode360 platform
- **Relationship:** Integrated with Code Connect API

### 1d. ICC Digital Codes Premium (Subscription Platform)

- **Website:** https://codes.iccsafe.org
- **Revit Add-In:** Available on Autodesk App Store (searches 2,900+ codes within Revit)
- **No direct API access** beyond Code Connect -- this is a consumer/end-user platform

**Subscription Pricing (as of 2025):**
| Tier | Monthly (Non-Member) | Annual (Non-Member) | 3-Year (Non-Member) |
|------|---------------------|--------------------|--------------------|
| Premium Complete | $97.00 | $1,056 | $1,870 |
| 2021 I-Code Collection | $89.00 | $888 | $1,586 |

**Volume Discounts:** 25% at 2 licenses, up to 55% at 100+ licenses.
**ICC Membership:** Starts at $66/year, reduces all subscription prices by ~25%.

### Assessment

ICC Code Connect API is **the most promising official path** to structured building code data. The API is production-grade, JSON-formatted, and used by major software companies. The barrier is **cost and approval** -- ICC requires a commercial relationship and content licensing agreement. There does not appear to be a free developer sandbox or trial tier.

---

## 2. UpCodes

### API Status: NO PUBLIC API

- **Website:** https://up.codes
- **Coverage:** 6,000+ state and city building codes, 80+ jurisdictions, 190K local amendments, 6M+ code sections
- **Update Frequency:** ~7,000 updates/month
- **Y Combinator backed**

**Platform Features:**
- Searchable code library with cross-references
- UpCodes Copilot (AI-powered compliance research assistant using LLM)
- Project-based collaboration tools
- Jurisdiction-specific code views with local amendments overlaid

**Pricing:**
| Plan | Approximate Cost |
|------|-----------------|
| Essentials | ~$33/month (annual) or ~$39/month (monthly) |
| Professional | Higher tier (pricing not publicly confirmed) |
| Enterprise | Custom pricing, contact sales |

**API Access:**
- According to GetApp (2026): "UpCodes does not have an API available"
- GitHub organization exists at https://github.com/upcodes but contains only utility repos (diff_match_patch-python, RevitTestFramework)
- No public developer documentation found
- Enterprise tier may include integration options, but this is unconfirmed

**UpCodes Copilot** is their AI product -- it answers code questions with citations, similar to what an MCP server would do. This suggests they have internally structured their code data in a way that supports RAG (retrieval-augmented generation), but they do not expose this externally.

### Assessment

UpCodes has the **best structured building code database** in the industry (6M+ sections with amendments), but it is **completely locked down**. No API, no data export, no developer program. The only path would be a business partnership/enterprise agreement, which would likely be expensive and restrictive. Web scraping would be both legally problematic and technically difficult (React SPA with authentication).

---

## 3. NFPA Codes

### API Status: NO API AVAILABLE

- **Platform:** NFPA LiNK (https://link.nfpa.org)
- **Coverage:** 1,400+ NFPA codes and standards
- **Key Codes:** NFPA 101 (Life Safety), NFPA 13 (Sprinklers), NFPA 72 (Fire Alarm), NFPA 70 (NEC)

**Free Access:**
- NFPA makes codes available online for free (read-only, non-downloadable) at https://www.nfpa.org/for-professionals/codes-and-standards/free-access
- This is a browser-based viewer, not structured data

**NFPA LiNK Pricing (effective March 3, 2025):**
| Plan | Price |
|------|-------|
| Monthly (recurring) | $13.99/mo |
| Individual Annual (auto-renew) | $129.99/yr |
| Individual Annual (non-auto) | $169.99/yr |
| 5-User Team Annual | $639.99/yr |
| 10-User Team Annual | $1,259.99/yr |
| Enterprise | Custom pricing |

**Developer Access:** None found. No API documentation, no developer portal, no SDK. NFPA LiNK is purely a web/mobile reading platform. No evidence of any programmatic access pathway.

### Assessment

NFPA codes are **critical for fire/life safety compliance** but have **zero programmatic access**. The only option is the free browser-based viewer (which could theoretically be scraped, but the content is copyrighted). NFPA has not signaled any interest in API access.

---

## 4. State-Specific Code Databases

### Florida Building Code

- **Website:** https://www.floridabuilding.org
- **API Status:** NO API
- **Access:** Free online at codes.iccsafe.org (hosted by ICC)
- **Nature:** Florida Building Code is based on I-Codes with Florida-specific amendments
- **Product Approval System:** Has an online database (BCIS) but no public API
- **9th Edition (2026):** Currently in development

### California Building Standards Commission (CBSC)

- **Website:** https://www.dgs.ca.gov/BSC
- **API Status:** NO API
- **Access:** Title 24 (12 parts) available through ICC's platform and third-party publishers
- **Nature:** California significantly modifies I-Codes; Title 24 is the most complex state building code
- **2025 Edition:** Published July 1, 2025; effective January 1, 2026

### New York City Building Code

- **Website:** NYC Open Data portal (api-portal.nyc.gov)
- **API Status:** PARTIAL -- NYC Open Data provides DOB permit/violation data via Socrata API, but NOT the actual building code text
- **GitHub:** https://github.com/maxmcd/bis (unofficial NYC BIS API wrapper)
- **Nature:** NYC has its own building code (not directly based on I-Codes), available through ICC Code Connect API (2020 NY State Codes confirmed available)

### Assessment

**No state or city building code authority offers a direct API for code text.** Florida and California codes are accessible through ICC's platform. NYC has the most data-friendly infrastructure (Open Data portal) but for permit/inspection data, not code text itself.

---

## 5. Open Source Alternatives

### Status: VERY LIMITED

**No comprehensive open-source building code database exists.** This is due to:
1. Copyright restrictions on model codes
2. Complexity of amendments across 50 states and thousands of jurisdictions
3. Codes change on 3-year cycles with mid-cycle amendments

**What does exist:**

| Resource | Description | Usefulness |
|----------|-------------|------------|
| **buildingSMART IFC** | Open standard for BIM data exchange | High for model checking, not code text |
| **buildingSMART IDS** | XML standard for Information Delivery Specifications | Useful for defining compliance requirements |
| **BCF-XML** | BIM Collaboration Format for issue tracking | Useful for flagging compliance issues |
| **Autodesk Community Forum** | Discussion thread requesting structured building code data (2023) | Confirms demand, no solution |
| **Public.Resource.Org** | Advocacy org that posts government edicts online | Some codes available but legally contested |

**GitHub Search Results:**
- No repositories found containing structured building code text data
- UpCodes GitHub (github.com/upcodes) has utility repos only, no code data
- No "OpenBuildingCodes" initiative exists
- buildingSMART repos focus on IFC/BIM standards, not regulatory code text

### Assessment

There is a **market gap** for open-source building code data. The copyright status of adopted codes (see Legal section) creates uncertainty that discourages open initiatives. The closest thing to an open standard for building code compliance checking is through IFC + IDS, but these address model validation, not code text lookup.

---

## 6. AI Code Compliance Tools (Competitor Landscape)

The AI compliance space has exploded in 2024-2025. Key players:

### Tier 1: Funded Startups with ICC Integration

| Company | Focus | Code Data Source | Funding | Status |
|---------|-------|-----------------|---------|--------|
| **Archistar (eCheck/AI PreCheck)** | Automated plan review for municipalities | ICC Code Connect API (Premier Platinum Reseller) | Major funding (Australian) | Active, deployed in 25+ municipalities including Austin, LA, Vancouver |
| **CivCheck** | Guided AI plan review | ICC integration | Acquired by Clariti (Oct 2025) | Active, deployed in Honolulu, Bellevue |
| **CodeComply.AI** | AI plan review from uploaded PDFs | Digitized IBC, IPC, IMC, NFPA 101, ADA, local codes | $2M seed (2024) | Active, Miami-based |

### Tier 2: Emerging AI Compliance Tools

| Company | Focus | Notes |
|---------|-------|-------|
| **Permitify** | AI co-pilot for plan review | YC-backed (W25), $500K seed, browser-based |
| **Blitz AI** | AI compliance infrastructure | blitzpermits.ai, early stage |
| **UpCodes Copilot** | AI-powered code research assistant | Built on UpCodes' 6M+ section database |

### Tier 3: Design-Stage AI Tools (Not Pure Compliance)

| Company | Focus | Notes |
|---------|-------|-------|
| **TestFit** | Generative design with zoning awareness | Real-time feasibility with parking/unit counts |
| **Delve** (Sidewalk Labs) | Data-driven urban planning | Performance metrics, not code text |
| **Swapp** | AI construction documentation from BIM | Code-aware CD generation |

### How They Access Code Data

1. **Archistar/eCheck:** Direct ICC Code Connect API integration (the gold standard)
2. **CodeComply.AI:** "Turns 400+ lines of compliance codes into algorithms" -- appears to have manually digitized code rules into algorithmic form (not raw code text lookup)
3. **UpCodes Copilot:** Built on their proprietary 6M+ section database with RAG
4. **Permitify:** "Reads site context, zoning data, and uploaded drawings" -- likely uses a combination of digitized rules and document analysis
5. **CivCheck:** "AI checks for code issues across every review group" -- appears to use rule-based algorithms cross-referenced to code databases

**Key Insight:** Most AI compliance tools do NOT do raw code text lookup. They pre-process building codes into structured rules/algorithms, then apply those rules to building plans. This is fundamentally different from an MCP server that would return code text in response to queries.

---

## 7. Legal/Licensing Considerations

### The Core Issue

Building codes are written by private organizations (ICC, NFPA) as "model codes." When governments adopt them as law, a tension arises: the code text is copyrighted, but it is also the law.

### Key Legal Precedents

**Georgia v. Public.Resource.Org, Inc. (2020) -- U.S. Supreme Court:**
- Held 5-4 that the Official Code of Georgia Annotated (including annotations) is ineligible for copyright protection
- Extended the "government edicts doctrine": works created by legislators in their official capacity cannot be copyrighted
- **Implication for building codes:** Codes adopted as law are arguably in the public domain, but codes NOT yet adopted (model codes) retain copyright

**Veeck v. Southern Building Code Congress International (2002) -- 5th Circuit:**
- Held that model codes enacted into law lose copyright protection
- The text of the law belongs to the public

**ICC v. UpCodes (2017-present):**
- ICC sued UpCodes for copyright infringement for posting I-Codes online
- In 2020, Judge Marrero ruled UpCodes' posting was covered by public domain and fair use
- Key distinction: codes adopted into law = public domain; model codes NOT adopted = still copyrighted
- ICC cannot sue for adopted code text, but CAN sue if UpCodes copies model codes that haven't been enacted
- ICC filed a second suit for "false advertising" and "unfair competition"
- **Status as of 2026:** Litigation appears to still be ongoing; no final resolution found

### Practical Legal Implications for an MCP Server

| Approach | Legal Risk | Notes |
|----------|-----------|-------|
| Use ICC Code Connect API with license | **LOW** | Legitimate, licensed access; ICC's intended pathway |
| Scrape UpCodes | **HIGH** | Terms of service violation + potential copyright claims |
| Scrape ICC free viewer (codes.iccsafe.org) | **MEDIUM-HIGH** | Free viewer is for human reading; TOS prohibits scraping |
| Post adopted code text (citing public domain) | **MEDIUM** | Supported by case law but requires careful tracking of which codes are adopted where |
| Use NFPA free access content | **MEDIUM** | Free for reading, not for redistribution or programmatic use |
| Use knowledge files (curated summaries) | **LOW** | Transformative use; not reproducing copyrighted text verbatim |

### AI Training Considerations (2025 Landscape)

- The Copyright Office concluded in May 2025 that "some uses of copyrighted works for generative AI training will qualify as fair use, and some will not"
- **Bartz v. Anthropic** (2025): Court found LLM training is "quintessentially transformative" but ONLY when training data is lawfully sourced
- **Bottom line:** Using building code text to train an LLM is legally uncertain; using it for RAG retrieval with proper licensing is much safer

---

## 8. MCP Server Design (Proposed Approach)

### Recommended Architecture: Hybrid Tiered System

Given the research findings, the most realistic path is a **three-tier approach**:

```
Tier 1: Local Knowledge Base (FREE, immediate)
   - Curated knowledge files (summaries, tables, requirements)
   - Pre-processed code rules in structured JSON
   - The 113 knowledge files already in RevitMCPBridge as foundation

Tier 2: ICC Code Adoption Database API (FREE/LOW COST)
   - Query which code editions a jurisdiction has adopted
   - Answer "What version of IBC does Miami-Dade use?"

Tier 3: ICC Code Connect API (COMMERCIAL LICENSE)
   - Direct code text lookup by section number
   - Full-text search across code titles
   - Structured content retrieval (sections, tables, figures)
```

### Proposed MCP Tool Interface

```typescript
// Tier 1: Knowledge Base Tools (immediate)
tools: {
  // Lookup pre-processed requirements by topic
  get_code_requirement: {
    params: {
      topic: string,          // e.g., "egress", "fire_rating", "occupancy_load"
      building_type?: string,  // e.g., "healthcare", "assembly", "residential"
      code?: string,           // e.g., "IBC", "IPC", "NFPA101"
    },
    returns: { requirement: string, source: string, section_ref: string }
  },

  // Lookup occupancy requirements
  get_occupancy_requirements: {
    params: {
      building_type: string,   // e.g., "healthcare", "educational"
      occupancy_group?: string, // e.g., "A-1", "B", "I-2"
    },
    returns: { requirements: OccupancyRequirement[] }
  },

  // Table lookup (pre-processed)
  lookup_code_table: {
    params: {
      code: string,            // e.g., "IBC"
      table_number: string,    // e.g., "1004.5", "601"
    },
    returns: { table_data: object, source: string }
  },

  // Tier 2: Adoption Database (requires ICC API credentials)
  check_jurisdiction_adoption: {
    params: {
      state: string,
      county?: string,
      city?: string,
      code_title?: string,     // e.g., "IBC", "IRC"
    },
    returns: { adopted_edition: string, effective_date: string, amendments: string[] }
  },

  // Tier 3: Direct Code Lookup (requires ICC Code Connect license)
  get_code_section: {
    params: {
      code: string,            // e.g., "IBC"
      edition: string,         // e.g., "2021"
      section: string,         // e.g., "1004.1.2"
    },
    returns: { text: string, tables: Table[], figures: Figure[], cross_refs: string[] }
  },

  search_code: {
    params: {
      query: string,           // e.g., "maximum travel distance assembly"
      code?: string,           // limit to specific code
      edition?: string,
    },
    returns: { results: SearchResult[] }
  },

  // Utility tools
  get_code_hierarchy: {
    params: {
      code: string,
      edition: string,
    },
    returns: { chapters: Chapter[] }  // TOC/structure
  }
}
```

### Knowledge Base Structure (Tier 1)

The 113 knowledge files already in RevitMCPBridge should be reorganized into a queryable format:

```
knowledge/
  ibc/
    chapter_3_occupancy.json      # Use groups, occupancy classifications
    chapter_5_heights_areas.json  # Table 504.3, 504.4, etc.
    chapter_6_construction.json   # Fire resistance requirements
    chapter_7_fire_protection.json
    chapter_10_egress.json        # Occupant load, travel distance, exit width
    chapter_11_accessibility.json
    tables/
      table_601.json              # Fire-resistance rating requirements
      table_1004_5.json           # Maximum floor area allowances per occupant
  irc/
    ...
  ipc/
    ...
  nfpa/
    nfpa101_life_safety.json
    nfpa13_sprinklers.json
  state_amendments/
    florida.json
    california_title24.json
    new_york.json
```

Each file would contain:
- Section number and heading
- Requirement text (summarized/paraphrased to avoid copyright issues)
- Key values (distances, ratings, areas, loads)
- Cross-references to related sections
- Tables as structured data (JSON)
- Common interpretations and application notes

### Implementation Phases

**Phase 1 (2-3 weeks):** Knowledge Base MCP Server
- Structure existing knowledge files into JSON format
- Build MCP server with `get_code_requirement`, `get_occupancy_requirements`, `lookup_code_table`
- Test with common code queries from RevitMCPBridge workflows

**Phase 2 (1-2 weeks):** Adoption Database Integration
- Register for ICC Code Adoption Database API credentials
- Implement `check_jurisdiction_adoption` tool
- Cache adoption data locally (changes infrequently)

**Phase 3 (timeline depends on ICC relationship):** Code Connect API Integration
- Contact ICC (Phil Anthony) to discuss API access and pricing
- Negotiate developer/startup pricing tier
- Implement `get_code_section` and `search_code` tools
- Build caching layer to minimize API calls

**Phase 4 (ongoing):** Content Expansion
- Add NFPA code summaries (manually structured from free access viewer)
- Add state-specific amendment summaries
- Build cross-reference graph between codes
- Add AI-generated compliance checklists

---

## 9. Recommended Path Forward

### Immediate Actions (This Week)

1. **Contact ICC Developer Relations** -- Email Phil Anthony (panthony@iccsafe.org) to:
   - Request Code Adoption Database API credentials (this may be free or low-cost)
   - Inquire about Code Connect API pricing for a small developer/startup
   - Ask about developer sandbox/trial access
   - Mention the Revit integration angle (ICC is invested in Revit ecosystem)

2. **Audit existing RevitMCPBridge knowledge files** -- Determine which of the 113 files contain code-related content vs. Revit API documentation

3. **Prototype Tier 1 MCP server** -- Build a basic MCP server that queries a local JSON knowledge base of building code requirements

### Short-Term (1-3 Months)

4. **Structure IBC Chapter 10 (Egress)** as proof-of-concept -- this is the most frequently referenced chapter and the most amenable to structured data (occupant load tables, travel distances, exit widths)

5. **Integrate ICC Code Adoption Database** -- Once credentials are obtained, build the jurisdiction lookup tool

6. **Evaluate UpCodes Enterprise** -- Contact UpCodes sales to explore enterprise API access or data licensing (if ICC pricing is prohibitive)

### Medium-Term (3-6 Months)

7. **Negotiate ICC Code Connect API access** -- This is the strategic goal; direct code text lookup is the most valuable capability

8. **Build compliance checking logic** -- Layer rule-based checks on top of code data (e.g., "Given 500 occupants in an Assembly space, are two exits sufficient?")

9. **Add NFPA content** -- Manually structure key NFPA codes (101, 13, 72) from free access content

### What NOT to Do

- Do NOT scrape UpCodes, ICC, or NFPA websites
- Do NOT reproduce copyrighted code text verbatim in knowledge files (paraphrase and cite)
- Do NOT build on the assumption of free/open code data -- it does not exist
- Do NOT try to cover all codes at once -- start with IBC egress (Ch 10), occupancy (Ch 3), and construction type (Ch 5-6)

---

## 10. Estimated Effort

| Component | Effort | Dependencies |
|-----------|--------|-------------|
| Tier 1: Knowledge Base MCP Server | 2-3 weeks | None -- can start immediately |
| Tier 1: Structure IBC key chapters into JSON | 2-4 weeks | Manual work, requires building code expertise |
| Tier 2: ICC Adoption Database integration | 1 week | API credentials from ICC |
| Tier 3: ICC Code Connect integration | 2 weeks | Commercial license from ICC (timeline unknown) |
| NFPA content structuring | 2-3 weeks | Manual work from free access content |
| Cross-reference graph | 1-2 weeks | Requires Tier 1 content to be complete |
| AI compliance checking logic | 4-8 weeks | Requires Tier 1 + domain expertise |
| **Total to MVP (Tier 1 only)** | **4-7 weeks** | **No external dependencies** |
| **Total to full solution (Tiers 1-3)** | **3-6 months** | **ICC commercial relationship** |

### Cost Estimates

| Item | Estimated Annual Cost |
|------|----------------------|
| ICC Code Adoption Database API | $0-$1,000 (may be free for registered developers) |
| ICC Code Connect API (startup tier) | $5,000-$25,000/yr (estimate -- must negotiate) |
| ICC Digital Codes Premium (for manual research) | $1,056/yr (non-member annual) |
| UpCodes Professional (for research/verification) | ~$400/yr |
| NFPA LiNK Individual (for research) | $130/yr |
| **Total minimum (Tier 1 only)** | **~$1,600/yr** (subscriptions for manual research) |
| **Total with API access (Tiers 1-3)** | **~$7,000-$27,000/yr** |

---

## Sources

### ICC Resources
- [ICC Code Connect API](https://solutions.iccsafe.org/codeconnect)
- [ICC Code Connect API Documentation (v1.0.1)](https://api.iccsafe.org/)
- [ICC Developer Portal](https://www.iccsafe.org/developers/)
- [ICC Code Adoption Database API](https://adoptions-api.iccsafe.org/api/doc)
- [eCode360 Developer Documentation](https://developer.ecode360.com/)
- [ICC Digital Codes Pricing](https://codes.iccsafe.org/pricing)
- [ICC Digital Codes Premium Subscription Costs](https://support.iccsafe.org/ht_kb/digital-codes/what-does-a-digital-codes-premium-subscription-cost/)
- [ICC Has an API For That](https://www.forconstructionpros.com/business/news/22263203/international-code-council-icc-has-an-api-for-that)
- [ICC Code Connect API Introduction (ASPE Pipeline)](https://aspe.org/pipeline/international-code-council-introduces-icc-code-connect-api/)
- [ICC Revit Add-In Announcement](https://aspe.org/pipeline/international-code-council-releases-new-revit-add-in-to-help-the-design-community-streamline-schematic-design-workflows/)
- [ICC Digital Codes Premium Enterprise](https://solutions.iccsafe.org/premium-enterprise)
- [ICC Digital Codes Premium 2026 Revit Add-In](https://apps.autodesk.com/RVT/en/Detail/Index?id=8082282703133651215&appLang=en&os=Win64)

### UpCodes Resources
- [UpCodes Platform](https://up.codes/)
- [UpCodes Code Library](https://up.codes/features/code-library)
- [UpCodes Copilot (AI)](https://up.codes/features/ai)
- [UpCodes Pricing](https://up.codes/pricing)
- [UpCodes GitHub](https://github.com/upcodes)
- [UpCodes on Y Combinator](https://www.ycombinator.com/companies/upcodes)

### NFPA Resources
- [NFPA Codes and Standards](https://www.nfpa.org/for-professionals/codes-and-standards)
- [NFPA LiNK](https://link.nfpa.org/)
- [NFPA Free Access](https://www.nfpa.org/for-professionals/codes-and-standards/free-access)
- [NFPA LiNK Pricing Update (March 2025)](https://www.nfpa.org/customer-support/why-is-nfpa-link-increasing-the-subscription-cost)

### AI Compliance Tools
- [Archistar AI PreCheck](https://www.archistar.ai/aiprecheck/)
- [ICC-Archistar Collaboration Announcement](https://www.iccsafe.org/about/periodicals-and-newsroom/international-code-council-collaborates-with-archistar-to-modernize-permitting-and-accelerate-housing-development/)
- [CodeComply.AI](https://codecomply.ai/)
- [CivCheck (acquired by Clariti)](https://www.civcheck.ai/)
- [Permitify (YC W25)](https://www.ycombinator.com/companies/permitify)
- [Blitz AI](https://blitzpermits.ai/)

### Legal References
- [Georgia v. Public.Resource.Org, Inc. (2020) -- Supreme Court](https://www.law.cornell.edu/supremecourt/text/18-1150)
- [ICC v. UpCodes -- Construction Dive Coverage](https://www.constructiondive.com/news/icc-v-upcodes-can-a-private-organization-copyright-the-law/558723/)
- [Court Decision Favoring UpCodes -- TechCrunch](https://techcrunch.com/2020/11/16/a-court-decision-in-favor-of-startup-upcodes-may-help-shape-open-access-to-the-law/)
- [UpCodes Free Law Page](https://up.codes/free-law)
- [Code Developers Battle Over Access -- Facilities Dive](https://www.facilitiesdive.com/news/code-developers-battle-each-other-and-third-parties-over-access-to-thei/761317/)

### Open Standards
- [buildingSMART BCF-XML](https://github.com/buildingSMART/BCF-XML)
- [buildingSMART IDS (Information Delivery Specification)](https://github.com/buildingSMART/IDS)
- [IFC Standard](https://standards.buildingsmart.org/IFC/RELEASE/IFC4_3/HTML/content/scope.htm)

### State Code Resources
- [Florida Building Code Online](https://www.floridabuilding.org/)
- [California Building Standards Commission](https://www.dgs.ca.gov/BSC)
- [NYC Open Data API Portal](https://api-portal.nyc.gov/)

### GovPilot/Partners
- [GovPilot ICC Integration](https://www.govpilot.com/blog/govpilot-beefs-up-digital-building-code-tools-via-icc-deal)
- [CivicPlus ICC Integration](https://www.civicplus.help/community-development/docs/international-code-council-icc-integration)

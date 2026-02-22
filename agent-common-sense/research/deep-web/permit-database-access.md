# South Florida County Permit & Property Database Access

> **Research Date:** February 21, 2026
> **Focus Area:** Miami-Dade County & Broward County, Florida
> **Purpose:** Evaluate programmatic access to county permit, planning, and property appraiser databases for AEC professional use

---

## Table of Contents

1. [Overview](#overview)
2. [Miami-Dade County](#miami-dade-county)
3. [Broward County](#broward-county)
4. [Property Appraiser Databases](#property-appraiser-databases)
5. [Existing Aggregation Services](#existing-aggregation-services)
6. [Scraping Approaches](#scraping-approaches)
7. [Custom MCP Server Design](#custom-mcp-server-design)
8. [Estimated Effort](#estimated-effort)
9. [Legal Considerations](#legal-considerations)
10. [Value Proposition for AEC](#value-proposition-for-aec)

---

## Overview

South Florida's two largest counties (Miami-Dade and Broward) each operate independent permit management systems with varying degrees of programmatic accessibility. Neither county offers a purpose-built, documented REST API for permit data. However, Miami-Dade County has a robust ArcGIS-based Open Data Hub that exposes significant data through standard ArcGIS REST endpoints. Broward County's data is less accessible, relying on legacy POSSE-based web portals with no public API.

**Key Finding:** The most viable path to programmatic access is a hybrid approach -- using Miami-Dade's ArcGIS REST services for structured data, Accela's developer API where available, and Playwright-based scraping for portals that lack APIs.

---

## Miami-Dade County

### Portal Systems

Miami-Dade County operates **multiple** permit-related systems (important distinction: the **County** systems differ from the **City of Miami** systems):

| System | URL | Purpose |
|--------|-----|---------|
| **EPS Portal** | `miamidade.gov/Apps/RER/EPSPortal` | Plan review status, application submittal |
| **EPS Advanced Search** | `miamidade.gov/Apps/RER/EPSPortal/PlanReview/AdvancedSearch` | Search by address/folio |
| **E-Permitting** | `miamidade.gov/permits/e-permitting.asp` | Contractor permit applications (unincorporated areas) |
| **Building Support Case Search** | `miamidade.gov/permits/online-services.asp` | Code enforcement cases |
| **Open Data Hub** | `gis-mdc.opendata.arcgis.com` | Downloadable datasets with API access |
| **Open Data Portal** | `opendata.miamidade.gov` | Socrata-based data portal |

**City of Miami** (separate jurisdiction):
| System | URL | Purpose |
|--------|-----|---------|
| **iBuild** | `miami.gov/Permits-Construction/iBuild-Portal-Link` | Digital permitting (City of Miami only) |
| **City Open Data** | `datahub-miamigis.opendata.arcgis.com` | City GIS datasets |
| **Developer Portal** | `miami.gov/Developer` | City API documentation |

### API Status: ArcGIS REST Services (PRIMARY ACCESS METHOD)

Miami-Dade's GIS infrastructure is hosted on ArcGIS Online under organization ID `8Pc9XBTAsYuxx9Ny`.

**Base URL:** `https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/`

#### Permit-Related Feature Services

| Service Name | Type | Description |
|-------------|------|-------------|
| `Permit_by_Polygon` | FeatureServer | Permits mapped to property boundaries |
| `EnergovCodeCasePublicView` | FeatureServer | Code enforcement cases (Energov system) |
| `EnergovCitationCasePublicView` | FeatureServer | Citation cases |
| `Open_Building_Violations` | FeatureServer | Active building code violations |
| `Closed_Building_Violations_(Past_year)` | FeatureServer | Recently closed violations |
| `Closed_Building_Violations_(Past_5_years)` | FeatureServer | Historical violations |
| `CodeComplianceViolation_Open_View` | FeatureServer | Open code compliance violations |
| `CodeComplianceViolation_Lien_View` | FeatureServer | Violations with liens |
| `LifeSafetyPermitDistricts_gdb` | FeatureServer | Life safety permit districts |

#### Property/Parcel Services

| Service Name | Type | Description |
|-------------|------|-------------|
| `Parcelpoly_gdb` | FeatureServer | Parcel boundary polygons |
| `Property2023Dec_gdb` | FeatureServer | Property records (December 2023 snapshot) |
| `CommercialProperty_gdb` | FeatureServer | Commercial property parcels |
| `Address_view` | FeatureServer | Address point data |
| `BuildingFootprintUBIDFolio_gdb` | FeatureServer | Building footprints linked to folio numbers |

#### Building Permit Point Data (Open Data Hub)

The primary building permit dataset is available through the Open Data Hub as a point feature class covering the last 3 years (~181,333 records at time of research).

**Dataset URL:** `gis-mdc.opendata.arcgis.com/datasets/MDC::building-permit`

**Available download formats:** CSV, KML, Shapefile, GeoJSON, GeoPackage, File Geodatabase, Excel

#### Building Permit Data Fields

| Field | Description |
|-------|-------------|
| `PROCNUM` | Process/permit number |
| `TYPE` | Permit type |
| `APPTYPE` | Application type |
| `STATUS` | Current permit status |
| `ADDRESS` / `STNDADDR` | Property address / Standardized address |
| `UNIT` | Unit number |
| `FOLIO` / `GEOFOLIO` | Property folio number / Geographic folio |
| `CAT1` - `CAT10` | Permit category codes (up to 10) |
| `DESC1` - `DESC10` | Category descriptions (up to 10) |
| `ISSUDATE` | Issue date |
| `LSTINSDT` | Last inspection date |
| `RENDATE` | Renewal date |
| `CCDATE` | Certificate of Completion date |
| `BLDCMPDT` | Building completion date |
| `LSTAPPRDT` | Last approval date |
| `ESTVALUE` | Estimated value |
| `PROPUSE` | Property use code |
| `CLUC` | County land use code |
| `RESCOMM` | Residential/Commercial flag |
| `ISCONDO` | Condo flag |
| `CONTRNUM` | Contractor number |
| `CONTRNAME` | Contractor name |
| `LGLDESC1` / `LGLDESC2` | Legal description |
| `MPRMTNUM` | Master permit number |

#### Energov Code Case Fields (Public View)

| Field | Type | Description |
|-------|------|-------------|
| `CASENUMBER` | String | Case reference number |
| `TYPE` | String | Case type |
| `STATUS` | String | Current status |
| `PARCELNUMBER` | String | Parcel ID |
| `DESCRIPTION` | String | Case description |
| `ADDRESSLINE1-3` | String | Full address |
| `CITY` / `STATE` / `POSTALCODE` | String | Location |
| `OPENEDDATE` | Date | Date case opened |
| `CLOSEDDATE` | Date | Date case closed |

#### Example ArcGIS REST Query

```
GET https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/EnergovCodeCasePublicView/FeatureServer/0/query
  ?where=ADDRESSLINE1 LIKE '%123 MAIN%'
  &outFields=*
  &returnGeometry=true
  &f=json
```

**Query capabilities:** pagination, statistics, ordering, distinct values, SQL expressions, spatial queries, full-text search. Max 2,000 records per request (up to 32,000 without geometry).

#### EPS Portal (No Public API)

The EPS Portal at `miamidade.gov/Apps/RER/EPSPortal` is the primary interface for searching active plan reviews and permit applications. It is an ASP.NET web application with no documented API. The Advanced Search accepts address or folio number inputs. To access this data programmatically, browser automation (Playwright) would be required to submit searches and parse results.

### Data Update Frequency

- Building permit point data: **Weekly**
- Code compliance data: Appears to be **near real-time** via Energov integration
- Property data: **Annual** snapshots (Property2023Dec_gdb)

---

## Broward County

### Portal Systems

| System | URL | Purpose |
|--------|-----|---------|
| **BCS Permit Search** | `dpepp.broward.org/BCS/` | Public permit search (POSSE backend) |
| **ePermits OneStop** | `broward.org/ePermits/` | Permit application submission |
| **GeoHub** | `geohub-bcgis.opendata.arcgis.com` | Open GIS data portal |
| **GIS Data Download** | `maint.broward.org/GISData.htm` | Shapefile downloads |
| **Accela Citizen Access** | `aca-prod.accela.com/FTL/` | City of Fort Lauderdale permits (Accela) |

### API Status

**Broward County (Unincorporated):** NO PUBLIC API. The BCS system at `dpepp.broward.org` runs on the **POSSE Licensing and Inspection** database (from 2001). This is a legacy ASP.NET WebForms application with server-side rendering. There is no REST API, no AJAX endpoints to exploit, and no open data feed for permits.

**Individual Cities in Broward:** Some cities like Fort Lauderdale use **Accela Citizen Access**, which has a well-documented developer API (see below). Other cities may have their own systems.

### Accela API (Fort Lauderdale and Other Cities)

Several Broward County municipalities use Accela's civic platform. Accela offers a comprehensive REST API:

**Base URL:** `https://apis.accela.com/v4/`

**Authentication:**
- OAuth 2.0 (Authorization Code, Implicit, or Password flows)
- Requires developer account registration at `developer.accela.com`
- Client ID and Client Secret obtained from the Developer Portal
- Agency name and environment name from Accela support
- Separate token types for agency apps vs. citizen apps

**Key API Endpoints:**
| Endpoint | Description |
|----------|-------------|
| `GET /v4/records` | Search permit records |
| `GET /v4/records/{id}` | Get specific permit details |
| `GET /v4/inspections` | List inspections |
| `GET /v4/inspections/{id}` | Get inspection details |
| `PUT /v4/inspections/{id}` | Update inspection |
| `GET /v4/settings/inspections/types/{ids}` | Get inspection type definitions |
| `GET /v4/addresses` | Search addresses |
| `GET /v4/parcels` | Search parcels |
| `GET /v4/owners` | Search property owners |

**Limitation:** Each Accela instance is agency-specific. You need separate credentials for each municipality that uses Accela. Not all endpoints may be exposed by every agency.

### Broward GeoHub

The Broward County GeoHub (`geohub-bcgis.opendata.arcgis.com`) provides GIS data layers, but the available datasets focus more on planning/zoning boundaries, infrastructure, and environmental data rather than individual permit records. Contact: `BCGIS@broward.org`

### Available Data Through BCS Portal (Scraping Required)

The BCS portal allows searching by:
- **Address** (`PossePresentation=ParcelSearchByAddress`)
- **Master Permit** (`PossePresentation=SearchForMasterPermit`)
- **Permit Number** (`PossePresentation=SearchForPermitGuest`)
- **Certificate of Use** (`PossePresentation=SearchForCertOfUse`)
- **Contractor** (by license number or name)

Data fields visible in the portal include: permit number, application type, status, address, contractor, issue date, expiration date, inspection results, and permit conditions.

---

## Property Appraiser Databases

### Miami-Dade Property Appraiser

**Website:** `miamidade.gov/Apps/PA/propertysearch/`
**Official Site:** `miamidadepa.gov`

**API Status:** No documented public REST API for live searches.

**Programmatic Access Options:**

1. **Open Data Portal** (`opendata.miamidade.gov/datasets/property-search`): Property assessment, owner, legal, and sales information available as a dataset. Likely accessible via ArcGIS REST or Socrata API.

2. **ArcGIS Feature Services:**
   - `Property2023Dec_gdb/FeatureServer/0` -- Property records (annual snapshot)
   - Fields: `PID`, `FOLIO`, `TTRRSS`, `CONDOFLG`, `SUBCODE`, `PARCEL`, `PARCEL_STRAP`
   - Note: This appears to be parcel geometry with limited attributes, not the full property appraiser dataset

3. **Bulk Data Files:** Available at $50/file from `PADataRequest@miamidadepa.gov`. Custom requests may cost more and take weeks.

4. **Comparable Sales Tool:** Online tool for comparing sale information, no API.

5. **Online Property Search:** The web interface at `miamidade.gov/Apps/PA/propertysearch/` provides comprehensive data but no documented API. Would require Playwright scraping.

**Available Data (via web interface):**
- Property ownership (current and historical)
- Assessed values (land, building, total)
- Exemptions
- Sales history
- Building characteristics (year built, sq ft, bedrooms, bathrooms, etc.)
- Legal description
- Zoning
- Tax roll data
- Aerial photographs

### Broward County Property Appraiser (BCPA)

**Website:** `bcpa.net` / `web.bcpa.net/BcpaClient/`
**Contact:** Marty Kiar, (954) 357-6830

**API Status:** No public API documented.

**Programmatic Access Options:**

1. **Web Search Tool** (`web.bcpa.net/BcpaClient/`): Search by owner name, address, or folio number. No API -- scraping required.

2. **BCPA Web Map** (`gisweb-adapters.bcpa.net/bcpawebmap_ex/bcpawebmap.aspx`): Interactive GIS map with parcel data. May expose ArcGIS REST endpoints.

3. **Records Menu** (`bcpa.net/RecMenu.asp`): Various record lookup tools, all web-based.

4. **GeoHub** (`geohub-bcgis.opendata.arcgis.com`): Some parcel data may be available as open data layers.

**Available Data (via web interface):**
- Ownership history
- Assessed values
- Exemptions
- Tax bills and payment status
- Property characteristics
- Sale dates and prices
- Parcel boundaries

---

## Existing Aggregation Services

### Shovels.ai (RECOMMENDED)

**Website:** `shovels.ai`
**API:** `docs.shovels.ai/api-reference/`

**Coverage:** 85% of US population, all 48 continental states, 180 million building permits across 30 million addresses, 3 million contractor profiles.

**Data Available:**
- Permit search by value, type, status, property characteristics
- Work type filtering (roofing, HVAC, solar, etc.)
- Contractor intelligence (specialties, license types, work history)
- Geographic search (zip code, city, county, custom area via geo_id)
- Property details (sq ft, year built, property type)
- Market analytics (permit volumes and values by geography)

**Pricing:** Flexible tiers, contact `sales@shovels.ai` for enterprise pricing. Free trial available.

**Pros:** Modern REST API, developer-friendly, good coverage, standardized data
**Cons:** Pricing not transparent, may not have hyperlocal South Florida depth

### BuildZoom / BuildZoom Data

**Website:** `buildzoom.com` / `buildzoomdata.com` / `buildingpermitdata.org`

**Coverage:** 350+ million permits spanning 25+ years, 2,400 jurisdictions covering 90% of US population, 6M+ licensed contractors.

**Data Available:**
- Permit history by address, zip code, state, metro area
- Contractor license information
- Customer reviews
- Contact information
- National Building Permit Database

**API:** Available, contact `partnerships@buildzoom.com` for access.

**Pricing:** Not publicly listed, enterprise pricing model.

### BuildFax (Verisk)

**Website:** `buildfax.com`

**Coverage:** Nationwide building permit and property condition data. Now owned by Verisk.

**Data Available:**
- Permit history
- Property condition intelligence
- Renovation and improvement tracking
- Risk assessment data

**API:** Available, primarily for insurance and appraisal industry integrations.

**Pricing:** Enterprise, contact sales.

### Regrid

**Website:** `regrid.com`

**Coverage:** Nationwide parcel data, including Broward County.

**Data Available:**
- Parcel boundaries
- Owner information
- Assessed values
- Zoning
- Export as shapefile, spreadsheet, or KML

**API:** Available for parcel data.

### Third-Party Florida License Lookup

**Contractor-Verify** (`contractor-verify.com`): API access to 365,000+ Florida contractor licenses from DBPR. Free account, GET request API.

**Apify DBPR Scraper:** Pre-built scraper for MyFloridaLicense.com data.

### Open Standards

**BLDS (Building & Land Development Specification):** Open data standard for building permits. Adopted by some municipalities including Tampa, FL. Miami-Dade and Broward have NOT adopted BLDS.

**OpenPermit:** API specification for standardized permit data access. Limited adoption.

---

## Scraping Approaches

### When Scraping Is Needed

| Data Source | API Available? | Scraping Needed? |
|------------|---------------|------------------|
| Miami-Dade ArcGIS layers | YES | No |
| Miami-Dade EPS Portal | NO | YES |
| Miami-Dade Property Appraiser web search | NO | YES |
| Broward BCS Permit Portal | NO | YES |
| Broward Property Appraiser (BCPA) | NO | YES |
| Accela cities (Ft. Lauderdale) | YES (with credentials) | No |
| DBPR License Lookup | Third-party API | Maybe |

### Recommended Tool: Playwright (Python)

Playwright is the recommended tool for scraping government portals in 2025-2026 for the following reasons:

- **Full browser rendering** -- handles JavaScript-heavy ASP.NET WebForms (POSSE, EPS Portal)
- **Async support** -- efficient for batching multiple searches
- **Stealth mode** -- less likely to be blocked than raw HTTP requests
- **Multi-browser** -- Chromium, Firefox, WebKit
- **Built-in waits** -- handles dynamic content loading
- **Python integration** -- easy to wrap in an MCP server

### Scraping Strategy by Portal

**Miami-Dade EPS Portal:**
```
1. Navigate to Advanced Search page
2. Fill address or folio field
3. Submit form, wait for results table
4. Parse result rows (permit number, type, status, dates)
5. Optionally click into each result for full detail
```

**Broward BCS Portal (POSSE):**
```
1. Navigate to ParcelSearchByAddress
2. Fill street number, name, type
3. Submit, wait for POSSE response
4. Parse permit list
5. Click each permit for inspection history
```

**Property Appraiser Sites:**
```
1. Navigate to property search page
2. Enter folio number or address
3. Parse property details (values, owner, characteristics)
4. Navigate to sales history tab
5. Parse historical sales data
```

### Rate Limiting Best Practices

- **Minimum delay:** 2-5 seconds between requests (simulate human behavior)
- **Exponential backoff:** On HTTP 429 or timeout, wait `base_delay * 2^attempt * random(0.5, 1.5)`
- **Session rotation:** Rotate user agents; optionally use residential proxies
- **Respect robots.txt:** Check each portal's robots.txt before scraping
- **Off-peak hours:** Run bulk scrapes during overnight hours (11 PM - 6 AM ET)
- **Caching:** Cache results aggressively; permit data changes slowly
- **Error handling:** Graceful degradation when portals are down or under maintenance

---

## Custom MCP Server Design

### Proposed Architecture

```
south-florida-permits-mcp/
  src/
    server.py              # MCP server entry point
    tools/
      permits.py           # Permit search tools
      property.py          # Property data tools
      contractors.py       # Contractor/license tools
      violations.py        # Code violations tools
    providers/
      arcgis.py            # Miami-Dade ArcGIS REST client
      accela.py            # Accela API client (Ft. Lauderdale)
      scraper_eps.py       # Miami-Dade EPS Portal scraper
      scraper_bcs.py       # Broward BCS Portal scraper
      scraper_pa_mdc.py    # Miami-Dade Property Appraiser scraper
      scraper_pa_bcpa.py   # Broward Property Appraiser scraper
      shovels.py           # Shovels.ai API client (optional)
    cache/
      cache_manager.py     # Redis or SQLite caching layer
    config.py              # API keys, rate limits, timeouts
  tests/
  pyproject.toml
```

### Proposed MCP Tools

#### Permit Tools

```python
@tool
def search_permits(
    address: str = None,
    folio: str = None,
    permit_number: str = None,
    county: str = "miami-dade",  # "miami-dade" | "broward"
    status: str = None,          # "open" | "closed" | "all"
    date_from: str = None,       # ISO date
    date_to: str = None,
    permit_type: str = None      # "building" | "electrical" | "plumbing" | "mechanical"
) -> list[PermitRecord]:
    """Search building permits across South Florida counties."""

@tool
def get_permit_details(
    permit_number: str,
    county: str = "miami-dade"
) -> PermitDetail:
    """Get full details for a specific permit including inspection history."""

@tool
def get_permit_inspections(
    permit_number: str,
    county: str = "miami-dade"
) -> list[InspectionRecord]:
    """Get inspection history and results for a permit."""

@tool
def get_permits_by_contractor(
    contractor_name: str = None,
    contractor_number: str = None,
    county: str = "miami-dade"
) -> list[PermitRecord]:
    """Find all permits associated with a contractor."""
```

#### Property Tools

```python
@tool
def search_property(
    address: str = None,
    folio: str = None,
    owner_name: str = None,
    county: str = "miami-dade"
) -> PropertyRecord:
    """Search property records including assessed values, ownership, and building characteristics."""

@tool
def get_property_sales_history(
    folio: str,
    county: str = "miami-dade"
) -> list[SaleRecord]:
    """Get historical sales data for a property."""

@tool
def get_property_permits(
    folio: str,
    county: str = "miami-dade"
) -> list[PermitRecord]:
    """Get all permits ever pulled for a property (combines permit + property data)."""

@tool
def search_properties_in_area(
    latitude: float,
    longitude: float,
    radius_miles: float = 0.5,
    property_type: str = None,  # "residential" | "commercial" | "industrial"
    min_value: float = None,
    max_value: float = None
) -> list[PropertySummary]:
    """Search properties within a geographic radius."""
```

#### Code Violation Tools

```python
@tool
def search_violations(
    address: str = None,
    folio: str = None,
    status: str = "open",  # "open" | "closed" | "lien" | "all"
    county: str = "miami-dade"
) -> list[ViolationRecord]:
    """Search code compliance violations."""

@tool
def get_violation_details(
    case_number: str,
    county: str = "miami-dade"
) -> ViolationDetail:
    """Get full details of a code violation case."""
```

#### Contractor Tools

```python
@tool
def verify_contractor_license(
    license_number: str = None,
    contractor_name: str = None,
    state: str = "FL"
) -> ContractorLicense:
    """Verify a contractor's license status via DBPR."""

@tool
def get_contractor_permit_history(
    contractor_name: str = None,
    contractor_number: str = None,
    county: str = "miami-dade"
) -> ContractorProfile:
    """Get a contractor's permit history and project portfolio."""
```

#### Market Intelligence Tools

```python
@tool
def get_permit_activity_summary(
    zip_code: str = None,
    city: str = None,
    county: str = "miami-dade",
    period_months: int = 12
) -> MarketSummary:
    """Get permit activity summary for an area (volume, values, types)."""

@tool
def find_recent_large_projects(
    county: str = "miami-dade",
    min_value: float = 1000000,
    limit: int = 20
) -> list[PermitRecord]:
    """Find recently permitted large construction projects."""

@tool
def track_development_pipeline(
    address: str = None,
    neighborhood: str = None,
    county: str = "miami-dade"
) -> DevelopmentPipeline:
    """Track active development projects near a location."""
```

### Data Flow

```
User Query (via Claude)
    |
    v
MCP Tool Handler
    |
    +---> ArcGIS REST (Miami-Dade permits, violations, parcels)
    |        Direct HTTP GET, JSON response, no auth needed
    |
    +---> Accela API (Ft. Lauderdale and other Accela cities)
    |        OAuth 2.0 auth, JSON response
    |
    +---> Playwright Scraper (EPS Portal, BCS Portal, Property Appraisers)
    |        Browser automation, HTML parsing
    |
    +---> Shovels.ai API (fallback/supplemental)
    |        API key auth, JSON response
    |
    +---> SQLite Cache
             Cache results for 24h (permits) / 7d (property)
```

---

## Estimated Effort

### Phase 1: ArcGIS Integration (1-2 weeks)
- Build ArcGIS REST client for Miami-Dade
- Wrap permit, violation, and property feature services
- Implement query builder with spatial/attribute filtering
- Build caching layer
- **Difficulty:** Low -- well-documented standard REST API

### Phase 2: Scraper Development (3-4 weeks)
- Miami-Dade EPS Portal scraper (1 week)
- Broward BCS Portal scraper (1 week)
- Miami-Dade Property Appraiser scraper (0.5 week)
- Broward BCPA scraper (0.5 week)
- Error handling, retry logic, rate limiting (0.5 week)
- **Difficulty:** Medium -- ASP.NET WebForms are tricky, POSSE is legacy

### Phase 3: Accela Integration (1 week)
- Register developer account
- Implement OAuth flow
- Build records/inspections client
- **Difficulty:** Low-Medium -- good API docs but agency-specific config

### Phase 4: MCP Server Shell (1 week)
- Set up MCP server with tool definitions
- Route requests to appropriate providers
- Normalize response formats
- Add error handling and logging

### Phase 5: Testing & Hardening (1-2 weeks)
- End-to-end testing with real queries
- Handle edge cases (missing data, portal downtime)
- Performance optimization
- Documentation

### Total Estimated Effort: 7-10 weeks for a single developer

### Optional Phase 6: Shovels.ai Integration (0.5 week)
- As supplemental/fallback data source
- Useful for historical data and national coverage

---

## Legal Considerations

### Florida Public Records Act (Chapter 119, F.S.)

Florida has one of the strongest public records laws in the United States:

- **Constitutional right:** Article I, Section 24 of the Florida Constitution establishes that "every person has the right to inspect or copy any public record"
- **Broad scope:** All records made or received in connection with official business of any public body, officer, or employee
- **Presumption of openness:** All records are presumed public; exemptions must be explicitly created by statute
- **Enforcement:** If an agency unlawfully refuses access, courts can award attorney's fees

### Implications for Programmatic Access

1. **Building permit data is public record.** All permit applications, statuses, inspection results, and contractor information are public records under Florida law.

2. **Property appraiser data is public record.** Assessed values, ownership, sales history, and building characteristics are all public.

3. **No prohibition on automated access.** Florida law does not distinguish between manual and automated retrieval of public records. However, some portals may have Terms of Service that restrict automated access.

4. **Web scraping of public government data is generally legal.** The landmark *hiQ Labs v. LinkedIn* (2022) case established that scraping publicly accessible data does not violate the CFAA. Government data portals serving public records have an even stronger case for legal access.

5. **Exemptions exist but are narrow.** Over 1,000 exemptions exist in Chapter 119, but they primarily cover:
   - Ongoing criminal investigations
   - Personnel/medical records
   - Security system plans
   - Social Security numbers (partially exempt)
   - Homestead exemption applicant details

6. **Best practice: Be transparent.** If challenged, you can file a formal public records request and reference your right under Chapter 119.

### Practical Recommendations

- Check each portal's robots.txt and Terms of Service
- Implement respectful rate limiting (2-5 second delays)
- Cache aggressively to minimize repeated requests
- Do not bypass authentication mechanisms
- Do not access non-public endpoints
- Consider filing formal data requests for bulk historical data
- Keep logs of all automated access for legal compliance

---

## Value Proposition for AEC

### Questions Agents Could Answer

**For Architects:**
- "What permits have been pulled at 123 Main St? Has there been any previous construction?"
- "Show me all permits for commercial projects over $5M in Brickell in the last 2 years"
- "What's the zoning and land use classification for this parcel?"
- "Are there any open code violations at this property?"
- "What's the history of building modifications at this address?"

**For Contractors:**
- "Is contractor XYZ properly licensed? What's their permit history?"
- "What competitors are active in Broward County for commercial renovation work?"
- "How many permits has [competitor] pulled this year?"
- "Show me all open permits in [zip code] for HVAC work"

**For Developers/Investors:**
- "What's the development pipeline in Wynwood? Show me all permits over $1M in the last 6 months"
- "Track new construction permits in Aventura -- what's being built?"
- "What's the assessed value trend for properties on this block?"
- "Who owns the parcels adjacent to my site?"
- "What permits has the current owner pulled? Any renovation history?"

**For Project Managers:**
- "What's the current status of permit #2024-12345?"
- "Have all inspections passed for our project at 456 Ocean Drive?"
- "When was the last inspection and what was the result?"
- "Is our Certificate of Completion on record?"

### Market Intelligence Use Cases

1. **Competitor tracking:** Monitor which contractors are pulling permits, where, and for what project types
2. **Development trend analysis:** Track permit volumes by neighborhood, type, and value to identify hot markets
3. **Site due diligence:** Before designing, research full permit and violation history of a property
4. **Client verification:** Verify project status claims from clients or partners
5. **Lead generation:** Identify properties with expired permits, open violations, or aging infrastructure
6. **Bid intelligence:** Find upcoming projects early in the permit pipeline
7. **Risk assessment:** Check for code violations, liens, and compliance issues before acquisition

### Competitive Advantage

No existing tool combines South Florida permit data, property appraiser data, contractor licensing, and code violations into a single AI-accessible interface. Building this MCP server would create a significant competitive advantage for any AEC firm operating in the Miami-Dade/Broward market.

---

## Key URLs and Resources

### Miami-Dade County
- Open Data Hub: https://gis-mdc.opendata.arcgis.com/
- Open Data Portal: https://opendata.miamidade.gov/
- ArcGIS Services Directory: https://services.arcgis.com/8Pc9XBTAsYuxx9Ny/arcgis/rest/services/
- EPS Portal: https://www.miamidade.gov/Apps/RER/EPSPortal
- Property Appraiser: https://www.miamidade.gov/Apps/PA/propertysearch/
- Building Permit Dataset: https://gis-mdc.opendata.arcgis.com/datasets/MDC::building-permit
- GIS Contact: gis@miamidade.gov
- PA Data Requests: PADataRequest@miamidadepa.gov

### Broward County
- BCS Permit Search: https://dpepp.broward.org/BCS/
- ePermits OneStop: https://www.broward.org/ePermits/
- GeoHub: https://geohub-bcgis.opendata.arcgis.com/
- Property Appraiser: https://web.bcpa.net/BcpaClient/
- BCPA Web Map: https://gisweb-adapters.bcpa.net/bcpawebmap_ex/bcpawebmap.aspx
- GIS Contact: BCGIS@broward.org

### City of Miami (Separate from County)
- Open Data GIS: https://datahub-miamigis.opendata.arcgis.com/
- Building Permits Since 2014: https://datahub-miamigis.opendata.arcgis.com/datasets/building-permits-since-2014
- Developer Portal: https://www.miami.gov/Developer

### APIs and Developer Resources
- Accela Developer Portal: https://developer.accela.com/
- Accela API Reference: https://developer.accela.com/docs/api_reference/api-index.html
- ArcGIS REST API Docs: https://developers.arcgis.com/rest/
- Shovels.ai API: https://docs.shovels.ai/api-reference/
- Contractor-Verify API: https://contractor-verify.com/
- BLDS Data Spec: https://permitdata.org/
- OpenPermit Spec: http://www.openpermit.org/api.html

### Aggregation Services
- Shovels.ai: https://www.shovels.ai/
- BuildZoom Data: https://www.buildzoomdata.com/
- BuildFax: https://www.buildfax.com/
- Regrid: https://app.regrid.com/
- DBPR License Search: https://www.myfloridalicense.com/wl11.asp

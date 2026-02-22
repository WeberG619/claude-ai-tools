#!/usr/bin/env python3
"""
Academic Research MCP Server - Literature Discovery & Analysis

Data Sources:
- Semantic Scholar (paper search, citations, references, recommendations)
- arXiv (preprint search, category browsing)

Tools:
1. search_papers - Search Semantic Scholar for papers by keyword/topic
2. get_paper_details - Get full details of a specific paper
3. search_arxiv - Search arXiv for preprints
4. get_citations - Get papers that cite a given paper
5. get_references - Get papers referenced by a given paper
6. get_recommendations - Get recommended papers similar to a given paper
7. search_by_topic - Smart topic search combining both sources
"""

import json
import sys
import os
import time
import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote_plus

# MCP SDK
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

import requests

# Initialize MCP server
server = Server("research-mcp")

# ============== CONFIGURATION ==============

SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"
SEMANTIC_SCHOLAR_REC_BASE = "https://api.semanticscholar.org/recommendations/v1"
ARXIV_BASE = "http://export.arxiv.org/api/query"

# Optional API key for higher rate limits on Semantic Scholar
SEMANTIC_SCHOLAR_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")

# Rate limiting: Semantic Scholar allows 1 req/sec without API key, 10 req/sec with key
RATE_LIMIT_INTERVAL = 1.0 if not SEMANTIC_SCHOLAR_API_KEY else 0.1
_last_ss_request_time = 0.0

# Cache: 10-minute duration
_cache = {}
CACHE_DURATION = 600  # 10 minutes


# ============== HELPERS ==============

def get_cached(key, fetch_func, duration=CACHE_DURATION):
    """Simple cache to avoid redundant API calls."""
    now = datetime.now().timestamp()
    if key in _cache:
        data, timestamp = _cache[key]
        if now - timestamp < duration:
            return data
    data = fetch_func()
    _cache[key] = (data, now)
    return data


def _clean_cache():
    """Remove expired cache entries to prevent memory bloat."""
    now = datetime.now().timestamp()
    expired = [k for k, (_, ts) in _cache.items() if now - ts > CACHE_DURATION]
    for k in expired:
        del _cache[k]


def _rate_limit_ss():
    """Enforce rate limit for Semantic Scholar API."""
    global _last_ss_request_time
    now = time.time()
    elapsed = now - _last_ss_request_time
    if elapsed < RATE_LIMIT_INTERVAL:
        time.sleep(RATE_LIMIT_INTERVAL - elapsed)
    _last_ss_request_time = time.time()


def _ss_headers():
    """Get headers for Semantic Scholar requests."""
    headers = {"Accept": "application/json"}
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
    return headers


def _ss_get(url, params=None, max_retries=3):
    """Make a rate-limited GET request to Semantic Scholar with retry on 429."""
    for attempt in range(max_retries):
        _rate_limit_ss()
        resp = requests.get(url, params=params, headers=_ss_headers(), timeout=30)
        if resp.status_code == 429 and attempt < max_retries - 1:
            # Exponential backoff: 2s, 4s, 8s...
            wait = 2 ** (attempt + 1)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    # Should not reach here, but just in case
    resp.raise_for_status()
    return resp.json()


def _arxiv_get(params):
    """Make a GET request to arXiv API and parse XML response."""
    resp = requests.get(ARXIV_BASE, params=params, timeout=30)
    resp.raise_for_status()
    return _parse_arxiv_xml(resp.text)


def _parse_arxiv_xml(xml_text):
    """Parse arXiv Atom XML feed into a list of paper dicts."""
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    root = ET.fromstring(xml_text)
    papers = []

    for entry in root.findall("atom:entry", ns):
        # Extract arxiv ID from the id URL
        entry_id = entry.find("atom:id", ns).text.strip()
        arxiv_id = entry_id.split("/abs/")[-1] if "/abs/" in entry_id else entry_id

        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")

        abstract = entry.find("atom:summary", ns).text.strip().replace("\n", " ")

        authors = []
        for author_el in entry.findall("atom:author", ns):
            name = author_el.find("atom:name", ns)
            if name is not None:
                authors.append(name.text.strip())

        published = entry.find("atom:published", ns).text.strip()[:10]
        updated = entry.find("atom:updated", ns).text.strip()[:10]

        # Find PDF link
        pdf_link = ""
        for link in entry.findall("atom:link", ns):
            if link.get("title") == "pdf":
                pdf_link = link.get("href", "")
                break

        # Categories
        categories = []
        primary_cat = entry.find("arxiv:primary_category", ns)
        if primary_cat is not None:
            categories.append(primary_cat.get("term", ""))
        for cat in entry.findall("atom:category", ns):
            term = cat.get("term", "")
            if term and term not in categories:
                categories.append(term)

        # DOI if present
        doi_el = entry.find("arxiv:doi", ns)
        doi = doi_el.text.strip() if doi_el is not None else ""

        # Comment (often contains page count, conference info)
        comment_el = entry.find("arxiv:comment", ns)
        comment = comment_el.text.strip() if comment_el is not None else ""

        papers.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "published": published,
            "updated": updated,
            "pdf_link": pdf_link,
            "categories": categories,
            "doi": doi,
            "comment": comment,
            "url": f"https://arxiv.org/abs/{arxiv_id}",
        })

    return papers


def _truncate(text, max_len=300):
    """Truncate text to max_len characters with ellipsis."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."


def _format_authors(authors, max_authors=5):
    """Format author list, truncating if needed."""
    if not authors:
        return "Unknown"
    if isinstance(authors[0], dict):
        names = [a.get("name", "Unknown") for a in authors]
    else:
        names = authors
    if len(names) <= max_authors:
        return ", ".join(names)
    return ", ".join(names[:max_authors]) + f" (+{len(names) - max_authors} more)"


# ============== API FUNCTIONS ==============

def search_semantic_scholar(query, limit=10, year_from=None, year_to=None):
    """Search Semantic Scholar for papers."""
    fields = "title,abstract,year,authors,citationCount,url,externalIds,venue"
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": fields,
    }

    # Year filtering
    if year_from or year_to:
        year_range = f"{year_from or ''}-{year_to or ''}"
        params["year"] = year_range

    cache_key = f"ss_search:{query}:{limit}:{year_from}:{year_to}"

    def fetch():
        return _ss_get(f"{SEMANTIC_SCHOLAR_BASE}/paper/search", params=params)

    result = get_cached(cache_key, fetch)
    return result.get("data", [])


def get_paper_details_ss(paper_id):
    """Get detailed paper information from Semantic Scholar."""
    fields = (
        "title,abstract,year,authors,references.title,references.year,"
        "references.authors,references.citationCount,citations.title,"
        "citations.year,citations.authors,citations.citationCount,"
        "citationCount,url,venue,externalIds,tldr,fieldsOfStudy,"
        "publicationTypes,publicationDate,influentialCitationCount"
    )
    cache_key = f"ss_paper:{paper_id}"

    def fetch():
        return _ss_get(f"{SEMANTIC_SCHOLAR_BASE}/paper/{paper_id}", params={"fields": fields})

    return get_cached(cache_key, fetch)


def get_paper_citations_ss(paper_id, limit=20):
    """Get papers that cite a given paper."""
    fields = "title,year,authors,citationCount,url,abstract,venue"
    cache_key = f"ss_citations:{paper_id}:{limit}"

    def fetch():
        return _ss_get(
            f"{SEMANTIC_SCHOLAR_BASE}/paper/{paper_id}/citations",
            params={"fields": fields, "limit": min(limit, 1000)},
        )

    result = get_cached(cache_key, fetch)
    return result.get("data", [])


def get_paper_references_ss(paper_id, limit=20):
    """Get papers referenced by a given paper."""
    fields = "title,year,authors,citationCount,url,abstract,venue"
    cache_key = f"ss_references:{paper_id}:{limit}"

    def fetch():
        return _ss_get(
            f"{SEMANTIC_SCHOLAR_BASE}/paper/{paper_id}/references",
            params={"fields": fields, "limit": min(limit, 1000)},
        )

    result = get_cached(cache_key, fetch)
    return result.get("data", [])


def get_recommendations_ss(paper_id, limit=10):
    """Get recommended papers similar to a given paper."""
    fields = "title,year,authors,citationCount,url,abstract,venue,externalIds"
    cache_key = f"ss_recs:{paper_id}:{limit}"

    def fetch():
        _rate_limit_ss()
        resp = requests.get(
            f"{SEMANTIC_SCHOLAR_REC_BASE}/papers/forpaper/{paper_id}",
            params={"fields": fields, "limit": min(limit, 500)},
            headers=_ss_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    result = get_cached(cache_key, fetch)
    return result.get("recommendedPapers", [])


def search_arxiv_api(query, category=None, max_results=10, sort_by="relevance"):
    """Search arXiv for preprints."""
    # Build search query
    search_parts = []
    if category:
        search_parts.append(f"cat:{category}")
    if query:
        search_parts.append(f"all:{query}")
    search_query = " AND ".join(search_parts) if search_parts else query

    sort_map = {
        "relevance": "relevance",
        "date": "lastUpdatedDate",
        "submitted": "submittedDate",
    }
    sort_by_param = sort_map.get(sort_by, "relevance")

    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": min(max_results, 100),
        "sortBy": sort_by_param,
        "sortOrder": "descending",
    }

    cache_key = f"arxiv:{search_query}:{max_results}:{sort_by}"

    def fetch():
        return _arxiv_get(params)

    return get_cached(cache_key, fetch)


# ============== TOOL DEFINITIONS ==============

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available research tools."""
    return [
        Tool(
            name="search_papers",
            description="Search Semantic Scholar for academic papers by keyword/topic. Returns papers with title, authors, year, citation count, and abstract snippet.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (keywords, paper title, or topic)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of results to return (default 10, max 100)",
                        "default": 10,
                    },
                    "year_from": {
                        "type": "integer",
                        "description": "Filter papers published from this year onward (optional)",
                    },
                    "year_to": {
                        "type": "integer",
                        "description": "Filter papers published up to this year (optional)",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_paper_details",
            description="Get full details of a specific paper including abstract, authors, TLDR, references count, citations count, fields of study. Accepts Semantic Scholar paper ID, DOI, or arXiv ID (prefixed with 'ARXIV:').",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Semantic Scholar paper ID, DOI (e.g. '10.1234/...'), or arXiv ID (e.g. 'ARXIV:2301.00001')",
                    },
                },
                "required": ["paper_id"],
            },
        ),
        Tool(
            name="search_arxiv",
            description="Search arXiv for preprints. Supports category filtering (e.g. cs.CV, cs.AI, physics.hep-th) and sorting by relevance or date.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (supports arXiv search syntax: all:term, ti:term, au:author, abs:abstract, cat:category)",
                    },
                    "category": {
                        "type": "string",
                        "description": "arXiv category filter (e.g. 'cs.CV', 'cs.AI', 'cs.LG', 'physics.hep-th', 'math.AG')",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Number of results to return (default 10, max 100)",
                        "default": 10,
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sort order: 'relevance', 'date', or 'submitted' (default 'relevance')",
                        "enum": ["relevance", "date", "submitted"],
                        "default": "relevance",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_citations",
            description="Get papers that cite a given paper. Useful for finding follow-up work and seeing how a paper has been used.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Semantic Scholar paper ID, DOI, or arXiv ID (e.g. 'ARXIV:2301.00001')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of citing papers to return (default 20, max 1000)",
                        "default": 20,
                    },
                },
                "required": ["paper_id"],
            },
        ),
        Tool(
            name="get_references",
            description="Get papers referenced by a given paper. Useful for understanding a paper's foundation and related prior work.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Semantic Scholar paper ID, DOI, or arXiv ID (e.g. 'ARXIV:2301.00001')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of referenced papers to return (default 20, max 1000)",
                        "default": 20,
                    },
                },
                "required": ["paper_id"],
            },
        ),
        Tool(
            name="get_recommendations",
            description="Get recommended papers similar to a given paper. Uses Semantic Scholar's recommendation engine to find related work.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Semantic Scholar paper ID, DOI, or arXiv ID (e.g. 'ARXIV:2301.00001')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of recommendations to return (default 10, max 500)",
                        "default": 10,
                    },
                },
                "required": ["paper_id"],
            },
        ),
        Tool(
            name="search_by_topic",
            description="Smart topic search combining Semantic Scholar and arXiv results. Deduplicates by title similarity and returns a comprehensive view of the topic.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Research topic or keywords to search for",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Max results per source (default 10, combined results may be up to 2x this)",
                        "default": 10,
                    },
                },
                "required": ["topic"],
            },
        ),
    ]


# ============== TOOL EXECUTION ==============

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute research tools."""

    # Clean expired cache entries periodically
    _clean_cache()

    try:
        # === SEARCH PAPERS (Semantic Scholar) ===
        if name == "search_papers":
            query = arguments["query"]
            limit = arguments.get("limit", 10)
            year_from = arguments.get("year_from")
            year_to = arguments.get("year_to")

            papers = search_semantic_scholar(query, limit, year_from, year_to)

            if not papers:
                return [TextContent(type="text", text=f"No papers found for query: '{query}'")]

            results = []
            for i, paper in enumerate(papers, 1):
                entry = {
                    "rank": i,
                    "title": paper.get("title", "Untitled"),
                    "authors": _format_authors(paper.get("authors", [])),
                    "year": paper.get("year"),
                    "citations": paper.get("citationCount", 0),
                    "venue": paper.get("venue", ""),
                    "abstract_snippet": _truncate(paper.get("abstract", ""), 250),
                    "paper_id": paper.get("paperId", ""),
                    "url": paper.get("url", ""),
                    "external_ids": paper.get("externalIds", {}),
                }
                results.append(entry)

            output = {
                "query": query,
                "total_results": len(results),
                "filters": {},
                "papers": results,
            }
            if year_from:
                output["filters"]["year_from"] = year_from
            if year_to:
                output["filters"]["year_to"] = year_to

            return [TextContent(type="text", text=json.dumps(output, indent=2))]

        # === GET PAPER DETAILS ===
        elif name == "get_paper_details":
            paper_id = arguments["paper_id"]

            paper = get_paper_details_ss(paper_id)

            if not paper:
                return [TextContent(type="text", text=f"Paper not found: {paper_id}")]

            # Build TLDR summary
            tldr = ""
            if paper.get("tldr"):
                tldr = paper["tldr"].get("text", "")

            # Count refs and citations
            refs = paper.get("references", [])
            cites = paper.get("citations", [])

            result = {
                "title": paper.get("title", "Untitled"),
                "authors": _format_authors(paper.get("authors", []), max_authors=10),
                "year": paper.get("year"),
                "venue": paper.get("venue", ""),
                "publication_date": paper.get("publicationDate"),
                "citation_count": paper.get("citationCount", 0),
                "influential_citation_count": paper.get("influentialCitationCount", 0),
                "references_count": len(refs) if refs else 0,
                "abstract": paper.get("abstract", "No abstract available"),
                "tldr": tldr,
                "fields_of_study": paper.get("fieldsOfStudy", []),
                "publication_types": paper.get("publicationTypes", []),
                "url": paper.get("url", ""),
                "external_ids": paper.get("externalIds", {}),
                "paper_id": paper.get("paperId", ""),
            }

            # Include top cited references
            if refs:
                sorted_refs = sorted(
                    [r for r in refs if r.get("title")],
                    key=lambda x: x.get("citationCount", 0) or 0,
                    reverse=True,
                )[:5]
                result["top_references"] = [
                    {
                        "title": r.get("title", ""),
                        "year": r.get("year"),
                        "citations": r.get("citationCount", 0),
                    }
                    for r in sorted_refs
                ]

            # Include top citing papers
            if cites:
                sorted_cites = sorted(
                    [c for c in cites if c.get("title")],
                    key=lambda x: x.get("citationCount", 0) or 0,
                    reverse=True,
                )[:5]
                result["top_citing_papers"] = [
                    {
                        "title": c.get("title", ""),
                        "year": c.get("year"),
                        "citations": c.get("citationCount", 0),
                    }
                    for c in sorted_cites
                ]

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        # === SEARCH ARXIV ===
        elif name == "search_arxiv":
            query = arguments["query"]
            category = arguments.get("category")
            max_results = arguments.get("max_results", 10)
            sort_by = arguments.get("sort_by", "relevance")

            papers = search_arxiv_api(query, category, max_results, sort_by)

            if not papers:
                return [TextContent(type="text", text=f"No arXiv papers found for query: '{query}'")]

            results = []
            for i, paper in enumerate(papers, 1):
                entry = {
                    "rank": i,
                    "title": paper["title"],
                    "authors": _format_authors(paper["authors"]),
                    "abstract_snippet": _truncate(paper["abstract"], 250),
                    "arxiv_id": paper["arxiv_id"],
                    "published": paper["published"],
                    "updated": paper["updated"],
                    "categories": paper["categories"],
                    "pdf_link": paper["pdf_link"],
                    "url": paper["url"],
                    "doi": paper["doi"],
                    "comment": paper["comment"],
                }
                results.append(entry)

            output = {
                "query": query,
                "category_filter": category,
                "sort_by": sort_by,
                "total_results": len(results),
                "papers": results,
            }

            return [TextContent(type="text", text=json.dumps(output, indent=2))]

        # === GET CITATIONS ===
        elif name == "get_citations":
            paper_id = arguments["paper_id"]
            limit = arguments.get("limit", 20)

            citations_data = get_paper_citations_ss(paper_id, limit)

            if not citations_data:
                return [TextContent(type="text", text=f"No citations found for paper: {paper_id}")]

            results = []
            for i, item in enumerate(citations_data[:limit], 1):
                citing_paper = item.get("citingPaper", {})
                if not citing_paper.get("title"):
                    continue
                entry = {
                    "rank": i,
                    "title": citing_paper.get("title", "Untitled"),
                    "authors": _format_authors(citing_paper.get("authors", [])),
                    "year": citing_paper.get("year"),
                    "citations": citing_paper.get("citationCount", 0),
                    "venue": citing_paper.get("venue", ""),
                    "abstract_snippet": _truncate(citing_paper.get("abstract", ""), 200),
                    "url": citing_paper.get("url", ""),
                }
                results.append(entry)

            # Sort by citation count descending
            results.sort(key=lambda x: x.get("citations", 0) or 0, reverse=True)
            # Re-rank after sorting
            for i, r in enumerate(results, 1):
                r["rank"] = i

            output = {
                "paper_id": paper_id,
                "total_citing_papers": len(results),
                "citing_papers": results,
            }

            return [TextContent(type="text", text=json.dumps(output, indent=2))]

        # === GET REFERENCES ===
        elif name == "get_references":
            paper_id = arguments["paper_id"]
            limit = arguments.get("limit", 20)

            refs_data = get_paper_references_ss(paper_id, limit)

            if not refs_data:
                return [TextContent(type="text", text=f"No references found for paper: {paper_id}")]

            results = []
            for i, item in enumerate(refs_data[:limit], 1):
                cited_paper = item.get("citedPaper", {})
                if not cited_paper.get("title"):
                    continue
                entry = {
                    "rank": i,
                    "title": cited_paper.get("title", "Untitled"),
                    "authors": _format_authors(cited_paper.get("authors", [])),
                    "year": cited_paper.get("year"),
                    "citations": cited_paper.get("citationCount", 0),
                    "venue": cited_paper.get("venue", ""),
                    "abstract_snippet": _truncate(cited_paper.get("abstract", ""), 200),
                    "url": cited_paper.get("url", ""),
                }
                results.append(entry)

            # Sort by citation count descending
            results.sort(key=lambda x: x.get("citations", 0) or 0, reverse=True)
            for i, r in enumerate(results, 1):
                r["rank"] = i

            output = {
                "paper_id": paper_id,
                "total_references": len(results),
                "referenced_papers": results,
            }

            return [TextContent(type="text", text=json.dumps(output, indent=2))]

        # === GET RECOMMENDATIONS ===
        elif name == "get_recommendations":
            paper_id = arguments["paper_id"]
            limit = arguments.get("limit", 10)

            recs = get_recommendations_ss(paper_id, limit)

            if not recs:
                return [TextContent(type="text", text=f"No recommendations found for paper: {paper_id}")]

            results = []
            for i, paper in enumerate(recs[:limit], 1):
                entry = {
                    "rank": i,
                    "title": paper.get("title", "Untitled"),
                    "authors": _format_authors(paper.get("authors", [])),
                    "year": paper.get("year"),
                    "citations": paper.get("citationCount", 0),
                    "venue": paper.get("venue", ""),
                    "abstract_snippet": _truncate(paper.get("abstract", ""), 200),
                    "url": paper.get("url", ""),
                    "external_ids": paper.get("externalIds", {}),
                }
                results.append(entry)

            output = {
                "source_paper_id": paper_id,
                "total_recommendations": len(results),
                "recommended_papers": results,
            }

            return [TextContent(type="text", text=json.dumps(output, indent=2))]

        # === SEARCH BY TOPIC (Combined) ===
        elif name == "search_by_topic":
            topic = arguments["topic"]
            max_results = arguments.get("max_results", 10)

            # Fetch from both sources
            ss_papers = []
            arxiv_papers = []
            errors = []

            try:
                ss_papers = search_semantic_scholar(topic, max_results)
            except Exception as e:
                errors.append(f"Semantic Scholar error: {str(e)}")

            try:
                arxiv_papers = search_arxiv_api(topic, None, max_results)
            except Exception as e:
                errors.append(f"arXiv error: {str(e)}")

            if not ss_papers and not arxiv_papers:
                error_msg = f"No papers found for topic: '{topic}'"
                if errors:
                    error_msg += f"\nErrors: {'; '.join(errors)}"
                return [TextContent(type="text", text=error_msg)]

            # Normalize results into a common format
            combined = []
            seen_titles = set()

            # Process Semantic Scholar results
            for paper in ss_papers:
                title = (paper.get("title") or "Untitled").strip().lower()
                title_key = title[:80]  # use first 80 chars for dedup
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)

                arxiv_id = ""
                ext_ids = paper.get("externalIds", {})
                if ext_ids and ext_ids.get("ArXiv"):
                    arxiv_id = ext_ids["ArXiv"]

                combined.append({
                    "title": paper.get("title", "Untitled"),
                    "authors": _format_authors(paper.get("authors", [])),
                    "year": paper.get("year"),
                    "citations": paper.get("citationCount", 0),
                    "venue": paper.get("venue", ""),
                    "abstract_snippet": _truncate(paper.get("abstract", ""), 200),
                    "source": "semantic_scholar",
                    "paper_id": paper.get("paperId", ""),
                    "arxiv_id": arxiv_id,
                    "url": paper.get("url", ""),
                })

            # Process arXiv results
            for paper in arxiv_papers:
                title = paper["title"].strip().lower()
                title_key = title[:80]
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)

                combined.append({
                    "title": paper["title"],
                    "authors": _format_authors(paper["authors"]),
                    "year": int(paper["published"][:4]) if paper["published"] else None,
                    "citations": None,  # arXiv doesn't provide citation counts
                    "venue": "arXiv",
                    "abstract_snippet": _truncate(paper["abstract"], 200),
                    "source": "arxiv",
                    "paper_id": "",
                    "arxiv_id": paper["arxiv_id"],
                    "url": paper["url"],
                    "pdf_link": paper["pdf_link"],
                    "categories": paper["categories"],
                })

            # Sort: papers with citations first, then by citation count, then by year
            def sort_key(p):
                cites = p.get("citations") or 0
                year = p.get("year") or 0
                return (cites > 0, cites, year)

            combined.sort(key=sort_key, reverse=True)

            # Add rank
            for i, paper in enumerate(combined, 1):
                paper["rank"] = i

            output = {
                "topic": topic,
                "total_results": len(combined),
                "sources_queried": ["semantic_scholar", "arxiv"],
                "errors": errors if errors else None,
                "papers": combined,
            }

            return [TextContent(type="text", text=json.dumps(output, indent=2, default=str))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        if status == 429:
            return [TextContent(
                type="text",
                text=f"Rate limited by API. Please wait a moment and try again.\nDetails: {str(e)}",
            )]
        elif status == 404:
            return [TextContent(
                type="text",
                text=f"Resource not found. Check that the paper ID is correct.\nDetails: {str(e)}",
            )]
        else:
            return [TextContent(type="text", text=f"HTTP error ({status}): {str(e)}")]
    except requests.exceptions.Timeout:
        return [TextContent(type="text", text="Request timed out. The API may be slow; please retry.")]
    except requests.exceptions.ConnectionError:
        return [TextContent(type="text", text="Connection error. Check your internet connection.")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error in {name}: {str(e)}")]


# ============== ENTRY POINT ==============

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

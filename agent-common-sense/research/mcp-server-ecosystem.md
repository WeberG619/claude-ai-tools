# MCP Server Ecosystem Catalog

> **Last Updated:** February 18, 2026
> **Ecosystem Size:** ~7,300+ servers on Smithery.ai registry; 8,380+ on PulseMCP; ~76k stars on official reference repo
> **Purpose:** Catalog of public MCP servers for AI agent infrastructure planning

---

## Our Existing Stack (For Reference)

Already integrated MCP servers -- do not duplicate:
- **Claude Memory** -- persistent memory and corrections
- **Voice TTS** -- text-to-speech output
- **Bluebeam PDF** -- PDF markup and review
- **Excel** -- spreadsheet manipulation via COM automation
- **YouTube** -- video info, transcripts, comments, search
- **Financial Data** -- stock quotes, market data, portfolio management
- **Playwright** -- browser automation (structured accessibility snapshots)
- **CDP Browser** -- Chrome DevTools Protocol browser control
- **Visual Memory** -- screenshot capture and recall
- **SQLite** -- local database queries and management
- **Aider (multiple)** -- AI code editing via Ollama/Llama4/Quasar models

---

## Table of Contents

1. [File Systems and Storage](#1-file-systems-and-storage)
2. [Communication and Messaging](#2-communication-and-messaging)
3. [Databases and Data](#3-databases-and-data)
4. [Cloud Services and Infrastructure](#4-cloud-services-and-infrastructure)
5. [Productivity and Business Tools](#5-productivity-and-business-tools)
6. [Development and Code](#6-development-and-code)
7. [AI and ML](#7-ai-and-ml)
8. [Web Search and Content](#8-web-search-and-content)
9. [Browser Automation](#9-browser-automation)
10. [Monitoring and Observability](#10-monitoring-and-observability)
11. [Design and Creative](#11-design-and-creative)
12. [Specialized / Vertical](#12-specialized--vertical)
13. [Meta / Infrastructure](#13-meta--infrastructure)
14. [Recommendations Summary](#14-recommendations-summary)

---

## 1. File Systems and Storage

### Official / Reference

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Filesystem (Official)** | [modelcontextprotocol/servers/filesystem](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) | (part of 76k repo) | Production-ready | Secure local file system access with configurable allowed directories. Read, write, move, search files. Reference implementation. |

### Google Drive

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Google Workspace MCP** | [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp) | ~2.5k | Production-ready | **BEST OPTION.** All-in-one: Gmail, Calendar, Drive, Docs, Sheets, Slides, Chat, Forms, Tasks, Contacts, Search. Remote OAuth2.1 multi-user support. Most feature-complete. |
| **Google Drive MCP (Official ref)** | [modelcontextprotocol/servers/gdrive](https://github.com/modelcontextprotocol/servers) | (part of 76k repo) | Reference | Basic Google Drive file access, search, and read. Reference implementation by Anthropic. |
| **Google Docs MCP** | [a-bonus/google-docs-mcp](https://github.com/a-bonus/google-docs-mcp) | ~500 | Beta | Full access to Google Docs with direct edits and formatting. Focused on Docs/Sheets/Drive. |
| **Google Drive MCP** | [piotr-agier/google-drive-mcp](https://github.com/piotr-agier/google-drive-mcp) | ~200 | Beta | Secure integration with Drive, Docs, Sheets, Slides. Standardized interface. |

### OneDrive / SharePoint

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Files MCP Server (Microsoft)** | [microsoft/files-mcp-server](https://github.com/microsoft/files-mcp-server) | ~300 | Beta | Official Microsoft OneDrive MCP server for local testing and community contribution. |
| **OneDrive + SharePoint** | [ftaricano/mcp-onedrive-sharepoint](https://github.com/ftaricano/mcp-onedrive-sharepoint) | ~100 | Beta | Unified OneDrive and SharePoint access via Microsoft Graph API. File operations and collaboration. |

### Dropbox

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Dropbox MCP** | [amgadabdelhafez/dbx-mcp-server](https://github.com/amgadabdelhafez/dbx-mcp-server) | ~80 | Proof-of-concept | Basic Dropbox integration for MCP-compatible clients. |

### S3 / Cloud Object Storage

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **AWS MCP (Official)** | [awslabs/mcp](https://github.com/awslabs/mcp) | ~5k | Production-ready | Official AWS MCP servers including S3 access, along with comprehensive AWS service integration. |
| **FileStash MCP** | (community) | ~50 | Beta | Remote storage gateway: SFTP, S3, FTP, SMB, NFS, WebDAV, GIT, FTPS, cloud services. |

### Recommendation for Our Stack

**HIGH VALUE:** `taylorwilsdon/google_workspace_mcp` -- single server covers Gmail, Calendar, Drive, Docs, Sheets. Replaces the need for 5+ individual servers. Already production-ready with OAuth2.1.

---

## 2. Communication and Messaging

### Slack

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Slack MCP (korotovsky)** | [korotovsky/slack-mcp-server](https://github.com/korotovsky/slack-mcp-server) | ~300 | Production-ready | Most powerful Slack MCP. No permission requirements, stealth mode via cookies, DMs, Group DMs, smart history fetch. Supports Stdio/SSE/HTTP transports. |
| **Slack MCP (ubie-oss)** | [ubie-oss/slack-mcp-server](https://github.com/ubie-oss/slack-mcp-server) | ~100 | Beta | Comprehensive Slack workspace interface. Channel management, messaging, user info. Official OAuth auth. |

### Discord

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Discord MCP** | (community implementations) | ~50-100 | Beta | LLM interactions with Discord channels. Message sending and reading through Discord API. |

### Microsoft Teams

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Microsoft 365 MCP** | [microsoft/mcp](https://github.com/microsoft/mcp) | ~1k | Beta | Official Microsoft MCP catalog. Graph API integration covering Teams, Outlook, Office. |

### Email

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Google Workspace MCP** | [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp) | ~2.5k | Production-ready | Includes full Gmail integration (send, read, search, labels, drafts). Best Gmail option. |
| **Outlook MCP** | (part of Microsoft MCP catalog) | -- | Beta | Microsoft Outlook email via Graph API. Part of the broader Microsoft MCP effort. |

### WhatsApp

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **WhatsApp MCP** | [lharries/whatsapp-mcp](https://github.com/lharries/whatsapp-mcp) | ~200 | Proof-of-concept | Search personal WhatsApp messages, contacts; send messages to individuals or groups. |
| **Infobip MCP** | (official) | ~100 | Beta | SMS, RCS, WhatsApp, Viber messaging. Enterprise communication platform. |

### Telegram

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Telegram MCP (chigwell)** | [chigwell/telegram-mcp](https://github.com/chigwell/telegram-mcp) | ~150 | Beta | Full Telegram via Telethon. Read chats, manage groups, send/modify messages, media, contacts. |
| **Telegram MCP (sparfenyuk)** | [sparfenyuk/mcp-telegram](https://github.com/sparfenyuk/mcp-telegram) | ~100 | Beta | Telegram via MTProto. Send/edit/delete messages, search chats, manage drafts, download media. |

### Recommendation for Our Stack

**HIGH VALUE:** `korotovsky/slack-mcp-server` if Slack integration is needed. Gmail is already covered by the Google Workspace recommendation above.

---

## 3. Databases and Data

### PostgreSQL

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **PostgreSQL (Official ref)** | [modelcontextprotocol/servers/postgres](https://github.com/modelcontextprotocol/servers) | (part of 76k repo) | Reference | Schema inspection and read-only query capabilities. Reference implementation. |
| **MCP Alchemy** | (community) | ~200 | Production-ready | Universal SQLAlchemy-based: PostgreSQL, MySQL, MariaDB, SQLite, Oracle, MS SQL Server. Schema/relationship inspection, large dataset analysis. |

### MongoDB

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **MongoDB MCP** | [QuantGeekDev/mongo-mcp](https://github.com/QuantGeekDev/mongo-mcp) | ~200 | Beta | Direct MongoDB interaction for LLMs. Collection querying and analysis. |

### Supabase

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Supabase MCP (Official)** | [supabase-community/supabase-mcp](https://github.com/supabase-community/supabase-mcp) | ~800 | Production-ready | Official community server. Connect Supabase to AI assistants. Table management, config, querying. |
| **Supabase MCP Server** | [alexander-zuev/supabase-mcp-server](https://github.com/alexander-zuev/supabase-mcp-server) | ~400 | Production-ready | End-to-end Supabase management: read/write queries, Management API, automatic migration versioning, logs. |

### Notion

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Notion MCP (Official)** | [makenotion/notion-mcp-server](https://github.com/makenotion/notion-mcp-server) | ~3.9k | Production-ready | **Official by Notion.** Search content, query databases, manage pages and comments. v2.0 with Notion API 2025-09-03. Hosted remote server with secure OAuth access. |

### Airtable

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Airtable MCP** | [rashidazarang/airtable-mcp](https://github.com/rashidazarang/airtable-mcp) | ~150 | Beta | Connect AI tools directly to Airtable. CRUD on records, base management, table operations, schema manipulation, data migration. |

### Other Databases

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **DuckDB MCP** | (community) | ~100 | Beta | Schema inspection and analytical query support for DuckDB. |
| **MySQL MCP** | (community) | ~150 | Beta | MySQL integration with configurable access controls. |
| **Redis MCP** | (community) | ~100 | Beta | Natural language interface for Redis data management. |
| **Snowflake MCP** | (community) | ~100 | Beta | Read/write with insight tracking for Snowflake data warehouse. |
| **BigQuery MCP** | (community, multiple) | ~100-200 | Beta | Schema inspection and query support for Google BigQuery. |
| **Neon MCP** | (community) | ~100 | Beta | Serverless Postgres database management via natural language. |

### Recommendation for Our Stack

**HIGH VALUE:** `makenotion/notion-mcp-server` -- official, well-maintained, 3.9k stars. Notion is widely used for knowledge management.
**MEDIUM VALUE:** PostgreSQL or MCP Alchemy if connecting to production databases becomes needed.

---

## 4. Cloud Services and Infrastructure

### AWS

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **AWS MCP (Official)** | [awslabs/mcp](https://github.com/awslabs/mcp) | ~5k | Production-ready | **Official by AWS.** Comprehensive AWS API support + latest docs, API references, Getting Started info. Managed remote MCP server. Multiple sub-servers (S3, CDK, CloudFormation, etc.). |
| **AWS CLI MCP** | [alexei-led/aws-mcp-server](https://github.com/alexei-led/aws-mcp-server) | ~300 | Beta | Execute AWS CLI commands in containerized environment. Bridges AI tools with AWS CLI. |

### Azure

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Azure MCP (Official)** | [Azure/azure-mcp](https://github.com/Azure/azure-mcp) | ~1.5k | Production-ready | **Official by Microsoft.** Azure context across 40+ services. Production-ready. |
| **AKS MCP (Official)** | [Azure/aks-mcp](https://github.com/Azure/aks-mcp) | ~500 | Production-ready | AI-native Kubernetes operations for AKS clusters. Open source by Azure. |

### Kubernetes

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Kubernetes MCP (Azure)** | [Azure/mcp-kubernetes](https://github.com/Azure/mcp-kubernetes) | ~800 | Production-ready | AI assistants interact with any Kubernetes cluster. Bridge for Claude, Cursor, GitHub Copilot. |
| **K8s MCP (manusa)** | [manusa/Kubernetes-MCP-Server](https://github.com/manusa/Kubernetes-MCP-Server) | ~200 | Beta | CRUD operations for any Kubernetes resource. Go implementation. |
| **K8s MCP (alexei-led)** | [alexei-led/k8s-mcp-server](https://github.com/alexei-led/k8s-mcp-server) | ~150 | Beta | Execute kubectl, helm, istioctl, argocd commands. |

### Docker

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Docker MCP (ckreiling)** | [ckreiling/mcp-server-docker](https://github.com/ckreiling/mcp-server-docker) | ~670 | Production-ready | Manage containers, images, volumes, networks. Mounts Docker socket. Most starred Docker MCP. |
| **Docker MCP (QuantGeekDev)** | [QuantGeekDev/docker-mcp](https://github.com/QuantGeekDev/docker-mcp) | ~450 | Beta | Container and compose stack management through Claude AI. |
| **Docker Hub MCP** | [docker/hub-mcp](https://github.com/docker/hub-mcp) | ~120 | Beta | Official Docker Hub server. Repository search, Docker Hardened images. |
| **Docker MCP Gateway** | [docker/mcp-gateway](https://github.com/docker/mcp-gateway) | ~300 | Production-ready | Docker CLI plugin. Run MCP servers in isolated containers. 270+ servers in catalog. |

### Terraform / IaC

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Terraform MCP (Official)** | [hashicorp/terraform-mcp-server](https://github.com/hashicorp/terraform-mcp-server) | ~1.5k | Production-ready | **Official by HashiCorp.** Provider discovery, module analysis, Registry API. Dual transport (Stdio/StreamableHTTP). HCP Terraform and Terraform Enterprise support. |

### Cloudflare

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Cloudflare MCP (Official)** | [cloudflare/mcp-server-cloudflare](https://github.com/cloudflare/mcp-server-cloudflare) | ~1k | Production-ready | **Official by Cloudflare.** Deploy/configure Workers, KV, R2, D1. Edge deployment, DNS management, cache control. |

### Vercel

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Vercel MCP** | (official) | ~300 | Beta | Connects MCP agents to Vercel deployment/hosting platform. OAuth 2.1 auth. |

### Container Management

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Portainer MCP** | [portainer/portainer-mcp](https://github.com/portainer/portainer-mcp) | ~200 | Beta | Container and infrastructure management through Portainer. |
| **Cyclops MCP** | [cyclops-ui/mcp-cyclops](https://github.com/cyclops-ui/mcp-cyclops) | ~100 | Beta | Kubernetes resource management via UI abstraction layer. |

### Recommendation for Our Stack

**MEDIUM VALUE:** `ckreiling/mcp-server-docker` for Docker container management. Only valuable if actively managing Docker deployments via AI agent.
**LOW VALUE for now:** AWS/Azure/Terraform servers -- only valuable if managing cloud infrastructure.

---

## 5. Productivity and Business Tools

### Atlassian (Jira + Confluence)

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Atlassian MCP (Official)** | [atlassian/atlassian-mcp-server](https://github.com/atlassian/atlassian-mcp-server) | ~1k | Production-ready | **Official by Atlassian.** Remote MCP server with OAuth. Jira, Confluence, Compass Cloud data in real-time. Hosted by Atlassian. |
| **MCP Atlassian (sooperset)** | [sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian) | ~4.2k | Production-ready | Community-built. Supports both Cloud AND Server/Data Center deployments. Most starred Atlassian MCP. |
| **Atlassian MCP (xuanxt)** | [xuanxt/atlassian-mcp](https://github.com/xuanxt/atlassian-mcp) | ~200 | Beta | 51 tools for Confluence pages, Jira issues, sprints, boards, backlogs. Docker deployment. |

### Linear

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Linear MCP** | (community) | ~200 | Beta | Search, create, and update Linear issues, projects, and comments. |

### CRM (Salesforce, HubSpot)

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **HubSpot MCP (Official)** | [HubSpot developers](https://developers.hubspot.com/mcp) | ~300 | Production-ready | **Official by HubSpot.** CRM data access with OAuth 2.0. Contacts, companies, deals. |
| **HubSpot MCP (peakmojo)** | [peakmojo/mcp-hubspot](https://github.com/peakmojo/mcp-hubspot) | ~100 | Beta | HubSpot CRM data with built-in vector storage and caching. |
| **Salesforce MCP** | (community) | ~150 | Beta | Connect LLMs to Salesforce data via SOQL, SOSL, and APIs. |

### Google Calendar (standalone)

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Google Calendar MCP** | [nspady/google-calendar-mcp](https://github.com/nspady/google-calendar-mcp) | ~300 | Beta | Check schedules, find availability, add/delete events. (Also covered by Google Workspace MCP above.) |

### Google Maps / Location

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Google Maps MCP** | [cablate/mcp-google-map](https://github.com/cablate/mcp-google-map) | ~200 | Beta | Geocoding, place search, directions, distance matrix. Streamable HTTP transport. |
| **Google Maps (Official)** | Maps Grounding Lite | -- | Production-ready | Fully-managed by Google. Geospatial data and routing. Announced Dec 2025. |

### Payments

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Stripe MCP (Official)** | [Stripe docs](https://docs.stripe.com/mcp) | ~500 | Production-ready | **Official by Stripe.** Connect AI editors to Stripe. OAuth auth or API keys. Remote or local. |
| **Twilio MCP (Official)** | [twilio-labs/mcp](https://github.com/twilio-labs/mcp) | ~300 | Beta | OpenAPI-to-MCP tool generator. Exposes all Twilio APIs as MCP tools. SMS, voice, payments. |

### Microsoft Dynamics 365

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Dynamics 365 ERP MCP** | (Microsoft) | -- | Production-ready | Unlocks hundreds of thousands of ERP functions. 50+ partners implementing. |

### Recommendation for Our Stack

**HIGH VALUE:** `sooperset/mcp-atlassian` if using Jira/Confluence -- 4.2k stars, supports Cloud and Server.
**MEDIUM VALUE:** Stripe MCP if handling payments. Google Maps if location-aware tasks needed.

---

## 6. Development and Code

### GitHub

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **GitHub MCP (Official)** | [github/github-mcp-server](https://github.com/github/github-mcp-server) | ~14k | Production-ready | **Official by GitHub.** Repository management, issues, PRs, code analysis, GitHub Actions CI/CD, Dependabot alerts, releases. Dynamic toolset discovery. The most-starred standalone MCP server. |

### GitLab

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **GitLab MCP** | (community) | ~200 | Beta | Project management and CI/CD integration for GitLab. |

### Git (local)

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Git MCP (Official ref)** | [modelcontextprotocol/servers/git](https://github.com/modelcontextprotocol/servers) | (part of 76k repo) | Reference | Local Git repository operations. Reading history, diffs, branches. |

### CI/CD

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **TeamCity MCP** | [Daghis/teamcity-mcp](https://github.com/Daghis/teamcity-mcp) | ~100 | Beta | JetBrains TeamCity with 87 tools. Builds, tests, agents, pipeline management. Dual-mode (dev/full). |
| **Jenkins MCP** | [avisangle/jenkins-mcp-server](https://github.com/avisangle/jenkins-mcp-server) | ~50 | Beta | Enterprise Jenkins CI/CD. Multi-tier caching, pipeline monitoring, artifact management. 21 tools. |

### Code Analysis

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Serena** | [oraios/serena](https://github.com/oraios/serena) | ~20k | Production-ready | Coding agent toolkit using language servers for semantic retrieval and editing. MCP server and other integrations. Extremely popular. |
| **Context7** | [upstash/context7](https://github.com/upstash/context7) | ~45k | Production-ready | Up-to-date, version-specific documentation and code examples for LLMs. The most-starred MCP-related project overall. |
| **Desktop Commander** | [wonderwhy-er/DesktopCommanderMCP](https://github.com/wonderwhy-er/DesktopCommanderMCP) | ~5.4k | Production-ready | Terminal control, file system search, diff file editing. Swiss-army-knife for desktop automation. |
| **Code Analysis MCP** | [saiprashanths/code-analysis-mcp](https://github.com/saiprashanths/code-analysis-mcp) | ~100 | Beta | Understand and analyze codebases through natural language conversations. |
| **Code Review MCP** | [praneybehl/code-review-mcp](https://github.com/praneybehl/code-review-mcp) | ~50 | Proof-of-concept | Code reviews using OpenAI and Google models for Claude-code. |

### Error Tracking

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Sentry MCP (Official)** | [getsentry/sentry-mcp](https://github.com/getsentry/sentry-mcp) | ~460 | Production-ready | **Official by Sentry.** Retrieve error/performance data. Remote MCP with OAuth. No install needed. |

### Recommendation for Our Stack

**HIGH VALUE:** `github/github-mcp-server` -- 14k stars, official, massively extends GitHub capabilities beyond basic git. CI/CD monitoring, code analysis, security alerts.
**HIGH VALUE:** `upstash/context7` -- 45k stars, gives LLMs current documentation. Prevents outdated API usage.
**MEDIUM VALUE:** `oraios/serena` -- 20k stars, powerful for semantic code operations via language servers.

---

## 7. AI and ML

### Vector Databases

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Qdrant MCP (Official)** | [qdrant/mcp-server-qdrant](https://github.com/qdrant/mcp-server-qdrant) | ~400 | Production-ready | **Official by Qdrant.** Semantic memory layer on top of Qdrant vector search engine. |
| **Milvus MCP** | (community + official docs) | ~200 | Beta | Vector search, collection management, data retrieval via natural language. Milvus has 40k+ stars. |
| **ChromaDB MCP** | (community) | ~100 | Beta | Lightweight vector database integration. Good for prototyping. |
| **Pinecone MCP** | (community) | ~80 | Proof-of-concept | Managed vector database queries via MCP. |

### Hugging Face

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **HuggingFace MCP (Official)** | [Hugging Face docs](https://huggingface.co/docs/hub/hf-mcp-server) | ~300 | Production-ready | **Official by HuggingFace.** Search/explore Hub resources, use community tools from within editor/chat/CLI. |
| **HuggingFace MCP (community)** | [bui21x/huggingface-mcp-server](https://github.com/bui21x/huggingface-mcp-server) | ~50 | Beta | ML model inference and management capabilities. |

### RAG / Embeddings

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **RAGDocs MCP** | (community) | ~100 | Beta | Retrieve and process documentation through vector search. Augment responses with relevant docs. |
| **Ultimate MCP Server** | [Dicklesworthstone/ultimate_mcp_server](https://github.com/Dicklesworthstone/ultimate_mcp_server) | ~300 | Beta | Multi-provider LLM delegation, browser automation, document processing, vector ops, cognitive memory. Kitchen-sink approach. |

### Recommendation for Our Stack

**HIGH VALUE:** `qdrant/mcp-server-qdrant` -- if building RAG or semantic search capabilities. Official, production-ready.
**MEDIUM VALUE:** `upstash/context7` is listed in Development but also serves as an AI/ML documentation tool.

---

## 8. Web Search and Content

### Search Engines

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Brave Search (Official ref)** | [modelcontextprotocol/servers/brave-search](https://github.com/modelcontextprotocol/servers) | (part of 76k repo) | Reference | Web and local search via Brave's Search API. $3/1k queries. |
| **Tavily MCP** | (official) | ~500 | Production-ready | Search engine designed for AI agents. Search + extract. $8/1k requests. |
| **Exa Search MCP** | (official) | ~300 | Production-ready | AI-native search engine. $1.50/1k searches. |
| **Firecrawl MCP** | (official) | ~400 | Production-ready | Web scraping and content extraction. $83/100k credits, free tier available. |
| **MCP Omnisearch** | [spences10/mcp-omnisearch](https://github.com/spences10/mcp-omnisearch) | ~100 | Beta | Unified: Tavily, Brave, Kagi, Perplexity, FastGPT, Jina AI, Exa. Single interface for multiple providers. |
| **OneSearch MCP** | [yokingma/one-search-mcp](https://github.com/yokingma/one-search-mcp) | ~200 | Beta | Web search and scraping. SearXNG, Tavily, DuckDuckGo, Bing, Google, Exa, and more. |

### Content Fetching

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Fetch (Official ref)** | [modelcontextprotocol/servers/fetch](https://github.com/modelcontextprotocol/servers) | (part of 76k repo) | Reference | Fetch web content and convert to markdown. Reference implementation. |

### Recommendation for Our Stack

**MEDIUM VALUE:** Tavily or Brave Search MCP for programmatic web search from agent workflows. Already have WebSearch/WebFetch built into Claude Code, but these enable agentic search patterns.

---

## 9. Browser Automation

Already in our stack: **Playwright MCP** and **CDP Browser MCP**. Listed here for completeness and alternatives.

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Playwright MCP (Official)** | [microsoft/playwright-mcp](https://github.com/nicksavill) | ~5k | Production-ready | **Already in our stack.** Structured accessibility snapshots for web interaction. |
| **Browserbase MCP** | [browserbase/mcp-server-browserbase](https://github.com/browserbase/mcp-server-browserbase) | ~500 | Production-ready | Cloud browser automation with Stagehand v3.0. Enhanced extraction, multi-browser support. |
| **Puppeteer MCP** | [modelcontextprotocol/servers/puppeteer](https://github.com/modelcontextprotocol/servers) | (part of 76k repo) | Reference | Headless Chrome control. Navigation, screenshots, PDFs, form filling. |

### Recommendation for Our Stack

**NO ACTION NEEDED** -- we already have Playwright and CDP Browser covering this category comprehensively.

---

## 10. Monitoring and Observability

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Grafana MCP (Official)** | [grafana/mcp-grafana](https://github.com/grafana/mcp-grafana) | ~500 | Production-ready | **Official by Grafana.** Dashboard search, datasource queries, incident management. TraceQL queries. |
| **Datadog MCP (Official)** | [Datadog docs](https://docs.datadoghq.com/bits_ai/mcp_server/) | ~300 | Production-ready | **Official by Datadog.** Remote MCP server with SSE. Metrics, logs, traces, troubleshooting. |
| **Datadog MCP (shelfio)** | [shelfio/datadog-mcp](https://github.com/shelfio/datadog-mcp) | ~100 | Beta | Community Datadog monitoring via MCP. |
| **Sentry MCP (Official)** | [getsentry/sentry-mcp](https://github.com/getsentry/sentry-mcp) | ~460 | Production-ready | Error and performance data retrieval. (Also listed under Development.) |
| **Netdata MCP** | [netdata/netdata](https://github.com/netdata/netdata) | ~75.2k | Production-ready | Real-time system monitoring as MCP server. AI-assisted operations. (Netdata itself is massive; MCP is one feature.) |

### Recommendation for Our Stack

**LOW VALUE for now** -- only relevant if managing production infrastructure via AI agent.

---

## 11. Design and Creative

### Figma

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Figma Context MCP** | [GLips/Figma-Context-MCP](https://github.com/GLips/Figma-Context-MCP) | ~1k | Production-ready | Provides Figma layout information to AI coding agents like Cursor. Design-to-code workflows. |
| **Figma MCP (Official)** | [Figma](https://github.com/mcp/com.figma.mcp/mcp) | ~500 | Production-ready | Official Figma MCP. Structured design file contents via MCP. |
| **Figma Console MCP** | [southleft/figma-console-mcp](https://github.com/southleft/figma-console-mcp) | ~200 | Beta | Real-time console access, visual debugging, design system extraction, design creation. |

### Blender (3D)

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Blender MCP** | [poly-mcp/Blender-MCP-Server](https://github.com/poly-mcp/Blender-MCP-Server) | ~500 | Beta | Control Blender via AI agents. 51 tools. Thread-safe execution, 3D workflow automation. |

### Other Creative

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Maya MCP** | [PatrickPalmer/MayaMCP](https://github.com/PatrickPalmer/MayaMCP) | ~100 | Proof-of-concept | Autodesk Maya automation via MCP. |
| **REAPER DAW MCP** | [TwelveTake-Studios/reaper-mcp](https://github.com/TwelveTake-Studios/reaper-mcp) | ~50 | Proof-of-concept | Audio DAW for mixing, mastering, MIDI composition. |
| **EverArt MCP** | [modelcontextprotocol/servers/everart](https://github.com/modelcontextprotocol/servers) | (part of 76k repo) | Reference | AI art generation via EverArt API. |

### Recommendation for Our Stack

**LOW VALUE** -- only relevant if doing design-to-code workflows with Figma, or 3D modeling.

---

## 12. Specialized / Vertical

### CAD / BIM (Beyond Our Bluebeam)

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Revit MCP** | [revit-mcp/revit-mcp](https://github.com/revit-mcp/revit-mcp) | ~300 | Beta | AI-powered Revit modeling. Core CRUD commands for Revit elements. AI-driven BIM automation. Multiple implementations exist. |
| **Revit MCP (PiggyAndrew)** | [PiggyAndrew/revit_mcp](https://github.com/piggyandrew/revit_mcp) | ~200 | Beta | Claude AI to Autodesk Revit integration. Seamless communication. |
| **IFC MCP** | (community) | ~50 | Proof-of-concept | IFC/BIM data access for building design, construction, management. Natural language interface to BIM models. |
| **NVIDIA Isaac Sim MCP** | [omni-mcp/isaac-sim-mcp](https://github.com/omni-mcp/isaac-sim-mcp) | ~50 | Proof-of-concept | NVIDIA Isaac Sim robotics simulation control. |

### Meeting Intelligence

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **tl;dv MCP** | (community) | ~100 | Beta | Meeting intelligence across Google Meet, Zoom, Microsoft Teams. Unified interface for meeting recordings and insights. |

### Spatial / Scientific

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **ChatSpatial** | [cafferychen777/ChatSpatial](https://github.com/cafferychen777/ChatSpatial) | ~100 | Beta | Spatial transcriptomics analysis with 60+ methods. Scientific research tool. |

### Recommendation for Our Stack

**NOTE:** We have our own `RevitMCPBridge2026` which uses named pipes (not HTTP). The community Revit MCPs use different transport mechanisms. Our implementation is custom-tailored to our workflow.

---

## 13. Meta / Infrastructure

### Multi-Server Management

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **SageMCP** | [sagemcp/SageMCP](https://github.com/sagemcp/SageMCP) | ~200 | Beta | Multi-tenant MCP server platform. Built-in OAuth/API key auth for 23+ services (GitHub, GitLab, Jira, Slack, Discord, Teams, Gmail, Outlook, Notion, etc.). |
| **MetaMCP** | (community) | ~2k | Beta | Unified middleware. Manages MCP connections with GUI. Aggregates multiple MCP servers. |
| **MCPJungle** | [mcpjungle/MCPJungle](https://github.com/mcpjungle/MCPJungle) | ~850 | Beta | Self-hosted MCP server registry for enterprise AI agents. |
| **Rube** | (community) | ~100 | Beta | Connects AI tools to 500+ apps (Gmail, Slack, GitHub, Notion). Authenticate once, perform real actions. |
| **Knit MCP** | (community) | ~50 | Beta | Connect with 10,000+ tools across CRM, HRIS, Payroll, Accounting, ERP, Calendar, Chat. |
| **Composio MCP** | [composio.dev](https://mcp.composio.dev/) | ~500 | Production-ready | Platform for connecting 250+ tools. Pre-built integrations with OAuth management. |

### MCP Proxies and Gateways

| Server | GitHub | Stars | Status | Description |
|--------|--------|-------|--------|-------------|
| **Docker MCP Gateway** | [docker/mcp-gateway](https://github.com/docker/mcp-gateway) | ~300 | Production-ready | Run MCP servers in isolated Docker containers. Secrets management. 270+ servers in catalog. |
| **pluggedin-mcp-proxy** | [VeriTeknik/pluggedin-mcp-proxy](https://github.com/VeriTeknik/pluggedin-mcp-proxy) | ~200 | Beta | Proxy server combining multiple MCP servers into single interface. |

### Recommendation for Our Stack

**MEDIUM VALUE:** `docker/mcp-gateway` could be useful for running MCP servers in isolated containers with proper security boundaries.

---

## 14. Recommendations Summary

### Tier 1: High Value -- Should Add

| Server | Why | Stars | Effort |
|--------|-----|-------|--------|
| **GitHub MCP (Official)** | 14k stars. Full GitHub automation: repos, issues, PRs, Actions, security alerts. We already use git but this adds CI/CD monitoring and code analysis. | ~14k | Low -- official, well-documented |
| **Google Workspace MCP** | Single server for Gmail + Calendar + Drive + Docs + Sheets + Slides. Replaces need for 5+ servers. OAuth2.1 ready. | ~2.5k | Medium -- OAuth setup required |
| **Context7** | 45k stars. Up-to-date documentation in prompts. Prevents outdated API usage. Essential for code generation quality. | ~45k | Low -- simple to add |
| **Notion MCP (Official)** | 3.9k stars. Official, actively maintained. Knowledge management integration. | ~3.9k | Low -- hosted remote server |

### Tier 2: Medium Value -- Consider Adding

| Server | Why | Stars | Effort |
|--------|-----|-------|--------|
| **Atlassian MCP** | 4.2k stars. Jira + Confluence. Only if using Atlassian products. | ~4.2k | Medium |
| **Qdrant Vector DB MCP** | Official vector DB MCP. Enables RAG and semantic search workflows. | ~400 | Medium |
| **Docker MCP** | Container management. Only if managing Docker deployments via agent. | ~670 | Low |
| **Sentry MCP (Official)** | Error tracking integration. Only if using Sentry for monitoring. | ~460 | Low -- remote, no install |
| **Slack MCP** | If Slack is used for team communication. Stealth mode option. | ~300 | Low |
| **Stripe MCP (Official)** | If handling payments. Official, well-supported. | ~500 | Low |
| **Serena** | 20k stars. Semantic code operations via language servers. Powerful coding toolkit. | ~20k | Medium |

### Tier 3: Low Value for Current Stack -- Monitor

| Server | Why |
|--------|-----|
| **AWS/Azure/Terraform MCP** | Only if managing cloud infrastructure |
| **Grafana/Datadog MCP** | Only if monitoring production systems |
| **Figma MCP** | Only if doing design-to-code workflows |
| **Blender MCP** | Only if doing 3D modeling |
| **Kubernetes MCP** | Only if managing K8s clusters |
| **HubSpot/Salesforce MCP** | Only if using these CRMs |

### Already Covered -- No Action Needed

| Category | Our Server | Notes |
|----------|-----------|-------|
| Browser Automation | Playwright + CDP | Comprehensive coverage |
| PDF | Bluebeam | Specialized for our workflow |
| Spreadsheets | Excel MCP | COM automation, full-featured |
| Video | YouTube MCP | Info, transcripts, comments |
| Finance | Financial MCP | Comprehensive market data |
| Database | SQLite | Local DB covered |
| Memory | Claude Memory | Persistent memory system |
| Voice | Voice TTS | Text-to-speech |
| Visual | Visual Memory | Screenshot capture/recall |
| Code AI | Aider (3 models) | Multi-model code editing |
| Revit/BIM | RevitMCPBridge2026 | Custom named-pipes implementation |

---

## Key Sources and Registries

### Official Resources
- [MCP Specification](https://modelcontextprotocol.io/specification/2025-11-25) -- November 2025 spec
- [Official MCP Registry](https://registry.modelcontextprotocol.io/) -- Central index
- [Official Reference Servers](https://github.com/modelcontextprotocol/servers) -- 76k stars
- [MCP Examples](https://modelcontextprotocol.io/examples) -- Example implementations

### Community Catalogs
- [awesome-mcp-servers (punkpeye)](https://github.com/punkpeye/awesome-mcp-servers) -- Largest community list
- [awesome-mcp-servers (appcypher)](https://github.com/appcypher/awesome-mcp-servers) -- Well-categorized
- [awesome-mcp-servers (TensorBlock)](https://github.com/TensorBlock/awesome-mcp-servers) -- Comprehensive with docs
- [best-of-mcp-servers (tolkonepiu)](https://github.com/tolkonepiu/best-of-mcp-servers) -- Ranked weekly, 410 servers
- [awesome-devops-mcp-servers](https://github.com/rohitg00/awesome-devops-mcp-servers) -- DevOps-focused

### Discovery Platforms
- [Smithery.ai](https://smithery.ai/) -- 7,300+ servers, semantic search, hosted deployment
- [Glama.ai](https://glama.ai/mcp/servers) -- Largest MCP directory with security scanning
- [PulseMCP](https://www.pulsemcp.com/servers) -- 8,380+ servers with usage rankings
- [MCP Market](https://mcpmarket.com/leaderboards) -- Top 100 leaderboard by stars
- [Awesome Claude](https://awesomeclaude.ai/top-mcp-servers) -- Ranked by GitHub stars
- [MCP Servers.org](https://mcpservers.org/) -- Community directory

### Platform-Specific Catalogs
- [Docker MCP Catalog](https://github.com/docker/mcp-gateway) -- 270+ servers containerized
- [Composio MCP](https://mcp.composio.dev/) -- 250+ tool integrations
- [Microsoft MCP Catalog](https://github.com/microsoft/mcp) -- Official Microsoft servers

---

## Ecosystem Statistics (February 2026)

- **Total registered MCP servers:** ~8,000+ across all registries
- **Official vendor implementations:** 30+ (GitHub, AWS, Azure, Atlassian, Notion, Stripe, Cloudflare, Terraform, Sentry, Grafana, Datadog, HubSpot, Docker, Google, etc.)
- **Most starred MCP project:** Context7 (~45k stars)
- **Most starred standalone MCP server:** GitHub MCP Server (~14k stars)
- **Official reference repo:** modelcontextprotocol/servers (~76k stars)
- **Ecosystem growth:** 407% since September 2025 registry launch
- **Specification version:** November 2025 (adds async execution, auth, enterprise features)

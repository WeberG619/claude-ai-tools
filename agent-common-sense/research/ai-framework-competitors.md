# AI Agent Orchestration Framework — Competitor Landscape Analysis

> **Date:** February 18, 2026
> **Purpose:** Business intelligence for positioning the Autonomy Engine
> **Scope:** Commercial platforms, open-source frameworks, AI IDEs, vertical solutions

---

## Executive Summary

The AI agent orchestration market is exploding. GitHub stars for agent frameworks have grown 500%+ since 2023. Enterprise adoption is accelerating, with Gartner projecting 65% of all application development will be powered by low-code/no-code platforms by 2026. However, **no competitor combines all four pillars of the Autonomy Engine** — goal tracking, autonomous planning, alignment injection, and cross-agent coordination — into a unified system designed for individual professionals and small firms.

The market is bifurcated: enterprise platforms (expensive, complex) vs. open-source frameworks (developer-only, no opinion on alignment). The Autonomy Engine occupies an uncontested niche: an opinionated, production-grade orchestration layer for non-enterprise professionals who need agent systems that stay aligned with their goals across sessions.

---

## 1. Commercial AI Agent Platforms

### Relevance AI
- **URL:** https://relevanceai.com
- **Pricing:** Free ($0) / Pro ($19/mo) / Team ($199/mo) / Business ($599/mo) / Enterprise (custom)
- **Credit model:** Actions + Vendor Credits (pass-through LLM costs, 20% markup without own API key)
- **Target market:** SMB to enterprise; sales and operations teams
- **Key differentiators:** No-code agent builder, BabyAGI-style autonomous agents, 4,000+ integrations
- **Maturity:** GA — production-ready, active development
- **vs. Autonomy Engine:** Relevance AI provides drag-and-drop agent building and CRM-focused workflows. It has no goal hierarchy, no alignment injection, no cross-agent coordination layer. It is a SaaS tool for sales teams, not a system for professional autonomy.

### CrewAI (Commercial)
- **URL:** https://crewai.com
- **Pricing:** Free tier (50 executions/mo) / $99/mo / $6,000/yr / Enterprise up to $120,000/yr
- **Target market:** Developers and enterprises deploying multi-agent crews
- **Key differentiators:** Role-based agent collaboration ("Crews"), lean Python framework, visual studio, 1.4 billion executions claimed
- **Maturity:** GA — major enterprise traction (PwC, IBM, Capgemini, NVIDIA)
- **vs. Autonomy Engine:** CrewAI excels at role-based task execution with a clean developer API. However, it has no persistent goal tracking across sessions, no alignment injection (sub-agents have no "common sense" kernel), and no built-in planning that decomposes goals into multi-step plans with dependency graphs. CrewAI orchestrates crews; the Autonomy Engine orchestrates intentions.

### Cognosys (rebranded to Ottogrid, Oct 2024)
- **URL:** https://cognosys.ai / https://ottogrid.com
- **Pricing:** Free / Pro ($15/mo) / Ultimate ($59/mo) / Enterprise (custom)
- **Revenue:** ~$660K ARR as of 2025 (6-person team)
- **Target market:** Individual knowledge workers, researchers, SMBs
- **Key differentiators:** Goal-oriented AI agents, Smart Table Interface (Autogrid — each cell is an AI agent), continuous learning agents
- **Maturity:** GA — pivoted from general agent to structured data workflows
- **vs. Autonomy Engine:** Cognosys has rudimentary goal decomposition (it breaks goals into tasks). However, it lacks hierarchical goal trees with dependency tracking, alignment injection for sub-agents, resource locking, or cross-session memory-driven correction loops. Its "goal-oriented" approach is shallow compared to the Autonomy Engine's full goal-plan-alignment-coordination stack.

### Adept AI (acquired by Amazon, June 2024)
- **URL:** https://adept.ai
- **Pricing:** Enterprise only (contact sales; estimated $100K+ annual)
- **Target market:** Large enterprises with repetitive software workflows
- **Key differentiators:** Proprietary ACT models for computer use, automates multi-step tasks across SaaS apps, strong enterprise security
- **Maturity:** GA (enterprise) — now part of Amazon's AI strategy
- **vs. Autonomy Engine:** Adept focuses on computer-use automation (clicking, typing, navigating). It is a task execution engine, not a goal management system. No hierarchical goal tracking, no alignment injection, no open-source component. Its acquisition by Amazon means it will likely become an AWS service, not an accessible tool for small firms.

### Lindy AI
- **URL:** https://lindy.ai
- **Pricing:** Free (400 credits/mo) / Starter ($19.99/mo) / Pro ($49.99/mo) / Business (custom)
- **Target market:** Professionals and teams automating daily workflows (email, meetings, scheduling)
- **Key differentiators:** Natural language agent builder, Autopilot computer-use, 4,000+ app integrations, Claude Sonnet 4.5 as default model
- **Maturity:** GA — v3.0 launched Aug 2025 with major upgrades
- **vs. Autonomy Engine:** Lindy is a polished consumer/prosumer product for workflow automation (email triage, meeting notes, scheduling). It has no goal hierarchy, no alignment injection, no resource coordination between agents. It is a powerful AI assistant builder, but not an orchestration framework with opinions about alignment and planning.

### Dust.tt
- **URL:** https://dust.tt
- **Pricing:** Pro (EUR 29/user/mo) / Enterprise (custom)
- **Target market:** Teams and startups needing company-knowledge-connected AI agents
- **Key differentiators:** Deep knowledge integration (Google Drive, Notion, Slack), MCP support, multi-model support (GPT-4, Claude), Dust Apps for custom actions
- **Maturity:** GA — focused on enterprise knowledge work
- **vs. Autonomy Engine:** Dust is a knowledge-connected agent platform. Its strength is RAG over company data. It has no goal tracking, no autonomous planning, no alignment injection, no cross-agent coordination. It solves a different problem (knowledge access) rather than agent orchestration.

### Summary Table — Commercial Platforms

| Platform | Price Range | Target | Goal Tracking | Planning | Alignment | Coordination |
|----------|------------|--------|:---:|:---:|:---:|:---:|
| Relevance AI | $0-599/mo | SMB/Enterprise | No | No | No | No |
| CrewAI | $0-120K/yr | Developers/Enterprise | No | Partial* | No | Partial* |
| Cognosys | $0-59/mo | Individuals/SMB | Rudimentary | No | No | No |
| Adept | $100K+/yr | Enterprise | No | No | No | No |
| Lindy AI | $0-49.99/mo | Professionals | No | No | No | No |
| Dust.tt | EUR 29+/user/mo | Teams | No | No | No | No |
| **Autonomy Engine** | **Open-source** | **Professionals/Small firms** | **Yes** | **Yes** | **Yes** | **Yes** |

*CrewAI has task decomposition within crews and role-based collaboration, but not persistent hierarchical goal trees or alignment injection.

---

## 2. Open-Source Agent Frameworks

### LangGraph (LangChain)
- **URL:** https://github.com/langchain-ai/langgraph
- **GitHub stars:** ~16K+ (as of mid-2025, likely 18-20K+ now)
- **Community:** Massive — part of LangChain ecosystem (parent has 80K+ stars)
- **Last commit:** Active daily development
- **Production readiness:** HIGH — used by Klarna (85M users), Elastic, Replit
- **Key differentiators:** Graph-based state machines for agent workflows, checkpoint APIs, persistent memory, directed acyclic graph (DAG) execution, LangGraph Platform for deployment
- **Pricing (Platform):** Free self-hosted / LangGraph Cloud pricing varies
- **vs. Autonomy Engine:** LangGraph is the most technically mature graph-based orchestration framework. It provides state machines, checkpointing, and memory. However, it is a **low-level building block** — it has no opinion about goals, no alignment injection, no common-sense kernel, and no built-in planning with template matching. You could build the Autonomy Engine on top of LangGraph, but LangGraph alone is a DAG executor, not an autonomous system with judgment.

### AutoGen (Microsoft) → Microsoft Agent Framework
- **URL:** https://github.com/microsoft/autogen
- **GitHub stars:** ~50K+
- **Community:** 559 contributors, massive Microsoft backing
- **Last commit:** Active (but Microsoft recommends new users move to Microsoft Agent Framework which merges AutoGen + Semantic Kernel)
- **Production readiness:** HIGH — Microsoft-backed, extensive testing
- **Key differentiators:** Pioneered multi-agent conversation paradigm, customizable agent behaviors, human-in-the-loop support
- **Status:** Maintenance mode — new features going to Microsoft Agent Framework instead
- **vs. Autonomy Engine:** AutoGen pioneered multi-agent conversations, but is now being sunset in favor of Microsoft Agent Framework. It has no goal hierarchy, no alignment injection, no common-sense kernel. It is a conversation orchestrator, not a goal-driven system.

### CrewAI (Open-Source)
- **URL:** https://github.com/crewAIInc/crewAI
- **GitHub stars:** ~44K+
- **Community:** Large, active, fast-growing (fastest-growing agent framework)
- **Last commit:** Active — Jan 2026 updates (async chains, A2A)
- **Production readiness:** HIGH — independent of LangChain, lean Python framework
- **Key differentiators:** Role-playing agents, crew-based collaboration, Flows architecture, fully independent from LangChain
- **vs. Autonomy Engine:** CrewAI open-source is the role-based agent framework leader. It assigns roles and tasks to agents and lets them collaborate. But it has no persistent cross-session goal tracking, no alignment injection layer, no correction-based learning loops, and no common-sense kernel. The Autonomy Engine could use CrewAI as an execution substrate while adding the missing goal/alignment/coordination layers.

### Agency Swarm (VRSEN)
- **URL:** https://github.com/VRSEN/agency-swarm
- **GitHub stars:** ~3.9K
- **Community:** Small but focused; active YouTube presence from creator
- **Last commit:** Active (but slower cadence than CrewAI/LangGraph)
- **Production readiness:** MEDIUM — good for prototyping, less enterprise-hardened
- **Key differentiators:** Built on OpenAI Agents SDK, organizational-structure-based agent design, multi-LLM support (OpenAI, Anthropic, Google)
- **vs. Autonomy Engine:** Agency Swarm mimics real-world org structures for agent teams. Interesting design philosophy but lacks goal tracking, planning, alignment injection, and coordination. Smaller community means less ecosystem support.

### Phidata / Agno
- **URL:** https://github.com/agno-agi/agno (rebranded from Phidata)
- **GitHub stars:** ~18.5K+
- **Community:** Active, growing post-rebrand
- **Last commit:** Active
- **Production readiness:** MEDIUM-HIGH — multi-modal, good agent UI, AgentOS for deployment
- **Key differentiators:** Multi-modal agents (text, images, audio, video), unified API, AgentOS control plane, claims to be fastest agent framework
- **vs. Autonomy Engine:** Agno is a fast, multi-modal agent framework. Strong execution layer. But no goal tracking, no alignment injection, no planning system, no coordination layer. It is a framework for building agents, not for orchestrating goal-driven autonomous systems.

### Composio
- **URL:** https://github.com/ComposioHQ/composio
- **GitHub stars:** Growing rapidly (exact count not confirmed, estimated 10K+)
- **Community:** Active — SOC 2 Type 2 compliant, trusted by Glean, Altera
- **Last commit:** Active
- **Production readiness:** HIGH — production-grade integration layer
- **Key differentiators:** 500+ LLM-ready tool integrations, managed auth, works with 25+ agentic frameworks, MCP support
- **vs. Autonomy Engine:** Composio is an **integration layer**, not an orchestration framework. It solves the "how do agents connect to external tools" problem brilliantly. It is complementary to the Autonomy Engine — could be used as the action layer underneath. No goal tracking, planning, alignment, or coordination.

### Summary Table — Open-Source Frameworks

| Framework | Stars | Production Ready | Goal Tracking | Planning | Alignment | Coordination |
|-----------|-------|:---:|:---:|:---:|:---:|:---:|
| LangGraph | ~18K+ | Yes | No | No | No | No |
| AutoGen | ~50K+ | Yes (maintenance) | No | No | No | No |
| CrewAI OSS | ~44K+ | Yes | No | Partial | No | Partial |
| Agency Swarm | ~3.9K | Medium | No | No | No | No |
| Agno/Phidata | ~18.5K+ | Medium-High | No | No | No | No |
| Composio | ~10K+ | Yes | No | No | No | No |
| **Autonomy Engine** | **N/A (new)** | **Early** | **Yes** | **Yes** | **Yes** | **Yes** |

---

## 3. AI-Powered IDE / Dev Tools

These compete in the broader "AI assists professionals" category.

### Cursor
- **URL:** https://cursor.com
- **Pricing:** Pro $20/mo / Business $40/user/mo
- **Target:** Software developers
- **Key differentiators:** AI-native IDE (VS Code fork), inline code generation, multi-file context, agentic features
- **Maturity:** GA — market leader in AI IDEs
- **vs. Autonomy Engine:** Cursor is a code-centric tool for developers. The Autonomy Engine is domain-agnostic and targets professionals who work across code, documents, BIM models, spreadsheets, and business workflows. No overlap in architecture; different problem spaces.

### Windsurf (Cognition/Codeium)
- **URL:** https://windsurf.com
- **Pricing:** $15/mo / $30/mo team
- **Target:** Software developers, large codebases
- **Key differentiators:** Acquired by Cognition (Devin), SWE-1.5 proprietary model, speed-optimized, enterprise security
- **Maturity:** GA — strong momentum post-acquisition
- **vs. Autonomy Engine:** Code-centric IDE. No goal tracking, planning, or alignment. Different space entirely.

### Devin (Cognition)
- **URL:** https://devin.ai
- **Pricing:** Core $20/mo (pay-as-you-go ACUs) / Team / Enterprise
- **Target:** Development teams wanting autonomous coding agents
- **Key differentiators:** Autonomous software engineer, can work on multi-hour tasks, browser + editor + terminal environment
- **Maturity:** GA — v2.0 launched 2025, dramatic price reduction from $500/mo
- **vs. Autonomy Engine:** Devin is a specialized coding agent, not a general orchestration framework. It automates software engineering tasks. The Autonomy Engine orchestrates multiple agents across diverse professional domains. Different target, different architecture.

### Claude Code (Anthropic)
- **URL:** https://claude.ai (CLI tool)
- **Pricing:** Pro $20/mo / Max $100-200/mo (API pricing for programmatic use)
- **Target:** Developers using CLI-based agentic coding
- **Key differentiators:** Agentic coding from terminal, extended thinking, tool use, MCP ecosystem
- **Maturity:** GA — Weber's primary execution substrate
- **vs. Autonomy Engine:** Claude Code is the **execution runtime** that the Autonomy Engine wraps. The Autonomy Engine adds goal tracking, planning, alignment injection, and coordination ON TOP OF Claude Code's capabilities. They are complementary, not competitive.

### GitHub Copilot Workspace
- **URL:** https://github.com/features/copilot
- **Pricing:** Copilot Pro $10/mo / Pro+ $39/mo / Business $19/user/mo / Enterprise $39/user/mo
- **Target:** GitHub-native development teams
- **Key differentiators:** Issue-to-PR workflow, multi-file code generation, deep GitHub integration, shared workspaces
- **Maturity:** GA — available to all paid Copilot users
- **vs. Autonomy Engine:** Copilot Workspace automates the GitHub issue-to-PR pipeline. It is a dev workflow tool, not a multi-domain orchestration system.

---

## 4. Vertical Agent Solutions

### AEC / BIM / Construction

The AEC sector is **remarkably underserved** by AI agent platforms. Only 27% of AEC professionals use AI, but 94% of those plan to increase usage in 2026.

| Solution | Focus | Status |
|----------|-------|--------|
| **Autodesk AI Assistants** | Geometry-based AI across Revit, AutoCAD, Civil 3D | Announced — debuting in Revit 2026, expanding 2027 |
| **Genusys AI** | Automated MEP layouts in Revit | GA — niche but production-ready |
| **Aurivus** | 3D model reconstruction from scans | GA — claims 70% modeling time reduction |
| **Boon** | AI agents for preconstruction/estimating | GA — workflow-specific |
| **ALLPLAN AI Assistant** | AI guidance on AEC standards and workflows | GA — launched with ALLPLAN 2026 |
| **WiseBIM** | AI for Autodesk Revit (Autodesk App Store) | GA — plugin-level |

**Critical gap:** None of these provide general-purpose agent orchestration for AEC professionals. They are all point solutions (BIM modeling, estimating, visualization). No one offers an orchestration layer that connects Revit automation + document analysis + client communication + project tracking with persistent goals and alignment. This is the Autonomy Engine's strongest vertical opportunity.

### Legal AI

| Solution | Focus | Pricing | Status |
|----------|-------|---------|--------|
| **Harvey AI** | Enterprise legal AI | ~$1,200/lawyer/mo (20-seat min) | GA — $195M ARR, $11B valuation |
| **CoCounsel (Thomson Reuters)** | Legal research + workflow AI | $110-400/mo | GA — Deep Research feature |
| **Spellbook** | Contract drafting | $99+/mo | GA |
| **EvenUp** | Personal injury AI | Custom | GA — niche |

**Gap for Autonomy Engine:** Legal AI is dominated by large, expensive platforms targeting Am Law 200 firms. Solo practitioners and small firms are underserved. An Autonomy Engine with legal-domain templates could offer goal-tracked case management + document analysis + client communication for a fraction of Harvey's price.

### Financial AI

| Solution | Focus | Pricing | Status |
|----------|-------|---------|--------|
| **Pigment** | FP&A with AI agents (Analyst, Planner, Modeler) | Enterprise pricing | GA |
| **Cube** | Agentic FP&A (forecasts, scenarios, variance) | Enterprise pricing | GA |
| **DataSnipper** | Agentic AI in Excel for audit | Enterprise pricing | GA |
| **Hazel (Altruist)** | Autonomous tax-planning/wealth AI | Unknown | New |

**Gap for Autonomy Engine:** Financial AI agents are enterprise-priced and enterprise-targeted. Small accounting firms and independent financial advisors lack affordable, goal-driven agent systems.

---

## 5. Gap Analysis

### What the Autonomy Engine Does That NO Competitor Does

The Autonomy Engine is unique in combining **all four pillars** in a single integrated system:

**1. Hierarchical Goal Tracking (goals.py)**
- Persistent goal trees with parent-child relationships and dependency graphs
- Priority-weighted progress rollup from children to parents
- Actionable goal detection (active + no blockers + leaf = work on NOW)
- Stale goal detection and audit trails
- Brain.json sync for cross-session persistence
- **No competitor has this.** CrewAI has task assignment. Cognosys has rudimentary goal decomposition. But nobody has persistent, hierarchical, dependency-aware goal trees with rollup.

**2. Autonomous Planning (planner.py)**
- Goal-to-plan decomposition with template matching
- Multi-step plans with agent assignment, dependency tracking, parallel execution detection
- Adaptive replanning on failure (replan from step N with new steps)
- Fallback agent assignment when primary agent fails
- Plan promotion to reusable templates (learning from success)
- Workflow integration (record and replay successful patterns)
- **No competitor has this depth.** LangGraph has state machines. CrewAI has crew task decomposition. But nobody auto-generates plans from goal descriptions, matches templates, and adaptively replans with fallback agents.

**3. Alignment Injection (alignment.py)**
- Automatic compilation of alignment prompts for sub-agents
- Domain detection from task description
- Multi-layer principle system (core > correction > user > domain)
- Kernel + corrections + strong agent framework injection into every sub-agent
- Drift detection and violation tracking
- Outcome verification against principles
- Token-budget-aware trimming
- **This is completely unique.** No framework ensures sub-agents receive alignment data. In every other system, sub-agents start from a blank slate. The Autonomy Engine is the only system where a sub-agent automatically inherits the main agent's corrections, common sense, and domain-specific principles.

**4. Cross-Agent Coordination (coordinator.py)**
- Workflow session tracking with agent lifecycle management
- Resource locking (exclusive/shared) with conflict detection and expiration
- Shared state between agents within a workflow
- Handoff validation (ensures clean transitions between sequential agents)
- Accumulated context injection (later agents see results from earlier agents)
- Stale session cleanup
- **No competitor has resource locking for agents.** CrewAI has collaboration between roles. LangGraph has shared state via checkpoints. But nobody has resource locking to prevent two agents from editing the same Revit model simultaneously, with handoff validation and accumulated context.

### What Competitors Do Better

| Capability | Best Competitor | How They're Better |
|-----------|----------------|-------------------|
| **Scale / Production deployment** | LangGraph Platform, CrewAI Enterprise | Battle-tested at Klarna (85M users). Autonomy Engine is early-stage. |
| **No-code agent building** | Lindy AI, Relevance AI, Zapier | Beautiful drag-and-drop UIs. Autonomy Engine requires Python/CLI. |
| **Integration breadth** | Composio (500+ tools), Lindy (4,000+ apps) | Massive pre-built connector libraries. Autonomy Engine relies on MCP + custom tools. |
| **Community size** | AutoGen (50K stars), CrewAI (44K stars) | Orders of magnitude more contributors and ecosystem. |
| **Enterprise features** | All commercial platforms | SSO, SCIM, audit logs, compliance, SLAs. Autonomy Engine has none. |
| **Multi-modal support** | Agno/Phidata | Text, images, audio, video natively. Autonomy Engine is text-primary. |
| **Computer use** | Adept, Lindy Autopilot, Devin | GUI automation at scale. Autonomy Engine delegates to Claude Code's computer use. |
| **Documentation & onboarding** | LangGraph, CrewAI | Extensive docs, tutorials, courses. Autonomy Engine has code + docstrings. |

### Where's the Moat?

The Autonomy Engine's moat is **not technical complexity** — any competent team could build individual components. The moat is:

1. **Integration of all four pillars.** Building goal tracking is easy. Building planning is easy. Building alignment injection is easy. Building coordination is easy. Making all four work together, with corrections flowing from coordination back into alignment back into planning back into goals — that is hard and nobody is doing it.

2. **Opinionated about alignment.** Every other framework is a "bring your own alignment" system. The Autonomy Engine ships with a common-sense kernel, correction-based learning, drift detection, and verification. It has an opinion about how agents should behave.

3. **Designed for professionals, not developers.** Most open-source frameworks require significant engineering to be useful. The Autonomy Engine is designed to wrap Claude Code and make a solo architect, engineer, or small-firm owner more autonomous — not to be a developer tool.

4. **Correction-driven evolution.** The kernel-corrections system means the Autonomy Engine gets smarter with use. Mistakes are stored, corrections are injected into future sub-agents, and correction effectiveness is tracked. This creates a personalized, self-improving system that no SaaS platform offers.

5. **Vertical potential (AEC/BIM).** The AEC vertical is dramatically underserved by AI agent platforms. The Autonomy Engine already has Revit-specific templates (pdf-to-revit-model, BIM validation), domain keywords for BIM, and integration with RevitMCPBridge. No other agent framework has any BIM awareness whatsoever.

### Strategic Positioning

```
                    Enterprise ────────────────────── Individual
                         |                                |
                         |   Harvey, Adept, Dust          |
      High               |   LangGraph Platform           |
      Complexity          |   CrewAI Enterprise            |
                         |                                |
                         |                                |
                         |          AUTONOMY ENGINE       |
                         |          (Goal-Driven,         |
                         |           Aligned,             |
                         |           Professional)        |
                         |                                |
                         |                                |
      Low                |                     Lindy AI   |
      Complexity         |                     Relevance  |
                         |                     Cognosys   |
                         |                                |
                    Enterprise ────────────────────── Individual
```

The Autonomy Engine sits in the **medium-complexity, individual/small-firm** quadrant where no one else competes with a full goal-plan-align-coordinate stack.

---

## Key Takeaways

1. **The market is massive and growing fast** — but fragmented between expensive enterprise tools and developer-only open-source frameworks.

2. **Nobody has all four pillars** — this is the Autonomy Engine's unique value proposition and should be the centerpiece of any positioning.

3. **AEC/BIM is a blue ocean** — only 27% of AEC professionals use AI, and existing solutions are all point tools. A goal-driven agent orchestration system for architects and engineers would be first-to-market.

4. **The biggest gap is alignment** — every other system treats sub-agents as stateless. The Autonomy Engine's correction-driven alignment injection is genuinely novel.

5. **The biggest weakness is maturity** — community size, documentation, production hardening, and enterprise features are all areas where competitors are far ahead. This is the execution risk.

6. **Composio and LangGraph are allies, not enemies** — they solve different layers (integration and execution respectively). The Autonomy Engine could sit on top of both.

---

## Sources

### Commercial Platforms
- [Relevance AI Pricing](https://relevanceai.com/pricing)
- [CrewAI Pricing](https://www.crewai.com/pricing)
- [Cognosys / Ottogrid](https://www.cognosys.ai/pricing)
- [Adept AI](https://www.adept.ai/)
- [Lindy AI Pricing](https://www.lindy.ai/pricing)
- [Dust.tt Pricing](https://dust.tt/home/pricing)

### Open-Source Frameworks
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [AutoGen GitHub](https://github.com/microsoft/autogen)
- [CrewAI GitHub](https://github.com/crewAIInc/crewAI)
- [Agency Swarm GitHub](https://github.com/VRSEN/agency-swarm)
- [Agno (Phidata) GitHub](https://github.com/agno-agi/agno)
- [Composio GitHub](https://github.com/ComposioHQ/composio)

### AI IDEs / Dev Tools
- [Cursor vs Windsurf Comparison](https://windsurf.com/compare/windsurf-vs-cursor)
- [Devin 2.0 — VentureBeat](https://venturebeat.com/programming-development/devin-2-0-is-here-cognition-slashes-price-of-ai-software-engineer-to-20-per-month-from-500)
- [Claude Code Pricing](https://claudelog.com/claude-code-pricing/)
- [GitHub Copilot Plans](https://github.com/features/copilot/plans)

### Vertical Solutions
- [40 AI-Driven AEC Solutions — BuiltWorlds](https://builtworlds.com/news/40-ai-driven-aec-solutions-to-know-in-2026/)
- [Harvey AI Valuation — Techietory](https://techietory.com/news/harvey-ai-raises-200-million-11-billion-valuation-legal-platform-2026/)
- [AI Agents for Finance — RTS Labs](https://rtslabs.com/ai-agents-for-finance/)
- [ASCE: AEC Slow to Adopt AI](https://www.asce.org/publications-and-news/civil-engineering-source/article/2025/12/18/architecture-engineering-construction-sector-slow-to-adapt-ai-survey-shows)

### Market Analysis
- [Top 10 Most Starred AI Agent Frameworks (2026) — Medium](https://techwithibrahim.medium.com/top-10-most-starred-ai-agent-frameworks-on-github-2026-df6e760a950b)
- [Top 7 Agentic AI Frameworks in 2026 — AlphaMatch](https://www.alphamatch.ai/blog/top-agentic-ai-frameworks-2026)
- [No-Code AI Agent Builders — Lindy](https://www.lindy.ai/blog/no-code-ai-agent-builder)
- [AI Agent Orchestration Patterns — Microsoft](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)

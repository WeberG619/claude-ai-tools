"""Proposal agent - drafts proposals using templates and AI."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.database import Database
from core.models import Opportunity, Proposal, Template, ProposalStatus, OpportunityStatus
from core.config import TEMPLATES_DIR, TEMPLATE_CATEGORIES, SKILLS

logger = logging.getLogger("opportunityengine.agents.proposal")


class ProposalAgent:
    """Drafts, refines, and manages proposals for qualified opportunities."""

    def __init__(self, db: Database):
        self.db = db
        self._ensure_templates_loaded()

    def _ensure_templates_loaded(self):
        """Load/refresh templates from markdown files into DB."""
        existing = self.db.list_templates()
        existing_map = {t.name: t for t in existing}

        for cat_name, cat_info in TEMPLATE_CATEGORIES.items():
            filepath = os.path.join(TEMPLATES_DIR, cat_info["file"])
            if not os.path.exists(filepath):
                continue
            with open(filepath, "r") as f:
                content = f.read()

            if cat_name not in existing_map:
                # New template — insert
                tmpl = Template(
                    name=cat_name,
                    category=", ".join(cat_info["match_skills"]),
                    content=content,
                )
                self.db.insert_template(tmpl)
                logger.info(f"Loaded template: {cat_name}")
            elif existing_map[cat_name].content != content:
                # Content changed on disk — update DB (preserve stats)
                self.db.update_template(existing_map[cat_name].id, content=content)
                logger.info(f"Refreshed template: {cat_name}")

    def draft_proposal(self, opp_id: int) -> Proposal:
        """Draft a proposal for an opportunity.

        1. Load the opportunity
        2. Select best template
        3. Generate personalized proposal via Claude
        4. Save as draft
        """
        opp = self.db.get_opportunity(opp_id)
        if not opp:
            raise ValueError(f"Opportunity {opp_id} not found")

        # Check if proposal already exists
        existing = self.db.get_proposal_for_opportunity(opp_id)
        if existing and existing.status in (ProposalStatus.APPROVED, ProposalStatus.SUBMITTED):
            raise ValueError(f"Opportunity {opp_id} already has an {existing.status} proposal")

        # Select best template
        template = self._select_template(opp)
        template_name = template.name if template else "none"
        template_content = template.content if template else ""

        # Generate proposal content
        content = self._generate_proposal(opp, template_content)

        # Suggest pricing
        pricing = self._suggest_pricing(opp)

        # Create proposal
        proposal = Proposal(
            opportunity_id=opp_id,
            content=content,
            pricing=pricing,
            template_used=template_name,
            status=ProposalStatus.DRAFT,
            created_at=datetime.utcnow().isoformat(),
        )
        proposal.id = self.db.insert_proposal(proposal)

        # Update opportunity status
        self.db.update_opportunity(opp_id, status=OpportunityStatus.PROPOSAL_DRAFTED)

        # Track template usage
        if template:
            self.db.update_template(
                template.id,
                times_used=template.times_used + 1,
                last_used=datetime.utcnow().isoformat(),
            )

        logger.info(f"Drafted proposal for opp #{opp_id} using template '{template_name}'")
        return proposal

    # ── Job classification ─────────────────────────────────────────────

    # Classification keywords — checked against title + description + skills
    _JOB_CLASSES = {
        "bim_revit": {
            "keywords": ["revit", "revit api", "pyrevit", "dynamo", "bim", "building information",
                         "autocad", "navisworks", "ifc", "cad", "architectural model", "revit plugin",
                         "revit addin", "revit add-in", "autodesk"],
            "weight": 3,  # High weight — this is Weber's killer differentiator
        },
        "construction_docs": {
            "keywords": ["construction documents", "cd set", "permit drawings", "architectural drawings",
                         "permit", "building code", "floor plan", "elevation", "section drawing",
                         "as-built", "schematic design", "design development"],
            "weight": 2,
        },
        "ai_automation": {
            "keywords": ["ai agent", "autonomous", "llm", "claude", "gpt", "openai", "langchain",
                         "mcp server", "tool use", "chatbot", "conversational ai", "ai automation",
                         "machine learning", "rag", "retrieval augmented", "fine-tun", "prompt engineer",
                         "ai assistant", "agent framework", "agentic"],
            "weight": 2,
        },
        "web_scraping": {
            "keywords": ["scraping", "scraper", "web scraping", "data extraction", "crawl",
                         "selenium", "playwright", "puppeteer", "beautifulsoup", "scrapy",
                         "parse website", "extract data from"],
            "weight": 2,
        },
        "software_dev": {
            "keywords": ["python", "javascript", "typescript", "react", "node", "django", "flask",
                         "fastapi", "c#", ".net", "api", "rest api", "graphql", "full stack",
                         "fullstack", "backend", "frontend", "database", "sql", "web app",
                         "mobile app", "saas"],
            "weight": 1,  # Lower weight — generic, only wins if nothing else matches
        },
        "github_bounty": {
            "keywords": ["bounty", "issue", "pull request", "open source", "contribution",
                         "bug fix", "feature request"],
            "weight": 1,
        },
    }

    @classmethod
    def _classify_opportunity(cls, opp: Opportunity) -> str:
        """Classify an opportunity into a job category.

        Returns one of: bim_revit, construction_docs, ai_automation,
        web_scraping, software_dev, github_bounty, general.
        """
        text = f"{opp.title} {opp.description}".lower()
        skills_text = " ".join(s.lower() for s in opp.skills_required)
        combined = f"{text} {skills_text}"

        scores = {}
        for cls_name, cls_info in cls._JOB_CLASSES.items():
            hits = sum(1 for kw in cls_info["keywords"] if kw in combined)
            if hits > 0:
                scores[cls_name] = hits * cls_info["weight"]

        if not scores:
            return "general"

        # GitHub source gets a boost for github_bounty
        if opp.source == "github" and "github_bounty" in scores:
            scores["github_bounty"] *= 2

        return max(scores, key=scores.get)

    def _select_template(self, opp: Opportunity) -> Optional[Template]:
        """Select the best template based on job classification + skill overlap."""
        templates = self.db.list_templates()
        if not templates:
            return None

        job_class = self._classify_opportunity(opp)
        opp_text = f"{opp.title} {opp.description}".lower()
        opp_skills = [s.lower() for s in opp.skills_required]

        # Map job class → preferred template name
        class_to_template = {
            "bim_revit": "revit_bim",
            "construction_docs": "construction_docs",
            "ai_automation": "ai_automation",
            "web_scraping": "web_scraping",
            "software_dev": "software_dev",
            "github_bounty": "github_bounty",
            "general": "general",
        }

        best_template = None
        best_score = -1

        for tmpl in templates:
            cat_info = TEMPLATE_CATEGORIES.get(tmpl.name, {})
            match_skills = cat_info.get("match_skills", [])

            score = 0
            for skill_name in match_skills:
                skill_data = SKILLS.get(skill_name, {})
                for keyword in skill_data.get("keywords", []):
                    kw = keyword.lower()
                    if kw in opp_text or any(kw in s for s in opp_skills):
                        score += 1
                        break

            # Big bonus if template matches the classified job type
            preferred = class_to_template.get(job_class)
            if tmpl.name == preferred:
                score += 5

            # Bonus for win rate
            if tmpl.win_rate > 0:
                score += tmpl.win_rate / 50

            if score > best_score:
                best_score = score
                best_template = tmpl

        return best_template

    def _generate_proposal(self, opp: Opportunity, template_content: str) -> str:
        """Generate a personalized proposal using Claude CLI."""
        prompt = self._build_prompt(opp, template_content)

        try:
            result = subprocess.run(
                ["claude", "--print"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0 and result.stdout.strip():
                return self._clean_proposal(result.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Claude CLI unavailable ({e}), using template fallback")

        # Fallback: fill template placeholders
        return self._template_fallback(opp, template_content)

    @staticmethod
    def _clean_proposal(text: str) -> str:
        """Strip AI meta-commentary that shouldn't appear in final proposals."""
        # ── Leading preamble patterns ──
        preamble_patterns = [
            r"^Here.s (?:the|a|my) (?:drafted|tailored|personalized|professional|custom|winning) proposal.*?:\s*\n+---\s*\n+",
            r"^Here.s (?:the|a|my) (?:drafted|tailored|personalized|professional|custom|winning) proposal.*?:\s*\n+",
            r"^Here.s (?:the|a|my) proposal.*?:\s*\n+",
            r"^(?:Draft|Proposal|Response|Message):\s*\n+---\s*\n+",
            r"^(?:Draft|Proposal|Response|Message):\s*\n+",
            r"^Sure[,!]?\s+[Hh]ere.s.*?:\s*\n+",
            r"^(?:Absolutely|Certainly)[,!]?\s+[Hh]ere.s.*?:\s*\n+",
            r"^---\s*\n+",
        ]
        for pat in preamble_patterns:
            text = re.sub(pat, "", text, flags=re.DOTALL)

        # ── Trailing analysis / meta-commentary ──
        trailing_patterns = [
            r"\n+---\s*\n+\*\*Key choices.*$",
            r"\n+---\s*\n+\*\*Notes?:?\*\*.*$",
            r"\n+---\s*\n+\*\*Why this works.*$",
            r"\n+---\s*\n+\*\*Strategy.*$",
            r"\n+---\s*\n+\*\*Tone.*$",
            r"\n+---\s*\n+\*\*This (?:proposal|draft|response).*$",
            r"\n+---\s*\n+This (?:proposal|draft|message) (?:is|was|keeps|uses|maintains).*$",
            r"\n+---\s*\n+(?:I|The) (?:kept|used|chose|went with|focused|avoided|highlighted).*$",
            r"\n+---\s*$",
            # No separator — just trailing meta starting with common AI commentary
            r"\n{2,}(?:Concise|Short|Professional|Direct|This draft|This proposal|This response|This message|I (?:kept|focused|avoided|used|chose|went)).*$",
            r"\n{2,}\*(?:This|Note|Approach|The proposal|Word count|I focused).*$",
        ]
        for pat in trailing_patterns:
            text = re.sub(pat, "", text, flags=re.DOTALL)

        return text.strip()

    # ── Bio fragments — only the relevant one gets included ────────────

    _BIO_BIM_REVIT = """\
- Built RevitMCPBridge — open-source project with 705+ API endpoints connecting AI to Autodesk Revit (github.com/WeberG619/RevitMCPBridge2026)
- Official Autodesk Developer Network (ADN) member
- 15 years in architecture/AEC — you understand BIM workflows, building codes, and construction documents, not just code
- Revit 2024-2026, pyRevit, Dynamo, AutoCAD, Navisworks
- Website: bimopsstudio.com | GitHub: github.com/WeberG619"""

    _BIO_CONSTRUCTION_DOCS = """\
- AEC background with 15 years producing construction document sets
- BIM specialist — Revit, AutoCAD, BIM coordination workflows
- Familiar with South Florida building codes, FBC, and permitting
- Production experience with CD sets, permit drawings, and as-built documentation
- Website: bimopsstudio.com"""

    _BIO_AI_AUTOMATION = """\
- Built 50+ production autonomous agents with Claude API, MCP servers, and tool-use architectures
- Designed multi-agent orchestration systems that run 24/7 in production
- Full-stack: Python, C#, TypeScript, FastAPI, React
- Experience with RAG pipelines, structured outputs, cost optimization, and monitoring
- GitHub: github.com/WeberG619"""

    _BIO_WEB_SCRAPING = """\
- Built production scraping systems handling anti-bot protection, JS-rendered content, and CAPTCHAs
- Tools: Playwright, Selenium, Scrapy, CDP (Chrome DevTools Protocol)
- Full pipeline: extraction → cleaning → delivery (CSV, JSON, databases)
- Proxy rotation, rate limiting, error recovery, and monitoring built in
- GitHub: github.com/WeberG619"""

    _BIO_SOFTWARE_DEV = """\
- Full-stack developer: Python, C#, TypeScript, React, FastAPI, Django
- REST APIs, GraphQL, SQL/PostgreSQL/MongoDB, cloud deployment
- Ship fast with clean, tested code — typically working first version in days
- GitHub: github.com/WeberG619"""

    _BIO_GITHUB_BOUNTY = """\
- Active open-source contributor (Python, C#, TypeScript)
- Write clean, tested code that follows existing project conventions
- Quick turnaround on PRs with responsive review iteration
- GitHub: github.com/WeberG619"""

    _BIO_GENERAL = """\
- Developer and automation specialist — Python, C#, TypeScript
- API development, data processing, full-stack web apps
- Ship reliable systems that run without babysitting
- GitHub: github.com/WeberG619"""

    _CLASS_TO_BIO = {
        "bim_revit": _BIO_BIM_REVIT,
        "construction_docs": _BIO_CONSTRUCTION_DOCS,
        "ai_automation": _BIO_AI_AUTOMATION,
        "web_scraping": _BIO_WEB_SCRAPING,
        "software_dev": _BIO_SOFTWARE_DEV,
        "github_bounty": _BIO_GITHUB_BOUNTY,
        "general": _BIO_GENERAL,
    }

    # ── Lead-in hooks per job class ──────────────────────────────────

    _CLASS_HOOKS = {
        "bim_revit": "Lead with your deep Revit/BIM domain expertise. Mention RevitMCPBridge as your differentiator. Show you understand their BIM workflow, not just coding.",
        "construction_docs": "Lead with your architectural background and CD production experience. Show you know building codes and permit requirements. Mention local South Florida experience if relevant.",
        "ai_automation": "Lead with production AI systems you've built — not demos or tutorials. Mention autonomous agents, multi-agent orchestration, tool-use architectures. Show you know the difference between a chatbot wrapper and a real system.",
        "web_scraping": "Lead with technical scraping expertise. Mention specific tools (Playwright, CDP, Scrapy). Show you build scrapers that keep working, not one-shot scripts.",
        "software_dev": "Lead with speed and reliability. Show you ship working code fast. Reference the specific tech stack they need.",
        "github_bounty": "Show you've already looked at the issue and the codebase. Propose a concrete implementation approach. Keep it technical and brief.",
        "general": "Lead with relevant experience closest to their needs. Be concrete about what you'd deliver and how quickly.",
    }

    def _build_prompt(self, opp: Opportunity, template: str) -> str:
        """Build a job-type-aware prompt for Claude to draft a proposal."""
        job_class = self._classify_opportunity(opp)
        bio = self._CLASS_TO_BIO.get(job_class, self._BIO_GENERAL)
        hook = self._CLASS_HOOKS.get(job_class, self._CLASS_HOOKS["general"])

        # Platform tone
        if opp.source in ("reddit", "hackernews"):
            tone = "Short, direct, casual-professional. No 'Dear Hiring Manager'. Reddit/HN users hate corporate speak. 100-200 words max."
        elif opp.source == "github":
            tone = "Technical, concise. Show you understand the codebase. No sales language. 80-150 words."
        elif opp.source in ("upwork", "freelancer"):
            tone = "Professional but warm. Show personality. 150-250 words."
        else:
            tone = "Professional, concise. 150-250 words."

        return f"""Write a freelance proposal as Weber Gouin. Output ONLY the proposal text — no preamble, no "Here's the proposal:", no "---", no post-analysis.

**JOB:**
Title: {opp.title}
Platform: {opp.source}
Budget: {opp.budget_display}
Skills needed: {', '.join(opp.skills_required) if opp.skills_required else 'Not specified'}

Description:
{opp.description[:2500]}

**YOUR BACKGROUND (Weber Gouin) — ONLY mention what's relevant to THIS job:**
{bio}

**APPROACH FOR THIS JOB:**
{hook}

**TONE:** {tone}

**TEMPLATE (follow this structure loosely):**
{template[:1500] if template else 'No template — write a professional, concise proposal.'}

**RULES:**
1. First sentence must reference something SPECIFIC from their job description — prove you read it
2. ONLY mention experience relevant to THIS job. Do NOT mention Revit/BIM unless the job is about Revit/BIM. Do NOT mention AI agents unless the job is about AI.
3. Propose a concrete first step or technical approach for their specific problem
4. End with availability and a question that moves the conversation forward
5. Do NOT include pricing
6. NEVER start with "I'm interested in your project" or "I noticed your posting"
7. Sound like a senior engineer talking to a peer, not a salesperson
8. Sign off as "Weber Gouin" (just the name, no titles)
"""

    # Fallback openers per job class (when Claude CLI is unavailable)
    _FALLBACK_OPENERS = {
        "bim_revit": (
            "I'm a Revit API developer with 700+ production methods and 15 years in AEC — "
            "I understand BIM workflows, not just code."
        ),
        "construction_docs": (
            "I have 15 years producing construction document sets and understand what it takes "
            "to get from design development to permit-ready drawings."
        ),
        "ai_automation": (
            "I build production AI systems — autonomous agents, multi-agent orchestration, "
            "and tool-use architectures that run 24/7, not chatbot demos."
        ),
        "web_scraping": (
            "I build production scraping systems with Playwright, CDP, and Scrapy — "
            "scrapers that keep working, not one-shot scripts that break."
        ),
        "software_dev": (
            "I'm a full-stack developer shipping production code in Python, C#, and TypeScript "
            "daily — fast turnaround with clean, tested results."
        ),
        "github_bounty": (
            "I've looked at this issue and have a clear path to a solution. "
            "I write clean, tested code that follows existing project conventions."
        ),
        "general": (
            "I'm a developer and automation specialist — Python, C#, TypeScript — "
            "shipping reliable systems that run without babysitting."
        ),
    }

    def _template_fallback(self, opp: Opportunity, template: str) -> str:
        """Placeholder replacement when AI isn't available — job-type-aware."""
        job_class = self._classify_opportunity(opp)
        skills_text = ', '.join(opp.skills_required[:3]) if opp.skills_required else 'this area'

        if not template:
            opener = self._FALLBACK_OPENERS.get(job_class, self._FALLBACK_OPENERS["general"])
            return (
                f"Hi,\n\n"
                f"{opener}\n\n"
                f"For {skills_text} work like this, I can typically deliver a working solution fast.\n\n"
                f"Can we discuss the specifics? I can start immediately.\n\n"
                f"Best,\nWeber Gouin"
            )

        content = template
        # Don't dump raw description into template — use a brief summary
        desc_summary = opp.description[:200].rsplit(' ', 1)[0] + "..." if len(opp.description) > 200 else opp.description
        replacements = {
            "{{title}}": opp.title,
            "{{description}}": desc_summary,
            "{{skills}}": ", ".join(opp.skills_required[:5]) if opp.skills_required else "relevant technologies",
            "{{budget}}": opp.budget_display,
            "{{source}}": opp.source,
        }
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)

        return content

    def _suggest_pricing(self, opp: Opportunity) -> str:
        """Suggest competitive pricing based on budget range."""
        if opp.budget_min and opp.budget_max and opp.budget_min != opp.budget_max:
            # Bid in the lower-middle of range to be competitive
            suggested = opp.budget_min + (opp.budget_max - opp.budget_min) * 0.4
            return f"${suggested:,.0f}"
        elif opp.budget_max:
            return f"${opp.budget_max * 0.85:,.0f}"
        elif opp.budget_min:
            return f"${opp.budget_min:,.0f}"
        return "To be discussed"

    def approve_proposal(self, opp_id: int) -> Proposal:
        """Mark a proposal as approved for submission."""
        prop = self.db.get_proposal_for_opportunity(opp_id)
        if not prop:
            raise ValueError(f"No proposal found for opportunity {opp_id}")
        if prop.status != ProposalStatus.DRAFT:
            raise ValueError(f"Proposal is '{prop.status}', expected 'draft'")

        self.db.update_proposal(
            prop.id,
            status=ProposalStatus.APPROVED,
            approved_at=datetime.utcnow().isoformat(),
        )
        prop.status = ProposalStatus.APPROVED
        return prop

    def mark_submitted(self, opp_id: int) -> Proposal:
        """Mark a proposal as submitted to the platform."""
        prop = self.db.get_proposal_for_opportunity(opp_id)
        if not prop:
            raise ValueError(f"No proposal found for opportunity {opp_id}")

        now = datetime.utcnow().isoformat()
        self.db.update_proposal(
            prop.id,
            status=ProposalStatus.SUBMITTED,
            submitted_at=now,
        )
        self.db.update_opportunity(
            opp_id,
            status=OpportunityStatus.SUBMITTED,
            submitted_at=now,
        )
        prop.status = ProposalStatus.SUBMITTED
        return prop

    def record_outcome(self, opp_id: int, won: bool, lessons: str = ""):
        """Record win/loss and update template stats."""
        opp = self.db.get_opportunity(opp_id)
        if not opp:
            raise ValueError(f"Opportunity {opp_id} not found")

        prop = self.db.get_proposal_for_opportunity(opp_id)
        new_status = OpportunityStatus.WON if won else OpportunityStatus.LOST
        now = datetime.utcnow().isoformat()

        self.db.update_opportunity(opp_id, status=new_status, resolved_at=now)

        if prop:
            prop_status = ProposalStatus.ACCEPTED if won else ProposalStatus.REJECTED
            self.db.update_proposal(
                prop.id,
                status=prop_status,
                lessons_learned=lessons,
            )

            # Update template stats
            tmpl = self.db.get_template_by_name(prop.template_used)
            if tmpl:
                updates = {"wins": tmpl.wins + 1} if won else {"losses": tmpl.losses + 1}
                self.db.update_template(tmpl.id, **updates)

        logger.info(f"Recorded {'WIN' if won else 'LOSS'} for opp #{opp_id}")

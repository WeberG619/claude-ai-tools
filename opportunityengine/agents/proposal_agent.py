"""Proposal agent - drafts proposals using templates and AI."""

from __future__ import annotations

import logging
import os
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
        """Load templates from markdown files into DB if not already present."""
        existing = self.db.list_templates()
        existing_names = {t.name for t in existing}

        for cat_name, cat_info in TEMPLATE_CATEGORIES.items():
            if cat_name in existing_names:
                continue
            filepath = os.path.join(TEMPLATES_DIR, cat_info["file"])
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    content = f.read()
                tmpl = Template(
                    name=cat_name,
                    category=", ".join(cat_info["match_skills"]),
                    content=content,
                )
                self.db.insert_template(tmpl)
                logger.info(f"Loaded template: {cat_name}")

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

    def _select_template(self, opp: Opportunity) -> Optional[Template]:
        """Select the best template based on skill overlap."""
        templates = self.db.list_templates()
        if not templates:
            return None

        opp_text = f"{opp.title} {opp.description}".lower()
        opp_skills = [s.lower() for s in opp.skills_required]

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
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"Claude CLI unavailable ({e}), using template fallback")

        # Fallback: fill template placeholders
        return self._template_fallback(opp, template_content)

    def _build_prompt(self, opp: Opportunity, template: str) -> str:
        """Build the prompt for Claude to draft a proposal."""
        return f"""Draft a professional freelance proposal for this opportunity.

**Job Title:** {opp.title}
**Platform:** {opp.source}
**Budget:** {opp.budget_display}
**Required Skills:** {', '.join(opp.skills_required) if opp.skills_required else 'Not specified'}

**Job Description:**
{opp.description[:3000]}

**Template Style:**
{template[:2000] if template else 'Write a professional, concise proposal.'}

**Instructions:**
- Write as Weber Gouin, a BIM/Revit specialist and full-stack developer
- Highlight relevant experience: 700+ Revit API methods, automation expertise, AEC background
- Be specific about technical approach for THEIR needs
- Keep it concise (200-400 words)
- Professional but personable tone
- Include a brief mention of timeline
- Do NOT include pricing (that's handled separately)
- Do NOT include generic filler - every sentence should add value
- Match the platform norms ({opp.source})
"""

    def _template_fallback(self, opp: Opportunity, template: str) -> str:
        """Simple placeholder replacement when AI isn't available."""
        if not template:
            return (
                f"Hi,\n\n"
                f"I'm interested in your project: {opp.title}\n\n"
                f"With extensive experience in {', '.join(opp.skills_required[:3]) if opp.skills_required else 'this area'}, "
                f"I can deliver quality results efficiently.\n\n"
                f"I'd love to discuss the details.\n\n"
                f"Best,\nWeber Gouin"
            )

        content = template
        replacements = {
            "{{title}}": opp.title,
            "{{description}}": opp.description[:500],
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

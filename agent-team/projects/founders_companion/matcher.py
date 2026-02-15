"""
Founder's Companion - Founder Match System
==========================================
AI-powered matching to connect founders facing similar challenges.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import random

from models import (
    Founder, FounderMatch, Message, ChallengeCategory,
    StartupStage, MoodLevel, SubscriptionTier
)
from config import get_config


class FounderMatcher:
    """
    Matches founders based on shared challenges and compatibility.

    Matching factors:
    1. Common challenges (highest weight)
    2. Similar startup stage
    3. Industry overlap
    4. Complementary experience
    5. Timezone proximity
    """

    # How much weight each factor gets in compatibility
    WEIGHTS = {
        "challenges": 0.40,
        "stage": 0.25,
        "industry": 0.15,
        "experience": 0.10,
        "timezone": 0.10
    }

    # Minimum score to suggest a match
    MIN_COMPATIBILITY = 0.50

    def __init__(self, database):
        self.db = database
        self.config = get_config()

    def find_matches(
        self,
        founder: Founder,
        limit: int = 5
    ) -> List[Tuple[Founder, float, List[ChallengeCategory]]]:
        """
        Find compatible founders for matching.

        Returns list of (founder, compatibility_score, common_challenges)
        """
        # Check if founder is open to matching
        if not founder.open_to_matching:
            return []

        # Check subscription allows matching
        if founder.tier == SubscriptionTier.SOLO:
            return []

        # Get all potential matches
        candidates = self.db.get_matchable_founders(
            exclude_id=founder.id,
            open_to_matching=True
        )

        # Calculate compatibility scores
        scored_matches = []
        for candidate in candidates:
            score, common = self._calculate_compatibility(founder, candidate)
            if score >= self.MIN_COMPATIBILITY:
                scored_matches.append((candidate, score, common))

        # Sort by score and return top matches
        scored_matches.sort(key=lambda x: x[1], reverse=True)
        return scored_matches[:limit]

    def create_match(
        self,
        founder_1: Founder,
        founder_2: Founder,
        auto_accept: bool = False
    ) -> FounderMatch:
        """Create a new match between two founders."""
        score, common = self._calculate_compatibility(founder_1, founder_2)

        match = FounderMatch(
            founder_1_id=founder_1.id,
            founder_2_id=founder_2.id,
            compatibility_score=score,
            common_challenges=common,
            match_reason=self._generate_match_reason(common, score),
            status="pending"
        )

        if auto_accept:
            match.founder_1_accepted = True
            match.founder_2_accepted = True
            match.status = "active"

        self.db.save_match(match)
        return match

    def accept_match(self, match_id: str, founder_id: str) -> Optional[FounderMatch]:
        """Accept a pending match."""
        match = self.db.get_match(match_id)
        if not match:
            return None

        if match.founder_1_id == founder_id:
            match.founder_1_accepted = True
        elif match.founder_2_id == founder_id:
            match.founder_2_accepted = True
        else:
            return None

        # Check if both accepted
        if match.founder_1_accepted and match.founder_2_accepted:
            match.status = "active"

        self.db.update_match(match)
        return match

    def decline_match(self, match_id: str, founder_id: str) -> Optional[FounderMatch]:
        """Decline a pending match."""
        match = self.db.get_match(match_id)
        if not match:
            return None

        if match.founder_1_id != founder_id and match.founder_2_id != founder_id:
            return None

        match.status = "declined"
        match.ended_at = datetime.now()
        match.end_reason = "declined"

        self.db.update_match(match)
        return match

    def send_message(
        self,
        match: FounderMatch,
        sender: Founder,
        content: str
    ) -> Optional[Message]:
        """Send a message in an active match."""
        if match.status != "active":
            return None

        if sender.id not in [match.founder_1_id, match.founder_2_id]:
            return None

        message = Message(
            match_id=match.id,
            sender_id=sender.id,
            content=content
        )

        # Update match activity
        match.messages_exchanged += 1
        match.last_interaction = datetime.now()

        self.db.save_message(message)
        self.db.update_match(match)

        return message

    def reveal_identity(self, match_id: str, founder_id: str) -> Optional[FounderMatch]:
        """Reveal real identity to match partner."""
        match = self.db.get_match(match_id)
        if not match or match.status != "active":
            return None

        if match.founder_1_id == founder_id:
            match.founder_1_revealed = True
        elif match.founder_2_id == founder_id:
            match.founder_2_revealed = True
        else:
            return None

        self.db.update_match(match)
        return match

    def end_match(
        self,
        match_id: str,
        founder_id: str,
        reason: str = "ended by user"
    ) -> Optional[FounderMatch]:
        """End an active match."""
        match = self.db.get_match(match_id)
        if not match:
            return None

        if founder_id not in [match.founder_1_id, match.founder_2_id]:
            return None

        match.status = "ended"
        match.ended_at = datetime.now()
        match.end_reason = reason

        self.db.update_match(match)
        return match

    def _calculate_compatibility(
        self,
        founder_1: Founder,
        founder_2: Founder
    ) -> Tuple[float, List[ChallengeCategory]]:
        """
        Calculate compatibility score between two founders.

        Returns (score 0-1, list of common challenges)
        """
        # Challenge overlap (most important)
        common_challenges = [
            c for c in founder_1.current_challenges
            if c in founder_2.current_challenges
        ]
        challenge_score = min(1.0, len(common_challenges) / 2)  # 2+ common = max

        # Stage similarity
        stage_diff = abs(
            list(StartupStage).index(founder_1.stage) -
            list(StartupStage).index(founder_2.stage)
        )
        stage_score = max(0, 1 - (stage_diff * 0.25))  # Adjacent = 0.75, same = 1.0

        # Industry match
        industry_score = 1.0 if founder_1.industry == founder_2.industry else 0.3

        # Experience complement (slight difference is good)
        exp_diff = abs(founder_1.years_as_founder - founder_2.years_as_founder)
        if exp_diff <= 1:
            exp_score = 0.8  # Very similar
        elif exp_diff <= 3:
            exp_score = 1.0  # Good complement
        else:
            exp_score = 0.5  # Large gap

        # Timezone (simplified - would use actual timezone in production)
        tz_score = 0.8  # Default to reasonable

        # Weighted total
        total = (
            challenge_score * self.WEIGHTS["challenges"] +
            stage_score * self.WEIGHTS["stage"] +
            industry_score * self.WEIGHTS["industry"] +
            exp_score * self.WEIGHTS["experience"] +
            tz_score * self.WEIGHTS["timezone"]
        )

        return round(total, 2), common_challenges

    def _generate_match_reason(
        self,
        common_challenges: List[ChallengeCategory],
        score: float
    ) -> str:
        """Generate a human-readable match reason."""
        if not common_challenges:
            return "You're both founders navigating similar journeys."

        challenge_names = [c.value.replace("_", " ") for c in common_challenges[:2]]

        if len(challenge_names) == 1:
            return f"You're both working through {challenge_names[0]}."
        else:
            return f"You share common ground: {challenge_names[0]} and {challenge_names[1]}."

    def get_intro_message(self, match: FounderMatch) -> str:
        """Generate an introduction message for a new match."""
        founder_1 = self.db.get_founder(match.founder_1_id)
        founder_2 = self.db.get_founder(match.founder_2_id)

        return f"""
🤝 You've been matched!

{founder_1.anonymous_name} & {founder_2.anonymous_name}

{match.match_reason}

This is a safe space to share, vent, and support each other.
You can stay anonymous until you're both ready to reveal more.

Some conversation starters:
• "What's the hardest part of your week been?"
• "What's one win you're proud of recently?"
• "What advice would you give yourself a year ago?"

Take your time. There's no pressure here.

Remember: Everything shared in this match stays between you two.
"""

    def get_active_matches(self, founder: Founder) -> List[FounderMatch]:
        """Get all active matches for a founder."""
        return self.db.get_matches_by_founder(founder.id, status="active")

    def get_pending_matches(self, founder: Founder) -> List[FounderMatch]:
        """Get pending match requests for a founder."""
        return self.db.get_matches_by_founder(founder.id, status="pending")

    def get_match_stats(self, founder: Founder) -> dict:
        """Get matching statistics for a founder."""
        all_matches = self.db.get_matches_by_founder(founder.id)

        return {
            "total_matches": len(all_matches),
            "active_matches": len([m for m in all_matches if m.status == "active"]),
            "total_messages": sum(m.messages_exchanged for m in all_matches),
            "identities_revealed": len([
                m for m in all_matches
                if (m.founder_1_id == founder.id and m.founder_1_revealed) or
                   (m.founder_2_id == founder.id and m.founder_2_revealed)
            ])
        }

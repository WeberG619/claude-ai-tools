"""
Founder's Companion - Data Models
=================================
Core data structures for the platform.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


class MoodLevel(Enum):
    """Founder's current emotional state."""
    CRISIS = 1      # Needs immediate support
    STRUGGLING = 2  # Having a hard time
    DIFFICULT = 3   # Challenging but managing
    OKAY = 4        # Neutral
    GOOD = 5        # Positive
    THRIVING = 6    # Excellent


class ChallengeCategory(Enum):
    """Common founder challenges for matching."""
    FUNDRAISING = "fundraising"
    COFOUNDER_CONFLICT = "cofounder_conflict"
    BURNOUT = "burnout"
    LONELINESS = "loneliness"
    IMPOSTER_SYNDROME = "imposter_syndrome"
    WORK_LIFE_BALANCE = "work_life_balance"
    FINANCIAL_STRESS = "financial_stress"
    TEAM_ISSUES = "team_issues"
    PRODUCT_MARKET_FIT = "product_market_fit"
    COMPETITION = "competition"
    FAMILY_STRAIN = "family_strain"
    HEALTH_ISSUES = "health_issues"
    DECISION_FATIGUE = "decision_fatigue"


class StartupStage(Enum):
    """Company stage for context."""
    IDEA = "idea"
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B_PLUS = "series_b_plus"
    PROFITABLE = "profitable"
    ACQUIRED = "acquired"


class SubscriptionTier(Enum):
    """User subscription level."""
    FREE_TRIAL = "free_trial"
    SOLO = "solo"
    CONNECTED = "connected"
    SUPPORTED = "supported"
    ENTERPRISE = "enterprise"


@dataclass
class Founder:
    """Core founder profile."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str = ""
    anonymous_name: str = ""  # "Determined Dragon", "Resilient Phoenix", etc.

    # Profile
    first_name: Optional[str] = None
    company_name: Optional[str] = None
    stage: StartupStage = StartupStage.IDEA
    industry: str = "technology"
    team_size: int = 1
    years_as_founder: float = 0.0

    # Current state
    current_challenges: List[ChallengeCategory] = field(default_factory=list)
    current_mood: MoodLevel = MoodLevel.OKAY

    # Subscription
    tier: SubscriptionTier = SubscriptionTier.FREE_TRIAL
    tier_expires: Optional[datetime] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    timezone: str = "UTC"

    # Privacy settings
    open_to_matching: bool = True
    anonymous_until_consent: bool = True


@dataclass
class VaultEntry:
    """Private confession in the Vault - encrypted at rest."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    founder_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    # Content (stored encrypted)
    content: str = ""  # The raw confession
    encrypted_content: Optional[bytes] = None  # AES-encrypted version

    # Context
    mood_before: MoodLevel = MoodLevel.OKAY
    mood_after: Optional[MoodLevel] = None
    challenge_category: Optional[ChallengeCategory] = None

    # AI Response
    ai_response: str = ""
    response_helpful: Optional[bool] = None


@dataclass
class DailyCheckIn:
    """Morning/evening check-in."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    founder_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    check_in_type: str = "morning"  # morning, evening, adhoc

    # State capture
    mood: MoodLevel = MoodLevel.OKAY
    energy_level: int = 5  # 1-10
    sleep_quality: Optional[int] = None  # 1-10
    stress_level: int = 5  # 1-10

    # Reflections
    biggest_worry: Optional[str] = None
    small_win: Optional[str] = None
    gratitude: Optional[str] = None
    intention: Optional[str] = None  # For morning

    # AI interaction
    ai_prompt: str = ""
    ai_response: str = ""
    helpful_rating: Optional[int] = None  # 1-5


@dataclass
class FounderMatch:
    """Connection between two founders."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    founder_1_id: str = ""
    founder_2_id: str = ""

    # Matching details
    matched_at: datetime = field(default_factory=datetime.now)
    compatibility_score: float = 0.0
    common_challenges: List[ChallengeCategory] = field(default_factory=list)
    match_reason: str = ""

    # Connection status
    status: str = "pending"  # pending, accepted, active, ended
    founder_1_accepted: bool = False
    founder_2_accepted: bool = False

    # Privacy
    founder_1_revealed: bool = False
    founder_2_revealed: bool = False

    # Activity
    messages_exchanged: int = 0
    last_interaction: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    end_reason: Optional[str] = None


@dataclass
class Message:
    """Message between matched founders."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    match_id: str = ""
    sender_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    content: str = ""
    read: bool = False
    read_at: Optional[datetime] = None


@dataclass
class GroupSession:
    """Group support session for common challenges."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    challenge_focus: ChallengeCategory = ChallengeCategory.BURNOUT

    scheduled_at: datetime = field(default_factory=datetime.now)
    duration_minutes: int = 60
    max_participants: int = 8

    facilitator_id: Optional[str] = None  # AI or human
    participants: List[str] = field(default_factory=list)

    status: str = "scheduled"  # scheduled, active, completed, cancelled


@dataclass
class MoodTrend:
    """Aggregated mood data for insights."""
    founder_id: str = ""
    period_start: datetime = field(default_factory=datetime.now)
    period_end: datetime = field(default_factory=datetime.now)

    average_mood: float = 0.0
    mood_variance: float = 0.0
    lowest_mood: MoodLevel = MoodLevel.OKAY
    highest_mood: MoodLevel = MoodLevel.OKAY

    check_ins_count: int = 0
    vault_entries_count: int = 0

    top_challenges: List[ChallengeCategory] = field(default_factory=list)
    improvement_trend: float = 0.0  # Positive = improving


def generate_anonymous_name() -> str:
    """Generate a memorable anonymous name for a founder."""
    import random

    adjectives = [
        "Resilient", "Determined", "Creative", "Bold", "Wise",
        "Brave", "Curious", "Focused", "Inspired", "Steadfast",
        "Ambitious", "Thoughtful", "Energetic", "Calm", "Dynamic"
    ]

    nouns = [
        "Phoenix", "Dragon", "Eagle", "Lion", "Wolf",
        "Falcon", "Tiger", "Bear", "Owl", "Hawk",
        "Pioneer", "Navigator", "Explorer", "Builder", "Voyager"
    ]

    return f"{random.choice(adjectives)} {random.choice(nouns)}"

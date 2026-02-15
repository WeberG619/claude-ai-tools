"""
Founder's Companion - FastAPI Application
=========================================
REST API for the mental health platform.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from config import load_config, get_config
from database import Database
from models import (
    MoodLevel, ChallengeCategory, StartupStage, SubscriptionTier
)
from vault import Vault
from companion import AICompanion
from matcher import FounderMatcher


# Initialize
config = load_config()
app = FastAPI(
    title="Founder's Companion",
    description="AI Mental Health Platform for Startup Founders",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database and services
db = Database()
vault = Vault(db)
companion = AICompanion(db)
matcher = FounderMatcher(db)


# ============ Pydantic Models ============

class FounderCreate(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    company_name: Optional[str] = None
    stage: Optional[str] = "idea"
    industry: Optional[str] = "technology"
    team_size: Optional[int] = 1
    years_as_founder: Optional[float] = 0


class FounderUpdate(BaseModel):
    first_name: Optional[str] = None
    company_name: Optional[str] = None
    stage: Optional[str] = None
    industry: Optional[str] = None
    team_size: Optional[int] = None
    years_as_founder: Optional[float] = None
    current_challenges: Optional[List[str]] = None
    open_to_matching: Optional[bool] = None


class VaultEntryCreate(BaseModel):
    content: str
    mood_before: str  # MoodLevel name
    passphrase: str  # User's encryption passphrase
    challenge: Optional[str] = None


class CheckInCreate(BaseModel):
    mood: str  # MoodLevel name
    energy_level: int
    biggest_worry: Optional[str] = None
    small_win: Optional[str] = None
    intention: Optional[str] = None
    gratitude: Optional[str] = None


class SupportRequest(BaseModel):
    message: str
    challenge: Optional[str] = None


class MessageCreate(BaseModel):
    content: str


# ============ API Endpoints ============

@app.get("/")
async def root():
    """API info."""
    return {
        "name": "Founder's Companion API",
        "version": "1.0.0",
        "status": "running",
        "mission": "Helping founders who struggle in silence"
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "database": "connected"}


# ============ Founder Endpoints ============

@app.post("/founders")
async def create_founder(data: FounderCreate):
    """Register a new founder."""
    existing = db.get_founder_by_email(data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    founder = db.create_founder(
        email=data.email,
        first_name=data.first_name,
        company_name=data.company_name,
        stage=StartupStage(data.stage) if data.stage else StartupStage.IDEA,
        industry=data.industry or "technology",
        team_size=data.team_size or 1,
        years_as_founder=data.years_as_founder or 0
    )

    return {
        "id": founder.id,
        "email": founder.email,
        "anonymous_name": founder.anonymous_name,
        "message": f"Welcome, {founder.anonymous_name}! Your journey begins here."
    }


@app.get("/founders/{founder_id}")
async def get_founder(founder_id: str):
    """Get founder profile."""
    founder = db.get_founder(founder_id)
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")

    return {
        "id": founder.id,
        "anonymous_name": founder.anonymous_name,
        "first_name": founder.first_name,
        "stage": founder.stage.value,
        "industry": founder.industry,
        "current_mood": founder.current_mood.name,
        "current_challenges": [c.value for c in founder.current_challenges],
        "tier": founder.tier.value,
        "open_to_matching": founder.open_to_matching,
        "created_at": founder.created_at.isoformat(),
        "last_active": founder.last_active.isoformat()
    }


@app.patch("/founders/{founder_id}")
async def update_founder(founder_id: str, data: FounderUpdate):
    """Update founder profile."""
    founder = db.get_founder(founder_id)
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")

    if data.first_name is not None:
        founder.first_name = data.first_name
    if data.company_name is not None:
        founder.company_name = data.company_name
    if data.stage is not None:
        founder.stage = StartupStage(data.stage)
    if data.industry is not None:
        founder.industry = data.industry
    if data.team_size is not None:
        founder.team_size = data.team_size
    if data.years_as_founder is not None:
        founder.years_as_founder = data.years_as_founder
    if data.current_challenges is not None:
        founder.current_challenges = [ChallengeCategory(c) for c in data.current_challenges]
    if data.open_to_matching is not None:
        founder.open_to_matching = data.open_to_matching

    founder.last_active = datetime.now()
    db.update_founder(founder)

    return {"message": "Profile updated", "id": founder.id}


# ============ Vault Endpoints ============

@app.post("/founders/{founder_id}/vault")
async def create_vault_entry(founder_id: str, data: VaultEntryCreate):
    """Create a private vault entry."""
    founder = db.get_founder(founder_id)
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")

    entry = vault.create_entry(
        founder=founder,
        content=data.content,
        mood_before=MoodLevel[data.mood_before.upper()],
        passphrase=data.passphrase,
        challenge=ChallengeCategory(data.challenge) if data.challenge else None
    )

    return {
        "id": entry.id,
        "ai_response": entry.ai_response,
        "message": "Your thoughts are safely stored. No one can read them but you."
    }


@app.get("/founders/{founder_id}/vault/{entry_id}")
async def read_vault_entry(founder_id: str, entry_id: str, passphrase: str):
    """Read and decrypt a vault entry."""
    founder = db.get_founder(founder_id)
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")

    entry = vault.read_entry(entry_id, founder, passphrase)
    if not entry:
        raise HTTPException(status_code=401, detail="Invalid passphrase or entry not found")

    return {
        "id": entry.id,
        "content": entry.content,
        "timestamp": entry.timestamp.isoformat(),
        "mood_before": entry.mood_before.name,
        "mood_after": entry.mood_after.name if entry.mood_after else None,
        "ai_response": entry.ai_response
    }


@app.get("/founders/{founder_id}/vault/mood-history")
async def get_mood_history(founder_id: str, days: int = 30):
    """Get mood history (no content revealed)."""
    founder = db.get_founder(founder_id)
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")

    history = vault.get_mood_history(founder, days)
    return {"history": history}


# ============ Check-in Endpoints ============

@app.post("/founders/{founder_id}/checkin/morning")
async def morning_checkin(founder_id: str):
    """Start morning check-in."""
    founder = db.get_founder(founder_id)
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")

    checkin = companion.morning_checkin(founder)

    return {
        "id": checkin.id,
        "greeting": checkin.ai_response,
        "message": "Good morning! How are you really feeling today?"
    }


@app.post("/founders/{founder_id}/checkin/{checkin_id}/complete")
async def complete_checkin(founder_id: str, checkin_id: str, data: CheckInCreate):
    """Complete a check-in with responses."""
    founder = db.get_founder(founder_id)
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")

    checkin = companion.complete_morning_checkin(
        checkin_id=checkin_id,
        mood=MoodLevel[data.mood.upper()],
        energy=data.energy_level,
        intention=data.intention,
        biggest_worry=data.biggest_worry
    )

    return {
        "id": checkin.id,
        "ai_response": checkin.ai_response,
        "mood_recorded": checkin.mood.name
    }


@app.post("/founders/{founder_id}/checkin/evening")
async def evening_reflection(founder_id: str, data: CheckInCreate):
    """Evening reflection check-in."""
    founder = db.get_founder(founder_id)
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")

    checkin = companion.evening_reflection(
        founder=founder,
        mood=MoodLevel[data.mood.upper()],
        energy=data.energy_level,
        small_win=data.small_win,
        biggest_worry=data.biggest_worry,
        gratitude=data.gratitude
    )

    return {
        "id": checkin.id,
        "ai_response": checkin.ai_response,
        "message": "Rest well. Tomorrow is a new day."
    }


@app.post("/founders/{founder_id}/support")
async def get_support(founder_id: str, data: SupportRequest):
    """Get ad-hoc AI support."""
    founder = db.get_founder(founder_id)
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")

    checkin = companion.get_support(
        founder=founder,
        message=data.message,
        challenge=ChallengeCategory(data.challenge) if data.challenge else None
    )

    return {
        "ai_response": checkin.ai_response,
        "message": "I'm here for you."
    }


@app.get("/founders/{founder_id}/insights")
async def get_insights(founder_id: str, days: int = 30):
    """Get check-in insights and trends."""
    founder = db.get_founder(founder_id)
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")

    insights = companion.get_insights(founder, days)
    return insights


# ============ Matching Endpoints ============

@app.get("/founders/{founder_id}/matches/suggestions")
async def get_match_suggestions(founder_id: str):
    """Get suggested matches."""
    founder = db.get_founder(founder_id)
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")

    if not founder.open_to_matching:
        return {"message": "Matching is disabled in your settings", "suggestions": []}

    suggestions = matcher.find_matches(founder, limit=5)

    return {
        "suggestions": [
            {
                "founder_id": f.id,
                "anonymous_name": f.anonymous_name,
                "compatibility_score": score,
                "common_challenges": [c.value for c in common],
                "stage": f.stage.value
            }
            for f, score, common in suggestions
        ]
    }


@app.post("/founders/{founder_id}/matches/{other_id}")
async def create_match(founder_id: str, other_id: str):
    """Initiate a match with another founder."""
    founder = db.get_founder(founder_id)
    other = db.get_founder(other_id)

    if not founder or not other:
        raise HTTPException(status_code=404, detail="Founder not found")

    match = matcher.create_match(founder, other)

    return {
        "match_id": match.id,
        "status": match.status,
        "message": "Match request sent!"
    }


@app.post("/founders/{founder_id}/matches/{match_id}/accept")
async def accept_match(founder_id: str, match_id: str):
    """Accept a match request."""
    match = matcher.accept_match(match_id, founder_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    response = {"match_id": match.id, "status": match.status}

    if match.status == "active":
        response["intro_message"] = matcher.get_intro_message(match)
        response["message"] = "You're connected! Start your conversation."
    else:
        response["message"] = "Waiting for the other founder to accept."

    return response


@app.get("/founders/{founder_id}/matches")
async def get_matches(founder_id: str):
    """Get all matches for a founder."""
    founder = db.get_founder(founder_id)
    if not founder:
        raise HTTPException(status_code=404, detail="Founder not found")

    active = matcher.get_active_matches(founder)
    pending = matcher.get_pending_matches(founder)

    return {
        "active": [
            {
                "match_id": m.id,
                "compatibility_score": m.compatibility_score,
                "messages_exchanged": m.messages_exchanged,
                "common_challenges": [c.value for c in m.common_challenges]
            }
            for m in active
        ],
        "pending": [
            {
                "match_id": m.id,
                "compatibility_score": m.compatibility_score,
                "common_challenges": [c.value for c in m.common_challenges]
            }
            for m in pending
        ]
    }


@app.post("/matches/{match_id}/messages")
async def send_message(match_id: str, founder_id: str, data: MessageCreate):
    """Send a message in a match."""
    match = db.get_match(match_id)
    founder = db.get_founder(founder_id)

    if not match or not founder:
        raise HTTPException(status_code=404, detail="Match or founder not found")

    message = matcher.send_message(match, founder, data.content)
    if not message:
        raise HTTPException(status_code=400, detail="Cannot send message to this match")

    return {
        "message_id": message.id,
        "timestamp": message.timestamp.isoformat()
    }


@app.get("/matches/{match_id}/messages")
async def get_messages(match_id: str, founder_id: str):
    """Get messages in a match."""
    match = db.get_match(match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if founder_id not in [match.founder_1_id, match.founder_2_id]:
        raise HTTPException(status_code=403, detail="Not part of this match")

    messages = db.get_messages(match_id)

    return {
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "is_mine": m.sender_id == founder_id
            }
            for m in messages
        ]
    }


# ============ Run ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.host, port=config.port)

"""
Founder's Companion - Daily AI Companion
========================================
The supportive AI friend that checks in with founders daily.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import httpx

from models import (
    Founder, DailyCheckIn, MoodLevel, ChallengeCategory,
    MoodTrend, StartupStage
)
from config import get_config


class AICompanion:
    """
    The Daily Companion - An AI friend for founders.

    Provides:
    - Morning check-ins (intention setting)
    - Evening reflections (wins and gratitude)
    - Ad-hoc support when needed
    - Personalized encouragement based on history
    """

    # Prompts for different situations
    MORNING_CHECKIN_PROMPT = """You are Founder's Companion, a warm and supportive AI friend for startup founders.

The founder {name} is checking in for their morning reflection.

Their profile:
- Stage: {stage}
- Team size: {team_size}
- Years as founder: {years}
- Current challenges: {challenges}
- Recent mood trend: {mood_trend}
- Last check-in mood: {last_mood}

Respond with:
1. A warm, personalized greeting (use their name or anonymous name)
2. Ask how they're really feeling today - remind them this is a safe space
3. Based on their recent mood, acknowledge their journey
4. If they've been struggling, be extra gentle

Keep your response under 100 words. Be warm but not saccharine.
Sound like a wise friend, not a corporate chatbot."""

    EVENING_REFLECTION_PROMPT = """You are Founder's Companion, helping a founder reflect on their day.

Founder: {name}
Today's mood: {mood}
Energy level: {energy}/10
Today's biggest worry: {worry}
Today's small win: {win}

Respond with:
1. Acknowledge their day - validate both the struggle and the win
2. Offer perspective on their worry (if shared)
3. Celebrate their win, no matter how small
4. Set up tomorrow with hope

Keep it under 100 words. Be genuine and encouraging.
End with something that will help them sleep better."""

    SUPPORT_PROMPT = """You are Founder's Companion, providing support to a founder who needs it.

Founder: {name}
Current mood: {mood}
What they're dealing with: {challenge}
What they said: {message}

Provide empathetic, practical support:
1. Validate their feelings
2. Offer perspective (72% of founders feel this way)
3. One small, actionable suggestion
4. Remind them they're not alone

Don't be preachy. Be like a wise friend who's been there.
Keep it under 150 words."""

    def __init__(self, database):
        self.db = database
        self.config = get_config()
        self.client = httpx.Client(timeout=30.0)

    def morning_checkin(self, founder: Founder) -> DailyCheckIn:
        """Start the morning check-in process."""
        # Get mood history
        mood_trend = self._get_mood_trend(founder)
        last_checkin = self.db.get_last_checkin(founder.id)

        # Generate personalized prompt
        prompt = self._generate_morning_prompt(founder, mood_trend, last_checkin)

        # Create check-in record
        checkin = DailyCheckIn(
            founder_id=founder.id,
            check_in_type="morning",
            ai_prompt=prompt
        )

        # Get AI response
        checkin.ai_response = self._call_ai(prompt)

        # Save initial check-in
        self.db.save_checkin(checkin)

        return checkin

    def complete_morning_checkin(
        self,
        checkin_id: str,
        mood: MoodLevel,
        energy: int,
        intention: Optional[str] = None,
        biggest_worry: Optional[str] = None
    ) -> DailyCheckIn:
        """Complete morning check-in with founder's responses."""
        checkin = self.db.get_checkin(checkin_id)
        if not checkin:
            raise ValueError("Check-in not found")

        checkin.mood = mood
        checkin.energy_level = energy
        checkin.intention = intention
        checkin.biggest_worry = biggest_worry

        # Generate follow-up response
        follow_up = self._generate_morning_followup(checkin)
        checkin.ai_response = follow_up

        # Update founder's current mood
        founder = self.db.get_founder(checkin.founder_id)
        if founder:
            founder.current_mood = mood
            founder.last_active = datetime.now()
            self.db.update_founder(founder)

        self.db.update_checkin(checkin)
        return checkin

    def evening_reflection(
        self,
        founder: Founder,
        mood: MoodLevel,
        energy: int,
        small_win: Optional[str] = None,
        biggest_worry: Optional[str] = None,
        gratitude: Optional[str] = None
    ) -> DailyCheckIn:
        """Evening reflection and wind-down."""
        checkin = DailyCheckIn(
            founder_id=founder.id,
            check_in_type="evening",
            mood=mood,
            energy_level=energy,
            small_win=small_win,
            biggest_worry=biggest_worry,
            gratitude=gratitude
        )

        # Generate prompt and response
        prompt = self.EVENING_REFLECTION_PROMPT.format(
            name=founder.first_name or founder.anonymous_name,
            mood=mood.name,
            energy=energy,
            worry=biggest_worry or "Not shared",
            win=small_win or "Not shared"
        )

        checkin.ai_prompt = prompt
        checkin.ai_response = self._call_ai(prompt)

        # Update founder
        founder.current_mood = mood
        founder.last_active = datetime.now()
        self.db.update_founder(founder)

        self.db.save_checkin(checkin)
        return checkin

    def get_support(
        self,
        founder: Founder,
        message: str,
        challenge: Optional[ChallengeCategory] = None
    ) -> DailyCheckIn:
        """Ad-hoc support when founder needs it."""
        checkin = DailyCheckIn(
            founder_id=founder.id,
            check_in_type="adhoc",
            mood=founder.current_mood
        )

        prompt = self.SUPPORT_PROMPT.format(
            name=founder.first_name or founder.anonymous_name,
            mood=founder.current_mood.name,
            challenge=challenge.value if challenge else "general",
            message=message
        )

        checkin.ai_prompt = prompt
        checkin.ai_response = self._call_ai(prompt)

        founder.last_active = datetime.now()
        self.db.update_founder(founder)

        self.db.save_checkin(checkin)
        return checkin

    def _generate_morning_prompt(
        self,
        founder: Founder,
        mood_trend: str,
        last_checkin: Optional[DailyCheckIn]
    ) -> str:
        """Generate personalized morning prompt."""
        return self.MORNING_CHECKIN_PROMPT.format(
            name=founder.first_name or founder.anonymous_name,
            stage=founder.stage.value,
            team_size=founder.team_size,
            years=founder.years_as_founder,
            challenges=", ".join(c.value for c in founder.current_challenges) or "not specified",
            mood_trend=mood_trend,
            last_mood=last_checkin.mood.name if last_checkin else "unknown"
        )

    def _generate_morning_followup(self, checkin: DailyCheckIn) -> str:
        """Generate follow-up after founder shares their state."""
        founder = self.db.get_founder(checkin.founder_id)

        if checkin.mood.value <= 2:
            # Struggling - extra support
            return self._struggling_morning_response(founder, checkin)
        elif checkin.mood.value <= 4:
            # Managing - supportive
            return self._supportive_morning_response(founder, checkin)
        else:
            # Good - encouraging
            return self._positive_morning_response(founder, checkin)

    def _struggling_morning_response(
        self,
        founder: Founder,
        checkin: DailyCheckIn
    ) -> str:
        """Response for founders starting the day in a tough place."""
        name = founder.first_name or founder.anonymous_name
        return f"""
{name}, thank you for being honest with me. Starting the day feeling this way is hard.

Here's what I want you to remember:
• You don't have to conquer today - just survive it
• One small task is enough. Pick the easiest thing on your list
• It's okay to not be okay

If your worry feels too heavy, come back to the Vault. I'm here.

What's the smallest possible win you could achieve today? Just one thing.

You've got this. One moment at a time. 💙
"""

    def _supportive_morning_response(
        self,
        founder: Founder,
        checkin: DailyCheckIn
    ) -> str:
        """Response for founders who are managing."""
        name = founder.first_name or founder.anonymous_name
        intention = checkin.intention or "make progress"

        return f"""
Good morning, {name}. I hear you.

Your intention to {intention} is a great focus for today.

{"If that worry keeps nagging you, write it in the Vault. Sometimes getting it out of your head helps." if checkin.biggest_worry else ""}

Remember:
• Progress over perfection
• You're further along than you think
• One good decision today compounds over time

Go make something happen. I'll be here tonight for your reflection.

Have a good one! 🌟
"""

    def _positive_morning_response(
        self,
        founder: Founder,
        checkin: DailyCheckIn
    ) -> str:
        """Response for founders feeling good."""
        name = founder.first_name or founder.anonymous_name

        return f"""
{name}! Love the energy this morning. ✨

Ride this wave. When you're feeling good, that's when you can:
• Tackle that hard conversation you've been avoiding
• Make the bold decision
• Help someone else who might be struggling

Your energy is contagious - share it with your team today.

Go crush it! See you tonight for a celebration. 🚀
"""

    def _get_mood_trend(self, founder: Founder) -> str:
        """Get recent mood trend description."""
        checkins = self.db.get_recent_checkins(founder.id, days=7)

        if not checkins:
            return "This is your first check-in"

        moods = [c.mood.value for c in checkins]
        avg_mood = sum(moods) / len(moods)

        if avg_mood <= 2:
            return "You've been having a tough week"
        elif avg_mood <= 3:
            return "It's been a challenging week but you're showing up"
        elif avg_mood <= 4:
            return "You've been steady this week"
        else:
            return "You've been doing well recently"

    def _call_ai(self, prompt: str) -> str:
        """Call OpenAI API for response."""
        if not self.config.openai.api_key:
            # Fallback for testing without API key
            return self._fallback_response(prompt)

        try:
            response = self.client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.openai.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.config.openai.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": self.config.openai.max_tokens,
                    "temperature": self.config.openai.temperature
                }
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"AI call failed: {e}")
            return self._fallback_response(prompt)

    def _fallback_response(self, prompt: str) -> str:
        """Fallback when AI is unavailable."""
        return """
Hey there, founder.

I'm here for you today. Whatever you're facing, remember:
• You chose this path because you believe in something
• Every successful founder has been where you are
• Small progress is still progress

Take a breath. You've got this.

💙
"""

    def get_insights(self, founder: Founder, days: int = 30) -> Dict[str, Any]:
        """Get insights from check-in data."""
        checkins = self.db.get_recent_checkins(founder.id, days=days)

        if not checkins:
            return {"message": "Not enough data yet"}

        moods = [c.mood.value for c in checkins]
        energies = [c.energy_level for c in checkins]

        # Calculate trends
        if len(moods) >= 7:
            recent_avg = sum(moods[-7:]) / 7
            earlier_avg = sum(moods[:-7]) / max(1, len(moods) - 7)
            trend = "improving" if recent_avg > earlier_avg else "declining" if recent_avg < earlier_avg else "stable"
        else:
            trend = "gathering data"

        return {
            "check_ins_count": len(checkins),
            "average_mood": round(sum(moods) / len(moods), 1),
            "average_energy": round(sum(energies) / len(energies), 1),
            "best_day": max(checkins, key=lambda c: c.mood.value).timestamp.strftime("%A"),
            "trend": trend,
            "streak": self._calculate_streak(checkins)
        }

    def _calculate_streak(self, checkins: List[DailyCheckIn]) -> int:
        """Calculate consecutive days of check-ins."""
        if not checkins:
            return 0

        streak = 1
        sorted_checkins = sorted(checkins, key=lambda c: c.timestamp, reverse=True)

        for i in range(1, len(sorted_checkins)):
            diff = sorted_checkins[i-1].timestamp.date() - sorted_checkins[i].timestamp.date()
            if diff.days <= 1:
                streak += 1
            else:
                break

        return streak

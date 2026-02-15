#!/usr/bin/env python3
"""
Office Command Center - Autonomous Agent System
================================================
AI-powered agents for daily business operations:
- Secretary: Email triage, scheduling, reminders
- Writer: Draft emails, documents, proposals
- Researcher: Look up info, summarize documents
- Coordinator: Track tasks, follow-ups, deadlines
"""

import os
import json
import time
import re
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / 'agent-team' / '.env')

import anthropic

from agent_prompts import get_prompt, OFFICE_PERSONAS
from office_tools import OfficeBridge, GmailTool, CalendarTool, TaskTracker

# Voice script for TTS
VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")

# Status file for dashboard
STATUS_FILE = Path(__file__).parent / "agent_status.json"

# Global voice control
VOICE_DISABLED = False


def extract_narration(text: str) -> str:
    """Extract brief speakable narration from agent response."""
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline code
    text = re.sub(r'`[^`]+`', '', text)
    # Remove markdown headers
    text = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE)
    # Remove bullet points
    text = re.sub(r'^[\s]*[-*]\s+.*$', '', text, flags=re.MULTILINE)
    # Clean whitespace
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r' +', ' ', text)
    text = text.strip()
    # Keep first 2 sentences max
    sentences = text.split('. ')
    if len(sentences) > 2:
        text = '. '.join(sentences[:2]) + '.'
    return text[:200]


@dataclass
class Persona:
    """Agent persona with name, voice, and visual identity."""
    name: str
    voice: str
    color: str
    icon: str
    agent_type: str


class OfficeAgent:
    """An autonomous office agent powered by Claude."""

    def __init__(self, agent_type: str, api_key: str = None):
        self.agent_type = agent_type
        persona_data = OFFICE_PERSONAS.get(agent_type, OFFICE_PERSONAS["narrator"])
        self.persona = Persona(
            name=persona_data["name"],
            voice=persona_data["voice"],
            color=persona_data["color"],
            icon=persona_data["icon"],
            agent_type=agent_type
        )

        # Initialize Claude client
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY required")
        self.client = anthropic.Anthropic(api_key=api_key)

        # Store last activity for view persistence
        self._last_activity = None

    def _update_status(self, text: str, speaking: bool = True, activity: dict = None):
        """Update the dashboard status file."""
        try:
            status = {
                "agent": self.agent_type,
                "speaking": speaking,
                "text": text[:200] if text else "",
                "timestamp": time.time(),
                "persona": {
                    "name": self.persona.name,
                    "icon": self.persona.icon,
                    "color": self.persona.color
                }
            }
            if activity:
                status["activity"] = activity
            with open(STATUS_FILE, "w") as f:
                json.dump(status, f)
        except Exception as e:
            print(f"Status update error: {e}")

    def _detect_activity(self, text: str) -> dict:
        """Detect activity type from response text for visual display."""
        text_lower = text.lower()

        # Check for email drafts
        if any(kw in text_lower for kw in ['draft', 'email', 'compose', 'subject:', 'dear', 'hi ']):
            return {
                "type": "email_compose",
                "content": text[:500],
                "icon": "📧"
            }

        # Check for calendar operations
        if any(kw in text_lower for kw in ['schedule', 'meeting', 'calendar', 'appointment', 'event']):
            return {
                "type": "calendar_view",
                "content": text[:500],
                "icon": "📅"
            }

        # Check for task operations
        if any(kw in text_lower for kw in ['task', 'follow-up', 'reminder', 'deadline', 'to-do', 'action item']):
            return {
                "type": "task_view",
                "content": text[:500],
                "icon": "✅"
            }

        # Check for research/lookup
        if any(kw in text_lower for kw in ['found', 'search', 'looking', 'research', 'information']):
            return {
                "type": "research_view",
                "content": text[:500],
                "icon": "🔍"
            }

        # Default to general office view
        return {
            "type": "office_view",
            "content": text[:500],
            "icon": "🏢"
        }

    def _speak(self, text: str, activity: dict = None) -> bool:
        """Speak the text using TTS."""
        import subprocess

        self._last_activity = activity

        if VOICE_DISABLED:
            self._update_status(text, speaking=True, activity=activity)
            time.sleep(0.1)
            self._update_status(text, speaking=False, activity=activity)
            return True

        narration = extract_narration(text)
        if not narration or len(narration) < 10:
            self._update_status(text, speaking=True, activity=activity)
            time.sleep(0.3)
            self._update_status(text, speaking=False, activity=activity)
            return True

        try:
            self._update_status(text, speaking=True, activity=activity)

            print(f"\n{'━'*60}")
            print(f"🎤 {self.persona.name.upper()} ({self.persona.voice}) speaking...")
            print(f"{'━'*60}")
            print(f'  "{narration[:100]}..."' if len(narration) > 100 else f'  "{narration}"')

            result = subprocess.run(
                ["python3", str(VOICE_SCRIPT), narration, self.persona.voice],
                capture_output=True,
                timeout=120
            )

            print(f"\n  ✓ {self.persona.name.upper()} finished")
            return result.returncode == 0

        except Exception as e:
            print(f"Speech error: {e}")
            return False
        finally:
            self._update_status("", speaking=False, activity=getattr(self, '_last_activity', None))

    def think(self, context: str, team_history: List[Dict] = None) -> str:
        """Have the agent think and respond using Claude API."""
        messages = []

        if team_history:
            history_text = "\n".join([
                f"{msg['agent'].upper()}: {msg['text']}"
                for msg in team_history[-10:]
            ])
            messages.append({
                "role": "user",
                "content": f"Recent team conversation:\n{history_text}\n\nCurrent context: {context}"
            })
        else:
            messages.append({
                "role": "user",
                "content": context
            })

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=get_prompt(self.agent_type, task=context, history=str(team_history or [])),
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            return f"Error: {e}"

    def respond(self, context: str, team_history: List[Dict] = None, speak: bool = True) -> str:
        """Think and speak a response."""
        response = self.think(context, team_history)
        activity = self._detect_activity(response)

        print(f"\n[{self.persona.name.upper()}]: {response}")
        if speak:
            self._speak(response, activity=activity)

        return response


class OfficeTeam:
    """The Office Command Center team."""

    def __init__(self):
        self.secretary = OfficeAgent("secretary")
        self.writer = OfficeAgent("writer")
        self.researcher = OfficeAgent("researcher")
        self.coordinator = OfficeAgent("coordinator")
        self.narrator = OfficeAgent("narrator")

        self.agents = {
            "secretary": self.secretary,
            "writer": self.writer,
            "researcher": self.researcher,
            "coordinator": self.coordinator,
            "narrator": self.narrator
        }

        self.team_history = []
        self.bridge = OfficeBridge()

    def _add_to_history(self, agent: str, text: str):
        """Add a message to team history."""
        self.team_history.append({
            "agent": agent,
            "text": text,
            "timestamp": time.time()
        })

    def handle_task(self, task: str, max_rounds: int = 6):
        """Handle an office task with the team."""
        print(f"\n{'='*60}")
        print(f"  OFFICE COMMAND CENTER")
        print(f"  Task: {task}")
        print(f"{'='*60}\n")

        # Narrator introduces
        intro = self.narrator.respond(
            f"Introduce this office task to the user: {task}",
            speak=True
        )
        self._add_to_history("narrator", intro)

        # Secretary triages first
        secretary_response = self.secretary.respond(task, self.team_history)
        self._add_to_history("secretary", secretary_response)

        # Continue conversation based on handoffs
        for round_num in range(max_rounds):
            last_response = self.team_history[-1]["text"].lower()

            # Detect handoff
            next_agent = None
            if "writer" in last_response:
                next_agent = "writer"
            elif "researcher" in last_response:
                next_agent = "researcher"
            elif "coordinator" in last_response:
                next_agent = "coordinator"
            elif "secretary" in last_response:
                next_agent = "secretary"
            elif "complete" in last_response or "done" in last_response:
                break

            if next_agent and next_agent in self.agents:
                response = self.agents[next_agent].respond(task, self.team_history)
                self._add_to_history(next_agent, response)
            else:
                break

        # Narrator summarizes
        summary = self.narrator.respond(
            f"Summarize what the team accomplished for: {task}",
            self.team_history,
            speak=True
        )
        self._add_to_history("narrator", summary)

        print(f"\n{'='*60}")
        print(f"  TASK COMPLETE")
        print(f"{'='*60}\n")

        return self.team_history

    def quick_email(self, to: str, subject: str, context: str):
        """Quick workflow: Draft and send an email."""
        task = f"Draft an email to {to} about: {subject}. Context: {context}"

        # Writer drafts
        draft = self.writer.respond(task, speak=True)
        self._add_to_history("writer", draft)

        # Extract the email body from the draft
        # Look for content between code blocks or after "Draft:"
        email_body = draft
        if "```" in draft:
            match = re.search(r'```(?:\w+)?\n([\s\S]*?)```', draft)
            if match:
                email_body = match.group(1)

        # Open Gmail compose
        result = self.bridge.execute_action("compose_email", {
            "to": to,
            "subject": subject,
            "body": email_body
        })

        # Narrator confirms
        self.narrator.respond(
            f"Email draft opened in Gmail for {to} about {subject}",
            speak=True
        )

        return result

    def check_calendar(self):
        """Quick workflow: Check today's calendar."""
        result = self.bridge.execute_action("get_calendar_today", {})

        self.secretary.respond(
            f"Here's today's calendar: {result.get('events', 'No events found')}",
            speak=True
        )

        return result

    def add_followup(self, title: str, due_date: str, notes: str = ""):
        """Quick workflow: Add a follow-up task."""
        result = self.bridge.execute_action("add_task", {
            "title": title,
            "due_date": due_date,
            "priority": "normal",
            "category": "follow-up",
            "notes": notes
        })

        self.coordinator.respond(
            f"Added follow-up task: {title} due {due_date}",
            speak=True
        )

        return result


# CLI interface
if __name__ == "__main__":
    import sys

    team = OfficeTeam()

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        team.handle_task(task)
    else:
        print("Usage: python autonomous_agents.py <task>")
        print("Example: python autonomous_agents.py 'Draft an email to Bruce about the project timeline'")

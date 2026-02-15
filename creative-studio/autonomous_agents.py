#!/usr/bin/env python3
"""
Creative Studio - Autonomous Agent System
==========================================
AI-powered agents for presentations and content creation:
- Director: Creative vision, structure, storytelling
- Designer: Layouts, visuals, slide design
- Copywriter: Headlines, messaging, scripts
- Editor: Polish, proofread, refine
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

from agent_prompts import get_prompt, CREATIVE_PERSONAS
from creative_tools import CreativeBridge, SlideBuilder

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


class CreativeAgent:
    """An autonomous creative agent powered by Claude."""

    def __init__(self, agent_type: str, api_key: str = None):
        self.agent_type = agent_type
        persona_data = CREATIVE_PERSONAS.get(agent_type, CREATIVE_PERSONAS["narrator"])
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

        # Check for slide/presentation work
        if any(kw in text_lower for kw in ['slide', 'presentation', 'deck', 'layout']):
            return {
                "type": "slide_design",
                "content": text[:500],
                "icon": "🎨"
            }

        # Check for copywriting
        if any(kw in text_lower for kw in ['headline', 'copy', 'tagline', 'script', 'draft']):
            return {
                "type": "copywriting",
                "content": text[:500],
                "icon": "✍️"
            }

        # Check for editing/review
        if any(kw in text_lower for kw in ['review', 'edit', 'approved', 'revision', 'polish']):
            return {
                "type": "editing",
                "content": text[:500],
                "icon": "📝"
            }

        # Check for creative direction
        if any(kw in text_lower for kw in ['vision', 'story', 'narrative', 'structure', 'audience']):
            return {
                "type": "directing",
                "content": text[:500],
                "icon": "🎬"
            }

        # Default creative view
        return {
            "type": "creative_view",
            "content": text[:500],
            "icon": "🎨"
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
                max_tokens=1500,  # More tokens for creative content
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


class CreativeTeam:
    """The Creative Studio team."""

    def __init__(self):
        self.director = CreativeAgent("director")
        self.designer = CreativeAgent("designer")
        self.copywriter = CreativeAgent("copywriter")
        self.editor = CreativeAgent("editor")
        self.narrator = CreativeAgent("narrator")

        self.agents = {
            "director": self.director,
            "designer": self.designer,
            "copywriter": self.copywriter,
            "editor": self.editor,
            "narrator": self.narrator
        }

        self.team_history = []
        self.bridge = CreativeBridge()

    def _add_to_history(self, agent: str, text: str):
        """Add a message to team history."""
        self.team_history.append({
            "agent": agent,
            "text": text,
            "timestamp": time.time()
        })

    def create_presentation(self, topic: str, slides: int = 5, max_rounds: int = 8):
        """Create a presentation with the team."""
        print(f"\n{'='*60}")
        print(f"  🎨 CREATIVE STUDIO")
        print(f"  Creating: {topic}")
        print(f"{'='*60}\n")

        # Start presentation
        self.bridge.start_presentation(topic)

        # Narrator introduces
        intro = self.narrator.respond(
            f"Introduce this creative project: Creating a {slides}-slide presentation about '{topic}'",
            speak=True
        )
        self._add_to_history("narrator", intro)

        # Director sets vision
        task = f"Create a {slides}-slide presentation about: {topic}. Define the story structure and key messages."
        director_response = self.director.respond(task, self.team_history)
        self._add_to_history("director", director_response)

        # Continue conversation based on handoffs
        for round_num in range(max_rounds):
            last_response = self.team_history[-1]["text"].lower()

            # Detect handoff
            next_agent = None
            if "designer" in last_response:
                next_agent = "designer"
            elif "copywriter" in last_response:
                next_agent = "copywriter"
            elif "editor" in last_response:
                next_agent = "editor"
            elif "director" in last_response:
                next_agent = "director"
            elif "approved" in last_response or "ready for delivery" in last_response:
                break

            if next_agent and next_agent in self.agents:
                response = self.agents[next_agent].respond(topic, self.team_history)
                self._add_to_history(next_agent, response)

                # Extract and add slides from designer responses
                if next_agent == "designer":
                    self._extract_slides(response)
            else:
                break

        # Save presentation
        result = self.bridge.save_presentation()

        # Narrator summarizes
        summary = self.narrator.respond(
            f"Present the completed presentation about '{topic}' to Weber. Mention it's been saved and how to view it.",
            self.team_history,
            speak=True
        )
        self._add_to_history("narrator", summary)

        print(f"\n{'='*60}")
        print(f"  PRESENTATION COMPLETE")
        if result.get("success"):
            print(f"  Saved to: {result['paths'].get('html', 'N/A')}")
        print(f"{'='*60}\n")

        return result

    def _extract_slides(self, response: str):
        """Extract slide content from designer response."""
        # Look for slide definitions
        slide_matches = re.findall(
            r'\[Slide \d+:?\s*([^\]]+)\]|Slide \d+:?\s*(.+?)(?=Slide \d+|$)',
            response, re.IGNORECASE | re.DOTALL
        )

        for match in slide_matches:
            title = match[0] or match[1]
            if title:
                title = title.strip().split('\n')[0]
                self.bridge.add_slide(title, [], notes=response[:200])

    def write_copy(self, brief: str, format: str = "general"):
        """Create copy/content with the team."""
        print(f"\n{'='*60}")
        print(f"  🎨 CREATIVE STUDIO - Copywriting")
        print(f"  Brief: {brief}")
        print(f"{'='*60}\n")

        # Narrator introduces
        intro = self.narrator.respond(
            f"Introduce this copywriting project: {brief}",
            speak=True
        )
        self._add_to_history("narrator", intro)

        # Director sets direction
        director_response = self.director.respond(
            f"Set the creative direction for this copy: {brief}. Define tone, audience, and key messages.",
            self.team_history
        )
        self._add_to_history("director", director_response)

        # Copywriter creates
        copy_response = self.copywriter.respond(brief, self.team_history)
        self._add_to_history("copywriter", copy_response)

        # Editor reviews
        editor_response = self.editor.respond(brief, self.team_history)
        self._add_to_history("editor", editor_response)

        # Narrator presents
        summary = self.narrator.respond(
            f"Present the completed copy to Weber",
            self.team_history,
            speak=True
        )

        print(f"\n{'='*60}")
        print(f"  COPY COMPLETE")
        print(f"{'='*60}\n")

        return self.team_history


# CLI interface
if __name__ == "__main__":
    import sys

    team = CreativeTeam()

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])

        # Detect task type
        if any(kw in task.lower() for kw in ['presentation', 'slides', 'deck', 'pitch']):
            team.create_presentation(task)
        else:
            team.write_copy(task)
    else:
        print("Usage: python autonomous_agents.py <task>")
        print("Examples:")
        print("  python autonomous_agents.py 'Create a 5-slide presentation about AI in Architecture'")
        print("  python autonomous_agents.py 'Write compelling taglines for BIM automation software'")

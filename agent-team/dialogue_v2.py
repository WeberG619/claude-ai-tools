#!/usr/bin/env python3
"""
Agent Team Dialogue System v2 - Professional Developer Conversations
=====================================================================
Sharp, intelligent dialogue. No fluff. Straight to the point.
"""

import json
import random
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# Voice script location
VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")
# Status file path - shared location accessible from both WSL and Windows
STATUS_FILE = Path("/mnt/d/_CLAUDE-TOOLS/agent-team/agent_status.json")

# Language detection by file extension
LANGUAGE_MAP = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.html': 'html',
    '.css': 'css',
    '.json': 'json',
    '.md': 'markdown',
    '.sh': 'bash',
    '.ps1': 'powershell',
    '.cs': 'csharp',
    '.cpp': 'cpp',
    '.c': 'c',
    '.go': 'go',
    '.rs': 'rust',
    '.java': 'java',
    '.rb': 'ruby',
    '.php': 'php',
    '.sql': 'sql',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.xml': 'xml',
}


@dataclass
class DevPersonality:
    """A developer's professional speech patterns."""
    name: str
    voice: str
    role: str

    # Speech patterns - professional, not casual
    thinking_sounds: List[str]
    agreement_phrases: List[str]
    pushback_phrases: List[str]
    transition_phrases: List[str]

    # Personality traits
    patience_level: int  # 1-10
    confidence_level: int  # 1-10
    chattiness: int  # 1-10

    allies: List[str] = field(default_factory=list)
    friction_with: List[str] = field(default_factory=list)


# Professional developer personalities - sharp and direct
DEVS = {
    "planner": DevPersonality(
        name="Planner",
        voice="andrew",
        role="Tech lead who keeps things on track",
        thinking_sounds=[
            "Let me think through this.",
            "Here's my take.",
            "Consider this approach.",
        ],
        agreement_phrases=[
            "That makes sense.",
            "Good point.",
            "Agreed.",
            "That works.",
        ],
        pushback_phrases=[
            "I see it differently.",
            "Let's reconsider that.",
            "What about this angle?",
            "Hold on.",
        ],
        transition_phrases=[
            "Next item.",
            "Moving forward.",
            "So here's the plan.",
        ],
        patience_level=7,
        confidence_level=8,
        chattiness=5,
        allies=["researcher"],
        friction_with=["builder"],
    ),

    "researcher": DevPersonality(
        name="Researcher",
        voice="christopher",
        role="The one who digs into everything",
        thinking_sounds=[
            "I looked into this.",
            "Based on my research.",
            "The data shows.",
        ],
        agreement_phrases=[
            "The data supports that.",
            "That aligns with what I found.",
            "Confirmed.",
        ],
        pushback_phrases=[
            "The numbers tell a different story.",
            "I found something that contradicts that.",
            "Let me verify.",
        ],
        transition_phrases=[
            "Related point.",
            "Also worth noting.",
            "On that topic.",
        ],
        patience_level=8,
        confidence_level=6,
        chattiness=6,
        allies=["planner", "critic"],
        friction_with=[],
    ),

    "builder": DevPersonality(
        name="Builder",
        voice="adam",
        role="The backend implementer",
        thinking_sounds=[
            "I can build that.",
            "Here's how I'd approach it.",
            "Technically speaking.",
        ],
        agreement_phrases=[
            "That works.",
            "Clean solution.",
            "I can do that.",
            "Straightforward.",
        ],
        pushback_phrases=[
            "That's overengineered.",
            "We're overcomplicating this.",
            "Let's just build it and iterate.",
            "Ship it first.",
        ],
        transition_phrases=[
            "For implementation.",
            "On the code side.",
            "Next step.",
        ],
        patience_level=4,
        confidence_level=8,
        chattiness=4,
        allies=["planner", "builder-frontend", "builder-infra"],
        friction_with=["critic"],
    ),

    "builder-frontend": DevPersonality(
        name="Builder-Frontend",
        voice="roger",
        role="The UI specialist",
        thinking_sounds=[
            "Let me style that.",
            "From a UX perspective.",
            "The component needs.",
        ],
        agreement_phrases=[
            "That's clean design.",
            "Users will love that.",
            "I'll make it beautiful.",
            "Great UX call.",
        ],
        pushback_phrases=[
            "That's not user-friendly.",
            "We need better UX here.",
            "The interface should be simpler.",
            "Accessibility matters.",
        ],
        transition_phrases=[
            "On the frontend.",
            "For the UI.",
            "Visually speaking.",
        ],
        patience_level=6,
        confidence_level=7,
        chattiness=5,
        allies=["builder", "builder-infra", "researcher"],
        friction_with=[],
    ),

    "builder-infra": DevPersonality(
        name="Builder-Infra",
        voice="davis",
        role="The DevOps engineer",
        thinking_sounds=[
            "Let me set that up.",
            "Infrastructure-wise.",
            "For deployment.",
        ],
        agreement_phrases=[
            "That's reliable.",
            "Good for scaling.",
            "I can automate that.",
            "Clean pipeline.",
        ],
        pushback_phrases=[
            "That won't scale.",
            "We need monitoring first.",
            "Security concern here.",
            "The pipeline needs work.",
        ],
        transition_phrases=[
            "On the ops side.",
            "For deployment.",
            "Infrastructure-wise.",
        ],
        patience_level=7,
        confidence_level=8,
        chattiness=4,
        allies=["builder", "builder-frontend", "critic"],
        friction_with=[],
    ),

    "critic": DevPersonality(
        name="Critic",
        voice="eric",
        role="Quality and risk assessment",
        thinking_sounds=[
            "Let me poke holes in this.",
            "Consider the edge cases.",
            "From a quality perspective.",
        ],
        agreement_phrases=[
            "That's solid.",
            "No objections.",
            "That addresses my concern.",
        ],
        pushback_phrases=[
            "What happens when...",
            "Have we considered...",
            "The risk here is...",
            "This could fail if...",
        ],
        transition_phrases=[
            "Another consideration.",
            "Also.",
            "One more thing.",
        ],
        patience_level=7,
        confidence_level=7,
        chattiness=5,
        allies=["researcher"],
        friction_with=["builder"],
    ),

    "narrator": DevPersonality(
        name="Narrator",
        voice="jenny",
        role="Technical product expert on the team",
        thinking_sounds=[
            "From a product standpoint.",
            "Looking at this holistically.",
            "The key insight here is.",
        ],
        agreement_phrases=[
            "That aligns with our goals.",
            "This fits the architecture.",
            "Good direction.",
        ],
        pushback_phrases=[
            "The product needs.",
            "Users will expect.",
            "We should prioritize.",
        ],
        transition_phrases=[
            "On the product side.",
            "For context.",
            "Worth highlighting.",
        ],
        patience_level=8,
        confidence_level=8,
        chattiness=5,
        allies=["planner", "researcher", "builder", "critic"],
        friction_with=[],
    ),
}


class AuthenticDialogue:
    """Creates professional developer conversations."""

    def __init__(self):
        self.conversation_history: List[Dict] = []
        self.last_speaker: Optional[str] = None
        self.current_activity: Optional[Dict] = None

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(file_path).suffix.lower()
        return LANGUAGE_MAP.get(ext, 'text')

    def _set_activity(self, activity: dict):
        """Internal: Update status file with activity information."""
        self.current_activity = activity
        try:
            # Read existing status if present
            existing = {}
            if STATUS_FILE.exists():
                with open(STATUS_FILE) as f:
                    existing = json.load(f)

            # Merge activity into status
            existing["activity"] = activity
            existing["activity_timestamp"] = time.time()

            with open(STATUS_FILE, "w") as f:
                json.dump(existing, f)
        except Exception as e:
            print(f"Activity update error: {e}")

    def clear_activity(self):
        """Clear the current activity from status file."""
        self.current_activity = None
        try:
            if STATUS_FILE.exists():
                with open(STATUS_FILE) as f:
                    existing = json.load(f)
                existing["activity"] = None
                with open(STATUS_FILE, "w") as f:
                    json.dump(existing, f)
        except:
            pass

    def navigate_to(self, url: str, title: str = None):
        """Signal browser navigation activity for dashboard display."""
        self._set_activity({
            "type": "browser_navigate",
            "url": url,
            "title": title or url[:50]
        })

    def search_web(self, query: str, engine: str = "github"):
        """Signal web search activity for dashboard display."""
        self._set_activity({
            "type": "browser_search",
            "query": query,
            "engine": engine
        })

    def write_code(self, file_path: str, content: str, language: str = None):
        """Signal code writing activity for dashboard display with typing animation."""
        self._set_activity({
            "type": "code_write",
            "file_path": file_path,
            "content": content,
            "language": language or self._detect_language(file_path)
        })

    def read_file(self, file_path: str, highlight_lines: list = None):
        """Signal file reading activity for dashboard display."""
        self._set_activity({
            "type": "code_read",
            "file_path": file_path,
            "highlight_lines": highlight_lines or []
        })

    def run_command(self, command: str, output: str = None):
        """Signal terminal command activity for dashboard display."""
        self._set_activity({
            "type": "terminal_run",
            "command": command,
            "output": output or ""
        })

    def show_thinking(self, topic: str):
        """Signal thinking/processing activity for dashboard display."""
        self._set_activity({
            "type": "thinking",
            "topic": topic
        })

    def set_status(self, agent: str, text: str, speaking: bool = True):
        """Update agent speech status for the monitor."""
        try:
            status = {
                "agent": agent,
                "speaking": speaking,
                "text": text[:100] if text else "",
                "timestamp": time.time()
            }
            # Preserve activity if present
            if self.current_activity:
                status["activity"] = self.current_activity
            with open(STATUS_FILE, "w") as f:
                json.dump(status, f)
        except:
            pass

    def speak(self, agent: str, text: str) -> bool:
        """Have an agent speak."""
        import threading

        dev = DEVS.get(agent.lower())
        if not dev:
            return False

        voice = dev.voice
        success = False

        try:
            # Set status BEFORE speaking
            self.set_status(agent, text, speaking=True)

            # Keep updating status while speaking to maintain green light
            speaking_active = True

            def keep_alive():
                """Keep the speaking status alive during TTS."""
                while speaking_active:
                    self.set_status(agent, text, speaking=True)
                    time.sleep(0.3)  # Update every 300ms

            # Start keep-alive thread
            keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
            keep_alive_thread.start()

            # Run TTS
            result = subprocess.run(
                ["python3", str(VOICE_SCRIPT), text, voice],
                capture_output=True,
                timeout=120
            )
            success = result.returncode == 0

            # Stop keep-alive
            speaking_active = False
            time.sleep(0.1)

        except Exception as e:
            print(f"Speech error: {e}")
            success = False

        finally:
            # Brief delay before clearing, so dashboard sees final state
            time.sleep(0.5)
            self.set_status(agent, "", speaking=False)
            time.sleep(0.1)  # Minimal pause between speakers

        return success

    def say(
        self,
        speaker: str,
        message: str,
        to: Optional[str] = None,
        reaction: Optional[str] = None,
    ) -> bool:
        """
        Have a developer say something.

        Args:
            speaker: Who's talking
            message: What they're saying
            to: Who they're addressing (optional)
            reaction: agree, disagree, thinking
        """
        dev = DEVS.get(speaker.lower())
        if not dev:
            print(f"Unknown speaker: {speaker}")
            return False

        # Add reaction-based opener (30% chance)
        if reaction and random.random() < 0.3:
            if reaction == "agree" and dev.agreement_phrases:
                opener = random.choice(dev.agreement_phrases)
                message = f"{opener} {message}"
            elif reaction == "disagree" and dev.pushback_phrases:
                opener = random.choice(dev.pushback_phrases)
                message = f"{opener} {message}"
            elif reaction == "thinking" and dev.thinking_sounds:
                opener = random.choice(dev.thinking_sounds)
                message = f"{opener} {message}"

        # Add direct address if talking to someone (20% chance)
        if to and random.random() < 0.2:
            to_dev = DEVS.get(to.lower())
            if to_dev:
                message = f"{to_dev.name}, {message[0].lower()}{message[1:]}"

        # Print and speak
        print(f"\n[{dev.name.upper()}]: {message}")
        success = self.speak(speaker, message)

        # Track conversation
        self.conversation_history.append({
            "speaker": speaker,
            "message": message,
            "to": to,
            "reaction": reaction
        })
        self.last_speaker = speaker

        return success

    def pause(self, seconds: float = 0.15):
        """Brief pause in conversation - default very short."""
        time.sleep(seconds)


class DevTeamChat:
    """
    High-level API for professional dev team conversations.

    Example:
        chat = DevTeamChat()
        chat.start_session("Building the OBS integration")
        chat.planner.thinks("Let's define the architecture first")
        chat.researcher.says("The WebSocket API is on port 4455")
        chat.builder.says("I'll implement the connection handler")
        chat.critic.questions("What's the error recovery strategy?")
        chat.narrator.says("This component handles all recording state")
        chat.end_session()
    """

    def __init__(self):
        self.dialogue = AuthenticDialogue()
        self.session_active = False

    def start_session(self, topic: str):
        """Start a new discussion session."""
        self.session_active = True
        self.dialogue.say(
            "narrator",
            f"The team is working on {topic}. Let me provide context as we go."
        )
        self.dialogue.pause(0.2)

    def end_session(self):
        """Wrap up the session."""
        self.dialogue.say(
            "narrator",
            "That covers the key decisions. The implementation is solid."
        )
        self.session_active = False

    class _AgentProxy:
        """Proxy for agent interactions."""

        def __init__(self, agent: str, dialogue: AuthenticDialogue):
            self.agent = agent
            self.dialogue = dialogue

        def thinks(self, message: str, to: str = None):
            """Agent thinking out loud."""
            self.dialogue.say(self.agent, message, to=to, reaction="thinking")
            self.dialogue.pause(0.15)

        def says(self, message: str, to: str = None):
            """Agent making a statement."""
            self.dialogue.say(self.agent, message, to=to)
            self.dialogue.pause(0.1)

        def agrees(self, message: str, to: str = None):
            """Agent agreeing with someone."""
            self.dialogue.say(self.agent, message, to=to, reaction="agree")
            self.dialogue.pause(0.1)

        def questions(self, message: str, to: str = None):
            """Agent pushing back or questioning."""
            self.dialogue.say(self.agent, message, to=to, reaction="disagree")
            self.dialogue.pause(0.15)

        def decides(self, message: str):
            """Agent making a decision."""
            self.dialogue.say(self.agent, f"Decision: {message}")
            self.dialogue.pause(0.15)

        def explains(self, message: str):
            """Agent explaining something technical."""
            self.dialogue.say(self.agent, message)
            self.dialogue.pause(0.1)

        # Visual activity methods for dashboard display
        def navigates_to(self, url: str, title: str = None):
            """Signal browser navigation - displays on dashboard."""
            self.dialogue.navigate_to(url, title)

        def searches(self, query: str, engine: str = "github"):
            """Signal web search - displays on dashboard."""
            self.dialogue.search_web(query, engine)

        def writes_code(self, file_path: str, content: str, language: str = None):
            """Signal code writing - triggers typing animation on dashboard."""
            self.dialogue.write_code(file_path, content, language)

        def reads_file(self, file_path: str, highlight_lines: list = None):
            """Signal file reading - displays on dashboard."""
            self.dialogue.read_file(file_path, highlight_lines)

        def runs_command(self, command: str, output: str = None):
            """Signal terminal command - displays on dashboard."""
            self.dialogue.run_command(command, output)

        def is_thinking(self, topic: str):
            """Signal thinking/processing - displays on dashboard."""
            self.dialogue.show_thinking(topic)

        def clear_activity(self):
            """Clear current visual activity from dashboard."""
            self.dialogue.clear_activity()

    @property
    def planner(self) -> _AgentProxy:
        return self._AgentProxy("planner", self.dialogue)

    @property
    def researcher(self) -> _AgentProxy:
        return self._AgentProxy("researcher", self.dialogue)

    @property
    def builder(self) -> _AgentProxy:
        return self._AgentProxy("builder", self.dialogue)

    @property
    def builder_frontend(self) -> _AgentProxy:
        return self._AgentProxy("builder-frontend", self.dialogue)

    @property
    def builder_infra(self) -> _AgentProxy:
        return self._AgentProxy("builder-infra", self.dialogue)

    @property
    def critic(self) -> _AgentProxy:
        return self._AgentProxy("critic", self.dialogue)

    @property
    def narrator(self) -> _AgentProxy:
        return self._AgentProxy("narrator", self.dialogue)

    def pause(self, seconds: float = 0.2):
        """Add a pause in the conversation."""
        self.dialogue.pause(seconds)


def demo_professional_conversation():
    """Demo showing professional developer conversation."""

    print("=" * 60)
    print("  PROFESSIONAL DEV TEAM CONVERSATION DEMO")
    print("=" * 60)
    print()

    chat = DevTeamChat()

    # Start the session
    chat.start_session("an OBS integration for automated recording")

    # Planning phase - crisp exchanges
    chat.planner.thinks("We need to connect to OBS via their API. What are our options?")

    chat.researcher.says("OBS exposes a WebSocket server on port 4455. There's a Python library called obsws-python.")

    chat.builder.says("WebSocket is straightforward. I can wrap it in a class with connection pooling.")

    chat.narrator.explains("The WebSocket approach means we get real-time state updates. Important for knowing when recordings actually start and stop.")

    chat.critic.questions("What's the failure mode if OBS isn't running?")

    chat.builder.says("Timeout on connect. We surface that to the caller.", to="critic")

    chat.critic.says("We need graceful degradation. The app shouldn't crash.", to="builder")

    chat.planner.decides("Add a status check method. Return clear error states. No exceptions bubbling up.")

    chat.builder.agrees("That's clean. I'll add an enum for connection states.")

    # Building phase
    chat.narrator.explains("The architecture is set. Three main components: connection manager, command dispatcher, and state tracker.")

    chat.builder.says("Starting with the connection manager. I'll implement retry logic with exponential backoff.")

    chat.researcher.says("The API returns the output path when recording stops. We should expose that.")

    chat.builder.agrees("Good catch. I'll add that to the stop recording response.")

    chat.critic.says("What about concurrent access? Multiple callers hitting start simultaneously?")

    chat.builder.says("Mutex on state transitions. Only one operation at a time.")

    chat.narrator.explains("This mutex pattern prevents race conditions. Critical for recording integrity.")

    # Wrap up
    chat.planner.says("We have the architecture. Builder, proceed with implementation.")

    chat.builder.says("On it. Core functionality in twenty minutes.")

    chat.critic.says("I'll review the error handling paths.")

    chat.narrator.explains("The team is aligned. Clear responsibilities, defined interfaces. This is how professional development works.")

    chat.end_session()

    print()
    print("=" * 60)
    print("  DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo_professional_conversation()
    else:
        print("Professional Developer Dialogue System v2")
        print("-" * 40)
        print("Usage:")
        print("  python dialogue_v2.py demo    # Run demo conversation")
        print()
        print("Or import and use in your code:")
        print("  from dialogue_v2 import DevTeamChat")
        print("  chat = DevTeamChat()")
        print("  chat.planner.thinks('Let me analyze this...')")
        print("  chat.builder.says('I can implement that.')")
        print("  chat.narrator.explains('This is the core architecture.')")

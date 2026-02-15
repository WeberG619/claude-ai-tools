#!/usr/bin/env python3
"""
Agent Team Dialogue Orchestrator
================================
Creates natural, back-and-forth conversations between agents.
Supports direct addressing, disagreements, questions, and personality.
"""

import json
import random
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum
from pathlib import Path

# Voice script location
VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")
STATUS_FILE = Path("/tmp/agent_speech_status.json")

class ConversationType(Enum):
    STATEMENT = "statement"
    QUESTION = "question"
    AGREEMENT = "agreement"
    DISAGREEMENT = "disagreement"
    BUILD_ON = "build_on"
    DISCOVERY = "discovery"
    DECISION = "decision"
    PIVOT = "pivot"
    HUMOR = "humor"
    AUDIENCE_HOOK = "audience_hook"


@dataclass
class AgentPersonality:
    """Defines an agent's personality and speech patterns."""
    name: str
    voice: str
    role: str
    traits: List[str]
    speaking_style: str
    catchphrases: List[str] = field(default_factory=list)
    agrees_with: List[str] = field(default_factory=list)  # Agents they tend to agree with
    challenges: List[str] = field(default_factory=list)   # Agents they tend to challenge


# Define agent personalities
AGENTS = {
    "planner": AgentPersonality(
        name="Planner",
        voice="andrew",
        role="Strategic leader who sets direction",
        traits=["calm", "strategic", "decisive", "big-picture"],
        speaking_style="measured and thoughtful, often pauses to consider",
        catchphrases=[
            "Let's think about this strategically.",
            "Here's what I'm thinking...",
            "The key question is...",
            "Let's step back and look at the bigger picture.",
        ],
        agrees_with=["researcher"],
        challenges=["builder"]  # Sometimes reins in builder's enthusiasm
    ),
    "researcher": AgentPersonality(
        name="Researcher",
        voice="guy",
        role="Information gatherer who finds insights",
        traits=["curious", "thorough", "excited about discoveries", "detail-oriented"],
        speaking_style="enthusiastic when sharing findings, asks lots of questions",
        catchphrases=[
            "I found something interesting!",
            "The data suggests...",
            "What if we looked at it this way?",
            "Actually, there's more to this...",
        ],
        agrees_with=["planner"],
        challenges=["critic"]  # Defends findings against criticism
    ),
    "builder": AgentPersonality(
        name="Builder",
        voice="christopher",
        role="Executor who makes things happen",
        traits=["pragmatic", "action-oriented", "impatient with theory", "hands-on"],
        speaking_style="direct and practical, wants to get things done",
        catchphrases=[
            "Let me just build it.",
            "I can make that work.",
            "Here's how I'd implement it...",
            "Less talking, more doing.",
        ],
        agrees_with=["planner"],
        challenges=["critic"]  # Gets frustrated with too much criticism
    ),
    "critic": AgentPersonality(
        name="Critic",
        voice="eric",
        role="Quality guardian who catches problems",
        traits=["skeptical", "thorough", "fair", "asks hard questions"],
        speaking_style="measured, often plays devil's advocate, but constructive",
        catchphrases=[
            "Have we considered...",
            "I see a potential issue.",
            "Let me push back on that.",
            "That's good, but what about...",
        ],
        agrees_with=["researcher"],
        challenges=["builder"]  # Naturally questions builder's work
    ),
    "narrator": AgentPersonality(
        name="Narrator",
        voice="jenny",
        role="Audience bridge who explains and engages",
        traits=["warm", "clear", "engaging", "summarizes well"],
        speaking_style="friendly and accessible, breaks down complexity",
        catchphrases=[
            "Let me explain what's happening here.",
            "This is where it gets interesting.",
            "Watch closely...",
            "Here's the key takeaway.",
        ],
        agrees_with=["planner", "researcher", "builder", "critic"],
        challenges=[]  # Narrator is neutral, bridges to audience
    ),
}


@dataclass
class DialogueTurn:
    """A single turn in the conversation."""
    speaker: str
    message: str
    addresses: Optional[str] = None  # Who they're talking to
    conversation_type: ConversationType = ConversationType.STATEMENT
    emotion: str = "neutral"  # neutral, excited, concerned, frustrated, amused


class DialogueOrchestrator:
    """Orchestrates natural conversations between agents."""

    def __init__(self):
        self.conversation_history: List[DialogueTurn] = []
        self.current_topic: str = ""
        self.tension_level: int = 0  # 0-10, affects likelihood of disagreement

    def set_status(self, agent: str, text: str, speaking: bool = True):
        """Update agent speech status for the monitor."""
        try:
            status = {
                "agent": agent,
                "speaking": speaking,
                "text": text[:100] if text else "",
                "timestamp": time.time()
            }
            with open(STATUS_FILE, "w") as f:
                json.dump(status, f)
        except:
            pass

    def speak(self, agent: str, text: str) -> bool:
        """Have an agent speak with their voice."""
        personality = AGENTS.get(agent.lower())
        if not personality:
            return False

        voice = personality.voice
        self.set_status(agent, text, speaking=True)

        try:
            result = subprocess.run(
                ["python3", str(VOICE_SCRIPT), text, voice],
                capture_output=True,
                timeout=60
            )
            success = result.returncode == 0
        except Exception as e:
            print(f"Speech error: {e}")
            success = False

        self.set_status(agent, "", speaking=False)
        time.sleep(0.3)  # Brief pause between speakers
        return success

    def add_personality_flavor(self, agent: str, message: str, conv_type: ConversationType) -> str:
        """Add personality-appropriate phrases to the message."""
        personality = AGENTS.get(agent.lower())
        if not personality:
            return message

        # Sometimes add a catchphrase
        if random.random() < 0.3 and personality.catchphrases:
            catchphrase = random.choice(personality.catchphrases)
            if conv_type == ConversationType.STATEMENT:
                message = f"{catchphrase} {message}"

        return message

    def generate_response_opener(self, speaker: str, addresses: Optional[str], conv_type: ConversationType) -> str:
        """Generate an appropriate opener based on conversation type."""
        openers = {
            ConversationType.AGREEMENT: [
                f"I agree with {addresses}.",
                f"That's a good point, {addresses}.",
                f"{addresses} is right.",
                "Exactly.",
                "I was thinking the same thing.",
            ],
            ConversationType.DISAGREEMENT: [
                f"I'm not sure I agree with {addresses} here.",
                f"Let me push back on that, {addresses}.",
                "I see it differently.",
                f"Hold on, {addresses}.",
                "That's one way to look at it, but...",
            ],
            ConversationType.QUESTION: [
                f"{addresses}, what do you think about",
                f"I have a question for {addresses}.",
                f"{addresses}, can you clarify",
                "Here's what I'm wondering:",
            ],
            ConversationType.BUILD_ON: [
                f"Building on what {addresses} said,",
                f"To add to {addresses}'s point,",
                "And there's another angle here.",
                "That reminds me,",
            ],
            ConversationType.DISCOVERY: [
                "Wait, I just realized something.",
                "This changes things.",
                "I found something important.",
                "Hold on everyone,",
            ],
            ConversationType.DECISION: [
                "Okay team, we need to decide.",
                "Let's make a call here.",
                "Here's what we're going to do.",
                "Decision time.",
            ],
            ConversationType.PIVOT: [
                "We need to change direction.",
                "New information, new plan.",
                "Let's pivot.",
                "Forget what I said earlier.",
            ],
            ConversationType.AUDIENCE_HOOK: [
                "Now here's where it gets interesting.",
                "Watch what happens next.",
                "This is the critical moment.",
                "Pay attention to this part.",
            ],
        }

        if conv_type in openers:
            opener = random.choice(openers[conv_type])
            if addresses and "{addresses}" not in opener and conv_type != ConversationType.AUDIENCE_HOOK:
                # Sometimes add direct address
                if random.random() < 0.4:
                    opener = f"{addresses}, {opener.lower()}"
            return opener
        return ""

    def create_dialogue_turn(
        self,
        speaker: str,
        content: str,
        addresses: Optional[str] = None,
        conv_type: ConversationType = ConversationType.STATEMENT
    ) -> DialogueTurn:
        """Create a dialogue turn with appropriate formatting."""

        # Get opener based on conversation type
        opener = self.generate_response_opener(speaker, addresses, conv_type)

        # Combine opener with content
        if opener:
            full_message = f"{opener} {content}"
        else:
            full_message = content

        # Add personality flavor
        full_message = self.add_personality_flavor(speaker, full_message, conv_type)

        turn = DialogueTurn(
            speaker=speaker,
            message=full_message,
            addresses=addresses,
            conversation_type=conv_type
        )

        self.conversation_history.append(turn)
        return turn

    def execute_turn(self, turn: DialogueTurn) -> bool:
        """Execute a dialogue turn (speak it)."""
        print(f"\n[{turn.speaker.upper()}]: {turn.message}")
        return self.speak(turn.speaker, turn.message)

    def natural_exchange(
        self,
        exchanges: List[Dict]
    ) -> List[DialogueTurn]:
        """
        Execute a natural exchange between agents.

        exchanges format:
        [
            {"speaker": "planner", "says": "content", "to": "builder", "type": "question"},
            {"speaker": "builder", "says": "content", "type": "statement"},
            ...
        ]
        """
        turns = []

        for exchange in exchanges:
            speaker = exchange.get("speaker", "narrator")
            content = exchange.get("says", "")
            addresses = exchange.get("to")
            conv_type_str = exchange.get("type", "statement")

            try:
                conv_type = ConversationType(conv_type_str)
            except:
                conv_type = ConversationType.STATEMENT

            turn = self.create_dialogue_turn(speaker, content, addresses, conv_type)
            self.execute_turn(turn)
            turns.append(turn)

            # Dynamic pause based on content length and type
            pause = 0.5 + (len(content) / 500)  # Longer content = longer pause
            if conv_type == ConversationType.DISCOVERY:
                pause += 0.5  # Extra pause for dramatic effect
            time.sleep(min(pause, 2.0))

        return turns

    def team_discussion(
        self,
        topic: str,
        context: str,
        allow_disagreement: bool = True,
        include_audience: bool = True
    ) -> List[DialogueTurn]:
        """
        Run a full team discussion on a topic.
        Returns the dialogue turns.
        """
        self.current_topic = topic
        turns = []

        # Narrator introduces (if including audience)
        if include_audience:
            intro = self.create_dialogue_turn(
                "narrator",
                f"The team is about to tackle {topic}. Let's see how they approach this.",
                conv_type=ConversationType.AUDIENCE_HOOK
            )
            self.execute_turn(intro)
            turns.append(intro)
            time.sleep(1)

        # Planner sets direction
        planner_turn = self.create_dialogue_turn(
            "planner",
            f"Alright team, {context}. Let's figure out the best approach.",
            conv_type=ConversationType.STATEMENT
        )
        self.execute_turn(planner_turn)
        turns.append(planner_turn)
        time.sleep(0.8)

        # Researcher provides information
        researcher_turn = self.create_dialogue_turn(
            "researcher",
            "I've been looking into this.",
            addresses="planner",
            conv_type=ConversationType.BUILD_ON
        )
        self.execute_turn(researcher_turn)
        turns.append(researcher_turn)
        time.sleep(0.8)

        # Builder wants to act
        builder_turn = self.create_dialogue_turn(
            "builder",
            "I think I know how to build this. Let me start working on it.",
            conv_type=ConversationType.STATEMENT
        )
        self.execute_turn(builder_turn)
        turns.append(builder_turn)
        time.sleep(0.8)

        # Critic raises concern (if allowing disagreement)
        if allow_disagreement and random.random() < 0.7:
            critic_turn = self.create_dialogue_turn(
                "critic",
                "Before you dive in, have we thought about edge cases?",
                addresses="builder",
                conv_type=ConversationType.DISAGREEMENT
            )
            self.execute_turn(critic_turn)
            turns.append(critic_turn)
            time.sleep(0.8)

            # Builder responds to critic
            builder_response = self.create_dialogue_turn(
                "builder",
                "Fair point. I'll keep that in mind as I build.",
                addresses="critic",
                conv_type=ConversationType.AGREEMENT
            )
            self.execute_turn(builder_response)
            turns.append(builder_response)
            time.sleep(0.8)

        # Planner makes decision
        decision_turn = self.create_dialogue_turn(
            "planner",
            "Good discussion. Let's move forward with this approach.",
            conv_type=ConversationType.DECISION
        )
        self.execute_turn(decision_turn)
        turns.append(decision_turn)

        # Narrator wraps up (if including audience)
        if include_audience:
            wrap = self.create_dialogue_turn(
                "narrator",
                "The team has made their decision. Now let's watch them execute.",
                conv_type=ConversationType.AUDIENCE_HOOK
            )
            self.execute_turn(wrap)
            turns.append(wrap)

        return turns


class ConversationBuilder:
    """
    Fluent API for building natural conversations.

    Usage:
        conv = ConversationBuilder()
        conv.planner("Let's discuss the architecture")
           .researcher("I found some interesting patterns", to="planner")
           .builder("I can implement that", agrees_with="researcher")
           .critic("But have we considered security?", challenges="builder")
           .planner("Good point. Let's address that.", decides=True)
           .narrator("The team is finding their rhythm.", to_audience=True)
           .execute()
    """

    def __init__(self):
        self.orchestrator = DialogueOrchestrator()
        self.exchanges: List[Dict] = []

    def _add(
        self,
        speaker: str,
        says: str,
        to: Optional[str] = None,
        conv_type: str = "statement"
    ) -> "ConversationBuilder":
        self.exchanges.append({
            "speaker": speaker,
            "says": says,
            "to": to,
            "type": conv_type
        })
        return self

    def planner(self, says: str, to: str = None, decides: bool = False, asks: bool = False) -> "ConversationBuilder":
        conv_type = "decision" if decides else ("question" if asks else "statement")
        return self._add("planner", says, to, conv_type)

    def researcher(self, says: str, to: str = None, discovers: bool = False, asks: bool = False) -> "ConversationBuilder":
        conv_type = "discovery" if discovers else ("question" if asks else "statement")
        return self._add("researcher", says, to, conv_type)

    def builder(self, says: str, to: str = None, agrees_with: str = None, asks: bool = False) -> "ConversationBuilder":
        conv_type = "agreement" if agrees_with else ("question" if asks else "statement")
        to = to or agrees_with
        return self._add("builder", says, to, conv_type)

    def critic(self, says: str, to: str = None, challenges: str = None, agrees_with: str = None) -> "ConversationBuilder":
        if challenges:
            conv_type = "disagreement"
            to = to or challenges
        elif agrees_with:
            conv_type = "agreement"
            to = to or agrees_with
        else:
            conv_type = "statement"
        return self._add("critic", says, to, conv_type)

    def narrator(self, says: str, to_audience: bool = True) -> "ConversationBuilder":
        conv_type = "audience_hook" if to_audience else "statement"
        return self._add("narrator", says, None, conv_type)

    def pause(self, seconds: float = 1.0) -> "ConversationBuilder":
        """Add a pause in the conversation."""
        self.exchanges.append({"pause": seconds})
        return self

    def execute(self) -> List[DialogueTurn]:
        """Execute all the exchanges."""
        turns = []
        for exchange in self.exchanges:
            if "pause" in exchange:
                time.sleep(exchange["pause"])
            else:
                turn_list = self.orchestrator.natural_exchange([exchange])
                turns.extend(turn_list)
        return turns


def demo_conversation():
    """Demo showing the dialogue system capabilities."""

    print("=" * 60)
    print("  AGENT TEAM DIALOGUE DEMO")
    print("=" * 60)
    print()

    conv = ConversationBuilder()

    conv.narrator("Welcome back! Today the team is tackling something exciting.") \
        .pause(0.5) \
        .planner("Alright team, we need to build an OBS integration. This will let us record our sessions automatically.") \
        .researcher("I've been looking into the OBS API.", to="planner") \
        .researcher("It has WebSocket support built in. We can control everything programmatically.", discovers=True) \
        .builder("Nice! I can work with that. Let me start setting up the connection.", agrees_with="researcher") \
        .critic("Hold on, Builder.", challenges="builder") \
        .critic("Have we thought about error handling? What if OBS isn't running?") \
        .builder("Fair point, Critic. I'll add connection checks.", to="critic") \
        .planner("Good catch. Let's make it robust.", decides=True) \
        .narrator("Notice how the Critic caught a potential issue before it became a problem. That's the value of having different perspectives on the team.") \
        .pause(1.0) \
        .researcher("One more thing.", to="planner") \
        .researcher("I found that we can also control audio levels through the API. We could automatically unmute Desktop Audio when recording starts.", discovers=True) \
        .planner("Excellent find, Researcher. Builder, can you add that?", to="builder", asks=True) \
        .builder("Already on it.", to="planner") \
        .narrator("And just like that, the team is building something real. Stay tuned to see the result.") \
        .execute()

    print()
    print("=" * 60)
    print("  DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo_conversation()
    else:
        print("Agent Team Dialogue Orchestrator")
        print("-" * 40)
        print("Usage:")
        print("  python dialogue_orchestrator.py demo    # Run demo conversation")
        print()
        print("Or import and use in your code:")
        print("  from dialogue_orchestrator import ConversationBuilder")
        print("  conv = ConversationBuilder()")
        print("  conv.planner('Hello team').researcher('Hi!').execute()")

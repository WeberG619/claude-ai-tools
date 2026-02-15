#!/usr/bin/env python3
"""
Agent Team Session Runner
=========================
Runs full agent sessions with natural dialogue, OBS integration,
and real work being done. Designed for YouTube-quality content.
"""

import json
import subprocess
import time
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Import our dialogue system
from dialogue_orchestrator import ConversationBuilder, DialogueOrchestrator, AGENTS

# OBS control
OBS_HOST = "192.168.1.51"
OBS_PORT = 4455
OBS_PASSWORD = "2GwO1bvUqSIy3V2X"


class SessionPhase(Enum):
    INTRO = "intro"
    PLANNING = "planning"
    RESEARCH = "research"
    BUILDING = "building"
    REVIEW = "review"
    CONCLUSION = "conclusion"


@dataclass
class SessionConfig:
    """Configuration for a session."""
    title: str
    goal: str
    project_path: Optional[str] = None
    auto_record: bool = True
    include_audience_hooks: bool = True
    allow_disagreements: bool = True
    max_duration_minutes: int = 30


class OBSController:
    """Controls OBS recording."""

    def __init__(self):
        self.client = None
        self.recording = False

    def connect(self) -> bool:
        """Connect to OBS."""
        try:
            import obsws_python as obs
            self.client = obs.ReqClient(
                host=OBS_HOST,
                port=OBS_PORT,
                password=OBS_PASSWORD,
                timeout=5
            )
            return True
        except Exception as e:
            print(f"OBS connection failed: {e}")
            return False

    def start_recording(self) -> Optional[str]:
        """Start recording and return success status."""
        if not self.client:
            if not self.connect():
                return None
        try:
            self.client.start_record()
            self.recording = True
            time.sleep(1)  # Let recording stabilize
            return "Recording started"
        except Exception as e:
            return f"Failed: {e}"

    def stop_recording(self) -> Optional[str]:
        """Stop recording and return file path."""
        if not self.client or not self.recording:
            return None
        try:
            result = self.client.stop_record()
            self.recording = False
            return result.output_path if hasattr(result, 'output_path') else "Recording saved"
        except Exception as e:
            return f"Failed: {e}"

    def ensure_audio(self):
        """Ensure Desktop Audio is unmuted."""
        if not self.client:
            if not self.connect():
                return
        try:
            self.client.set_input_mute('Desktop Audio', False)
        except:
            pass

    def disconnect(self):
        """Disconnect from OBS."""
        if self.client:
            try:
                self.client.disconnect()
            except:
                pass
            self.client = None


class AgentSession:
    """
    Runs a full agent team session.
    Orchestrates dialogue, work, and recording.
    """

    def __init__(self, config: SessionConfig):
        self.config = config
        self.conv = ConversationBuilder()
        self.obs = OBSController()
        self.phase = SessionPhase.INTRO
        self.start_time = None
        self.recording_path = None

    def run_intro(self):
        """Run the introduction phase."""
        self.phase = SessionPhase.INTRO

        self.conv.narrator(f"Welcome to Agent Team! Today we're working on: {self.config.title}")
        self.conv.pause(0.5)
        self.conv.narrator(f"Our goal: {self.config.goal}")
        self.conv.pause(0.5)
        self.conv.narrator("Let's see how the team approaches this challenge.")
        self.conv.pause(1.0)

        # Team acknowledgment
        self.conv.planner("Alright team, you heard the goal. Let's make it happen.")
        self.conv.researcher("I'm ready to dig into the research.", to="planner")
        self.conv.builder("Let's build something great.", agrees_with="planner")
        self.conv.critic("I'll make sure we do it right.", to="planner")

        self.conv.execute()
        self.conv = ConversationBuilder()  # Reset for next phase

    def run_planning(self, plan_details: str):
        """Run the planning phase."""
        self.phase = SessionPhase.PLANNING

        self.conv.narrator("The Planner is taking the lead.", to_audience=True)
        self.conv.pause(0.5)

        self.conv.planner(f"Here's how I see this breaking down. {plan_details}")
        self.conv.pause(0.3)

        self.conv.researcher("That makes sense. Should I start gathering information?", to="planner", asks=True)
        self.conv.planner("Yes, go ahead Researcher.", to="researcher", decides=True)

        if self.config.allow_disagreements:
            self.conv.critic("Before we commit, are we sure this is the right approach?", challenges="planner")
            self.conv.planner("Good question, Critic. Here's why I think so...", to="critic")
            self.conv.critic("Okay, I'm convinced. Let's proceed.", agrees_with="planner")

        self.conv.execute()
        self.conv = ConversationBuilder()

    def run_research(self, findings: List[Dict[str, str]]):
        """
        Run the research phase.
        findings: [{"topic": "...", "finding": "..."}, ...]
        """
        self.phase = SessionPhase.RESEARCH

        self.conv.narrator("Now the Researcher is in their element.", to_audience=True)
        self.conv.pause(0.5)

        for i, finding in enumerate(findings):
            topic = finding.get("topic", "this topic")
            content = finding.get("finding", "I found some useful information.")

            if i == 0:
                self.conv.researcher(f"I've been looking into {topic}.", to="planner")
                self.conv.researcher(content, discovers=True)
            else:
                self.conv.researcher(f"And regarding {topic}...", to="planner")
                self.conv.researcher(content, discovers=True)

            # React to findings
            if i == 0:
                self.conv.planner("Interesting. This changes things.", to="researcher")
            elif i == len(findings) - 1:
                self.conv.builder("I can work with this information.", agrees_with="researcher")

            self.conv.pause(0.3)

        self.conv.execute()
        self.conv = ConversationBuilder()

    def run_building(self, steps: List[Dict[str, str]], on_step_complete: Optional[callable] = None):
        """
        Run the building phase.
        steps: [{"description": "...", "details": "..."}, ...]
        on_step_complete: callback function to do actual work
        """
        self.phase = SessionPhase.BUILDING

        self.conv.narrator("Time for the Builder to shine. Watch the code come together.", to_audience=True)
        self.conv.pause(0.5)

        self.conv.builder("Alright, I'm starting to build.", to="planner")
        self.conv.execute()
        self.conv = ConversationBuilder()

        for i, step in enumerate(steps):
            description = step.get("description", "Working on the next piece")
            details = step.get("details", "")

            self.conv.builder(f"Step {i+1}: {description}")

            if details:
                self.conv.builder(details)

            self.conv.execute()
            self.conv = ConversationBuilder()

            # Execute actual work if callback provided
            if on_step_complete:
                result = on_step_complete(step)
                if result:
                    self.conv.builder(f"Done. {result}")
                    self.conv.execute()
                    self.conv = ConversationBuilder()

            # Occasional critic interjection
            if self.config.allow_disagreements and i == len(steps) // 2:
                self.conv.critic("Looking good so far, but don't forget error handling.", to="builder")
                self.conv.builder("On it.", to="critic")
                self.conv.execute()
                self.conv = ConversationBuilder()

            time.sleep(0.5)

        self.conv.builder("Build complete!", to="planner")
        self.conv.planner("Great work, Builder.", to="builder")
        self.conv.execute()
        self.conv = ConversationBuilder()

    def run_review(self, review_points: List[str]):
        """
        Run the review phase.
        review_points: List of things to review
        """
        self.phase = SessionPhase.REVIEW

        self.conv.narrator("Now comes the critical review. This is where quality gets ensured.", to_audience=True)
        self.conv.pause(0.5)

        self.conv.critic("Let me take a look at what we've built.", to="builder")
        self.conv.execute()
        self.conv = ConversationBuilder()

        for i, point in enumerate(review_points):
            if i < len(review_points) - 1:
                self.conv.critic(point)
            else:
                # Last point - wrap up positively
                self.conv.critic(point)
                self.conv.critic("Overall, this is solid work.", agrees_with="builder")

            self.conv.execute()
            self.conv = ConversationBuilder()
            time.sleep(0.3)

        self.conv.builder("Thanks for the thorough review, Critic.", to="critic")
        self.conv.planner("Good collaboration, team.", to="critic")
        self.conv.execute()
        self.conv = ConversationBuilder()

    def run_conclusion(self, summary: str, next_steps: Optional[List[str]] = None):
        """Run the conclusion phase."""
        self.phase = SessionPhase.CONCLUSION

        self.conv.narrator("Let's wrap up and see what the team accomplished.", to_audience=True)
        self.conv.pause(0.5)

        self.conv.planner(f"Great session, team. {summary}")

        if next_steps:
            self.conv.planner("For next time, we should work on:")
            for step in next_steps[:3]:  # Limit to 3
                self.conv.planner(f"- {step}")

        self.conv.researcher("I learned a lot today.", to="planner")
        self.conv.builder("The code is ready for the next phase.", to="planner")
        self.conv.critic("I'm satisfied with the quality.", agrees_with="builder")

        self.conv.pause(0.5)
        self.conv.narrator(f"And that's a wrap! The team successfully completed: {self.config.title}")
        self.conv.narrator("Thanks for watching. See you next time!")

        self.conv.execute()

    def start(self):
        """Start the session, including OBS recording if enabled."""
        self.start_time = time.time()

        if self.config.auto_record:
            print("Starting OBS recording...")
            self.obs.ensure_audio()
            result = self.obs.start_recording()
            if result:
                print(f"OBS: {result}")
            time.sleep(1)

    def end(self) -> Optional[str]:
        """End the session and stop recording."""
        if self.config.auto_record:
            print("Stopping OBS recording...")
            result = self.obs.stop_recording()
            if result:
                print(f"OBS: Recording saved to {result}")
                self.recording_path = result
            self.obs.disconnect()

        elapsed = time.time() - self.start_time if self.start_time else 0
        print(f"\nSession complete! Duration: {elapsed/60:.1f} minutes")

        return self.recording_path


def run_demo_session():
    """Run a demo session to show the system."""

    config = SessionConfig(
        title="Building the OBS MCP Server",
        goal="Create a system that lets our agents control their own recordings",
        auto_record=True,
        include_audience_hooks=True,
        allow_disagreements=True
    )

    session = AgentSession(config)

    print("=" * 60)
    print("  AGENT TEAM SESSION")
    print(f"  {config.title}")
    print("=" * 60)
    print()

    # Start recording
    session.start()
    time.sleep(1)

    # Run the session phases
    session.run_intro()
    time.sleep(0.5)

    session.run_planning(
        "We need three main components: the OBS connection, the tool handlers, and the MCP protocol. "
        "Researcher will find the API details, Builder will write the code, and Critic will review."
    )
    time.sleep(0.5)

    session.run_research([
        {
            "topic": "OBS WebSocket API",
            "finding": "OBS has a built-in WebSocket server on port 4455. We can use Python's obsws-python library to connect."
        },
        {
            "topic": "available commands",
            "finding": "We can start recording, stop recording, switch scenes, control audio, and take screenshots. Everything we need."
        }
    ])
    time.sleep(0.5)

    session.run_building([
        {"description": "Setting up the OBS connection", "details": "Creating the client with authentication"},
        {"description": "Adding recording controls", "details": "Start, stop, pause, and resume functions"},
        {"description": "Implementing audio controls", "details": "Volume and mute management"},
        {"description": "Wrapping it as an MCP server", "details": "Adding the JSON-RPC protocol layer"}
    ])
    time.sleep(0.5)

    session.run_review([
        "The connection handling looks good. It properly catches exceptions.",
        "Recording controls are complete. I like that stop returns the file path.",
        "Audio controls work well. Good that you added the unmute on session start."
    ])
    time.sleep(0.5)

    session.run_conclusion(
        "We built a fully functional OBS MCP server that lets us control recordings programmatically.",
        ["Add scene management features", "Build a recording dashboard", "Create automated highlight detection"]
    )

    # Stop recording and get path
    recording_path = session.end()

    if recording_path:
        print(f"\n Recording saved: {recording_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_demo_session()
    else:
        print("Agent Team Session Runner")
        print("-" * 40)
        print("Usage:")
        print("  python session_runner.py demo    # Run demo session")
        print()
        print("Or import and use in your code:")
        print("  from session_runner import AgentSession, SessionConfig")

#!/usr/bin/env python3
"""
Autonomous Agent System - Real AI-powered agents using Claude API
=================================================================
Each agent calls Claude API with their unique persona and context.
They make real decisions, not scripted responses.
"""

import os
import json
import time
import asyncio
from pathlib import Path
from typing import Optional, Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / '.env')

import anthropic

# Import the visual session for dashboard integration
from visual_session import VisualActivityController
from dialogue_v2 import DEVS, STATUS_FILE

# Import speech coordinator for synchronized speech (prevents overlap)
try:
    from speech_coordinator import SpeechCoordinator
    SPEECH_COORDINATOR = SpeechCoordinator()
    SPEECH_COORD_AVAILABLE = True
except ImportError:
    SPEECH_COORDINATOR = None
    SPEECH_COORD_AVAILABLE = False

# Import visual sync for real-time dashboard updates
try:
    from visual_sync import VisualSyncController, sync_response
    VISUAL_SYNC_AVAILABLE = True
except ImportError:
    VISUAL_SYNC_AVAILABLE = False

# Import execution bridge for real action execution
try:
    from execution_bridge import (
        ExecutionBridge, ExecutionResult, format_execution_results
    )
    EXECUTION_BRIDGE_AVAILABLE = True
except ImportError:
    EXECUTION_BRIDGE_AVAILABLE = False
    ExecutionBridge = None
    ExecutionResult = None

# Voice script for TTS
VOICE_SCRIPT = Path("/mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py")

# Global flag to disable voice/TTS - set to True to mute all agent speech
VOICE_DISABLED = False  # Voice ENABLED - agents narrate their actions


def extract_narration(text: str) -> str:
    """
    Extract BRIEF speakable narration from agent response.
    AGGRESSIVELY removes code - we show code visually, don't read it.
    Only keep 1-2 sentences of explanation.
    """
    import re

    # COMPLETELY REMOVE code blocks - don't even say "code written"
    text = re.sub(r'```[\s\S]*?```', '', text)

    # Remove ALL inline code (backticks)
    text = re.sub(r'`[^`]+`', '', text)

    # Remove anything that looks like code (lines starting with def, class, import, etc)
    text = re.sub(r'^(def |class |import |from |if |for |while |return |#).*$', '', text, flags=re.MULTILINE)

    # Remove raw JSON/dict/list content
    text = re.sub(r'[\{\[][\s\S]*?[\}\]]', '', text)

    # Remove file paths
    text = re.sub(r'[/\\][\w./\\-]+\.\w+', '', text)

    # Remove bullet points and numbered lists
    text = re.sub(r'^[\s]*[-*•]\s+.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+.*$', '', text, flags=re.MULTILINE)

    # Remove markdown headers
    text = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE)

    # Remove "Here's", "Let me create", etc followed by filename - just keep brief intro
    text = re.sub(r"(Let me create|Here's|Creating|Writing)\s+\w+\.\w+.*", r'\1 the file.', text)

    # Clean up whitespace
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r' +', ' ', text)
    text = text.strip()

    # Keep ONLY first 1-2 sentences (max 150 chars for quick speech)
    if len(text) > 150:
        # Find first sentence boundary
        end = text.find('. ')
        if end > 20 and end < 150:
            text = text[:end+1]
        else:
            text = text[:150].rsplit(' ', 1)[0] + '...'

    return text.strip()


@dataclass
class AgentPersona:
    """Defines an agent's personality and capabilities."""
    name: str
    role: str
    voice: str
    system_prompt: str
    tools: List[str] = field(default_factory=list)
    temperature: float = 0.7


# Define agent personas with detailed system prompts
AGENT_PERSONAS = {
    "planner": AgentPersona(
        name="Planner",
        role="Tech Lead",
        voice="andrew",
        system_prompt="""You are the PLANNER, a senior tech lead on a development team.

Your personality:
- Strategic thinker who sees the big picture
- Keeps discussions focused and productive
- Makes clear decisions when needed
- Delegates tasks effectively
- Calm and composed under pressure

Your responsibilities:
- Define project goals and milestones
- Break down complex tasks into manageable pieces
- Coordinate between team members
- Make architectural decisions
- Ensure the team stays on track

Communication style:
- Clear, concise, professional
- Use phrases like "Let's focus on...", "The priority is...", "Here's the plan..."
- Keep responses to 1-3 sentences for natural conversation
- Speak as if in a real team meeting

You are in a live team session. Respond naturally as the Planner would in a real conversation.""",
        temperature=0.6
    ),

    "researcher": AgentPersona(
        name="Researcher",
        role="Technical Researcher",
        voice="christopher",
        system_prompt="""You are the RESEARCHER, the team's technical research specialist.

Your personality:
- Curious and thorough
- Data-driven decision maker
- Enjoys diving deep into documentation
- Shares findings concisely
- Backs claims with evidence

Your responsibilities:
- Research technical solutions and best practices
- Find relevant documentation and examples
- Analyze competitor approaches
- Verify technical feasibility
- Report findings to the team

Communication style:
- Informative but not overwhelming
- Use phrases like "I found that...", "The data shows...", "Based on my research..."
- Keep responses to 1-3 sentences for natural conversation
- Share key insights, not exhaustive details

You are in a live team session. Respond naturally as the Researcher would in a real conversation.""",
        temperature=0.7
    ),

    "builder": AgentPersona(
        name="Builder",
        role="Backend Developer",
        voice="adam",
        system_prompt="""You are the BUILDER, the team's backend developer and implementer.

Your personality:
- Pragmatic and action-oriented
- Prefers simple, working solutions over complex ones
- Hands-on problem solver
- Sometimes impatient with over-planning
- Confident in technical abilities

Your responsibilities:
- Write and review backend code
- Implement APIs, databases, server logic
- Solve technical problems
- Estimate implementation effort
- Build prototypes quickly

**EXECUTION MODE INSTRUCTIONS:**
When asked to create code, you MUST output it in executable format:
1. First say "Let me create [filename]:" (e.g., "Let me create calculator.py:")
2. Then output the complete code in a code block with language tag
3. Include a test in the code's __main__ block so it can be verified

Example format:
Let me create calculator.py:
```python
def add(a, b):
    return a + b

if __name__ == '__main__':
    print(f'Test: add(2,3) = {add(2,3)}')
```

This format allows the execution bridge to detect and run your code automatically.

Communication style:
- Direct and practical
- When creating code, ALWAYS use the format above
- Focus on doing rather than discussing

You are in a live team session with execution enabled.""",
        temperature=0.7
    ),

    "builder-frontend": AgentPersona(
        name="Builder-Frontend",
        role="Frontend Developer",
        voice="roger",
        system_prompt="""You are the BUILDER-FRONTEND, the team's frontend developer and UI specialist.

Your personality:
- Creative and visual-focused
- Passionate about user experience
- Detail-oriented with design
- Advocates for the end user
- Excited about modern frameworks

Your responsibilities:
- Build React components and UI
- Implement CSS/Tailwind styling
- Create responsive, accessible interfaces
- Handle client-side state management
- Optimize frontend performance

Communication style:
- Enthusiastic about UI work
- Use phrases like "The user will love...", "Let me style that...", "The component is ready..."
- Keep responses to 1-3 sentences for natural conversation
- Focus on visual and UX outcomes

You are in a live team session. Respond naturally as the Frontend Builder would in a real conversation.""",
        temperature=0.7
    ),

    "builder-infra": AgentPersona(
        name="Builder-Infra",
        role="DevOps Engineer",
        voice="davis",
        system_prompt="""You are the BUILDER-INFRA, the team's DevOps and infrastructure specialist.

Your personality:
- Systematic and reliability-focused
- Automation enthusiast
- Security-conscious
- Thinks about scale and maintainability
- Prefers infrastructure-as-code

Your responsibilities:
- Write Dockerfiles and compose configs
- Set up CI/CD pipelines
- Handle cloud deployment
- Configure monitoring and logging
- Ensure system reliability

Communication style:
- Methodical and thorough
- Use phrases like "The pipeline will...", "Deploying to...", "The container is configured..."
- Keep responses to 1-3 sentences for natural conversation
- Focus on reliability and automation

You are in a live team session. Respond naturally as the Infrastructure Builder would in a real conversation.""",
        temperature=0.7
    ),

    "critic": AgentPersona(
        name="Critic",
        role="Quality & Security Reviewer",
        voice="eric",
        system_prompt="""You are the CRITIC, the team's quality and security specialist.

Your personality:
- Detail-oriented and thorough
- Constructively critical (not negative)
- Focused on edge cases and risks
- Values code quality and security
- Asks probing questions

Your responsibilities:
- Review code for bugs and security issues
- Identify potential problems early
- Ensure quality standards are met
- Challenge assumptions constructively
- Suggest improvements

Communication style:
- Thoughtful and questioning
- Use phrases like "Have we considered...", "What happens if...", "The risk here is..."
- Keep responses to 1-3 sentences for natural conversation
- Raise concerns without being negative

You are in a live team session. Respond naturally as the Critic would in a real conversation.""",
        temperature=0.6
    ),

    "narrator": AgentPersona(
        name="Narrator",
        role="Technical Product Expert",
        voice="jenny",
        system_prompt="""You are the NARRATOR, providing context and insights to viewers watching the team work.

Your personality:
- Warm and engaging
- Educational without being condescending
- Highlights important moments
- Provides context for technical decisions
- Makes complex topics accessible

Your responsibilities:
- Explain what the team is doing to viewers
- Highlight key decisions and their implications
- Provide context for technical discussions
- Summarize progress and outcomes
- Make the session engaging for viewers

Communication style:
- Friendly and inclusive
- Use phrases like "What's happening here is...", "This is important because...", "Notice how..."
- Keep responses to 2-4 sentences
- Speak TO the audience, not to the team

You are narrating a live development session for an audience. Help them understand what's happening.""",
        temperature=0.8
    )
}


class AutonomousAgent:
    """A single autonomous agent that calls Claude API."""

    def __init__(
        self,
        agent_type: str,
        client: anthropic.Anthropic,
        execution_bridge: Optional['ExecutionBridge'] = None
    ):
        self.agent_type = agent_type
        self.persona = AGENT_PERSONAS[agent_type]
        self.client = client
        self.conversation_history: List[Dict] = []
        self.visual = VisualActivityController()
        self.execution_bridge = execution_bridge

    def _update_status(self, text: str, speaking: bool = True, activity: dict = None):
        """Update the dashboard status file.

        Args:
            text: The text being spoken/displayed
            speaking: Whether the agent is currently speaking
            activity: Optional activity dict with type (code_write, terminal_run, browser_navigate)
        """
        try:
            status = {
                "agent": self.agent_type,
                "speaking": speaking,
                "text": text[:200] if text else "",
                "timestamp": time.time()
            }
            # IMPORTANT: Preserve activity field for visual display
            if activity:
                status["activity"] = activity
            with open(STATUS_FILE, "w") as f:
                json.dump(status, f)
        except Exception as e:
            print(f"Status update error: {e}")

    def _speak(self, text: str, activity: dict = None) -> bool:
        """Speak the text using TTS with SYNCHRONIZED access.

        Uses SpeechCoordinator for file-locking to prevent overlapping speech.
        Extracts narration only (no code - code is shown visually).

        Args:
            text: The text to speak (narration will be extracted)
            activity: Optional activity to preserve in status (for visual display)
        """
        # Store activity for use in finally block (ensures view persists after speech)
        self._last_activity = activity
        import subprocess
        import threading

        # Check if voice is disabled globally
        if VOICE_DISABLED:
            # Still update status for visual feedback, but don't speak
            self._update_status(text, speaking=True, activity=activity)
            time.sleep(0.1)  # Brief pause for visual update
            self._update_status(text, speaking=False, activity=activity)  # Preserve activity!
            return True

        # Extract narration only (strips code blocks, technical output)
        narration = extract_narration(text)
        if not narration or len(narration) < 10:
            # Nothing meaningful to speak - just show visual
            self._update_status(text, speaking=True, activity=activity)
            time.sleep(0.3)
            self._update_status(text, speaking=False, activity=activity)  # Preserve activity!
            return True

        try:
            # Set speaking status BEFORE starting TTS (preserve activity!)
            self._update_status(text, speaking=True, activity=activity)

            # Keep updating status while speaking to maintain green light
            speaking_active = True

            def keep_alive():
                """Keep the speaking status alive during TTS."""
                while speaking_active:
                    # IMPORTANT: Preserve activity during speech!
                    self._update_status(text, speaking=True, activity=activity)
                    time.sleep(0.5)  # Update every 500ms

            # Start keep-alive thread
            keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
            keep_alive_thread.start()

            # Use COORDINATOR for synchronized speech (prevents overlap)
            if SPEECH_COORD_AVAILABLE and SPEECH_COORDINATOR:
                # SpeechCoordinator handles file locking internally
                result = SPEECH_COORDINATOR.speak(
                    agent=self.agent_type,
                    text=narration,
                    rate="+10%"
                )
            else:
                # Fallback: direct subprocess (no locking)
                result = subprocess.run(
                    ["python3", str(VOICE_SCRIPT), narration, self.persona.voice],
                    capture_output=True,
                    timeout=120
                )
                result = result.returncode == 0

            # Stop keep-alive
            speaking_active = False

            return result

        except Exception as e:
            print(f"Speech error: {e}")
            return False
        finally:
            # Clear speaking status but PRESERVE activity for view persistence
            self._update_status("", speaking=False, activity=getattr(self, '_last_activity', None))

    def think(self, context: str, team_history: List[Dict] = None) -> str:
        """
        Have the agent think and respond using Claude API.

        Args:
            context: Current situation or question
            team_history: Recent conversation from other agents

        Returns:
            The agent's response
        """
        # Build messages
        messages = []

        # Add team history as context
        if team_history:
            history_text = "\n".join([
                f"{msg['agent'].upper()}: {msg['text']}"
                for msg in team_history[-10:]  # Last 10 messages
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

        # Broadcast reasoning start - SHOW THE THINKING PROCESS
        if VISUAL_SYNC_AVAILABLE:
            try:
                sync = VisualSyncController()
                # Show what the agent is about to think about
                sync.broadcast_reasoning(self.agent_type, f"Analyzing: {context[:80]}...", "active")
                # Also push to terminal view so user can SEE it
                sync.push_status({
                    "agent": self.agent_type,
                    "speaking": False,
                    "text": f"[{self.persona.name}] Thinking about: {context[:150]}...",
                    "activity": {
                        "type": "terminal_run",
                        "command": f"# {self.persona.name} is analyzing the task...",
                        "output": f"Context: {context[:300]}..."
                    },
                    "timestamp": time.time()
                })
            except Exception as e:
                print(f"Visual sync error: {e}")

        # Call Claude API
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                temperature=self.persona.temperature,
                system=self.persona.system_prompt,
                messages=messages
            )

            response_text = response.content[0].text

            # NEW: Execute any actions in the response via ExecutionBridge
            if self.execution_bridge and EXECUTION_BRIDGE_AVAILABLE:
                try:
                    exec_result = self.execution_bridge.process_response(
                        self.agent_type, response_text
                    )

                    # Append execution results to response if any actions were taken
                    if exec_result.any_executed:
                        response_text += format_execution_results(exec_result)

                        # Push real execution results to dashboard with proper activity types
                        if VISUAL_SYNC_AVAILABLE:
                            sync = VisualSyncController()
                            for result in exec_result.results:
                                sync.push_execution_result(self.agent_type, result)
                                # Push code_write activity if file was written
                                if result.action_type == 'write_file' and result.success:
                                    sync.push_status({
                                        "agent": self.agent_type,
                                        "speaking": True,
                                        "text": f"Created {result.path}",
                                        "activity": {
                                            "type": "code_write",
                                            "file_path": str(result.path),
                                            "content": result.content or "",
                                            "language": "python" if str(result.path).endswith('.py') else "text"
                                        },
                                        "timestamp": time.time()
                                    })
                                # Push auto_test results to terminal view
                                elif result.action_type == 'auto_test':
                                    sync.push_status({
                                        "agent": self.agent_type,
                                        "speaking": True,
                                        "text": f"Testing {result.path}",
                                        "activity": {
                                            "type": "terminal_run",
                                            "command": f"python3 {result.path}",
                                            "output": result.output or result.error or "No output"
                                        },
                                        "timestamp": time.time()
                                    })
                except Exception as exec_error:
                    print(f"Execution bridge error for {self.agent_type}: {exec_error}")

            # Broadcast reasoning complete and sync visual activity
            # SHOW THE RESPONSE SO USER CAN SEE THE PLANNING
            if VISUAL_SYNC_AVAILABLE:
                try:
                    sync = VisualSyncController()
                    sync.broadcast_reasoning(self.agent_type, response_text[:100], "completed")

                    # Push the full response to terminal view so user can READ it
                    sync.push_status({
                        "agent": self.agent_type,
                        "speaking": True,
                        "text": response_text[:200],
                        "activity": {
                            "type": "terminal_run",
                            "command": f"# {self.persona.name}'s Response:",
                            "output": response_text
                        },
                        "timestamp": time.time()
                    })

                    # Detect and sync any file/URL references in response
                    sync.sync_from_response(self.agent_type, response_text)
                except Exception as e:
                    print(f"Visual sync error: {e}")

            return response_text

        except Exception as e:
            print(f"API error for {self.agent_type}: {e}")
            return f"[{self.persona.name} is thinking...]"

    def _detect_activity(self, text: str) -> Optional[dict]:
        """Detect activity type from response text for visual display."""
        import re
        text_lower = text.lower()

        # Check for code writing - be aggressive about detecting code blocks
        code_match = re.search(r'```(\w+)?\n([\s\S]*?)```', text)
        if code_match:
            lang = code_match.group(1) or 'text'
            code = code_match.group(2)
            # Try to find file path
            file_match = re.search(r'`([^`]+\.\w+)`|"([^"]+\.\w+)"|\'([^\']+\.\w+)\'', text)
            file_path = file_match.group(1) or file_match.group(2) or file_match.group(3) if file_match else 'code'
            return {
                "type": "code_write",
                "file_path": file_path,
                "content": code,
                "language": lang
            }

        # Check for terminal commands - expanded keywords
        if any(kw in text_lower for kw in ['running', 'executing', 'command:', '$ ', 'npm ', 'pip ', 'python ', 'git ', 'ls ', 'cd ', 'test', 'build']):
            cmd_match = re.search(r'`([^`]+)`|running\s+(\S+)', text, re.IGNORECASE)
            if cmd_match:
                cmd = cmd_match.group(1) or cmd_match.group(2)
                return {
                    "type": "terminal_run",
                    "command": cmd,
                    "output": ""
                }

        # Check for browser/URL
        url_match = re.search(r'(https?://[^\s<>"\']+)', text)
        if url_match and any(kw in text_lower for kw in ['navigate', 'browsing', 'opening', 'checking', 'documentation', 'research', 'found']):
            return {
                "type": "browser_navigate",
                "url": url_match.group(1),
                "title": ""
            }

        # ALWAYS return an activity - default to terminal view showing agent's thinking
        # This ensures the dashboard ALWAYS switches views based on agent activity
        return {
            "type": "terminal_run",
            "command": f"# {self.persona.name} is working...",
            "output": text[:500] if text else "Processing..."
        }

    def respond(self, context: str, team_history: List[Dict] = None, speak: bool = True) -> str:
        """
        Think and speak a response.

        Args:
            context: Current situation or question
            team_history: Recent conversation from other agents
            speak: Whether to speak the response (default True)

        Returns:
            The spoken response
        """
        response = self.think(context, team_history)

        # Detect activity for visual display
        activity = self._detect_activity(response)

        # Print and speak
        print(f"\n[{self.persona.name.upper()}]: {response}")
        if speak:
            self._speak(response, activity=activity)

        return response

    def speak_only(self, text: str, activity: dict = None):
        """Just speak pre-generated text."""
        print(f"\n[{self.persona.name.upper()}]: {text}")
        # Auto-detect activity if not provided
        if activity is None:
            activity = self._detect_activity(text)
        self._speak(text, activity=activity)


class AutonomousTeam:
    """
    A team of autonomous agents that can collaborate.
    """

    def __init__(
        self,
        workspace: Optional[Path] = None,
        enable_execution: bool = False
    ):
        """
        Initialize the autonomous team.

        Args:
            workspace: Root directory for file operations (default: current directory)
            enable_execution: If True, agents can execute real actions (files, commands, git)
                            If False, agents operate in simulation mode (no real execution)
        """
        # Initialize Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        self.client = anthropic.Anthropic(api_key=api_key)

        # Workspace and execution settings
        self.workspace = Path(workspace) if workspace else Path.cwd()
        self.enable_execution = enable_execution

        # Create execution bridge if enabled and available
        self.execution_bridge = None
        if enable_execution and EXECUTION_BRIDGE_AVAILABLE:
            self.execution_bridge = ExecutionBridge(
                workspace_root=self.workspace,
                enabled=True
            )
            print(f"✓ Execution bridge enabled (workspace: {self.workspace})")
        elif enable_execution:
            print("⚠ Execution requested but execution_bridge module not available")

        # Create agents with execution bridge
        self.agents = {
            name: AutonomousAgent(name, self.client, self.execution_bridge)
            for name in AGENT_PERSONAS.keys()
        }

        # Team conversation history
        self.team_history: List[Dict] = []

        # Visual controller for shared activities
        self.visual = VisualActivityController()

        # Browser agent for web research (lazy loaded)
        self._browser = None

    @property
    def browser(self):
        """Lazy load browser agent."""
        if self._browser is None:
            from interactive_browser import BrowserAgent
            self._browser = BrowserAgent()
        return self._browser

    async def research_web(self, topic: str) -> Dict:
        """Have the team research a topic on the web."""
        return await self.browser.research(topic)

    async def open_url(self, url: str) -> Dict:
        """Open and analyze a URL."""
        return await self.browser.open_and_analyze(url)

    def _add_to_history(self, agent: str, text: str):
        """Add a message to team history."""
        self.team_history.append({
            "agent": agent,
            "text": text,
            "timestamp": time.time()
        })

    @property
    def planner(self) -> AutonomousAgent:
        return self.agents["planner"]

    @property
    def researcher(self) -> AutonomousAgent:
        return self.agents["researcher"]

    @property
    def builder(self) -> AutonomousAgent:
        return self.agents["builder"]

    @property
    def critic(self) -> AutonomousAgent:
        return self.agents["critic"]

    @property
    def narrator(self) -> AutonomousAgent:
        return self.agents["narrator"]

    @property
    def builder_frontend(self) -> AutonomousAgent:
        return self.agents["builder-frontend"]

    @property
    def builder_infra(self) -> AutonomousAgent:
        return self.agents["builder-infra"]

    def parallel_build(self, tasks: Dict[str, str]) -> Dict[str, str]:
        """
        Execute multiple builder tasks in parallel.

        Args:
            tasks: Dict mapping builder name to task description
                   e.g., {"builder": "Create API", "builder-frontend": "Build form"}

        Returns:
            Dict mapping builder name to their response
        """
        print(f"\n{'='*60}")
        print(f"  PARALLEL BUILD: {len(tasks)} builders working simultaneously")
        print(f"{'='*60}\n")

        # Broadcast parallel start for dashboard
        try:
            from visual_sync import VisualSyncController
            sync = VisualSyncController()
            sync.broadcast_parallel_start(list(tasks.keys()))
        except ImportError:
            pass

        results = {}

        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all tasks
            futures = {}
            for builder_name, task in tasks.items():
                if builder_name in self.agents:
                    agent = self.agents[builder_name]
                    context = f"Your specialized task: {task}"
                    future = executor.submit(
                        agent.think, context, list(self.team_history)
                    )
                    futures[future] = builder_name
                else:
                    print(f"Warning: Unknown builder '{builder_name}'")

            # Collect results as they complete
            for future in as_completed(futures):
                builder_name = futures[future]
                try:
                    response = future.result()
                    results[builder_name] = response
                    self._add_to_history(builder_name, response)
                    print(f"[{builder_name.upper()}]: {response}")
                except Exception as e:
                    results[builder_name] = f"Error: {e}"
                    print(f"[{builder_name.upper()}] Error: {e}")

        # Speak results sequentially (TTS can't overlap)
        for builder_name, response in results.items():
            if builder_name in self.agents:
                self.agents[builder_name].speak_only(response)

        return results

    def discuss(self, topic: str, agents: List[str] = None, rounds: int = 1):
        """
        Have agents discuss a topic autonomously.
        Uses pipelining for faster transitions (1-2 sec between agents).

        Args:
            topic: The topic to discuss
            agents: Which agents should participate (default: all except narrator)
            rounds: How many rounds of discussion
        """
        import concurrent.futures

        if agents is None:
            agents = ["planner", "researcher", "builder", "critic"]

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

        # Narrator introduces - think first
        intro = self.narrator.think(
            f"Introduce this topic to the audience: {topic}",
            self.team_history
        )
        self._add_to_history("narrator", intro)

        # Pre-compute first agent response while narrator speaks
        first_agent = self.agents[agents[0]]
        context = f"""Topic: {topic}

Your turn to contribute to the discussion. What are your thoughts?
Keep your response brief (1-3 sentences) and natural."""

        next_future = executor.submit(first_agent.think, context, list(self.team_history))
        self.narrator.speak_only(intro)

        # Discussion rounds with pipelining
        all_speakers = []
        for round_num in range(rounds):
            all_speakers.extend(agents)

        for i, agent_name in enumerate(all_speakers):
            agent = self.agents[agent_name]

            # Get the pre-computed response
            response = next_future.result()
            self._add_to_history(agent_name, response)

            # Start computing next response while this one speaks
            if i + 1 < len(all_speakers):
                next_agent_name = all_speakers[i + 1]
                next_agent = self.agents[next_agent_name]
                next_future = executor.submit(next_agent.think, context, list(self.team_history))
            else:
                # Last agent - pre-compute narrator wrap-up
                next_future = executor.submit(
                    self.narrator.think,
                    "Summarize what the team just discussed for the audience.",
                    list(self.team_history)
                )

            agent.speak_only(response)

        # Narrator wraps up (already computed)
        wrap_up = next_future.result()
        self._add_to_history("narrator", wrap_up)
        self.narrator.speak_only(wrap_up)

        executor.shutdown(wait=False)

    def work_on_task(self, task: str):
        """
        Have the team work on a specific task autonomously.
        Uses pipelining for faster transitions (1-2 sec between agents).

        This is a more structured workflow:
        1. Planner breaks down the task
        2. Researcher gathers information
        3. Builder proposes implementation
        4. Critic reviews
        5. Team iterates
        """
        import concurrent.futures

        print(f"\n{'='*60}")
        print(f"  AUTONOMOUS TASK: {task}")
        print(f"{'='*60}\n")

        # Use thread pool for parallel thinking/speaking
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

        # Step 1: Narrator introduces (think + speak)
        intro = self.narrator.think(f"Introduce this task to the audience: {task}", self.team_history)
        self._add_to_history("narrator", intro)

        # Start thinking about planner's response while narrator speaks
        planner_future = executor.submit(
            self.planner.think,
            f"Analyze this task and break it down: {task}",
            list(self.team_history)  # Copy to avoid race condition
        )
        self.narrator.speak_only(intro)

        # Step 2: Planner speaks (already computed), start researcher thinking
        plan = planner_future.result()
        self._add_to_history("planner", plan)

        researcher_future = executor.submit(
            self.researcher.think,
            f"What information or research do we need for: {task}",
            list(self.team_history)
        )
        self.planner.speak_only(plan)

        # Step 3: Researcher speaks, start builder thinking
        research = researcher_future.result()
        self._add_to_history("researcher", research)

        builder_future = executor.submit(
            self.builder.think,
            f"How would you implement this: {task}",
            list(self.team_history)
        )
        self.researcher.speak_only(research)

        # Step 4: Builder speaks, start critic thinking
        build = builder_future.result()
        self._add_to_history("builder", build)

        critic_future = executor.submit(
            self.critic.think,
            f"Review the proposed approach. Any concerns?",
            list(self.team_history)
        )
        self.builder.speak_only(build)

        # Step 5: Critic speaks, start planner final thinking
        critique = critic_future.result()
        self._add_to_history("critic", critique)

        planner_final_future = executor.submit(
            self.planner.think,
            "Based on the discussion, what's our decision?",
            list(self.team_history)
        )
        self.critic.speak_only(critique)

        # Step 6: Planner decision, start narrator conclusion
        decision = planner_final_future.result()
        self._add_to_history("planner", decision)

        narrator_future = executor.submit(
            self.narrator.think,
            "Summarize the outcome for the audience.",
            list(self.team_history)
        )
        self.planner.speak_only(decision)

        # Step 7: Narrator concludes
        conclusion = narrator_future.result()
        self._add_to_history("narrator", conclusion)
        self.narrator.speak_only(conclusion)

        executor.shutdown(wait=False)


def demo_autonomous_team():
    """Demo the autonomous team working together."""
    print("\n" + "="*60)
    print("  AUTONOMOUS AGENT TEAM DEMO")
    print("="*60 + "\n")

    try:
        team = AutonomousTeam()
        print("✓ Team initialized with Claude API\n")

        # Have the team work on a real task
        team.work_on_task(
            "Improve the Agent Team dashboard by adding keyboard shortcuts"
        )

        print("\n" + "="*60)
        print("  DEMO COMPLETE")
        print("="*60)

    except ValueError as e:
        print(f"Error: {e}")
        print("\nMake sure ANTHROPIC_API_KEY is set in .env file")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo_autonomous_team()
    else:
        print("Autonomous Agent System")
        print("-" * 40)
        print("Usage:")
        print("  python autonomous_agents.py demo   # Run demo")
        print()
        print("Or import and use:")
        print("  from autonomous_agents import AutonomousTeam")
        print("  team = AutonomousTeam()")
        print("  team.work_on_task('Your task here')")

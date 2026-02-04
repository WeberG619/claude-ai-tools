#!/usr/bin/env python3
"""
Execution Bridge - Real Action Execution for Agent Team
========================================================
Parses agent responses and executes real actions (file I/O, commands, git).
Transforms agents from performative demos into actual work executors.
"""

import os
import re
import json
import time
import subprocess
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


class ActionType(Enum):
    """Types of actions that can be executed."""
    WRITE_FILE = "write_file"
    READ_FILE = "read_file"
    RUN_COMMAND = "run_command"
    GIT_OPERATION = "git_operation"
    TEST_RUN = "test_run"
    UNKNOWN = "unknown"


@dataclass
class Action:
    """Represents a parsed action from an agent response."""
    type: ActionType
    content: str
    file_path: Optional[str] = None
    language: Optional[str] = None
    raw_match: str = ""


@dataclass
class ToolResult:
    """Result of executing a tool/action."""
    success: bool
    output: str = ""
    error: Optional[str] = None
    action_type: str = ""
    path: Optional[str] = None
    content: Optional[str] = None


@dataclass
class ExecutionResult:
    """Complete result of processing an agent response."""
    actions: List[Action] = field(default_factory=list)
    results: List[ToolResult] = field(default_factory=list)

    @property
    def any_executed(self) -> bool:
        return len(self.results) > 0

    @property
    def all_succeeded(self) -> bool:
        return all(r.success for r in self.results)


# Dangerous command patterns that require approval
DANGEROUS_PATTERNS = [
    r'rm\s+-rf',              # Recursive delete
    r'rm\s+-r\s+/',           # Delete root paths
    r'dd\s+',                 # Disk operations
    r'>\s*/dev/',             # Device writes
    r'mkfs\.',                # Format filesystem
    r'git\s+push',            # Push to remote
    r'git\s+push\s+--force',  # Force push
    r'git\s+reset\s+--hard',  # Hard reset
    r'git\s+clean\s+-fd',     # Clean untracked
    r'drop\s+table',          # SQL drops
    r'drop\s+database',       # Database drops
    r'truncate\s+',           # Data deletion
    r'delete\s+from\s+\w+\s*;?$',  # Mass delete
    r':(){ :|:& };:',         # Fork bomb
    r'chmod\s+-R\s+777',      # Dangerous permissions
    r'curl.*\|\s*(?:ba)?sh',  # Pipe to shell
]

# Safe git operations that don't need approval
SAFE_GIT_OPS = ['status', 'diff', 'log', 'branch', 'show', 'ls-files', 'rev-parse']


class ExecutionBridge:
    """
    Parses agent responses and executes real actions.

    This is the core engine that transforms agent text responses into
    actual file operations, command execution, and git operations.
    """

    # Patterns for detecting file write intents
    FILE_WRITE_PATTERNS = [
        r'(?:let me |I\'ll |I will )?(?:create|write|save)(?: a)? (?:file|code)(?: to)? ["`]?([^\s"`\n]+)["`]?',
        r'(?:writing|creating|saving)(?: to)? ["`]?([^\s"`\n]+\.\w{1,10})["`]?',
        r'file:\s*["`]?([^\s"`\n]+\.\w{1,10})["`]?',
    ]

    # Pattern for code blocks with optional language
    CODE_BLOCK_PATTERN = r'```(\w*)\n(.*?)```'

    # Patterns for detecting command execution intents
    COMMAND_PATTERNS = [
        r'(?:running|execute|run|executing)[:\s]+[`"]?([^`"\n]+)[`"]?',
        r'\$\s*(.+)$',
        r'(?:command|cmd)[:\s]+[`"]?([^`"\n]+)[`"]?',
    ]

    # Patterns for terminal commands in backticks
    TERMINAL_COMMAND_PATTERNS = [
        r'`((?:npm|pip|python|python3|pytest|docker|git|node|yarn|cargo|go|make)\s+[^`]+)`',
    ]

    # Patterns for git operations
    GIT_PATTERNS = [
        r'git\s+(commit|push|pull|checkout|branch|merge|add|reset|stash|rebase|cherry-pick)\s*.*',
    ]

    def __init__(
        self,
        workspace_root: Path,
        approval_callback: Optional[Callable[[Action], bool]] = None,
        enabled: bool = True
    ):
        """
        Initialize the execution bridge.

        Args:
            workspace_root: Root directory for file operations
            approval_callback: Optional callback for dangerous operation approval
            enabled: Whether execution is enabled (False = simulation mode)
        """
        self.workspace = Path(workspace_root)
        self.approval_callback = approval_callback
        self.enabled = enabled
        self.audit_log: List[Dict] = []
        self.approval_queue: List[Action] = []
        self._pending_approvals: Dict[str, asyncio.Event] = {}

        # Ensure workspace exists
        self.workspace.mkdir(parents=True, exist_ok=True)

    def process_response(self, agent: str, response: str) -> ExecutionResult:
        """
        Parse response, execute actions, return results.

        Args:
            agent: Name of the agent that generated the response
            response: The text response from the agent

        Returns:
            ExecutionResult with all actions and their results
        """
        if not self.enabled:
            return ExecutionResult()

        actions = self.parse_actions(response)
        results = []

        for action in actions:
            # Check if approval is needed
            if self.requires_approval(action):
                if not self.get_approval(action):
                    results.append(ToolResult(
                        success=False,
                        error=f"Action blocked - no approval for: {action.type.value}",
                        action_type=action.type.value
                    ))
                    continue

            # Execute the action
            result = self.execute(action)
            results.append(result)

            # Log the action
            self.audit_log.append({
                "timestamp": time.time(),
                "agent": agent,
                "action_type": action.type.value,
                "content": action.content[:200],
                "file_path": action.file_path,
                "success": result.success,
                "error": result.error
            })

        return ExecutionResult(actions=actions, results=results)

    def parse_actions(self, text: str) -> List[Action]:
        """
        Parse all actionable intents from agent response text.

        Args:
            text: The agent's response text

        Returns:
            List of Action objects detected in the text
        """
        actions = []

        # Look for code blocks with file paths mentioned nearby
        code_blocks = re.findall(self.CODE_BLOCK_PATTERN, text, re.DOTALL)

        for i, (language, code) in enumerate(code_blocks):
            # Try to find a file path associated with this code block
            # Look in the text before the code block
            block_start = text.find(f"```{language}\n{code}```")
            if block_start > 0:
                preceding_text = text[max(0, block_start-200):block_start]

                # Look for file path patterns
                file_path = None
                for pattern in self.FILE_WRITE_PATTERNS:
                    match = re.search(pattern, preceding_text, re.IGNORECASE)
                    if match:
                        file_path = match.group(1)
                        break

                if file_path:
                    actions.append(Action(
                        type=ActionType.WRITE_FILE,
                        content=code.strip(),
                        file_path=file_path,
                        language=language or self._detect_language(file_path),
                        raw_match=f"```{language}\n{code}```"
                    ))

        # Look for command execution patterns
        for pattern in self.COMMAND_PATTERNS + self.TERMINAL_COMMAND_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
                command = match.group(1).strip()
                if command and len(command) > 2:
                    # Check if it's a git operation
                    git_match = re.match(r'git\s+(\w+)', command)
                    if git_match:
                        actions.append(Action(
                            type=ActionType.GIT_OPERATION,
                            content=command,
                            raw_match=match.group(0)
                        ))
                    else:
                        actions.append(Action(
                            type=ActionType.RUN_COMMAND,
                            content=command,
                            raw_match=match.group(0)
                        ))

        # Deduplicate actions
        seen = set()
        unique_actions = []
        for action in actions:
            key = (action.type, action.content[:50], action.file_path)
            if key not in seen:
                seen.add(key)
                unique_actions.append(action)

        return unique_actions

    def requires_approval(self, action: Action) -> bool:
        """Check if an action requires user approval."""
        if action.type == ActionType.RUN_COMMAND:
            return self.is_dangerous_command(action.content)
        elif action.type == ActionType.GIT_OPERATION:
            # Extract git subcommand
            match = re.match(r'git\s+(\w+)', action.content)
            if match:
                subcommand = match.group(1)
                return subcommand not in SAFE_GIT_OPS
        return False

    def is_dangerous_command(self, command: str) -> bool:
        """Check if a command matches dangerous patterns."""
        command_lower = command.lower()
        return any(re.search(p, command_lower, re.IGNORECASE) for p in DANGEROUS_PATTERNS)

    def get_approval(self, action: Action) -> bool:
        """
        Request approval for a dangerous operation.

        Args:
            action: The action requiring approval

        Returns:
            True if approved, False if denied
        """
        if self.approval_callback:
            return self.approval_callback(action)

        # Default behavior: queue for approval, don't execute
        self.approval_queue.append(action)
        return False

    def execute(self, action: Action) -> ToolResult:
        """
        Execute a single action.

        Args:
            action: The action to execute

        Returns:
            ToolResult with success/failure and output
        """
        try:
            if action.type == ActionType.WRITE_FILE:
                return self.write_file(action.file_path, action.content)
            elif action.type == ActionType.READ_FILE:
                return self.read_file(action.file_path)
            elif action.type == ActionType.RUN_COMMAND:
                return self.run_command(action.content)
            elif action.type == ActionType.GIT_OPERATION:
                return self.git_operation(action.content)
            else:
                return ToolResult(
                    success=False,
                    error=f"Unknown action type: {action.type}",
                    action_type=action.type.value
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                action_type=action.type.value
            )

    def write_file(self, path: str, content: str) -> ToolResult:
        """
        Write content to a file.

        Args:
            path: Relative or absolute path to the file
            content: Content to write

        Returns:
            ToolResult with success/failure
        """
        try:
            # Resolve path relative to workspace
            if not os.path.isabs(path):
                full_path = self.workspace / path
            else:
                full_path = Path(path)

            # Create parent directories
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            full_path.write_text(content)

            return ToolResult(
                success=True,
                output=f"Wrote {len(content)} bytes to {path}",
                action_type="write_file",
                path=str(full_path),
                content=content[:500]  # Preview
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to write file: {e}",
                action_type="write_file"
            )

    def read_file(self, path: str) -> ToolResult:
        """
        Read file content.

        Args:
            path: Path to the file

        Returns:
            ToolResult with file content
        """
        try:
            # Resolve path
            if not os.path.isabs(path):
                full_path = self.workspace / path
            else:
                full_path = Path(path)

            if not full_path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {path}",
                    action_type="read_file"
                )

            content = full_path.read_text()
            return ToolResult(
                success=True,
                output=content[:2000],  # Limit output size
                action_type="read_file",
                path=str(full_path)
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to read file: {e}",
                action_type="read_file"
            )

    def run_command(self, command: str, timeout: int = 60) -> ToolResult:
        """
        Execute a shell command with safety checks.

        Args:
            command: The command to execute
            timeout: Maximum execution time in seconds

        Returns:
            ToolResult with command output
        """
        try:
            # Safety check (should have been done before, but double-check)
            if self.is_dangerous_command(command):
                return ToolResult(
                    success=False,
                    error="Command blocked - dangerous operation",
                    action_type="run_command"
                )

            # Execute the command
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return ToolResult(
                success=result.returncode == 0,
                output=result.stdout[:2000] if result.stdout else "",
                error=result.stderr[:500] if result.returncode != 0 else None,
                action_type="run_command"
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=f"Command timed out after {timeout}s",
                action_type="run_command"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Command failed: {e}",
                action_type="run_command"
            )

    def git_operation(self, operation: str) -> ToolResult:
        """
        Execute a git command.

        Args:
            operation: Full git command (e.g., "git commit -m 'message'")

        Returns:
            ToolResult with git output
        """
        # Ensure it starts with 'git'
        if not operation.strip().startswith('git'):
            operation = f'git {operation}'

        return self.run_command(operation)

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        ext_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.html': 'html', '.css': 'css', '.json': 'json',
            '.md': 'markdown', '.sh': 'bash', '.ps1': 'powershell',
            '.cs': 'csharp', '.cpp': 'cpp', '.go': 'go',
            '.rs': 'rust', '.java': 'java', '.rb': 'ruby',
            '.yaml': 'yaml', '.yml': 'yaml', '.xml': 'xml',
            '.sql': 'sql', '.dockerfile': 'dockerfile',
        }
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, 'text')

    def get_audit_log(self, limit: int = 50) -> List[Dict]:
        """Get recent audit log entries."""
        return self.audit_log[-limit:]

    def get_pending_approvals(self) -> List[Action]:
        """Get actions waiting for approval."""
        return list(self.approval_queue)

    def approve_action(self, index: int) -> bool:
        """
        Approve a pending action by index.

        Args:
            index: Index in the approval queue

        Returns:
            True if approved and executed, False otherwise
        """
        if 0 <= index < len(self.approval_queue):
            action = self.approval_queue.pop(index)
            result = self.execute(action)
            return result.success
        return False

    def deny_action(self, index: int) -> bool:
        """
        Deny a pending action by index.

        Args:
            index: Index in the approval queue

        Returns:
            True if action was removed
        """
        if 0 <= index < len(self.approval_queue):
            self.approval_queue.pop(index)
            return True
        return False


def format_execution_results(exec_result: ExecutionResult) -> str:
    """
    Format execution results for appending to agent response.

    Args:
        exec_result: The execution result to format

    Returns:
        Formatted string for display
    """
    if not exec_result.any_executed:
        return ""

    lines = ["\n\n---\n**Execution Results:**\n"]

    for result in exec_result.results:
        status = "SUCCESS" if result.success else "FAILED"
        icon = "✅" if result.success else "❌"

        lines.append(f"- {icon} **{result.action_type}**: {status}")

        if result.output:
            preview = result.output[:100].replace('\n', ' ')
            lines.append(f"  Output: `{preview}...`")

        if result.error:
            lines.append(f"  Error: `{result.error}`")

    return "\n".join(lines)


# Singleton instance for convenience
_bridge_instance: Optional[ExecutionBridge] = None


def get_execution_bridge(workspace: Optional[Path] = None) -> ExecutionBridge:
    """Get or create the singleton execution bridge instance."""
    global _bridge_instance
    if _bridge_instance is None:
        workspace = workspace or Path.cwd()
        _bridge_instance = ExecutionBridge(workspace)
    return _bridge_instance


def set_execution_bridge(bridge: ExecutionBridge):
    """Set the global execution bridge instance."""
    global _bridge_instance
    _bridge_instance = bridge


if __name__ == "__main__":
    # Test the execution bridge
    print("Execution Bridge Test")
    print("=" * 50)

    # Create a test workspace
    test_workspace = Path("/tmp/agent-team-test")
    bridge = ExecutionBridge(test_workspace, enabled=True)

    # Test response parsing
    test_response = """
    I'll create a simple Python script for you.

    Creating file: `hello.py`

    ```python
    def main():
        print("Hello, World!")

    if __name__ == "__main__":
        main()
    ```

    Now let me run it:
    Running: `python hello.py`
    """

    print("\nTest Response:")
    print(test_response[:200] + "...")

    print("\nParsing actions...")
    actions = bridge.parse_actions(test_response)

    for action in actions:
        print(f"  - Type: {action.type.value}")
        print(f"    Content: {action.content[:50]}...")
        if action.file_path:
            print(f"    File: {action.file_path}")

    print("\nExecution Bridge ready for integration.")

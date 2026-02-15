#!/usr/bin/env python3
"""
Visual Session Controller - Controls visual activities for dashboard display.
============================================================================
Provides methods to trigger visual activities on the live dashboard:
- Browser navigation and screenshots
- Code typing animations
- Terminal command display
- Synchronized with agent speech

Usage:
    from visual_session import VisualActivityController, VisualDevTeamChat

    # Simple usage with chat integration
    chat = VisualDevTeamChat()
    chat.researcher.says("Let me search GitHub for MCP servers...")
    chat.researcher.searches("mcp server python")
    chat.visual.show_github_search("mcp server python")
    time.sleep(3)  # Let viewer see the results

    # Or standalone visual controller
    visual = VisualActivityController()
    await visual.show_github_search("query")
    await visual.show_code_typing("file.py", code_content)
"""

import asyncio
import json
import time
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
from urllib.parse import quote
from dataclasses import dataclass

# Import dialogue system
import sys
sys.path.insert(0, str(Path(__file__).parent))
from dialogue_v2 import DevTeamChat, AuthenticDialogue, DEVS

# Status file path - shared location accessible from both WSL and Windows
# WSL path maps to Windows D:\_CLAUDE-TOOLS\agent-team\agent_status.json
STATUS_FILE = Path("/mnt/d/_CLAUDE-TOOLS/agent-team/agent_status.json")
SCREENSHOT_FILE = Path("/tmp/browser_screenshot.png")


class VisualActivityController:
    """
    Controls visual activities for dashboard display.

    This class provides methods to trigger visual activities that appear
    on the live dashboard. Each method updates the status file which the
    dashboard polls for updates.
    """

    def __init__(self):
        self.playwright_available = self._check_playwright()
        self._current_browser_url = None

    def _check_playwright(self) -> bool:
        """Check if Playwright MCP is available."""
        try:
            # Check if playwright is installed
            import playwright
            return True
        except ImportError:
            return False

    def _set_activity(self, activity: dict):
        """Write activity to status file for dashboard to pick up."""
        try:
            # Read existing status
            existing = {}
            if STATUS_FILE.exists():
                with open(STATUS_FILE) as f:
                    existing = json.load(f)

            # Update activity
            existing["activity"] = activity
            existing["activity_timestamp"] = time.time()

            with open(STATUS_FILE, "w") as f:
                json.dump(existing, f)

        except Exception as e:
            print(f"Activity update error: {e}")

    def clear_activity(self):
        """Clear current activity from dashboard."""
        self._set_activity(None)

    # =========================================================================
    # Browser Activities
    # =========================================================================

    def show_github_search(self, query: str, delay: float = 0, open_real_browser: bool = True) -> str:
        """
        Show GitHub search on dashboard and optionally open in real browser.

        Args:
            query: Search query
            delay: Optional delay before showing (for speech sync)
            open_real_browser: If True, also opens the URL in the real Chrome browser

        Returns:
            The GitHub search URL
        """
        if delay > 0:
            time.sleep(delay)

        url = f"https://github.com/search?q={quote(query)}&type=repositories"
        self._set_activity({
            "type": "browser_navigate",
            "url": url,
            "title": f"GitHub: {query}"
        })
        self._current_browser_url = url

        # Capture screenshot for dashboard display
        self._capture_screenshot_async(url)

        # Open in real browser for OBS capture (optional)
        if open_real_browser:
            self._open_in_browser(url)

        return url

    def _open_in_browser(self, url: str):
        """Open URL in the real Chrome browser (for OBS capture)."""
        try:
            import subprocess
            # Use PowerShell to open Chrome on Windows
            subprocess.Popen(
                ['powershell.exe', '-Command', f'Start-Process "chrome.exe" -ArgumentList "{url}"'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"Could not open browser: {e}")

    def show_website(self, url: str, title: str = None, delay: float = 0, open_real_browser: bool = True):
        """
        Show website navigation on dashboard and optionally open in real browser.

        Args:
            url: URL to navigate to
            title: Optional title to display
            delay: Optional delay before showing
            open_real_browser: If True, also opens the URL in the real Chrome browser
        """
        if delay > 0:
            time.sleep(delay)

        self._set_activity({
            "type": "browser_navigate",
            "url": url,
            "title": title or url[:50]
        })
        self._current_browser_url = url

        # Capture screenshot for dashboard display
        self._capture_screenshot_async(url)

        # Open in real browser for OBS capture (optional)
        if open_real_browser:
            self._open_in_browser(url)

    def show_google_search(self, query: str, delay: float = 0) -> str:
        """Show Google search on dashboard."""
        if delay > 0:
            time.sleep(delay)

        url = f"https://www.google.com/search?q={quote(query)}"
        self._set_activity({
            "type": "browser_search",
            "query": query,
            "engine": "google"
        })
        return url

    def show_npm_package(self, package_name: str, delay: float = 0) -> str:
        """Show NPM package page on dashboard."""
        if delay > 0:
            time.sleep(delay)

        url = f"https://www.npmjs.com/package/{package_name}"
        self._set_activity({
            "type": "browser_navigate",
            "url": url,
            "title": f"NPM: {package_name}"
        })
        return url

    def show_pypi_package(self, package_name: str, delay: float = 0) -> str:
        """Show PyPI package page on dashboard."""
        if delay > 0:
            time.sleep(delay)

        url = f"https://pypi.org/project/{package_name}/"
        self._set_activity({
            "type": "browser_navigate",
            "url": url,
            "title": f"PyPI: {package_name}"
        })
        return url

    def _capture_screenshot_async(self, url: str):
        """Capture screenshot in background using Playwright."""
        import subprocess
        import threading

        def capture():
            try:
                # Run playwright capture in background
                script = f'''
import asyncio
from playwright.async_api import async_playwright

async def capture():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=['--no-sandbox'])
    page = await browser.new_page(viewport={{'width': 1280, 'height': 800}})
    await page.goto("{url}", timeout=15000, wait_until='domcontentloaded')
    await asyncio.sleep(1)
    await page.screenshot(path="/tmp/browser_screenshot.png")
    await browser.close()
    await pw.stop()

asyncio.run(capture())
'''
                subprocess.run(['python3', '-c', script], timeout=20, capture_output=True)
            except Exception as e:
                print(f"Screenshot capture failed: {e}")

        # Run in background thread
        thread = threading.Thread(target=capture, daemon=True)
        thread.start()

    # =========================================================================
    # Code Activities
    # =========================================================================

    def show_code_typing(self, file_path: str, content: str, language: str = None, delay: float = 0):
        """
        Trigger code typing animation on dashboard.

        The dashboard will display the code with a character-by-character
        typing animation with syntax highlighting.

        Args:
            file_path: Path to display (e.g., "server.py")
            content: Code content to type
            language: Programming language for highlighting
            delay: Optional delay before showing
        """
        if delay > 0:
            time.sleep(delay)

        self._set_activity({
            "type": "code_write",
            "file_path": file_path,
            "content": content,
            "language": language or self._detect_language(file_path)
        })

    def show_code_reading(self, file_path: str, content: str = None, highlight_lines: List[int] = None):
        """
        Show file reading activity on dashboard.

        Displays code without typing animation, optionally highlighting
        specific lines.

        Args:
            file_path: Path to display
            content: Optional content to show
            highlight_lines: Optional list of line numbers to highlight
        """
        self._set_activity({
            "type": "code_read",
            "file_path": file_path,
            "content": content or "",
            "highlight_lines": highlight_lines or []
        })

    def _detect_language(self, file_path: str) -> str:
        """Detect language from file extension."""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.md': 'markdown',
            '.cs': 'csharp',
            '.cpp': 'cpp',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.rb': 'ruby',
            '.sh': 'bash',
            '.ps1': 'powershell',
            '.sql': 'sql',
            '.yaml': 'yaml',
            '.yml': 'yaml',
        }
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, 'text')

    # =========================================================================
    # Terminal Activities
    # =========================================================================

    def show_terminal(self, command: str, output: str = None, delay: float = 0):
        """
        Show terminal command on dashboard.

        Args:
            command: Command being executed
            output: Optional command output
            delay: Optional delay before showing
        """
        if delay > 0:
            time.sleep(delay)

        self._set_activity({
            "type": "terminal_run",
            "command": command,
            "output": output or ""
        })

    def show_git_command(self, git_args: str, output: str = None):
        """Show git command execution."""
        self.show_terminal(f"git {git_args}", output)

    def show_npm_install(self, packages: str = None, output: str = None):
        """Show npm install command."""
        cmd = "npm install" + (f" {packages}" if packages else "")
        self.show_terminal(cmd, output)

    def show_pip_install(self, packages: str, output: str = None):
        """Show pip install command."""
        self.show_terminal(f"pip install {packages}", output)

    def show_test_run(self, framework: str = "pytest", output: str = None):
        """Show test execution."""
        self.show_terminal(framework, output)

    # =========================================================================
    # Thinking/Processing
    # =========================================================================

    def show_thinking(self, topic: str):
        """Show agent is processing/thinking about something."""
        self._set_activity({
            "type": "thinking",
            "topic": topic
        })

    # =========================================================================
    # File Activities
    # =========================================================================

    def show_file(self, file_path: str, title: str = None, delay: float = 0):
        """
        Open and display a file in the dashboard.

        Supports: PDF, Word (.docx), Excel (.xlsx), Images, Text files

        Args:
            file_path: Absolute path to the file
            title: Optional title to display
            delay: Optional delay before showing
        """
        if delay > 0:
            time.sleep(delay)

        # Convert WSL path to Windows path if needed
        if file_path.startswith('/mnt/'):
            # /mnt/d/... -> D:\...
            parts = file_path.split('/')
            drive = parts[2].upper()
            windows_path = f"{drive}:\\" + "\\".join(parts[3:])
        else:
            windows_path = file_path

        self._set_activity({
            "type": "file_open",
            "file_path": windows_path,
            "title": title or Path(file_path).name
        })

    def show_pdf(self, file_path: str, title: str = None):
        """Open a PDF file in the dashboard."""
        self.show_file(file_path, title or f"PDF: {Path(file_path).name}")

    def show_word_doc(self, file_path: str, title: str = None):
        """Open a Word document in the dashboard."""
        self.show_file(file_path, title or f"Word: {Path(file_path).name}")

    def show_excel(self, file_path: str, title: str = None):
        """Open an Excel spreadsheet in the dashboard."""
        self.show_file(file_path, title or f"Excel: {Path(file_path).name}")

    def show_image(self, file_path: str, title: str = None):
        """Open an image in the dashboard."""
        self.show_file(file_path, title or f"Image: {Path(file_path).name}")


class VisualDevTeamChat(DevTeamChat):
    """
    Extended DevTeamChat with integrated visual activity controller.

    Example:
        chat = VisualDevTeamChat()

        chat.researcher.says("Let me search for MCP server implementations...")
        chat.visual.show_github_search("mcp server python")
        time.sleep(3)

        chat.builder.says("I'll create the server now...")
        chat.visual.show_code_typing("server.py", server_code)
    """

    def __init__(self):
        super().__init__()
        self.visual = VisualActivityController()

    def sync_activity_with_speech(self, agent: str, message: str, activity_fn, *args, **kwargs):
        """
        Synchronize an activity with agent speech.

        The activity is triggered just before the agent speaks,
        so viewers see what the agent is doing while they talk about it.

        Args:
            agent: Agent name (planner, researcher, builder, critic, narrator)
            message: What the agent says
            activity_fn: Visual activity function to call
            *args, **kwargs: Arguments for the activity function
        """
        # Trigger activity first
        activity_fn(*args, **kwargs)

        # Brief pause for dashboard to update
        time.sleep(0.2)

        # Then have agent speak
        proxy = getattr(self, agent, None)
        if proxy:
            proxy.says(message)


def demo_visual_session():
    """Demo showing visual activities synchronized with agent speech."""
    print("=" * 60)
    print("  VISUAL SESSION DEMO")
    print("=" * 60)
    print("\nOpen http://localhost:8890/live in your browser to see the dashboard\n")

    chat = VisualDevTeamChat()

    # Introduction
    chat.narrator.explains(
        "Today we're building an MCP server. "
        "Watch as we research, plan, and implement."
    )

    # Research phase
    chat.researcher.says(
        "Let me search GitHub for existing MCP server implementations."
    )
    chat.visual.show_github_search("mcp server python implementation")
    time.sleep(4)

    chat.researcher.says(
        "Found several examples. The Model Context Protocol uses JSON-RPC."
    )

    # Planning
    chat.planner.thinks(
        "We need three components: transport layer, message handler, and tool registry."
    )
    chat.visual.show_thinking("Designing architecture...")
    time.sleep(2)

    # Building
    chat.builder.says(
        "I'll start with the server skeleton."
    )

    server_code = '''#!/usr/bin/env python3
"""Simple MCP Server Example"""

import asyncio
import json
from typing import Any, Dict

class MCPServer:
    """Model Context Protocol server."""

    def __init__(self, name: str):
        self.name = name
        self.tools = {}

    def register_tool(self, name: str, handler):
        """Register a tool handler."""
        self.tools[name] = handler

    async def handle_request(self, request: Dict) -> Dict:
        """Handle incoming JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})

        if method == "tools/list":
            return {"tools": list(self.tools.keys())}

        if method == "tools/call":
            tool_name = params.get("name")
            if tool_name in self.tools:
                result = await self.tools[tool_name](params)
                return {"result": result}

        return {"error": "Unknown method"}

# Usage
server = MCPServer("example-server")
'''

    chat.visual.show_code_typing("mcp_server.py", server_code, "python")
    time.sleep(10)  # Let the typing animation complete

    # Review
    chat.critic.thinks(
        "The structure is clean. Error handling could be more robust."
    )

    chat.builder.agrees(
        "Good point. I'll add proper exception handling in the next iteration."
    )

    # Terminal demo
    chat.builder.says(
        "Let me run the tests to verify the implementation."
    )
    chat.visual.show_terminal(
        "pytest test_mcp_server.py -v",
        "test_server_init PASSED\ntest_tool_registration PASSED\ntest_handle_request PASSED\n\n3 passed in 0.12s"
    )
    time.sleep(3)

    # Wrap up
    chat.narrator.explains(
        "The foundation is complete. The team demonstrated research, implementation, and testing."
    )

    print("\n" + "=" * 60)
    print("  DEMO COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo_visual_session()
    else:
        print("Visual Session Controller")
        print("-" * 40)
        print("Usage:")
        print("  python visual_session.py demo    # Run visual demo")
        print()
        print("Or import and use in your session scripts:")
        print("  from visual_session import VisualDevTeamChat")
        print("  chat = VisualDevTeamChat()")
        print("  chat.visual.show_github_search('query')")
        print("  chat.visual.show_code_typing('file.py', code)")

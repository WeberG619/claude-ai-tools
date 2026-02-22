#!/usr/bin/env python3
"""
Claude Memory MCP — Setup Wizard

Interactive installer that:
1. Checks Python version
2. Installs the package (editable or from PyPI)
3. Creates data directory & initializes database
4. Registers in Claude Code MCP settings
5. Optionally installs semantic search extras
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def banner(msg: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


def step(n: int, msg: str) -> None:
    print(f"\n[{n}/6] {msg}")
    print("-" * 50)


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"  {prompt}{suffix}: ").strip()
    return answer or default


def ask_yn(prompt: str, default: bool = True) -> bool:
    yn = "Y/n" if default else "y/N"
    answer = input(f"  {prompt} ({yn}): ").strip().lower()
    if not answer:
        return default
    return answer.startswith("y")


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def check_python() -> bool:
    """Step 1: Verify Python >= 3.10."""
    v = sys.version_info
    ok = v >= (3, 10)
    print(f"  Python {v.major}.{v.minor}.{v.micro} — {'OK' if ok else 'FAIL (need >= 3.10)'}")
    return ok


def install_package(project_dir: Path) -> bool:
    """Step 2: pip install the package."""
    editable = ask_yn("Install in editable/dev mode (pip install -e .)?", default=True)
    cmd = [sys.executable, "-m", "pip", "install"]
    if editable:
        cmd += ["-e", str(project_dir)]
    else:
        cmd += [str(project_dir)]

    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def init_data(project_dir: Path) -> Path:
    """Step 3: Create data directory and initialize database."""
    data_dir = project_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "memories.db"

    if db_path.exists():
        import sqlite3
        conn = sqlite3.connect(db_path)
        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        conn.close()
        print(f"  Existing database found: {db_path}")
        print(f"  Contains {count} memories — keeping it.")
    else:
        print(f"  Creating new database at: {db_path}")
        # Import and run init to create tables
        sys.path.insert(0, str(project_dir / "src"))
        from claude_memory.server import init_database
        init_database()
        print("  Database initialized with all tables.")

    return data_dir


def setup_user_config() -> str:
    """Step 4: Ensure ~/.claude/user.json exists."""
    config_path = Path.home() / ".claude" / "user.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        user_id = config.get("user_id", "")
        if user_id:
            print(f"  Found user config: user_id = {user_id}")
            return user_id

    print("  No user.json found. Let's create one.")
    user_id = ask("Enter your user ID (e.g. your name or email)", os.getenv("USER", "user"))
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = {}
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    config["user_id"] = user_id

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  Wrote {config_path}")
    return user_id


def register_mcp(project_dir: Path) -> bool:
    """Step 5: Register server in Claude Code MCP settings."""
    # Claude Code settings locations (in priority order)
    settings_paths = [
        Path.home() / ".config" / "claude" / "settings.json",
        Path.home() / ".claude" / "settings.local.json",
    ]

    settings_path = None
    settings = {}
    for p in settings_paths:
        if p.exists():
            settings_path = p
            with open(p) as f:
                settings = json.load(f)
            break

    if settings_path is None:
        settings_path = settings_paths[0]
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"  No settings file found. Will create: {settings_path}")

    servers = settings.setdefault("mcpServers", {})
    server_py = str(project_dir / "src" / "claude_memory" / "server.py")
    python_path = str(project_dir / "src")

    new_entry = {
        "type": "stdio",
        "command": "python3",
        "args": [server_py],
        "env": {
            "PYTHONPATH": python_path,
        },
    }

    if "claude-memory" in servers:
        existing = servers["claude-memory"]
        if existing.get("args") == new_entry["args"]:
            print(f"  Already registered correctly in {settings_path}")
            return True
        else:
            print(f"  Existing entry found (different path):")
            print(f"    Current: {existing.get('args', [])}")
            print(f"    New:     {new_entry['args']}")
            if not ask_yn("Update to new path?"):
                print("  Skipping MCP registration.")
                return True

    servers["claude-memory"] = new_entry

    # Show diff
    print(f"\n  Will write to: {settings_path}")
    print(f"  Server entry:")
    print(json.dumps({"claude-memory": new_entry}, indent=4))

    if ask_yn("Apply this change?"):
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)
        print(f"  Updated {settings_path}")
        return True
    else:
        print("  Skipped. You can manually add the MCP server config later.")
        return True


def install_semantic() -> None:
    """Step 6: Optionally install semantic search extras."""
    print("  Semantic search uses fastembed + numpy (~500MB download).")
    print("  Without it, memory search uses SQLite FTS5 (still very good).")
    if ask_yn("Install semantic search extras?", default=False):
        cmd = [sys.executable, "-m", "pip", "install", "claude-memory-mcp[semantic]"]
        print(f"  Running: {' '.join(cmd)}")
        subprocess.run(cmd)
    else:
        print("  Skipped. Install later with: pip install claude-memory-mcp[semantic]")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    banner("Claude Memory MCP — Setup Wizard")
    project_dir = Path(__file__).parent.resolve()
    print(f"  Project directory: {project_dir}")

    # Step 1: Python version
    step(1, "Checking Python version")
    if not check_python():
        print("\n  Please install Python 3.10+ and try again.")
        sys.exit(1)

    # Step 2: Install package
    step(2, "Installing package")
    if not install_package(project_dir):
        print("\n  Package installation failed. Check errors above.")
        sys.exit(1)

    # Step 3: Data directory & database
    step(3, "Initializing data directory")
    init_data(project_dir)

    # Step 4: User config
    step(4, "Setting up user identity")
    user_id = setup_user_config()

    # Step 5: Register MCP server
    step(5, "Registering MCP server in Claude Code")
    register_mcp(project_dir)

    # Step 6: Semantic search
    step(6, "Optional: Semantic search")
    install_semantic()

    # Done
    banner("Setup Complete!")
    print("  Quick start:")
    print("    1. Restart Claude Code (or run /mcp to reload servers)")
    print("    2. Try: memory_stats")
    print("    3. Try: memory_store(content='Hello from setup!', tags=['test'])")
    print()
    print(f"  Data:     {project_dir / 'data' / 'memories.db'}")
    print(f"  User:     {user_id}")
    print(f"  Docs:     {project_dir / 'README.md'}")
    print()


if __name__ == "__main__":
    main()

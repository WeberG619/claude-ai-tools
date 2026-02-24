"""
Tool Scoping Module — Per-Agent Tool Access Control
====================================================
Loads tool_profiles.yaml and provides runtime validation and prompt injection
for Claude Code sub-agents.

This module is the bridge between the YAML configuration and the alignment
injection pipeline. It is consumed by:
  - alignment.py (via compile_profile → _profile_to_prompt)
  - alignment_hook.py (directly for prompt injection)
  - permissions.py (for PermissionScope construction)

Usage:
    from tool_scoping import validate_tool_access, get_tool_restriction_prompt, load_agent_profile

    allowed = validate_tool_access("tech-scout", "Edit")   # → False
    allowed = validate_tool_access("tech-scout", "Read")   # → True
    prompt  = get_tool_restriction_prompt("tech-scout")    # → formatted restriction block

CLI:
    python tool_scoping.py profile --agent tech-scout
    python tool_scoping.py check --agent tech-scout --tool Edit
    python tool_scoping.py list
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ─── YAML LOADING ──────────────────────────────────────────────────────────────

_YAML_PATH = Path(__file__).parent / "tool_profiles.yaml"
_cache: Optional["ToolScopingConfig"] = None


def _load_yaml(path: Path) -> dict:
    """Load YAML using PyYAML if available, otherwise simple manual parse."""
    try:
        import yaml
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except ImportError:
        # Fallback: use json if YAML not available — won't work but keeps import clean
        raise RuntimeError(
            "PyYAML is required for tool_scoping.py. "
            "Install with: pip install pyyaml"
        )


# ─── DATA CLASSES ─────────────────────────────────────────────────────────────

@dataclass
class AgentProfile:
    """Resolved tool access profile for a single agent."""
    agent_name: str
    profile_name: str
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    bash_allowed: bool = False
    bash_safe_patterns: list[str] = field(default_factory=list)
    bash_denied_patterns: list[str] = field(default_factory=list)
    write_access: bool = False
    execute_access: bool = False
    network_access: bool = False
    allowed_directories: list[str] = field(default_factory=list)
    allowed_file_patterns: list[str] = field(default_factory=list)
    custom_constraints: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "profile_name": self.profile_name,
            "allowed_tools": self.allowed_tools,
            "denied_tools": self.denied_tools,
            "bash_allowed": self.bash_allowed,
            "write_access": self.write_access,
            "execute_access": self.execute_access,
            "network_access": self.network_access,
            "allowed_directories": self.allowed_directories,
            "allowed_file_patterns": self.allowed_file_patterns,
            "custom_constraints": self.custom_constraints,
            "notes": self.notes,
        }


@dataclass
class ToolScopingConfig:
    """Fully loaded and resolved tool scoping configuration."""
    profiles: dict[str, dict]           # raw profile definitions from YAML
    agents: dict[str, AgentProfile]     # resolved per-agent profiles

    def get_agent(self, agent_name: str) -> Optional[AgentProfile]:
        return self.agents.get(agent_name)


# ─── CONFIG LOADING + RESOLUTION ──────────────────────────────────────────────

def _resolve_profile(
    profile_name: str,
    profiles: dict[str, dict],
    agent_overrides: dict,
) -> AgentProfile:
    """
    Resolve a profile definition into a flat AgentProfile, applying inheritance
    (via `extends`) and agent-level overrides.
    """
    agent_name = agent_overrides.get("_agent_name", "unknown")

    # Walk the inheritance chain (max depth 5 to prevent cycles)
    chain: list[dict] = []
    current = profile_name
    for _ in range(5):
        pdef = profiles.get(current)
        if not pdef:
            break
        chain.insert(0, pdef)
        parent = pdef.get("extends")
        if not parent:
            break
        current = parent

    # Merge chain (parent → child → agent overrides).
    # For most fields: child overrides parent (latest wins).
    # For tools/additional_tools: accumulate from base, then add child additions.
    # For denied_tools: union across chain (any denial is final).
    merged: dict = {}
    accumulated_tools: list[str] = []
    accumulated_denied: list[str] = []
    for pdef in chain:
        # Update scalar/list fields (child overrides parent)
        merged.update({k: v for k, v in pdef.items()
                       if k not in ("extends", "description", "tools", "additional_tools",
                                    "denied_tools")})
        # Accumulate base tools from first profile that defines them
        if "tools" in pdef and not accumulated_tools:
            accumulated_tools = list(pdef["tools"])
        # Apply additional_tools from each profile in the chain
        for extra_tool in pdef.get("additional_tools", []):
            if extra_tool not in accumulated_tools:
                accumulated_tools.append(extra_tool)
        # Union denied_tools across chain
        for denied in pdef.get("denied_tools", []):
            if denied not in accumulated_denied:
                accumulated_denied.append(denied)

    # Remove explicitly denied tools from allowed list (deny wins)
    allowed_tools_raw = accumulated_tools if accumulated_tools else list(merged.get("tools", []))
    allowed_tools: list[str] = [t for t in allowed_tools_raw if t not in accumulated_denied]
    merged["_denied_tools"] = accumulated_denied

    # Apply agent-level additional_allowed
    extra = agent_overrides.get("additional_allowed", [])
    for t in extra:
        if t not in allowed_tools:
            allowed_tools.append(t)

    # Collect bash patterns
    bash_safe = list(merged.get("bash_safe_patterns", []))
    bash_denied = list(merged.get("bash_denied_patterns", []))

    # Directories
    allowed_dirs = list(merged.get("allowed_directories", []))
    agent_dirs = agent_overrides.get("allowed_directories", [])
    for d in agent_dirs:
        if d not in allowed_dirs:
            allowed_dirs.append(d)

    # File patterns
    file_patterns = list(merged.get("allowed_file_patterns", []))
    agent_patterns = agent_overrides.get("allowed_file_patterns", [])
    for p in agent_patterns:
        if p not in file_patterns:
            file_patterns.append(p)

    # Constraints
    constraints = list(merged.get("custom_constraints", []))
    agent_constraints = agent_overrides.get("custom_constraints", [])
    for c in agent_constraints:
        if c not in constraints:
            constraints.append(c)

    return AgentProfile(
        agent_name=agent_name,
        profile_name=profile_name,
        allowed_tools=allowed_tools,
        denied_tools=list(merged.get("_denied_tools", [])),
        bash_allowed=merged.get("bash_allowed", False),
        bash_safe_patterns=bash_safe,
        bash_denied_patterns=bash_denied,
        write_access=merged.get("write_access", False),
        execute_access=merged.get("execute_access", False),
        network_access=merged.get("network_access", False),
        allowed_directories=allowed_dirs,
        allowed_file_patterns=file_patterns,
        custom_constraints=constraints,
        notes=agent_overrides.get("notes", ""),
    )


def load_config(yaml_path: Optional[Path] = None) -> ToolScopingConfig:
    """Load and resolve the full tool scoping configuration from YAML."""
    global _cache
    path = yaml_path or _YAML_PATH
    if _cache is not None and yaml_path is None:
        return _cache

    raw = _load_yaml(path)
    profiles_raw: dict = raw.get("profiles", {})
    agents_raw: dict = raw.get("agents", {})

    resolved: dict[str, AgentProfile] = {}
    for agent_name, agent_cfg in agents_raw.items():
        if not isinstance(agent_cfg, dict):
            continue
        profile_name = agent_cfg.get("profile", "read-only")
        overrides = dict(agent_cfg)
        overrides["_agent_name"] = agent_name
        resolved[agent_name] = _resolve_profile(profile_name, profiles_raw, overrides)

    config = ToolScopingConfig(profiles=profiles_raw, agents=resolved)
    if yaml_path is None:
        _cache = config
    return config


def _get_restrictive_profile(agent_name: str) -> AgentProfile:
    """Return a maximally restrictive profile for unknown agents."""
    return AgentProfile(
        agent_name=agent_name,
        profile_name="read-only",
        allowed_tools=["Read", "Grep", "Glob"],
        denied_tools=["Edit", "Write", "Bash", "NotebookEdit", "Task"],
        bash_allowed=False,
        write_access=False,
        execute_access=False,
        network_access=False,
        custom_constraints=["Unknown agent — restricted to read-only operations"],
        notes="Fallback profile: agent not found in tool_profiles.yaml",
    )


def load_agent_profile(agent_name: str) -> AgentProfile:
    """
    Get the resolved AgentProfile for a named agent.
    Returns a restrictive read-only profile for unknown agents.
    """
    if not agent_name or not isinstance(agent_name, str):
        return _get_restrictive_profile("unknown")
    try:
        config = load_config()
        profile = config.get_agent(agent_name)
        if profile is None:
            return _get_restrictive_profile(agent_name)
        return profile
    except Exception:
        return _get_restrictive_profile(agent_name)


# ─── CORE API ─────────────────────────────────────────────────────────────────

def _tool_matches(tool_name: str, patterns: list[str]) -> bool:
    """Check if a tool name matches any pattern (supports glob wildcards)."""
    for pattern in patterns:
        if fnmatch.fnmatch(tool_name, pattern):
            return True
        if pattern.endswith("*") and tool_name.startswith(pattern[:-1]):
            return True
    return False


def validate_tool_access(agent_name: str, tool_name: str) -> bool:
    """
    Check whether an agent is permitted to use a specific tool.

    Returns True if allowed, False if denied.

    Rules (in priority order):
      1. If tool is in denied_tools → False
      2. If tool is in allowed_tools (including wildcard patterns) → True
      3. If allowed_tools is empty → True (no allowlist = permissive)
      4. Default → False
    """
    profile = load_agent_profile(agent_name)

    # Rule 1: explicit deny list takes priority
    if profile.denied_tools and _tool_matches(tool_name, profile.denied_tools):
        return False

    # Rule 2: explicit allow list
    if profile.allowed_tools and _tool_matches(tool_name, profile.allowed_tools):
        return True

    # Rule 3: empty allowlist = permissive
    if not profile.allowed_tools:
        return True

    # Rule 4: not in allowlist
    return False


def get_tool_restriction_prompt(agent_name: str) -> str:
    """
    Generate a concise prompt block describing tool restrictions for an agent.
    Suitable for injection into a sub-agent system prompt preamble.

    Returns an empty string if the agent has full/unrestricted access.
    """
    profile = load_agent_profile(agent_name)

    lines: list[str] = []
    lines.append("## Tool Access Scope")
    lines.append(f"Profile: {profile.profile_name}")

    if profile.allowed_tools:
        lines.append(f"Allowed tools: {', '.join(profile.allowed_tools)}")
    if profile.denied_tools:
        lines.append(f"DENIED tools: {', '.join(profile.denied_tools)}")

    access_parts = []
    if profile.write_access:
        access_parts.append("write")
    if profile.execute_access:
        access_parts.append("execute")
    if profile.network_access:
        access_parts.append("network")
    if access_parts:
        lines.append(f"Access: {', '.join(access_parts)}")
    else:
        lines.append("Access: read-only (no write, no execute)")

    if profile.bash_allowed and profile.bash_safe_patterns:
        lines.append(f"Bash safe patterns: {', '.join(profile.bash_safe_patterns[:6])}")
    if profile.bash_allowed and profile.bash_denied_patterns:
        lines.append(f"Bash DENIED patterns: {', '.join(profile.bash_denied_patterns)}")

    if profile.allowed_directories:
        lines.append(f"Allowed directories: {', '.join(profile.allowed_directories)}")
    if profile.allowed_file_patterns:
        lines.append(f"Allowed file types: {', '.join(profile.allowed_file_patterns)}")

    if profile.custom_constraints:
        lines.append("")
        lines.append("Constraints:")
        for c in profile.custom_constraints:
            lines.append(f"  - {c}")

    if profile.notes:
        lines.append(f"Notes: {profile.notes}")

    return "\n".join(lines)


def get_tool_restriction_prompt_short(agent_name: str) -> str:
    """
    One-liner tool restriction summary for tight context budgets.
    Returns a single line describing the profile and key restrictions.
    """
    profile = load_agent_profile(agent_name)

    parts = [f"[{profile.profile_name}]"]
    if not profile.write_access:
        parts.append("no-write")
    if not profile.execute_access:
        parts.append("no-exec")
    if not profile.bash_allowed:
        parts.append("no-bash")
    if profile.denied_tools:
        denied = ", ".join(profile.denied_tools[:4])
        parts.append(f"deny: {denied}")
    if profile.custom_constraints:
        parts.append(f"note: {profile.custom_constraints[0][:60]}")

    return "Tool scope: " + " | ".join(parts)


def list_all_profiles() -> list[dict]:
    """Return a list of all agent names and their profile summaries."""
    try:
        config = load_config()
        results = []
        for name, profile in sorted(config.agents.items()):
            results.append({
                "agent": name,
                "profile": profile.profile_name,
                "write": profile.write_access,
                "execute": profile.execute_access,
                "network": profile.network_access,
                "tools_count": len(profile.allowed_tools),
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]


# ─── PERMISSIONS.PY BRIDGE ────────────────────────────────────────────────────

def to_permission_scope(agent_name: str):
    """
    Convert an AgentProfile to a permissions.PermissionScope.
    Used by permissions.py to integrate with the alignment system.

    Returns a PermissionScope-compatible object.
    """
    try:
        from permissions import PermissionScope
        profile = load_agent_profile(agent_name)
        return PermissionScope(
            allowed_tools=profile.allowed_tools,
            denied_tools=profile.denied_tools,
            allowed_directories=profile.allowed_directories,
            denied_directories=[],
            write_access=profile.write_access,
            execute_access=profile.execute_access,
            network_access=profile.network_access,
            max_files_modified=0,
            allowed_file_patterns=profile.allowed_file_patterns,
            custom_constraints=profile.custom_constraints,
        )
    except ImportError:
        return None


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Tool Scoping — per-agent tool access validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    # profile subcommand
    p_profile = sub.add_parser("profile", help="Show resolved profile for an agent")
    p_profile.add_argument("--agent", required=True)
    p_profile.add_argument("--json", action="store_true", help="Output as JSON")

    # check subcommand
    p_check = sub.add_parser("check", help="Check if an agent can use a tool")
    p_check.add_argument("--agent", required=True)
    p_check.add_argument("--tool", required=True)

    # list subcommand
    sub.add_parser("list", help="List all agent profiles")

    # prompt subcommand
    p_prompt = sub.add_parser("prompt", help="Show restriction prompt for an agent")
    p_prompt.add_argument("--agent", required=True)
    p_prompt.add_argument("--short", action="store_true", help="One-liner format")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "profile":
        profile = load_agent_profile(args.agent)
        if args.json:
            print(json.dumps(profile.to_dict(), indent=2))
        else:
            print(f"Agent:    {profile.agent_name}")
            print(f"Profile:  {profile.profile_name}")
            print(f"Tools:    {', '.join(profile.allowed_tools)}")
            if profile.denied_tools:
                print(f"Denied:   {', '.join(profile.denied_tools)}")
            print(f"Write:    {profile.write_access}")
            print(f"Execute:  {profile.execute_access}")
            print(f"Network:  {profile.network_access}")
            if profile.allowed_directories:
                print(f"Dirs:     {', '.join(profile.allowed_directories)}")
            if profile.custom_constraints:
                print("Constraints:")
                for c in profile.custom_constraints:
                    print(f"  - {c}")
            if profile.notes:
                print(f"Notes:    {profile.notes}")

    elif args.command == "check":
        allowed = validate_tool_access(args.agent, args.tool)
        status = "ALLOWED" if allowed else "DENIED"
        print(f"{status}: {args.agent} / {args.tool}")
        if not allowed:
            exit(1)

    elif args.command == "list":
        profiles = list_all_profiles()
        if profiles and "error" in profiles[0]:
            print(f"Error: {profiles[0]['error']}")
            return
        print(f"{'Agent':<28} {'Profile':<22} {'W':>2} {'X':>2} {'N':>2} {'Tools':>5}")
        print("-" * 70)
        for p in profiles:
            w = "Y" if p["write"] else "."
            x = "Y" if p["execute"] else "."
            n = "Y" if p["network"] else "."
            print(f"{p['agent']:<28} {p['profile']:<22} {w:>2} {x:>2} {n:>2} {p['tools_count']:>5}")

    elif args.command == "prompt":
        if args.short:
            print(get_tool_restriction_prompt_short(args.agent))
        else:
            print(get_tool_restriction_prompt(args.agent))


if __name__ == "__main__":
    main()

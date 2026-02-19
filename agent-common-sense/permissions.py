"""
Permission Scoping v1.0
========================
Defines per-agent permission boundaries: which tools, directories, and
capabilities each agent type is allowed to use. Provides compile-time
prompt injection and post-execution compliance verification.

Different from AlignmentCore: alignment controls *what* an agent says
(quality, principles). Permissions control *what* an agent can *do*
(tools, file writes, bash execution).

Usage:
    from permissions import get_scope_for_agent, compile_permission_prompt, verify_output_compliance

    scope = get_scope_for_agent("tech-scout")
    prompt_block = compile_permission_prompt(scope, "tech-scout")
    # ... inject prompt_block into agent prompt ...

    result = verify_output_compliance(agent_output, scope)
    if not result.compliant:
        for v in result.violations:
            print(f"[{v['severity']}] {v['type']}: {v['detail']}")

CLI:
    python permissions.py scope --agent tech-scout
    python permissions.py verify --agent tech-scout --output "I edited the config file"
"""

import re
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# ─── DATA CLASSES ──────────────────────────────────────────────

@dataclass
class PermissionScope:
    """Defines what an agent is allowed to do."""
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    allowed_directories: list[str] = field(default_factory=list)
    denied_directories: list[str] = field(default_factory=list)
    write_access: bool = False
    execute_access: bool = False
    network_access: bool = False
    max_files_modified: int = 0
    allowed_file_patterns: list[str] = field(default_factory=list)
    custom_constraints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "allowed_tools": self.allowed_tools,
            "denied_tools": self.denied_tools,
            "allowed_directories": self.allowed_directories,
            "denied_directories": self.denied_directories,
            "write_access": self.write_access,
            "execute_access": self.execute_access,
            "network_access": self.network_access,
            "max_files_modified": self.max_files_modified,
            "allowed_file_patterns": self.allowed_file_patterns,
            "custom_constraints": self.custom_constraints,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PermissionScope":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ComplianceResult:
    """Result of checking output against permission scope."""
    compliant: bool = True
    violations: list[dict] = field(default_factory=list)
    checked_patterns: int = 0

    def to_dict(self) -> dict:
        return {
            "compliant": self.compliant,
            "violations": self.violations,
            "checked_patterns": self.checked_patterns,
        }


# ─── OUTPUT VERIFICATION PATTERNS ─────────────────────────────

# Tool usage evidence
TOOL_USAGE_PATTERNS = [
    re.compile(r"(?:used|called|invoked|ran|executed|using)\s+(\w+)\s+tool", re.IGNORECASE),
    re.compile(r"(\w+)\s+tool\s+(?:was|has been)\s+(?:used|called|invoked)", re.IGNORECASE),
    re.compile(r"(?:via|through|with)\s+(?:the\s+)?(\w+)\s+tool", re.IGNORECASE),
    re.compile(r"\b(Edit|Write|Bash|Read|Grep|Glob|NotebookEdit)\b(?:\s+tool)?"),
]

# Write evidence
WRITE_EVIDENCE_PATTERNS = [
    re.compile(r"(?:created|wrote|modified|deleted|updated|saved|overwrote)\s+(?:the\s+)?(?:file|directory|folder)", re.IGNORECASE),
    re.compile(r"(?:writing|creating|modifying|deleting|updating|saving)\s+(?:to\s+)?(?:the\s+)?(?:file|directory|folder)", re.IGNORECASE),
    re.compile(r"file\s+(?:has been|was)\s+(?:created|written|modified|deleted|updated|saved)", re.IGNORECASE),
]

# Execute evidence
EXECUTE_EVIDENCE_PATTERNS = [
    re.compile(r"(?:ran|executed|running|executed)\s+(?:the\s+)?(?:bash|command|script|subprocess)", re.IGNORECASE),
    re.compile(r"(?:bash|shell|terminal)\s+(?:command|execution|output)", re.IGNORECASE),
    re.compile(r"subprocess\.(?:run|call|Popen)", re.IGNORECASE),
]

# Path extraction
PATH_PATTERN = re.compile(r"(?:/[a-zA-Z0-9._-]+){2,}")


# ─── DEFAULT SCOPES ───────────────────────────────────────────

DEFAULT_SCOPES: dict[str, PermissionScope] = {
    "tech-scout": PermissionScope(
        allowed_tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch"],
        denied_tools=["Edit", "Write", "Bash", "NotebookEdit"],
        write_access=False,
        execute_access=False,
        network_access=True,
    ),
    "market-analyst": PermissionScope(
        allowed_tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch"],
        denied_tools=["Edit", "Write", "Bash", "NotebookEdit"],
        write_access=False,
        execute_access=False,
        network_access=True,
    ),
    "code-architect": PermissionScope(
        allowed_tools=["Read", "Grep", "Glob", "WebSearch"],
        denied_tools=["Edit", "Write", "Bash", "NotebookEdit"],
        write_access=False,
        execute_access=False,
        network_access=True,
    ),
    "floor-plan-processor": PermissionScope(
        allowed_tools=["Read", "Grep", "Glob", "Bash"],
        denied_tools=[],
        allowed_directories=["/mnt/d/Projects"],
        write_access=True,
        execute_access=True,
        network_access=False,
    ),
    "excel-reporter": PermissionScope(
        allowed_tools=["Read", "Grep", "Glob", "mcp__excel-mcp__*"],
        denied_tools=["Bash", "NotebookEdit"],
        write_access=True,
        execute_access=False,
        network_access=False,
    ),
    "revit-builder": PermissionScope(
        allowed_tools=["Read", "Grep", "Glob", "mcp__revit-mcp__*"],
        denied_tools=[],
        write_access=True,
        execute_access=True,
        network_access=False,
    ),
    "bim-validator": PermissionScope(
        allowed_tools=["Read", "Grep", "Glob", "mcp__revit-mcp__*"],
        denied_tools=["Edit", "Write", "Bash"],
        write_access=False,
        execute_access=False,
        network_access=False,
    ),
    "client-liaison": PermissionScope(
        allowed_tools=["Read", "Grep", "Glob", "WebSearch"],
        denied_tools=["Bash"],
        write_access=True,
        execute_access=False,
        network_access=True,
        custom_constraints=["Never send emails without user approval"],
    ),
    "invoice-tracker": PermissionScope(
        allowed_tools=["Read", "Grep", "Glob", "mcp__excel-mcp__*"],
        denied_tools=["Bash", "NotebookEdit"],
        write_access=True,
        execute_access=False,
        network_access=False,
    ),
    "proposal-writer": PermissionScope(
        allowed_tools=["Read", "Grep", "Glob", "Write", "WebSearch"],
        denied_tools=["Bash"],
        write_access=True,
        execute_access=False,
        network_access=True,
        allowed_file_patterns=["*.md", "*.txt", "*.docx"],
    ),
    "python-engineer": PermissionScope(
        allowed_tools=["Read", "Grep", "Glob", "Write", "Edit", "Bash"],
        denied_tools=[],
        allowed_directories=["/mnt/d/_CLAUDE-TOOLS", "/mnt/d/Projects"],
        write_access=True,
        execute_access=True,
        network_access=False,
    ),
}

# Restrictive default for unknown agents
_RESTRICTIVE_DEFAULT = PermissionScope(
    allowed_tools=["Read", "Grep", "Glob"],
    denied_tools=["Edit", "Write", "Bash", "NotebookEdit"],
    write_access=False,
    execute_access=False,
    network_access=False,
    custom_constraints=["Unknown agent type — restricted to read-only operations"],
)


# ─── FUNCTIONS ─────────────────────────────────────────────────

def get_scope_for_agent(agent_name: str) -> PermissionScope:
    """Get the permission scope for an agent. Unknown agents get restrictive defaults."""
    if not agent_name or not isinstance(agent_name, str):
        return PermissionScope(
            allowed_tools=["Read", "Grep", "Glob"],
            denied_tools=["Edit", "Write", "Bash", "NotebookEdit"],
            write_access=False,
            execute_access=False,
            network_access=False,
            custom_constraints=["Invalid agent name — restricted to read-only operations"],
        )
    return DEFAULT_SCOPES.get(agent_name, _RESTRICTIVE_DEFAULT)


def compile_permission_prompt(scope: PermissionScope, agent_name: str = "") -> str:
    """Generate a prompt text block describing the agent's permission boundaries."""
    lines = []
    lines.append("# Permission Scope")
    if agent_name:
        lines.append(f"Agent: {agent_name}")
    lines.append("")

    # Tools
    if scope.allowed_tools:
        lines.append(f"ALLOWED tools: {', '.join(scope.allowed_tools)}")
    if scope.denied_tools:
        lines.append(f"DENIED tools: {', '.join(scope.denied_tools)}")

    # Access
    lines.append(f"Write access: {'Yes' if scope.write_access else 'DENIED'}")
    lines.append(f"Execute access: {'Yes' if scope.execute_access else 'DENIED'}")
    lines.append(f"Network access: {'Yes' if scope.network_access else 'DENIED'}")

    # Directories
    if scope.allowed_directories:
        lines.append(f"Allowed directories: {', '.join(scope.allowed_directories)}")
    if scope.denied_directories:
        lines.append(f"Denied directories: {', '.join(scope.denied_directories)}")

    # File patterns
    if scope.allowed_file_patterns:
        lines.append(f"Allowed file types: {', '.join(scope.allowed_file_patterns)}")

    # Max files
    if scope.max_files_modified > 0:
        lines.append(f"Max files to modify: {scope.max_files_modified}")

    # Custom
    if scope.custom_constraints:
        lines.append("")
        lines.append("Constraints:")
        for c in scope.custom_constraints:
            lines.append(f"- {c}")

    return "\n".join(lines)


def _tool_matches(tool_name: str, patterns: list[str]) -> bool:
    """Check if a tool name matches any pattern (supports trailing wildcard)."""
    for pattern in patterns:
        if pattern.endswith("*"):
            if tool_name.startswith(pattern[:-1]):
                return True
        elif tool_name == pattern:
            return True
    return False


def verify_output_compliance(output: str, scope: PermissionScope) -> ComplianceResult:
    """Verify an agent's output doesn't evidence actions outside its permission scope."""
    result = ComplianceResult()

    if not output or not isinstance(output, str):
        return result

    output_trimmed = output[:10000]
    patterns_checked = 0

    # 1. Check for denied tool usage
    for pattern in TOOL_USAGE_PATTERNS:
        patterns_checked += 1
        for match in pattern.finditer(output_trimmed):
            tool_name = match.group(1) if match.lastindex else match.group(0).strip()
            if scope.denied_tools and _tool_matches(tool_name, scope.denied_tools):
                result.violations.append({
                    "type": "denied_tool_usage",
                    "detail": f"Evidence of denied tool '{tool_name}' usage",
                    "severity": "high",
                })
            elif scope.allowed_tools and not _tool_matches(tool_name, scope.allowed_tools):
                # Tool not in allowed list (and allowed list is non-empty)
                # Only flag specific tool names we recognize
                known_tools = {"Edit", "Write", "Bash", "Read", "Grep", "Glob", "NotebookEdit",
                               "WebSearch", "WebFetch", "Task"}
                if tool_name in known_tools:
                    result.violations.append({
                        "type": "unlisted_tool_usage",
                        "detail": f"Tool '{tool_name}' not in allowed list",
                        "severity": "medium",
                    })

    # 2. Check for write evidence when write_access is False
    if not scope.write_access:
        for pattern in WRITE_EVIDENCE_PATTERNS:
            patterns_checked += 1
            if pattern.search(output_trimmed):
                result.violations.append({
                    "type": "unauthorized_write",
                    "detail": "Evidence of file write/modify operation without write access",
                    "severity": "high",
                })
                break

    # 3. Check for execute evidence when execute_access is False
    if not scope.execute_access:
        for pattern in EXECUTE_EVIDENCE_PATTERNS:
            patterns_checked += 1
            if pattern.search(output_trimmed):
                result.violations.append({
                    "type": "unauthorized_execute",
                    "detail": "Evidence of command execution without execute access",
                    "severity": "high",
                })
                break

    # 4. Check paths against allowed/denied directories
    if scope.allowed_directories or scope.denied_directories:
        paths_found = PATH_PATTERN.findall(output_trimmed)
        for path in paths_found:
            patterns_checked += 1
            # Check denied directories
            if scope.denied_directories:
                for denied in scope.denied_directories:
                    if path.startswith(denied):
                        result.violations.append({
                            "type": "denied_directory_access",
                            "detail": f"Path '{path}' is in denied directory '{denied}'",
                            "severity": "high",
                        })
                        break

            # Check allowed directories (only if allowed list is non-empty)
            if scope.allowed_directories:
                in_allowed = any(path.startswith(d) for d in scope.allowed_directories)
                if not in_allowed:
                    # Don't flag common system paths or the agent's own tool paths
                    skip_prefixes = ["/mnt/d/_CLAUDE-TOOLS/agent-common-sense",
                                     "/home", "/tmp", "/usr", "/etc"]
                    if not any(path.startswith(sp) for sp in skip_prefixes):
                        result.violations.append({
                            "type": "directory_outside_scope",
                            "detail": f"Path '{path}' not in allowed directories",
                            "severity": "medium",
                        })

    result.checked_patterns = patterns_checked
    result.compliant = len(result.violations) == 0
    return result


def merge_scopes(base: PermissionScope, override: PermissionScope) -> PermissionScope:
    """Merge two scopes using intersection (tighter = safer).
    The result is the most restrictive combination of both scopes."""

    # Tool intersection: only tools allowed by BOTH
    if base.allowed_tools and override.allowed_tools:
        # Expand wildcards for intersection
        merged_tools = []
        for tool in base.allowed_tools:
            if _tool_matches(tool, override.allowed_tools):
                merged_tools.append(tool)
        for tool in override.allowed_tools:
            if _tool_matches(tool, base.allowed_tools) and tool not in merged_tools:
                merged_tools.append(tool)
        allowed_tools = merged_tools
    elif base.allowed_tools:
        allowed_tools = list(base.allowed_tools)
    elif override.allowed_tools:
        allowed_tools = list(override.allowed_tools)
    else:
        allowed_tools = []

    # Denied tools: union (block anything either blocks)
    denied_tools = list(set(base.denied_tools) | set(override.denied_tools))

    # Directory intersection
    if base.allowed_directories and override.allowed_directories:
        allowed_dirs = [d for d in base.allowed_directories
                        if any(d.startswith(o) or o.startswith(d)
                               for o in override.allowed_directories)]
        if not allowed_dirs:
            # No overlap — use the more restrictive set
            allowed_dirs = list(override.allowed_directories)
    elif base.allowed_directories:
        allowed_dirs = list(base.allowed_directories)
    elif override.allowed_directories:
        allowed_dirs = list(override.allowed_directories)
    else:
        allowed_dirs = []

    # Denied directories: union
    denied_dirs = list(set(base.denied_directories) | set(override.denied_directories))

    # Boolean flags: denied if EITHER denies
    write = base.write_access and override.write_access
    execute = base.execute_access and override.execute_access
    network = base.network_access and override.network_access

    # Max files: minimum (more restrictive)
    if base.max_files_modified > 0 and override.max_files_modified > 0:
        max_files = min(base.max_files_modified, override.max_files_modified)
    elif base.max_files_modified > 0:
        max_files = base.max_files_modified
    elif override.max_files_modified > 0:
        max_files = override.max_files_modified
    else:
        max_files = 0

    # File patterns: intersection
    if base.allowed_file_patterns and override.allowed_file_patterns:
        file_patterns = [p for p in base.allowed_file_patterns
                         if p in override.allowed_file_patterns]
    elif base.allowed_file_patterns:
        file_patterns = list(base.allowed_file_patterns)
    elif override.allowed_file_patterns:
        file_patterns = list(override.allowed_file_patterns)
    else:
        file_patterns = []

    # Custom constraints: union
    custom = list(set(base.custom_constraints) | set(override.custom_constraints))

    return PermissionScope(
        allowed_tools=allowed_tools,
        denied_tools=denied_tools,
        allowed_directories=allowed_dirs,
        denied_directories=denied_dirs,
        write_access=write,
        execute_access=execute,
        network_access=network,
        max_files_modified=max_files,
        allowed_file_patterns=file_patterns,
        custom_constraints=custom,
    )


def log_violation(agent_name: str, violation: dict, db_path: Optional[str] = None):
    """Log a permission violation to the alignment_drift_log table."""
    if not db_path:
        candidates = [
            Path("/mnt/d/_CLAUDE-TOOLS/claude-memory-server/data/memories.db"),
            Path.home() / ".claude-memory" / "memories.db",
        ]
        for p in candidates:
            if p.exists():
                db_path = str(p)
                break

    if not db_path:
        return

    try:
        conn = sqlite3.connect(db_path)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            INSERT INTO alignment_drift_log
            (agent_name, violation_type, description, severity, detected_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            agent_name,
            "permission_scope_violation",
            f"{violation.get('type', 'unknown')}: {violation.get('detail', '')}",
            violation.get("severity", "medium"),
            now,
        ))
        conn.commit()
        conn.close()
    except Exception:
        pass


# ─── CLI ───────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Permission Scoping v1.0")
    sub = parser.add_subparsers(dest="command")

    p_scope = sub.add_parser("scope", help="Show scope for an agent")
    p_scope.add_argument("--agent", required=True, help="Agent name")

    p_verify = sub.add_parser("verify", help="Verify output compliance")
    p_verify.add_argument("--agent", required=True, help="Agent name")
    p_verify.add_argument("--output", required=True, help="Agent output text")

    p_list = sub.add_parser("list", help="List all agent scopes")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "scope":
        scope = get_scope_for_agent(args.agent)
        prompt = compile_permission_prompt(scope, args.agent)
        print(prompt)
        print()
        print(f"Scope data: {json.dumps(scope.to_dict(), indent=2)}")

    elif args.command == "verify":
        scope = get_scope_for_agent(args.agent)
        text = args.output
        if Path(text).exists():
            text = Path(text).read_text()

        result = verify_output_compliance(text, scope)
        if result.compliant:
            print(f"COMPLIANT: No violations detected ({result.checked_patterns} patterns checked)")
        else:
            print(f"VIOLATIONS ({len(result.violations)}):")
            for v in result.violations:
                print(f"  [{v['severity']}] {v['type']}: {v['detail']}")

    elif args.command == "list":
        print("Agent Permission Scopes:")
        print()
        for name, scope in sorted(DEFAULT_SCOPES.items()):
            tools = ", ".join(scope.allowed_tools[:4])
            if len(scope.allowed_tools) > 4:
                tools += f" (+{len(scope.allowed_tools)-4})"
            w = "W" if scope.write_access else "-"
            x = "X" if scope.execute_access else "-"
            n = "N" if scope.network_access else "-"
            print(f"  {name:25s} [{w}{x}{n}] tools: {tools}")


if __name__ == "__main__":
    main()

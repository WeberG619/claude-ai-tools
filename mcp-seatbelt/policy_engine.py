#!/usr/bin/env python3
"""
Policy Engine - Loads and matches security policies from YAML files.

Policies define risk levels and validation rules for MCP tools.
"""

import fnmatch
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class PolicyRule:
    """A single validation rule within a policy."""
    type: str  # recipient_whitelist, block_patterns, path_validation, etc.
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Policy:
    """Security policy for a tool or tool pattern."""
    pattern: str
    risk: int = 5
    action: str = "log_only"  # block, allow, log_only, warn
    require_approval: bool = False
    rules: List[PolicyRule] = field(default_factory=list)
    description: str = ""


class PolicyEngine:
    """Loads and matches security policies against tool names."""

    DEFAULT_POLICY_DIR = Path(__file__).parent / "policies"

    def __init__(self, policy_dirs: Optional[List[Path]] = None):
        """
        Initialize the policy engine.

        Args:
            policy_dirs: List of directories to load policies from.
                        Defaults to ./policies/
        """
        self.policy_dirs = policy_dirs or [self.DEFAULT_POLICY_DIR]
        self.policies: Dict[str, Policy] = {}
        self.default_policy: Optional[Policy] = None
        self._load_policies()

    def _load_policies(self) -> None:
        """Load all policy files from configured directories."""
        for policy_dir in self.policy_dirs:
            if not policy_dir.exists():
                continue

            # Load in order: default.yaml first, then others alphabetically
            yaml_files = sorted(policy_dir.glob("*.yaml"))
            default_file = policy_dir / "default.yaml"

            if default_file in yaml_files:
                yaml_files.remove(default_file)
                yaml_files.insert(0, default_file)

            for yaml_file in yaml_files:
                self._load_policy_file(yaml_file)

    def _load_policy_file(self, filepath: Path) -> None:
        """Load policies from a single YAML file."""
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to load policy file {filepath}: {e}")
            return

        # Process environment variable substitutions
        data = self._substitute_env_vars(data)

        # Load tool-specific policies
        tools = data.get('tools', {})
        for pattern, config in tools.items():
            if pattern == 'default':
                self.default_policy = self._create_policy(pattern, config)
            else:
                self.policies[pattern] = self._create_policy(pattern, config)

        # Load global settings
        if 'contacts_whitelist' in data:
            os.environ['SEATBELT_CONTACTS_WHITELIST'] = ','.join(data['contacts_whitelist'])

    def _substitute_env_vars(self, data: Any) -> Any:
        """Recursively substitute ${VAR} patterns with environment variables."""
        if isinstance(data, str):
            # Match ${VAR} or ${VAR:-default}
            pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'

            def replacer(match):
                var_name = match.group(1)
                default = match.group(2) or ''
                return os.environ.get(var_name, default)

            return re.sub(pattern, replacer, data)

        elif isinstance(data, dict):
            return {k: self._substitute_env_vars(v) for k, v in data.items()}

        elif isinstance(data, list):
            return [self._substitute_env_vars(item) for item in data]

        return data

    def _create_policy(self, pattern: str, config: Dict[str, Any]) -> Policy:
        """Create a Policy object from config dict."""
        rules = []
        for rule_config in config.get('rules', []):
            rule_type = rule_config.pop('type', 'unknown')
            rules.append(PolicyRule(type=rule_type, config=rule_config))

        return Policy(
            pattern=pattern,
            risk=config.get('risk', 5),
            action=config.get('action', 'log_only'),
            require_approval=config.get('require_approval', False),
            rules=rules,
            description=config.get('description', '')
        )

    def get_policy(self, tool_name: str) -> Policy:
        """
        Get the most specific matching policy for a tool.

        Matching order:
        1. Exact match
        2. Wildcard patterns (most specific first)
        3. Default policy

        Args:
            tool_name: Full tool name (e.g., mcp__whatsapp__send_message)

        Returns:
            Matching Policy, or default policy if no match
        """
        # Try exact match first
        if tool_name in self.policies:
            return self.policies[tool_name]

        # Try wildcard patterns, sorted by specificity (longer patterns first)
        matching = []
        for pattern, policy in self.policies.items():
            if '*' in pattern and fnmatch.fnmatch(tool_name, pattern):
                matching.append((len(pattern.replace('*', '')), policy))

        if matching:
            # Return most specific match (longest non-wildcard portion)
            matching.sort(key=lambda x: x[0], reverse=True)
            return matching[0][1]

        # Fall back to default
        if self.default_policy:
            return self.default_policy

        # Ultimate fallback: permissive default
        return Policy(
            pattern="*",
            risk=5,
            action="log_only",
            description="Default permissive policy"
        )

    def list_policies(self) -> List[Policy]:
        """Return all loaded policies."""
        policies = list(self.policies.values())
        if self.default_policy:
            policies.append(self.default_policy)
        return policies

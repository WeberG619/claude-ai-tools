#!/usr/bin/env python3
"""
Validator - Implements security validation rules for MCP tool calls.

Each rule type checks specific aspects of tool parameters.
"""

import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from policy_engine import Policy, PolicyRule


@dataclass
class ValidationResult:
    """Result of validating a tool call against policies."""
    action: str = "allow"  # allow, block, warn, log_only
    message: str = ""
    policy_matched: str = ""
    rules_checked: List[str] = field(default_factory=list)
    rules_failed: List[str] = field(default_factory=list)
    risk_score: int = 0
    redacted_params: Dict[str, Any] = field(default_factory=dict)


class Validator:
    """Validates MCP tool calls against security policies."""

    # Fields that should be redacted in logs
    SENSITIVE_FIELDS = {
        'password', 'token', 'secret', 'key', 'credential', 'auth',
        'ssn', 'social_security', 'credit_card', 'bank_account'
    }

    # Dangerous patterns that should never appear in any parameter
    UNIVERSAL_BLOCK_PATTERNS = [
        r'rm\s+-rf\s+/',  # Delete root
        r':()\{\s*:\|:\s*&\s*\};:',  # Fork bomb
        r'> /dev/sd[a-z]',  # Write to raw disk
        r'dd\s+if=.*of=/dev/',  # DD to device
        # Gap fix: Sensitive paths
        r'[/\\]\.ssh[/\\]',  # SSH keys
        r'[/\\]\.gnupg[/\\]',  # GPG keys
        r'[/\\]\.aws[/\\]',  # AWS credentials
        r'[/\\]\.kube[/\\]',  # Kubernetes config
        r'id_rsa|id_ed25519|id_ecdsa',  # Private keys by name
        r'\.pem\b',  # .pem key files (word boundary handles quotes)
        r'private.*\.key\b',  # private .key files
        r'credentials\.json|secrets\.json',  # Common credential files
    ]

    def __init__(self):
        """Initialize the validator with rule handlers."""
        self.rule_handlers: Dict[str, Callable] = {
            'recipient_whitelist': self._check_recipient_whitelist,
            'block_patterns': self._check_block_patterns,
            'path_validation': self._check_path_validation,
            'command_sanitize': self._check_command_sanitize,
            'require_fields': self._check_required_fields,
            'max_length': self._check_max_length,
            'allowed_values': self._check_allowed_values,
        }

    def validate(self, tool_name: str, tool_input: Dict[str, Any],
                 policy: Policy) -> ValidationResult:
        """
        Validate a tool call against its policy.

        Args:
            tool_name: The MCP tool name
            tool_input: Parameters being passed to the tool
            policy: The applicable security policy

        Returns:
            ValidationResult with action and details
        """
        result = ValidationResult(
            action=policy.action,
            policy_matched=policy.pattern,
            redacted_params=self._redact_sensitive(tool_input)
        )

        # Check universal block patterns first
        if self._check_universal_blocks(tool_input, result):
            result.action = "block"
            return result

        # If policy says always block, no need to check rules
        if policy.action == "block":
            result.message = policy.description or "Blocked by policy"
            return result

        # If require_approval and we can't prompt, block
        if policy.require_approval:
            result.action = "block"
            result.message = "Requires approval (interactive mode not available)"
            return result

        # Run each rule in the policy
        for rule in policy.rules:
            result.rules_checked.append(rule.type)

            handler = self.rule_handlers.get(rule.type)
            if not handler:
                continue

            passed, message = handler(tool_name, tool_input, rule.config)

            if not passed:
                result.rules_failed.append(rule.type)
                result.action = "block"
                result.message = message
                return result

        return result

    def _check_universal_blocks(self, tool_input: Dict[str, Any],
                                 result: ValidationResult) -> bool:
        """Check for universally dangerous patterns."""
        input_str = str(tool_input)

        for pattern in self.UNIVERSAL_BLOCK_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                result.message = f"Blocked: Dangerous pattern detected"
                result.rules_failed.append("universal_block")
                return True

        return False

    def _redact_sensitive(self, params: Dict[str, Any],
                          max_length: int = 50) -> Dict[str, Any]:
        """Redact sensitive fields and truncate long values for logging."""
        redacted = {}

        for key, value in params.items():
            # Check if field name suggests sensitive data
            key_lower = key.lower()
            is_sensitive = any(s in key_lower for s in self.SENSITIVE_FIELDS)

            if is_sensitive:
                redacted[key] = "REDACTED"
            elif isinstance(value, str) and len(value) > max_length:
                redacted[key] = value[:max_length] + "..."
            elif isinstance(value, dict):
                redacted[key] = self._redact_sensitive(value, max_length)
            elif isinstance(value, list) and len(value) > 5:
                redacted[key] = f"[{len(value)} items]"
            else:
                redacted[key] = value

        return redacted

    # === Rule Handlers ===

    def _check_recipient_whitelist(self, tool_name: str,
                                    tool_input: Dict[str, Any],
                                    config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Check if recipient is in whitelist.

        Config:
            allowed: List of allowed recipients or patterns
            fields: List of parameter names to check (default: ['to', 'recipient', 'phone'])
        """
        allowed = config.get('allowed', [])
        fields = config.get('fields', ['to', 'recipient', 'phone', 'contact'])

        # Also check environment variable whitelist
        env_whitelist = os.environ.get('SEATBELT_CONTACTS_WHITELIST', '')
        if env_whitelist:
            allowed.extend(env_whitelist.split(','))

        # Find recipient value
        recipient = None
        for field in fields:
            if field in tool_input:
                recipient = str(tool_input[field])
                break

        if not recipient:
            return True, ""  # No recipient field found, allow

        # Check against whitelist
        for pattern in allowed:
            pattern = pattern.strip()
            if not pattern:
                continue

            # Exact match
            if recipient == pattern:
                return True, ""

            # Domain match (e.g., @bdarchitect.net)
            if pattern.startswith('@') and recipient.endswith(pattern):
                return True, ""

            # Wildcard match
            if '*' in pattern:
                regex = pattern.replace('*', '.*')
                if re.match(regex, recipient, re.IGNORECASE):
                    return True, ""

        return False, f"Recipient '{recipient}' not in whitelist"

    def _check_block_patterns(self, tool_name: str,
                               tool_input: Dict[str, Any],
                               config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Block if any parameter contains forbidden patterns.

        Config:
            patterns: List of regex patterns to block
            fields: Specific fields to check (default: all)
        """
        patterns = config.get('patterns', [])
        fields = config.get('fields', None)  # None = check all

        values_to_check = []
        if fields:
            for field in fields:
                if field in tool_input:
                    values_to_check.append(str(tool_input[field]))
        else:
            values_to_check = [str(v) for v in tool_input.values()]

        for value in values_to_check:
            for pattern in patterns:
                if re.search(pattern, value, re.IGNORECASE):
                    return False, f"Blocked pattern detected: {pattern}"

        return True, ""

    def _check_path_validation(self, tool_name: str,
                                tool_input: Dict[str, Any],
                                config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Validate file paths are within allowed roots.

        Config:
            allowed_roots: List of allowed path prefixes
            fields: Fields containing paths (default: ['path', 'file', 'filepath'])
            block_traversal: Block ../ patterns (default: True)
        """
        allowed_roots = config.get('allowed_roots', [])
        fields = config.get('fields', ['path', 'file', 'filepath', 'file_path'])
        block_traversal = config.get('block_traversal', True)

        for field in fields:
            if field not in tool_input:
                continue

            path = str(tool_input[field])

            # Check for path traversal
            if block_traversal and '..' in path:
                return False, f"Path traversal detected in {field}"

            # Check against allowed roots
            if allowed_roots:
                path_normalized = path.replace('\\', '/').lower()
                allowed = False

                for root in allowed_roots:
                    root_normalized = root.replace('\\', '/').lower()
                    if path_normalized.startswith(root_normalized):
                        allowed = True
                        break

                if not allowed:
                    return False, f"Path '{path}' outside allowed roots"

        return True, ""

    def _check_command_sanitize(self, tool_name: str,
                                 tool_input: Dict[str, Any],
                                 config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Sanitize shell commands to prevent injection.

        Config:
            block_chars: Characters that indicate injection attempt
            fields: Fields containing commands
        """
        block_chars = config.get('block_chars', [';', '|', '&', '`', '$', '$(', '${'])
        fields = config.get('fields', ['command', 'cmd', 'script'])

        for field in fields:
            if field not in tool_input:
                continue

            value = str(tool_input[field])

            for char in block_chars:
                if char in value:
                    return False, f"Potential command injection: '{char}' in {field}"

        return True, ""

    def _check_required_fields(self, tool_name: str,
                                tool_input: Dict[str, Any],
                                config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Ensure required fields are present.

        Config:
            fields: List of required field names
        """
        required = config.get('fields', [])

        for field in required:
            if field not in tool_input or not tool_input[field]:
                return False, f"Missing required field: {field}"

        return True, ""

    def _check_max_length(self, tool_name: str,
                          tool_input: Dict[str, Any],
                          config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Check field value lengths.

        Config:
            limits: Dict of field_name -> max_length
        """
        limits = config.get('limits', {})

        for field, max_len in limits.items():
            if field in tool_input:
                value = str(tool_input[field])
                if len(value) > max_len:
                    return False, f"Field '{field}' exceeds max length {max_len}"

        return True, ""

    def _check_allowed_values(self, tool_name: str,
                               tool_input: Dict[str, Any],
                               config: Dict[str, Any]) -> tuple[bool, str]:
        """
        Check field values against allowed list.

        Config:
            constraints: Dict of field_name -> list of allowed values
        """
        constraints = config.get('constraints', {})

        for field, allowed in constraints.items():
            if field in tool_input:
                value = tool_input[field]
                if value not in allowed:
                    return False, f"Invalid value for '{field}': {value}"

        return True, ""

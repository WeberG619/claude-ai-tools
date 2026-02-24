#!/usr/bin/env python3
"""
Structured Output Validator — JSON Schema + text assertion validation.
Validates any agent output against a named contract.
"""

import json
import re
from typing import Dict, List, Optional, Tuple


class ValidationResult:
    """Result of a validation check."""

    def __init__(self, passed: bool, errors: List[str] = None, warnings: List[str] = None):
        self.passed = passed
        self.errors = errors or []
        self.warnings = warnings or []

    def __bool__(self):
        return self.passed

    def to_dict(self) -> Dict:
        return {"passed": self.passed, "errors": self.errors, "warnings": self.warnings}

    def summary(self) -> str:
        if self.passed:
            msg = "VALIDATION PASSED"
            if self.warnings:
                msg += f" ({len(self.warnings)} warning(s))"
            return msg
        return f"VALIDATION FAILED: {'; '.join(self.errors)}"


class OutputValidator:
    """Validates outputs against JSON Schema + text assertions."""

    def validate(self, output: str, contract: Dict) -> ValidationResult:
        """Validate output against a contract definition."""
        errors = []
        warnings = []

        # 1. JSON Schema validation (if output is JSON)
        schema = contract.get("schema")
        if schema:
            json_errors = self._validate_schema(output, schema)
            errors.extend(json_errors)

        # 2. Text assertions
        for assertion in contract.get("text_assertions", []):
            result = self._check_assertion(output, assertion)
            if result:
                if assertion.get("severity") == "warning":
                    warnings.append(result)
                else:
                    errors.append(result)

        # 3. Length checks
        min_words = contract.get("min_words")
        if min_words:
            word_count = len(output.split())
            if word_count < min_words:
                errors.append(f"Output too short: {word_count} words (min {min_words})")

        max_words = contract.get("max_words")
        if max_words:
            word_count = len(output.split())
            if word_count > max_words:
                warnings.append(f"Output long: {word_count} words (max {max_words})")

        return ValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_schema(self, output: str, schema: Dict) -> List[str]:
        """Validate output as JSON against a schema. Basic validation without jsonschema dep."""
        errors = []

        # Try to parse as JSON
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            # Output isn't JSON — try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', output, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    errors.append("Output contains invalid JSON in code block")
                    return errors
            else:
                # Not JSON output — skip schema validation for text outputs
                return []

        # Basic schema checks (no jsonschema dependency needed)
        expected_type = schema.get("type")
        if expected_type == "object" and not isinstance(data, dict):
            errors.append(f"Expected object, got {type(data).__name__}")
            return errors

        if expected_type == "array" and not isinstance(data, list):
            errors.append(f"Expected array, got {type(data).__name__}")
            return errors

        # Required fields
        required = schema.get("required", [])
        if isinstance(data, dict):
            for field in required:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
                elif data[field] is None or data[field] == "":
                    errors.append(f"Required field is empty: {field}")

        # Property type checks
        properties = schema.get("properties", {})
        if isinstance(data, dict):
            for prop, prop_schema in properties.items():
                if prop in data and data[prop] is not None:
                    prop_type = prop_schema.get("type")
                    if prop_type == "string" and not isinstance(data[prop], str):
                        errors.append(f"Field {prop}: expected string, got {type(data[prop]).__name__}")
                    elif prop_type == "number" and not isinstance(data[prop], (int, float)):
                        errors.append(f"Field {prop}: expected number, got {type(data[prop]).__name__}")
                    elif prop_type == "boolean" and not isinstance(data[prop], bool):
                        errors.append(f"Field {prop}: expected boolean, got {type(data[prop]).__name__}")
                    elif prop_type == "array" and not isinstance(data[prop], list):
                        errors.append(f"Field {prop}: expected array, got {type(data[prop]).__name__}")

        return errors

    def _check_assertion(self, output: str, assertion: Dict) -> Optional[str]:
        """Check a single text assertion. Returns error message or None."""
        pattern = assertion.get("pattern", "")
        if not pattern:
            return None

        flags = re.IGNORECASE if assertion.get("case_insensitive", True) else 0
        found = bool(re.search(pattern, output, flags))

        if assertion.get("required") and not found:
            return f"Required pattern not found: {pattern}"

        if assertion.get("fail_if_present") and found:
            return f"Forbidden pattern found: {pattern}"

        return None

    def is_retryable(self, result: ValidationResult, contract: Dict) -> bool:
        """Check if a failed validation is worth retrying."""
        max_retries = contract.get("max_retries", 0)
        return not result.passed and max_retries > 0

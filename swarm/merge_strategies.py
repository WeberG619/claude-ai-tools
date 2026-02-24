#!/usr/bin/env python3
"""
Merge Strategies — Combine results from parallel workers.
"""

import json
import re
from typing import List, Dict, Optional


def concatenate(results: List[str], separator: str = "\n\n---\n\n") -> str:
    """Simple concatenation of all results."""
    return separator.join(f"## Worker {i+1}\n{r}" for i, r in enumerate(results))


def deduplicate(results: List[str]) -> str:
    """Concatenate but remove duplicate findings."""
    seen_lines = set()
    unique_lines = []

    for result in results:
        for line in result.split("\n"):
            stripped = line.strip()
            # Normalize for comparison (ignore leading bullets/numbers)
            normalized = re.sub(r'^[\s\-\*\d\.]+', '', stripped).strip().lower()
            if normalized and normalized not in seen_lines:
                seen_lines.add(normalized)
                unique_lines.append(line)

    return "\n".join(unique_lines)


def merge_json(results: List[str]) -> str:
    """Merge JSON results into a single structure."""
    merged = {"workers": [], "combined": {}}

    for i, result in enumerate(results):
        # Try to extract JSON from result
        try:
            data = json.loads(result)
        except json.JSONDecodeError:
            json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', result, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    data = {"raw": result[:500]}
            else:
                data = {"raw": result[:500]}

        merged["workers"].append({"worker_id": i + 1, "result": data})

        # Merge dict results
        if isinstance(data, dict):
            for key, value in data.items():
                if key in merged["combined"]:
                    existing = merged["combined"][key]
                    if isinstance(existing, list) and isinstance(value, list):
                        merged["combined"][key].extend(value)
                    elif isinstance(existing, dict) and isinstance(value, dict):
                        merged["combined"][key].update(value)
                    else:
                        merged["combined"][key] = [existing, value]
                else:
                    merged["combined"][key] = value

    return json.dumps(merged, indent=2)


def vote(results: List[str], question: str = "") -> str:
    """Majority-vote merge — find consensus across workers."""
    # Extract key findings from each result
    findings = {}
    for i, result in enumerate(results):
        for line in result.split("\n"):
            stripped = line.strip()
            if stripped and len(stripped) > 10:
                normalized = re.sub(r'^[\s\-\*\d\.]+', '', stripped).strip().lower()
                if normalized not in findings:
                    findings[normalized] = {"text": stripped, "votes": 0, "workers": []}
                findings[normalized]["votes"] += 1
                findings[normalized]["workers"].append(i + 1)

    # Sort by votes (consensus items first)
    sorted_findings = sorted(findings.values(), key=lambda x: -x["votes"])

    lines = [f"## Consensus Analysis ({len(results)} workers)"]
    consensus = [f for f in sorted_findings if f["votes"] > 1]
    unique = [f for f in sorted_findings if f["votes"] == 1]

    if consensus:
        lines.append(f"\n### Consensus ({len(consensus)} findings agreed by multiple workers)")
        for f in consensus[:20]:
            lines.append(f"  [{f['votes']}/{len(results)}] {f['text']}")

    if unique:
        lines.append(f"\n### Unique findings ({len(unique)} from individual workers)")
        for f in unique[:20]:
            lines.append(f"  [W{f['workers'][0]}] {f['text']}")

    return "\n".join(lines)


STRATEGIES = {
    "concatenate": concatenate,
    "deduplicate": deduplicate,
    "merge_json": merge_json,
    "vote": vote,
}


def get_merge_strategy(name: str):
    """Get a merge function by name."""
    return STRATEGIES.get(name, concatenate)


def list_merge_strategies() -> List[Dict]:
    """List available merge strategies."""
    return [
        {"name": "concatenate", "description": "Simple concatenation with headers"},
        {"name": "deduplicate", "description": "Concatenate and remove duplicate lines"},
        {"name": "merge_json", "description": "Merge JSON results into combined structure"},
        {"name": "vote", "description": "Majority-vote consensus across workers"},
    ]

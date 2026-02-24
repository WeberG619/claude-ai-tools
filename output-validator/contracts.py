#!/usr/bin/env python3
"""
Contract Registry — Loads and manages output validation contracts.
"""

import json
from pathlib import Path
from typing import Dict, Optional, List

CONTRACTS_DIR = Path(__file__).parent / "contracts"


def load_contract(name: str) -> Optional[Dict]:
    """Load a contract by name (without .json extension)."""
    path = CONTRACTS_DIR / f"{name}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def list_contracts() -> List[Dict]:
    """List all available contracts."""
    contracts = []
    if not CONTRACTS_DIR.exists():
        return contracts
    for path in sorted(CONTRACTS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text())
            contracts.append({
                "name": data.get("name", path.stem),
                "description": data.get("description", ""),
                "file": path.name,
            })
        except Exception:
            contracts.append({"name": path.stem, "description": "Error loading", "file": path.name})
    return contracts


def get_contract(name: str) -> Optional[Dict]:
    """Get a contract by name. Alias for load_contract."""
    return load_contract(name)


def match_contract(agent_type: str = None, task_type: str = None) -> Optional[Dict]:
    """Auto-match a contract based on agent or task type."""
    # Mapping of agent/task patterns to contract names
    mappings = {
        "code": "code_change",
        "developer": "code_change",
        "research": "research_report",
        "explore": "research_report",
        "bim": "bim_operation",
        "revit": "bim_operation",
    }

    search = (agent_type or "").lower() + " " + (task_type or "").lower()
    for pattern, contract_name in mappings.items():
        if pattern in search:
            return load_contract(contract_name)

    # Default: task_result contract
    return load_contract("task_result")

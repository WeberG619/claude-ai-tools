"""
Domain module loader for the Common Sense Engine.

Loads domain-specific corrections from JSON files in the domains/ directory.
Supports loading individual domains, all domains, or custom domain packs.

Usage:
    from domains import DomainLoader

    loader = DomainLoader()

    # List available domains
    available = loader.list_domains()

    # Load a specific domain
    git_domain = loader.load("git")

    # Load all domains
    all_corrections = loader.load_all()

    # Aggregate seeds.json from domain files (backward compat)
    loader.regenerate_seeds()
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


DOMAINS_DIR = Path(__file__).parent / "domains"
SEEDS_PATH = Path(__file__).parent / "seeds.json"


@dataclass
class DomainPack:
    """A loaded domain module."""
    name: str
    version: str
    description: str
    corrections: list[dict]

    @property
    def count(self) -> int:
        return len(self.corrections)

    @property
    def critical_count(self) -> int:
        return sum(1 for c in self.corrections if c.get("severity") == "critical")

    def get_correction(self, correction_id: str) -> Optional[dict]:
        for c in self.corrections:
            if c.get("id") == correction_id:
                return c
        return None


class DomainLoader:
    """Loads and manages domain-specific correction packs."""

    def __init__(self, domains_dir: Path = None):
        self.domains_dir = domains_dir or DOMAINS_DIR
        self._cache: dict[str, DomainPack] = {}

    def list_domains(self) -> list[dict]:
        """List all available domain files with metadata."""
        domains = []
        if not self.domains_dir.exists():
            return domains

        for f in sorted(self.domains_dir.glob("*.json")):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                domains.append({
                    "name": data.get("domain", f.stem),
                    "version": data.get("version", "unknown"),
                    "description": data.get("description", ""),
                    "correction_count": len(data.get("corrections", [])),
                    "file": str(f),
                })
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Skipping malformed domain file {f}: {e}", file=sys.stderr)

        return domains

    def load(self, domain_name: str) -> Optional[DomainPack]:
        """Load a single domain by name."""
        if domain_name in self._cache:
            return self._cache[domain_name]

        domain_file = self.domains_dir / f"{domain_name}.json"
        if not domain_file.exists():
            print(f"Domain not found: {domain_name}", file=sys.stderr)
            return None

        try:
            with open(domain_file) as f:
                data = json.load(f)

            pack = DomainPack(
                name=data.get("domain", domain_name),
                version=data.get("version", "unknown"),
                description=data.get("description", ""),
                corrections=data.get("corrections", []),
            )
            self._cache[domain_name] = pack
            return pack

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Failed to load domain {domain_name}: {e}", file=sys.stderr)
            return None

    def load_all(self) -> list[DomainPack]:
        """Load all available domains."""
        packs = []
        for domain_info in self.list_domains():
            pack = self.load(domain_info["name"])
            if pack:
                packs.append(pack)
        return packs

    def load_domains(self, names: list[str]) -> list[DomainPack]:
        """Load specific domains by name."""
        packs = []
        for name in names:
            pack = self.load(name)
            if pack:
                packs.append(pack)
        return packs

    def get_all_corrections(self, domain_names: list[str] = None) -> list[dict]:
        """Get all corrections from specified domains (or all if none specified).

        Each correction is annotated with its source domain.
        """
        if domain_names:
            packs = self.load_domains(domain_names)
        else:
            packs = self.load_all()

        corrections = []
        for pack in packs:
            for correction in pack.corrections:
                # Annotate with source domain
                annotated = {**correction, "_domain": pack.name}
                corrections.append(annotated)

        return corrections

    def regenerate_seeds(self, output_path: Path = None) -> int:
        """Regenerate seeds.json from all domain files.

        This provides backward compatibility with code that reads seeds.json directly.
        """
        output = output_path or SEEDS_PATH
        all_corrections = self.get_all_corrections()

        # Remove internal annotation
        clean_corrections = []
        for c in all_corrections:
            clean = {k: v for k, v in c.items() if not k.startswith("_")}
            clean_corrections.append(clean)

        seeds = {
            "version": "2.0",
            "description": "Auto-generated from domain modules. Do not edit directly — edit domain files in domains/ instead.",
            "generated_from": [d["name"] for d in self.list_domains()],
            "corrections": clean_corrections,
        }

        with open(output, "w") as f:
            json.dump(seeds, f, indent=2)

        return len(clean_corrections)

    def add_correction(self, domain_name: str, correction: dict) -> bool:
        """Add a new correction to a domain file.

        Creates the domain file if it doesn't exist.
        """
        domain_file = self.domains_dir / f"{domain_name}.json"

        if domain_file.exists():
            with open(domain_file) as f:
                data = json.load(f)
        else:
            data = {
                "domain": domain_name,
                "version": "1.0",
                "description": f"Corrections for {domain_name}",
                "corrections": [],
            }

        # Check for duplicate IDs
        existing_ids = {c["id"] for c in data["corrections"] if "id" in c}
        if correction.get("id") in existing_ids:
            print(f"Correction {correction['id']} already exists in {domain_name}",
                  file=sys.stderr)
            return False

        data["corrections"].append(correction)

        with open(domain_file, "w") as f:
            json.dump(data, f, indent=2)

        # Invalidate cache
        self._cache.pop(domain_name, None)

        return True

    def validate_all(self) -> dict:
        """Validate all domain files for correctness.

        Returns dict with domain name → list of issues.
        """
        issues = {}

        all_ids = set()
        for domain_info in self.list_domains():
            pack = self.load(domain_info["name"])
            if not pack:
                issues[domain_info["name"]] = ["Failed to load"]
                continue

            domain_issues = []

            for c in pack.corrections:
                # Required fields
                required = {"id", "what_went_wrong", "correct_approach", "detection", "severity", "tags"}
                missing = required - set(c.keys())
                if missing:
                    domain_issues.append(f"{c.get('id', 'UNKNOWN')}: missing {missing}")

                # Unique IDs across all domains
                cid = c.get("id", "")
                if cid in all_ids:
                    domain_issues.append(f"Duplicate ID: {cid}")
                all_ids.add(cid)

                # Valid severity
                if c.get("severity") not in {"critical", "high", "medium", "low"}:
                    domain_issues.append(f"{cid}: invalid severity '{c.get('severity')}'")

                # Tags non-empty
                if not c.get("tags"):
                    domain_issues.append(f"{cid}: no tags")

            if domain_issues:
                issues[domain_info["name"]] = domain_issues

        return issues


# ─── CLI ─────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Domain module manager")
    parser.add_argument("command", choices=["list", "load", "validate", "regenerate"],
                        help="list: show domains, load: load a domain, validate: check all, regenerate: rebuild seeds.json")
    parser.add_argument("--domain", help="Domain name (for load command)")
    args = parser.parse_args()

    loader = DomainLoader()

    if args.command == "list":
        for d in loader.list_domains():
            print(f"  {d['name']:15s} {d['correction_count']:3d} corrections  {d['description'][:60]}")

    elif args.command == "load":
        if not args.domain:
            print("--domain required")
            sys.exit(1)
        pack = loader.load(args.domain)
        if pack:
            print(f"Domain: {pack.name} v{pack.version}")
            print(f"Corrections: {pack.count} ({pack.critical_count} critical)")
            for c in pack.corrections:
                print(f"  [{c['severity']:8s}] {c['id']}: {c['what_went_wrong'][:80]}")

    elif args.command == "validate":
        issues = loader.validate_all()
        if issues:
            for domain, problems in issues.items():
                print(f"\n{domain}:")
                for p in problems:
                    print(f"  - {p}")
        else:
            print("All domain files valid.")

    elif args.command == "regenerate":
        count = loader.regenerate_seeds()
        print(f"Regenerated seeds.json with {count} corrections from {len(loader.list_domains())} domains.")


if __name__ == "__main__":
    main()

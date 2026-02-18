"""
Injection helper for Claude Code sub-agents.

Reads the kernel and domain corrections, returns a formatted string
you can prepend to any agent's prompt to give it common sense.

v2.0 changes:
  - Supports domain-selective injection (load only relevant domains)
  - Uses kernel-core.md (universal) by default
  - Includes effectiveness annotations from feedback tracking

Usage:
    import inject

    # Full injection (universal kernel + all seeds)
    agent_prompt = inject.get_full_injection() + "\\n\\n" + your_agent_prompt

    # Domain-selective (only git and filesystem)
    agent_prompt = inject.get_full_injection(domains=["git", "filesystem"])

    # Kernel only, no seeds
    agent_prompt = inject.get_kernel()

From CLI:
    python inject.py                        # Full injection
    python inject.py --kernel-only          # Just the kernel
    python inject.py --domains git,fs       # Selective domains
    python inject.py --core                 # Universal kernel (no user-specific)
"""

import json
from pathlib import Path

HERE = Path(__file__).parent


def get_kernel(core_only: bool = False) -> str:
    """Return the common sense kernel prompt.

    Args:
        core_only: If True, use kernel-core.md (universal, no user-specific rules).
                   If False, use kernel.md (may include user-specific rules).
    """
    if core_only:
        kernel_path = HERE / "kernel-core.md"
    else:
        kernel_path = HERE / "kernel.md"

    if not kernel_path.exists():
        # Fallback to whichever exists
        for fallback in [HERE / "kernel-core.md", HERE / "kernel.md"]:
            if fallback.exists():
                return fallback.read_text()
        return ""

    return kernel_path.read_text()


def get_seeds_as_prompt(domains: list[str] = None) -> str:
    """Format seed corrections as a prompt-injectable block.

    Args:
        domains: Optional list of domain names to include.
                 If None, includes all domains.
    """
    # Try domain loader first
    try:
        from domains import DomainLoader
        loader = DomainLoader()
        if domains:
            corrections = loader.get_all_corrections(domains)
        else:
            corrections = loader.get_all_corrections()
    except ImportError:
        # Fallback to seeds.json
        seeds_path = HERE / "seeds.json"
        if not seeds_path.exists():
            return ""
        data = json.loads(seeds_path.read_text())
        corrections = data.get("corrections", [])

    if not corrections:
        return ""

    lines = [
        "## Pre-Loaded Experience (Known Mistakes to Avoid)",
        ""
    ]

    # Group by domain for readability
    by_domain: dict[str, list] = {}
    for c in corrections:
        domain = c.get("domain", c.get("_domain", "general"))
        by_domain.setdefault(domain, []).append(c)

    for domain, domain_corrections in sorted(by_domain.items()):
        lines.append(f"### {domain.upper()}")
        for c in domain_corrections:
            severity_icon = {
                "critical": "!!!",
                "high": "!!",
                "medium": "!",
                "low": "~"
            }.get(c.get("severity", "medium"), "!")

            lines.append(
                f"- [{severity_icon}] {c.get('what_went_wrong', 'Unknown issue')}"
            )
            lines.append(
                f"  **Do instead:** {c.get('correct_approach', 'N/A')}"
            )
            lines.append(
                f"  **Watch for:** {c.get('detection', 'N/A')}"
            )
            lines.append("")

    return "\n".join(lines)


def get_corrections_supplement() -> str:
    """Load the auto-generated kernel-corrections.md if it exists."""
    corrections_path = HERE / "kernel-corrections.md"
    if corrections_path.exists():
        return corrections_path.read_text()
    return ""


def get_full_injection(include_seeds: bool = True,
                       include_corrections: bool = True,
                       domains: list[str] = None,
                       core_only: bool = False) -> str:
    """Get the complete common sense injection.

    Args:
        include_seeds: Include seed corrections from domain files
        include_corrections: Include auto-generated correction supplement
        domains: Optional domain filter for seeds
        core_only: Use universal kernel (no user-specific rules)
    """
    parts = [get_kernel(core_only=core_only)]

    if include_seeds:
        seeds = get_seeds_as_prompt(domains=domains)
        if seeds:
            parts.append(seeds)

    if include_corrections:
        corrections = get_corrections_supplement()
        if corrections:
            parts.append(corrections)

    return "\n\n---\n\n".join(parts)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate common sense prompt injection")
    parser.add_argument("--with-seeds", action="store_true",
                        help="Include seed corrections")
    parser.add_argument("--kernel-only", action="store_true",
                        help="Only the kernel, no seeds")
    parser.add_argument("--seeds-only", action="store_true",
                        help="Only the seeds, no kernel")
    parser.add_argument("--core", action="store_true",
                        help="Use universal kernel (no user-specific rules)")
    parser.add_argument("--domains", type=str, default=None,
                        help="Comma-separated domain names to include")
    parser.add_argument("--no-corrections", action="store_true",
                        help="Exclude auto-generated corrections supplement")
    args = parser.parse_args()

    domain_list = args.domains.split(",") if args.domains else None

    if args.seeds_only:
        print(get_seeds_as_prompt(domains=domain_list))
    elif args.kernel_only:
        print(get_kernel(core_only=args.core))
    else:
        print(get_full_injection(
            include_seeds=args.with_seeds or not args.kernel_only,
            include_corrections=not args.no_corrections,
            domains=domain_list,
            core_only=args.core,
        ))


if __name__ == "__main__":
    main()

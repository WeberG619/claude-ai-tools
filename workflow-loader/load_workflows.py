#!/usr/bin/env python3
"""
Session Start Hook: Load Weber's Workflows
This script outputs critical workflow information that Claude MUST follow.
"""

import os

WORKFLOWS_FILE = "/mnt/d/_CLAUDE-TOOLS/WEBER_WORKFLOWS.md"

def load_workflows():
    """Load and output the workflows file content."""

    print("=" * 60)
    print("🚨 MANDATORY WORKFLOWS LOADED - FOLLOW THESE EXACTLY")
    print("=" * 60)

    if os.path.exists(WORKFLOWS_FILE):
        with open(WORKFLOWS_FILE, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract key sections for quick reference
        lines = content.split('\n')

        # Print identity section
        print("\n## IDENTITY")
        print("- User: Weber Gouin (NEVER 'Rick')")
        print("- Email: weberg619@gmail.com")
        print("- Browser: Chrome (NEVER Edge/Outlook)")

        # Print critical rules
        print("\n## CRITICAL RULES")
        print("- EMAIL: Use Gmail in Chrome, NOT Outlook")
        print("- REVIT: Use named pipes, NOT HTTP")
        print("- SIGN: Always 'Weber Gouin'")

        # Print contact quick-ref
        print("\n## TOP CONTACTS")
        print("- Isa Fantal: ifantal@lesfantal.com")
        print("- Bruce Davis: bruce@bdarchitect.net")
        print("- Paola Gomez: paola@bdarchitect.net")
        print("- Rachelle (Afuri): rachelle@afuriaesthetics.com")

        print("\n## FULL WORKFLOWS FILE")
        print(f"Location: {WORKFLOWS_FILE}")
        print("Read this file for complete reference.")

    else:
        print(f"ERROR: Workflows file not found at {WORKFLOWS_FILE}")
        print("Create this file with Weber's standard workflows!")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    load_workflows()

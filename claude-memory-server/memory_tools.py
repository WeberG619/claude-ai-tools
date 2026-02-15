#!/usr/bin/env python3
"""
CLI wrapper for new self-improvement loop tools.
Usage: python memory_tools.py <command> [args...]

Commands:
  check <action> <context>     - Check for relevant corrections before an action
  helped <id> <true/false>     - Mark whether a correction helped
  avoided <what> <how> [id]    - Log when you avoided a mistake
  patterns                     - Analyze correction patterns
  stats                        - Get improvement statistics
"""

import sys
import os

# Add server module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from server import (
    memory_check_before_action,
    memory_correction_helped,
    memory_log_avoided_mistake,
    memory_synthesize_patterns,
    memory_get_improvement_stats
)

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "check":
        if len(sys.argv) < 4:
            print("Usage: check <planned_action> <context>")
            sys.exit(1)
        result = memory_check_before_action(sys.argv[2], sys.argv[3])
        print(result)

    elif command == "helped":
        if len(sys.argv) < 4:
            print("Usage: helped <correction_id> <true/false> [notes]")
            sys.exit(1)
        correction_id = int(sys.argv[2])
        helped = sys.argv[3].lower() in ('true', 'yes', '1')
        notes = sys.argv[4] if len(sys.argv) > 4 else None
        result = memory_correction_helped(correction_id, helped, notes)
        print(result)

    elif command == "avoided":
        if len(sys.argv) < 4:
            print("Usage: avoided <what_almost_happened> <how_avoided> [correction_id] [project]")
            sys.exit(1)
        what = sys.argv[2]
        how = sys.argv[3]
        corr_id = int(sys.argv[4]) if len(sys.argv) > 4 else None
        project = sys.argv[5] if len(sys.argv) > 5 else None
        result = memory_log_avoided_mistake(what, how, corr_id, project)
        print(result)

    elif command == "patterns":
        result = memory_synthesize_patterns()
        print(result)

    elif command == "stats":
        result = memory_get_improvement_stats()
        print(result)

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()

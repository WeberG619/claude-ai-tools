#!/usr/bin/env python3
"""
Creative Studio - Run Script
=============================
CLI interface for running the Creative Studio agent team.
"""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Creative Studio - AI Team for Presentations & Content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a presentation
  python run_team.py --presentation "AI in Architecture" --slides 5

  # Write copy/content
  python run_team.py --copy "Write taglines for BIM automation software"

  # General creative task
  python run_team.py --task "Create a pitch deck for our new AI service"
"""
    )

    parser.add_argument("--task", "-t", help="General creative task")
    parser.add_argument("--presentation", "-p", help="Create a presentation on this topic")
    parser.add_argument("--slides", "-s", type=int, default=5, help="Number of slides (default: 5)")
    parser.add_argument("--copy", "-c", help="Write copy/content for this brief")
    parser.add_argument("--mute", action="store_true", help="Disable voice output")

    args = parser.parse_args()

    # Import the team
    from autonomous_agents import CreativeTeam, VOICE_DISABLED
    import autonomous_agents

    if args.mute:
        autonomous_agents.VOICE_DISABLED = True

    team = CreativeTeam()

    print(f"\n{'='*60}")
    print(f"  🎨 CREATIVE STUDIO")
    print(f"{'='*60}\n")

    if args.presentation:
        team.create_presentation(args.presentation, slides=args.slides)

    elif args.copy:
        team.write_copy(args.copy)

    elif args.task:
        # Auto-detect task type
        task_lower = args.task.lower()
        if any(kw in task_lower for kw in ['presentation', 'slides', 'deck', 'pitch']):
            team.create_presentation(args.task, slides=args.slides)
        else:
            team.write_copy(args.task)

    else:
        parser.print_help()
        print("\n💡 Try: python run_team.py --presentation 'AI in Architecture'")

    print(f"\n{'='*60}")
    print(f"  SESSION COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

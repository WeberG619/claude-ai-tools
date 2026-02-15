#!/usr/bin/env python3
"""
Office Command Center - Run Script
===================================
CLI interface for running the Office Command Center agent team.
"""

import sys
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Office Command Center - AI Team for Business Operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Handle a general task
  python run_team.py --task "Check my calendar for today and summarize"

  # Quick email draft
  python run_team.py --email --to "bruce@bdarchitect.net" --subject "Project Update" --context "Brief update on project timeline"

  # Add a follow-up
  python run_team.py --followup "Call Bruce about drawings" --due "2026-02-06"

  # Check calendar
  python run_team.py --calendar
"""
    )

    parser.add_argument("--task", "-t", help="General task for the team")
    parser.add_argument("--email", action="store_true", help="Draft an email")
    parser.add_argument("--to", help="Email recipient")
    parser.add_argument("--subject", "-s", help="Email subject")
    parser.add_argument("--context", "-c", help="Context for email/task")
    parser.add_argument("--followup", "-f", help="Add a follow-up task")
    parser.add_argument("--due", help="Due date for follow-up (YYYY-MM-DD)")
    parser.add_argument("--calendar", action="store_true", help="Check today's calendar")
    parser.add_argument("--mute", action="store_true", help="Disable voice output")

    args = parser.parse_args()

    # Import the team
    from autonomous_agents import OfficeTeam, VOICE_DISABLED
    import autonomous_agents

    if args.mute:
        autonomous_agents.VOICE_DISABLED = True

    team = OfficeTeam()

    print(f"\n{'='*60}")
    print(f"  🏢 OFFICE COMMAND CENTER")
    print(f"{'='*60}\n")

    if args.email and args.to:
        # Quick email workflow
        subject = args.subject or "Follow-up"
        context = args.context or "Please draft a professional email."
        team.quick_email(args.to, subject, context)

    elif args.calendar:
        # Check calendar
        team.check_calendar()

    elif args.followup:
        # Add follow-up
        due = args.due or "2026-02-05"  # Default to tomorrow
        team.add_followup(args.followup, due)

    elif args.task:
        # General task handling
        team.handle_task(args.task)

    else:
        parser.print_help()
        print("\n💡 Try: python run_team.py --task 'Draft an email to Bruce about the project'")

    print(f"\n{'='*60}")
    print(f"  SESSION COMPLETE")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

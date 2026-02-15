#!/usr/bin/env python3
"""
Weekly Review - Automated brain maintenance and learning synthesis.

Runs periodically (ideally weekly via Task Scheduler) to:
1. Synthesize patterns from corrections
2. Decay unhelpful corrections
3. Archive old low-effectiveness corrections
4. Generate and store weekly learning summary

Can also be run manually: python weekly_review.py
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Add memory server to path
sys.path.insert(0, '/mnt/d/_CLAUDE-TOOLS/claude-memory-server/src')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("/mnt/d/_CLAUDE-TOOLS/system-bridge/weekly_reports")
OUTPUT_DIR.mkdir(exist_ok=True)


def run_pattern_synthesis():
    """Analyze corrections to find recurring patterns."""
    try:
        from server import memory_synthesize_patterns
        result = memory_synthesize_patterns()
        logger.info("Pattern synthesis completed")
        return result
    except Exception as e:
        logger.error(f"Pattern synthesis failed: {e}")
        return None


def decay_unhelpful_corrections(dry_run=True):
    """Reduce importance of corrections that aren't helping."""
    try:
        from server import memory_decay_corrections
        result = memory_decay_corrections(
            dry_run=dry_run,
            surfaced_threshold=5,  # If surfaced 5+ times with 0 helps
            decay_amount=1
        )
        logger.info(f"Decay corrections {'(dry run)' if dry_run else ''} completed")
        return result
    except Exception as e:
        logger.error(f"Decay corrections failed: {e}")
        return None


def archive_old_corrections(dry_run=True):
    """Archive old, low-effectiveness corrections."""
    try:
        from server import memory_archive_old_corrections
        result = memory_archive_old_corrections(
            dry_run=dry_run,
            days_old=90,
            max_effectiveness=0.3
        )
        logger.info(f"Archive old corrections {'(dry run)' if dry_run else ''} completed")
        return result
    except Exception as e:
        logger.error(f"Archive corrections failed: {e}")
        return None


def get_improvement_stats():
    """Get current self-improvement statistics."""
    try:
        from server import memory_get_improvement_stats
        result = memory_get_improvement_stats()
        return result
    except Exception as e:
        logger.error(f"Get improvement stats failed: {e}")
        return None


def get_memory_stats():
    """Get overall memory statistics."""
    try:
        from server import memory_stats
        result = memory_stats()
        return result
    except Exception as e:
        logger.error(f"Get memory stats failed: {e}")
        return None


def store_weekly_summary(summary: str):
    """Store the weekly summary as a memory."""
    try:
        from server import memory_store
        result = memory_store(
            content=summary,
            memory_type="outcome",
            importance=7,
            tags=["weekly-review", "learning-summary"],
            summary=f"Weekly learning review - {datetime.now().strftime('%Y-%m-%d')}"
        )
        logger.info("Weekly summary stored to memory")
        return result
    except Exception as e:
        logger.error(f"Store weekly summary failed: {e}")
        return None


def generate_weekly_report(patterns, decay_result, archive_result, stats, improvement_stats):
    """Generate human-readable weekly report."""
    report = []
    report.append(f"# Weekly Learning Review - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report.append("")

    # Pattern synthesis results
    report.append("## Pattern Analysis")
    if patterns:
        report.append(patterns[:2000])  # Limit size
    else:
        report.append("Pattern synthesis did not return results.")
    report.append("")

    # Decay results
    report.append("## Correction Decay (Preview)")
    if decay_result:
        report.append(decay_result[:1000])
    else:
        report.append("No decay results.")
    report.append("")

    # Archive results
    report.append("## Archive Candidates (Preview)")
    if archive_result:
        report.append(archive_result[:1000])
    else:
        report.append("No archive candidates.")
    report.append("")

    # Memory statistics
    report.append("## Memory Statistics")
    if stats:
        report.append(stats[:500])
    else:
        report.append("Statistics unavailable.")
    report.append("")

    # Improvement statistics
    report.append("## Self-Improvement Stats")
    if improvement_stats:
        report.append(improvement_stats[:500])
    else:
        report.append("Improvement stats unavailable.")
    report.append("")

    return "\n".join(report)


def main(apply_changes=False):
    """Run the weekly review process."""
    logger.info("=" * 50)
    logger.info("Starting Weekly Learning Review")
    logger.info(f"Mode: {'APPLY CHANGES' if apply_changes else 'DRY RUN (preview only)'}")
    logger.info("=" * 50)

    # 1. Run pattern synthesis
    logger.info("\n[1/5] Synthesizing patterns from corrections...")
    patterns = run_pattern_synthesis()

    # 2. Decay unhelpful corrections
    logger.info("\n[2/5] Checking for unhelpful corrections to decay...")
    decay_result = decay_unhelpful_corrections(dry_run=not apply_changes)

    # 3. Archive old corrections
    logger.info("\n[3/5] Checking for old corrections to archive...")
    archive_result = archive_old_corrections(dry_run=not apply_changes)

    # 4. Get statistics
    logger.info("\n[4/5] Gathering statistics...")
    stats = get_memory_stats()
    improvement_stats = get_improvement_stats()

    # 5. Generate and save report
    logger.info("\n[5/5] Generating weekly report...")
    report = generate_weekly_report(patterns, decay_result, archive_result, stats, improvement_stats)

    # Save report to file
    report_file = OUTPUT_DIR / f"weekly_review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_file.write_text(report)
    logger.info(f"Report saved to: {report_file}")

    # Store summary to memory
    summary = f"""Weekly Learning Review - {datetime.now().strftime('%Y-%m-%d')}

Key Findings:
- Pattern synthesis completed
- Decay check: {'Changes applied' if apply_changes else 'Preview only'}
- Archive check: {'Changes applied' if apply_changes else 'Preview only'}

See full report: {report_file}
"""
    store_weekly_summary(summary)

    logger.info("\n" + "=" * 50)
    logger.info("Weekly Review Complete")
    logger.info("=" * 50)

    # Print report to stdout
    print(report)

    return report


if __name__ == "__main__":
    # Default to dry run unless --apply is specified
    apply_changes = "--apply" in sys.argv

    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
Weekly Review - Brain Maintenance Script

Usage:
    python weekly_review.py           # Dry run (preview changes)
    python weekly_review.py --apply   # Apply changes (decay/archive)

This script:
1. Synthesizes patterns from corrections
2. Identifies unhelpful corrections to decay
3. Identifies old corrections to archive
4. Generates a weekly learning report
5. Stores summary to memory database

Run weekly via Task Scheduler or manually.
""")
        sys.exit(0)

    main(apply_changes=apply_changes)

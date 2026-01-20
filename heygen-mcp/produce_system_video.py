#!/usr/bin/env python3
"""
AI-Powered Automation System - YouTube Video Production
Generates professional video segments explaining the system
"""

import os
import sys
import json
from pathlib import Path

# Add parent to path for heygen import
sys.path.insert(0, str(Path(__file__).parent))
from heygen import create_video_from_text, create_multi_scene_video, get_quota, AVATARS

# Output directory
OUTPUT_DIR = Path(__file__).parent / "video_segments"
OUTPUT_DIR.mkdir(exist_ok=True)

# Video Script - Professional male presenter
AVATAR = "Adrian_public_2_20240312"  # Adrian in Blue Suit - Professional male
GENDER = "male"

# =============================================================================
# VIDEO SCRIPT - AI-Powered Automation System Overview
# =============================================================================

SCRIPT_SEGMENTS = [
    {
        "name": "01_intro",
        "text": """Welcome! Today I'm going to show you something that's changing the way professionals work with complex software. Imagine having an AI assistant that doesn't just answer questions, but actually controls your software, automates repetitive tasks, and learns from every interaction. That's exactly what we've built."""
    },
    {
        "name": "02_problem",
        "text": """If you work with specialized software like CAD, BIM, design tools, or any complex professional application, you know the pain. Hours spent on repetitive tasks. Switching between applications. Copying data manually. Following the same workflows over and over. What if an AI could handle all of that for you?"""
    },
    {
        "name": "03_solution",
        "text": """Our system connects a powerful AI assistant directly to your professional software through a technology called Model Context Protocol, or MCP. This creates a bridge that lets the AI see what you're working on, understand your project, and take actions on your behalf. It's like having an expert colleague who never sleeps and never forgets."""
    },
    {
        "name": "04_how_it_works",
        "text": """Here's how it works. You communicate with the AI using natural language, just like talking to a colleague. The AI understands your request, accesses your software through the bridge connection, and executes the necessary commands. It can read project data, make modifications, run analyses, and even generate reports. All while you focus on the creative and strategic work that matters most."""
    },
    {
        "name": "05_features_memory",
        "text": """One of the most powerful features is the persistent memory system. The AI remembers your preferences, past decisions, and project context across sessions. If you corrected something last week, it won't make that same mistake again. It learns your workflow and adapts to how you work."""
    },
    {
        "name": "06_features_voice",
        "text": """The system also includes voice feedback. After completing tasks, the AI speaks a summary of what was accomplished, any issues encountered, and recommendations for next steps. You can keep working while staying informed, no need to read through logs or check status constantly."""
    },
    {
        "name": "07_features_automation",
        "text": """For repetitive workflows, you can create automation pipelines. Define a sequence of steps once, and the AI executes them consistently every time. Document processing, quality checks, data extraction, model generation. Tasks that used to take hours now happen in minutes."""
    },
    {
        "name": "08_applications",
        "text": """While our system works exceptionally well with BIM software like Revit, the architecture is flexible. The same approach can connect AI to virtually any professional software. Engineering tools, design applications, project management systems, database platforms. If it has an API or can be automated, our bridge technology can connect it to AI."""
    },
    {
        "name": "09_benefits",
        "text": """The benefits are significant. We're seeing productivity improvements of fifty percent or more on routine tasks. Error rates drop dramatically because the AI follows consistent procedures. And professionals can focus on high-value work instead of manual data entry and repetitive operations."""
    },
    {
        "name": "10_closing",
        "text": """This is the future of professional software. AI that doesn't replace you, but amplifies your capabilities. If you're interested in learning more about how this system can transform your workflow, check the links in the description. Thanks for watching, and I'll see you in the next video."""
    }
]

def check_credits():
    """Verify we have enough credits"""
    quota = get_quota()
    if quota:
        remaining = quota['remaining_quota']
        print(f"Credits available: {remaining}")
        # Estimate ~30-50 credits per segment, 10 segments = 300-500 credits
        if remaining < 300:
            print("WARNING: You may not have enough credits for all segments")
            print("Each segment costs approximately 30-50 credits")
        return remaining
    return 0

def generate_segment(segment, avatar=AVATAR, gender=GENDER):
    """Generate a single video segment"""
    name = segment['name']
    text = segment['text']
    output_path = str(OUTPUT_DIR / f"{name}.mp4")

    print(f"\n{'='*60}")
    print(f"Generating: {name}")
    print(f"Text length: {len(text)} characters")
    print(f"Output: {output_path}")
    print(f"{'='*60}")

    result = create_video_from_text(
        text=text,
        avatar_id=avatar,
        output_path=output_path,
        gender=gender,
        voice_style="professional",
        resolution="720p"
    )

    if result:
        print(f"SUCCESS: {name}")
        return output_path
    else:
        print(f"FAILED: {name}")
        return None

def generate_all_segments():
    """Generate all video segments"""
    print("\n" + "="*60)
    print("AI-POWERED AUTOMATION SYSTEM - VIDEO PRODUCTION")
    print("="*60)

    # Check credits first
    credits = check_credits()
    if credits < 100:
        print("\nInsufficient credits. Please add more credits to continue.")
        return

    print(f"\nGenerating {len(SCRIPT_SEGMENTS)} video segments...")
    print(f"Avatar: {AVATAR}")
    print(f"Output directory: {OUTPUT_DIR}")

    successful = []
    failed = []

    for segment in SCRIPT_SEGMENTS:
        result = generate_segment(segment)
        if result:
            successful.append(segment['name'])
        else:
            failed.append(segment['name'])

    print("\n" + "="*60)
    print("PRODUCTION COMPLETE")
    print("="*60)
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print(f"\nFailed segments: {', '.join(failed)}")

    # Check remaining credits
    check_credits()

    print(f"\nVideo segments saved to: {OUTPUT_DIR}")
    print("\nNext steps:")
    print("1. Review each segment")
    print("2. Add text overlays and graphics in video editor")
    print("3. Add background music")
    print("4. Compile into final video")

def generate_single(segment_name):
    """Generate a single segment by name"""
    for segment in SCRIPT_SEGMENTS:
        if segment['name'] == segment_name:
            return generate_segment(segment)
    print(f"Segment not found: {segment_name}")
    return None

def list_segments():
    """List all script segments"""
    print("\nVideo Script Segments:")
    print("-" * 40)
    for i, seg in enumerate(SCRIPT_SEGMENTS, 1):
        words = len(seg['text'].split())
        duration = words / 150 * 60  # Rough estimate: 150 words/min
        print(f"{i:2}. {seg['name']}: ~{duration:.0f}s ({words} words)")
    print("-" * 40)
    total_words = sum(len(s['text'].split()) for s in SCRIPT_SEGMENTS)
    total_duration = total_words / 150
    print(f"Total: ~{total_duration:.1f} minutes ({total_words} words)")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Produce AI System Overview Video")
    parser.add_argument("--all", action="store_true", help="Generate all segments")
    parser.add_argument("--segment", type=str, help="Generate specific segment by name")
    parser.add_argument("--list", action="store_true", help="List all segments")
    parser.add_argument("--credits", action="store_true", help="Check remaining credits")

    args = parser.parse_args()

    if args.credits:
        check_credits()
    elif args.list:
        list_segments()
    elif args.segment:
        generate_single(args.segment)
    elif args.all:
        generate_all_segments()
    else:
        # Default: show segments and ask for confirmation
        list_segments()
        print("\nUse --all to generate all segments")
        print("Use --segment <name> to generate a specific segment")

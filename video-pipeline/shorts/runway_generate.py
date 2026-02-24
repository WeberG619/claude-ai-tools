#!/usr/bin/env python3 -u
"""
Submit all Runway clip generations and download as they complete.
Handles throttling gracefully — Runway queues tasks and processes sequentially.
Run with: python3 -u runway_generate.py
"""

import sys
import time
import json
import requests
from pathlib import Path
from runwayml import RunwayML

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

RUNWAY_KEY = "key_30d5f913c25e834c7d5f21f14eea9f470f86687d972a39ef571ffa8a1ca91b520513e135f7914ae7c057ebaad0ab723d39fc8952e0b107ab8303694daa34e087"
MODEL = "gen4.5"
CLIP_DURATION = 10
BASE = Path("/mnt/d/_CLAUDE-TOOLS/video-pipeline/shorts")

STYLE = (
    "dark futuristic tech environment, holographic glowing interface, "
    "cyan and blue neon accents, cinematic camera movement, "
    "volumetric lighting, depth of field, sci-fi aesthetic, "
    "professional cinematography"
)

# All clips to generate: (video_dir, clip_index, prompt)
ALL_CLIPS = []

def add_clips(video_dir, prompts):
    for i, p in enumerate(prompts):
        ALL_CLIPS.append((video_dir, i, p))

# ── VIDEO 01: RETRY LADDER ──
add_clips("video_01_retry_ladder", [
    "Close-up of a futuristic AI terminal displaying cascading red error codes on holographic screens, a glowing blue strategy ladder diagram materializing beside the errors, dark control room with cyan ambient lighting and volumetric fog, cinematic slow push-in camera",
    "A robotic precision arm making a surgical micro-repair on a glowing circuit board, tiny sparks of cyan light shooting out, ultra-detailed close-up, dark background with blue rim lighting, macro sci-fi cinematography",
    "A vast holographic codebase floating in dark space being completely deconstructed and rebuilt, code blocks dissolving into particles and reforming into new architecture with flowing blue and purple energy connections, cinematic wide shot with dramatic lighting",
    "Multiple luminous pathways branching from a glowing decision node in dark space, camera tracking along one path that blazes bright green while all others fade to dim, particles streaming along the successful route, cinematic",
    "Glowing data particles spiraling into a crystalline neural network brain structure, each node pulsing cyan as knowledge is permanently stored, camera slowly pulling back to reveal the complete memory system, cinematic finale",
])

# ── VIDEO 02: ARCHITECTURE ──
add_clips("video_02_architecture", [
    "A single brilliant sphere of cyan light activating in the center of complete darkness, holographic rings slowly expanding outward as a futuristic command hub powers up from nothing, volumetric light beams, cinematic slow reveal",
    "Five smaller glowing orbs of different colors cyan green yellow magenta blue emerging and orbiting around a central hub, beams of flowing light connecting them in a constellation network pattern, dark space, cinematic orbit camera",
    "Streams of luminous data particles flowing rapidly between interconnected glowing nodes in a futuristic network, packets of light traveling along pathways at high speed, the network pulsing with synchronized activity, cinematic",
    "A complete interconnected system of glowing nodes and flowing data streams fully operational, holographic dashboard overlays showing live status, camera slowly pulling back to reveal the entire magnificent architecture, cinematic wide shot",
])

# ── VIDEO 03: CHECKPOINT ──
add_clips("video_03_checkpoint", [
    "A futuristic glowing progress timeline bar floating in dark space, diamond-shaped checkpoint markers appearing one by one along the line, each checkpoint emitting a brilliant pulse of green light upon activation, holographic particles, cinematic",
    "A crystalline data structure materializing in mid-air, capturing a complete system state as a frozen 3D snapshot, swirling particles suspending in place like digital amber, gold and cyan light illuminating the preservation, cinematic",
    "A futuristic holographic display experiencing a dramatic system crash, the screen fragmenting with red glitches and going dark, then rebooting as checkpoint data streams back in with green restoration light spreading across the interface, cinematic",
    "A seamless system resumption showing progress bars instantly filling from their saved checkpoint positions, holographic interface displaying RESUMED in green light, everything continuing smoothly from exactly where it stopped, cinematic",
])

# ── VIDEO 04: SWARM ──
add_clips("video_04_swarm", [
    "A single large glowing orb of light floating in dark space then dramatically splitting into five smaller autonomous orbs that fan out in different directions, brilliant light trails connecting them back to the center, explosive particle effects, cinematic slow motion",
    "Five autonomous glowing agents working simultaneously in parallel, each processing its own independent data stream, rhythmic synchronized pulsing between them, dark space with threads of connecting light between all workers, cinematic",
    "Multiple data streams from five separate sources converging dramatically into a central collection point, information merging and combining in a brilliant swirling vortex of cyan and blue light, cinematic dramatic composition",
    "A completed assembly of merged results materializing as a unified holographic report, golden completion glow radiating outward, futuristic dashboard displaying dramatic speedup metrics and success indicators, cinematic triumphant finale",
])

# ── VIDEO 05: VALIDATOR ──
add_clips("video_05_validator", [
    "A futuristic quality control interface with holographic contract documents and JSON schemas floating in dark space, structured data fields glowing with cyan outlines, validation criteria listed in columns of light, cinematic",
    "An automated precision scanning beam sweeping methodically across holographic output data, bright green checkmarks materializing one by one as each validation criterion passes, systematic quality inspection process, cinematic",
    "A dramatic red X flashing on a failed validation check with alarm indicators pulsing, then an amber retry mechanism activating, the output being corrected and rescanned, culminating in a green checkmark of approval, cinematic",
    "All validation checks completing simultaneously with green checkmarks, a golden VERIFIED seal stamping onto the approved output with a burst of light, zero defects counter displayed, triumphant quality assurance completion, cinematic finale",
])

# ── VIDEO 06: FULL SYSTEM ──
add_clips("video_06_full_system", [
    "A massive futuristic command center powering up from total darkness, multiple holographic screens activating one by one around a central console, the room gradually filling with cyan and blue light, cinematic dolly shot moving through the space",
    "A complex data pipeline visualization showing tasks entering from one side and flowing through multiple illuminated processing stages, each stage glowing a different color as data transforms and advances, dark environment, cinematic",
    "Five distinct system modules all operating simultaneously like a coordinated symphony, connected by flowing streams of data, each module pulsing with its own color but synchronized together as one system, cinematic wide shot",
    "A massive holographic dashboard showing all systems green and operational, counters incrementing rapidly, performance metrics climbing, every component connected and healthy, professional futuristic control room, cinematic",
    "Camera dramatically pulling back from the complete integrated system, all five glowing modules visible and connected by flowing light streams, the entire architecture pulsing with coordinated energy in dark space, cinematic epic finale",
])


def main():
    client = RunwayML(api_key=RUNWAY_KEY)
    manifest_path = BASE / "runway_manifest.json"

    # Load existing manifest if any
    existing = {}
    if manifest_path.exists():
        for t in json.loads(manifest_path.read_text()):
            key = f"{t['video']}_{t['clip_idx']}"
            existing[key] = t

    # Phase 1: Submit all clips that don't have tasks yet
    all_tasks = list(existing.values())
    submitted_new = 0

    print(f"Total clips needed: {len(ALL_CLIPS)}")
    print(f"Already submitted: {len(existing)}")

    for video_dir, clip_idx, prompt in ALL_CLIPS:
        key = f"{video_dir}_{clip_idx}"
        out_path = BASE / video_dir / "runway_clips" / f"clip_{clip_idx:02d}.mp4"

        # Skip if already downloaded
        if out_path.exists() and out_path.stat().st_size > 100000:
            print(f"  SKIP (downloaded): {video_dir} clip {clip_idx}")
            continue

        # Skip if already submitted
        if key in existing:
            print(f"  SKIP (submitted): {video_dir} clip {clip_idx}")
            continue

        # Submit new
        clip_dir = BASE / video_dir / "runway_clips"
        clip_dir.mkdir(parents=True, exist_ok=True)

        full_prompt = f"{prompt}. {STYLE}"
        try:
            task = client.text_to_video.create(
                model=MODEL,
                prompt_text=full_prompt,
                ratio="1280:720",
                duration=CLIP_DURATION,
            )
            task_entry = {
                "task_id": task.id,
                "video": video_dir,
                "clip_idx": clip_idx,
                "output_path": str(out_path),
            }
            all_tasks.append(task_entry)
            submitted_new += 1
            print(f"  Submitted: {video_dir} clip {clip_idx} -> {task.id}")
            time.sleep(2)  # Generous rate limit delay
        except Exception as e:
            print(f"  ERROR: {video_dir} clip {clip_idx}: {e}")
            time.sleep(5)

    # Save updated manifest
    with open(manifest_path, "w") as f:
        json.dump(all_tasks, f, indent=2)
    print(f"\nSubmitted {submitted_new} new clips. Total: {len(all_tasks)}")

    # Phase 2: Poll and download all pending clips
    print(f"\n{'='*50}")
    print("Polling for completions...")
    print(f"{'='*50}\n")

    pending = []
    for t in all_tasks:
        out_path = Path(t["output_path"])
        if out_path.exists() and out_path.stat().st_size > 100000:
            continue
        pending.append(t)

    completed = 0
    failed = 0
    total = len(pending)

    while pending:
        still_pending = []
        for t in pending:
            try:
                result = client.tasks.retrieve(t["task_id"])
                data = result.model_dump()
                status = data.get("status", "UNKNOWN")

                if status == "SUCCEEDED":
                    output = data.get("output", [])
                    url = output[0] if isinstance(output, list) and output else output
                    if url:
                        r = requests.get(url, timeout=120)
                        Path(t["output_path"]).write_bytes(r.content)
                        mb = len(r.content) / 1024 / 1024
                        completed += 1
                        print(f"  DONE [{completed}/{total}]: {t['video']} clip {t['clip_idx']} ({mb:.1f} MB)")
                    else:
                        failed += 1
                        print(f"  FAIL (no URL): {t['video']} clip {t['clip_idx']}")

                elif status in ("FAILED", "CANCELLED"):
                    failed += 1
                    failure = data.get("failure", "unknown")
                    print(f"  FAIL: {t['video']} clip {t['clip_idx']}: {failure}")

                else:
                    progress = data.get("progress", 0)
                    still_pending.append(t)

            except Exception as e:
                still_pending.append(t)

        pending = still_pending
        if pending:
            # Find which one is actively running
            active = None
            for t in pending:
                try:
                    result = client.tasks.retrieve(t["task_id"])
                    data = result.model_dump()
                    if data.get("status") == "RUNNING":
                        active = f"{t['video']} clip {t['clip_idx']} ({data.get('progress', 0):.0%})"
                        break
                except:
                    pass
            status_msg = f"Active: {active}" if active else "Queued"
            print(f"  ... waiting: {len(pending)} remaining, {completed} done | {status_msg}")
            time.sleep(15)

    print(f"\n{'='*50}")
    print(f"GENERATION COMPLETE: {completed} downloaded, {failed} failed")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

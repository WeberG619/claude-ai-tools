#!/usr/bin/env python3
"""
Runway ML Cinematic Video Pipeline
Generates professional AI videos using Runway Gen-4.5 + ElevenLabs + FFmpeg.

Usage: python3 runway_pipeline.py [generate|assemble|all]
  generate  — Submit all Runway clip generations and download
  assemble  — Assemble downloaded clips into final videos
  all       — Full pipeline (default)
"""

import sys
import time
import math
import json
import requests
import subprocess
from pathlib import Path

from runwayml import RunwayML

# ── CONFIG ──────────────────────────────────────────────────────────────────
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

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ── VIDEO DEFINITIONS ──────────────────────────────────────────────────────

VIDEOS = [
    # ── VIDEO 01: RETRY LADDER ──
    {
        "dir": "video_01_retry_ladder",
        "clips": [
            "Close-up of a futuristic AI terminal displaying cascading red error codes on holographic screens, a glowing blue strategy ladder diagram materializing beside the errors, dark control room with cyan ambient lighting and volumetric fog, cinematic slow push-in camera",
            "A robotic precision arm making a surgical micro-repair on a glowing circuit board, tiny sparks of cyan light shooting out, ultra-detailed close-up, dark background with blue rim lighting, macro sci-fi cinematography",
            "A vast holographic codebase floating in dark space being completely deconstructed and rebuilt, code blocks dissolving into particles and reforming into new architecture with flowing blue and purple energy connections, cinematic wide shot with dramatic lighting",
            "Multiple luminous pathways branching from a glowing decision node in dark space, camera tracking along one path that blazes bright green while all others fade to dim, particles streaming along the successful route, cinematic",
            "Glowing data particles spiraling into a crystalline neural network brain structure, each node pulsing cyan as knowledge is permanently stored, camera slowly pulling back to reveal the complete memory system, cinematic finale",
        ],
        "segments": [
            ("01_hook", "When my AI agent fails, it doesn't just try the same thing twice."),
            ("02_intro", "It runs a strategy ladder."),
            ("03_quickfix", "First. Quick fix. Minimal change. Two shots at it."),
            ("04_refactor", "If that fails, it reads more context, and refactors the approach."),
            ("05_alternative", "Still failing? Completely different strategy. Alternative solution."),
            ("06_escalate", "And if nothing works, it writes me a detailed failure report, so I'm not starting from zero."),
            ("07_result", "Four strategies. Five max attempts. Fifteen minute hard timeout."),
            ("08_memory", "It logs every attempt, so next time, it skips straight to what worked."),
            ("09_cta", "This is cadre AI. Link in bio."),
        ],
    },

    # ── VIDEO 02: ARCHITECTURE ──
    {
        "dir": "video_02_architecture",
        "clips": [
            "A single brilliant sphere of cyan light activating in the center of complete darkness, holographic rings slowly expanding outward as a futuristic command hub powers up from nothing, volumetric light beams, cinematic slow reveal",
            "Five smaller glowing orbs of different colors cyan green yellow magenta blue emerging and orbiting around a central hub, beams of flowing light connecting them in a constellation network pattern, dark space, cinematic orbit camera",
            "Streams of luminous data particles flowing rapidly between interconnected glowing nodes in a futuristic network, packets of light traveling along pathways at high speed, the network pulsing with synchronized activity, cinematic",
            "A complete interconnected system of glowing nodes and flowing data streams fully operational, holographic dashboard overlays showing live status, camera slowly pulling back to reveal the entire magnificent architecture, cinematic wide shot",
        ],
        "segments": [
            ("01_hook", "Five systems. Zero external dependencies. All running on one machine."),
            ("02_board", "The task board tracks every operation across sessions."),
            ("03_retry", "Adaptive retry escalates strategies when something fails."),
            ("04_checkpoint", "Checkpoints save agent state so nothing is ever lost."),
            ("05_validator", "Output contracts validate every result before delivery."),
            ("06_swarm", "The swarm engine fans out parallel workers for big tasks."),
            ("07_cta", "All open source. cadre AI. Link in bio."),
        ],
    },

    # ── VIDEO 03: CHECKPOINT ──
    {
        "dir": "video_03_checkpoint",
        "clips": [
            "A futuristic glowing progress timeline bar floating in dark space, diamond-shaped checkpoint markers appearing one by one along the line, each checkpoint emitting a brilliant pulse of green light upon activation, holographic particles, cinematic",
            "A crystalline data structure materializing in mid-air, capturing a complete system state as a frozen 3D snapshot, swirling particles suspending in place like digital amber, gold and cyan light illuminating the preservation, cinematic",
            "A futuristic holographic display experiencing a dramatic system crash, the screen fragmenting with red glitches and going dark, then rebooting as checkpoint data streams back in with green restoration light spreading across the interface, cinematic",
            "A seamless system resumption showing progress bars instantly filling from their saved checkpoint positions, holographic interface displaying RESUMED in green light, everything continuing smoothly from exactly where it stopped, cinematic",
        ],
        "segments": [
            ("01_hook", "My AI agent saves its own brain. Here's how."),
            ("02_problem", "Long tasks crash. Sessions timeout. Context fills up."),
            ("03_solution", "After every phase, the agent checkpoints its state."),
            ("04_what", "Files modified. Decisions made. What comes next."),
            ("05_resume", "New session? Resume from the last checkpoint. Full context restored."),
            ("06_never", "Nothing is ever lost. Not a single decision."),
            ("07_cta", "Open source. cadre AI. Link in bio."),
        ],
    },

    # ── VIDEO 04: SWARM ──
    {
        "dir": "video_04_swarm",
        "clips": [
            "A single large glowing orb of light floating in dark space then dramatically exploding outward into five smaller autonomous orbs that fan out in different directions, brilliant light trails connecting them back to the center, explosive particle effects, cinematic slow motion",
            "Five autonomous glowing agents working simultaneously in parallel, each processing its own independent data stream, rhythmic synchronized pulsing between them, dark space with threads of connecting light between all workers, cinematic",
            "Multiple data streams from five separate sources converging dramatically into a central collection point, information merging and combining in a brilliant swirling vortex of cyan and blue light, cinematic dramatic composition",
            "A completed assembly of merged results materializing as a unified holographic report, golden completion glow radiating outward, futuristic dashboard displaying dramatic speedup metrics and success indicators, cinematic triumphant finale",
        ],
        "segments": [
            ("01_hook", "One task. Five AI agents. All working at the same time."),
            ("02_problem", "Big tasks are slow when one agent does everything."),
            ("03_decompose", "The swarm engine decomposes the task into independent pieces."),
            ("04_dispatch", "Each piece goes to a parallel worker. Five agents, five threads."),
            ("05_validate", "Every result is validated against an output contract."),
            ("06_merge", "Results merge back. Deduplicated. Quality-checked."),
            ("07_cta", "Parallel AI agents. Open source. cadre AI."),
        ],
    },

    # ── VIDEO 05: VALIDATOR ──
    {
        "dir": "video_05_validator",
        "clips": [
            "A futuristic quality control interface with holographic contract documents and JSON schemas floating in dark space, structured data fields glowing with cyan outlines, validation criteria listed in columns of light, cinematic",
            "An automated precision scanning beam sweeping methodically across holographic output data, bright green checkmarks materializing one by one as each validation criterion passes, systematic quality inspection process, cinematic",
            "A dramatic red X flashing on a failed validation check with alarm indicators pulsing, then an amber retry mechanism activating, the output being corrected and rescanned, culminating in a green checkmark of approval, cinematic",
            "All validation checks completing simultaneously with green checkmarks, a golden VERIFIED seal stamping onto the approved output with a burst of light, zero defects counter displayed, triumphant quality assurance completion, cinematic finale",
        ],
        "segments": [
            ("01_hook", "My AI doesn't just generate output. It proves it's correct."),
            ("02_problem", "Most AI agents ship broken results. No checks. No contracts."),
            ("03_contracts", "Every output has a contract. JSON schema. Text assertions."),
            ("04_validate", "Missing a required field? Fails. Contains a TODO? Fails."),
            ("05_retry", "Failed validation triggers automatic retry. Up to two attempts."),
            ("06_result", "Every result that reaches you has been validated."),
            ("07_cta", "Output contracts for AI. Open source. cadre AI."),
        ],
    },

    # ── VIDEO 06: FULL SYSTEM ──
    {
        "dir": "video_06_full_system",
        "clips": [
            "A massive futuristic command center powering up from total darkness, multiple holographic screens activating one by one around a central console, the room gradually filling with cyan and blue light, cinematic dolly shot moving through the space",
            "A complex data pipeline visualization showing tasks entering from one side and flowing through multiple illuminated processing stages, each stage glowing a different color as data transforms and advances, dark environment, cinematic",
            "Five distinct system modules all operating simultaneously like a coordinated symphony, connected by flowing streams of data, each module pulsing with its own color but synchronized together as one system, cinematic wide shot",
            "A massive holographic dashboard showing all systems green and operational, counters incrementing rapidly, performance metrics climbing, every component connected and healthy, professional futuristic control room, cinematic",
            "Camera dramatically pulling back from the complete integrated system, all five glowing modules visible and connected by flowing light streams, the entire architecture pulsing with coordinated energy in dark space, cinematic epic finale",
        ],
        "segments": [
            ("01_hook", "This is what happens when you give an AI agent a real engineering system."),
            ("02_flow", "A task comes in. The board picks it up."),
            ("03_execute", "The agent starts working. Checkpoint after every phase."),
            ("04_fail", "Something fails? The retry ladder kicks in."),
            ("05_swarm", "Too big for one agent? The swarm fans out."),
            ("06_validate", "Every output validated. Every result quality-checked."),
            ("07_memory", "It remembers everything. Gets smarter with every run."),
            ("08_cta", "This is cadre AI. All open source. Link in bio."),
        ],
    },
]


# ── HELPERS ─────────────────────────────────────────────────────────────────

def get_duration(path):
    """Get media duration in seconds via ffprobe."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True)
        return float(r.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def escape_ffmpeg(text):
    """Escape text for FFmpeg drawtext filter."""
    return text.replace("\\", "\\\\").replace("'", "'\\\\\\\\''").replace(":", "\\:").replace("%", "%%")


# ── PHASE 1: GENERATE CLIPS ────────────────────────────────────────────────

def generate_clips():
    """Submit all Runway generations, poll, and download clips."""
    client = RunwayML(api_key=RUNWAY_KEY)

    # Submit all tasks
    all_tasks = []
    for video in VIDEOS:
        clip_dir = BASE / video["dir"] / "runway_clips"
        clip_dir.mkdir(parents=True, exist_ok=True)

        for i, prompt in enumerate(video["clips"]):
            out_path = clip_dir / f"clip_{i:02d}.mp4"

            # Skip if already downloaded
            if out_path.exists() and out_path.stat().st_size > 100000:
                print(f"  SKIP (exists): {video['dir']} clip {i}")
                continue

            full_prompt = f"{prompt}. {STYLE}"
            try:
                task = client.text_to_video.create(
                    model=MODEL,
                    prompt_text=full_prompt,
                    ratio="1280:720",
                    duration=CLIP_DURATION,
                )
                all_tasks.append({
                    "task_id": task.id,
                    "video": video["dir"],
                    "clip_idx": i,
                    "output_path": str(out_path),
                })
                print(f"  Submitted: {video['dir']} clip {i} → {task.id}")
                time.sleep(1.5)  # Rate limit between submissions
            except Exception as e:
                print(f"  ERROR submitting {video['dir']} clip {i}: {e}")

    if not all_tasks:
        print("\nAll clips already exist! Skipping generation.")
        return

    print(f"\n{'='*50}")
    print(f"Submitted {len(all_tasks)} clips. Polling for completion...")
    print(f"{'='*50}\n")

    # Save task manifest for resume capability
    manifest_path = BASE / "runway_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(all_tasks, f, indent=2)

    # Poll all tasks
    pending = list(all_tasks)
    completed = 0
    failed = 0

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
                        r = requests.get(url, timeout=60)
                        Path(t["output_path"]).write_bytes(r.content)
                        mb = len(r.content) / 1024 / 1024
                        completed += 1
                        print(f"  ✓ Downloaded: {t['video']} clip {t['clip_idx']} ({mb:.1f} MB) [{completed}/{len(all_tasks)}]")
                    else:
                        failed += 1
                        print(f"  ✗ No output URL: {t['video']} clip {t['clip_idx']}")

                elif status in ("FAILED", "CANCELLED"):
                    failed += 1
                    print(f"  ✗ {status}: {t['video']} clip {t['clip_idx']}: {data.get('failure', 'unknown')}")

                else:
                    progress = data.get("progress", 0)
                    still_pending.append(t)

            except Exception as e:
                still_pending.append(t)

        pending = still_pending
        if pending:
            print(f"  ... {len(pending)} clips still generating, {completed} done, {failed} failed")
            time.sleep(10)

    print(f"\nGeneration complete: {completed} downloaded, {failed} failed")


# ── PHASE 2: ASSEMBLE VIDEOS ───────────────────────────────────────────────

def assemble_video(video):
    """Assemble Runway clips + ElevenLabs audio + captions into final video."""
    vdir = BASE / video["dir"]
    clip_dir = vdir / "runway_clips"
    audio_dir = vdir / "audio"
    audio_path = audio_dir / "full_narration.mp3"

    print(f"\nAssembling: {video['dir']}")

    # Get clips in order
    clips = sorted(clip_dir.glob("clip_*.mp4"))
    if not clips:
        print(f"  No clips found, skipping")
        return

    if not audio_path.exists():
        print(f"  No audio found, skipping")
        return

    audio_dur = get_duration(audio_path)
    print(f"  Clips: {len(clips)}, Audio: {audio_dur:.1f}s")

    # Get individual segment durations for caption timing
    seg_durations = []
    for seg_name, seg_text in video["segments"]:
        seg_file = audio_dir / f"{seg_name}.mp3"
        if seg_file.exists():
            seg_durations.append(get_duration(seg_file))
        else:
            seg_durations.append(audio_dur / len(video["segments"]))

    # Calculate caption start/end times
    captions = []
    current_t = 0.0
    for i, ((seg_name, seg_text), dur) in enumerate(zip(video["segments"], seg_durations)):
        captions.append((current_t, current_t + dur, seg_text))
        current_t += dur

    # Step 1: Scale each clip to 1920x1080 and normalize
    scaled_clips = []
    for i, clip in enumerate(clips):
        scaled = clip_dir / f"scaled_{i:02d}.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(clip),
            "-vf", "scale=1920:1080:flags=lanczos,fps=30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an",
            str(scaled)
        ], capture_output=True)
        if scaled.exists():
            scaled_clips.append(scaled)

    if not scaled_clips:
        print(f"  Scaling failed, skipping")
        return

    # Step 2: Build xfade filter chain for smooth transitions
    total_clip_dur = sum(get_duration(c) for c in scaled_clips)
    xfade_dur = 0.5  # half-second crossfade

    if len(scaled_clips) == 1:
        filter_complex = "[0:v]copy[outv]"
        inputs = ["-i", str(scaled_clips[0])]
    else:
        inputs = []
        for c in scaled_clips:
            inputs.extend(["-i", str(c)])

        # Build xfade chain
        parts = []
        offset = get_duration(scaled_clips[0]) - xfade_dur
        if len(scaled_clips) == 2:
            parts.append(f"[0:v][1:v]xfade=transition=fade:duration={xfade_dur}:offset={offset:.2f}[outv]")
        else:
            # First transition
            parts.append(f"[0:v][1:v]xfade=transition=fade:duration={xfade_dur}:offset={offset:.2f}[v01]")
            for j in range(2, len(scaled_clips)):
                prev_label = f"v{j-2:02d}{j-1:02d}" if j > 2 else "v01"
                offset += get_duration(scaled_clips[j-1]) - xfade_dur
                if j == len(scaled_clips) - 1:
                    parts.append(f"[{prev_label}][{j}:v]xfade=transition=fade:duration={xfade_dur}:offset={offset:.2f}[outv]")
                else:
                    next_label = f"v{j-1:02d}{j:02d}"
                    parts.append(f"[{prev_label}][{j}:v]xfade=transition=fade:duration={xfade_dur}:offset={offset:.2f}[{next_label}]")

        filter_complex = ";".join(parts)

    # Step 3: Calculate speed adjustment to match audio
    effective_clip_dur = total_clip_dur - xfade_dur * (len(scaled_clips) - 1)
    speed_ratio = effective_clip_dur / audio_dur

    # Add speed adjustment and caption overlays
    speed_filter = f"setpts={1/speed_ratio}*PTS" if abs(speed_ratio - 1.0) > 0.02 else ""

    # Build caption drawtext filters
    caption_filters = []
    for start, end, text in captions:
        escaped = escape_ffmpeg(text)
        caption_filters.append(
            f"drawtext=text='{escaped}'"
            f":enable='between(t,{start:.2f},{end:.2f})'"
            f":fontfile={FONT}:fontsize=42:fontcolor=white"
            f":borderw=3:bordercolor=black"
            f":x=(w-text_w)/2:y=h-90"
        )

    # Combine all video filters
    post_filters = []
    if speed_filter:
        post_filters.append(speed_filter)
    post_filters.extend(caption_filters)

    if post_filters:
        filter_complex += f";[outv]{','.join(post_filters)}[finalv]"
        map_video = "[finalv]"
    else:
        map_video = "[outv]"

    # Step 4: Final assembly with audio
    output_landscape = vdir / "final_landscape.mp4"
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", map_video,
        "-map", f"{len(scaled_clips)}:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output_landscape)
    ]

    print(f"  Assembling landscape...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FFmpeg error: {result.stderr[-500:]}")
        # Fallback: simple concat without xfade
        print(f"  Trying simple concat fallback...")
        assemble_simple(video, scaled_clips, audio_path, captions, speed_ratio)
        return

    if output_landscape.exists():
        mb = output_landscape.stat().st_size / 1024 / 1024
        print(f"  Landscape: {output_landscape} ({mb:.1f} MB)")
    else:
        print(f"  Landscape assembly failed")
        return

    # Step 5: Create vertical version
    output_vertical = vdir / "final_vertical.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", str(output_landscape),
        "-vf", "crop=608:1080:656:0,scale=1080:1920:flags=lanczos",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "copy",
        str(output_vertical)
    ], capture_output=True)

    if output_vertical.exists():
        mb = output_vertical.stat().st_size / 1024 / 1024
        print(f"  Vertical: {output_vertical} ({mb:.1f} MB)")

    # Cleanup scaled clips
    for f in clip_dir.glob("scaled_*.mp4"):
        f.unlink()


def assemble_simple(video, clips, audio_path, captions, speed_ratio):
    """Simple fallback assembly without crossfade transitions."""
    vdir = BASE / video["dir"]
    clip_dir = vdir / "runway_clips"

    # Create concat list
    concat_file = clip_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")

    # Concat + speed adjust + captions
    caption_filters = []
    for start, end, text in captions:
        escaped = escape_ffmpeg(text)
        caption_filters.append(
            f"drawtext=text='{escaped}'"
            f":enable='between(t,{start:.2f},{end:.2f})'"
            f":fontfile={FONT}:fontsize=42:fontcolor=white"
            f":borderw=3:bordercolor=black"
            f":x=(w-text_w)/2:y=h-90"
        )

    speed_filter = f"setpts={1/speed_ratio}*PTS" if abs(speed_ratio - 1.0) > 0.02 else ""
    all_filters = [f for f in [speed_filter] + caption_filters if f]
    vf = ",".join(all_filters) if all_filters else "null"

    output = vdir / "final_landscape.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-i", str(audio_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(output)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if output.exists():
        mb = output.stat().st_size / 1024 / 1024
        print(f"  Landscape (simple): {output} ({mb:.1f} MB)")

        # Vertical
        output_v = vdir / "final_vertical.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-i", str(output),
            "-vf", "crop=608:1080:656:0,scale=1080:1920:flags=lanczos",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "copy", str(output_v)
        ], capture_output=True)
    else:
        print(f"  Simple assembly also failed: {result.stderr[-300:]}")

    # Cleanup
    concat_file.unlink(missing_ok=True)


# ── MAIN ────────────────────────────────────────────────────────────────────

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    print("=" * 60)
    print("RUNWAY ML CINEMATIC VIDEO PIPELINE")
    print(f"Model: {MODEL} | Clip Duration: {CLIP_DURATION}s")
    print(f"Videos: {len(VIDEOS)} | Clips per video: {max(len(v['clips']) for v in VIDEOS)}")
    print("=" * 60)

    if mode in ("generate", "all"):
        print("\n── PHASE 1: GENERATING CLIPS ──\n")
        generate_clips()

    if mode in ("assemble", "all"):
        print("\n── PHASE 2: ASSEMBLING VIDEOS ──\n")
        for video in VIDEOS:
            assemble_video(video)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()

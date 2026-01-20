#!/usr/bin/env python3
"""
Video MCP Server - Open Source Video Creation Tools

Provides Claude with video creation capabilities:
- Talking avatars (SadTalker)
- Image generation (Stable Diffusion / Flux)
- Video composition (FFmpeg + MoviePy)
- Voice synthesis (Edge TTS)
- Captions (Whisper)

Author: Claude Workflow System
"""

import asyncio
import json
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import base64

# MCP SDK
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent
from mcp.server.stdio import stdio_server

# Configuration
VIDEO_MCP_DIR = Path(__file__).parent.parent
MODELS_DIR = VIDEO_MCP_DIR / "models"
CACHE_DIR = VIDEO_MCP_DIR / "cache"
OUTPUT_DIR = VIDEO_MCP_DIR / "output"

# Ensure directories exist
MODELS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Initialize MCP server
server = Server("video-mcp")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_timestamp() -> str:
    """Get timestamp for file naming."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def check_tool_available(tool_name: str) -> bool:
    """Check if a command-line tool is available."""
    return shutil.which(tool_name) is not None


def run_command(cmd: List[str], timeout: int = 300) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


async def generate_tts_audio(text: str, output_path: Path, voice: str = "en-US-AndrewNeural") -> bool:
    """Generate TTS audio using Edge TTS."""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(output_path))
        return True
    except Exception as e:
        print(f"TTS Error: {e}")
        return False


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available video tools."""
    return [
        Tool(
            name="video_create_slideshow",
            description="Create a video slideshow from images with narration. Provide images, script text for each slide, and optional background music.",
            inputSchema={
                "type": "object",
                "properties": {
                    "slides": {
                        "type": "array",
                        "description": "Array of slide objects with 'image_path' and 'narration' text",
                        "items": {
                            "type": "object",
                            "properties": {
                                "image_path": {"type": "string"},
                                "narration": {"type": "string"},
                                "duration": {"type": "number", "description": "Override duration in seconds"}
                            },
                            "required": ["image_path", "narration"]
                        }
                    },
                    "output_name": {"type": "string", "description": "Output filename (without extension)"},
                    "voice": {"type": "string", "description": "TTS voice (default: en-US-AndrewNeural)"},
                    "transition": {"type": "string", "enum": ["fade", "none"], "description": "Transition type"},
                    "background_music": {"type": "string", "description": "Path to background music (optional)"}
                },
                "required": ["slides", "output_name"]
            }
        ),
        Tool(
            name="video_create_from_script",
            description="Create a complete video from a JSON script file (like the one used for system overview video).",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_path": {"type": "string", "description": "Path to JSON script file"},
                    "output_name": {"type": "string", "description": "Output filename"},
                    "voice": {"type": "string", "description": "TTS voice to use"}
                },
                "required": ["script_path", "output_name"]
            }
        ),
        Tool(
            name="video_generate_slide",
            description="Generate a single slide image with title, subtitle, and bullet points.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "subtitle": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                    "output_path": {"type": "string"},
                    "style": {"type": "string", "enum": ["dark", "light", "gradient"], "default": "dark"}
                },
                "required": ["title", "output_path"]
            }
        ),
        Tool(
            name="video_synthesize_speech",
            description="Generate speech audio from text using Edge TTS.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to speak"},
                    "output_path": {"type": "string", "description": "Output audio file path"},
                    "voice": {"type": "string", "description": "Voice name (default: en-US-AndrewNeural)"}
                },
                "required": ["text", "output_path"]
            }
        ),
        Tool(
            name="video_compose",
            description="Compose multiple video/image clips into a single video with audio.",
            inputSchema={
                "type": "object",
                "properties": {
                    "clips": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "duration": {"type": "number"},
                                "type": {"type": "string", "enum": ["image", "video"]}
                            }
                        }
                    },
                    "audio_path": {"type": "string", "description": "Audio track to overlay"},
                    "output_path": {"type": "string"},
                    "resolution": {"type": "string", "default": "1920x1080"}
                },
                "required": ["clips", "output_path"]
            }
        ),
        Tool(
            name="video_add_captions",
            description="Add captions/subtitles to a video using Whisper for transcription or from SRT file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_path": {"type": "string"},
                    "output_path": {"type": "string"},
                    "srt_path": {"type": "string", "description": "Optional SRT file (if not provided, will transcribe)"},
                    "style": {"type": "string", "enum": ["bottom", "top", "center"], "default": "bottom"}
                },
                "required": ["video_path", "output_path"]
            }
        ),
        Tool(
            name="video_create_avatar",
            description="Create a talking avatar video from an image and audio using SadTalker (requires SadTalker installed).",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "Path to face image"},
                    "audio_path": {"type": "string", "description": "Path to audio file"},
                    "output_path": {"type": "string"},
                    "preprocess": {"type": "string", "enum": ["crop", "resize", "full"], "default": "crop"},
                    "still_mode": {"type": "boolean", "default": False, "description": "Reduce head motion"},
                    "expression_scale": {"type": "number", "default": 1.0}
                },
                "required": ["image_path", "audio_path", "output_path"]
            }
        ),
        Tool(
            name="video_list_voices",
            description="List all available TTS voices.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="video_get_info",
            description="Get information about a video file (duration, resolution, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_path": {"type": "string"}
                },
                "required": ["video_path"]
            }
        ),
        Tool(
            name="video_extract_audio",
            description="Extract audio track from a video file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_path": {"type": "string"},
                    "output_path": {"type": "string"}
                },
                "required": ["video_path", "output_path"]
            }
        ),
        Tool(
            name="video_concatenate",
            description="Concatenate multiple videos into one.",
            inputSchema={
                "type": "object",
                "properties": {
                    "videos": {"type": "array", "items": {"type": "string"}},
                    "output_path": {"type": "string"},
                    "transition": {"type": "string", "enum": ["none", "fade"], "default": "none"}
                },
                "required": ["videos", "output_path"]
            }
        ),
        Tool(
            name="video_check_dependencies",
            description="Check which video tools are installed and available.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="video_install_guide",
            description="Get installation instructions for video generation tools.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "enum": ["sadtalker", "stable-diffusion", "whisper", "all"]}
                },
                "required": ["tool"]
            }
        )
    ]


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""

    if name == "video_check_dependencies":
        return await check_dependencies()

    elif name == "video_list_voices":
        return await list_voices()

    elif name == "video_synthesize_speech":
        return await synthesize_speech(arguments)

    elif name == "video_generate_slide":
        return await generate_slide(arguments)

    elif name == "video_create_slideshow":
        return await create_slideshow(arguments)

    elif name == "video_create_from_script":
        return await create_from_script(arguments)

    elif name == "video_compose":
        return await compose_video(arguments)

    elif name == "video_get_info":
        return await get_video_info(arguments)

    elif name == "video_extract_audio":
        return await extract_audio(arguments)

    elif name == "video_concatenate":
        return await concatenate_videos(arguments)

    elif name == "video_add_captions":
        return await add_captions(arguments)

    elif name == "video_create_avatar":
        return await create_avatar(arguments)

    elif name == "video_install_guide":
        return await install_guide(arguments)

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def check_dependencies() -> List[TextContent]:
    """Check which dependencies are installed."""
    deps = {
        "ffmpeg": check_tool_available("ffmpeg"),
        "ffprobe": check_tool_available("ffprobe"),
        "python3": check_tool_available("python3"),
    }

    # Check Python packages
    packages = {}
    try:
        import edge_tts
        packages["edge_tts"] = True
    except ImportError:
        packages["edge_tts"] = False

    try:
        from PIL import Image
        packages["pillow"] = True
    except ImportError:
        packages["pillow"] = False

    try:
        import whisper
        packages["whisper"] = True
    except ImportError:
        packages["whisper"] = False

    # Check for SadTalker
    sadtalker_path = MODELS_DIR / "SadTalker"
    packages["sadtalker"] = sadtalker_path.exists()

    result = {
        "system_tools": deps,
        "python_packages": packages,
        "ready_for": []
    }

    if deps["ffmpeg"] and packages["edge_tts"] and packages["pillow"]:
        result["ready_for"].append("slideshow_videos")
        result["ready_for"].append("voice_synthesis")

    if packages["sadtalker"]:
        result["ready_for"].append("talking_avatars")

    if packages["whisper"]:
        result["ready_for"].append("auto_captions")

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def list_voices() -> List[TextContent]:
    """List available TTS voices."""
    voices = {
        "English (US)": [
            "en-US-AndrewNeural (Male, warm)",
            "en-US-GuyNeural (Male, casual)",
            "en-US-DavisNeural (Male, professional)",
            "en-US-JennyNeural (Female, friendly)",
            "en-US-AriaNeural (Female, professional)",
            "en-US-AmandaNeural (Female, warm)",
            "en-US-MichelleNeural (Female, casual)"
        ],
        "English (UK)": [
            "en-GB-RyanNeural (Male)",
            "en-GB-SoniaNeural (Female)"
        ],
        "English (Australia)": [
            "en-AU-WilliamNeural (Male)",
            "en-AU-NatashaNeural (Female)"
        ]
    }

    return [TextContent(type="text", text=json.dumps(voices, indent=2))]


async def synthesize_speech(args: Dict) -> List[TextContent]:
    """Generate speech from text."""
    text = args["text"]
    output_path = Path(args["output_path"])
    voice = args.get("voice", "en-US-AndrewNeural")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    success = await generate_tts_audio(text, output_path, voice)

    if success:
        # Get duration
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", str(output_path)]
        _, duration_str = run_command(cmd)
        duration = float(duration_str.strip()) if duration_str.strip() else 0

        return [TextContent(type="text", text=json.dumps({
            "success": True,
            "output_path": str(output_path),
            "duration_seconds": duration,
            "voice": voice
        }))]
    else:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "Failed to generate speech"
        }))]


async def generate_slide(args: Dict) -> List[TextContent]:
    """Generate a slide image."""
    from PIL import Image, ImageDraw, ImageFont

    title = args["title"]
    subtitle = args.get("subtitle", "")
    bullets = args.get("bullets", [])
    output_path = Path(args["output_path"])
    style = args.get("style", "dark")

    # Style settings
    styles = {
        "dark": {"bg": (20, 25, 35), "title": (100, 200, 255), "text": (220, 220, 220), "accent": (80, 180, 120)},
        "light": {"bg": (245, 245, 250), "title": (30, 60, 120), "text": (50, 50, 50), "accent": (60, 140, 200)},
        "gradient": {"bg": (30, 40, 60), "title": (255, 200, 100), "text": (240, 240, 240), "accent": (255, 150, 100)}
    }
    s = styles.get(style, styles["dark"])

    # Create image
    img = Image.new('RGB', (1920, 1080), s["bg"])
    draw = ImageDraw.Draw(img)

    # Get fonts (fallback to default)
    def get_font(size, bold=False):
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        for p in font_paths:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    title_font = get_font(72, bold=True)
    subtitle_font = get_font(36)
    bullet_font = get_font(32)

    # Draw title
    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    draw.text(((1920 - title_width) // 2, 120), title, font=title_font, fill=s["title"])

    # Draw subtitle
    if subtitle:
        sub_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        sub_width = sub_bbox[2] - sub_bbox[0]
        draw.text(((1920 - sub_width) // 2, 210), subtitle, font=subtitle_font, fill=s["text"])

    # Draw bullets
    y_pos = 320
    for bullet in bullets:
        draw.ellipse([(140, y_pos + 12), (156, y_pos + 28)], fill=s["accent"])
        draw.text((180, y_pos), bullet, font=bullet_font, fill=s["text"])
        y_pos += 60

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, 'PNG')

    return [TextContent(type="text", text=json.dumps({
        "success": True,
        "output_path": str(output_path),
        "resolution": "1920x1080"
    }))]


async def create_slideshow(args: Dict) -> List[TextContent]:
    """Create a video slideshow from slides with narration."""
    slides = args["slides"]
    output_name = args["output_name"]
    voice = args.get("voice", "en-US-AndrewNeural")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        slides_info = []

        for i, slide in enumerate(slides):
            # Generate audio for narration
            audio_path = temp_dir / f"audio_{i:03d}.mp3"
            await generate_tts_audio(slide["narration"], audio_path, voice)

            # Get audio duration
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                   "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)]
            _, duration_str = run_command(cmd)
            duration = float(duration_str.strip()) if duration_str.strip() else 5.0

            slides_info.append({
                "image": slide["image_path"],
                "audio": str(audio_path),
                "duration": slide.get("duration", duration)
            })

        # Create concat files
        video_concat = temp_dir / "video.txt"
        audio_concat = temp_dir / "audio.txt"

        with open(video_concat, 'w') as f:
            for info in slides_info:
                f.write(f"file '{info['image']}'\n")
                f.write(f"duration {info['duration']}\n")
            f.write(f"file '{slides_info[-1]['image']}'\n")

        with open(audio_concat, 'w') as f:
            for info in slides_info:
                f.write(f"file '{info['audio']}'\n")

        # Create video from images
        video_only = temp_dir / "video.mp4"
        run_command([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(video_concat),
            '-vf', 'scale=1920:1080,format=yuv420p',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            str(video_only)
        ])

        # Concatenate audio
        audio_combined = temp_dir / "audio.mp3"
        run_command([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(audio_concat),
            '-c:a', 'libmp3lame', '-q:a', '2',
            str(audio_combined)
        ])

        # Combine video and audio
        output_path = OUTPUT_DIR / f"{output_name}.mp4"
        run_command([
            'ffmpeg', '-y', '-i', str(video_only), '-i', str(audio_combined),
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
            str(output_path)
        ])

        # Get final video info
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
               "-of", "json", str(output_path)]
        _, info_str = run_command(cmd)

        return [TextContent(type="text", text=json.dumps({
            "success": True,
            "output_path": str(output_path),
            "slides_count": len(slides),
            "info": info_str
        }))]

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def create_from_script(args: Dict) -> List[TextContent]:
    """Create video from a JSON script file."""
    script_path = Path(args["script_path"])
    output_name = args["output_name"]
    voice = args.get("voice", "en-US-AndrewNeural")

    if not script_path.exists():
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": f"Script file not found: {script_path}"
        }))]

    with open(script_path) as f:
        script = json.load(f)

    # Convert script format to slideshow format
    slides = []
    for slide_data in script.get("slides", []):
        # Generate slide image
        temp_img = CACHE_DIR / f"slide_{slide_data['id']:02d}.png"

        await generate_slide({
            "title": slide_data.get("title", ""),
            "subtitle": slide_data.get("subtitle", ""),
            "bullets": slide_data.get("bullets", []),
            "output_path": str(temp_img)
        })

        slides.append({
            "image_path": str(temp_img),
            "narration": slide_data.get("narration", "")
        })

    # Create slideshow
    return await create_slideshow({
        "slides": slides,
        "output_name": output_name,
        "voice": voice
    })


async def compose_video(args: Dict) -> List[TextContent]:
    """Compose clips into a video."""
    clips = args["clips"]
    output_path = Path(args["output_path"])
    audio_path = args.get("audio_path")
    resolution = args.get("resolution", "1920x1080")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        concat_file = temp_dir / "concat.txt"

        with open(concat_file, 'w') as f:
            for clip in clips:
                if clip.get("type") == "image":
                    f.write(f"file '{clip['path']}'\n")
                    f.write(f"duration {clip.get('duration', 5)}\n")
                else:
                    f.write(f"file '{clip['path']}'\n")
            # Repeat last for concat
            f.write(f"file '{clips[-1]['path']}'\n")

        video_only = temp_dir / "video.mp4"
        w, h = resolution.split('x')

        run_command([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
            '-vf', f'scale={w}:{h},format=yuv420p',
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            str(video_only)
        ])

        if audio_path:
            run_command([
                'ffmpeg', '-y', '-i', str(video_only), '-i', audio_path,
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                str(output_path)
            ])
        else:
            shutil.copy(video_only, output_path)

        return [TextContent(type="text", text=json.dumps({
            "success": True,
            "output_path": str(output_path)
        }))]

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def get_video_info(args: Dict) -> List[TextContent]:
    """Get video file information."""
    video_path = args["video_path"]

    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration,size,bit_rate:stream=width,height,codec_name,r_frame_rate',
        '-of', 'json', video_path
    ]
    success, output = run_command(cmd)

    if success:
        return [TextContent(type="text", text=output)]
    else:
        return [TextContent(type="text", text=json.dumps({"error": output}))]


async def extract_audio(args: Dict) -> List[TextContent]:
    """Extract audio from video."""
    video_path = args["video_path"]
    output_path = Path(args["output_path"])

    output_path.parent.mkdir(parents=True, exist_ok=True)

    success, output = run_command([
        'ffmpeg', '-y', '-i', video_path,
        '-vn', '-acodec', 'libmp3lame', '-q:a', '2',
        str(output_path)
    ])

    return [TextContent(type="text", text=json.dumps({
        "success": success,
        "output_path": str(output_path) if success else None,
        "error": output if not success else None
    }))]


async def concatenate_videos(args: Dict) -> List[TextContent]:
    """Concatenate multiple videos."""
    videos = args["videos"]
    output_path = Path(args["output_path"])
    transition = args.get("transition", "none")

    temp_dir = Path(tempfile.mkdtemp())

    try:
        concat_file = temp_dir / "concat.txt"

        with open(concat_file, 'w') as f:
            for video in videos:
                f.write(f"file '{video}'\n")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        success, output = run_command([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
            '-c', 'copy', str(output_path)
        ])

        return [TextContent(type="text", text=json.dumps({
            "success": success,
            "output_path": str(output_path) if success else None,
            "videos_combined": len(videos)
        }))]

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


async def add_captions(args: Dict) -> List[TextContent]:
    """Add captions to video."""
    video_path = args["video_path"]
    output_path = Path(args["output_path"])
    srt_path = args.get("srt_path")
    style = args.get("style", "bottom")

    if not srt_path:
        # Auto-transcribe using Whisper
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(video_path)

            # Generate SRT
            srt_path = Path(tempfile.mktemp(suffix=".srt"))
            with open(srt_path, 'w') as f:
                for i, segment in enumerate(result["segments"], 1):
                    start = segment["start"]
                    end = segment["end"]
                    text = segment["text"].strip()

                    start_str = f"{int(start//3600):02d}:{int((start%3600)//60):02d}:{int(start%60):02d},{int((start%1)*1000):03d}"
                    end_str = f"{int(end//3600):02d}:{int((end%3600)//60):02d}:{int(end%60):02d},{int((end%1)*1000):03d}"

                    f.write(f"{i}\n{start_str} --> {end_str}\n{text}\n\n")
        except ImportError:
            return [TextContent(type="text", text=json.dumps({
                "success": False,
                "error": "Whisper not installed. Install with: pip install openai-whisper"
            }))]

    # Add subtitles using FFmpeg
    style_map = {
        "bottom": "Alignment=2",
        "top": "Alignment=6",
        "center": "Alignment=5"
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    success, output = run_command([
        'ffmpeg', '-y', '-i', video_path,
        '-vf', f"subtitles={srt_path}:force_style='{style_map[style]},FontSize=24,PrimaryColour=&Hffffff&'",
        '-c:a', 'copy',
        str(output_path)
    ])

    return [TextContent(type="text", text=json.dumps({
        "success": success,
        "output_path": str(output_path) if success else None,
        "error": output if not success else None
    }))]


async def create_avatar(args: Dict) -> List[TextContent]:
    """Create talking avatar video using SadTalker (runs on Windows for CUDA)."""
    image_path = args["image_path"]
    audio_path = args["audio_path"]
    output_path = Path(args["output_path"])
    preprocess = args.get("preprocess", "crop")
    still_mode = args.get("still_mode", False)
    expression_scale = args.get("expression_scale", 1.0)

    # SadTalker location (Windows path)
    sadtalker_win_path = r"D:\_CLAUDE-TOOLS\video-mcp\models\SadTalker"
    sadtalker_path = MODELS_DIR / "SadTalker"

    if not sadtalker_path.exists():
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "SadTalker not installed. Run the setup script: D:\\_CLAUDE-TOOLS\\video-mcp\\models\\setup_sadtalker.bat"
        }))]

    # Check if venv exists (indicates setup completed)
    venv_path = sadtalker_path / "venv"
    if not venv_path.exists():
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "SadTalker not set up. Run: D:\\_CLAUDE-TOOLS\\video-mcp\\models\\setup_sadtalker.bat"
        }))]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert WSL paths to Windows paths
    def to_win_path(p):
        p = str(p)
        if p.startswith('/mnt/'):
            drive = p[5].upper()
            return f"{drive}:{p[6:]}".replace('/', '\\')
        return p

    win_image = to_win_path(image_path)
    win_audio = to_win_path(audio_path)
    win_output_dir = to_win_path(output_path.parent)

    # Build PowerShell command to run SadTalker on Windows with CUDA
    still_flag = "--still" if still_mode else ""
    ps_cmd = f'''
    cd "{sadtalker_win_path}"
    & .\\venv\\Scripts\\activate.ps1
    python inference.py --driven_audio "{win_audio}" --source_image "{win_image}" --result_dir "{win_output_dir}" --preprocess {preprocess} --expression_scale {expression_scale} {still_flag}
    '''

    try:
        result = subprocess.run(
            ['powershell.exe', '-Command', ps_cmd],
            capture_output=True,
            text=True,
            timeout=600
        )
        success = result.returncode == 0
        output = result.stdout if success else result.stderr

        # Find the generated video file
        generated_video = None
        if success:
            import glob
            videos = glob.glob(str(output_path.parent / "*.mp4"))
            if videos:
                generated_video = max(videos, key=os.path.getctime)

        return [TextContent(type="text", text=json.dumps({
            "success": success,
            "output_path": generated_video,
            "output": output[:500] if output else None,
            "error": result.stderr[:500] if not success and result.stderr else None
        }))]

    except subprocess.TimeoutExpired:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": "SadTalker timed out after 10 minutes"
        }))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({
            "success": False,
            "error": str(e)
        }))]


async def install_guide(args: Dict) -> List[TextContent]:
    """Get installation instructions for video tools."""
    tool = args["tool"]

    guides = {
        "sadtalker": """
# SadTalker Installation Guide

## Prerequisites
- NVIDIA GPU with CUDA support (8GB+ VRAM recommended)
- Anaconda/Miniconda
- Git

## Installation Steps

```bash
# Clone repository
cd /mnt/d/_CLAUDE-TOOLS/video-mcp/models
git clone https://github.com/OpenTalker/SadTalker.git
cd SadTalker

# Create conda environment
conda create -n sadtalker python=3.8
conda activate sadtalker

# Install PyTorch with CUDA
pip install torch==1.12.1+cu113 torchvision==0.13.1+cu113 torchaudio==0.12.1 --extra-index-url https://download.pytorch.org/whl/cu113

# Install FFmpeg
conda install ffmpeg

# Install requirements
pip install -r requirements.txt

# Download pretrained models
bash scripts/download_models.sh
```

## Usage
Once installed, use the `video_create_avatar` tool with an image and audio file.
""",
        "stable-diffusion": """
# Stable Diffusion Installation Guide

## Option 1: ComfyUI (Recommended for video)

```bash
# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Install requirements
pip install -r requirements.txt

# Download models to models/checkpoints/
# Get SD 1.5, SDXL, or SVD from huggingface.co
```

## Option 2: Automatic1111 WebUI

```bash
# Clone repo
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
cd stable-diffusion-webui

# Run (will auto-install dependencies)
./webui.sh
```

## For AnimateDiff (video from images)
Install the AnimateDiff extension in ComfyUI or A1111.
""",
        "whisper": """
# Whisper Installation Guide

```bash
# Install OpenAI Whisper
pip install openai-whisper

# Or install faster-whisper for better performance
pip install faster-whisper
```

## Models
- tiny: Fastest, least accurate
- base: Good balance (recommended)
- small: Better accuracy
- medium: High accuracy
- large: Best accuracy, requires lots of VRAM

Whisper will auto-download models on first use.
""",
        "all": """
# Complete Video Stack Installation

## 1. Core Tools (Required)
```bash
# FFmpeg
sudo apt install ffmpeg

# Python packages
pip install edge-tts pillow moviepy
```

## 2. Speech Recognition (Optional)
```bash
pip install openai-whisper
```

## 3. Talking Avatars (Optional)
See `video_install_guide(tool='sadtalker')` for full instructions.

## 4. AI Image/Video Generation (Optional)
See `video_install_guide(tool='stable-diffusion')` for options.

## Quick Start
After installing core tools, you can already:
- Create slideshows with narration
- Generate slide images
- Synthesize speech
- Compose and edit videos

Advanced features (avatars, AI generation) require additional setup.
"""
    }

    return [TextContent(type="text", text=guides.get(tool, "Unknown tool"))]


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

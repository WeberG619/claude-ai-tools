#!/usr/bin/env python3
"""
AI Render for Revit - Capture current view and enhance with AI.

Usage:
    python render_view.py                    # Default exterior_day preset
    python render_view.py exterior_dusk      # Specific preset
    python render_view.py exterior_day "with palm trees and pool"  # Custom additions
"""

import argparse
import base64
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

# Configuration - load from config.json or environment
CONFIG_FILE = Path(__file__).parent / "config.json"

def load_config():
    """Load configuration from config.json or environment."""
    config = {
        "replicate_api_token": os.environ.get("REPLICATE_API_TOKEN", "r8_HtU11reGPKdxthkdfo8myHuHbwiWLQ92gZbcj"),
        "output_dir": r"D:\temp\ai_renders",
        "revit_http_url": "http://localhost:8765"
    }

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            file_config = json.load(f)
            # Only use file values if not "YOUR_TOKEN_HERE" placeholder
            if file_config.get("replicate_api_token") and file_config["replicate_api_token"] != "YOUR_TOKEN_HERE":
                config["replicate_api_token"] = file_config["replicate_api_token"]
            if file_config.get("output_dir"):
                config["output_dir"] = file_config["output_dir"]
            if file_config.get("revit_http_url"):
                config["revit_http_url"] = file_config["revit_http_url"]

    return config

_config = load_config()
REVIT_HTTP_URL = _config["revit_http_url"]
REPLICATE_API_TOKEN = _config["replicate_api_token"]
OUTPUT_DIR = Path(_config["output_dir"])

# Ensure output dir exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Style presets optimized for architectural renders
PRESETS = {
    "exterior_day": {
        "prompt": "professional architectural photography, daytime exterior, bright sunny day, blue sky with soft clouds, lush green landscaping, manicured lawn, palm trees, tropical plants, photorealistic materials, high-end finishes, sharp shadows, 8k uhd, architectural digest quality, Florida modern architecture, white stucco facade",
        "negative": "sketch, drawing, cartoon, anime, painting, watercolor, blurry, low quality, distorted, deformed, ugly, amateur, oversaturated",
        "strength": 0.45
    },
    "exterior_dusk": {
        "prompt": "professional architectural photography, dusk exterior, golden hour lighting, warm ambient glow from windows, dramatic sky with orange and purple hues, landscape lighting, photorealistic materials, moody atmosphere, 8k uhd, luxury home at sunset",
        "negative": "sketch, drawing, cartoon, daytime, harsh shadows, overexposed, bright sun",
        "strength": 0.50
    },
    "exterior_night": {
        "prompt": "professional architectural photography, nighttime exterior, dramatic interior lighting visible through windows, landscape uplighting, pool lights reflecting, starry sky, high contrast, modern luxury, photorealistic, cinematic lighting, blue hour",
        "negative": "daytime, bright sky, overexposed, cartoon, sketch, harsh lighting",
        "strength": 0.55
    },
    "interior_modern": {
        "prompt": "professional interior photography, modern luxury interior, natural daylight through windows, high-end furniture and finishes, designer decor, potted plants, art on walls, photorealistic materials, warm and inviting, architectural digest, 8k uhd, lived-in feel",
        "negative": "empty, bare, unfinished, cartoon, sketch, dark, gloomy, sterile, cold",
        "strength": 0.50
    },
    "interior_warm": {
        "prompt": "professional interior photography, cozy warm interior, afternoon golden light streaming through windows, rich textures, comfortable furnishings, books and plants, lived-in feel, photorealistic, inviting atmosphere, hygge vibes",
        "negative": "cold, sterile, empty, cartoon, harsh lighting, night, dark",
        "strength": 0.50
    },
    "aerial_site": {
        "prompt": "professional aerial architectural photography, bird's eye view, site plan with lush landscaping, pool, driveway, surrounding context, photorealistic rendering, clear sunny day, drone photography style, sharp details",
        "negative": "fisheye, distorted, blurry, cartoon, sketch, flat, unrealistic",
        "strength": 0.55
    },
    "sketch": {
        "prompt": "architectural concept sketch, hand-drawn style, pencil rendering, professional presentation, clean lines, subtle shading, watercolor wash accents, design development quality",
        "negative": "photorealistic, photograph, digital, 3D render, harsh, messy",
        "strength": 0.70
    },
    "watercolor": {
        "prompt": "architectural watercolor illustration, professional presentation rendering, loose brushwork, soft colors, artistic interpretation, hand-painted quality, design proposal style",
        "negative": "photorealistic, photograph, digital, sharp edges, harsh lines, mechanical",
        "strength": 0.75
    }
}


def capture_revit_view(width: int = 1920, height: int = 1080) -> tuple[str, dict]:
    """Capture the current Revit view via HTTP bridge."""
    print("Capturing current Revit view...")

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            REVIT_HTTP_URL,
            json={
                "method": "captureViewport",
                "params": {
                    "width": width,
                    "height": height
                }
            }
        )

        if response.status_code != 200:
            raise Exception(f"Revit HTTP error: {response.status_code} - {response.text}")

        result = response.json()

        if not result.get("success"):
            raise Exception(f"Capture failed: {result.get('error', 'Unknown error')}")

        data = result.get("result", result)
        file_path = data.get("filePath")
        view_name = data.get("viewName", "Unknown")

        print(f"  View captured: {view_name}")
        print(f"  File: {file_path}")

        return file_path, data


def render_with_replicate(
    image_path: str,
    prompt: str,
    negative_prompt: str,
    strength: float
) -> str:
    """Send image to Replicate for AI enhancement."""

    if not REPLICATE_API_TOKEN:
        raise Exception("REPLICATE_API_TOKEN not set. Get one at https://replicate.com/account/api-tokens")

    print(f"Sending to Replicate (strength={strength:.2f})...")

    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    data_uri = f"data:image/png;base64,{image_data}"

    # Use realistic-vision model (best for architecture)
    model_version = "lucataco/realistic-vision-v5.1:2c8e954decbf70b7607a4414e5785ef9e4de4b8c51d50fb8b8b349160e0ef6bb"

    input_params = {
        "prompt": prompt,
        "image": data_uri,
        "prompt_strength": strength,
        "negative_prompt": negative_prompt,
        "guidance_scale": 7.5,
        "num_inference_steps": 30
    }

    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    with httpx.Client(timeout=120.0) as client:
        # Create prediction
        response = client.post(
            "https://api.replicate.com/v1/predictions",
            headers=headers,
            json={
                "version": model_version.split(":")[-1],
                "input": input_params
            }
        )

        if response.status_code != 201:
            raise Exception(f"Replicate API error: {response.status_code} - {response.text}")

        prediction = response.json()
        prediction_url = prediction["urls"]["get"]

        # Poll for completion
        print("  Processing", end="", flush=True)
        for _ in range(120):  # 2 min timeout
            time.sleep(1)
            print(".", end="", flush=True)

            status_response = client.get(prediction_url, headers=headers)
            status_data = status_response.json()
            status = status_data.get("status")

            if status == "succeeded":
                print(" done!")
                output = status_data.get("output")
                if isinstance(output, list):
                    output_url = output[0]
                else:
                    output_url = output

                # Download result
                img_response = client.get(output_url)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = OUTPUT_DIR / f"render_{timestamp}.png"

                with open(output_path, "wb") as f:
                    f.write(img_response.content)

                return str(output_path)

            elif status == "failed":
                print(" failed!")
                raise Exception(f"Render failed: {status_data.get('error')}")

            elif status == "canceled":
                print(" canceled!")
                raise Exception("Render was canceled")

        raise Exception("Render timed out")


def main():
    parser = argparse.ArgumentParser(description="AI Render for Revit")
    parser.add_argument("preset", nargs="?", default="exterior_day",
                       choices=list(PRESETS.keys()),
                       help="Style preset (default: exterior_day)")
    parser.add_argument("custom", nargs="?", default="",
                       help="Custom additions to the prompt")
    parser.add_argument("--strength", "-s", type=float,
                       help="Override strength (0.0-1.0, lower=more control)")
    parser.add_argument("--width", "-w", type=int, default=1920,
                       help="Capture width (default: 1920)")
    parser.add_argument("--height", type=int, default=1080,
                       help="Capture height (default: 1080)")
    parser.add_argument("--list", "-l", action="store_true",
                       help="List available presets")

    args = parser.parse_args()

    if args.list:
        print("Available presets:")
        print("-" * 40)
        for name, preset in PRESETS.items():
            desc = preset["prompt"][:60] + "..."
            print(f"  {name:16} - {desc}")
        return

    preset = PRESETS[args.preset]

    # Build prompt
    prompt = preset["prompt"]
    if args.custom:
        prompt = f"{prompt}, {args.custom}"

    strength = args.strength if args.strength is not None else preset["strength"]

    print("=" * 60)
    print("AI Render for Revit")
    print("=" * 60)
    print(f"Preset: {args.preset}")
    print(f"Strength: {strength:.2f} (lower = preserve more geometry)")
    if args.custom:
        print(f"Custom: {args.custom}")
    print()

    try:
        # Step 1: Capture view
        image_path, metadata = capture_revit_view(args.width, args.height)

        # Step 2: Render with AI
        output_path = render_with_replicate(
            image_path,
            prompt,
            preset["negative"],
            strength
        )

        print()
        print("=" * 60)
        print("RENDER COMPLETE")
        print("=" * 60)
        print(f"Source: {metadata.get('viewName', 'Unknown')}")
        print(f"Output: {output_path}")
        print()

        # Return path for script usage
        return output_path

    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

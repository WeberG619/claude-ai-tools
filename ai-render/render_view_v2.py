#!/usr/bin/env python3
"""
AI Render for Revit v2 - Using ControlNet for structure preservation.

This version uses ControlNet to lock the geometry from your Revit view
while allowing the AI to enhance materials, lighting, and landscaping.
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

# Configuration
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
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Style presets - optimized for ControlNet (lower strength since structure is preserved)
PRESETS = {
    "exterior_day": {
        "prompt": "professional architectural photography of this exact building, daytime exterior, bright sunny day, blue sky with soft clouds, lush green landscaping around building, palm trees, photorealistic materials and textures, high-end finishes, sharp details, 8k uhd, architectural digest quality, same building design and proportions",
        "negative": "different building, changed architecture, wrong proportions, sketch, cartoon, blurry, distorted, deformed, extra windows, missing windows, different roof",
        "control_strength": 0.85,  # High to preserve structure
        "guidance_scale": 7.5
    },
    "exterior_dusk": {
        "prompt": "professional architectural photography of this exact building, golden hour dusk lighting, warm ambient glow from windows, dramatic orange and purple sky, landscape lighting, photorealistic materials, same building design, 8k uhd",
        "negative": "different building, changed architecture, wrong proportions, daytime, harsh shadows, overexposed",
        "control_strength": 0.85,
        "guidance_scale": 7.5
    },
    "exterior_night": {
        "prompt": "professional architectural photography of this exact building at night, dramatic interior lighting visible through windows, landscape uplighting, pool lights, starry sky, same building design and shape, photorealistic, 8k uhd",
        "negative": "different building, changed architecture, daytime, bright sky, overexposed",
        "control_strength": 0.85,
        "guidance_scale": 7.5
    },
    "interior_modern": {
        "prompt": "professional interior photography of this exact room, natural daylight through windows, high-end furniture, designer decor, plants, photorealistic materials, same room layout and proportions, architectural digest, 8k uhd",
        "negative": "different room, changed layout, cartoon, dark, empty",
        "control_strength": 0.80,
        "guidance_scale": 7.5
    },
    "enhance_only": {
        "prompt": "professional architectural photography of this exact building, photorealistic materials and textures, enhanced lighting, same design same proportions same windows same roof, 8k uhd quality",
        "negative": "different building, changed design, wrong proportions, cartoon, blurry",
        "control_strength": 0.95,  # Very high - minimal changes
        "guidance_scale": 5.0
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


def render_with_controlnet(
    image_path: str,
    prompt: str,
    negative_prompt: str,
    control_strength: float,
    guidance_scale: float
) -> str:
    """
    Render using ControlNet to preserve building structure.
    Uses Canny edge detection to lock geometry.
    """

    if not REPLICATE_API_TOKEN:
        raise Exception("REPLICATE_API_TOKEN not set")

    print(f"Sending to Replicate ControlNet (control_strength={control_strength:.2f})...")
    print("  This preserves your building's exact geometry...")

    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    data_uri = f"data:image/png;base64,{image_data}"

    # Use SDXL ControlNet - better quality, preserves structure via edge detection
    model_version = "lucataco/sdxl-controlnet:06d6fae3b75ab68a28cd2900afa6033166910dd09fd9751047043a5bbb4c184b"

    input_params = {
        "image": data_uri,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "num_inference_steps": 30,
        "condition_scale": control_strength,  # How strongly to follow the structure (0-1)
    }

    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    with httpx.Client(timeout=180.0) as client:
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
        for _ in range(180):  # 3 min timeout
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
                output_path = OUTPUT_DIR / f"render_controlnet_{timestamp}.png"

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
    parser = argparse.ArgumentParser(description="AI Render for Revit v2 (ControlNet)")
    parser.add_argument("preset", nargs="?", default="exterior_day",
                       choices=list(PRESETS.keys()),
                       help="Style preset (default: exterior_day)")
    parser.add_argument("custom", nargs="?", default="",
                       help="Custom additions to the prompt")
    parser.add_argument("--control-strength", "-c", type=float,
                       help="Override control strength (0.0-1.0, higher=more structure preservation)")
    parser.add_argument("--width", "-w", type=int, default=1920,
                       help="Capture width (default: 1920)")
    parser.add_argument("--height", type=int, default=1080,
                       help="Capture height (default: 1080)")
    parser.add_argument("--image", "-i", type=str,
                       help="Use existing image instead of capturing from Revit")
    parser.add_argument("--list", "-l", action="store_true",
                       help="List available presets")

    args = parser.parse_args()

    if args.list:
        print("Available presets:")
        print("-" * 50)
        for name, preset in PRESETS.items():
            strength = preset["control_strength"]
            print(f"  {name:16} - structure preservation: {strength:.0%}")
        return

    preset = PRESETS[args.preset]

    # Build prompt
    prompt = preset["prompt"]
    if args.custom:
        prompt = f"{prompt}, {args.custom}"

    control_strength = args.control_strength if args.control_strength is not None else preset["control_strength"]

    print("=" * 60)
    print("AI Render for Revit v2 (ControlNet)")
    print("=" * 60)
    print(f"Preset: {args.preset}")
    print(f"Structure preservation: {control_strength:.0%}")
    if args.custom:
        print(f"Custom: {args.custom}")
    print()

    try:
        # Step 1: Get image (capture or use provided)
        if args.image:
            image_path = args.image
            metadata = {"viewName": "Manual image"}
            print(f"Using provided image: {image_path}")
        else:
            image_path, metadata = capture_revit_view(args.width, args.height)

        # Step 2: Render with ControlNet
        output_path = render_with_controlnet(
            image_path,
            prompt,
            preset["negative"],
            control_strength,
            preset["guidance_scale"]
        )

        print()
        print("=" * 60)
        print("RENDER COMPLETE")
        print("=" * 60)
        print(f"Source: {metadata.get('viewName', 'Unknown')}")
        print(f"Output: {output_path}")
        print()
        print("The AI preserved your building's geometry while enhancing")
        print("materials, lighting, and adding landscaping.")

        return output_path

    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

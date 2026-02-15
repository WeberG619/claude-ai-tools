#!/usr/bin/env python3
"""
Flux AI Render for Revit - Photorealistic Quality

Uses Black Forest Labs' Flux Pro models for state-of-the-art photorealism.
- Flux Canny Pro: Edge-based structure preservation (clean architectural lines)
- Flux Depth Pro: Depth-based preservation (better for 3D geometry)

Cost: ~$0.05 per render (higher quality than SDXL)
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
    config = {
        "replicate_api_token": os.environ.get("REPLICATE_API_TOKEN", ""),
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

# Flux models
FLUX_MODELS = {
    "canny": {
        "version": "black-forest-labs/flux-canny-pro:835f0372c2cf4b2e494c2b8626288212ea5c2694ccc2e29f00dfb8cbf2a5e0ce",
        "description": "Edge-based - best for clean architectural lines"
    },
    "depth": {
        "version": "black-forest-labs/flux-depth-pro:0e370dce5fdf15aa8b5fe2491474be45628756e8fba97574bfb3bcab46d09fff",
        "description": "Depth-based - best for 3D geometry preservation"
    }
}

# Location profiles for photorealistic prompts
LOCATION_PROFILES = {
    "south_florida": {
        "environment": "South Florida coastal setting, Miami modern architecture",
        "vegetation": "mature royal palm trees, coconut palms, tropical landscaping with bird of paradise, croton plants, bougainvillea hedges, manicured st augustine grass lawn",
        "sky": "clear tropical blue sky with small white cumulus clouds, bright Florida sunshine",
        "atmosphere": "warm humid tropical atmosphere, soft coastal golden hour light",
        "materials": "clean white stucco exterior, impact-resistant hurricane windows, natural stone accents, contemporary metal railings"
    },
    "southwest_desert": {
        "environment": "Arizona Sonoran desert setting, desert contemporary architecture",
        "vegetation": "saguaro cactus, palo verde trees, agave plants, desert xeriscaping with decomposed granite, native desert wildflowers",
        "sky": "deep blue desert sky, dramatic sunset colors with orange and purple",
        "atmosphere": "crisp dry desert light, sharp defined shadows, warm earth tones",
        "materials": "smooth stucco in warm desert tones, rusted corten steel accents, natural stone"
    },
    "southern_california": {
        "environment": "Southern California coastal setting, California contemporary architecture",
        "vegetation": "mediterranean landscaping, mature olive trees, italian cypress, birds of paradise, succulent gardens, ornamental grasses",
        "sky": "california golden hour light, soft blue sky with subtle marine layer",
        "atmosphere": "warm california sunshine, soft diffused coastal light",
        "materials": "clean white stucco, floor-to-ceiling glass, natural wood accents, concrete"
    },
    "default": {
        "environment": "contemporary residential architecture",
        "vegetation": "professional landscaping, mature trees, manicured lawn, ornamental plantings",
        "sky": "clear blue sky with soft clouds, natural daylight",
        "atmosphere": "pleasant natural lighting, professional architectural photography",
        "materials": "high-end exterior finishes, clean modern materials"
    }
}


def build_flux_prompt(location: str, custom: str = "", include_pool: bool = False) -> str:
    """
    Build a detailed photorealistic prompt for Flux.
    Flux works best with detailed, descriptive prompts.
    """
    profile = LOCATION_PROFILES.get(location, LOCATION_PROFILES["default"])

    prompt_parts = [
        "Ultra photorealistic architectural photography",
        "exact same building design and structure as the reference image",
        "preserving all windows, doors, roof lines, and proportions exactly",
        profile["environment"],
        profile["materials"],
        profile["vegetation"],
        profile["sky"],
        profile["atmosphere"],
    ]

    if include_pool:
        prompt_parts.append("luxury infinity edge swimming pool with crystal clear blue water")

    if custom:
        prompt_parts.append(custom)

    prompt_parts.extend([
        "shot on Sony A7R IV, 24mm lens",
        "professional real estate photography",
        "8K resolution, ultra sharp details",
        "natural color grading, no overexposure",
        "balanced exposure, detailed shadows and highlights"
    ])

    return ", ".join(prompt_parts)


def capture_revit_view(width: int = 1920, height: int = 1080) -> tuple[str, dict]:
    """Capture the current Revit view via HTTP bridge."""
    print("Capturing current Revit view...")

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            REVIT_HTTP_URL,
            json={
                "method": "captureViewport",
                "params": {"width": width, "height": height}
            }
        )

        if response.status_code != 200:
            raise Exception(f"Revit HTTP error: {response.status_code}")

        result = response.json()
        if not result.get("success"):
            raise Exception(f"Capture failed: {result.get('error')}")

        data = result.get("result", result)
        print(f"  View: {data.get('viewName', 'Unknown')}")
        return data.get("filePath"), data


def render_with_flux(
    image_path: str,
    prompt: str,
    model_type: str = "depth",
    steps: int = 50,
    guidance: float = 30
) -> str:
    """
    Render using Flux Pro models for photorealistic output.
    """
    if not REPLICATE_API_TOKEN:
        raise Exception("REPLICATE_API_TOKEN not set")

    model_info = FLUX_MODELS[model_type]
    print(f"\nUsing Flux {model_type.title()} Pro")
    print(f"  {model_info['description']}")
    print(f"  Steps: {steps}, Guidance: {guidance}")

    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    data_uri = f"data:image/png;base64,{image_data}"

    input_params = {
        "prompt": prompt,
        "control_image": data_uri,
        "steps": steps,
        "guidance": guidance,
        "output_format": "png",
        "safety_tolerance": 5,  # More permissive for architecture
    }

    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    with httpx.Client(timeout=300.0) as client:
        print("\nSending to Flux API...")
        response = client.post(
            "https://api.replicate.com/v1/predictions",
            headers=headers,
            json={
                "version": model_info["version"].split(":")[-1],
                "input": input_params
            }
        )

        if response.status_code != 201:
            raise Exception(f"API error: {response.status_code} - {response.text}")

        prediction = response.json()
        prediction_url = prediction["urls"]["get"]

        print("Processing", end="", flush=True)
        for i in range(300):  # 5 min timeout
            time.sleep(1)
            if i % 5 == 0:
                print(".", end="", flush=True)

            status_response = client.get(prediction_url, headers=headers)
            status_data = status_response.json()
            status = status_data.get("status")

            if status == "succeeded":
                print(" done!")
                output = status_data.get("output")
                output_url = output[0] if isinstance(output, list) else output

                img_response = client.get(output_url)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = OUTPUT_DIR / f"render_flux_{model_type}_{timestamp}.png"

                with open(output_path, "wb") as f:
                    f.write(img_response.content)

                return str(output_path)

            elif status == "failed":
                print(" failed!")
                raise Exception(f"Render failed: {status_data.get('error')}")

            elif status == "canceled":
                raise Exception("Render was canceled")

        raise Exception("Render timed out")


def main():
    parser = argparse.ArgumentParser(description="Flux AI Render - Photorealistic Quality")
    parser.add_argument("--model", "-m", default="depth",
                       choices=["canny", "depth"],
                       help="Flux model type: canny (edges) or depth (3D geometry)")
    parser.add_argument("--location", "-l", default="south_florida",
                       choices=list(LOCATION_PROFILES.keys()),
                       help="Location profile for environment")
    parser.add_argument("--pool", "-p", action="store_true",
                       help="Add swimming pool")
    parser.add_argument("--custom", "-c", type=str, default="",
                       help="Custom prompt additions")
    parser.add_argument("--steps", type=int, default=50,
                       help="Diffusion steps (15-50, higher=better quality)")
    parser.add_argument("--guidance", type=float, default=30,
                       help="Prompt guidance (1-100, higher=follow prompt more)")
    parser.add_argument("--image", "-i", type=str,
                       help="Use existing image instead of capturing")
    parser.add_argument("--width", "-w", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)

    args = parser.parse_args()

    print("=" * 60)
    print("FLUX AI RENDER - Photorealistic Quality")
    print("=" * 60)
    print(f"Model: Flux {args.model.title()} Pro")
    print(f"Location: {args.location.replace('_', ' ').title()}")
    if args.pool:
        print("Pool: Yes")
    if args.custom:
        print(f"Custom: {args.custom}")
    print()

    try:
        # Get image
        if args.image:
            image_path = args.image
            view_name = "Manual image"
            print(f"Using image: {image_path}")
        else:
            image_path, metadata = capture_revit_view(args.width, args.height)
            view_name = metadata.get("viewName", "Unknown")

        # Build prompt
        prompt = build_flux_prompt(
            location=args.location,
            custom=args.custom,
            include_pool=args.pool
        )

        print(f"\nPrompt preview: {prompt[:100]}...")

        # Render
        output_path = render_with_flux(
            image_path,
            prompt,
            model_type=args.model,
            steps=args.steps,
            guidance=args.guidance
        )

        print()
        print("=" * 60)
        print("RENDER COMPLETE")
        print("=" * 60)
        print(f"Source: {view_name}")
        print(f"Model: Flux {args.model.title()} Pro")
        print(f"Output: {output_path}")
        print(f"Cost: ~$0.05")

        return output_path

    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

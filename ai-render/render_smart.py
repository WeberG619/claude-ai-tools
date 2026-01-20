#!/usr/bin/env python3
"""
Smart AI Render for Revit - Location and Material Aware

Features:
- Queries Revit for project location (address, city, state)
- Builds location-specific prompts (vegetation, sky, atmosphere)
- Detects materials in the model for targeted enhancement
- Uses ControlNet to preserve exact building geometry
"""

import argparse
import base64
import json
import os
import re
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


# =============================================================================
# LOCATION-BASED ENVIRONMENT PROFILES
# =============================================================================

LOCATION_PROFILES = {
    "south_florida": {
        "keywords": ["miami", "fort lauderdale", "boca raton", "palm beach", "broward",
                     "dade", "florida keys", "homestead", "coral gables", "south florida",
                     "fl 33", "fl 34"],  # FL zip codes starting with 33/34
        "vegetation": "mature palm trees, royal palms, coconut palms, tropical landscaping, bird of paradise plants, bougainvillea, hibiscus flowers, croton plants, frangipani, lush green grass, hedge of ficus",
        "sky": "bright tropical blue sky with soft cumulus clouds, high humidity atmosphere, slight golden haze",
        "atmosphere": "warm humid tropical atmosphere, bright Florida sunshine, soft coastal light",
        "extras": "miami modern architecture style, luxury Florida residence",
        "pool": "infinity edge pool with blue water reflecting palm trees",
    },
    "central_florida": {
        "keywords": ["orlando", "tampa", "jacksonville", "gainesville", "ocala", "fl 32"],
        "vegetation": "live oak trees with spanish moss, sabal palms, azaleas, magnolia trees, pine trees, st augustine grass lawn",
        "sky": "blue sky with afternoon thunderhead clouds building, humid atmosphere",
        "atmosphere": "warm subtropical light, slight humidity haze",
        "extras": "florida vernacular architecture",
        "pool": "screened pool enclosure with tropical landscaping",
    },
    "southwest_desert": {
        "keywords": ["phoenix", "scottsdale", "tucson", "arizona", "az 85", "las vegas", "nevada", "nv 89"],
        "vegetation": "desert xeriscaping, saguaro cactus, palo verde trees, agave plants, decomposed granite, native desert plants, minimal lawn, ornamental grasses",
        "sky": "deep blue desert sky, dramatic sunset colors, clear dry atmosphere",
        "atmosphere": "crisp dry desert light, sharp shadows, warm earth tones",
        "extras": "southwest contemporary architecture, desert modern",
        "pool": "negative edge pool overlooking desert landscape",
    },
    "southern_california": {
        "keywords": ["los angeles", "san diego", "orange county", "ca 90", "ca 91", "ca 92", "malibu", "beverly hills", "santa monica"],
        "vegetation": "mediterranean landscaping, olive trees, italian cypress, birds of paradise, succulent gardens, drought-tolerant plants, ornamental grasses, bougainvillea",
        "sky": "california blue sky, golden hour light, slight marine layer",
        "atmosphere": "warm california sunshine, soft coastal light, golden tones",
        "extras": "california contemporary architecture, indoor-outdoor living",
        "pool": "modern rectangular pool with fire features",
    },
    "pacific_northwest": {
        "keywords": ["seattle", "portland", "washington", "oregon", "wa 98", "or 97"],
        "vegetation": "evergreen trees, douglas fir, cedar, japanese maples, rhododendrons, ferns, moss, lush green groundcover",
        "sky": "overcast pacific northwest sky, soft diffused light, dramatic clouds",
        "atmosphere": "cool misty atmosphere, soft natural light, green tones",
        "extras": "northwest modern architecture, natural wood elements",
        "pool": "naturalistic pool with stone surroundings",
    },
    "northeast": {
        "keywords": ["new york", "boston", "connecticut", "new jersey", "massachusetts", "ny 10", "nj 07", "ct 06", "ma 02"],
        "vegetation": "deciduous trees, maple trees, oak trees, boxwood hedges, perennial gardens, manicured lawn, foundation plantings",
        "sky": "clear blue northeast sky, distinct seasons, crisp light",
        "atmosphere": "clear northeast light, defined shadows",
        "extras": "east coast traditional architecture, classic proportions",
        "pool": "traditional rectangular pool with bluestone coping",
    },
    "texas": {
        "keywords": ["houston", "dallas", "austin", "san antonio", "texas", "tx 75", "tx 77", "tx 78"],
        "vegetation": "live oak trees, crape myrtle, mexican feather grass, lantana, texas sage, bermuda grass lawn, agave",
        "sky": "big texas sky, dramatic clouds, intense sunlight",
        "atmosphere": "bright intense texas sun, warm atmosphere",
        "extras": "texas modern architecture, hill country style",
        "pool": "resort-style pool with water features",
    },
    "default": {
        "keywords": [],
        "vegetation": "mature landscaping, ornamental trees, manicured lawn, foundation plantings, seasonal flowers",
        "sky": "blue sky with soft clouds, natural daylight",
        "atmosphere": "pleasant natural lighting, balanced exposure",
        "extras": "contemporary residential architecture",
        "pool": "modern pool with clean lines",
    }
}


# =============================================================================
# MATERIAL ENHANCEMENT PROFILES
# =============================================================================

MATERIAL_ENHANCEMENTS = {
    "stucco": "smooth white stucco walls with subtle texture, clean modern finish",
    "stone": "natural stone veneer with detailed texture, warm earth tones, authentic appearance",
    "brick": "rich red brick with mortar joints, traditional craftsmanship",
    "wood": "natural wood siding with beautiful grain pattern, warm wood tones",
    "glass": "floor-to-ceiling glass windows with slight reflections, clean modern glazing",
    "metal": "brushed metal railings with contemporary finish",
    "concrete": "smooth architectural concrete, modern brutalist finish",
    "tile": "ceramic roof tiles with terracotta warmth",
}


def detect_location(project_info: dict) -> tuple[str, dict]:
    """
    Detect location profile from project info.
    Returns (profile_name, profile_dict)
    """
    # Extract address components
    address = project_info.get("address", "").lower()
    city = project_info.get("city", "").lower()
    state = project_info.get("state", "").lower()
    zip_code = project_info.get("zip", "").lower()

    # Combine for matching
    location_text = f"{address} {city} {state} {zip_code}"

    # Try to match a profile
    for profile_name, profile in LOCATION_PROFILES.items():
        if profile_name == "default":
            continue
        for keyword in profile["keywords"]:
            if keyword.lower() in location_text:
                print(f"  Detected location: {profile_name.replace('_', ' ').title()}")
                return profile_name, profile

    # Default fallback
    print("  Using default location profile")
    return "default", LOCATION_PROFILES["default"]


def detect_materials(materials_list: list) -> list[str]:
    """
    Detect materials from Revit material list and return enhancement prompts.
    """
    enhancements = []
    materials_text = " ".join([m.lower() for m in materials_list])

    for material, enhancement in MATERIAL_ENHANCEMENTS.items():
        if material in materials_text:
            enhancements.append(enhancement)
            print(f"  Detected material: {material}")

    return enhancements


def get_project_info(client: httpx.Client) -> dict:
    """Get project information from Revit."""
    print("Querying project location...")

    try:
        response = client.post(
            REVIT_HTTP_URL,
            json={"method": "getProjectInfo"}
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                info = result.get("result", result)
                print(f"  Project: {info.get('name', 'Unknown')}")
                if info.get("address"):
                    print(f"  Address: {info.get('address')}")
                return info
    except Exception as e:
        print(f"  Could not get project info: {e}")

    return {}


def get_project_materials(client: httpx.Client) -> list[str]:
    """Get list of materials used in the project."""
    print("Detecting materials...")

    try:
        response = client.post(
            REVIT_HTTP_URL,
            json={"method": "getMaterials", "params": {"limit": 50}}
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                materials = result.get("result", {}).get("materials", [])
                return [m.get("name", "") for m in materials if m.get("name")]
    except Exception as e:
        print(f"  Could not get materials: {e}")

    return []


def capture_revit_view(client: httpx.Client, width: int = 1920, height: int = 1080) -> tuple[str, dict]:
    """Capture the current Revit view."""
    print("Capturing current Revit view...")

    response = client.post(
        REVIT_HTTP_URL,
        json={
            "method": "captureViewport",
            "params": {"width": width, "height": height}
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
    return file_path, data


def build_smart_prompt(
    base_style: str,
    location_profile: dict,
    material_enhancements: list[str],
    custom_additions: str = "",
    include_pool: bool = False
) -> tuple[str, str]:
    """
    Build an intelligent prompt based on location and materials.
    Returns (prompt, negative_prompt)
    """

    # Base architectural prompt
    prompt_parts = [
        "professional architectural photography of this exact building",
        f"{location_profile['atmosphere']}",
        f"{location_profile['sky']}",
        f"{location_profile['vegetation']}",
    ]

    # Add material enhancements
    if material_enhancements:
        prompt_parts.extend(material_enhancements)

    # Add style extras
    prompt_parts.append(location_profile["extras"])

    # Add pool if requested
    if include_pool:
        prompt_parts.append(location_profile["pool"])

    # Add custom additions
    if custom_additions:
        prompt_parts.append(custom_additions)

    # Quality suffixes
    prompt_parts.extend([
        "same building design and proportions",
        "photorealistic materials and textures",
        "8k uhd quality",
        "architectural digest photography"
    ])

    prompt = ", ".join(prompt_parts)

    # Negative prompt
    negative = "different building, changed architecture, wrong proportions, different roof shape, extra windows, missing windows, cartoon, sketch, blurry, distorted, deformed, ugly, low quality"

    return prompt, negative


def render_with_controlnet(
    image_path: str,
    prompt: str,
    negative_prompt: str,
    control_strength: float = 0.85
) -> str:
    """Render using SDXL ControlNet."""

    if not REPLICATE_API_TOKEN:
        raise Exception("REPLICATE_API_TOKEN not set")

    print(f"\nSending to AI (structure preservation: {control_strength:.0%})...")

    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')

    data_uri = f"data:image/png;base64,{image_data}"

    model_version = "lucataco/sdxl-controlnet:06d6fae3b75ab68a28cd2900afa6033166910dd09fd9751047043a5bbb4c184b"

    input_params = {
        "image": data_uri,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "num_inference_steps": 35,  # Slightly more for better quality
        "condition_scale": control_strength,
    }

    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }

    with httpx.Client(timeout=180.0) as client:
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

        print("Processing", end="", flush=True)
        for _ in range(180):
            time.sleep(1)
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
                output_path = OUTPUT_DIR / f"render_smart_{timestamp}.png"

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
    parser = argparse.ArgumentParser(description="Smart AI Render for Revit")
    parser.add_argument("--style", "-s", default="day",
                       choices=["day", "dusk", "night"],
                       help="Time of day style")
    parser.add_argument("--pool", "-p", action="store_true",
                       help="Add pool to the scene")
    parser.add_argument("--custom", "-c", type=str, default="",
                       help="Custom additions to the prompt")
    parser.add_argument("--location", "-l", type=str, default="",
                       help="Override location (e.g., 'south_florida', 'southwest_desert')")
    parser.add_argument("--strength", type=float, default=0.85,
                       help="Structure preservation (0.7-0.95, higher=more preservation)")
    parser.add_argument("--image", "-i", type=str,
                       help="Use existing image instead of capturing from Revit")
    parser.add_argument("--width", "-w", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)

    args = parser.parse_args()

    print("=" * 60)
    print("SMART AI RENDER FOR REVIT")
    print("=" * 60)
    print()

    try:
        with httpx.Client(timeout=30.0) as client:
            # Get project info for location detection
            if args.location:
                # Manual override
                profile_name = args.location.lower().replace(" ", "_")
                location_profile = LOCATION_PROFILES.get(profile_name, LOCATION_PROFILES["default"])
                print(f"Using specified location: {profile_name}")
            else:
                # Auto-detect from Revit project
                project_info = get_project_info(client)
                profile_name, location_profile = detect_location(project_info)

            # Get materials from project
            materials = get_project_materials(client)
            material_enhancements = detect_materials(materials)

            # Capture or use provided image
            if args.image:
                image_path = args.image
                view_name = "Manual image"
                print(f"\nUsing provided image: {image_path}")
            else:
                image_path, metadata = capture_revit_view(client, args.width, args.height)
                view_name = metadata.get("viewName", "Unknown")

        # Build smart prompt
        print("\nBuilding location-aware prompt...")
        prompt, negative = build_smart_prompt(
            base_style=args.style,
            location_profile=location_profile,
            material_enhancements=material_enhancements,
            custom_additions=args.custom,
            include_pool=args.pool
        )

        print(f"\nLocation: {profile_name.replace('_', ' ').title()}")
        print(f"Style: {args.style}")
        if args.pool:
            print("Pool: Yes")
        if args.custom:
            print(f"Custom: {args.custom}")

        # Render
        output_path = render_with_controlnet(
            image_path,
            prompt,
            negative,
            args.strength
        )

        print()
        print("=" * 60)
        print("RENDER COMPLETE")
        print("=" * 60)
        print(f"Source: {view_name}")
        print(f"Location: {profile_name.replace('_', ' ').title()}")
        print(f"Output: {output_path}")

        return output_path

    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

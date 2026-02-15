#!/usr/bin/env python3
"""
Revit AI Render - Scene-Aware Photorealistic Rendering

Connects to RevitMCPBridge2026 via named pipes to:
1. Export clean view images (Realistic mode, no annotations)
2. Analyze scene materials, colors, and room types
3. Build accurate prompts from actual Revit data
4. Render with Flux Pro (depth or canny) preserving geometry

Replaces the broken screenshot-and-guess workflow.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# PowerShell Bridge
sys.path.insert(0, "/mnt/d/_CLAUDE-TOOLS/powershell-bridge")
try:
    from client import run_powershell as _ps_bridge
    _HAS_BRIDGE = True
except ImportError:
    _HAS_BRIDGE = False

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: pip install httpx")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CONFIG_FILE = Path(__file__).parent / "config.json"

def load_config():
    config = {
        "replicate_api_token": os.environ.get("REPLICATE_API_TOKEN", ""),
        "output_dir": r"D:\temp\ai_renders",
    }
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            file_config = json.load(f)
            if file_config.get("replicate_api_token") and file_config["replicate_api_token"] != "YOUR_TOKEN_HERE":
                config["replicate_api_token"] = file_config["replicate_api_token"]
            if file_config.get("output_dir"):
                config["output_dir"] = file_config["output_dir"]
    return config

_config = load_config()
REPLICATE_API_TOKEN = _config["replicate_api_token"]
OUTPUT_DIR = Path(_config["output_dir"])
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

# ---------------------------------------------------------------------------
# Interior prompt templates by room type
# ---------------------------------------------------------------------------

INTERIOR_TEMPLATES = {
    "bathroom": {
        "prefix": "Ultra photorealistic luxury bathroom interior",
        "lighting": "soft diffused vanity lighting, warm ambient glow",
        "atmosphere": "spa-like atmosphere, clean and modern",
        "camera": "wide angle interior architectural photograph",
    },
    "kitchen": {
        "prefix": "Ultra photorealistic modern kitchen interior",
        "lighting": "bright task lighting, under-cabinet LED strips, pendant lights",
        "atmosphere": "clean chef's kitchen, inviting and functional",
        "camera": "wide angle interior architectural photograph",
    },
    "living room": {
        "prefix": "Ultra photorealistic living room interior",
        "lighting": "warm natural light from windows, soft ambient fixtures",
        "atmosphere": "comfortable and elegant living space",
        "camera": "wide angle interior photograph, eye-level perspective",
    },
    "bedroom": {
        "prefix": "Ultra photorealistic bedroom interior",
        "lighting": "soft warm ambient lighting, natural window light",
        "atmosphere": "serene and restful bedroom retreat",
        "camera": "wide angle interior photograph",
    },
    "office": {
        "prefix": "Ultra photorealistic modern office interior",
        "lighting": "balanced task and ambient lighting, natural daylight",
        "atmosphere": "professional productive workspace",
        "camera": "wide angle interior architectural photograph",
    },
    "reception": {
        "prefix": "Ultra photorealistic reception area interior",
        "lighting": "dramatic architectural lighting, feature wall illumination",
        "atmosphere": "impressive professional first impression",
        "camera": "wide angle interior photograph, eye-level",
    },
    "dining room": {
        "prefix": "Ultra photorealistic dining room interior",
        "lighting": "warm pendant or chandelier lighting over table",
        "atmosphere": "elegant dining atmosphere",
        "camera": "wide angle interior photograph",
    },
    "conference room": {
        "prefix": "Ultra photorealistic conference room interior",
        "lighting": "balanced overhead and natural lighting",
        "atmosphere": "professional meeting space",
        "camera": "wide angle interior photograph",
    },
    "hallway": {
        "prefix": "Ultra photorealistic hallway interior",
        "lighting": "even corridor lighting, accent wall sconces",
        "atmosphere": "clean well-lit circulation space",
        "camera": "one-point perspective interior photograph",
    },
    "medical exam room": {
        "prefix": "Ultra photorealistic medical exam room interior",
        "lighting": "bright clinical lighting, balanced color temperature",
        "atmosphere": "clean clinical healthcare environment",
        "camera": "wide angle interior photograph",
    },
    "retail space": {
        "prefix": "Ultra photorealistic retail space interior",
        "lighting": "bright display lighting, accent spotlights",
        "atmosphere": "inviting commercial retail space",
        "camera": "wide angle interior photograph",
    },
    "default": {
        "prefix": "Ultra photorealistic interior photograph",
        "lighting": "balanced natural and artificial lighting",
        "atmosphere": "well-designed interior space",
        "camera": "wide angle interior architectural photograph",
    },
}

# Exterior location profiles (ported from render_flux.py)
LOCATION_PROFILES = {
    "south_florida": {
        "environment": "South Florida coastal setting, Miami modern architecture",
        "vegetation": "mature royal palm trees, coconut palms, tropical landscaping with bird of paradise, bougainvillea",
        "sky": "clear tropical blue sky with small white cumulus clouds, bright Florida sunshine",
        "atmosphere": "warm humid tropical atmosphere, soft coastal golden hour light",
    },
    "southwest_desert": {
        "environment": "Arizona Sonoran desert setting, desert contemporary architecture",
        "vegetation": "saguaro cactus, palo verde trees, agave plants, desert xeriscaping",
        "sky": "deep blue desert sky, dramatic sunset colors",
        "atmosphere": "crisp dry desert light, sharp defined shadows",
    },
    "southern_california": {
        "environment": "Southern California coastal setting, California contemporary",
        "vegetation": "mediterranean landscaping, olive trees, italian cypress, succulent gardens",
        "sky": "california golden hour light, soft blue sky",
        "atmosphere": "warm california sunshine, soft diffused coastal light",
    },
    "default": {
        "environment": "contemporary residential architecture",
        "vegetation": "professional landscaping, mature trees, manicured lawn",
        "sky": "clear blue sky with soft clouds, natural daylight",
        "atmosphere": "pleasant natural lighting, professional architectural photography",
    },
}


# ---------------------------------------------------------------------------
# Revit Named Pipe Bridge (WSL -> Windows PowerShell -> Named Pipe)
# ---------------------------------------------------------------------------

class RevitBridge:
    """Connects to RevitMCPBridge2026 via named pipes.
    Since we run in WSL, we shell out to powershell.exe to access Windows pipes."""

    PIPE_NAME = "RevitMCPBridge2026"

    def _call_pipe(self, method: str, params: dict = None) -> dict:
        """Send a JSON request through the named pipe via PowerShell."""
        request = json.dumps({"method": method, "params": params or {}})
        # Escape for PowerShell single-quoted string
        escaped = request.replace("'", "''")

        ps_script = f"""
$pipeName = '{self.PIPE_NAME}'
$pipe = New-Object System.IO.Pipes.NamedPipeClientStream('.', $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
$pipe.Connect(10000)
$writer = New-Object System.IO.StreamWriter($pipe)
$reader = New-Object System.IO.StreamReader($pipe)
$writer.AutoFlush = $true
$writer.WriteLine('{escaped}')
$response = $reader.ReadLine()
$pipe.Close()
Write-Output $response
"""
        if _HAS_BRIDGE:
            result = _ps_bridge(ps_script, timeout=60)
        else:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, timeout=60
            )

        if result.returncode != 0:
            raise ConnectionError(f"Pipe call failed: {result.stderr.strip()}")

        output = result.stdout.strip()
        if not output:
            raise ConnectionError("Empty response from Revit pipe")

        return json.loads(output)

    def export_view_for_render(self, width: int = 2048, view_id: int = None) -> dict:
        """Export clean view image + scene analysis in one call."""
        params = {"width": width}
        if view_id is not None:
            params["viewId"] = str(view_id)
        response = self._call_pipe("exportViewForRender", params)
        if not response.get("success"):
            raise RuntimeError(f"exportViewForRender failed: {response.get('error')}")
        return response["result"]

    def get_scene_description(self, view_id: int = None) -> dict:
        """Get scene type, materials, and suggested prompt."""
        params = {}
        if view_id is not None:
            params["viewId"] = str(view_id)
        response = self._call_pipe("getSceneDescription", params)
        if not response.get("success"):
            raise RuntimeError(f"getSceneDescription failed: {response.get('error')}")
        return response["result"]

    def get_view_materials(self, view_id: int = None) -> dict:
        """Get material data for prompt building."""
        params = {}
        if view_id is not None:
            params["viewId"] = str(view_id)
        response = self._call_pipe("getViewMaterials", params)
        if not response.get("success"):
            raise RuntimeError(f"getViewMaterials failed: {response.get('error')}")
        return response["result"]


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------

def build_prompt_from_scene(scene_data: dict, overrides: dict = None, location: str = None) -> str:
    """Build a Flux prompt from Revit scene analysis data.

    For interiors: uses room-type templates + actual materials.
    For exteriors: uses location profile + actual materials.
    Overrides let you swap specific materials.
    """
    scene_type = scene_data.get("sceneType", "interior")
    room_type = scene_data.get("roomType", "default")
    suggested = scene_data.get("suggestedPrompt", "")

    # If we have overrides, modify the suggested prompt
    if overrides and suggested:
        for key, value in overrides.items():
            # Replace material descriptions for specific categories
            # e.g., "walls=white marble" replaces the wall material description
            key_lower = key.lower()
            suggested_lower = suggested.lower()
            # Find and replace category descriptions
            for pattern in [f"{key_lower} ", f"{key_lower}:"]:
                idx = suggested_lower.find(pattern)
                if idx != -1:
                    # Find the next comma or end
                    end = suggested.find(",", idx)
                    if end == -1:
                        end = len(suggested)
                    old_part = suggested[idx:end]
                    suggested = suggested.replace(old_part, f"{key_lower} {value}")
                    break
        return suggested

    if suggested:
        return suggested

    # Fallback: build from templates
    if scene_type == "interior":
        template = INTERIOR_TEMPLATES.get(room_type, INTERIOR_TEMPLATES["default"])
        parts = [
            template["prefix"],
            scene_data.get("sceneDescription", ""),
            template["lighting"],
            template["atmosphere"],
            "preserving exact room geometry and proportions",
            template["camera"],
            "8K resolution, Architectural Digest quality",
        ]
    else:
        profile = LOCATION_PROFILES.get(location or "default", LOCATION_PROFILES["default"])
        parts = [
            "Ultra photorealistic exterior architectural photography",
            "exact same building design and structure as reference",
            scene_data.get("sceneDescription", ""),
            profile["environment"],
            profile["vegetation"],
            profile["sky"],
            profile["atmosphere"],
            "preserving all windows, doors, roof lines, and proportions exactly",
            "8K resolution, professional real estate photography",
        ]

    parts = [p for p in parts if p]
    return ", ".join(parts)


def parse_overrides(override_str: str) -> dict:
    """Parse override string like 'walls=white marble, floor=dark walnut'."""
    if not override_str:
        return {}
    result = {}
    for pair in override_str.split(","):
        pair = pair.strip()
        if "=" in pair:
            key, value = pair.split("=", 1)
            result[key.strip()] = value.strip()
    return result


# ---------------------------------------------------------------------------
# Flux Pro Rendering (ported from render_flux.py)
# ---------------------------------------------------------------------------

def render_with_flux(
    image_path: str,
    prompt: str,
    model_type: str = "depth",
    steps: int = 50,
    guidance: float = 30,
) -> str:
    """Render using Flux Pro models via Replicate API."""
    if not REPLICATE_API_TOKEN:
        raise RuntimeError("REPLICATE_API_TOKEN not set. Check config.json or env var.")

    model_info = FLUX_MODELS[model_type]
    print(f"\nUsing Flux {model_type.title()} Pro")
    print(f"  {model_info['description']}")
    print(f"  Steps: {steps}, Guidance: {guidance}")

    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    data_uri = f"data:image/png;base64,{image_data}"

    input_params = {
        "prompt": prompt,
        "control_image": data_uri,
        "steps": steps,
        "guidance": guidance,
        "output_format": "png",
        "safety_tolerance": 5,
    }

    headers = {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=300.0) as client:
        print("\nSending to Flux API...")
        response = client.post(
            "https://api.replicate.com/v1/predictions",
            headers=headers,
            json={
                "version": model_info["version"].split(":")[-1],
                "input": input_params,
            },
        )

        if response.status_code != 201:
            raise RuntimeError(f"Replicate API error: {response.status_code} - {response.text}")

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
                output_path = OUTPUT_DIR / f"render_{model_type}_{timestamp}.png"

                with open(output_path, "wb") as f:
                    f.write(img_response.content)

                return str(output_path)

            elif status == "failed":
                print(" failed!")
                raise RuntimeError(f"Render failed: {status_data.get('error')}")

            elif status == "canceled":
                raise RuntimeError("Render was canceled")

        raise RuntimeError("Render timed out (5 min)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Revit AI Render - Scene-aware photorealistic rendering via Flux Pro",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python render_revit.py                             # Auto: capture + analyze + render
  python render_revit.py --image path.png            # Use existing image, get scene from Revit
  python render_revit.py --image path.png --prompt "text"  # Manual image + manual prompt
  python render_revit.py --override "walls=white marble, floor=dark walnut"
  python render_revit.py --model canny               # Use edge-based model
  python render_revit.py --guidance 50                # More prompt adherence
  python render_revit.py --scene-only                 # Just print scene data, no render
""",
    )
    parser.add_argument("--image", "-i", type=str,
                        help="Use existing image instead of exporting from Revit")
    parser.add_argument("--model", "-m", default="depth",
                        choices=["canny", "depth"],
                        help="Flux model: canny (edges) or depth (3D geometry)")
    parser.add_argument("--override", "-o", type=str, default="",
                        help="Material overrides: 'walls=marble, floor=walnut'")
    parser.add_argument("--prompt", "-p", type=str, default="",
                        help="Manual prompt (bypasses scene analysis)")
    parser.add_argument("--location", "-l", default="default",
                        choices=list(LOCATION_PROFILES.keys()),
                        help="Exterior location profile")
    parser.add_argument("--steps", type=int, default=50,
                        help="Diffusion steps (15-50)")
    parser.add_argument("--guidance", "-g", type=float, default=30,
                        help="Prompt guidance (1-100)")
    parser.add_argument("--width", "-w", type=int, default=2048,
                        help="Export image width in pixels")
    parser.add_argument("--view-id", type=int, default=None,
                        help="Specific Revit view ID to capture")
    parser.add_argument("--scene-only", action="store_true",
                        help="Only print scene analysis, don't render")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show prompt without rendering")

    args = parser.parse_args()

    print("=" * 60)
    print("REVIT AI RENDER - Scene-Aware Photorealistic Rendering")
    print("=" * 60)

    bridge = RevitBridge()
    overrides = parse_overrides(args.override)
    image_path = None
    scene_data = None

    # Step 1: Get image + scene data
    if args.image:
        image_path = args.image
        print(f"Using image: {image_path}")

        if not args.prompt:
            # Still get scene data from Revit for prompt building
            try:
                print("Getting scene data from Revit...")
                scene_data = bridge.get_scene_description(args.view_id)
            except Exception as e:
                print(f"  Could not get scene data: {e}")
                print("  Using generic prompt.")
    else:
        # Full pipeline: export + analyze
        print("Exporting view from Revit...")
        result = bridge.export_view_for_render(width=args.width, view_id=args.view_id)
        image_path = result["imagePath"]
        scene_data = result
        print(f"  View: {result.get('viewName', 'Unknown')}")
        print(f"  Scene: {result.get('sceneType', 'unknown')} - {result.get('roomType', '')}")
        print(f"  Image: {image_path}")

    # Step 2: Scene-only mode
    if args.scene_only:
        if scene_data:
            print("\n--- Scene Analysis ---")
            print(json.dumps(scene_data, indent=2))
        else:
            print("No scene data available.")
        return

    # Step 3: Build prompt
    if args.prompt:
        prompt = args.prompt
        print(f"\nUsing manual prompt.")
    elif scene_data:
        prompt = build_prompt_from_scene(scene_data, overrides, args.location)
        print(f"\nScene type: {scene_data.get('sceneType', 'unknown')}")
        print(f"Room type: {scene_data.get('roomType', 'unknown')}")
    else:
        # Fallback generic prompt
        prompt = (
            "Ultra photorealistic architectural photograph, "
            "preserving exact geometry and proportions, "
            "natural lighting, 8K resolution"
        )

    print(f"\nPrompt: {prompt[:120]}...")
    if overrides:
        print(f"Overrides: {overrides}")

    # Step 4: Dry run
    if args.dry_run:
        print("\n--- DRY RUN ---")
        print(f"Full prompt: {prompt}")
        print(f"Image: {image_path}")
        print(f"Model: Flux {args.model.title()} Pro")
        return

    # Step 5: Render
    if not image_path or not os.path.exists(image_path):
        print(f"\nERROR: Image not found: {image_path}")
        sys.exit(1)

    output_path = render_with_flux(
        image_path=image_path,
        prompt=prompt,
        model_type=args.model,
        steps=args.steps,
        guidance=args.guidance,
    )

    print()
    print("=" * 60)
    print("RENDER COMPLETE")
    print("=" * 60)
    print(f"Model:  Flux {args.model.title()} Pro")
    print(f"Output: {output_path}")
    print(f"Cost:   ~$0.05")

    return output_path


if __name__ == "__main__":
    main()

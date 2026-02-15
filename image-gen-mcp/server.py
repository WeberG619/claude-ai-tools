#!/usr/bin/env python3
"""
Image Generation MCP Server
Uses Replicate API to generate, enhance, and render images.
Includes Flux Pro models for photorealistic architectural rendering.
"""

import asyncio
import os
import base64
import httpx
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("image-gen")

# Replicate API configuration
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
REPLICATE_API_URL = "https://api.replicate.com/v1"

# Output directory for generated images
OUTPUT_DIR = Path(os.environ.get("IMAGE_OUTPUT_DIR", "/mnt/d/temp/ai_renders"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Available models with their Replicate identifiers
MODELS = {
    "flux-pro": {
        "id": "black-forest-labs/flux-pro",
        "description": "Flux Pro - highest quality text-to-image generation",
        "supports_img2img": False
    },
    "flux-schnell": {
        "id": "black-forest-labs/flux-schnell",
        "description": "Fast, high-quality image generation (recommended for speed)",
        "supports_img2img": False
    },
    "flux-dev": {
        "id": "black-forest-labs/flux-dev",
        "description": "Higher quality FLUX model (slower but better)",
        "supports_img2img": False
    },
    "flux-canny-pro": {
        "id": "black-forest-labs/flux-canny-pro",
        "description": "Flux Canny Pro - edge-based structure preservation, best for clean architectural lines",
        "supports_img2img": True,
        "control_model": True
    },
    "flux-depth-pro": {
        "id": "black-forest-labs/flux-depth-pro",
        "description": "Flux Depth Pro - depth-based preservation, best for 3D geometry",
        "supports_img2img": True,
        "control_model": True
    },
    "sdxl": {
        "id": "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
        "description": "Stable Diffusion XL - great for photorealistic images",
        "supports_img2img": True
    },
    "sdxl-lightning": {
        "id": "bytedance/sdxl-lightning-4step:5599ed30703defd1d160a25a63321b4dec97101d98b4674bcc56e41f62f35637",
        "description": "Fast SDXL variant - 4 steps, very quick",
        "supports_img2img": False
    },
    "realistic-vision": {
        "id": "lucataco/realistic-vision-v5.1:2c8e954decbf70b7607a4414e5785ef9e4de4b8c51d50fb8b8b349160e0ef6bb",
        "description": "Photorealistic images, great for architectural renders",
        "supports_img2img": True
    },
    "kandinsky": {
        "id": "ai-forever/kandinsky-2.2:ea1addaab376f4dc227f5368bbd8f6d8f15a18abf8a84e4dac0b2e51807aa235",
        "description": "Artistic style, good for creative renders",
        "supports_img2img": True
    }
}

# Location profiles for architectural rendering
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


def get_headers():
    """Get API headers with authentication."""
    if not REPLICATE_API_TOKEN:
        raise ValueError("REPLICATE_API_TOKEN environment variable not set")
    return {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }


async def wait_for_prediction(prediction_url: str, timeout: int = 300) -> dict:
    """Poll for prediction completion (non-blocking async)."""
    start_time = time.time()

    async with httpx.AsyncClient(timeout=30) as client:
        while time.time() - start_time < timeout:
            response = await client.get(prediction_url, headers=get_headers())
            result = response.json()

            status = result.get("status")
            if status == "succeeded":
                return result
            elif status == "failed":
                raise Exception(f"Prediction failed: {result.get('error')}")
            elif status == "canceled":
                raise Exception("Prediction was canceled")

            await asyncio.sleep(3)

    raise Exception(f"Prediction timed out after {timeout} seconds")


def download_image(url: str, filename: str) -> str:
    """Download image from URL and save locally."""
    output_path = OUTPUT_DIR / filename

    with httpx.Client(timeout=60) as client:
        response = client.get(url)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            f.write(response.content)

    return str(output_path)


def image_to_data_url(image_path: str) -> str:
    """Convert local image to base64 data URL for img2img."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(path, "rb") as f:
        image_data = f.read()

    ext = path.suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp"
    }
    mime_type = mime_types.get(ext, "image/png")

    b64 = base64.b64encode(image_data).decode("utf-8")
    return f"data:{mime_type};base64,{b64}"


def build_architectural_prompt(location: str, custom: str = "", include_pool: bool = False) -> str:
    """Build a detailed photorealistic prompt for architectural rendering."""
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


def create_prediction(model_id: str, input_params: dict) -> dict:
    """Create a Replicate prediction, handling both versioned and unversioned models."""
    payload = {"input": input_params}

    if ":" in model_id:
        payload["version"] = model_id.split(":")[-1]
    else:
        payload["model"] = model_id

    with httpx.Client(timeout=60) as client:
        response = client.post(
            f"{REPLICATE_API_URL}/predictions",
            headers=get_headers(),
            json=payload
        )

        if response.status_code != 201:
            raise Exception(f"Failed to create prediction: {response.text}")

        return response.json()


@mcp.tool()
async def image_generate(
    prompt: str,
    model: str = "flux-schnell",
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    num_outputs: int = 1,
    guidance_scale: float = 7.5,
    num_inference_steps: int = 25
) -> str:
    """
    Generate an image from a text prompt.

    Args:
        prompt: Detailed description of the image you want to generate.
                Include style, lighting, mood, and specific details.
        model: Model to use. Options:
               - flux-pro (highest quality, ~$0.05/image)
               - flux-schnell (fast, recommended)
               - flux-dev (higher quality)
               - sdxl (photorealistic)
               - sdxl-lightning (very fast)
               - realistic-vision (architectural/photorealistic)
               - kandinsky (artistic)
        negative_prompt: What to avoid in the image
        width: Image width (default 1024)
        height: Image height (default 1024)
        num_outputs: Number of images to generate (1-4)
        guidance_scale: How closely to follow the prompt (1-20, default 7.5)
        num_inference_steps: Quality/speed tradeoff (more = better but slower)

    Returns:
        Path to the generated image file(s)
    """
    if not REPLICATE_API_TOKEN:
        return "ERROR: REPLICATE_API_TOKEN not set."

    if model not in MODELS:
        return f"ERROR: Unknown model '{model}'. Available: {', '.join(MODELS.keys())}"

    model_info = MODELS[model]

    if model_info.get("control_model"):
        return f"ERROR: '{model}' requires a control image. Use image_enhance or architectural_render instead."

    input_params = {
        "prompt": prompt,
        "width": width,
        "height": height,
    }

    if "flux" in model:
        input_params["num_outputs"] = min(num_outputs, 4)
        input_params["output_format"] = "png"
    else:
        input_params["negative_prompt"] = negative_prompt
        input_params["num_outputs"] = min(num_outputs, 4)
        input_params["guidance_scale"] = guidance_scale
        input_params["num_inference_steps"] = num_inference_steps

    try:
        prediction = create_prediction(model_info["id"], input_params)
        result = await wait_for_prediction(prediction["urls"]["get"])

        outputs = result.get("output", [])
        if isinstance(outputs, str):
            outputs = [outputs]

        saved_paths = []
        timestamp = int(time.time())

        for i, url in enumerate(outputs):
            filename = f"generated_{model}_{timestamp}_{i}.png"
            path = download_image(url, filename)
            saved_paths.append(path)

        if len(saved_paths) == 1:
            return f"Image generated successfully!\n\nSaved to: {saved_paths[0]}\n\nModel: {model}\nPrompt: {prompt[:100]}..."
        else:
            paths_str = "\n".join(f"  - {p}" for p in saved_paths)
            return f"Generated {len(saved_paths)} images!\n\nSaved to:\n{paths_str}\n\nModel: {model}\nPrompt: {prompt[:100]}..."

    except Exception as e:
        return f"ERROR: {str(e)}"


@mcp.tool()
async def image_enhance(
    image_path: str,
    prompt: str,
    model: str = "sdxl",
    strength: float = 0.7,
    negative_prompt: str = "",
    guidance_scale: float = 7.5
) -> str:
    """
    Enhance or modify an existing image using img2img.
    Great for enhancing Revit renders with realistic lighting, textures, etc.

    Args:
        image_path: Path to the source image (your Revit render)
        prompt: Description of how to enhance the image.
                Example: "photorealistic architectural render, warm evening lighting,
                         detailed textures, professional photography"
        model: Model to use. Must support img2img:
               - sdxl (recommended for architecture)
               - realistic-vision (photorealistic)
               - kandinsky (artistic)
               - flux-canny-pro (edge-preserving, best for architectural lines)
               - flux-depth-pro (depth-preserving, best for 3D geometry)
        strength: How much to change the image (0.0-1.0)
                  Lower = closer to original, Higher = more creative
        negative_prompt: What to avoid
        guidance_scale: How closely to follow the prompt (1-20)

    Returns:
        Path to the enhanced image file
    """
    if not REPLICATE_API_TOKEN:
        return "ERROR: REPLICATE_API_TOKEN not set."

    if model not in MODELS:
        return f"ERROR: Unknown model '{model}'. Available: {', '.join(MODELS.keys())}"

    model_info = MODELS[model]

    if not model_info.get("supports_img2img"):
        img2img_models = [k for k, v in MODELS.items() if v.get("supports_img2img")]
        return f"ERROR: Model '{model}' does not support img2img. Use one of: {', '.join(img2img_models)}"

    try:
        image_data_url = image_to_data_url(image_path)
    except FileNotFoundError as e:
        return f"ERROR: {str(e)}"
    except Exception as e:
        return f"ERROR reading image: {str(e)}"

    # Build input based on whether it's a Flux control model or standard img2img
    if model_info.get("control_model"):
        input_params = {
            "prompt": prompt,
            "control_image": image_data_url,
            "steps": 50,
            "guidance": guidance_scale * 4,  # Flux uses higher guidance range (1-100)
            "output_format": "png",
            "safety_tolerance": 5,
        }
    else:
        input_params = {
            "prompt": prompt,
            "image": image_data_url,
            "prompt_strength": strength,
            "negative_prompt": negative_prompt,
            "guidance_scale": guidance_scale,
        }

    try:
        prediction = create_prediction(model_info["id"], input_params)
        result = await wait_for_prediction(prediction["urls"]["get"])

        outputs = result.get("output", [])
        if isinstance(outputs, str):
            outputs = [outputs]

        if not outputs:
            return "ERROR: No output image received"

        timestamp = int(time.time())
        filename = f"enhanced_{model}_{timestamp}.png"
        path = download_image(outputs[0], filename)

        return f"Image enhanced successfully!\n\nOriginal: {image_path}\nEnhanced: {path}\n\nModel: {model}\nStrength: {strength}\nPrompt: {prompt[:100]}..."

    except Exception as e:
        return f"ERROR: {str(e)}"


@mcp.tool()
async def architectural_render(
    image_path: str,
    location: str = "south_florida",
    model: str = "flux-depth-pro",
    custom_prompt: str = "",
    include_pool: bool = False,
    steps: int = 50,
    guidance: float = 30.0
) -> str:
    """
    One-shot photorealistic architectural render from a Revit/CAD export.
    Uses Flux Canny/Depth Pro to preserve building geometry while adding
    photorealistic environment, materials, landscaping, and sky.

    Args:
        image_path: Path to the source image (Revit render export, elevation, etc.)
        location: Location profile for environment/vegetation/sky. Options:
                  - south_florida (tropical, palm trees, Miami modern)
                  - southwest_desert (Arizona, cacti, desert contemporary)
                  - southern_california (Mediterranean, olive trees, coastal)
                  - default (generic professional)
        model: Flux model to use:
               - flux-depth-pro (recommended - best for 3D geometry preservation)
               - flux-canny-pro (best for clean architectural line drawings)
        custom_prompt: Additional prompt text to append (e.g., "evening lighting", "rainy day")
        include_pool: Add a swimming pool to the scene
        steps: Diffusion steps (15-50, higher = better quality, default 50)
        guidance: Prompt guidance (1-100, higher = follow prompt more closely, default 30)

    Returns:
        Path to the rendered image file with cost estimate
    """
    if not REPLICATE_API_TOKEN:
        return "ERROR: REPLICATE_API_TOKEN not set."

    # Validate model is a Flux control model
    valid_models = ["flux-canny-pro", "flux-depth-pro"]
    if model not in valid_models:
        return f"ERROR: architectural_render requires a Flux control model. Use one of: {', '.join(valid_models)}"

    if location not in LOCATION_PROFILES:
        return f"ERROR: Unknown location '{location}'. Available: {', '.join(LOCATION_PROFILES.keys())}"

    model_info = MODELS[model]

    try:
        image_data_url = image_to_data_url(image_path)
    except FileNotFoundError as e:
        return f"ERROR: {str(e)}"
    except Exception as e:
        return f"ERROR reading image: {str(e)}"

    # Build the architectural prompt from location profile
    prompt = build_architectural_prompt(
        location=location,
        custom=custom_prompt,
        include_pool=include_pool
    )

    input_params = {
        "prompt": prompt,
        "control_image": image_data_url,
        "steps": steps,
        "guidance": guidance,
        "output_format": "png",
        "safety_tolerance": 5,
    }

    try:
        prediction = create_prediction(model_info["id"], input_params)
        result = await wait_for_prediction(prediction["urls"]["get"], timeout=300)

        outputs = result.get("output", [])
        if isinstance(outputs, str):
            outputs = [outputs]

        if not outputs:
            return "ERROR: No output image received"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_short = model.replace("flux-", "").replace("-pro", "")
        filename = f"render_{model_short}_{location}_{timestamp}.png"
        path = download_image(outputs[0], filename)

        return (
            f"Architectural render complete!\n\n"
            f"Output: {path}\n"
            f"Model: {model}\n"
            f"Location: {location.replace('_', ' ').title()}\n"
            f"Steps: {steps}, Guidance: {guidance}\n"
            f"Pool: {'Yes' if include_pool else 'No'}\n"
            f"Cost: ~$0.05\n\n"
            f"Prompt: {prompt[:150]}..."
        )

    except Exception as e:
        return f"ERROR: {str(e)}"


@mcp.tool()
async def remove_background(image_path: str) -> str:
    """
    Remove the background from an image using AI.

    Args:
        image_path: Path to the source image

    Returns:
        Path to the image with background removed (transparent PNG)
    """
    if not REPLICATE_API_TOKEN:
        return "ERROR: REPLICATE_API_TOKEN not set."

    try:
        image_data_url = image_to_data_url(image_path)
    except FileNotFoundError as e:
        return f"ERROR: {str(e)}"
    except Exception as e:
        return f"ERROR reading image: {str(e)}"

    input_params = {
        "image": image_data_url,
    }

    try:
        prediction = create_prediction(
            "lucataco/remove-bg:95fcc2a26d3899cd6c2691c900571aadf58dee94aade85a7a4f6f3fd7c21e36f",
            input_params
        )
        result = await wait_for_prediction(prediction["urls"]["get"])

        output = result.get("output")
        if isinstance(output, list):
            output = output[0]

        if not output:
            return "ERROR: No output image received"

        timestamp = int(time.time())
        filename = f"nobg_{timestamp}.png"
        path = download_image(output, filename)

        return f"Background removed!\n\nOriginal: {image_path}\nResult: {path}"

    except Exception as e:
        return f"ERROR: {str(e)}"


@mcp.tool()
def image_list_models() -> str:
    """
    List all available image generation models and their capabilities.

    Returns:
        Table of available models with descriptions
    """
    output = ["# Available Image Generation Models\n"]
    output.append("| Model | Description | Img2Img | Control |")
    output.append("|-------|-------------|---------|---------|")

    for name, info in MODELS.items():
        img2img = "Yes" if info.get("supports_img2img") else "No"
        control = "Yes" if info.get("control_model") else "No"
        output.append(f"| {name} | {info['description']} | {img2img} | {control} |")

    output.append("\n## Usage Tips")
    output.append("- **For architectural rendering**: Use `architectural_render` with `flux-depth-pro` or `flux-canny-pro`")
    output.append("- **For Revit render enhancement**: Use `image_enhance` with `flux-depth-pro` or `sdxl`")
    output.append("- **For quick generation**: Use `flux-schnell` or `sdxl-lightning`")
    output.append("- **For highest quality text-to-image**: Use `flux-pro`")
    output.append("- **For artistic styles**: Use `kandinsky`")
    output.append("- **To remove backgrounds**: Use `remove_background`")

    output.append("\n## Location Profiles (for architectural_render)")
    for name, profile in LOCATION_PROFILES.items():
        output.append(f"- **{name}**: {profile['environment']}")

    return "\n".join(output)


@mcp.tool()
def image_list_outputs() -> str:
    """
    List all generated images in the output directory.

    Returns:
        List of generated image files with their paths
    """
    if not OUTPUT_DIR.exists():
        return "No output directory found. No images have been generated yet."

    images = list(OUTPUT_DIR.glob("*.png")) + list(OUTPUT_DIR.glob("*.jpg")) + list(OUTPUT_DIR.glob("*.webp"))

    if not images:
        return "No generated images found in the output directory."

    images.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    output = [f"# Generated Images ({len(images)} total)\n"]
    output.append(f"Output directory: {OUTPUT_DIR}\n")

    for img in images[:20]:
        stat = img.stat()
        size_kb = stat.st_size / 1024
        mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))
        output.append(f"- {img.name} ({size_kb:.1f} KB) - {mtime}")

    if len(images) > 20:
        output.append(f"\n... and {len(images) - 20} more")

    return "\n".join(output)


if __name__ == "__main__":
    mcp.run()

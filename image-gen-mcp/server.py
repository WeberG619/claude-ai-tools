#!/usr/bin/env python3
"""
Image Generation MCP Server
Uses Replicate API to generate and enhance images.
"""

import os
import base64
import httpx
import time
from pathlib import Path
from typing import Optional
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("image-gen")

# Replicate API configuration
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")
REPLICATE_API_URL = "https://api.replicate.com/v1"

# Output directory for generated images
OUTPUT_DIR = Path(os.environ.get("IMAGE_OUTPUT_DIR", "/mnt/d/_CLAUDE-TOOLS/image-gen-mcp/outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Available models with their Replicate identifiers
MODELS = {
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


def get_headers():
    """Get API headers with authentication."""
    if not REPLICATE_API_TOKEN:
        raise ValueError("REPLICATE_API_TOKEN environment variable not set")
    return {
        "Authorization": f"Token {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json"
    }


def wait_for_prediction(prediction_url: str, timeout: int = 300) -> dict:
    """Poll for prediction completion."""
    start_time = time.time()

    with httpx.Client(timeout=30) as client:
        while time.time() - start_time < timeout:
            response = client.get(prediction_url, headers=get_headers())
            result = response.json()

            status = result.get("status")
            if status == "succeeded":
                return result
            elif status == "failed":
                raise Exception(f"Prediction failed: {result.get('error')}")
            elif status == "canceled":
                raise Exception("Prediction was canceled")

            # Wait before polling again
            time.sleep(2)

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

    # Detect mime type from extension
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


@mcp.tool()
def image_generate(
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
        return "ERROR: REPLICATE_API_TOKEN not set. Please set this environment variable with your Replicate API token."

    if model not in MODELS:
        return f"ERROR: Unknown model '{model}'. Available: {', '.join(MODELS.keys())}"

    model_info = MODELS[model]

    # Build input based on model
    input_params = {
        "prompt": prompt,
        "width": width,
        "height": height,
    }

    # Add model-specific parameters
    if "flux" in model:
        input_params["num_outputs"] = min(num_outputs, 4)
        input_params["output_format"] = "png"
    else:
        input_params["negative_prompt"] = negative_prompt
        input_params["num_outputs"] = min(num_outputs, 4)
        input_params["guidance_scale"] = guidance_scale
        input_params["num_inference_steps"] = num_inference_steps

    try:
        # Create prediction
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{REPLICATE_API_URL}/predictions",
                headers=get_headers(),
                json={
                    "version": model_info["id"].split(":")[-1] if ":" in model_info["id"] else None,
                    "model": model_info["id"].split(":")[0] if ":" in model_info["id"] else model_info["id"],
                    "input": input_params
                }
            )

            if response.status_code != 201:
                return f"ERROR: Failed to create prediction: {response.text}"

            prediction = response.json()

        # Wait for completion
        result = wait_for_prediction(prediction["urls"]["get"])

        # Download output images
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
def image_enhance(
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
        strength: How much to change the image (0.0-1.0)
                  Lower = closer to original, Higher = more creative
        negative_prompt: What to avoid
        guidance_scale: How closely to follow the prompt (1-20)

    Returns:
        Path to the enhanced image file
    """
    if not REPLICATE_API_TOKEN:
        return "ERROR: REPLICATE_API_TOKEN not set. Please set this environment variable with your Replicate API token."

    if model not in MODELS:
        return f"ERROR: Unknown model '{model}'. Available: {', '.join(MODELS.keys())}"

    model_info = MODELS[model]

    if not model_info.get("supports_img2img"):
        return f"ERROR: Model '{model}' does not support img2img. Use one of: sdxl, realistic-vision, kandinsky"

    # Convert image to data URL
    try:
        image_data_url = image_to_data_url(image_path)
    except FileNotFoundError as e:
        return f"ERROR: {str(e)}"
    except Exception as e:
        return f"ERROR reading image: {str(e)}"

    input_params = {
        "prompt": prompt,
        "image": image_data_url,
        "prompt_strength": strength,
        "negative_prompt": negative_prompt,
        "guidance_scale": guidance_scale,
    }

    try:
        # Create prediction
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{REPLICATE_API_URL}/predictions",
                headers=get_headers(),
                json={
                    "version": model_info["id"].split(":")[-1],
                    "input": input_params
                }
            )

            if response.status_code != 201:
                return f"ERROR: Failed to create prediction: {response.text}"

            prediction = response.json()

        # Wait for completion
        result = wait_for_prediction(prediction["urls"]["get"])

        # Download output
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
def image_list_models() -> str:
    """
    List all available image generation models and their capabilities.

    Returns:
        Table of available models with descriptions
    """
    output = ["# Available Image Generation Models\n"]
    output.append("| Model | Description | Img2Img |")
    output.append("|-------|-------------|---------|")

    for name, info in MODELS.items():
        img2img = "Yes" if info.get("supports_img2img") else "No"
        output.append(f"| {name} | {info['description']} | {img2img} |")

    output.append("\n## Usage Tips")
    output.append("- **For Revit render enhancement**: Use `realistic-vision` or `sdxl` with img2img")
    output.append("- **For quick generation**: Use `flux-schnell` or `sdxl-lightning`")
    output.append("- **For highest quality**: Use `flux-dev` (slower)")
    output.append("- **For artistic styles**: Use `kandinsky`")

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

    # Sort by modification time, newest first
    images.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    output = [f"# Generated Images ({len(images)} total)\n"]
    output.append(f"Output directory: {OUTPUT_DIR}\n")

    for img in images[:20]:  # Show last 20
        stat = img.stat()
        size_kb = stat.st_size / 1024
        mtime = time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime))
        output.append(f"- {img.name} ({size_kb:.1f} KB) - {mtime}")

    if len(images) > 20:
        output.append(f"\n... and {len(images) - 20} more")

    return "\n".join(output)


if __name__ == "__main__":
    mcp.run()

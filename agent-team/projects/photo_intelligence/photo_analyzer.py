"""
Photo Analyzer - AI-powered construction photo analysis.
"""
import base64
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import httpx

from config import OpenAIConfig, TaggingConfig


@dataclass
class PhotoTag:
    """A tag extracted from a photo."""
    category: str
    value: str
    confidence: float
    details: Optional[str] = None


@dataclass
class PhotoAnalysis:
    """Complete analysis of a construction photo."""
    # Identification
    photo_id: str
    filename: str

    # Extracted data
    tags: List[PhotoTag]
    description: str
    room_type: Optional[str]
    floor_level: Optional[str]
    trade: Optional[str]
    work_stage: Optional[str]

    # Issues detected
    issues: List[Dict[str, str]]
    issue_count: int

    # Metadata
    analyzed_at: datetime
    processing_time: float
    model_used: str


class PhotoAnalyzer:
    """Analyzes construction photos using OpenAI Vision API."""

    ANALYSIS_PROMPT = """You are an expert construction site photo analyzer for architects, contractors, and inspectors.

Analyze this construction/building photo and extract the following information in JSON format:

{
    "description": "Brief description of what the photo shows",
    "room_type": "Type of room/space (e.g., kitchen, bathroom, office, hallway, exterior, roof)",
    "floor_level": "Floor level if identifiable (e.g., Level 1, Basement, Roof)",
    "trade": "Primary trade shown (e.g., electrical, plumbing, HVAC, framing, drywall, flooring, painting)",
    "work_stage": "Construction stage (e.g., demolition, rough-in, inspection, finish, punch-list)",
    "materials": ["List of visible materials"],
    "issues": [
        {
            "type": "Issue type (defect, damage, incomplete, code_violation, safety)",
            "description": "Description of the issue",
            "severity": "low/medium/high"
        }
    ],
    "tags": ["Additional relevant tags"],
    "confidence": 0.0-1.0
}

Be specific to construction/architecture context. If you can't determine something, use null.
Focus on details that would be useful for project documentation and punch lists."""

    def __init__(self, config: OpenAIConfig, tagging_config: TaggingConfig = None):
        self.config = config
        self.tagging = tagging_config or TaggingConfig()
        self.client = httpx.Client(timeout=60.0)

    def analyze_photo(self, image_path: str) -> PhotoAnalysis:
        """
        Analyze a single photo.

        Args:
            image_path: Path to the image file

        Returns:
            PhotoAnalysis with extracted information
        """
        start_time = datetime.now()
        path = Path(image_path)

        # Read and encode image
        image_data = self._encode_image(path)

        # Call OpenAI Vision API
        response = self._call_vision_api(image_data)

        # Parse response
        analysis = self._parse_response(response, path, start_time)

        return analysis

    def analyze_batch(self, image_paths: List[str]) -> List[PhotoAnalysis]:
        """Analyze multiple photos."""
        results = []
        for path in image_paths:
            try:
                result = self.analyze_photo(path)
                results.append(result)
            except Exception as e:
                print(f"Error analyzing {path}: {e}")
        return results

    def _encode_image(self, path: Path) -> str:
        """Encode image to base64."""
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _call_vision_api(self, image_data: str) -> Dict[str, Any]:
        """Call OpenAI Vision API."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }

        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.ANALYSIS_PROMPT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}",
                                "detail": self.config.detail
                            }
                        }
                    ]
                }
            ],
            "max_tokens": self.config.max_tokens
        }

        response = self.client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()

        return response.json()

    def _parse_response(self, response: Dict, path: Path, start_time: datetime) -> PhotoAnalysis:
        """Parse OpenAI response into PhotoAnalysis."""
        processing_time = (datetime.now() - start_time).total_seconds()

        # Extract content
        content = response["choices"][0]["message"]["content"]

        # Parse JSON from response
        try:
            # Find JSON in response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(content[json_start:json_end])
            else:
                data = {}
        except json.JSONDecodeError:
            data = {"description": content}

        # Build tags
        tags = []

        if data.get("room_type"):
            tags.append(PhotoTag(
                category="room_type",
                value=data["room_type"],
                confidence=data.get("confidence", 0.8)
            ))

        if data.get("floor_level"):
            tags.append(PhotoTag(
                category="floor_level",
                value=data["floor_level"],
                confidence=data.get("confidence", 0.8)
            ))

        if data.get("trade"):
            tags.append(PhotoTag(
                category="trade",
                value=data["trade"],
                confidence=data.get("confidence", 0.8)
            ))

        if data.get("work_stage"):
            tags.append(PhotoTag(
                category="work_stage",
                value=data["work_stage"],
                confidence=data.get("confidence", 0.8)
            ))

        for material in data.get("materials", []):
            tags.append(PhotoTag(
                category="material",
                value=material,
                confidence=data.get("confidence", 0.7)
            ))

        for tag in data.get("tags", []):
            tags.append(PhotoTag(
                category="custom",
                value=tag,
                confidence=0.7
            ))

        # Extract issues
        issues = data.get("issues", [])
        issue_count = len(issues)

        return PhotoAnalysis(
            photo_id=path.stem,
            filename=path.name,
            tags=tags,
            description=data.get("description", ""),
            room_type=data.get("room_type"),
            floor_level=data.get("floor_level"),
            trade=data.get("trade"),
            work_stage=data.get("work_stage"),
            issues=issues,
            issue_count=issue_count,
            analyzed_at=datetime.now(),
            processing_time=processing_time,
            model_used=self.config.model
        )

    def close(self):
        """Close the HTTP client."""
        self.client.close()


# Quick test
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python photo_analyzer.py <image_path>")
        sys.exit(1)

    from config import load_config
    config = load_config()

    if not config.openai.api_key:
        print("Error: OPENAI_API_KEY not set")
        sys.exit(1)

    analyzer = PhotoAnalyzer(config.openai)
    result = analyzer.analyze_photo(sys.argv[1])

    print(f"\nAnalysis of: {result.filename}")
    print(f"Description: {result.description}")
    print(f"Room: {result.room_type}")
    print(f"Floor: {result.floor_level}")
    print(f"Trade: {result.trade}")
    print(f"Stage: {result.work_stage}")
    print(f"Issues: {result.issue_count}")
    print(f"\nTags:")
    for tag in result.tags:
        print(f"  - {tag.category}: {tag.value} ({tag.confidence:.0%})")

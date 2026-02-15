"""
Photo Intelligence Configuration
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class OpenAIConfig:
    """OpenAI Vision API configuration."""
    api_key: Optional[str] = None
    model: str = "gpt-4o"  # GPT-4 with vision
    max_tokens: int = 1000
    detail: str = "high"  # "low", "high", or "auto"

    def __post_init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")


@dataclass
class StorageConfig:
    """File storage configuration."""
    # Local storage path
    upload_dir: str = "./uploads"
    # Maximum file size in MB
    max_file_size: int = 20
    # Allowed extensions
    allowed_extensions: tuple = (".jpg", ".jpeg", ".png", ".heic", ".webp")
    # Thumbnail size
    thumbnail_size: tuple = (400, 400)


@dataclass
class TaggingConfig:
    """Photo tagging configuration."""
    # Construction-specific categories to detect
    categories: tuple = (
        "room_type",      # Kitchen, bathroom, office, etc.
        "floor_level",    # Level 1, basement, roof, etc.
        "trade",          # Electrical, plumbing, HVAC, framing
        "work_stage",     # Rough-in, finish, punch list
        "issue_type",     # Defect, damage, incomplete, code violation
        "material",       # Drywall, concrete, wood, steel
    )
    # Confidence threshold for tags (0-1)
    confidence_threshold: float = 0.7


@dataclass
class AppConfig:
    """Main application configuration."""
    openai: OpenAIConfig
    storage: StorageConfig
    tagging: TaggingConfig
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = True
    # Database
    database_url: str = "sqlite:///photo_intelligence.db"


def load_config() -> AppConfig:
    """Load configuration from environment."""
    return AppConfig(
        openai=OpenAIConfig(),
        storage=StorageConfig(),
        tagging=TaggingConfig()
    )


# Environment variable template
ENV_TEMPLATE = """
# OpenAI API Key (required for photo analysis)
OPENAI_API_KEY=sk-your-openai-api-key

# Optional: Custom storage path
# UPLOAD_DIR=/path/to/uploads
"""

if __name__ == "__main__":
    print("Environment template for .env file:")
    print(ENV_TEMPLATE)

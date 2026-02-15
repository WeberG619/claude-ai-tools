"""
Founder's Companion - Configuration
===================================
Central configuration for the AI mental health platform.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class OpenAIConfig:
    """OpenAI API configuration."""
    api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    model: str = "gpt-4o"
    max_tokens: int = 1000
    temperature: float = 0.7  # Warm, empathetic responses


@dataclass
class EncryptionConfig:
    """Vault encryption settings."""
    # In production, use proper key management (AWS KMS, HashiCorp Vault, etc.)
    master_key_env: str = "FOUNDERS_COMPANION_MASTER_KEY"
    algorithm: str = "AES-256-GCM"
    key_derivation: str = "PBKDF2"
    iterations: int = 100000


@dataclass
class DatabaseConfig:
    """Database configuration."""
    db_path: str = "founders_companion.db"
    echo: bool = False  # SQL logging


@dataclass
class MatchingConfig:
    """Founder matching algorithm settings."""
    min_compatibility_score: float = 0.6
    max_matches_per_day: int = 3
    challenge_weight: float = 0.4
    stage_weight: float = 0.3
    industry_weight: float = 0.2
    mood_weight: float = 0.1


@dataclass
class SubscriptionTiers:
    """Pricing tiers."""
    SOLO_PRICE: float = 29.0
    CONNECTED_PRICE: float = 49.0
    SUPPORTED_PRICE: float = 99.0
    ENTERPRISE_PRICE: float = 499.0

    SOLO_MATCHES: int = 0
    CONNECTED_MATCHES: int = 5
    SUPPORTED_MATCHES: int = -1  # Unlimited

    SOLO_SESSIONS: int = 0
    CONNECTED_SESSIONS: int = 4
    SUPPORTED_SESSIONS: int = -1  # Unlimited


@dataclass
class AppConfig:
    """Main application configuration."""
    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = True

    # Components
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    encryption: EncryptionConfig = field(default_factory=EncryptionConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    tiers: SubscriptionTiers = field(default_factory=SubscriptionTiers)

    # Paths
    data_dir: Path = field(default_factory=lambda: Path("./data"))

    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    """Load configuration from environment."""
    return AppConfig(
        host=os.getenv("FC_HOST", "0.0.0.0"),
        port=int(os.getenv("FC_PORT", "8080")),
        debug=os.getenv("FC_DEBUG", "true").lower() == "true",
        openai=OpenAIConfig(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("FC_MODEL", "gpt-4o"),
        ),
        database=DatabaseConfig(
            db_path=os.getenv("FC_DB_PATH", "founders_companion.db"),
        ),
    )


# Singleton config instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get or create config singleton."""
    global _config
    if _config is None:
        _config = load_config()
    return _config

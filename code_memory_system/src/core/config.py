"""Configuration management for the code memory system."""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class CacheConfig(BaseModel):
    max_size_mb: int = Field(default=500, description="Maximum cache size in MB")
    hot_cache_ttl: int = Field(default=3600, description="Hot cache TTL in seconds")
    warm_cache_ttl: int = Field(default=86400, description="Warm cache TTL in seconds")
    
    
class DatabaseConfig(BaseModel):
    path: Path = Field(default=Path("./data/code_memory.db"))
    vector_db_path: Path = Field(default=Path("./data/vector_store"))
    
    
class PerformanceConfig(BaseModel):
    max_workers: int = Field(default=4, description="Maximum parallel workers")
    batch_size: int = Field(default=100, description="Batch size for processing")
    embedding_dimension: int = Field(default=768, description="Dimension of embeddings")
    

class RedisConfig(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    password: Optional[str] = None
    enabled: bool = Field(default=False)
    

class Config(BaseModel):
    """Main configuration for the code memory system."""
    cache: CacheConfig = Field(default_factory=CacheConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    openai_api_key: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            cache=CacheConfig(
                max_size_mb=int(os.getenv("MAX_CACHE_SIZE_MB", 500)),
                hot_cache_ttl=int(os.getenv("HOT_CACHE_TTL_SECONDS", 3600)),
                warm_cache_ttl=int(os.getenv("WARM_CACHE_TTL_SECONDS", 86400))
            ),
            database=DatabaseConfig(
                path=Path(os.getenv("DATABASE_PATH", "./data/code_memory.db")),
                vector_db_path=Path(os.getenv("VECTOR_DB_PATH", "./data/vector_store"))
            ),
            performance=PerformanceConfig(
                max_workers=int(os.getenv("MAX_WORKERS", 4)),
                batch_size=int(os.getenv("BATCH_SIZE", 100)),
                embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", 768))
            ),
            redis=RedisConfig(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                password=os.getenv("REDIS_PASSWORD"),
                enabled=bool(os.getenv("REDIS_HOST"))
            ),
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
    def ensure_directories(self):
        """Ensure all required directories exist."""
        self.database.path.parent.mkdir(parents=True, exist_ok=True)
        self.database.vector_db_path.mkdir(parents=True, exist_ok=True)
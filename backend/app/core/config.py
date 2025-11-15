from typing import List, Optional

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings, Field

import os


class Settings(BaseSettings):
    """Application settings"""

    # Application
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")

    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "PaperTrail"

    # Security
    SECRET_KEY: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60 * 24 * 8, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"], env="CORS_ORIGINS"
    )

    # Allowed hosts
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1"], env="ALLOWED_HOSTS"
    )

    # Database
    NEO4J_URI: str = Field(default="bolt://localhost:7687", env="NEO4J_URI")
    NEO4J_USER: str = Field(default="neo4j", env="NEO4J_USER")
    NEO4J_PASSWORD: str = Field(default="papertrail123", env="NEO4J_PASSWORD")
    NEO4J_DATABASE: str = Field(default="neo4j", env="NEO4J_DATABASE")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")

    # AI Services
    OPENAI_API_KEY: str = Field(default="sk-placeholder-for-development", env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4-turbo-preview", env="OPENAI_MODEL")
    OPENAI_MAX_TOKENS: int = Field(default=4000, env="OPENAI_MAX_TOKENS")

    # Vector Store
    FAISS_INDEX_PATH: str = Field(default="./data/faiss_index", env="FAISS_INDEX_PATH")
    EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", env="EMBEDDING_MODEL"
    )

    # File Upload
    UPLOAD_DIR: str = Field(default="./uploads", env="UPLOAD_DIR")
    MAX_FILE_SIZE: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    ALLOWED_FILE_TYPES: List[str] = Field(default=[".pdf"], env="ALLOWED_FILE_TYPES")

    # Processing
    MAX_CONCURRENT_PROCESSES: int = Field(default=4, env="MAX_CONCURRENT_PROCESSES")
    BATCH_SIZE: int = Field(default=10, env="BATCH_SIZE")

    # Monitoring
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # Agent Configuration
    AGENT_TIMEOUT: int = Field(default=300, env="AGENT_TIMEOUT")  # 5 minutes
    AGENT_MAX_RETRIES: int = Field(default=3, env="AGENT_MAX_RETRIES")

    # Graph Configuration
    GRAPH_CACHE_TTL: int = Field(default=3600, env="GRAPH_CACHE_TTL")  # 1 hour
    GRAPH_MAX_NODES: int = Field(default=10000, env="GRAPH_MAX_NODES")

    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.FAISS_INDEX_PATH, exist_ok=True)

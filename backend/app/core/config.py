import os
from typing import List, Optional

try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseSettings, Field  # type: ignore[no-redef]

    SettingsConfigDict = None  # type: ignore[assignment,misc]


class Settings(BaseSettings):
    """Application settings"""

    model_config = (
        SettingsConfigDict(
            env_file=".env",
            case_sensitive=True,
            extra="ignore",
        )
        if SettingsConfigDict is not None
        else None  # type: ignore[assignment]
    )

    # Application
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)

    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "PaperTrail"

    # Security
    SECRET_KEY: str = Field(default="your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24 * 8)
    ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )

    # Allowed hosts
    ALLOWED_HOSTS: List[str] = Field(default=["localhost", "127.0.0.1", "testserver"])

    # Database
    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    NEO4J_USERNAME: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="papertrail123")
    NEO4J_DATABASE: str = Field(default="neo4j")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379")

    # AI Services
    OPENAI_API_KEY: str = Field(default="sk-placeholder-for-development")
    OPENAI_BASE_URL: Optional[str] = Field(
        default="https://openrouter.ai/api/v1"
    )  # For OpenRouter or custom endpoints
    OPENAI_MODEL: str = Field(default="openai/gpt-4-turbo")  # OpenRouter model format
    OPENAI_MAX_TOKENS: int = Field(default=4000)
    # OpenRouter specific headers
    OPENROUTER_HTTP_REFERER: Optional[str] = Field(default=None)  # Your app URL
    OPENROUTER_X_TITLE: Optional[str] = Field(default="PaperTrail")  # App name

    # Vector Store - Pinecone
    PINECONE_API_KEY: str = Field(default="")
    PINECONE_INDEX_NAME: str = Field(default="quickstart")
    PINECONE_HOST: str = Field(default="")
    PINECONE_DIMENSION: int = Field(default=384)  # for all-MiniLM-L6-v2
    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")

    # Legacy FAISS (keep for backwards compatibility)
    FAISS_INDEX_PATH: str = Field(default="./data/faiss_index")

    # Redis LangCache
    LANGCACHE_API_KEY: str = Field(default="")
    LANGCACHE_SERVER_URL: str = Field(
        default="https://aws-us-east-1.langcache.redis.io"
    )
    LANGCACHE_CACHE_ID: str = Field(default="")
    LANGCACHE_ENABLED: bool = Field(default=True)

    # Firecrawl
    FIRECRAWL_API_KEY: str = Field(default="")
    FIRECRAWL_ENABLED: bool = Field(default=True)

    # ArXiv
    ARXIV_MAX_RESULTS: int = Field(default=100)
    ARXIV_RATE_LIMIT: float = Field(default=3.0)  # requests per second
    ARXIV_DOWNLOAD_DIR: str = Field(default="./data/arxiv_pdfs")

    # File Upload
    UPLOAD_DIR: str = Field(default="./uploads")
    MAX_FILE_SIZE: int = Field(default=50 * 1024 * 1024)  # 50MB
    ALLOWED_FILE_TYPES: List[str] = Field(default=[".pdf"])

    # Processing
    MAX_CONCURRENT_PROCESSES: int = Field(default=4)
    BATCH_SIZE: int = Field(default=10)

    # Monitoring
    ENABLE_METRICS: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")

    # Agent Configuration
    AGENT_TIMEOUT: int = Field(default=300)  # 5 minutes
    AGENT_MAX_RETRIES: int = Field(default=3)

    # Graph Configuration
    GRAPH_CACHE_TTL: int = Field(default=3600)  # 1 hour
    GRAPH_MAX_NODES: int = Field(default=10000)


# Create settings instance
settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.FAISS_INDEX_PATH, exist_ok=True)
os.makedirs(settings.ARXIV_DOWNLOAD_DIR, exist_ok=True)

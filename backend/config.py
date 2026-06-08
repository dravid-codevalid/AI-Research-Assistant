"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "AI Research Assistant"
    DEBUG: bool = False
    API_PREFIX: str = "/api"
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]
    LLM_PROVIDER: str = "echo"

    # --- Auth ---
    SECRET_KEY: str = "supersecretkey" # In production, set via env var
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days

    # --- AWS Bedrock (Level 2) ---
    AWS_REGION: str = "us-east-1"
    AWS_BEDROCK_MODEL_ID: str = "us.amazon.nova-lite-v1:0"

    # --- LiteLLM (Level 3) ---
    LITELLM_BASE_URL: str = "http://localhost:4000"
    LITELLM_MASTER_KEY: str = "sk-litellm-dev-master-key"

    # --- Database ---
    APP_DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:15432/postgres"

    # --- Agent Search ---
    TAVILY_API_KEY: str | None = None

    # --- Agent Memory (Level 4) ---
    AGENT_MEMORY_PATH: str = "./agent_memory.json"

    # --- Temporal (Level 5) ---
    TEMPORAL_HOST: str = "localhost:7233"
    TEMPORAL_TASK_QUEUE: str = "research-queue"



settings = Settings()

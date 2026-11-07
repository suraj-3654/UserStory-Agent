import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Memgraph Database Configuration
    MEMGRAPH_HOST: str = "memgraph"
    MEMGRAPH_PORT: int = 7687
    MEMGRAPH_USER: str = ""
    MEMGRAPH_PASSWORD: str = ""

    # Backend Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # Dynamic Model Selection & Resilience
    PRIMARY_LLM_PROVIDER: str = "ollama"  # "ollama", "groq", "openai", "openrouter", "custom"
    OPENAI_BASE_URL: str = "http://127.0.0.1:11434/v1"
    PRIMARY_API_KEY: str = "ollama"
    FALLBACK_API_KEY: str = ""

    # Task-Based Model Routing Tiers
    MODEL_SCANNING: str = "llama3.2:latest"
    MODEL_ELICITATION: str = "llama3.1:latest"
    MODEL_PLANNING: str = "llama3.1:latest"
    MODEL_CYPHER: str = "llama3.1:latest"
    MODEL_CODING: str = "llama3.1:latest"

    # Fallback Hierarchy
    MODEL_FALLBACK_LIST: str = "llama3.1:latest,llama3.2:latest"

    # Resilience: Exponential Backoff & Retry
    LLM_MAX_RETRIES: int = 2
    LLM_BACKOFF_FACTOR: float = 1.5
    LLM_TIMEOUT_SECONDS: float = 15.0

    # Repo workspace
    TEMP_REPO_DIR: str = "./temp_repos"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def fallback_models(self) -> List[str]:
        if not self.MODEL_FALLBACK_LIST:
            return []
        return [m.strip() for m in self.MODEL_FALLBACK_LIST.split(",") if m.strip()]

    @property
    def memgraph_uri(self) -> str:
        return f"bolt://{self.MEMGRAPH_HOST}:{self.MEMGRAPH_PORT}"


settings = Settings()

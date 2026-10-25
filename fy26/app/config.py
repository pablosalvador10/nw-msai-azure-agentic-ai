"""Service settings.

Every value comes from an environment variable with the same name in upper case
(FOUNDRY_MODEL -> foundry_model). Locally they are read from fy26/.env; in Azure,
Terraform sets them on the Container App.
"""

from enum import StrEnum
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMMode(StrEnum):
    FOUNDRY = "foundry"  # real models on Microsoft Foundry
    OFFLINE = "offline"  # deterministic stand-ins, no Azure needed (used by tests)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    student_id: str = "anonymous"
    app_version: str = "dev"
    llm_mode: LLMMode = LLMMode.FOUNDRY

    foundry_project_endpoint: str = ""
    foundry_openai_endpoint: str = ""
    foundry_model: str = ""
    foundry_embedding_model: str = ""

    applicationinsights_connection_string: str = ""
    service_api_key: SecretStr | None = None
    public_hostname: str = ""  # set by Terraform: the app's address, the only remote Host /mcp accepts

    max_body_bytes: int = 64_000
    rate_limit_per_minute: int = 240

    def missing(self) -> list[str]:
        """Names of required settings that are empty. Offline mode needs none."""
        if self.llm_mode is LLMMode.OFFLINE:
            return []
        required = {
            "FOUNDRY_PROJECT_ENDPOINT": self.foundry_project_endpoint,
            "FOUNDRY_OPENAI_ENDPOINT": self.foundry_openai_endpoint,
            "FOUNDRY_MODEL": self.foundry_model,
            "FOUNDRY_EMBEDDING_MODEL": self.foundry_embedding_model,
        }
        return [name for name, value in required.items() if not value]


@lru_cache
def get_settings() -> Settings:
    """The settings, read once from the environment and `.env`."""
    return Settings()

"""How the service talks to models.

Two implementations with the same methods:

- FoundryModels: real models on Microsoft Foundry, authenticated with Microsoft Entra ID.
  No API keys: DefaultAzureCredential uses your `az login` locally and the app's
  managed identity in Azure.
- OfflineModels: deterministic stand-ins so tests and the harness run without Azure.
"""

import hashlib
import math
import re
from typing import TypeVar

from agent_framework.foundry import FoundryChatClient
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.config import LLMMode, Settings

T = TypeVar("T", bound=BaseModel)

# Token audience for Foundry. The credential exchanges your identity for a short-lived token.
TOKEN_SCOPE = "https://ai.azure.com/.default"  # noqa: S105 (an OAuth scope, not a secret)


class FoundryModels:
    offline = False

    def __init__(self, settings: Settings) -> None:
        self.name = settings.foundry_model
        self.embedding_name = settings.foundry_embedding_model
        self.project_endpoint = settings.foundry_project_endpoint
        self.credential = DefaultAzureCredential()
        self.client = AsyncOpenAI(
            base_url=settings.foundry_openai_endpoint,
            api_key=get_bearer_token_provider(self.credential, TOKEN_SCOPE),
        )
        self._agent_client: FoundryChatClient | None = None

    async def chat(self, instructions: str, message: str) -> str:
        """One call to the Responses API: instructions + user message -> text."""
        response = await self.client.responses.create(model=self.name, instructions=instructions, input=message)
        return response.output_text

    async def parse(self, instructions: str, message: str, schema: type[T]) -> T:
        """Structured output: the model must return JSON matching `schema`.

        Rarely the output still fails validation (for example a refusal instead of
        JSON). One retry fixes almost every case.
        """
        for attempt in (1, 2):
            try:
                response = await self.client.responses.parse(
                    model=self.name, instructions=instructions, input=message, text_format=schema
                )
                if response.output_parsed is not None:
                    return response.output_parsed
            except ValidationError:
                if attempt == 2:
                    raise
        raise ValueError("The model returned no parsable output.")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(model=self.embedding_name, input=texts)
        return [item.embedding for item in response.data]

    def agent_client(self) -> FoundryChatClient:
        """Chat client for Microsoft Agent Framework agents, created once and reused."""
        if self._agent_client is None:
            self._agent_client = FoundryChatClient(
                project_endpoint=self.project_endpoint,
                model=self.name,
                credential=self.credential,
            )
        return self._agent_client

    async def aclose(self) -> None:
        await self.client.close()
        await self.credential.close()


class OfflineModels:
    """No network, no randomness. Good enough to exercise the plumbing, not to be smart."""

    offline = True
    name = "offline"

    async def chat(self, instructions: str, message: str) -> str:
        return f"(offline mode) You asked: {message[:200]}"

    async def parse(self, instructions: str, message: str, schema: type[T]) -> T:
        raise NotImplementedError("Offline mode has no structured output; services handle it.")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [hashed_embedding(text) for text in texts]

    def agent_client(self) -> FoundryChatClient:
        raise RuntimeError("Agents need a real model. Set LLM_MODE=foundry.")

    async def aclose(self) -> None:
        return None


Models = FoundryModels | OfflineModels


def make_models(settings: Settings) -> Models:
    """Real Foundry models, or offline stand-ins when LLM_MODE=offline."""
    if settings.llm_mode is LLMMode.OFFLINE:
        return OfflineModels()
    return FoundryModels(settings)


def hashed_embedding(text: str, dims: int = 512) -> list[float]:
    """Bag-of-words vector via the hashing trick: shared words -> similar vectors."""
    vector = [0.0] * dims
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        token = token[:-1] if len(token) > 3 and token.endswith("s") else token
        slot = int(hashlib.md5(token.encode(), usedforsecurity=False).hexdigest(), 16) % dims
        vector[slot] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]

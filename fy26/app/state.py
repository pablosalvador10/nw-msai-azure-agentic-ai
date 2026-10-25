"""Per-process state shared by every request: settings, model clients, the handbook index."""

import asyncio
import logging

from app.config import Settings
from app.models import Models, make_models
from app.rag import HandbookIndex

log = logging.getLogger(__name__)


class AppState:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.models: Models = make_models(settings)
        self._index: HandbookIndex | None = None
        self._lock = asyncio.Lock()

    @property
    def offline(self) -> bool:
        return self.models.offline

    @property
    def index_ready(self) -> bool:
        return self._index is not None

    async def index(self) -> HandbookIndex:
        """Build the handbook index on first use, then reuse it."""
        if self._index is None:
            async with self._lock:
                if self._index is None:
                    self._index = await HandbookIndex.build(self.models)
                    log.info("Handbook index built: %d chunks", len(self._index.chunks))
        return self._index

    async def warm_up(self) -> None:
        """Try to build the index at startup; if Azure is not ready yet, build it later."""
        try:
            await self.index()
        except Exception as exc:  # noqa: BLE001 - startup must not crash on a transient error
            log.warning("Index not built at startup (%s). It will be built on first use.", exc)

    async def aclose(self) -> None:
        await self.models.aclose()

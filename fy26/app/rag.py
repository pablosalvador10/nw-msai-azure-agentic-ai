"""Retrieval over the Lakeshore Ride handbook, built from scratch.

1. Split every handbook page into sections (chunks).
2. Turn each chunk into a vector with an embedding model.
3. For a question, embed it too and return the chunks whose vectors point the
   same way (cosine similarity).

No vector database: 40 chunks fit in memory. The same idea scales to millions of
chunks with a search service such as Azure AI Search.
"""

import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.models import Models

HANDBOOK_DIR = Path(__file__).parent / "data" / "handbook"


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    title: str
    heading: str
    text: str

    def render(self) -> str:
        return f"[{self.doc_id}] {self.title} > {self.heading}\n{self.text}"


@lru_cache
def load_chunks(directory: Path = HANDBOOK_DIR) -> tuple[Chunk, ...]:
    """Split every handbook page into one chunk per `##` section."""
    chunks: list[Chunk] = []
    for path in sorted(directory.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _split_front_matter(raw)
        doc_id, title = meta.get("id", path.stem), meta.get("title", path.stem)
        for heading, text in _sections(body):
            chunks.append(Chunk(doc_id=doc_id, title=title, heading=heading, text=text))
    return tuple(chunks)


def doc_ids() -> set[str]:
    """The ids of all handbook pages, for validating citations."""
    return {chunk.doc_id for chunk in load_chunks()}


def _split_front_matter(raw: str) -> tuple[dict[str, str], str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, flags=re.DOTALL)
    if not match:
        return {}, raw
    meta = dict(line.split(":", 1) for line in match.group(1).splitlines() if ":" in line)
    return {k.strip(): v.strip() for k, v in meta.items()}, match.group(2)


def _sections(body: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    heading, lines = "Overview", []
    for line in body.splitlines():
        if line.startswith("## "):
            if "".join(lines).strip():
                sections.append((heading, "\n".join(lines).strip()))
            heading, lines = line[3:].strip(), []
        elif not line.startswith("# "):
            lines.append(line)
    if "".join(lines).strip():
        sections.append((heading, "\n".join(lines).strip()))
    return sections


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity: 1 means same direction, 0 means unrelated."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


class HandbookIndex:
    def __init__(self, chunks: tuple[Chunk, ...], vectors: list[list[float]]) -> None:
        self.chunks = chunks
        self.vectors = vectors

    @classmethod
    async def build(cls, models: Models) -> "HandbookIndex":
        chunks = load_chunks()
        vectors = await models.embed([chunk.render() for chunk in chunks])
        return cls(chunks, vectors)

    async def search(self, models: Models, query: str, top_k: int = 4) -> list[tuple[Chunk, float]]:
        [query_vector] = await models.embed([query])
        scored = [
            (chunk, cosine(query_vector, vector)) for chunk, vector in zip(self.chunks, self.vectors, strict=True)
        ]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

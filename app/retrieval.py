"""
Corpus loading, chunking and embedding search.

Documents are split by `##` section. Every chunk keeps its document's date so
the LLM can tell a current policy from a superseded one.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Awaitable, Callable, List, Optional, Tuple

import numpy as np

# embed(texts, input_type) -> (len(texts), dim) array; input_type is "passage" or "query"
Embedder = Callable[[List[str], str], Awaitable[np.ndarray]]

_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_DATE_RE = re.compile(rf"\b({_MONTHS}) (?:(\d{{1,2}}), )?(\d{{4}})\b")
_TIER_RE = re.compile(r"^\*\*Tier\*\*:\s*(\w+)", re.MULTILINE)
_HEADER_LINES = 8  # the document date and tier always sit right under the title
# Without a cap, one many-sectioned document can fill every slot and crowd out
# the other documents a multi-part question needs.
MAX_PER_SOURCE = 3


@dataclass(frozen=True)
class Chunk:
    source: str  # file name, e.g. "refund_basic.md"
    title: str
    section: str
    doc_date: Optional[date]
    text: str
    tier: Optional[str] = None  # lowercase, from the header line "**Tier**: Basic", if the document has one

    def embedding_text(self) -> str:
        return f"{self.title} - {self.section}\n{self.text}"


def parse_doc_date(markdown: str) -> Optional[date]:
    """First date in the document header ("June 1, 2023" or "July 2024")."""
    header = "\n".join(markdown.splitlines()[:_HEADER_LINES])
    match = _DATE_RE.search(header)
    if not match:
        return None
    month, day, year = match.groups()
    return datetime.strptime(f"{month} {day or 1} {year}", "%B %d %Y").date()


def parse_tier(markdown: str) -> Optional[str]:
    """Tier named in the document header ("**Tier**: Basic"), lowercased, if it has one."""
    header = "\n".join(markdown.splitlines()[:_HEADER_LINES])
    match = _TIER_RE.search(header)
    return match.group(1).lower() if match else None


def chunk_document(source: str, markdown: str) -> List[Chunk]:
    """One chunk per `##` section, plus the preamble if it has content."""
    lines = markdown.splitlines()
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), source)
    doc_date = parse_doc_date(markdown)
    tier = parse_tier(markdown)

    sections: List[Tuple[str, List[str]]] = [("Overview", [])]
    for line in lines:
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif not line.startswith("# "):
            sections[-1][1].append(line)

    chunks = []
    for section, body in sections:
        text = "\n".join(body).strip()
        if text:
            chunks.append(Chunk(source, title, section, doc_date, text, tier))
    return chunks


def load_corpus(corpus_dir: Path) -> List[Chunk]:
    chunks: List[Chunk] = []
    for path in sorted(corpus_dir.glob("*.md")):
        chunks.extend(chunk_document(path.name, path.read_text(encoding="utf-8")))
    return chunks


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.where(norms == 0, 1.0, norms)


class CorpusIndex:
    """In-memory cosine-similarity index over corpus chunks."""

    def __init__(self, chunks: List[Chunk], vectors: np.ndarray, embed: Embedder):
        self.chunks = chunks
        self._vectors = _normalize(np.asarray(vectors, dtype=np.float32))
        self._embed = embed

    @classmethod
    async def build(cls, corpus_dir: Path, embed: Embedder) -> "CorpusIndex":
        chunks = load_corpus(corpus_dir)
        if not chunks:
            raise RuntimeError(f"No corpus documents found in {corpus_dir}")
        vectors = await embed([c.embedding_text() for c in chunks], "passage")
        return cls(chunks, vectors, embed)

    async def search(self, query: str, k: int = 8) -> List[Tuple[Chunk, float]]:
        query_vector = _normalize(np.asarray(await self._embed([query], "query"), dtype=np.float32))[0]
        scores = self._vectors @ query_vector
        hits: List[Tuple[Chunk, float]] = []
        per_source: dict = {}
        for i in np.argsort(-scores):
            chunk = self.chunks[i]
            if per_source.get(chunk.source, 0) < MAX_PER_SOURCE:
                per_source[chunk.source] = per_source.get(chunk.source, 0) + 1
                hits.append((chunk, float(scores[i])))
                if len(hits) == k:
                    break
        return hits

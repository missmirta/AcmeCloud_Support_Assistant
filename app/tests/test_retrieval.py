"""Corpus chunking, document dating and ranking."""

import asyncio
from datetime import date
from pathlib import Path

import numpy as np

from retrieval import MAX_PER_SOURCE, Chunk, CorpusIndex, chunk_document, load_corpus, parse_doc_date

CORPUS = Path(__file__).resolve().parents[2] / "corpus"












def test_every_corpus_document_is_dated_and_conflicting_docs_are_ordered():
    """The 'newest wins' rule only works if both sides of a conflict carry a date."""
    chunks = load_corpus(CORPUS)
    dates = {c.source: c.doc_date for c in chunks}

    assert len(dates) == len(list(CORPUS.glob("*.md")))
    assert all(d is not None for d in dates.values())
    assert dates["pricing_2024_q3.md"] > dates["pricing_2024_q1.md"]
    assert dates["data_retention_policy.md"] > dates["data_retention.md"]


def test_search_ranks_by_cosine_similarity(tmp_path):
    (tmp_path / "a.md").write_text("# A\n\n## Refunds\nrefund text\n\n## Pricing\nprice text\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("# B\n\n## Support\nsupport text\n", encoding="utf-8")
    axes = {"refund": [1, 0, 0], "price": [0, 1, 0], "support": [0, 0, 1]}

    async def embed(texts, input_type):
        return np.array([next(v for k, v in axes.items() if k in t.lower()) for t in texts], dtype=float)

    async def run():
        index = await CorpusIndex.build(tmp_path, embed)
        return await index.search("what is the price?", k=2)

    hits = asyncio.run(run())

    assert len(hits) == 2
    assert hits[0][0].section == "Pricing"
    assert hits[0][1] > hits[1][1]



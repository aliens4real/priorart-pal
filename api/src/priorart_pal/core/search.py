"""Retrieval service.

Embeds a user query via Voyage and runs cosine ANN against the
embeddings table via pgvector. Returns ranked patent chunks with
metadata sufficient for both API responses and downstream rerank
+ generation.

This is the pure retrieval layer. Phase 3 wraps a Cohere reranker
around it; Phase 3 also adds the structural overlay. Keeping that
logic outside `search_basic` so the basic path stays simple.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from priorart_pal.db.models import Embedding, Patent, PatentChunk
from priorart_pal.embed.voyage import VoyageEmbedder
from priorart_pal.logging_config import get_logger

log = get_logger(__name__)


@dataclass
class SearchHit:
    """A single retrieval result."""

    publication_number: str
    title: str | None
    assignee: str | None
    grant_date: date | None
    claim_num: int | None
    chunk_text: str
    distance: float


@dataclass
class SearchOutcome:
    """Everything the API route needs to format a response."""

    hits: list[SearchHit]
    elapsed_ms: int
    embed_elapsed_ms: int
    ann_elapsed_ms: int


async def search_basic(
    session: AsyncSession,
    embedder: VoyageEmbedder,
    *,
    query: str,
    top_k: int = 10,
) -> SearchOutcome:
    """Vanilla two-step retrieval: embed query → cosine ANN top-K.

    No rerank, no structural overlay — that's Phase 3+. Returns the K
    nearest patent chunks by cosine distance, ascending (smaller =
    more similar).
    """
    if not query.strip():
        raise ValueError("query must be non-empty")
    if top_k <= 0 or top_k > 200:
        raise ValueError("top_k must be between 1 and 200")

    started = perf_counter()
    qvec = await embedder.embed_query(query)
    embed_done = perf_counter()

    stmt = (
        select(
            Patent.publication_number,
            Patent.title,
            Patent.assignee,
            Patent.grant_date,
            PatentChunk.claim_num,
            PatentChunk.chunk_text,
            Embedding.embedding.cosine_distance(qvec).label("distance"),
        )
        .join(PatentChunk, PatentChunk.id == Embedding.chunk_id)
        .join(Patent, Patent.id == PatentChunk.patent_id)
        .order_by("distance")
        .limit(top_k)
    )
    result = await session.execute(stmt)
    rows = result.all()
    ann_done = perf_counter()

    hits = [
        SearchHit(
            publication_number=row.publication_number,
            title=row.title,
            assignee=row.assignee,
            grant_date=row.grant_date,
            claim_num=row.claim_num,
            chunk_text=row.chunk_text,
            distance=float(row.distance),
        )
        for row in rows
    ]

    log.info(
        "search.basic",
        query_len=len(query),
        top_k=top_k,
        hits=len(hits),
        embed_ms=int((embed_done - started) * 1000),
        ann_ms=int((ann_done - embed_done) * 1000),
    )

    return SearchOutcome(
        hits=hits,
        elapsed_ms=int((ann_done - started) * 1000),
        embed_elapsed_ms=int((embed_done - started) * 1000),
        ann_elapsed_ms=int((ann_done - embed_done) * 1000),
    )

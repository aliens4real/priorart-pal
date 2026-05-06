"""POST /search — vanilla retrieval endpoint.

Embeds a query, runs pgvector ANN, returns top-K patent chunks. No
rerank, no generation; that's Phase 3+. This is the lowest-friction
HTTP surface the FastAPI service can expose against the seeded corpus.

Request:
    POST /search
    Content-Type: application/json
    {"query": "free text", "top_k": 10}

Response:
    200 OK
    {
      "hits": [{"publication_number": "...", "distance": 0.42, ...}, ...],
      "elapsed_ms": 187,
      "embed_elapsed_ms": 89,
      "ann_elapsed_ms": 98
    }
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from priorart_pal.core.search import search_basic
from priorart_pal.db.session import get_session
from priorart_pal.embed.voyage import VoyageEmbedder

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=20_000)
    top_k: int = Field(10, ge=1, le=200)


class SearchHitResponse(BaseModel):
    publication_number: str
    title: str | None
    assignee: str | None
    grant_date: date | None
    claim_num: int | None
    chunk_text: str
    distance: float


class SearchResponse(BaseModel):
    hits: list[SearchHitResponse]
    elapsed_ms: int
    embed_elapsed_ms: int
    ann_elapsed_ms: int


@lru_cache
def _embedder() -> VoyageEmbedder:
    """One embedder per process; reused across requests."""
    return VoyageEmbedder()


# `B008` warns against calling Depends() in defaults, but FastAPI's whole
# DI mechanism is built on exactly that. Standard FastAPI idiom; safe.
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=SearchResponse)
async def post_search(
    body: SearchRequest,
    session: SessionDep,
) -> SearchResponse:
    try:
        outcome = await search_basic(
            session,
            _embedder(),
            query=body.query,
            top_k=body.top_k,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return SearchResponse(
        hits=[
            SearchHitResponse(
                publication_number=h.publication_number,
                title=h.title,
                assignee=h.assignee,
                grant_date=h.grant_date,
                claim_num=h.claim_num,
                chunk_text=h.chunk_text,
                distance=h.distance,
            )
            for h in outcome.hits
        ],
        elapsed_ms=outcome.elapsed_ms,
        embed_elapsed_ms=outcome.embed_elapsed_ms,
        ann_elapsed_ms=outcome.ann_elapsed_ms,
    )

"""Voyage AI embedding client.

Thin wrapper around `voyageai.AsyncClient` that:
  - Reads the API key from settings (never logs it).
  - Pins the model + dimension to what the rest of the system expects.
  - Handles batching (Voyage caps at 128 texts per call for voyage-3-large).
  - Retries on transient errors with exponential backoff.

Two `input_type` modes — they matter for retrieval quality:

  - 'document'  for corpus chunks (ingestion)
  - 'query'     for user search queries (live)

Voyage embeds them with different prompt prefixes; mismatching them
costs ~3-5pp on retrieval benchmarks vs. matched.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import voyageai

from priorart_pal.logging_config import get_logger
from priorart_pal.settings import get_settings

# The Voyage SDK logs full request bodies (including every doc text)
# at INFO under the "voyage" logger (NOT "voyageai" — there's a
# single-letter difference). We have our own structured retry/timing
# logs; this kills the spam.
logging.getLogger("voyage").setLevel(logging.WARNING)

log = get_logger(__name__)

# voyage-3-large per-call ceiling (verify in docs if model changes)
VOYAGE_BATCH_SIZE = 128
MAX_RETRIES = 4
BACKOFF_BASE_SEC = 1.5


@dataclass
class EmbedResult:
    embeddings: list[list[float]]
    total_tokens: int
    model: str
    input_type: str


class VoyageEmbedder:
    """Async embedder. Reuse one instance per process (the SDK keeps an
    HTTP connection pool internally)."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        settings = get_settings()
        self.model = model or settings.embedding_model
        key = api_key or settings.voyage_api_key
        if not key:
            raise RuntimeError(
                "PAP_VOYAGE_API_KEY not set. Add it to .env (or Secrets Manager "
                "in production) before calling the embedder."
            )
        # AsyncClient isn't in voyageai.__all__; mypy can't see it.
        self._client = voyageai.AsyncClient(api_key=key)  # type: ignore[attr-defined]

    async def embed_documents(self, texts: list[str]) -> EmbedResult:
        """Embed a list of corpus chunks. Batches automatically."""
        return await self._embed(texts, input_type="document")

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single user query. Returns the vector directly."""
        result = await self._embed([text], input_type="query")
        return result.embeddings[0]

    async def _embed(self, texts: list[str], *, input_type: str) -> EmbedResult:
        if not texts:
            return EmbedResult(
                embeddings=[],
                total_tokens=0,
                model=self.model,
                input_type=input_type,
            )

        all_vecs: list[list[float]] = []
        total_tokens = 0
        for batch_start in range(0, len(texts), VOYAGE_BATCH_SIZE):
            batch = texts[batch_start : batch_start + VOYAGE_BATCH_SIZE]
            response = await self._embed_batch_with_retry(batch, input_type=input_type)
            all_vecs.extend(response.embeddings)
            total_tokens += int(response.total_tokens)
        return EmbedResult(
            embeddings=all_vecs,
            total_tokens=total_tokens,
            model=self.model,
            input_type=input_type,
        )

    async def _embed_batch_with_retry(
        self, batch: list[str], *, input_type: str
    ) -> Any:
        for attempt in range(MAX_RETRIES + 1):
            try:
                return await self._client.embed(
                    texts=batch,
                    model=self.model,
                    input_type=input_type,
                )
            except Exception as exc:  # noqa: BLE001 — Voyage SDK errors aren't fully typed
                if attempt == MAX_RETRIES:
                    raise
                wait = BACKOFF_BASE_SEC * (2**attempt)
                log.warning(
                    "voyage.retry",
                    attempt=attempt + 1,
                    of=MAX_RETRIES + 1,
                    wait_sec=wait,
                    error_class=type(exc).__name__,
                )
                await asyncio.sleep(wait)
        raise RuntimeError("unreachable")  # for mypy

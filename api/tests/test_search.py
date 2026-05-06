"""Tests for /search.

Two flavors:

- **Schema tests** (always run): verify the request validation rejects
  the wrong shapes — empty query, top_k out of bounds. These don't
  touch the embedder or the database.

- **Integration test** (`@pytest.mark.local_db`): hits /search end-to-
  end against a populated local database and a live Voyage call. Skipped
  in CI because it needs the seeded corpus + a Voyage API key. Set
  `PAP_RUN_LOCAL_DB_TESTS=1` to opt in locally.
"""
from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

from priorart_pal.main import app


@pytest.mark.asyncio
async def test_search_rejects_empty_query() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/search", json={"query": "", "top_k": 5})
    # Pydantic v2 emits 422 for min_length violations.
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_rejects_invalid_top_k() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/search", json={"query": "anything", "top_k": 9999})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_rejects_negative_top_k() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/search", json={"query": "anything", "top_k": -1})
    assert resp.status_code == 422


@pytest.mark.skipif(
    os.environ.get("PAP_RUN_LOCAL_DB_TESTS") != "1",
    reason="needs seeded local DB + Voyage key; opt in via PAP_RUN_LOCAL_DB_TESTS=1",
)
@pytest.mark.asyncio
async def test_search_returns_relevant_hits_against_seed_corpus() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/search",
            json={
                "query": (
                    "perception module that detects pedestrians and cyclists "
                    "ahead of the vehicle using camera and lidar fusion"
                ),
                "top_k": 5,
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "hits" in body
    assert "elapsed_ms" in body
    assert len(body["hits"]) == 5
    # Distances should be ascending (nearest first).
    distances = [h["distance"] for h in body["hits"]]
    assert distances == sorted(distances)
    # Every hit has a publication_number with the expected US-... shape.
    for hit in body["hits"]:
        assert hit["publication_number"].startswith("US-")
        assert isinstance(hit["chunk_text"], str)
        assert len(hit["chunk_text"]) > 0

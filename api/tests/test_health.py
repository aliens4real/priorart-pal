"""Smoke-test the /health endpoint via FastAPI's TestClient.

`httpx.AsyncClient` with `ASGITransport` runs the app in-process — no real
network, no port binding. Fast and CI-safe.
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from priorart_pal.main import app


@pytest.mark.asyncio
async def test_health_returns_ok() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body

# api/ — FastAPI backend

The Python web service that serves the search/RAG endpoints. Runs in Docker on AWS App Runner in production; locally on `uvicorn` for dev.

## What FastAPI is (and why we use it)

FastAPI is an async-first Python web framework built on Starlette + Pydantic. The "async-first" part matters because RAG is heavily IO-bound — we wait on Postgres, Voyage, Cohere, and Anthropic on every request. Async lets a single worker handle many concurrent requests without blocking on those waits.

The Pydantic part matters because every request body, response, and config setting is a typed model — you get OpenAPI docs and runtime validation for free, and your IDE will tell you when you've broken a contract.

## Local dev

```bash
cd api
uv sync                       # install
uv run uvicorn priorart_pal.main:app --reload --port 8000
curl http://localhost:8000/health
```

OpenAPI docs at `http://localhost:8000/docs` once running.

## Test

```bash
uv run pytest -q
```

## Why a `src/priorart_pal/` layout

The `src/<package>/` layout (PEP 517 standard) prevents accidentally importing the project from the working directory instead of the installed package — a common bug class in Python projects. Tests run against the installed package, so they catch import / packaging mistakes that would bite in production.

## Configuration

`settings.py` uses `pydantic-settings`, which:

1. Reads from environment variables (production)
2. Falls back to a `.env` file (local dev only — `.env` is gitignored)
3. Validates types at startup — wrong type = app won't boot

In production, App Runner injects env vars from Secrets Manager via the IAM role from `infra/stacks/app_runner_stack.py`. We never read secrets from disk.

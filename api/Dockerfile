# Multi-stage build keeps the final image small.
# Stage 1 builds the wheel; stage 2 runs it.

FROM python:3.14-slim AS builder

# uv installed as a static binary — no Python dependency conflicts
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /usr/local/bin/uv

WORKDIR /build
COPY pyproject.toml uv.lock* ./
COPY src ./src

# Compile to a wheel that the runtime stage can install.
RUN uv venv /opt/venv \
 && uv sync --frozen --no-dev --no-install-project \
 && uv pip install --no-deps . \
 && rm -rf /root/.cache /tmp/uv

FROM python:3.14-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# App Runner expects the container to listen on $PORT (default 8000).
EXPOSE 8000

# Single worker is correct for App Runner — it provisions a separate
# container per concurrent request slice. Within a worker, async handles
# IO concurrency.
CMD ["uvicorn", "priorart_pal.main:app", "--host", "0.0.0.0", "--port", "8000"]

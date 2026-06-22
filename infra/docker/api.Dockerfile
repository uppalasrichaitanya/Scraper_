# ─── FastAPI API Dockerfile ───────────────────────────────────────────────────
FROM python:3.11-slim AS base

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

WORKDIR /app

# ── Dependencies layer ────────────────────────────────────────────────────────
FROM base AS deps

COPY pyproject.toml .
COPY uv.lock* .

RUN uv sync --no-dev --no-install-project

# ── Development image (default) ───────────────────────────────────────────────
FROM base AS development

COPY pyproject.toml .
COPY uv.lock* .

RUN uv sync --no-install-project

COPY . .

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production image ─────────────────────────────────────────────────────────
FROM base AS production

COPY --from=deps /app/.venv /app/.venv

COPY . .

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

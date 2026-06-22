# ─── Crawler / Celery Dockerfile ─────────────────────────────────────────────
# Uses Playwright which requires specific browser binaries + system deps
FROM python:3.11-slim AS base

# System dependencies for Playwright + Scrapy
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    # Playwright system deps
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1 \
    libdbus-1-3 \
    # Scrapy deps
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

# ── Dependencies ──────────────────────────────────────────────────────────────
FROM base AS deps

COPY pyproject.toml .
COPY uv.lock* .

RUN uv sync --no-dev --no-install-project

# Install Playwright browsers (Chromium only — smallest footprint)
RUN .venv/bin/playwright install chromium --with-deps

# ── Development image ─────────────────────────────────────────────────────────
FROM base AS development

COPY pyproject.toml .
COPY uv.lock* .

RUN uv sync --frozen

# Install Playwright browsers
RUN uv run playwright install chromium --with-deps

COPY . .

# Default: Celery worker
CMD ["uv", "run", "celery", "-A", "crawler.celery_app", "worker", "--loglevel=info", "-c", "4"]

# ── Production image ──────────────────────────────────────────────────────────
FROM base AS production

COPY --from=deps /app/.venv /app/.venv
COPY --from=deps /root/.cache/ms-playwright /root/.cache/ms-playwright

COPY . .

ENV PATH="/app/.venv/bin:$PATH"

CMD ["celery", "-A", "crawler.celery_app", "worker", "--loglevel=info", "-c", "4"]

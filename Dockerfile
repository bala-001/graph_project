# PAIQ 11.3 D-extraction service image.
# Defaults are SAFE: offline MockProvider, D feature flag OFF. A real rollout
# sets PAIQ_PROVIDER + PAIQ_D_EXTRACTION_ENABLED and mounts provider keys.
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PAIQ_PROVIDER=mock \
    PAIQ_D_EXTRACTION_ENABLED=false \
    PAIQ_JOURNAL_DIR=/data/journals

WORKDIR /app

# Install deps first for layer caching. Providers + eval extras included so the
# image can run real extraction and the eval runners; dev/test tooling is not.
COPY pyproject.toml README.md ./
COPY src ./src
COPY eval ./eval
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[providers,eval]"

# Non-root runtime user; journals live on a writable volume.
RUN useradd --create-home --uid 10001 paiq \
    && mkdir -p /data/journals \
    && chown -R paiq:paiq /data
USER paiq

# Healthcheck: the CLI resolves config without network or keys.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["paiq-d", "flag"]

ENTRYPOINT ["paiq-d"]
CMD ["flag"]

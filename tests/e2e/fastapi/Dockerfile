FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /workspace

COPY . /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN uv sync --frozen --group dev

RUN groupadd --system appuser \
    && useradd --system --gid appuser --create-home --home-dir /home/appuser appuser \
    && chown -R appuser:appuser /workspace

USER appuser

ENTRYPOINT []

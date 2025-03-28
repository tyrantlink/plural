FROM python:3.13-slim

WORKDIR /app

COPY metrics metrics
COPY .git .git
COPY shared shared

RUN pip install uv

WORKDIR /app/metrics

RUN uv sync

RUN apt-get update && \
    apt-get install -y \
    git \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

CMD uv run main.py

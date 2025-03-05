FROM python:3.13-slim

WORKDIR /app

COPY api api
COPY shared shared

RUN pip install uv

WORKDIR /app/api

RUN uv sync

RUN apt-get update && \
    apt-get install -y \
    git \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

EXPOSE 8080

CMD uv run main.py

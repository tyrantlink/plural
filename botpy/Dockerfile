FROM python:3.13-slim

WORKDIR /app

COPY botpy botpy
COPY .git .git
COPY shared shared

RUN pip install uv

WORKDIR /app/botpy

RUN apt-get update && \
    apt-get install -y \
    git \
    curl \
    gcc \
    libc6-dev \
    pkg-config \
    libssl-dev \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --profile minimal --default-toolchain stable && \
    rm -rf /root/.cargo/registry /root/.cargo/git

ENV PATH="/root/.cargo/bin:${PATH}"

RUN uv sync

RUN uv run main.py stupid-workaround-docker-pain

CMD uv run main.py

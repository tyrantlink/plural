FROM python:3.13-slim

WORKDIR /app

COPY bot bot
COPY shared shared

RUN pip install uv

WORKDIR /app/bot

RUN uv sync

CMD uv run main.py

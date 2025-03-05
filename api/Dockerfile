# Use Python 3.13 as the base image
FROM python:3.13-slim

WORKDIR /app

COPY . .
RUN ls -lah

RUN pip install uv

RUN uv sync

ENV PORT=8080

EXPOSE 8080

CMD uv run main.py

# build
FROM rust:1.85-slim as builder
WORKDIR /app

RUN apt-get update && \
    apt-get install -y \
    cmake \
    pkg-config \
    build-essential \
    libssl-dev \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# do this better
COPY . . 
RUN cargo build --release

# runtime
FROM debian:bookworm-slim
WORKDIR /app

RUN apt-get update && \
    apt-get install -y \
    git \
    libssl3 \
    ca-certificates \
    openssl \
    --no-install-recommends && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/gateway ./gateway
RUN chmod +x /app/gateway

CMD ["./gateway"]

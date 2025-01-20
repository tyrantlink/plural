# build
FROM rust:1.83-slim as builder
WORKDIR /app

RUN apt-get update && \
    apt-get install -y \
    cmake \
    pkg-config \
    build-essential \
    libssl-dev \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

COPY . .
RUN cargo build --release

# runtime
FROM debian:bookworm-slim
WORKDIR /app

RUN apt-get update && \
    apt-get install -y \
    libssl3 \
    ca-certificates \
    openssl \
    --no-install-recommends && \
    update-ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/egress-proxy ./egress-proxy
RUN chmod +x /app/egress-proxy

CMD ["./egress-proxy"]

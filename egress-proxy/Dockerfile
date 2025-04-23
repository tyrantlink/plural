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


COPY Cargo.toml .
COPY core core
COPY gateway gateway
COPY egress-proxy egress-proxy

RUN cargo build -rp egress-proxy

# runtime
FROM debian:bookworm-slim
WORKDIR /app

RUN apt-get update && \
    apt-get install -y \
    git \
    libssl-dev \
    ca-certificates \
    openssl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/egress-proxy ./egress-proxy
COPY .git .git
RUN chmod +x ./egress-proxy

EXPOSE 8086

CMD ["./egress-proxy"]

# build
from rustlang/rust:nightly as builder

workdir /app

run apt-get update && \
    apt-get install -y \
    cmake \
    pkg-config \
    build-essential \
    libssl-dev \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

copy Cargo.toml .
copy rust-toolchain.toml .
copy core core

copy egress-proxy egress-proxy

copy api/Cargo.toml api/Cargo.toml
copy api/src/main.rs api/src/main.rs
copy bot/Cargo.toml bot/Cargo.toml
copy bot/src/main.rs bot/src/main.rs
copy gateway/Cargo.toml gateway/Cargo.toml
copy gateway/src/main.rs gateway/src/main.rs
copy metrics/Cargo.toml metrics/Cargo.toml
copy metrics/src/main.rs metrics/src/main.rs

run cargo build -rp egress-proxy

# runtime
from debian:bookworm-slim
workdir /app

run apt-get update && \
    apt-get install -y \
    git \
    libssl-dev \
    ca-certificates \
    openssl \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

copy --from=builder /app/target/release/egress-proxy ./egress-proxy
copy .git .git

run chmod +x ./egress-proxy

expose 8086

cmd ["./egress-proxy"]

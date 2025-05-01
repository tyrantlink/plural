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

copy metrics metrics

copy api/Cargo.toml api/Cargo.toml
copy api/src/main.rs api/src/main.rs
copy bot/Cargo.toml bot/Cargo.toml
copy bot/src/main.rs bot/src/main.rs
copy egress-proxy/Cargo.toml egress-proxy/Cargo.toml
copy egress-proxy/src/main.rs egress-proxy/src/main.rs
copy gateway/Cargo.toml gateway/Cargo.toml
copy gateway/src/main.rs gateway/src/main.rs

run cargo build -rp plural-metrics

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

copy --from=builder /app/target/release/plural-metrics ./plural-metrics
copy .git .git

run chmod +x ./plural-metrics

cmd ["./plural-metrics"]

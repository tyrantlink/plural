use std::{sync::OnceLock, time::Duration};

pub use fred::{
    clients::{Client as RedisClient, Pipeline},
    error::Error as RedisError,
    interfaces::{
        KeysInterface,
        RedisJsonInterface,
        SetsInterface,
        StreamsInterface
    },
    types::{
        Expiration,
        SetOptions,
        streams::{XCapKind, XCapTrim}
    }
};
use fred::{
    interfaces::ClientLike,
    types::{
        Builder,
        config::{Config, TcpConfig}
    }
};
use opentelemetry::{
    global,
    trace::{FutureExt, Tracer}
};

use crate::env::env;

static REDIS: OnceLock<RedisClient> = OnceLock::new();

pub async fn init_redis() -> Result<(), Box<dyn std::error::Error>> {
    let tracer = global::tracer("");

    let redis = tracer
        .in_span("initializing redis", |cx| {
            async {
                let redis: RedisClient =
                    Builder::from_config(Config::from_url(&env().redis_url)?)
                        .with_connection_config(|config| {
                            config.connection_timeout = Duration::from_secs(5);

                            config.tcp = TcpConfig {
                                nodelay: Some(true),
                                ..Default::default()
                            }
                        })
                        .build()?;

                redis.init().await?;

                Ok::<RedisClient, RedisError>(redis)
            }
            .with_context(cx)
        })
        .await?;

    REDIS.set(redis).expect("Failed to set Redis client");

    Ok(())
}

pub fn redis() -> &'static RedisClient {
    REDIS.get().expect("Redis client not initialized")
}

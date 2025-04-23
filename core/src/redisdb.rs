use std::sync::OnceLock;
use std::time::Duration;

use fred::{
    clients::Client,
    interfaces::ClientLike,
    types::{
        config::{Config, TcpConfig},
        Builder,
    },
};

use crate::env::env;

static REDIS: OnceLock<Client> = OnceLock::new();

pub async fn init_redis() -> Result<(), Box<dyn std::error::Error>> {
    let redis: Client = Builder::from_config(
        Config::from_url(&env().redis_url)?)
        .with_connection_config(|config| {
            config.connection_timeout = Duration::from_secs(5);
            config.tcp = TcpConfig {
                nodelay: Some(true),
                ..Default::default()
            };
        })
        .build()?;

    redis.init().await?;

    REDIS.set(redis).expect("Failed to set Redis client");

    Ok(())
}

pub fn redis() -> &'static Client {
    REDIS.get().expect("Redis client not initialized")
}
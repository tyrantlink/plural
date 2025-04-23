#[cfg(feature = "version")]
mod version;
#[cfg(feature = "version")]
pub use version::get_version;

#[cfg(feature = "otel")]
mod otel;
#[cfg(feature = "otel")]
pub use otel::init_otel;

#[cfg(feature = "mongo")]
mod mongodb;

#[cfg(feature = "redis")]
mod redisdb;
#[cfg(feature = "redis")]
pub use redisdb::{init_redis, redis};

#[cfg(feature = "http")]
mod http;

#[cfg(feature = "env")]
mod env;
#[cfg(feature = "env")]
pub use env::env;
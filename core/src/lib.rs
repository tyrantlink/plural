#![forbid(unsafe_code)]

pub mod crypto;

#[cfg(feature = "version")]
mod version;
#[cfg(feature = "version")]
pub use version::get_version;

#[cfg(feature = "otel")]
mod otel;
#[cfg(feature = "otel")]
pub use otel::{init_otel, shutdown_otel};

#[cfg(feature = "mongo")]
pub mod db;
#[cfg(feature = "mongo")]
pub use db::{init_mongo, mongo};

#[cfg(feature = "redis")]
pub mod redis;
#[cfg(feature = "redis")]
pub use redis::{init_redis, redis};
// ? i dunno why defining redis twice just *works* but i don't wanna think about
// it

#[cfg(feature = "discord")]
pub mod discord;

#[cfg(feature = "env")]
mod env;
#[cfg(feature = "env")]
pub use env::env;

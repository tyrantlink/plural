#![forbid(unsafe_code)]

use opentelemetry::{
    global,
    trace::{FutureExt, Tracer}
};
use plural_core::{init_mongo, init_otel, init_redis, shutdown_otel};
use tokio::time::sleep;

mod healthcheck;

#[tokio::main]

async fn main() -> Result<(), Box<dyn std::error::Error>> {
    init_otel("bot")?;

    let tracer = global::tracer("");

    tracer
        .in_span("Initializing bot", |cx| async move {
            init_mongo(true).with_context(cx.clone()).await?;

            init_redis().with_context(cx.clone()).await?;

            Ok::<(), Box<dyn std::error::Error>>(())
        })
        .await?;

    healthcheck::spawn_healthcheck_server();

    sleep(std::time::Duration::from_secs(5)).await;

    shutdown_otel()
}

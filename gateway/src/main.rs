use std::env;
use std::error::Error;
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Duration;

use fred::serde_json;
use fred::{
    clients::Client as RedisClient,
    interfaces::{ClientLike, KeysInterface},
    types::{
        config::{Config as RedisConfig, TcpConfig},
        Builder as RedisBuilder,
    },
};
use futures::StreamExt;
use opentelemetry::{
    global,
    KeyValue,
    trace::{Tracer, Span, SpanKind},
};
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::Resource;
use tokio::signal;
use twilight_gateway::{Config, Intents, Message, Shard};
use twilight_http::Client;
use twilight_model::gateway::payload::outgoing::UpdatePresence;
use serde_json::Value;

use twilight_model::gateway::presence;

mod cache;

use version::get_version;
use cache::{cache_and_publish, Response, UNSUPPORTED_EVENTS};

struct Env {
    bot_token: String,
    redis_url: String,
    dev: bool
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let version = get_version("gateway");
    let guild_count = Arc::new(AtomicU64::new(0));
    let user_count = Arc::new(AtomicU64::new(0));

    let dev_env = env::var("DEV").unwrap_or("1".to_string());

    let env = Env {
        bot_token: env::var("BOT_TOKEN")?,
        redis_url: env::var("REDIS_URL")?,
        dev: !(dev_env == "false" || dev_env == "0")
    };

    let otel_resource = Resource::new(vec![
        KeyValue::new("service.name", "gateway"),
        KeyValue::new("service.version", version.clone()),
        KeyValue::new("deployment.environment.name", if env.dev { "dev" } else { "prod" })
    ]);

    if false {
        // ? only set up tracing in dev mode, as it's a lot of unnecessary spans
        global::set_tracer_provider(
            opentelemetry_sdk::trace::TracerProvider::builder()
                .with_resource(otel_resource.clone())
                .with_batch_exporter(
                opentelemetry_otlp::SpanExporter::builder()
                    .with_http()
                    .with_protocol(opentelemetry_otlp::Protocol::HttpBinary)
                    .build()?,
                opentelemetry_sdk::runtime::Tokio)
                .build()
        );
    }

    global::set_meter_provider(
        opentelemetry_sdk::metrics::SdkMeterProvider::builder()
            .with_resource(otel_resource)
            .with_reader(opentelemetry_sdk::metrics::PeriodicReader::builder(
                opentelemetry_otlp::MetricExporter::builder()
                .with_http()
                .with_protocol(opentelemetry_otlp::Protocol::HttpBinary)
                .with_temporality(opentelemetry_sdk::metrics::Temporality::Delta)
                .build()?,
                opentelemetry_sdk::runtime::Tokio)
            .with_interval(Duration::from_secs(60))
            .build())
            .build()
    );

    let redis: RedisClient = RedisBuilder::from_config(
        RedisConfig::from_url(&env.redis_url)?)
        .with_connection_config(|config| {
            config.connection_timeout = Duration::from_secs(5);
            config.tcp = TcpConfig {
                nodelay: Some(true),
                ..Default::default()
            };
        })
        .build()?;

    redis.init().await?;

    let bot = Client::new(env.bot_token.clone());
    let config = Config::new(
        env.bot_token,
        Intents::GUILDS
            | Intents::GUILD_EMOJIS_AND_STICKERS
            | Intents::GUILD_WEBHOOKS
            | Intents::GUILD_MESSAGES
            | Intents::GUILD_MESSAGE_REACTIONS
            | Intents::MESSAGE_CONTENT,
    );

    let shards =
        twilight_gateway::create_recommended(&bot, config, |_, builder| builder.build()).await?;
    let mut senders = Vec::with_capacity(shards.len());
    let mut tasks = Vec::with_capacity(shards.len());

    println!("event forwarding with {} shards v{}", shards.len(), version);

    for shard in shards {
        senders.push(shard.sender());
        tasks.push(tokio::spawn(runner(shard, redis.clone())));
    }

    let _ = tokio::spawn({
        let senders = senders.clone();
        let redis = redis.clone();
        let guild_count = guild_count.clone();
        let user_count = user_count.clone();

        async move {
            let mut interval = tokio::time::interval(Duration::from_secs(300));

            loop {
                interval.tick().await;

                match (
                    redis.get::<Option<u64>, _>("discord_guilds").await,
                    redis.get::<Option<u64>, _>("discord_users").await
                ) {
                    (Ok(Some(guilds)), Ok(Some(users))) => {
                        let previous_guilds = guild_count.swap(guilds, Ordering::SeqCst);
                        let previous_users = user_count.swap(users, Ordering::SeqCst);

                        if previous_guilds == guilds && previous_users == users {
                            continue;
                        }

                        let status = format!(
                            "/help | {} servers, {} users",
                            format_count(guilds),
                            format_count(users)
                        );

                        println!("Updating presence to: {}", status);

                        let presence = UpdatePresence::new(
                            vec![presence::Activity {
                                application_id: None,
                                assets: None,
                                buttons: Vec::new(),
                                created_at: None,
                                details: None,
                                emoji: None,
                                flags: None,
                                id: None,
                                instance: None,
                                kind: presence::ActivityType::Custom,
                                name: status.clone(),
                                party: None,
                                secrets: None,
                                state: Some(status),
                                timestamps: None,
                                url: None}],
                            false,
                            None,
                            presence::Status::Online,
                        ).unwrap();

                        for sender in &senders {
                            let _ = sender.command(&presence);
                        }
                    }
                    _ => {
                        println!("Failed to get guild/user count");
                    }
                }
            }
        }
    }).await?;

    signal::ctrl_c().await?;

    Ok(())
}

fn format_count(n: u64) -> String {
    n.to_string()
        .as_bytes()
        .rchunks(3)
        .rev()
        .map(std::str::from_utf8)
        .collect::<Result<Vec<&str>, _>>()
        .unwrap()
        .join(",")
}

async fn runner(mut shard: Shard, redis: RedisClient) {
    while let Some(message) = shard.next().await {
        match message {
            Ok(Message::Text(json_str)) => tokio::spawn(handle_message(json_str, redis.clone())),
            _ =>  continue
        };
    }
}

async fn handle_message(json_str: String, redis: RedisClient) {
    let json: Value = serde_json::from_str(&json_str).unwrap();

    let event_name = json["t"]
        .as_str()
        .unwrap_or("UNKNOWN")
        .to_string();

    if UNSUPPORTED_EVENTS.contains(&event_name.as_str()) ||
       json.get("d").is_none() {
        return;
    }
    
    let tracer = global::tracer("");

    let mut span = tracer
        .span_builder(event_name.to_owned())
        .with_kind(SpanKind::Client)
        .start(&tracer);

    match cache_and_publish(redis, json).await
    {
        Ok(Response::Published) => {
            println!("published {}", event_name);
            span.set_attribute(KeyValue::new("result", "published"));
        }
        Ok(Response::Duplicate) => {
            println!("duplicate {}", event_name);
            span.set_attribute(KeyValue::new("result", "duplicate"));
        }
        Ok(Response::Cached) => {
            println!("cached    {}", event_name);
            span.set_attribute(KeyValue::new("result", "cached"));
        }
        Ok(Response::Unsupported) => {
            println!("unsupport {}", event_name);
            span.set_attribute(KeyValue::new("result", "unsupported"));
        }
        Err(e) => {
            println!("Failed to publish event: {:?}", e);
            span.set_attribute(KeyValue::new("result", "error"));
            span.set_status(opentelemetry::trace::Status::Error {
                description: e.to_string().into()
            });
        }
    }
}

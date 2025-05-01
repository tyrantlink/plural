mod cache;

use std::{
    error::Error,
    sync::{
        Arc,
        atomic::{AtomicU64, Ordering}
    },
    time::Duration
};

use cache::{Response, UNSUPPORTED_EVENTS, cache_and_publish};
use futures::StreamExt;
use plural_core::{
    env,
    get_version,
    init_otel,
    init_redis,
    redis,
    redis::KeysInterface,
    shutdown_otel
};
use serde_json::Value;
use tokio::signal;
use twilight_gateway::{CloseFrame, Config, Intents, Message, Shard};
use twilight_http::Client;
use twilight_model::gateway::{payload::outgoing::UpdatePresence, presence};

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let version = get_version("gateway");
    let guild_count = Arc::new(AtomicU64::new(0));
    let user_count = Arc::new(AtomicU64::new(0));

    init_otel("gateway")?;

    init_redis().await?;

    let bot = Client::new(env().bot_token.clone());
    let config = Config::new(
        env().bot_token.clone(),
        Intents::GUILDS |
            Intents::GUILD_EMOJIS_AND_STICKERS |
            Intents::GUILD_WEBHOOKS |
            Intents::GUILD_MESSAGES |
            Intents::GUILD_MESSAGE_REACTIONS |
            Intents::MESSAGE_CONTENT
    );

    let shards =
        twilight_gateway::create_recommended(&bot, config, |_, builder| {
            builder.build()
        })
        .await?;

    let mut senders = Vec::with_capacity(shards.len());
    let mut tasks = Vec::with_capacity(shards.len());

    println!("event forwarding with {} shards v{}", shards.len(), version);

    for shard in shards {
        senders.push(shard.sender());
        tasks.push(tokio::spawn(runner(shard)));
    }

    let presence_task = tokio::spawn({
        let senders = senders.clone();
        let guild_count = guild_count.clone();
        let user_count = user_count.clone();

        async move {
            let mut interval = tokio::time::interval(Duration::from_secs(10));

            loop {
                interval.tick().await;

                match (
                    redis().get::<Option<u64>, _>("discord_guilds").await,
                    redis().get::<Option<u64>, _>("discord_users").await
                ) {
                    (Ok(Some(guilds)), Ok(Some(users))) => {
                        let previous_guilds =
                            guild_count.swap(guilds, Ordering::SeqCst);

                        let previous_users =
                            user_count.swap(users, Ordering::SeqCst);

                        if previous_guilds == guilds && previous_users == users
                        {
                            continue;
                        }

                        let status = format!(
                            "/help | {} servers, {} users",
                            format_count(guilds),
                            format_count(users)
                        );

                        println!("Updating presence to: {status}");

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
                                url: None
                            }],
                            false,
                            None,
                            presence::Status::Online
                        )
                        .unwrap();

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
    });

    tokio::select! {
        _ = signal::ctrl_c() => {}
        _ = presence_task => {}
    }

    for shard in senders {
        shard.close(CloseFrame::NORMAL)?;
    }

    shutdown_otel()
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

async fn runner(mut shard: Shard) {
    while let Some(message) = shard.next().await {
        match message {
            Ok(Message::Text(json_str)) => tokio::spawn(handle_message(json_str)),
            _ => continue
        };
    }
}

async fn handle_message(json_str: String) {
    let json: Value = serde_json::from_str(&json_str).unwrap();

    let event_name = json["t"].as_str().unwrap_or("UNKNOWN").to_string();

    if UNSUPPORTED_EVENTS.contains(&event_name.as_str()) ||
        json.get("d").is_none()
    {
        return;
    }

    match cache_and_publish(json).await {
        Ok(Response::Published) => {
            println!("published {event_name}");
        }
        Ok(Response::Duplicate) => {
            println!("duplicate {event_name}");
        }
        Ok(Response::Cached) => {
            println!("cached    {event_name}");
        }
        Ok(Response::Unsupported) => {
            println!("unsupport {event_name}");
        }
        Err(e) => {
            println!("Failed to publish event: {e:?}");
        }
    }
}

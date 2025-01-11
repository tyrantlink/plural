use twilight_gateway::{Message, Intents, Config, stream::{self, ShardMessageStream}};
use twilight_http::Client;
use futures::StreamExt;
use serde::Deserialize;
use std::error::Error;
use std::fs;
use fred::{
    clients::Client as RedisClient, interfaces::ClientLike, prelude::FunctionInterface, types::{
        config::Config as RedisConfig,
        Builder as RedisBuilder
    }
};

#[derive(Deserialize)]
struct Project {
    bot_token: String,
    redis_url: String,
}

async fn load_project() -> Result<Project, Box<dyn Error>> {
    let project_str: String = fs::read_to_string("project.toml")?;
    Ok(toml::from_str(&project_str)?)
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let project: Project = load_project().await?;

    let redis: RedisClient = RedisBuilder::from_config(RedisConfig::from_url(&project.redis_url)?)
        .build()?;

    redis.init().await?;

    let fload: Result<(), fred::prelude::Error> = redis.function_load(
        true,
        include_str!("dedupe_publish.lua")
    ).await;

    match fload {
        Ok(_) => {},
        Err(e) => {
            println!("Failed to load Redis function: {:?}", e);
        }
    }

    let bot = Client::new(project.bot_token.clone());
    let config = Config::new(
        project.bot_token,
        Intents::GUILDS                    |
        Intents::GUILD_EMOJIS_AND_STICKERS |
        Intents::GUILD_WEBHOOKS            |
        Intents::GUILD_MESSAGES            |
        Intents::GUILD_MESSAGE_REACTIONS   |
        Intents::MESSAGE_CONTENT
    );

    let mut shards = stream::create_recommended(&bot, config, |_, builder| builder.build())
        .await?
        .collect::<Vec<_>>();

    println!("event forwarding with {} shards", shards.len());

    let mut stream = ShardMessageStream::new(shards.iter_mut());

    while let Some((_shard, message)) = stream.next().await {
        let message = match message {
            Ok(message) => message,
            Err(_) => {
                continue;
            }
        };

        let json_str: String = match message {
            Message::Text(content) => content,
            Message::Close(_) => {
                continue;
            }
        };

        if json_str.starts_with("{\"t\":\"READY\"") ||
           json_str.starts_with("{\"t\":null")      ||
           json_str.starts_with("{\"t\":\"RESUMED\"")
        {
            continue;
        }

        let mut redis = redis.clone();
        tokio::spawn(async move {
            if let Err(e) = forward_event(&mut redis, json_str).await {
                println!("Error handling event: {:?}", e);
            }
        });
    }

    Ok(())
}

async fn forward_event(
    redis: &mut RedisClient,
    json_str: String,
) -> Result<(), Box<dyn Error>> {
    // normalize sequence number so the body is always the same regardless of gateway connection
    let mut json_str = json_str.clone();

    if let Some(sequence_start) = json_str.find("\"s\":") {
        json_str = json_str.replace(
            &json_str[
                sequence_start..sequence_start +
                json_str[sequence_start..].find(",").unwrap()],
            "\"s\":0"
        )
    }

    let result: i32 = redis.fcall(
        "dedupe_publish",
        &["discord_events"],
        &[&json_str]
    ).await?;

    if result == 0 {
        println!("duplicate event");
        return Ok(());
    }

    let mut event_name = "UNKNOWN";

    if let Some(event_start) = json_str.find("\"t\":\"") {
        event_name = &json_str[
            event_start + 5..json_str[event_start + 5..]
            .find("\"").unwrap() + event_start + 5
        ]
    }

    println!("forwarded {} event", event_name);

    Ok(())
}

use twilight_gateway::{Message, Intents, Config, Shard};
use twilight_http::Client;
use std::error::Error;
use futures::StreamExt;
use std::env;
use tokio::signal;
use fred::{
    clients::Client as RedisClient, interfaces::ClientLike, prelude::FunctionInterface, types::{
        config::Config as RedisConfig,
        Builder as RedisBuilder
    }
};

struct Env {
    bot_token: String,
    redis_url: String,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let env = Env {
        bot_token: env::var("BOT_TOKEN")?,
        redis_url: env::var("REDIS_URL")?,
    };

    let redis: RedisClient = RedisBuilder::from_config(RedisConfig::from_url(&env.redis_url)?)
        .build()?;

    redis.init().await?;

    let fload: Result<(), fred::prelude::Error> = redis.function_load(
        true,
        include_str!("publish.lua")
    ).await;

    match fload {
        Ok(_) => {},
        Err(e) => {
            println!("Failed to load Redis function: {:?}", e);
        }
    }

    let bot = Client::new(env.bot_token.clone());
    let config = Config::new(
        env.bot_token,
        Intents::GUILDS                    |
        Intents::GUILD_EMOJIS_AND_STICKERS |
        Intents::GUILD_WEBHOOKS            |
        Intents::GUILD_MESSAGES            |
        Intents::GUILD_MESSAGE_REACTIONS   |
        Intents::MESSAGE_CONTENT
    );

    let shards =
        twilight_gateway::create_recommended(&bot, config, |_, builder| builder.build()).await?;
    let mut senders = Vec::with_capacity(shards.len());
    let mut tasks = Vec::with_capacity(shards.len());

    println!("event forwarding with {} shards", shards.len());

    for shard in shards {
        senders.push(shard.sender());
        tasks.push(tokio::spawn(runner(shard, redis.clone())));
    }

    signal::ctrl_c().await?;

    Ok(())
}

fn get_event_name(json_str: &str) -> &str {
    match json_str.find("\"t\":") {
        Some(event_start) => {
            &json_str[
                event_start + 5..json_str[event_start + 5..]
                .find("\"").unwrap() + event_start + 5
            ]
        },
        None => "UNKNOWN"
    }
}

async fn runner(mut shard: Shard, redis: RedisClient) {
    while let Some(message) = shard.next().await {
        match message {
            Ok(message) => tokio::spawn(handle_message(message, redis.clone())),
            Err(_) => {
                continue;
            }
        };
    }
}


async fn handle_message(message: Message, redis: RedisClient) {
    let mut json_str: String = match message {
        Message::Text(content) => content,
        Message::Close(_) => {
            return;
        }
    };

    if json_str.starts_with("{\"t\":\"READY\"") ||
       json_str.starts_with("{\"t\":null")      ||
       json_str.starts_with("{\"t\":\"RESUMED\"")
    {
        return;
    }

    if let Some(sequence_start) = json_str.find("\"s\":") {
        json_str = json_str.replace(
            &json_str[
                sequence_start..sequence_start +
                json_str[sequence_start..].find(",").unwrap()],
            "\"s\":0"
        )
    }

    match redis.fcall(
        "publish",
        &["discord_events"],
        &[&json_str]
    ).await {
        Ok(0) => {
            println!("published {}", get_event_name(&json_str));
        },
        Ok(1) => {
            println!("duplicate {}", get_event_name(&json_str));
        },
        Ok(2) => {
            println!("cached    {}", get_event_name(&json_str));
        },
        Ok(3) => {
            println!("unsupport {}", get_event_name(&json_str));
        },
        Ok(result) => {
            println!("unknown   {} response: {}", get_event_name(&json_str), result);
        },
        Err(e) => {
            println!("Failed to publish event: {:?}", e);
        }
    }
}
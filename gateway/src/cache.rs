use std::{hash::{Hash, Hasher}, time::SystemTime, vec, env};

use base64::{prelude::BASE64_STANDARD_NO_PAD, Engine as _};
use fred::{
    clients::{
        Pipeline,
        Client as RedisClient},
    interfaces::{
        KeysInterface,
        RedisJsonInterface,
        StreamsInterface,
        SetsInterface},
    types::{SetOptions, Expiration, streams::{XCapKind, XCapTrim}}
};
use futures::future::join_all;
use lazy_static::lazy_static;
use rustc_hash::FxHasher;
use serde_json::{Value, json};


lazy_static! {
    static ref APPLICATION_ID: String = std::str::from_utf8(
        &BASE64_STANDARD_NO_PAD.decode(
            env::var("BOT_TOKEN")
                .expect("BOT_TOKEN not found")
                .split('.')
                .next()
                .expect("invalid BOT_TOKEN")
        ).expect("invalid BOT_TOKEN")
    ).expect("invalid BOT_TOKEN")
        .to_string();
}

static EMOJI_SHARDS: usize = 10;


static PUBLISHED_EVENTS: [&str; 4] = [
    "MESSAGE_CREATE",
    "MESSAGE_UPDATE",
    "MESSAGE_REACTION_ADD",
    "WEBHOOKS_UPDATE"
];

pub static UNSUPPORTED_EVENTS: [&str; 3] = [
    "READY",
    "RESUMED",
    "UNKNOWN"
];

pub enum Response {
    PUBLISHED,
    DUPLICATE,
    CACHED,
    UNSUPPORTED
}

enum CacheHandler {
    #[allow(non_camel_case_types)]
    MERGE_CREATE,
    DELETE
}


pub async fn cache_and_publish(
    redis: RedisClient,
    json: Value
) -> Result<Response, fred::error::Error> {
    if is_duplicate(&redis, &json).await? {
        return Ok(Response::DUPLICATE);
    }

    let pipeline = redis.pipeline();

    //? cloning here so i don't have to deal with the lifetime issues of the guild create event futures
    let mut response = if cache(&redis, &pipeline, json.clone()).await? {
        Ok(Response::CACHED)
    } else {
        Ok(Response::UNSUPPORTED)
    };

    if PUBLISHED_EVENTS.contains(&json["t"].as_str().unwrap_or("UNKNOWN")) {
        publish(&pipeline, &json).await?;
        response = Ok(Response::PUBLISHED);
    }

    let _: () = pipeline.all().await?;

    response
}

async fn is_duplicate(
    redis: &RedisClient,
    json: &Value
) -> Result<bool, fred::error::Error> {
    let hash = {
        let mut hasher = FxHasher::default();
        json["d"].hash(&mut hasher);
        format!("{:x}", hasher.finish())
    };

    if json["t"].as_str().unwrap_or("UNKNOWN") == "WEBHOOKS_UPDATE" {
        return Ok(false)
    }

    // ? try to figure out why this takes 7ms sometimes
    let response: Option<bool> = redis.set(
        format!("discord:event:{}:{}", json["t"].as_str().unwrap_or("UNKNOWN"), hash),
        "1",
        Some(Expiration::EX(10)),
        Some(SetOptions::NX),
        false
    ).await?;

    Ok(response.is_none())
}

async fn cache(
    redis: &RedisClient,
    pipeline: &Pipeline<RedisClient>,
    json: Value
) -> Result<bool, fred::error::Error> {
    let event_name = json["t"]
        .as_str()
        .unwrap_or("UNKNOWN")
        .to_string();

    let key;
    let mut data;
    let meta;
    let handler;
    let expire;
    let mut futures = Vec::new();

    match event_name.as_str() {
        "MESSAGE_CREATE" | "MESSAGE_UPDATE" => {
            key = format!("discord:message:{}", json["d"]["id"].as_str()
                .expect("message id not found"));
            meta = json!([]);
            handler = CacheHandler::MERGE_CREATE;
            expire = Some(3600);

            let author_id = json["d"]["author"]["id"].as_str()
                .expect("author id not found");

            update_user(redis, pipeline, &json["d"]["author"]).await?;

            if let Some(member) = json["d"].get("member") {
                let mut member = member.clone();
                member["guild_id"] = json["d"]["guild_id"].clone();
                member["user_id"] = Value::String(author_id.to_string());

                update_member(redis, pipeline, &mut member).await?;
            }

            data = { //? redact important fields for privacy
                let mut data = json["d"].clone();
                data.as_object_mut()
                    .expect("message is not an object")
                    .insert("content".to_string(), json!(""));
                data.as_object_mut()
                    .expect("message is not an object")
                    .insert("attachments".to_string(), json!([]));
                data.as_object_mut()
                    .expect("message is not an object")
                    .insert("embeds".to_string(), json!([]));

                data
            };

            if event_name == "MESSAGE_CREATE" && json["d"]["guild_id"].is_string() {
                let _: () = pipeline.json_set(
                    &format!(
                        "discord:channel:{}",
                        json["d"]["channel_id"].as_str()
                            .expect("channel id not found")),
                    "data.last_message_id",
                    json["d"]["id"].to_string(),
                    Some(SetOptions::XX)
                ).await?;
            }
        }
        "MESSAGE_DELETE" => {
            key = format!("discord:message:{}", json["d"]["id"].as_str()
                .expect("message id not found"));
            data = json["d"].clone();
            meta = json!([]);
            handler = CacheHandler::DELETE;
            expire = Some(3600);
        }
        "GUILD_CREATE" | "GUILD_UPDATE" => {
            key = format!("discord:guild:{}", json["d"]["id"].as_str()
                .expect("guild id not found"));
            meta = json!(["channels", "emojis", "members", "roles"]);
            handler = CacheHandler::MERGE_CREATE;
            expire = None;

            data = json["d"].clone();

            if json["d"]["channels"].is_array() {
                for channel in json["d"]["channels"].as_array().unwrap() {
                    futures.push(cache(
                        redis,
                        pipeline,
                        json_merge(
                            &json!({
                                "t": "CHANNEL_CREATE",
                                "d": channel
                            }),
                            &json!({"d": {
                                "guild_id": json["d"]["id"]
                            }})
                        )
                    ));
                }

                data.as_object_mut()
                    .expect("guild is not an object")
                    .remove("channels");
            }

            if json["d"]["threads"].is_array() {
                for thread in json["d"]["threads"].as_array().unwrap() {
                    futures.push(cache(
                        redis,
                        pipeline,
                        json_merge(
                            &json!({
                                "t": "THREAD_CREATE",
                                "d": thread
                            }),
                            &json!({"d": {
                                "guild_id": json["d"]["id"]
                            }})
                        )
                    ));
                }

                data.as_object_mut()
                    .expect("guild is not an object")
                    .remove("threads");
            }

            if json["d"]["emojis"].is_array() {
                futures.push(cache(
                    redis,
                    pipeline,
                    json!({
                        "t": "GUILD_EMOJIS_UPDATE",
                        "d": {
                            "guild_id": json["d"]["id"],
                            "emojis": json["d"]["emojis"]
                        }
                    })
                ));

                data.as_object_mut()
                    .expect("guild is not an object")
                    .remove("emojis");
            }

            if json["d"]["members"].is_array() {
                for member in json["d"]["members"].as_array().unwrap() {
                    futures.push(cache(
                        redis,
                        pipeline,
                        json_merge(
                            &json!({
                                "t": "GUILD_MEMBER_UPDATE",
                                "d": member
                            }),
                            &json!({"d": {
                                "guild_id": json["d"]["id"]
                            }})
                        )
                    ));
                }

                data.as_object_mut()
                    .expect("guild is not an object")
                    .remove("members");
            }

            if json["d"]["roles"].is_array() {
                for role in json["d"]["roles"].as_array().unwrap() {
                    futures.push(cache(
                        redis,
                        pipeline,
                        json!({
                            "t": "GUILD_ROLE_CREATE",
                            "d": {
                                "guild_id": json["d"]["id"],
                                "role": role
                            }
                        })
                    )); 
                }

                data.as_object_mut()
                    .expect("guild is not an object")
                    .remove("roles");
            }
        }
        "GUILD_DELETE" => {
            if json["d"]["unavailable"].as_bool().unwrap_or(false) {
                return Ok(true)
            }

            let mut delete = vec![
                format!("discord:guild:{}", json["d"]["id"].as_str()
                    .expect("guild id not found"))
            ];

            let channels: Option<Vec<String>> = redis.smembers(
                format!(
                    "discord:guild:{}:channels",
                    json["d"]["id"].as_str()
                        .expect("guild id not found")
                )
            ).await?;

            if let Some(channels) = channels {
                delete.extend(channels.iter().map(|channel| {
                    format!("discord:channel:{}", channel)
                }));
            }

            let emojis: Option<Vec<String>> = redis.smembers(
                format!(
                    "discord:guild:{}:emojis",
                    json["d"]["id"].as_str()
                        .expect("guild id not found")
                )
            ).await?;

            if let Some(emojis) = emojis {
                delete.extend(emojis.iter().map(|emoji| {
                    format!("discord:emoji:{}", emoji)
                }));
            }

            let members: Option<Vec<String>> = redis.smembers(
                format!(
                    "discord:guild:{}:members",
                    json["d"]["id"].as_str()
                        .expect("guild id not found")
                )
            ).await?;

            if let Some(members) = members {
                delete.extend(members.iter().map(|member| {
                    format!(
                        "discord:member:{}:{}", 
                        json["d"]["id"].as_str()
                            .expect("guild id not found"), 
                        member
                    )
                }));
            }

            let roles: Option<Vec<String>> = redis.smembers(
                format!(
                    "discord:guild:{}:roles",
                    json["d"]["id"].as_str()
                        .expect("guild id not found")
                )
            ).await?;

            if let Some(roles) = roles {
                delete.extend(roles.iter().map(|role| {
                    format!("discord:role:{}", role)
                }));
            }

            let _: () = pipeline.del(delete).await?;

            return Ok(true)
        }
        "GUILD_ROLE_CREATE" | "GUILD_ROLE_UPDATE" => {
            key = format!(
                "discord:role:{}",
                json["d"]["role"]["id"].as_str()
                    .expect("role id not found")
            );
            data = json["d"]["role"].clone();
            meta = json!([]);
            handler = CacheHandler::MERGE_CREATE;
            expire = None;

            let _: () = pipeline.sadd(
                format!(
                    "discord:guild:{}:roles",
                    json["d"]["guild_id"].as_str()
                        .expect("guild id not found")),
                json["d"]["role"]["id"].as_str()
                    .expect("role id not found")
            ).await?;
        }
        "GUILD_ROLE_DELETE" => {
            key = format!(
                "discord:role:{}",
                json["d"]["role_id"].as_str()
                    .expect("role id not found")
            );
            data = json["d"].clone();
            meta = json!([]);
            handler = CacheHandler::DELETE;
            expire = Some(86400);

            let _: () = pipeline.srem(
                format!(
                    "discord:guild:{}:roles",
                    json["d"]["guild_id"].as_str()
                        .expect("guild id not found")
                ),
                json["d"]["role_id"].as_str()
                    .expect("role id not found")
            ).await?;
        }
        "GUILD_EMOJIS_UPDATE" => {
            let emojis: Option<Vec<String>> = redis.smembers(
                format!(
                    "discord:guild:{}:emojis",
                    json["d"]["guild_id"].as_str()
                        .expect("guild id not found")
                )
            ).await?;

            if let Some(emojis) = emojis {
                let mut emoji_shards: Vec<Vec<String>> = vec![Vec::new(); EMOJI_SHARDS];

                for emoji in emojis {
                    emoji_shards[
                        emoji.parse::<usize>().unwrap() % EMOJI_SHARDS
                    ].push(emoji.to_string());
                }

                for (shard_id, emojis) in emoji_shards.into_iter().enumerate() {
                    if !emojis.is_empty() {
                        let _: () = pipeline.srem(
                            format!("discord_emojis:{}", shard_id),
                            emojis
                        ).await?;
                    }
                }
            }

            let _: () = pipeline.del(format!(
                "discord:guild:{}:emojis",
                json["d"]["guild_id"].as_str()
                    .expect("guild id not found")
            )).await?;

            if json["d"]["emojis"].as_array().unwrap().is_empty() {
                return Ok(true)
            }

            {
                let mut emoji_shards: Vec<Vec<String>> = vec![Vec::new(); EMOJI_SHARDS];

                for emoji in json["d"]["emojis"].as_array().unwrap() {
                    emoji_shards[
                        emoji["id"].as_str()
                            .expect("emoji id not found")
                            .parse::<usize>()
                            .unwrap() % EMOJI_SHARDS
                    ].push(emoji["id"].as_str()
                        .expect("emoji id not found")
                        .to_string()
                    );
                }

                for (shard_id, emojis) in emoji_shards.into_iter().enumerate() {
                    if !emojis.is_empty() {
                        let _: () = pipeline.sadd(
                            format!("discord_emojis:{}", shard_id),
                            emojis
                        ).await?;
                    }
                }
            }

            let _: () = pipeline.sadd(
                format!(
                    "discord:guild:{}:emojis",
                    json["d"]["guild_id"].as_str()
                        .expect("guild id not found")),
                json["d"]["emojis"].as_array().unwrap().iter().map(|emoji| {
                    emoji["id"].as_str()
                        .expect("emoji id not found")
                }).collect::<Vec<&str>>()
            ).await?;

            return Ok(true);
        }
        "CHANNEL_CREATE" | "CHANNEL_UPDATE" | "THREAD_CREATE" | "THREAD_UPDATE" => {
            key = format!(
                "discord:channel:{}",
                json["d"]["id"].as_str()
                    .expect("channel id not found")
            );

            data = json_merge(
                &json!({"__plural_last_webhook": 0}),
                &json["d"].clone(), 
            );

            meta = json!([]);
            handler = CacheHandler::MERGE_CREATE;
            expire = None;

            let _: () = pipeline.sadd(
                format!(
                    "discord:guild:{}:channels",
                    json["d"]["guild_id"].as_str()
                        .expect("guild id not found")),
                json["d"]["id"].as_str()
                    .expect("channel id not found")
            ).await?;
        }
        "CHANNEL_DELETE" | "THREAD_DELETE" => {
            key = format!(
                "discord:channel:{}",
                json["d"]["id"].as_str()
                    .expect("channel id not found")
            );
            data = json["d"].clone();
            meta = json!([]);
            handler = CacheHandler::DELETE;
            expire = Some(86400);

            if json["d"].get("guild_id").is_some() {
                let _: () = pipeline.srem(
                    format!(
                        "discord:guild:{}:channels",
                        json["d"]["guild_id"].as_str()
                            .expect("guild id not found")
                    ),
                    json["d"]["id"].as_str()
                        .expect("channel id not found")
                ).await?;
            }            
        }
        "THREAD_LIST_SYNC" => {
            for thread in json["d"]["threads"].as_array().unwrap() {
                futures.push(cache(
                    redis,
                    pipeline,
                    json_merge(
                        &json!({
                            "t": "THREAD_CREATE",
                            "d": thread
                        }),
                        &json!({"d": {
                            "guild_id": json["d"]["guild_id"]
                        }})
                    )
                ));
            }

            join_all(futures).await;

            return Ok(true);
        }
        "GUILD_MEMBER_UPDATE" => {
            update_member(
                redis,
                pipeline,
                &mut json["d"].clone()
            ).await?;

            return Ok(true);
        }
        "MESSAGE_REACTION_ADD" => {
            // ? don't care about the reaction, just extract member
            if json["d"].get("member").is_none() {
                return Ok(true)
            }

            update_member(
                redis,
                pipeline,
                &mut json_merge(
                    &json["d"]["member"],
                    &json!({"guild_id": json["d"]["guild_id"]})
                )
            ).await?;

            return Ok(true);
        }
        "WEBHOOKS_UPDATE" => {
            //? webhooks handled by downstream bot
            return Ok(true)
        }
        _ => {
            return Ok(false)
        }
    }

    let cached: Option<Value> = redis.json_get(
        &key,
        None::<String>,
        None::<String>,
        None::<String>,
        "$"
    ).await?;

    match (handler, cached) {
        (CacheHandler::MERGE_CREATE, Some(mut cached)) => {
            let _: () = pipeline.json_mset(vec![
                (&key, "deleted", Value::Bool(false)),
                (&key, "error", Value::Number(0.into())),
                (&key, "meta", meta),
                (&key, "data", json_merge(&mut cached[0]["data"], &data))
            ]).await?;
        }
        (CacheHandler::MERGE_CREATE, None) => {
            let _: () = pipeline.json_set(
                &key,
                "$",
                json_to_cache_model(&data, Some(&meta)),
                None,
            ).await?;
        }
        (CacheHandler::DELETE, Some(_)) => {
            let _: () = pipeline.json_mset(vec![
                (&key, "deleted", Value::Bool(true)),
                (&key, "error", Value::Number(0.into())),
                (&key, "data", data),
                (&key, "meta", json!([]))
            ]).await?;
        }
        (CacheHandler::DELETE, None) => {}
    }

    if let Some(expire) = expire {
        let _: () = pipeline.expire(
            &key,
            expire,
            None
        ).await?;
    }

    join_all(futures).await;

    Ok(true)
}

async fn publish(
    pipeline: &Pipeline<RedisClient>,
    json: &Value
) -> Result<(), fred::error::Error> {
    let _: () = pipeline.xadd(
        "discord_events",
        false,
        (
            XCapKind::MinID,
            XCapTrim::Exact,
            format!(
                "{}-0",
                SystemTime::now()
                    .duration_since(SystemTime::UNIX_EPOCH)
                    .expect("where we're going we won't need timestamps")
                    .as_millis()
                    .saturating_sub(20_000 as u128)
            ),
            None),
        "*",
        vec![
            ("data", json.to_string())
        ]
    ).await?;

    Ok(())
}

fn json_to_cache_model(
    data: &Value,
    meta: Option<&Value>
) -> Value {
    json!({
        "data": data,
        "meta": meta.unwrap_or(&json!([])),
        "deleted": false,
        "error": 0
    })
}

fn json_merge(
    base: &Value,
    update: &Value
) -> Value {
    match (base, update) {
        (
            Value::Object(base),
            Value::Object(update)
        ) => {
            let mut merged = base.clone();
            
            for (key, value) in update.iter() {
                match merged.get(key) {
                    Some(Value::Object(base_value)) => {
                        merged.insert(key.clone(), json_merge(
                            &Value::Object(base_value.clone()),
                            value
                        ));
                    }
                    _ => {
                        merged.insert(key.clone(), value.clone());
                    }
                }
            }


            merged.into()
        }
        (_, Value::Null) => Value::Null,
        (Value::Null, _) => update.clone(),
        _ => panic!("unexpected json type: {:?} {:?}", base, update)
    }
}

async fn update_user(
    redis: &RedisClient,
    pipeline: &Pipeline<RedisClient>,
    json: &Value
) -> Result<(), fred::error::Error> {
    let key = format!("discord:user:{}", json["id"].as_str()
        .expect("user id not found"));

    let cached: Option<Value> = redis.json_get(
        &key,
        None::<String>,
        None::<String>,
        None::<String>,
        "data"
    ).await?;

    match cached {
        Some(mut cached) => {
            let _: () = pipeline.json_set(
                &key,
                "data",
                json_merge(&mut cached, json),
                None,
            ).await?;
        }
        None => {
            let _: () = pipeline.json_set(
                &key,
                "$",
                json_to_cache_model(json, None),
                None,
            ).await?;
        }
    }

    let _: () = pipeline.expire(
        &key,
        86400,
        None
    ).await?;

    Ok(())
}

async fn update_member(
    redis: &RedisClient,
    pipeline: &Pipeline<RedisClient>,
    json: &mut Value
) -> Result<(), fred::error::Error> {
    let user_id = if json.get("user").is_some() {
        update_user(redis, pipeline, &json["user"]).await?;
        json["user"]["id"].as_str()
            .expect("user id not found")
            .to_string()
    } else {
        json["user_id"].as_str()
            .expect("user id not found")
            .to_string()
    };

    json.as_object_mut()
        .expect("member is not an object")
        .remove("user");

    let key = format!(
        "discord:member:{}:{}",
        json["guild_id"].as_str()
            .expect("guild id not found"),
        user_id
    );

    let cached: Option<Value> = redis.json_get(
        &key,
        None::<String>,
        None::<String>,
        None::<String>,
        "data"
    ).await?;

    match cached {
        Some(mut cached) => {
            let _: () = pipeline.json_set(
                &key,
                "data",
                json_merge(&mut cached, json),
                None,
            ).await?;
        }
        None => {
            let _: () = pipeline.json_set(
                &key,
                "$",
                json_to_cache_model(json, None),
                None,
            ).await?;
        }
    }

    // ? don't expire self, required for permission calculations
    if user_id != APPLICATION_ID.as_str() {
        let _: () = pipeline.expire(
            &key,
            600,
            None
        ).await?;
    }

    Ok(())
}

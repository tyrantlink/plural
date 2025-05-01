use std::time::Duration;

use actix_web::{HttpResponse, Responder, get, head, web};
use bson::doc;
use plural_core::{db::Message, redis, redis::KeysInterface};
use serde::Deserialize;
use tokio::time::sleep;

use crate::{
    error::ErrorResponse,
    models::{MessageModel, Token}
};

pub fn config(cfg: &mut web::ServiceConfig) {
    cfg.service(web::scope("/messages").service(get_message));
}

fn snowflake_to_age(snowflake: i64) -> f64 {
    (chrono::Utc::now().timestamp_millis() -
        ((snowflake >> 22) + 1420070400000)) as f64 /
        1000.0
}

#[derive(Deserialize)]
struct MessageQuery {
    member: Option<bool>
}

#[head("/{channel_id}/{message_id}")]
async fn head_message(
    path: web::Path<(i64, i64)>
) -> Result<impl Responder, ErrorResponse> {
    let (channel_id, message_id) = path.into_inner();

    let message_timestamp = snowflake_to_age(message_id);

    if message_timestamp > 604_800. {
        return Err(ErrorResponse {
            status: 410,
            detail: "Message is older than 7 days; status is unknown"
                .to_string(),
            ..Default::default()
        });
    }

    if message_timestamp < -30. {
        return Err(ErrorResponse {
            status: 410,
            detail: "Message is in the future; status is unknown".to_string(),
            ..Default::default()
        });
    }

    if redis()
        .exists(format!("pending_proxy:{channel_id}:{message_id}"))
        .await?
    {
        return Ok(HttpResponse::Ok().finish());
    }

    if Message::find_one(doc! {
    "channel_id": channel_id,
    "$or": [
        { "proxy_id": message_id },
        { "original_id": message_id }]})
    .await?
    .is_none()
    {
        Ok(HttpResponse::Ok().finish())
    } else {
        Err(ErrorResponse {
            status: 404,
            detail: "Message not found".to_string(),
            ..Default::default()
        })
    }
}

#[get("/{channel_id}/{message_id}")]
async fn get_message(
    path: web::Path<(i64, i64)>,
    query: web::Query<MessageQuery>,
    _token: Token
) -> Result<impl Responder, ErrorResponse> {
    let (channel_id, message_id) = path.into_inner();

    let with_member = query.member.unwrap_or(false);

    let message_timestamp = snowflake_to_age(message_id);

    if message_timestamp > 604_800. {
        return Err(ErrorResponse {
            status: 410,
            detail: "Message is older than 7 days; status is unknown"
                .to_string(),
            ..Default::default()
        });
    }

    if message_timestamp < -30. {
        return Err(ErrorResponse {
            status: 410,
            detail: "Message is in the future; status is unknown".to_string(),
            ..Default::default()
        });
    }

    let mut message = Message::find_one(doc! {
    "channel_id": channel_id,
    "$or": [
        { "proxy_id": message_id },
        { "original_id": message_id }]})
    .await?;

    if message.is_none() {
        let pending: bool = redis()
            .exists(format!("pending_proxy:{channel_id}:{message_id}"))
            .await?;

        let mut limit = 50;

        while pending && message.is_none() && limit > 0 {
            sleep(Duration::from_millis(100)).await;

            message = Message::find_one(doc! {
            "channel_id": channel_id,
            "$or": [
                { "proxy_id": message_id },
                { "original_id": message_id }]})
            .await?;

            if message.is_some() {
                break;
            }

            limit -= 1;
        }

        if pending && message.is_none() {
            return Err(ErrorResponse {
                status: 408,
                detail: "Message proxy is pending but took longer than 5 \
                         seconds to complete."
                    .to_string(),
                ..Default::default()
            });
        }
    }

    match message {
        Some(message) => Ok(HttpResponse::Ok()
            .json(MessageModel::from_message(message, with_member).await?)),
        None => Err(ErrorResponse {
            status: 404,
            detail: "Message not found".to_string(),
            ..Default::default()
        })
    }
}

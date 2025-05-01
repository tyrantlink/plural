use std::pin::Pin;

use actix_web::{FromRequest, HttpRequest};
use bcrypt::verify;
use bson::{doc, oid::ObjectId};
use plural_core::{
    crypto::{BASE66CHARS, decode_b66},
    db::Application,
    env,
    redis,
    redis::{Expiration, KeysInterface}
};
use regex::Regex;
use sha2::{Digest, Sha256};

use crate::error::ErrorResponse;

lazy_static::lazy_static! {
    static ref TOKEN_PATTERN: Regex = Regex::new(
        #[allow(clippy::uninlined_format_args)]
        format!(r"^([{}]{{1,16}})\.([{}]{{5,8}})\.([{}]{{20,27}})$",
            BASE66CHARS, BASE66CHARS, BASE66CHARS
    ).as_str()).unwrap();
}

#[derive(Debug)]
pub struct Token {
    pub app:      Application,
    pub internal: bool
}

pub enum TokenValidationError {
    InvalidFormat,
    ExpiredToken,
    DatabaseError
}

async fn verify_token(
    token: String,
    hashed: String
) -> Result<(), TokenValidationError> {
    match tokio::task::spawn_blocking(move || verify(&token, &hashed)).await {
        Ok(Ok(true)) => Ok(()),
        Ok(Ok(false)) => Err(TokenValidationError::ExpiredToken),
        _ => Err(TokenValidationError::InvalidFormat)
    }
}

impl Token {
    pub async fn new(token: String) -> Result<Self, TokenValidationError> {
        if token == env().internal_master_token {
            return Ok(Self {
                app:      Application::empty(),
                internal: true
            });
        }

        let Some(captures) = TOKEN_PATTERN.captures(&token) else {
            return Err(TokenValidationError::InvalidFormat);
        };

        let app_id = decode_b66(captures[1].to_string().as_str());

        let timestamp = decode_b66(captures[2].to_string().as_str());

        let key = decode_b66(captures[3].to_string().as_str());

        let redis_key = format!("token:{}", {
            let mut hasher = Sha256::new();

            hasher.update({
                let mut bytes = app_id.clone();

                bytes.extend_from_slice(&timestamp);

                bytes.extend_from_slice(&key);

                bytes
            });

            format!("{:x}", hasher.finalize())
        });

        let app = match Application::find_one(doc! {
            "_id": ObjectId::from_bytes(app_id.try_into()
                .map_err(|_| TokenValidationError::InvalidFormat)?)
        })
        .await
        {
            Ok(Some(app)) => {
                match redis().exists(&redis_key).await {
                    Ok(true) => {}
                    Ok(false) => {
                        verify_token(token.clone(), app.token.clone()).await?;

                        if redis()
                            .set::<String, _, _>(
                                redis_key.clone(),
                                "1",
                                Some(Expiration::EX(3600)),
                                None,
                                false
                            )
                            .await
                            .is_err()
                        {
                            return Err(TokenValidationError::DatabaseError);
                        }
                    }
                    Err(_) => return Err(TokenValidationError::DatabaseError)
                }

                app
            }
            _ => return Err(TokenValidationError::DatabaseError)
        };

        Ok(Self { app, internal: false })
    }
}

impl FromRequest for Token {
    type Error = ErrorResponse;
    type Future = Pin<Box<dyn Future<Output = Result<Self, Self::Error>>>>;

    fn from_request(
        request: &HttpRequest,
        _payload: &mut actix_web::dev::Payload
    ) -> Self::Future {
        let Some(token) = request
            .headers()
            .get("Authorization")
            .map(|h| h.to_str().unwrap_or_default().to_string())
        else {
            return Box::pin(async {
                Err(ErrorResponse {
                    status: 401,
                    detail: "Unauthorized".to_string(),
                    ..Default::default()
                })
            });
        };

        Box::pin(async move {
            match Token::new(token).await {
                Ok(token) => Ok(token),
                Err(TokenValidationError::InvalidFormat) => {
                    Err(ErrorResponse {
                        status: 401,
                        detail: "Invalid token format".to_string(),
                        ..Default::default()
                    })
                }
                Err(TokenValidationError::ExpiredToken) => Err(ErrorResponse {
                    status: 401,
                    detail: "Expired token".to_string(),
                    ..Default::default()
                }),
                Err(TokenValidationError::DatabaseError) => Err(ErrorResponse {
                    status: 500,
                    detail: "Database error".to_string(),
                    ..Default::default()
                })
            }
        })
    }
}

use actix_web::{HttpResponse, ResponseError, http::StatusCode};
use derive_more::Display;
use plural_core::{db::MongoError, redis::RedisError};
use serde_json::json;

#[derive(Debug, Display)]
#[display("status: {status}, detail: {detail}")]
pub struct ErrorResponse {
    pub status:  u16,
    pub detail:  String,
    pub headers: actix_web::http::header::HeaderMap
}

impl Default for ErrorResponse {
    fn default() -> Self {
        ErrorResponse {
            status:  500,
            detail:  "Internal Server Error".to_string(),
            headers: actix_web::http::header::HeaderMap::new()
        }
    }
}

impl ResponseError for ErrorResponse {
    fn status_code(&self) -> StatusCode {
        StatusCode::from_u16(self.status)
            .unwrap_or(StatusCode::INTERNAL_SERVER_ERROR)
    }

    fn error_response(&self) -> HttpResponse<actix_web::body::BoxBody> {
        let mut response =
            HttpResponse::build(self.status_code()).json(json!({
                "detail": self.detail
            }));

        for (key, value) in self.headers.iter() {
            response.headers_mut().insert(key.clone(), value.clone());
        }

        response
    }
}

impl From<MongoError> for ErrorResponse {
    fn from(_error: MongoError) -> Self {
        ErrorResponse {
            status: 500,
            detail: "Database Error".to_string(),
            ..Default::default()
        }
    }
}

impl From<RedisError> for ErrorResponse {
    fn from(_error: RedisError) -> Self {
        ErrorResponse {
            status: 500,
            detail: "Database Error".to_string(),
            ..Default::default()
        }
    }
}

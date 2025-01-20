use std::collections::HashMap;
use std::sync::Arc;

use actix_web::http::StatusCode;
use actix_web::{web, App, HttpRequest, HttpResponse, HttpServer};
use bytes::Bytes;
use parking_lot::RwLock;
use reqwest::{Client as ReqwestClient, Method, StatusCode as ReqwestStatusCode};
use tokio::sync::Semaphore;
use tokio::time::{Duration, Instant};

const DISCORD_API_URL: &str = "https://discord.com";

#[derive(Clone, Debug)]
struct RateLimit {
    semaphore: Arc<Semaphore>,
    limit: i32,
    remaining: i32,
    reset: Instant,
}

impl RateLimit {
    fn new() -> Self {
        RateLimit {
            semaphore: Arc::new(Semaphore::new(1)),
            limit: 1,
            remaining: 1,
            reset: Instant::now(),
        }
    }

    fn update_semaphore(&mut self, new_limit: i32, new_remaining: i32) {
        let old_sem = self.semaphore.clone();
        let new_permits = std::cmp::max(1, new_limit / 2);

        self.semaphore = Arc::new(Semaphore::new(new_permits as usize));
        self.limit = new_limit;
        self.remaining = new_remaining;

        drop(old_sem);
    }

    fn is_reset(&self) -> bool {
        Instant::now() >= self.reset
    }

    fn reset_after(&self) -> Duration {
        if self.is_reset() {
            Duration::from_secs(0)
        } else {
            self.reset - Instant::now()
        }
    }
}

struct AppState {
    rate_limits: RwLock<HashMap<String, RateLimit>>,
    client: ReqwestClient,
}

async fn handle_429(res: reqwest::Response) -> Result<Duration, HttpResponse> {
    let retry_data = res
        .json::<serde_json::Value>()
        .await
        .map_err(|_| HttpResponse::InternalServerError().finish())?;

    let retry_after = retry_data
        .get("retry_after")
        .and_then(|v| v.as_f64())
        .unwrap_or(1.0);

    let is_global = retry_data
        .get("global")
        .and_then(|v| v.as_bool())
        .unwrap_or(false);

    if is_global {
        println!("Hit global rate limit");
    }

    Ok(Duration::from_secs_f64(retry_after))
}

async fn proxy_handler(
    req: HttpRequest,
    body: web::Bytes,
    state: web::Data<AppState>,
) -> HttpResponse {
    let token = req
        .headers()
        .get("Authorization")
        .and_then(|h| h.to_str().ok())
        .unwrap_or("")
        .to_string();

    let rate_limit = {
        let mut rate_limits = state.rate_limits.write();
        rate_limits
            .entry(token.clone())
            .or_insert_with(RateLimit::new)
            .clone()
    };

    if rate_limit.remaining == 0 && !rate_limit.is_reset() {
        tokio::time::sleep(rate_limit.reset_after()).await;
    }

    let _permit = rate_limit.semaphore.acquire().await.unwrap();

    let url = format!("{}{}", DISCORD_API_URL, req.uri().path());
    let method = Method::from_bytes(req.method().as_str().as_bytes()).unwrap();

    let mut headers = Vec::new();
    for (name, value) in req.headers() {
        if name.as_str().to_lowercase() != "host" {
            headers.push((
                name.as_str().to_string(),
                value.to_str().unwrap().to_string(),
            ));
        }
    }

    headers.push(("Host".to_string(), "discord.com".to_string()));

    let path = req.uri().path().to_string();
    let string_method = req.method().as_str().to_string();
    let mut attempts = 0;
    const MAX_RETRIES: u32 = 10;

    loop {
        attempts += 1;
        let mut client_req = state.client.request(method.clone(), &url);

        for (name, value) in &headers {
            client_req = client_req.header(name, value);
        }

        client_req = client_req.body(body.clone());

        match client_req.send().await {
            Ok(res) => {
                let status = res.status();

                if status == ReqwestStatusCode::TOO_MANY_REQUESTS {
                    if attempts >= MAX_RETRIES {
                        return HttpResponse::TooManyRequests().finish();
                    }

                    match handle_429(res).await {
                        Ok(retry_after) => {
                            tokio::time::sleep(retry_after).await;
                            continue;
                        }
                        Err(response) => return response,
                    }
                }

                println!(
                    "{} {} {} {}{}",
                    token
                        .split('.')
                        .next()
                        .unwrap_or("")
                        .strip_prefix("Bot ")
                        .unwrap_or(""),
                    status.as_u16(),
                    string_method,
                    path,
                    if attempts > 1 {
                        format!(" in {} tries", attempts)
                    } else {
                        String::new()
                    }
                );

                if let (Some(limit), Some(remaining), Some(reset)) = (
                    res.headers().get("X-RateLimit-Limit"),
                    res.headers().get("X-RateLimit-Remaining"),
                    res.headers().get("X-RateLimit-Reset"),
                ) {
                    let limit = limit.to_str().unwrap_or("1").parse().unwrap_or(1);
                    let remaining = remaining.to_str().unwrap_or("1").parse().unwrap_or(1);
                    let reset_time = Instant::now()
                        + Duration::from_secs(reset.to_str().unwrap_or("0").parse().unwrap_or(0));

                    let mut rate_limits = state.rate_limits.write();
                    if let Some(rate_limit) = rate_limits.get_mut(&token) {
                        rate_limit.update_semaphore(limit, remaining);
                        rate_limit.reset = reset_time;
                    }
                }

                let mut client_res =
                    HttpResponse::build(StatusCode::from_u16(res.status().as_u16()).unwrap());

                for (name, value) in res.headers() {
                    client_res.insert_header((name.as_str(), value.to_str().unwrap()));
                }

                let body_bytes = res.bytes().await.unwrap_or_else(|_| Bytes::new());
                return client_res.body(body_bytes);
            }
            Err(_) => return HttpResponse::InternalServerError().finish(),
        }
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let state = web::Data::new(AppState {
        rate_limits: RwLock::new(HashMap::new()),
        client: ReqwestClient::new(),
    });

    println!("started /plu/ral egress proxy");

    HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .default_service(web::route().to(proxy_handler))
    })
    .bind("127.0.0.1:80")?
    .run()
    .await
}

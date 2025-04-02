use std::env;
use core::str;
use std::{collections::HashMap, io::Read};
use std::sync::Arc;

use actix_web::{web, App, HttpRequest, HttpResponse, HttpServer, http::StatusCode};
use base64::{prelude::BASE64_STANDARD_NO_PAD, Engine as _};
use bytes::Bytes;
use flate2::read::GzDecoder;
use http::{HeaderMap, HeaderName};
use lazy_static::lazy_static;
use opentelemetry_http::HeaderExtractor;
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::{propagation::TraceContextPropagator, Resource};
use opentelemetry::{global, trace::{SpanKind, TraceContextExt, Tracer, Status}, Context, KeyValue};
use parking_lot::RwLock;
use regex::Regex;
use reqwest::{Client as ReqwestClient, Method, StatusCode as ReqwestStatusCode};
use tokio::sync::Semaphore;
use tokio::time::{Duration, Instant};

use version::get_version;

const DISCORD_API_URL: &str = "https://discord.com";

lazy_static! {
    // ? add more as needed, only add what's required by /plu/ral
    static ref PATH_PATTERNS: HashMap<&'static str, Regex> = [
        ("/applications/:id",
            Regex::new(r"^/applications/\d+$").unwrap()),
        ("/interactions/:id/:token/callback",
            Regex::new(r"^/interactions/\d+/[a-zA-Z0-9_-]+/callback$").unwrap()),
        ("/webhooks/:id/:token",
            Regex::new(r"^/webhooks/\d+/[a-zA-Z0-9_-]+$").unwrap()),
        ("/webhooks/:id/:token/messages/:id",
            Regex::new(r"^/webhooks/\d+/[a-zA-Z0-9_-]+/messages/(\d+|@original)$").unwrap()),
        ("/applications/:id/commands",
            Regex::new(r"^/applications/\d+/commands$").unwrap()),
        ("/applications/:id/commands/:id",
            Regex::new(r"^/applications/\d+/commands/\d+$").unwrap()),
        ("/channels/:id/webhooks",
            Regex::new(r"^/channels/\d+/webhooks$").unwrap()),
        ("/channels/:id/messages/:id",
            Regex::new(r"^/channels/\d+/messages/\d+$").unwrap()),
        ("/webhooks/:id/:token",
            Regex::new(r"^/webhooks/\d+/[a-zA-Z0-9_-]+$").unwrap()),
        ("/webhooks/:id/:token/:messages/:id",
            Regex::new(r"^/webhooks/\d+/[a-zA-Z0-9_-]+/messages/\d+$").unwrap()),
        ("/applications/:id/emojis",
            Regex::new(r"^/applications/\d+/emojis$").unwrap()),
        ("/applications/:id/emojis/:id",
            Regex::new(r"^/applications/\d+/emojis/\d+$").unwrap()),
        ("/guilds/:id/members/:id",
            Regex::new(r"^/guilds/\d+/members/\d+$").unwrap()),
        ("/channels/:id/messages",
            Regex::new(r"^/channels/\d+/messages$").unwrap()),
        ("/users/:id",
            Regex::new(r"^/users/\d+$").unwrap()),
        ("/users/:id/guilds",
            Regex::new(r"^/users/\d+/guilds$").unwrap()),
        ("/users/:id/channels",
            Regex::new(r"^/users/\d+/channels$").unwrap())
    ].into();
}

fn format_path(path: String) -> String {
    let path = path.strip_prefix("/api/v10")
        .unwrap_or(&path)
        .replace("@me", "1"); // 1 gets replaced with :id

    for (replacement, pattern) in PATH_PATTERNS.iter() {
        if pattern.is_match(&path) {
            return replacement.to_string();
        }
    }

    path.to_string()
}

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
    rate_limits: RwLock<HashMap<String, HashMap<String, RateLimit>>>,
    bucket_path_map: RwLock<HashMap<(String, String), String>>,
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

fn extract_context_from_request(req: &HttpRequest) -> Context {
    let mut headers = HeaderMap::new();
    for (name, value) in req.headers() {
        headers.insert(
            name.as_str().parse::<HeaderName>().unwrap(),
            value.as_bytes().try_into().unwrap()
        );
    }

    global::get_text_map_propagator(|propagator| {
        propagator.extract(&HeaderExtractor(&headers))
    })
}


async fn proxy_handler(
    request: HttpRequest,
    body: web::Bytes,
    state: web::Data<AppState>,
) -> HttpResponse {
    let trace = request
        .headers()
        .get("X-Suppress-Tracer")
        .and_then(|h| h.to_str().ok())
        .unwrap_or("")
        .is_empty();

    let context = request
        .headers()
        .get("X-Context")
        .and_then(|h| h.to_str().ok())
        .unwrap_or("")
        .to_string();

    let token = request
        .headers()
        .get("Authorization")
        .and_then(|h| h.to_str().ok())
        .unwrap_or("")
        .to_string();

    let string_method = request.method().as_str().to_string();

    let path = request.uri().path().to_string();
    let formatted_path = format_path(path.clone());

    let query = request.uri().query().unwrap_or("");

    let path_key = (
        string_method.clone(),
        path.clone()
    );

    let bucket = {
        let bucket_paths = state.bucket_path_map.read();
        bucket_paths.get(&path_key).cloned()
    };

    let rate_limit = {
        let mut rate_limits = state.rate_limits.write();
        let token_buckets = rate_limits
            .entry(token.clone())
            .or_default();

        if let Some(bucket) = &bucket {
            token_buckets
                .entry(bucket.clone())
                .or_insert_with(RateLimit::new)
                .clone()
        } else {
            RateLimit::new()
        }
    };

    if rate_limit.remaining == 0 && !rate_limit.is_reset() {
        tokio::time::sleep(rate_limit.reset_after()).await;
    }

    let _permit = rate_limit.semaphore.acquire().await.unwrap();

    let method = Method::from_bytes(request.method().as_str().as_bytes()).unwrap();
    let url = format!(
        "{}{}",
        DISCORD_API_URL,
        request.uri().path_and_query().unwrap().as_str()
    );

    let mut headers = Vec::new();
    for (name, value) in request.headers() {
        if name.as_str().to_lowercase() != "host" {
            headers.push((
                name.as_str().to_string(),
                value.to_str().unwrap().to_string(),
            ));
        }
    }

    headers.push(("Host".to_string(), "discord.com".to_string()));

    let mut attempts = 0;
    const MAX_RETRIES: u32 = 10;

    let mut cx = Context::current();

    if trace {
        let parent_cx = extract_context_from_request(&request);
        let tracer = global::tracer("");
        let span = tracer
            .span_builder(format!("{} {}", method, formatted_path))
            .with_kind(SpanKind::Server)
            .with_attributes(vec![
                KeyValue::new("http.method", string_method.clone()),
                KeyValue::new("http.path", path.clone()),
                KeyValue::new("http.query", query.to_string())])
            .start_with_context(&tracer, &parent_cx);

        cx = Context::current_with_span(span);
        let _guard = cx.clone().attach();
    }

    loop {
        attempts += 1;
        let mut client_req = state.client.request(method.clone(), &url);

        for (name, value) in &headers {
            if name == "X-Suppress-Tracer" || name == "X-Context" {
                continue;
            }

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

                let _b64_token = BASE64_STANDARD_NO_PAD.decode(
                    token
                    .split('.')
                    .next()
                    .unwrap_or("")
                    .strip_prefix("Bot ")
                    .unwrap_or("")
                ).unwrap();

                let token_id = str::from_utf8(&_b64_token).unwrap();

                let (limit, remaining, reset, bucket, content_encoding) = (
                    res.headers().get("X-RateLimit-Limit").and_then(
                        |l| l.to_str().ok()),
                    res.headers().get("X-RateLimit-Remaining").and_then(
                        |r| r.to_str().ok()),
                    res.headers().get("X-RateLimit-Reset").and_then(
                        |r| r.to_str().ok()),
                    res.headers().get("X-RateLimit-Bucket").and_then(
                        |b| b.to_str().ok()),
                    res.headers().get("Content-Encoding").cloned()
                );

                if bucket.is_some() {
                    let bucket_name = bucket.unwrap().to_string();
                    let mut bucket_paths = state.bucket_path_map.write();
                    bucket_paths.insert(path_key.clone(), bucket_name.clone());

                    let limit = limit.unwrap_or("1").parse().unwrap_or(1);
                    let remaining = remaining.unwrap_or("1").parse().unwrap_or(1);
                    let reset_time = Instant::now()
                        + Duration::from_secs(reset.unwrap_or("0").parse().unwrap_or(0));

                    let mut rate_limits = state.rate_limits.write();
                    if let Some(token_buckets) = rate_limits.get_mut(&token) {
                        let rate_limit = token_buckets
                            .entry(bucket_name)
                            .or_insert_with(RateLimit::new);

                        rate_limit.update_semaphore(limit, remaining);
                        rate_limit.reset = reset_time;
                    }
                }

                println!(
                    "{}{} {} {}{} {}/{}{}",
                    if !token_id.is_empty() { format!("{} ", token_id) } else { String::new() },
                    status.as_u16(),
                    string_method,
                    formatted_path,
                    if attempts > 1 { format!(" in {} tries", attempts) } else { String::new() },
                    remaining.unwrap_or("?"),
                    limit.unwrap_or("?"),
                    if !trace { " (silent)" } else { "" }
                );

                if trace {
                    if let (
                        Some(limit),
                        Some(remaining)
                    ) = (limit, remaining) {
                        cx.span().update_name(format!(
                            "{} {} {}/{}",
                            method,
                            formatted_path,
                            remaining,
                            limit
                        ));
                    }

                    if !res.status().is_success() {
                        cx.span().set_status(
                            Status::Error {
                                description: status.as_str().to_owned().into()
                            }
                        );
                    }

                    let mut attributes = vec![
                        KeyValue::new(
                            "http.status_code",
                            res.status().as_u16() as i64),
                        KeyValue::new(
                            "attempts",
                            attempts as i64),
                        KeyValue::new(
                            "context",
                            context
                        )
                    ];

                    if !token_id.is_empty() {
                        attributes.push(KeyValue::new(
                            "bot_id",
                            token_id.to_string()
                        ));
                    }

                    if let Some(limit) = limit {
                        attributes.push(KeyValue::new(
                            "rate_limit.limit",
                            limit.parse::<i64>().unwrap()
                        ));
                    }

                    if let Some(remaining) = remaining {
                        attributes.push(KeyValue::new(
                            "rate_limit.remaining",
                            remaining.parse::<i64>().unwrap()
                        ));
                    }

                    if let Some(reset) = reset {
                        attributes.push(KeyValue::new(
                            "rate_limit.reset",
                            reset.parse::<f64>().unwrap()
                        ));
                    }

                    if let Some(bucket) = bucket {
                        attributes.push(KeyValue::new(
                            "rate_limit.bucket",
                            bucket.to_string()
                        ));
                    }

                    if let Some(reset_after) = res.headers().get("X-RateLimit-Reset-After") {
                        attributes.push(KeyValue::new(
                            "rate_limit.reset_after",
                            reset_after.to_str().unwrap().parse::<f64>().unwrap()
                        ));
                    }

                    if let Some(global) = res.headers().get("X-RateLimit-Global") {
                        attributes.push(KeyValue::new(
                            "rate_limit.global",
                            global.to_str().unwrap().parse::<bool>().unwrap()
                        ));
                    }

                    if let Some(scope) = res.headers().get("X-RateLimit-Scope") {
                        attributes.push(KeyValue::new(
                            "rate_limit.scope",
                            scope.to_str().unwrap().to_string()
                        ));
                    }

                    cx.span().set_attributes(
                        attributes
                    );
                }

                let mut client_res = HttpResponse::build(
                    StatusCode::from_u16(res.status().as_u16()).unwrap()
                );

                for (name, value) in res.headers() {
                    client_res.insert_header((name.as_str(), value.to_str().unwrap()));
                }

                let body_bytes;

                if !res.status().is_success() && trace {
                    body_bytes = res.bytes().await.unwrap_or_else(|_| Bytes::new());

                    cx.span().set_attribute(KeyValue::new(
                        "http.response_body",
                        {
                            if content_encoding == Some("gzip".parse().unwrap()) {
                                let mut decompressed = GzDecoder::new(&body_bytes[..]);
                                let mut text = String::new();
                                decompressed.read_to_string(&mut text).unwrap_or_default();
                                text
                            } else {
                                String::from_utf8_lossy(&body_bytes).to_string()
                            }
                        }
                    ));
                } else {
                    body_bytes = res.bytes().await.unwrap_or_else(|_| Bytes::new());
                }

                return client_res.body(body_bytes);
            }
            Err(_) => return HttpResponse::InternalServerError().finish(),
        }
    }
}

#[actix_web::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let version = get_version("egress-proxy");

    global::set_text_map_propagator(TraceContextPropagator::new());

    let dev = {
        let dev_env = env::var("DEV").unwrap_or("1".to_string());
        !(dev_env == "false" || dev_env == "0")
    };

    let provider = opentelemetry_sdk::trace::TracerProvider::builder()
        .with_resource(Resource::new(vec![
            KeyValue::new("service.name", "egress"),
            KeyValue::new("service.version", version.clone()),
            KeyValue::new("deployment.environment.name", if dev { "dev" } else { "prod" })]))
        .with_batch_exporter(
        opentelemetry_otlp::SpanExporter::builder()
            .with_http()
            .with_protocol(opentelemetry_otlp::Protocol::HttpBinary)
            .build()?,
        opentelemetry_sdk::runtime::Tokio)
        .build();
    global::set_tracer_provider(provider);

    let state = web::Data::new(AppState {
        rate_limits: RwLock::new(HashMap::new()),
        bucket_path_map: RwLock::new(HashMap::new()),
        client: ReqwestClient::new(),
    });

    println!("started /plu/ral egress proxy v{}", version);

    Ok(HttpServer::new(move || {
        App::new()
            .app_data(state.clone())
            .app_data(web::PayloadConfig::new(26_214_400))
            .app_data(web::JsonConfig::default().limit(5_242_880))
            .app_data(web::FormConfig::default().limit(26_214_400))
            .default_service(web::route().to(proxy_handler))})
    .bind("0.0.0.0:8086")?
    .run()
    .await?)
}

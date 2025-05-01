#![forbid(unsafe_code)]

use actix_web::{
    App,
    HttpResponse,
    HttpServer,
    Responder,
    get,
    middleware::from_fn
};
use plural_core::{init_mongo, init_otel, init_redis, shutdown_otel};

mod error;
mod handlers;
mod middleware;
mod models;


#[get("/healthcheck")]
async fn greet() -> impl Responder {
    HttpResponse::NoContent().finish()
}

#[actix_web::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    init_otel("api")?;

    init_mongo(true).await?;

    init_redis().await?;

    HttpServer::new(|| {
        App::new()
            .wrap(from_fn(middleware::otel))
            .configure(handlers::message)
    })
    .bind(("0.0.0.0", 8000))?
    .run()
    .await?;

    shutdown_otel()
}

use std::net::SocketAddr;

use http_body_util::Empty;
use hyper::{
    Method,
    Request,
    Response,
    StatusCode,
    body::Bytes,
    server::conn::http1,
    service::service_fn
};
use hyper_util::rt::TokioIo;
use tokio::net::TcpListener;

async fn healthcheck(
    req: Request<hyper::body::Incoming>
) -> Result<Response<Empty<Bytes>>, hyper::Error> {
    Ok(match (req.method(), req.uri().path()) {
        (&Method::GET, "/healthcheck") => Response::builder()
            .status(StatusCode::NO_CONTENT)
            .body(Empty::new())
            .unwrap(),
        _ => Response::builder()
            .status(StatusCode::NOT_FOUND)
            .body(Empty::new())
            .unwrap()
    })
}

pub fn spawn_healthcheck_server() {
    tokio::spawn(async move {
        let address: SocketAddr = ([0, 0, 0, 0], 8083).into();

        let listener = match TcpListener::bind(address).await {
            Ok(l) => l,
            Err(e) => {
                eprintln!("Failed to bind healthcheck server: {e}");
                return;
            }
        };

        println!("Healthcheck server listening on {address}");

        loop {
            let (stream, _) = match listener.accept().await {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("Healthcheck failed to accept connection: {e}");
                    continue;
                }
            };

            let io = TokioIo::new(stream);

            tokio::task::spawn(async move {
                if let Err(e) = http1::Builder::new()
                    .serve_connection(io, service_fn(healthcheck))
                    .await
                {
                    eprintln!("Healthcheck error serving connection: {e:?}");
                }
            });
        }
    });
}

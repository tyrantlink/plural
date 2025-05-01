use std::{collections::HashMap, str::FromStr};

use actix_web::{
    Error,
    body::MessageBody,
    dev::{ServiceRequest, ServiceResponse},
    middleware::Next
};
use http::{HeaderMap, HeaderName, HeaderValue};
use opentelemetry::{
    global,
    trace::{Span, Tracer}
};
use opentelemetry_http::HeaderExtractor;
use plural_core::env;

lazy_static::lazy_static! {
    static ref ROUTE_MAP: HashMap<String, String> = {
        HashMap::from([
            ("/messages/{channel_id}/{message_id}", "/messages/:id/:id")
        ].map(|(k, v)| (k.to_string(), v.to_string())))
    };
}

pub async fn otel_middleware(
    request: ServiceRequest,
    next: Next<impl MessageBody>
) -> Result<ServiceResponse<impl MessageBody>, Error> {
    let Some(route) = request
        .match_pattern()
        .and_then(|route| ROUTE_MAP.get(&route))
    else {
        return next.call(request).await;
    };

    let tracer = global::tracer("");

    let span = tracer
        .span_builder(format!("{} {}", request.method(), route))
        .with_kind(opentelemetry::trace::SpanKind::Server)
        .with_attributes(vec![
            opentelemetry::KeyValue::new(
                "http.method",
                request.method().to_string()
            ),
            opentelemetry::KeyValue::new(
                "http.path",
                request.uri().path().to_string()
            ),
            opentelemetry::KeyValue::new(
                "http.query",
                request.uri().query().unwrap_or_default().to_string()
            ),
        ]);

    let mut span = if request
        .headers()
        .get("Authorization")
        .map(|s| s.to_str().unwrap_or_default()) ==
        Some(format!("Bearer {}", env().internal_master_token).as_str())
    {
        span.start_with_context(
            &tracer,
            &global::get_text_map_propagator(|propagator| {
                propagator.extract(&HeaderExtractor(&HeaderMap::from_iter(
                    request.headers().iter().map(|(k, v)| {
                        (
                            HeaderName::from_str(k.as_str())
                                .unwrap_or(HeaderName::from_static("")),
                            HeaderValue::from_str(
                                v.to_str().unwrap_or_default()
                            )
                            .unwrap_or(HeaderValue::from_static(""))
                        )
                    })
                )))
            })
        )
    } else {
        span.start(&tracer)
    };

    let response = next.call(request).await;

    span.set_attribute(opentelemetry::KeyValue::new(
        "http.status_code",
        match response {
            Ok(ref res) => res.status().to_string(),
            Err(_) => "500".to_string()
        }
    ));

    response
}

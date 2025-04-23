use std::time::Duration;

use crate::env::env;
use crate::version::get_version;
use opentelemetry::{
    global,
    KeyValue
};
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::{Resource, propagation::TraceContextPropagator};

pub fn init_otel(name: &str) -> Result<(), Box<dyn std::error::Error>> {
    let version = get_version(name);

    global::set_text_map_propagator(TraceContextPropagator::new());

    let resource = Resource::new(vec![
        KeyValue::new("service.name", name.to_string()),
        KeyValue::new("service.version", version.clone()),
        KeyValue::new("deployment.environment.name",
            if env().dev { "dev" } else { "prod" })
    ]);

    global::set_tracer_provider(
        opentelemetry_sdk::trace::TracerProvider::builder()
        .with_resource(resource.clone())
        .with_batch_exporter(
        opentelemetry_otlp::SpanExporter::builder()
            .with_http()
            .with_protocol(opentelemetry_otlp::Protocol::HttpBinary)
            .build()?,
        opentelemetry_sdk::runtime::Tokio)
        .build()
    );

    global::set_meter_provider(
        opentelemetry_sdk::metrics::SdkMeterProvider::builder()
            .with_resource(resource)
            .with_reader(opentelemetry_sdk::metrics::PeriodicReader::builder(
                opentelemetry_otlp::MetricExporter::builder()
                .with_http()
                .with_protocol(opentelemetry_otlp::Protocol::HttpBinary)
                .with_temporality(opentelemetry_sdk::metrics::Temporality::Delta)
                .build()?,
                opentelemetry_sdk::runtime::Tokio)
            .with_interval(Duration::from_secs(60))
            .build())
            .build()
    );

    Ok(())
}
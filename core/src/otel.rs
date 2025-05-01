use std::{sync::OnceLock, time::Duration};

use opentelemetry::{KeyValue, global};
use opentelemetry_otlp::WithExportConfig;
use opentelemetry_sdk::{
    Resource,
    metrics::SdkMeterProvider,
    propagation::TraceContextPropagator,
    trace::TracerProvider as SdkTracerProvider
};

use crate::{env::env, version::get_version};

static GLOBAL_TRACER_PROVIDER: OnceLock<SdkTracerProvider> = OnceLock::new();
static GLOBAL_METER_PROVIDER: OnceLock<SdkMeterProvider> = OnceLock::new();


pub fn init_otel(name: &str) -> Result<(), Box<dyn std::error::Error>> {
    let version = get_version(name);

    global::set_text_map_propagator(TraceContextPropagator::new());

    let resource = Resource::new(vec![
        KeyValue::new("service.name", name.to_string()),
        KeyValue::new("service.version", version.clone()),
        KeyValue::new(
            "deployment.environment.name",
            if env().dev { "dev" } else { "prod" }
        ),
    ]);

    let tracer_provider = opentelemetry_sdk::trace::TracerProvider::builder()
        .with_resource(resource.clone())
        .with_batch_exporter(
            opentelemetry_otlp::SpanExporter::builder()
                .with_http()
                .with_protocol(opentelemetry_otlp::Protocol::HttpBinary)
                .build()?,
            opentelemetry_sdk::runtime::Tokio
        )
        .build();

    let meter_provider =
        opentelemetry_sdk::metrics::SdkMeterProvider::builder()
            .with_resource(resource)
            .with_reader(
                opentelemetry_sdk::metrics::PeriodicReader::builder(
                    opentelemetry_otlp::MetricExporter::builder()
                        .with_http()
                        .with_protocol(opentelemetry_otlp::Protocol::HttpBinary)
                        .with_temporality(
                            opentelemetry_sdk::metrics::Temporality::Delta
                        )
                        .build()?,
                    opentelemetry_sdk::runtime::Tokio
                )
                .with_interval(Duration::from_secs(60))
                .build()
            )
            .build();

    GLOBAL_TRACER_PROVIDER
        .set(tracer_provider.clone())
        .expect("Failed to set global tracer provider");
    GLOBAL_METER_PROVIDER
        .set(meter_provider.clone())
        .expect("Failed to set global meter provider");

    global::set_tracer_provider(tracer_provider);
    global::set_meter_provider(meter_provider);

    Ok(())
}

pub fn shutdown_otel() -> Result<(), Box<dyn std::error::Error>> {
    if let Some(provider) = GLOBAL_TRACER_PROVIDER.get() {
        provider.force_flush();
        provider.shutdown()?;
    }
    if let Some(provider) = GLOBAL_METER_PROVIDER.get() {
        provider.force_flush()?;
        provider.shutdown()?;
    }

    Ok(())
}

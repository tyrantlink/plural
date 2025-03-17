from __future__ import annotations

from logging import Filter, LogRecord, getLogger
from typing import TYPE_CHECKING

from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import set_global_textmap, extract, inject as _inject
from opentelemetry.propagators.textmap import default_setter
from opentelemetry.sdk.resources import Resource
from requests.exceptions import ConnectionError
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SpanExportResult,
    ReadableSpan
)
from opentelemetry.sdk.trace import (
    TracerProvider,
    Span,
    Tracer
)
from opentelemetry.trace import (
    get_tracer as _get_tracer,
    set_tracer_provider,
    SpanKind,
    get_current_span
)
from opentelemetry.sdk.metrics.export import (
    PeriodicExportingMetricReader
)
from opentelemetry.sdk.metrics import (
    MeterProvider,
    Counter
)
from opentelemetry.metrics import (
    get_meter as _get_meter,
    set_meter_provider
)

from .env import env, INSTANCE


if TYPE_CHECKING:
    from collections.abc import Sequence

    from opentelemetry.util._decorator import _AgnosticContextManager
    from opentelemetry.propagators.textmap import CarrierT, Setter
    from opentelemetry.context import Context


__all__ = (
    'SpanKind',
    'get_tracer',
    'init_otel',
    'inject',
    'span',
)


set_global_textmap(TraceContextTextMapPropagator())

otel_resource: Resource


class SuppressMissingModuleNameError(Filter):
    def filter(self, record: LogRecord) -> bool:
        return 'get_tracer called with missing module name.' not in record.msg


class SuppressConnectionResetError(Filter):
    def filter(self, record: LogRecord) -> bool:
        return 'Connection Reset by Peer' not in record.msg


class SimpleConsoleSpanExporter(ConsoleSpanExporter):
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            if span.parent is not None:
                continue

            self.out.write(span.name + '\n')

        self.out.flush()

        return SpanExportResult.SUCCESS


class FakeServerError:
    status_code = 500
    ok = False
    reason = 'Connection Reset by Peer'
    text = 'Connection Reset by Peer'


def _retry_export(self, serialized_data: bytes):  # noqa: ANN001, ANN202
    from opentelemetry.exporter.otlp.proto.http import Compression
    from io import BytesIO
    import gzip
    import zlib

    data = serialized_data
    if self._compression == Compression.Gzip:
        gzip_data = BytesIO()
        with gzip.GzipFile(fileobj=gzip_data, mode="w") as gzip_stream:
            gzip_stream.write(serialized_data)
        data = gzip_data.getvalue()
    elif self._compression == Compression.Deflate:
        data = zlib.compress(serialized_data)

    try:
        return self._session.post(
            url=self._endpoint,
            data=data,
            verify=self._certificate_file,
            timeout=self._timeout,
            cert=self._client_cert)
    except ConnectionError:
        return FakeServerError()


class RetryOTLPSpanExporter(OTLPSpanExporter):
    _export = _retry_export


class RetryOTLPMetricExporter(OTLPMetricExporter):
    _export = _retry_export


def get_tracer(name: str | None = None) -> Tracer:
    return _get_tracer(name or '')


def get_counter(name: str) -> Counter:
    return _get_meter(
        otel_resource.attributes.get('service.name'),
        otel_resource.attributes.get('service.version')
    ).create_counter(name)


def span(
    name: str,
    tracer_name: str | None = None,
    context: Context | None = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: dict | None = None,
    parent: str | None = None,
    **kwargs  # noqa: ANN003
) -> _AgnosticContextManager[Span]:
    if context and parent:
        raise ValueError('context and parent are mutually exclusive')

    return get_tracer(tracer_name).start_as_current_span(
        name,
        context=context or (
            extract({'traceparent': parent})
            if parent else None),
        kind=kind,
        attributes=attributes,
        **kwargs
    )


def init_otel(name: str, version: str) -> None:
    global otel_resource

    otel_resource = Resource({
        'service.name': name,
        'service.version': version,
        'service.instance.id': INSTANCE,
        'deployment.environment.name': (
            'dev' if env.dev else 'prod'
        )
    })

    tracer_provider = TracerProvider(resource=otel_resource)

    set_tracer_provider(tracer_provider)

    meter_provider = MeterProvider(
        resource=otel_resource,
        metric_readers=[
            PeriodicExportingMetricReader(
                RetryOTLPMetricExporter(),
                60000
            )
        ]
    )

    set_meter_provider(meter_provider)

    getLogger(
        'opentelemetry.sdk.trace'
    ).addFilter(
        SuppressMissingModuleNameError()
    )

    getLogger(
        'opentelemetry.exporter.otlp.proto.http.trace_exporter'
    ).addFilter(
        SuppressConnectionResetError()
    )

    tracer_provider.add_span_processor(
        BatchSpanProcessor(RetryOTLPSpanExporter()))
    tracer_provider.add_span_processor(
        BatchSpanProcessor(SimpleConsoleSpanExporter())
    )


def inject(
    carrier: CarrierT,
    context: Context | None = None,
    setter: Setter[CarrierT] = default_setter,
) -> CarrierT:
    """Uses the configured propagator to inject a Context into the carrier.

    Args:
        carrier: the medium used by Propagators to read
            values from and write values to.
            Should be paired with setter, which
            should know how to set header values on the carrier.
        context: An optional Context to use. Defaults to current
            context if not set.
        setter: An optional `Setter` object that can set values
            on the carrier.
    """
    _inject(carrier, context=context, setter=setter)

    return carrier


def cx() -> Span:
    return get_current_span()

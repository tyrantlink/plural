from os import environ

from pymongo import MongoClient

from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.metrics import Observation
from requests import get, ConnectionError

from version import load_semantic_version


class FakeServerError:
    status_code = 500
    ok = False
    reason = 'Connection Reset by Peer'
    text = 'Connection Reset by Peer'


class RetryOTLPMetricExporter(OTLPMetricExporter):
    def _export(self, serialized_data: bytes):  # noqa: ANN202
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


def main() -> None:
    mongo_uri = environ.get("MONGO_URL")
    dev = environ.get('DEV', '1') != '0'
    token = environ.get('BOT_TOKEN')

    version, _ = load_semantic_version('metrics')

    if not mongo_uri:
        raise ValueError("MONGO_URL environment variable is not set")

    if not token:
        raise ValueError("BOT_TOKEN environment variable is not set")

    mongo = MongoClient(mongo_uri)

    provider = MeterProvider(
        resource=Resource({
            'service.name': 'metrics',
            'service.version': version,
            'deployment.environment.name': (
                'dev' if dev else 'prod')}),
        metric_readers=[PeriodicExportingMetricReader(
            RetryOTLPMetricExporter(),
            60000
        )]
    )

    application = get(
        'https://discord.com/api/v10/applications/@me',
        headers={'Authorization': f'Bot {token}'}
    ).json()

    guilds: int = application.get('approximate_guild_count', 0)
    users: int = application.get('approximate_user_install_count', 0)
    registered_users = mongo.plural.usergroups.count_documents({})
    groups = mongo.plural.groups.count_documents({})
    members = mongo.plural.members.count_documents({})

    meter = provider.get_meter(
        'metrics',
        version
    )

    for name, value in {
        'guilds': guilds,
        'users': users,
        'registered_users': registered_users,
        'groups': groups,
        'members': members
    }.items():
        meter.create_observable_gauge(
            name,
            callbacks=[
                lambda _, v=value: [Observation(v)]
            ]
        )

    provider.force_flush()
    provider.shutdown()
    mongo.close()


if __name__ == "__main__":
    main()

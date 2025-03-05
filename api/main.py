from asyncio import set_event_loop_policy

from uvloop import EventLoopPolicy
from uvicorn import run

set_event_loop_policy(EventLoopPolicy())


def main() -> None:
    from src.core import app
    from plural.otel import init_otel
    from src.core.version import VERSION

    init_otel('api', VERSION)

    run(app, host='0.0.0.0', port=8080, forwarded_allow_ips='*')


if __name__ == '__main__':
    main()

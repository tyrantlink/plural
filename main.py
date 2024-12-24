from asyncio import set_event_loop_policy
from uvloop import EventLoopPolicy

set_event_loop_policy(EventLoopPolicy())


def main() -> None:
    from src.version import VERSION  # noqa: F401
    from src.core import app
    from uvicorn import run
    run(app, host='0.0.0.0', port=8080, forwarded_allow_ips='*')


if __name__ == '__main__':
    main()

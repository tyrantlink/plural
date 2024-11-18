from asyncio import set_event_loop_policy
from uvloop import EventLoopPolicy

set_event_loop_policy(EventLoopPolicy())


def main():
    from src.version import load_semantic_version

    load_semantic_version()

    from src.core import app
    from uvicorn import run
    run(app, host='0.0.0.0', port=8080, forwarded_allow_ips='*')


if __name__ == '__main__':
    main()

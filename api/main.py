from asyncio import set_event_loop_policy

from uvloop import EventLoopPolicy
from uvicorn import run

set_event_loop_policy(EventLoopPolicy())


def main():
    from src.core import app

    run(app, host='0.0.0.0', port=8080, forwarded_allow_ips='*')


if __name__ == '__main__':
    main()

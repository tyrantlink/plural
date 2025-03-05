from asyncio import set_event_loop_policy, run
from contextlib import suppress

from uvloop import EventLoopPolicy

set_event_loop_policy(EventLoopPolicy())


async def main() -> None:
    from src import event_listener
    from plural.otel import init_otel
    from src.version import VERSION

    init_otel('bot', VERSION)

    try:
        await event_listener()
    except BaseException as e:
        from src.http import GENERAL_SESSION, DISCORD_SESSION
        await GENERAL_SESSION.close()
        await DISCORD_SESSION.close()
        raise e


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        run(main())

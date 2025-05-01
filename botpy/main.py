from asyncio import set_event_loop_policy, run, gather
from contextlib import suppress
from sys import argv

from uvloop import EventLoopPolicy

set_event_loop_policy(EventLoopPolicy())


async def main() -> None:
    from src import event_listener, start_healthcheck
    from plural.otel import init_otel
    from src.version import VERSION

    init_otel('bot', VERSION)

    try:
        await gather(
            event_listener(),
            start_healthcheck())
    except BaseException as e:
        from src.http import GENERAL_SESSION, DISCORD_SESSION
        await GENERAL_SESSION.close()
        await DISCORD_SESSION.close()
        raise e


if __name__ == '__main__':
    # ? when building the docker image, uv sync doesn't install
    # ? the maturin stuff (caith) for some reason, so it adds like
    # ? 30 seconds to startup time
    # ? so we add this so we can uv run at build time
    # ? without actually running
    if 'stupid-workaround-docker-pain' in argv:
        exit(0)

    with suppress(KeyboardInterrupt):
        run(main())

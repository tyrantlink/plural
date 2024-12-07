from __future__ import annotations
from pydantic_core import ValidationError
from typing import TYPE_CHECKING
from traceback import format_tb
from src.models import project
from asyncio import gather
from io import BytesIO
import logfire

# ? logfire compat
from types import CodeType, FrameType
from functools import lru_cache
import opentelemetry.sdk.trace
from typing import TypedDict
from pathlib import Path
import inspect
import sys


if TYPE_CHECKING:
    from src.discord import Interaction


class BasePluralException(Exception):
    def __init__(self, *args, **kwargs) -> None:
        self._stack_info = get_user_stack_info()
        super().__init__(*args, **kwargs)


class PluralException(BasePluralException):
    ...


class HTTPException(BasePluralException):
    status_code: int = 0
    ...


class Unauthorized(HTTPException):
    status_code: int = 401
    ...


class Forbidden(HTTPException):
    status_code: int = 403
    ...


class NotFound(HTTPException):
    status_code: int = 404
    ...


class ServerError(HTTPException):
    status_code: int = 500
    ...


class ConversionError(BasePluralException):
    ...


class InteractionError(BasePluralException):
    ...


class DuplicateEventError(BasePluralException):
    ...


async def on_event_error(event: str, error: BaseException) -> None:
    from src.discord import Webhook, User, File

    tasks = []

    stack_info = {}

    if isinstance(error, BasePluralException):
        stack_info = error._stack_info

    if not isinstance(error, BasePluralException) or isinstance(error, PluralException):
        webhook = await Webhook.from_url(project.error_webhook)

        traceback = ''.join(format_tb(error.__traceback__)) + str(error)

        self_user = await User.fetch('@me')

        if len(traceback)+8 > 2000:
            tasks.append(webhook.execute(
                username=self_user.username,
                avatar_url=self_user.avatar_url,
                attachments=[
                    File(
                        BytesIO(traceback.encode()),
                        'error.txt'
                    )
                ]
            ))
        else:
            tasks.append(webhook.execute(
                f'```\n{traceback}\n```',
                username=self_user.username,
                avatar_url=self_user.avatar_url
            ))

    if not isinstance(error, (InteractionError, ConversionError)):
        logfire.error(
            '{event} event error',
            event=event,
            _exc_info=error.with_traceback(error.__traceback__),
            **stack_info,  # type: ignore #? mypy stupid
            **(
                error.errors()[0].get('input', 'no input')
                if isinstance(error, ValidationError) and error.errors()
                else {}
            )
        )

    await gather(*tasks)


async def on_interaction_error(interaction: Interaction, error: BaseException) -> None:
    from src.discord import InteractionType, Embed, Webhook, User, File

    if interaction.type not in {
        InteractionType.APPLICATION_COMMAND,
        InteractionType.MESSAGE_COMPONENT,
        InteractionType.MODAL_SUBMIT
    }:
        return

    tasks = []

    stack_info = {}

    if isinstance(error, BasePluralException):
        stack_info = error._stack_info

    if not isinstance(error, BasePluralException) or isinstance(error, PluralException):
        webhook = await Webhook.from_url(project.error_webhook)

        traceback = ''.join(format_tb(error.__traceback__)) + str(error)

        self_user = await User.fetch('@me')

        if len(traceback)+8 > 2000:
            tasks.append(webhook.execute(
                username=self_user.username,
                avatar_url=self_user.avatar_url,
                attachments=[
                    File(
                        BytesIO(traceback.encode()),
                        'error.txt'
                    )
                ]
            ))
        else:
            tasks.append(webhook.execute(
                f'```\n{traceback}\n```',
                username=self_user.username,
                avatar_url=self_user.avatar_url
            ))

    expected = isinstance(error, (InteractionError, ConversionError))

    if not expected:
        logfire.error(
            'interaction error',
            _exc_info=error.with_traceback(error.__traceback__),
            **stack_info,  # type: ignore #? mypy stupid
            **(
                error.errors()[0].get('input', 'no input')
                if isinstance(error, ValidationError) and error.errors()
                else {}
            )
        )

    send = (
        interaction.followup.send
        if interaction.response.responded else
        interaction.response.send_message
    )

    await gather(
        *tasks,
        send(
            embeds=[Embed.error(str(error), expected=expected)]
        )
    )


# ? logfire compat
# ? logfire compat
# ? logfire compat
# ? logfire compat
# ? logfire compat
# ? logfire compat
# ? logfire compat
# ? logfire compat
# ? logfire compat
# ? logfire compat
# ? logfire compat
# ? logfire compat


_CWD = Path('.').resolve()

StackInfo = TypedDict(
    'StackInfo', {
        'code.filepath': str,
        'code.lineno': int,
        'code.function': str
    },
    total=False
)

SITE_PACKAGES_DIR = str(
    Path(opentelemetry.sdk.trace.__file__).parent.parent.parent.parent.absolute())
PYTHON_LIB_DIR = str(Path(inspect.__file__).parent.absolute())
LOGFIRE_DIR = str(Path(logfire.__file__).parent.absolute())
NON_USER_CODE_PREFIXES = (SITE_PACKAGES_DIR, PYTHON_LIB_DIR, LOGFIRE_DIR)


def get_filepath_attribute(file: str) -> StackInfo:
    path = Path(file)
    if path.is_absolute():
        try:
            path = path.relative_to(_CWD)
        except ValueError:  # pragma: no cover
            # happens if filename path is not within CWD
            pass
    return {'code.filepath': str(path)}


@lru_cache(maxsize=2048)
def get_code_object_info(code: CodeType) -> StackInfo:
    result = get_filepath_attribute(code.co_filename)
    if code.co_name != '<module>':
        result['code.function'] = code.co_qualname if sys.version_info >= (
            3, 11) else code.co_name
    result['code.lineno'] = code.co_firstlineno
    return result


def get_stack_info_from_frame(frame: FrameType) -> StackInfo:
    return {
        **get_code_object_info(frame.f_code),
        'code.lineno': frame.f_lineno,
    }


def get_user_stack_info() -> StackInfo:
    """Get the stack info for the first calling frame in user code.

    See is_user_code for details.
    Returns an empty dict if no such frame is found.
    """
    frame, _stacklevel = get_user_frame_and_stacklevel()
    if frame:
        return get_stack_info_from_frame(frame)
    return {}


def get_user_frame_and_stacklevel() -> tuple[FrameType | None, int]:
    """Get the first calling frame in user code and a corresponding stacklevel that can be passed to `warnings.warn`.

    See is_user_code for details.
    Returns `(None, 0)` if no such frame is found.
    """
    frame = inspect.currentframe()
    stacklevel = 0
    while frame:
        if is_user_code(frame.f_code):
            return frame, stacklevel
        frame = frame.f_back
        stacklevel += 1
    return None, 0


@lru_cache(maxsize=8192)
def is_user_code(code: CodeType) -> bool:
    """Check if the code object is from user code.

    A code object is not user code if:
    - It is from a file in
        - the standard library
        - site-packages (specifically wherever opentelemetry is installed)
        - the logfire package
    - It is a list/dict/set comprehension.
        These are artificial frames only created before Python 3.12,
        and they are always called directly from the enclosing function so it makes sense to skip them.
        On the other hand, generator expressions and lambdas might be called far away from where they are defined.
    """

    if (
        (
            info := get_code_object_info(code)
        ) and (
            info.get('code.filepath') == 'src/errors.py' and
            info.get('code.function') in {
                'get_user_frame_and_stacklevel',
                'get_user_stack_info',
                'on_interaction_error',
                'BasePluralException.__init__'
            }
        ) or (
            info.get('code.filepath') == 'src/discord/listeners.py' and
            info.get('code.function') == 'emit'
        )
    ):
        return False

    return not (
        str(Path(code.co_filename).absolute()
            ).startswith(NON_USER_CODE_PREFIXES)
        or code.co_name in ('<listcomp>', '<dictcomp>', '<setcomp>')
    )

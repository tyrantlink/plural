from collections.abc import Coroutine
from asyncio import create_task, Task

__all__ = (
    'create_strong_task',
)


def create_strong_task(coroutine: Coroutine) -> Task:
    """
    create a task that will not be cancelled by the event loop
    """
    task = create_task(coroutine)
    task.add_done_callback(lambda _: None)
    return task

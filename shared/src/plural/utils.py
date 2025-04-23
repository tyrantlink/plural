from __future__ import annotations

from typing import TYPE_CHECKING
from asyncio import create_task

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from asyncio import Task


__all__ = (
    'create_strong_task',
)


def create_strong_task(coroutine: Coroutine) -> Task:
    """
    create a task that will not be cancelled by the event loop
    """
    task = create_task(coroutine)

    tasks = {task}

    task.add_done_callback(tasks.discard)

    return task

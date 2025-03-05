from __future__ import annotations

from typing import TYPE_CHECKING
from textwrap import dedent
from asyncio import gather

from plural.errors import HTTPException, InteractionError, ConversionError

from plural.otel import cx


if TYPE_CHECKING:
    from src.discord import Interaction


async def on_interaction_error(
    interaction: Interaction,
    error: Exception
) -> None:
    from src.discord import InteractionType, Embed, MessageFlag

    if interaction.type not in {
        InteractionType.APPLICATION_COMMAND,
        InteractionType.MESSAGE_COMPONENT,
        InteractionType.MODAL_SUBMIT
    }:
        return

    expected = isinstance(
        error,
        InteractionError |
        ConversionError |
        NotImplementedError
    )

    error_message = dedent(str(error)).strip()

    if isinstance(error, NotImplementedError):
        error_message = 'This feature is not implemented yet.'

    cx().set_attribute('response.error', error_message)

    responses = await gather(
        interaction.send(
            embeds=[Embed.error(error_message, expected=expected)],
            flags=MessageFlag.EPHEMERAL),
        return_exceptions=True
    )

    if isinstance(responses[-1], HTTPException):
        await interaction.followup.send(
            embeds=[Embed.error(error_message, expected=expected)]
        )

    if not expected:
        raise error

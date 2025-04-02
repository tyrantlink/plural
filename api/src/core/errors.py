from __future__ import annotations

from typing import TYPE_CHECKING
from contextlib import suppress
from textwrap import dedent
from asyncio import gather

from pydantic import BaseModel, ValidationError

from plural.errors import HTTPException, InteractionError, ConversionError
from plural.missing import MISSING

from plural.otel import cx


if TYPE_CHECKING:
    from src.discord import Interaction


class DiscordErrorResponse(BaseModel):
    message: str
    code: int
    errors: dict[
        str,
        dict[
            str,
            list[
                dict[str, str]
            ]
        ]
    ]


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

    error_embed = Embed.error(
        dedent(str(error)).strip()[:4095],
        expected=expected
    )

    if isinstance(error, InteractionError) and error.footer:
        error_embed.set_footer(text=error.footer)

    if isinstance(error, NotImplementedError):
        error_embed.description = 'This feature is not implemented yet.'

    cx().set_attribute(
        'response.error',
        error_embed.description
    )

    if isinstance(error, HTTPException):
        with suppress(ValidationError):
            discord_error = DiscordErrorResponse.model_validate(
                error.detail)
            expected = True
            error_embed.description = MISSING
            error_embed.title = 'Discord Error!'

            for field, errors in discord_error.errors.items():
                for detail in errors.get('_errors', []):
                    error_embed.add_field(
                        name=f'{field}: {detail['code']}',
                        value=detail['message']
                    )

            if len(error_embed.fields) == 0:
                error_embed.description = discord_error.message

            if len(error_embed.fields) > 25:
                error_embed.fields = error_embed.fields[:25]

            if 'RATE_LIMIT' in discord_error.code:
                error_embed.footer = (
                    'This looks like a discord rate limit error, '
                    'please try again in ~30 minutes.\n'
                    'Your member changes have still been saved, '
                    'but the userproxy is likely desynced.'
                )

    responses = await gather(
        interaction.send(
            embeds=[error_embed],
            flags=MessageFlag.EPHEMERAL),
        return_exceptions=True
    )

    if isinstance(responses[-1], HTTPException):
        await interaction.followup.send(
            embeds=[error_embed],
            flags=MessageFlag.EPHEMERAL
        )

    if not expected:
        raise error

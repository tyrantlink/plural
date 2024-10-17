from src.api.models.discord import Interaction, Attachment
from fastapi.responses import Response


#! remember to rename to attachment when you fix command
async def _slash_proxy(
    interaction: Interaction,
    message: str,
    attachments: Attachment | None = None,
    queue_for_reply: bool = False,
    **kwargs
) -> Response:
    return await interaction.response.send_message(
        content=message,
        attachments=[attachments] if attachments else None,
        ephemeral=queue_for_reply
    )


async def _message_reply(
    interaction: Interaction
) -> Response:
    ...
    # ? need to create modal, and make some sort of listener for the submission, probably with TTLdict[id, event] or something


async def _message_edit(
    interaction: Interaction
) -> Response:
    ...
    # ? needs same modal listener maybe use backround task

    # ? actually probably don't, continue stateless, for reply queue, just store in db, and then on modal submit, read from db and send message

    # ? and for edit, if the modal returns message object, edit the message, if it's stored in db, read webhook token from db and edit the message


async def on_command(interaction: Interaction) -> Response:
    assert interaction.data is not None

    options = {
        option.name: option.value
        for option in interaction.data.options or []
    }

    match interaction.data.name:
        case 'proxy':
            return await _slash_proxy(
                interaction,
                **options  # type: ignore #? i don't wanna deal with this
            )
        case 'reply':
            return await _message_reply(interaction)
        case 'edit':
            return await _message_edit(interaction)
        case _:
            raise ValueError('Invalid command name')

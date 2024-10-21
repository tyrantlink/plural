from src.api.models.discord import Interaction, Attachment
from src.db.reply import Reply, ReplyAttachment
from fastapi.responses import Response


#! remember to rename to attachment when you fix command
async def _slash_proxy(
    interaction: Interaction,
    message: str | None = None,
    attachment: Attachment | None = None,
    queue_for_reply: bool = False,
    **kwargs
) -> Response:
    if not message and not attachment:
        return await interaction.response.send_message(
            content='Please provide a message or attachment',
            ephemeral=True
        )

    if not queue_for_reply:
        return await interaction.response.send_message(
            content=message,
            attachment=attachment,
            ephemeral=False
        )

    reply = Reply(
        bot_id=int(interaction.application_id),
        channel=int(interaction.channel_id or '0'),
        content=message,
        attachment=(
            ReplyAttachment.model_validate(attachment.model_dump())
            if attachment
            else None
        )
    )

    await reply.save()

    return await interaction.response.send_message(
        content='Message queued for reply | use the reply command within the next 5 minutes',
        ephemeral=True
    )


async def _message_reply(
    interaction: Interaction
) -> Response:
    reply = await Reply.find_one({
        'bot_id': int(interaction.application_id),
        'channel': int(interaction.channel_id or '0')
    })

    if reply is None:
        return await interaction.response.send_message(
            content='No message queued for reply in this channel. please use /proxy to queue a message',
            ephemeral=True
        )

    await reply.delete()

    return await interaction.response.send_message(
        content=reply.content,
        attachment=(
            Attachment.model_validate(reply.attachment.model_dump())
            if reply.attachment
            else None
        ),
        ephemeral=False
    )


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

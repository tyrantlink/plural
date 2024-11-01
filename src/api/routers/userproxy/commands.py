from src.api.models.discord import Interaction, Attachment, TextInput, TextInputStyle, InteractionType, Permission
from src.api.models.discord.interaction import CommandInteractionData, ModalInteractionData
from src.api.models.discord.component import TextInput
from src.db.reply import Reply, ReplyAttachment
from typing import TYPE_CHECKING
from src.db import UserProxy


async def _slash_proxy(
    interaction: Interaction,
    message: str | None = None,
    attachment: Attachment | None = None,
    queue_for_reply: bool = False,
    **kwargs
) -> None:
    if not message and not attachment:
        return await interaction.send_modal(
            title='proxy a message',
            custom_id='send',
            components=[
                TextInput(
                    custom_id='message',
                    style=TextInputStyle.LONG,
                    max_length=2000,
                    label='message',
                    placeholder='message content\nyou should only use this if you need to send a message with newlines',
                    required=True
                )
            ]
        )

    if not queue_for_reply:
        return await interaction.send_message(
            content=message,
            attachment=attachment,
            ephemeral=False
        )

    if (
        attachment and
        not int(interaction.app_permissions) & Permission.ATTACH_FILES.value
    ):
        return await interaction.send_message(
            content='you do not have permission to send attachments in this channel!',
            ephemeral=True
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

    return await interaction.send_message(
        content='Message queued for reply | use the reply command within the next 5 minutes',
        ephemeral=True
    )


async def _message_reply(
    interaction: Interaction
) -> None:
    reply = await Reply.find_one({
        'bot_id': int(interaction.application_id),
        'channel': int(interaction.channel_id or '0')
    })

    if reply is None:
        return await interaction.send_modal(
            title='reply to a message',
            custom_id='send',
            components=[
                TextInput(
                    custom_id='message',
                    style=TextInputStyle.LONG,
                    max_length=2000,
                    label='message',
                    required=True
                )
            ]
        )

    await interaction.send_message(
        content=reply.content,
        attachment=(
            Attachment.model_validate(reply.attachment.model_dump())
            if reply.attachment
            else None
        ),
        ephemeral=False
    )

    await reply.delete()


async def _message_edit(
    interaction: Interaction
) -> None:
    assert interaction.data is not None
    assert interaction.data.resolved.messages is not None
    message = list(interaction.data.resolved.messages.values())[0]
    assert message.author is not None

    if message.author.id != interaction.application_id:
        return await interaction.send_message(
            content='you can only edit your own messages!',
            ephemeral=True
        )

    content = message.content

    return await interaction.send_modal(
        title='edit your message',
        custom_id=f'edit_{message.id}',
        components=[
            TextInput(
                custom_id='message',
                style=TextInputStyle.LONG,
                label='message',
                value=content,
                required=True
            )
        ]
    )


async def _custom_command_name(interaction: Interaction) -> str | None:
    user_proxy = await UserProxy.find_one({'bot_id': int(interaction.application_id)})
    if user_proxy is None:
        return None

    return user_proxy.command


async def on_command(interaction: Interaction) -> None:
    assert interaction.type == InteractionType.APPLICATION_COMMAND
    if TYPE_CHECKING:
        assert isinstance(interaction.data, CommandInteractionData)
    # ? i have spent like, two hours trying to figure out a better way to have the linter determine the types
    # ? but nothing i've tried has worked, so i'm just gonna assert the types and move on

    options = {
        option.name: option.value
        for option in interaction.data.options or []
    }

    match interaction.data.name:
        case 'proxy':
            await _slash_proxy(
                interaction,
                **options  # type: ignore #? i don't wanna deal with this
            )
        case 'reply':
            await _message_reply(interaction)
        case 'edit':
            await _message_edit(interaction)
        case unknown if unknown == await _custom_command_name(interaction):
            await _slash_proxy(
                interaction,
                **options  # type: ignore #? i don't wanna deal with this
            )
        case _:
            raise ValueError('Invalid command name')


async def on_modal_submit(interaction: Interaction) -> None:
    assert interaction.data is not None
    assert interaction.type == InteractionType.MODAL_SUBMIT
    if TYPE_CHECKING:
        assert isinstance(interaction.data, ModalInteractionData)

    content = interaction.data.components[0].components[0].value
    assert content is not None  # ? discord won't send a value if it's empty

    match interaction.data.custom_id.split('_'):
        case 'send', *_:
            await interaction.send_message(
                content=content,
                ephemeral=False
            )
        case 'edit', message_id:
            await interaction.edit_message(
                int(message_id),
                content=content
            )
        case _:
            raise ValueError('Unknown custom id')

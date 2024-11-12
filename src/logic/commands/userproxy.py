from src.discord import slash_command, message_command, Interaction, ApplicationCommandScope, Attachment, MessageFlag, ApplicationCommandOption, ApplicationCommandOptionType, Message
from src.logic.modals.userproxy import umodal_send, umodal_edit
from src.db import Reply


@slash_command(
    name='proxy',
    description='send a message',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='message',
            description='message to send',
            required=False
        ),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.ATTACHMENT,
            name='attachment',
            description='attachment to send',
            required=False
        ),
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.BOOLEAN,
            name='queue_for_reply',
            description='queue for reply',
            required=False
        )],
    scope=ApplicationCommandScope.USERPROXY)
async def uslash_proxy(
    interaction: Interaction,
    message: str | None = None,
    attachment: Attachment | None = None,
    queue_for_reply: bool = False
) -> None:
    if not message and not attachment:
        await interaction.response.send_modal(
            modal=umodal_send.with_title(
                'proxy a message'
            ).with_text_placeholder(0, 'you should only use this if you need to send a message with newlines')
        )
        return

    sender = (
        interaction.followup.send
        if attachment else
        interaction.response.send_message
    )

    if attachment:
        await interaction.response.defer(MessageFlag.NONE)

    if not queue_for_reply:
        await sender(
            content=message,
            attachments=[await attachment.as_file()] if attachment else None,
            flags=MessageFlag.NONE
        )
        return

    await Reply(
        bot_id=int(interaction.application_id),
        channel=int(interaction.channel_id or 0),
        content=message,
        attachment=(
            Reply.Attachment(
                url=attachment.url,
                filename=attachment.filename,
                description=attachment.description
            ) if attachment
            else None
        )
    ).save()

    await interaction.response.send_message(  # ! make this a success embed
        content='Message queued for reply | use the reply command within the next 5 minutes to send your message',
    )


@message_command(
    name='reply',
    scope=ApplicationCommandScope.USERPROXY)
async def umessage_reply(
    interaction: Interaction,
    message: Message
) -> None:
    reply = await Reply.find_one({
        'bot_id': int(interaction.application_id),
        'channel': int(interaction.channel_id or 0)
    })

    if reply is None:
        await interaction.response.send_modal(
            modal=umodal_send.with_title(
                f'reply to {
                    message.author.username if message.author else 'a message'}'
            ))
        return

    attachment = (
        await reply.attachment.as_file()
        if reply.attachment
        else None
    )

    sender = (
        interaction.followup.send
        if attachment else
        interaction.response.send_message
    )

    if attachment:
        await interaction.response.defer(MessageFlag.NONE)

    await sender(
        content=reply.content,
        attachments=[attachment] if attachment else None,
        flags=MessageFlag.NONE
    )

    await reply.delete()


@message_command(
    name='edit',
    scope=ApplicationCommandScope.USERPROXY)
async def umessage_edit(
    interaction: Interaction,
    message: Message
) -> None:
    await interaction.response.send_modal(
        modal=umodal_edit.with_title(
            'edit message'
        ).with_text_value(
            0, message.content
        ).with_extra([str(message.id)])
    )

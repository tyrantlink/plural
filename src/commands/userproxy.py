from src.discord import slash_command, message_command, Interaction, ApplicationCommandScope, Attachment, MessageFlag, ApplicationCommandOption, ApplicationCommandOptionType, Message, Embed, Permission, ApplicationIntegrationType
from src.components.userproxy import umodal_send, umodal_edit
from src.db import Reply, UserProxyInteraction
from src.errors import InteractionError
from src.models import project


@slash_command(
    name='proxy',
    description='send a message',
    options=[
        ApplicationCommandOption(
            type=ApplicationCommandOptionType.STRING,
            name='message',
            min_length=0,
            max_length=2000,
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
    scope=ApplicationCommandScope.USERPROXY,
    integration_types=[ApplicationIntegrationType.USER_INSTALL])
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
            ).with_text_kwargs(
                0, placeholder='you should only use this if you need to send a message with newlines'
            ).with_extra(
                queue_for_reply
            )
        )
        return

    sender = (
        interaction.followup.send
        if attachment else
        interaction.response.send_message
    )

    if attachment:
        assert interaction.app_permissions is not None
        if not interaction.app_permissions & Permission.ATTACH_FILES:
            raise InteractionError(
                'bot does not have permission to attach files in this channel')

        await interaction.response.defer(MessageFlag.NONE)

    if not queue_for_reply:
        sent_message = await sender(
            content=message,
            attachments=[await attachment.as_file()] if attachment else None,
            flags=MessageFlag.NONE
        )

        await UserProxyInteraction(
            application_id=interaction.application_id,
            message_id=sent_message.id,
            token=interaction.token
        ).save()
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

    await interaction.response.send_message(
        embeds=[
            Embed.success(
                title='message queued for reply',
                message='use the reply command within the next 5 minutes to send your message'
            )
        ],
    )


@message_command(
    name='reply',
    scope=ApplicationCommandScope.USERPROXY,
    integration_types=[ApplicationIntegrationType.USER_INSTALL])
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

    sent_message = await sender(
        content=reply.content,
        attachments=[attachment] if attachment else None,
        flags=MessageFlag.NONE
    )

    await reply.delete()

    await UserProxyInteraction(
        application_id=interaction.application_id,
        message_id=sent_message.id,
        token=interaction.token
    ).save()


@message_command(
    name='edit',
    scope=ApplicationCommandScope.USERPROXY,
    integration_types=[ApplicationIntegrationType.USER_INSTALL])
async def umessage_edit(
    interaction: Interaction,
    message: Message
) -> None:
    userproxy_interaction = await UserProxyInteraction.find_one({
        'message_id': message.id
    })

    if userproxy_interaction is None:
        raise InteractionError(
            'message not found\ndue to discord limitations, you can\'t edit messages that are older than 15 minutes')

    if userproxy_interaction.application_id != interaction.application_id != message.webhook_id:
        raise InteractionError('you can only edit your own messages!')

    await interaction.response.send_modal(
        modal=umodal_edit.with_title(
            'edit message'
        ).with_text_kwargs(
            0, value=message.content
        ).with_extra(
            message.id
        )
    )

    await interaction.followup.send(
        embeds=[
            Embed.warning(
                title='deprecation warning',
                message='\n\n'.join([
                    'userproxy edit command is deprecated and will be removed in the future',
                    'please add /plu/ral as a user app to edit messages',
                    f'you can add /plu/ral by clicking [here](https://discord.com/oauth2/authorize?client_id={
                        project.application_id})',
                    'once you have added /plu/ral, you can run /member userproxy sync to remove this command'
                ])
            )
        ]
    )

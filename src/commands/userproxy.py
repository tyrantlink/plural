from src.discord import slash_command, message_command, Interaction, ApplicationCommandScope, Attachment, MessageFlag, ApplicationCommandOption, ApplicationCommandOptionType, Message, Embed, Permission, ApplicationIntegrationType, InteractionContextType, Webhook
from regex import match as regex_match, sub, error as RegexError, IGNORECASE, escape
from src.components.userproxy import umodal_send, umodal_edit
from src.errors import InteractionError, NotFound
from src.db import Reply, UserProxyInteraction
from beanie import SortDirection
from src.models import project
from asyncio import gather


SED_PATTERN = r'^s/(.*?)/(.*?)/?([gi]*)$'


async def _sed_edit(
    interaction: Interaction,
    message: str
) -> bool:
    match = regex_match(SED_PATTERN, message)

    if not match:
        return False

    expression, replacement, _raw_flags = match.groups()

    flags = 0
    count = 1

    for flag in _raw_flags:
        match flag:
            case 'g':
                count = 0
            case 'i':
                flags |= IGNORECASE
            case _:  # ? should never happen as it doesn't match the pattern
                raise InteractionError(f'invalid flag: {flag}')

    userproxy_interaction = await UserProxyInteraction.find(
        {
            'application_id': interaction.application_id,
            'channel_id': interaction.channel_id
        },
        ignore_cache=True
    ).sort(('ts', SortDirection.DESCENDING)).limit(1).to_list()

    if not userproxy_interaction:
        raise InteractionError(
            'no message found; messages older than 15 minutes cannot be edited')

    userproxy_interaction = userproxy_interaction[0]

    webhook = Webhook.from_proxy_interaction(
        userproxy_interaction
    )

    try:
        original_message = await webhook.fetch_message(
            '@original',
            ignore_cache=True)
    except NotFound:
        raise InteractionError(
            'original message not found; message may have been deleted')

    try:
        edited_content = sub(
            escape(expression), replacement, original_message.content, count=count, flags=flags)
    except RegexError:
        raise InteractionError('invalid regular expression')

    embed = (
        Embed.success('message edited')
        if edited_content != original_message.content else
        Embed.warning('no changes were made')
    )

    embed.set_footer(text=f'message id: {original_message.id}')

    gather(
        webhook.edit_message(
            '@original',
            content=edited_content),
        interaction.response.send_message(embeds=[embed])
    )

    return True


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
    contexts=InteractionContextType.ALL(),
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

    if message and await _sed_edit(interaction, message):
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
            channel_id=sent_message.channel_id,
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

    await sender(
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
    contexts=InteractionContextType.ALL(),
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
            ).with_extra(
                False
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
        channel_id=sent_message.channel_id,
        token=interaction.token
    ).save()


@message_command(
    name='edit',
    scope=ApplicationCommandScope.USERPROXY,
    contexts=InteractionContextType.ALL(),
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
                    f'you can add /plu/ral by clicking [here](https://discord.com/oauth2/authorize?client_id={project.application_id})',
                    'once you have added /plu/ral, you can run /member userproxy sync to remove this command'
                ])
            )
        ]
    )

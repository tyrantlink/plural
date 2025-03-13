from typing import Any

from regex import (
    error as RegexError,  # noqa: N812
    IGNORECASE,
    compile,
    escape,
    sub
)

from beanie import PydanticObjectId
from datetime import timedelta
from asyncio import gather

from plural.db.enums import GroupSharePermissionLevel, ReplyFormat
from plural.db import Group, ProxyMember, Usergroup, redis, Reply
from plural.errors import InteractionError, PluralException
from plural.missing import MISSING
from plural.otel import span, cx

from src.core.avatar import upload_avatar, delete_avatar as _delete_avatar
from src.core.http import GENERAL_SESSION

from src.discord import (
    AllowedMentions,
    InteractionType,
    Interaction,
    Message,
    Webhook,
    Embed
)

SED = compile(r'^s/(.*?)/(.*?)(?:/([gi]+))?$')
INLINE_REPLY = compile(
    r'^-# \[↪\]\(<https:\/\/discord\.com\/channels\/\d+\/\d+\/\d+>\)')
MAX_SAFE_INTEGER = 2**53 - 1


def timestring_to_timedelta(time: str) -> timedelta:
    delta = timedelta()
    number = ''

    for character in time:
        match character:
            case 'd':
                delta += timedelta(days=int(number))
                number = ''
            case 'h':
                delta += timedelta(hours=int(number))
                number = ''
            case 'm':
                delta += timedelta(minutes=int(number))
                number = ''
            case 's':
                delta += timedelta(seconds=int(number))
                number = ''
            case ' ':
                pass
            case _ if character.isdigit():
                number += character
            case _:
                raise InteractionError(
                    f'invalid time format `{time}`'
                )

    return delta


async def sed_edit(
    interaction: Interaction,
    message: Message,
    sed: str,
    webhook: Webhook | None = None
) -> None:
    match = SED.match(sed)

    if match is None:
        raise InteractionError('invalid sed format')

    expression, replacement, _raw_flags = match.groups()

    flags = 0
    count = 1

    for flag in (_raw_flags or ''):
        match flag:
            case 'g':
                count = 0
            case 'i':
                flags |= IGNORECASE
            case _:
                raise RuntimeError(
                    f'invalid sed flag {flag} provided'
                    ' but regex pattern still matched'
                )

    try:
        edited_content = sub(
            escape(expression), replacement, message.content, count=count, flags=flags)
    except RegexError as e:
        raise InteractionError(
            'invalid regular expression'
        ) from e

    await edit_message(
        interaction,
        message,
        edited_content,
        webhook
    )


async def edit_message(
    interaction: Interaction,
    message: Message,
    content: str,
    webhook: Webhook | None = None
) -> None:
    if message.interaction_metadata:
        await _edit_userproxy_message(
            interaction,
            message,
            content,
            webhook)
    elif message.webhook_id:
        await _edit_webhook_message(
            interaction,
            message,
            content
        )
    else:
        await _edit_guild_userproxy_message(
            interaction,
            message,
            content
        )

    await redis.json().delete(
        f'discord:pending_edit:{message.id}', '$'
    )


async def _edit_response(
    interaction: Interaction,
    message: Message,
    content: str
) -> None:
    if interaction.type in {
        InteractionType.MESSAGE_COMPONENT,
        InteractionType.MODAL_SUBMIT
    }:
        await interaction.response.ack()
        return

    embed = (
        Embed.success('Message Edited')
        if content != message.content
        else Embed.warning('No Changes Made')
    )

    await interaction.response.send_message(
        embeds=[embed]
    )


async def _edit_guild_userproxy_message(
    interaction: Interaction,
    message: Message,
    content: str
) -> None:
    userproxy = await ProxyMember.find_one({
        'userproxy.bot_id': message.author.id
    })

    if userproxy is None:
        raise InteractionError('userproxy not found')

    await gather(
        _edit_response(interaction, message, content),
        message.edit(
            content,
            userproxy.userproxy.token
        )
    )


async def _edit_webhook_message(
    interaction: Interaction,
    message: Message,
    content: str
) -> None:
    channel_id = message.channel_id

    channel = await redis.json().get(f'discord:channel:{channel_id}')

    thread_id = MISSING

    if channel is None:
        raise ValueError('Channel not found in cache.')

    if channel['data'].get('type') in {11, 12}:
        thread_id = int(channel['data']['id'])

        channel = await redis.json().get(
            f'discord:channel:{channel['data']['parent_id']}'
        )

        if channel is None:
            raise ValueError('Parent channel not found in cache.')

    webhook = next((
        webhook
        for webhook in (
            (await redis.json().get(
                f'discord:webhooks:{channel['data']['id']}'
            )) or [])
        if webhook['id'] == str(message.webhook_id)
    ), None)

    if webhook is None:
        raise InteractionError('webhook not found')

    webhook = Webhook.model_validate(webhook)

    await gather(
        _edit_response(interaction, message, content),
        webhook.edit_message(
            message_id=message.id,
            content=content,
            thread_id=thread_id
        )
    )


async def _edit_userproxy_message(
    interaction: Interaction,
    message: Message,
    content: str,
    webhook: Webhook
) -> None:
    await webhook.edit_message(
        message_id=message.id,
        content=content
    )

    await _edit_response(interaction, message, content)


def group_edit_check(
    group: Group,
    user_id: int,
    group_error: bool = False
) -> None:
    if (
        (permission := group.users.get(user_id)) is not None and
        permission in {GroupSharePermissionLevel.PROXY_ONLY}
    ):
        raise InteractionError(
            f'Group `{group.name}` is shared with you with proxy-only permissions'
            if group_error else
            'This member is shared with you with proxy-only permissions'
        )


async def set_avatar(
    self: Group | ProxyMember,
    url: str,
    user_id: int,
    proxy_tag: int | None = None
) -> None:
    usergroup = await Usergroup.get_by_user(user_id)
    avatar_count = await usergroup.get_avatar_count(user_id)

    if avatar_count >= usergroup.data.image_limit:
        # ? technically potential bug here if you're near the limit
        # ? since only unique avatars are counted towards the total
        # ? so if you try to upload a duplicate avatar this will still raise
        # ? but the user would still be within their limit if the avatar was uploaded
        # ? but i don't wanna deal with that right now
        raise InteractionError(
            f'You have reached your avatar limit ({avatar_count}/{usergroup.data.image_limit})'
            '\n\nPlease delete an avatar before adding a new one'
        )

    if (
        self.avatar
        if proxy_tag is None else
        self.proxy_tags[proxy_tag].avatar
    ):
        await delete_avatar(self, proxy_tag)

    if proxy_tag is not None and not isinstance(self, ProxyMember):
        raise PluralException('Proxy tag can only be set on ProxyMember')

    parent_id = str(
        self.proxy_tags[proxy_tag].id
        if proxy_tag is not None else
        self.id
    )

    with span(
        'uploading avatar',
        attributes={(
            'proxy_tag'
            if proxy_tag is not None else
            'group'
            if isinstance(self, Group) else
            'member'
        ) + '.id': parent_id}
    ):
        avatar = await upload_avatar(
            parent_id,
            url,
            GENERAL_SESSION
        )

        cx().set_attribute('avatar.hash', avatar)

        if proxy_tag is not None:
            self.proxy_tags[proxy_tag].avatar = avatar
        else:
            self.avatar = avatar

        await self.save()


async def delete_avatar(
    self: Group | ProxyMember,
    proxy_tag: int | None = None
) -> None:
    hash, id = (
        (self.proxy_tags[proxy_tag].avatar, self.proxy_tags[proxy_tag].id)
        if proxy_tag is not None else
        (self.avatar, self.id)
    )

    with span(
        'deleting avatar',
        attributes={
            'avatar.hash': hash, (
                'proxy_tag'
                if proxy_tag is not None else
                'group'
                if isinstance(self, Group) else
                'member'
            ) + '.id': str(id),
        }
    ):
        if hash is None:
            raise InteractionError('No avatar to delete')

        await _delete_avatar(str(id), hash, GENERAL_SESSION)

        if proxy_tag is not None:
            self.proxy_tags[proxy_tag].avatar = None
        else:
            self.avatar = None

        await self.save()


# ? probably deduplicate this code
async def delete_avatars(
    avatars: list[tuple[Group | ProxyMember, int | None]],
    save: bool = True
) -> None:
    tasks = []

    for self, proxy_tag in avatars:
        hash, id = (
            (self.proxy_tags[proxy_tag].avatar, self.proxy_tags[proxy_tag].id)
            if proxy_tag is not None else
            (self.avatar, self.id)
        )

        if hash is None:
            raise InteractionError('No avatar to delete')

        tasks.append(_delete_avatar(str(id), hash, GENERAL_SESSION))

        if proxy_tag is not None:
            self.proxy_tags[proxy_tag].avatar = None
        else:
            self.avatar = None

        if save:
            tasks.append(self.save())

    with span(f'deleting {len(avatars)} avatars'):
        await gather(*tasks)


def make_json_safe(  # ? yay recursion
    obj: Any  # noqa: ANN401
) -> Any:  # noqa: ANN401
    match obj:
        case dict():
            return {
                key: make_json_safe(value)
                for key, value in obj.items()}
        case list():
            return [
                make_json_safe(value)
                for value in obj]
        case set():
            return make_json_safe(list(obj))
        case PydanticObjectId():
            return str(obj)
        case int() if obj > MAX_SAFE_INTEGER:
            return str(obj)
        case _:
            return obj


def handle_discord_markdown(text: str) -> str:
    markdown_patterns = {
        '*':   r'\*([^*]+)\*',
        '_':   r'_([^_]+)_',
        '**':  r'\*\*([^*]+)\*\*',
        '__':  r'__([^_]+)__',
        '~~':  r'~~([^~]+)~~',
        '`':   r'`([^`]+)`',
        '```': r'```[\s\S]+?```'
    }

    for pattern in markdown_patterns.values():
        text = sub(pattern, r'\1', text)

    for char in [
        '*', '_',
        '~', '`'
    ]:
        text = sub(
            r'(?<!\\)' + escape(char),
            r'\\' + char,
            text
        )

    return text


def format_reply(
    proxy_content: str,
    reference: Message | Reply,
    format: ReplyFormat,
    guild_id: int | None = None
) -> tuple[str | Embed | None, set[int]]:
    if format == ReplyFormat.NONE:
        return None, set()

    content = reference.content

    match reference:
        case Message():
            reference_id = reference.id
            channel_id = reference.channel_id

        case Reply():
            reference_id = reference.message_id
            channel_id = reference.channel

    jump_url = (
        'https://discord.com/channels'
        f'/{guild_id or '@me'}'
        f'/{channel_id}'
        f'/{reference_id}'
    )

    display_name = (
        reference.author.global_name or
        reference.author.username
    )

    match format:
        case ReplyFormat.INLINE:
            mention = (
                f'`@{display_name}`'
                if reference.webhook_id else
                f'<@{reference.author.id}>'
            )

            if INLINE_REPLY.match(content):
                content = '\n'.join(
                    content.split('\n')[1:]
                )

            content = content.replace('\n', ' ')

            # ? add zero-width space to prevent link previews
            content = handle_discord_markdown(
                content
                if len(content) <= 75 else
                f'{content[:75].strip()}…'
            ).replace('://', ':/​/')

            content = (
                content
                if content else
                f'[*Click to see attachment*](<{jump_url}>)'
                if reference.attachments else
                f'[*Click to see message*](<{jump_url}>)'
            )

            proxy_content = (
                f'-# [↪](<{jump_url}>) {mention} {content}'
                f'\n{proxy_content}'
            )

            if len(proxy_content) > 2000:
                return format_reply(
                    '',
                    reference,
                    ReplyFormat.EMBED
                )

            return (
                proxy_content,
                AllowedMentions.parse_content(content).users or set())
        case ReplyFormat.EMBED:
            content = (
                content
                if len(content) <= 75 else
                f'{content[:75].strip()}…'
            )

            return Embed(
                color=0x7289da,
                description=(
                    f'{'✉️ ' if reference.attachments else ''}'
                    f'**[Reply to:]({jump_url})** {content}'
                    if content.strip() else
                    f'*[click to see attachment{'' if len(reference.attachments)-1 else 's'}]({jump_url})*'
                    if reference.attachments else
                    f'*[click to see message]({jump_url})*')
            ).set_author(
                name=f'{display_name} ↩️',
                icon_url=reference.author.avatar_url
            ), set()

    return None, set()

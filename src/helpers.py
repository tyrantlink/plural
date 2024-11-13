# from discord import Interaction, ApplicationContext, Embed, Colour, Message, HTTPException, Forbidden
from discord.ui import Modal as _Modal, InputText, View as _View, Item
# from discord.utils import _bytes_to_base64_data, escape_markdown
from aiohttp import ClientSession, ClientResponse
from src.models import project, USERPROXY_FOOTER
from asyncio import sleep, create_task, Task
from hikari import Message as HikariMessage
from collections.abc import Mapping
from typing import Iterable, Any
from functools import partial
from json import dumps, loads
from copy import deepcopy
from src.db import Image
from uuid import uuid4
from io import BytesIO
from re import match
from fastapi import HTTPException


# ? completely unsorted and unformatted helper functions because i'm bad at programming
USERPROXY_COMMANDS = [
    {
        'name': 'proxy',
        'type': 1,
        'description': 'send a message',
        'options': [
            {
                'name': 'message',
                'description': 'message to send',
                'max_length': 2000,
                'type': 3,
                'required': False
            },
            {
                'name': 'attachment',
                'description': 'attachment to send',
                'type': 11,
                'required': False
            },
            {
                'name': 'queue_for_reply',
                'description': 'queue for reply message command (stores message until reply is used or 5 minutes pass)',
                'type': 5,
                'default': False,
                'required': False
            }
        ],
        'integration_types': [1],
        'contexts': [0, 1, 2]
    },
    {
        'name': 'reply',
        'type': 3,
        'integration_types': [1],
        'contexts': [0, 1, 2]
    },
    {
        'name': 'edit',
        'type': 3,
        'integration_types': [1],
        'contexts': [0, 1, 2]
    }
]


def chunk_string(string: str, chunk_size: int) -> list[str]:
    lines = string.split('\n')

    for i, _ in enumerate(lines):
        if len(lines[i]) > chunk_size:
            raise ValueError(
                f'line {i} is too long ({len(lines[i])}/{chunk_size})')

    chunks = []
    chunk = ''
    for line in lines:
        if len(chunk) + len(line) > chunk_size:
            chunks.append(chunk)
            chunk = ''

        chunk += f'{'\n' if chunk else ''}{line}'

    if chunk:
        chunks.append(chunk)

    return chunks


# def format_reply(
#     content: str,
#     reference: Message | HikariMessage,
#     guild_id: int | None = None
# ) -> str | ReplyEmbed:
#     refcontent = reference.content or ''
#     refattachments = reference.attachments
#     mention = (
#         reference.author.mention
#         if reference.webhook_id is None else
#         f'`@{reference.author.display_name}`'
#     )
#     jump_url = (
#         reference.jump_url
#         if isinstance(reference, Message) else
#         reference.make_link(guild_id)
#     )

#     base_reply = f'-# [↪](<{jump_url}>) {mention}'

#     if (
#         match(
#             r'^-# \[↪\]\(<https:\/\/discord\.com\/channels\/\d+\/\d+\/\d+>\)',
#             refcontent
#         )
#     ):
#         refcontent = '\n'.join(refcontent.split('\n')[1:])

#     refcontent = escape_markdown(refcontent.replace('\n', ' '))

#     formatted_refcontent = (
#         refcontent
#         if len(refcontent) <= 75 else
#         f'{refcontent[:75].strip()}…'
#     ).replace('://', ':/​/')  # ? add zero-width space to prevent link previews

#     reply_content = (
#         formatted_refcontent
#         if formatted_refcontent else
#         f'[*Click to see attachment*](<{jump_url}>)'
#         if refattachments else
#         f'[*Click to see message*](<{jump_url}>)'
#     )

#     total_content = f'{base_reply} {reply_content}\n{content}'
#     if len(total_content) <= 2000:
#         return total_content

#     return ReplyEmbed(reference, jump_url)


def merge_dicts(*dicts: Mapping) -> dict:
    """priority is first to last"""
    out: dict[Any, Any] = {}

    for d in reversed(dicts):
        for k, v in d.items():
            if isinstance(v, Mapping):
                out[k] = merge_dicts(out.get(k, {}), v)
            else:
                out[k] = v
    return out


def create_multipart(
    json_payload: dict,
    files: list[bytes]
) -> tuple[str, bytes]:  # boundary, body
    boundary = uuid4().hex

    body = BytesIO()

    body.write(f'--{boundary}\r\n'.encode('latin-1'))
    body.write(
        f'Content-Disposition: form-data; name="payload_json"\r\n'.encode('latin-1'))
    body.write('Content-Type: application/json\r\n\n'.encode('latin-1'))
    body.write(f'{dumps(json_payload)}\r\n'.encode('latin-1'))

    for index, file in enumerate(files):
        message = json_payload.get('data', None) or json_payload
        filename = message['attachments'][0]['filename']
        content_type = message['attachments'][0]['content_type']

        body.write(f'--{boundary}\r\n'.encode('latin-1'))
        body.write(
            f'Content-Disposition: form-data; name="files[{index}]"; filename="{filename}"\r\n'.encode('latin-1'))
        body.write(
            f'Content-Type: {content_type}\r\n\n'.encode('latin-1'))
        body.write(file)
        body.write('\r\n'.encode('latin-1'))

    body.write(f'--{boundary}--\r\n'.encode('latin-1'))

    return boundary, body.getvalue()


# async def multi_request(
#     token: str,
#     requests: list[tuple[str, str, dict[Any, Any]]]
# ) -> list[tuple[ClientResponse, str]]:
#     """requests is a list of tuples of method, endpoint, json"""
#     responses: list[tuple[ClientResponse, str]] = []
#     async with ClientSession() as session:
#         for method, endpoint, json in requests:
#             resp = await session.request(
#                 method,
#                 f'https://discord.com/api/v10/{endpoint}',
#                 headers={
#                     'Authorization': f'Bot {token}'
#                 },
#                 json=json
#             )

#             if resp.status not in {200, 201}:
#                 raise HTTPException(resp, await resp.text())

#             responses.append((resp, await resp.text()))

#     return responses


# def prettify_discord_errors(errors: list[str]) -> ErrorEmbed:
#     embed = ErrorEmbed(None)
#     for raw_error in errors:
#         try:  # ? this is really gross
#             json_error: dict[
#                 str, dict[str, dict[str, list[dict[str, str]]]]] = loads(raw_error)

#             error_detail = list(
#                 list(
#                     json_error['errors'].values()
#                 )[0].values())[0][0]

#             code, error = error_detail['code'], error_detail['message']

#             embed.add_field(name=code, value=error)
#         except Exception:
#             embed.add_field(name='unknown error', value=raw_error)

#     return embed


# async def sync_userproxy_with_member(
#     ctx: ApplicationContext,
#     userproxy: UserProxy,
#     bot_token: str,
#     sync_commands: bool = False
# ) -> None:
#     assert ctx.interaction.user is not None
#     member = await userproxy.get_member()

#     image_data = None

#     if member.avatar:
#         image = await Image.get(member.avatar)
#         if image is not None:
#             image_data = _bytes_to_base64_data(image.data)

#     # ? remember to add user descriptions to userproxy
#     bot_patch = {
#         'username': member.name
#     }

#     app_patch = {
#         'interactions_endpoint_url': f'{project.api_url}/userproxy/interaction',
#         'description': f'{member.description or ''}\n\n{USERPROXY_FOOTER.format(username=ctx.interaction.user.name)}'.strip()
#     }

#     if image_data:
#         bot_patch['avatar'] = image_data
#         app_patch['icon'] = image_data

#     requests: list[tuple[str, str, dict]] = [
#         ('patch', 'users/@me', bot_patch),
#         # ? effectively a get, to get public key
#         ('patch', 'applications/@me', {})
#     ]

#     if sync_commands:
#         commands = USERPROXY_COMMANDS
#         if userproxy.command is not None:
#             commands = deepcopy(USERPROXY_COMMANDS)
#             commands[0]['name'] = userproxy.command

#         requests.insert(
#             0,
#             (
#                 'put',
#                 f'applications/{userproxy.bot_id}/commands',
#                 commands  # type: ignore # ? i don't wanna deal with mypy
#             )
#         )

#     responses = await multi_request(
#         bot_token,
#         requests
#     )

#     errors = [
#         text
#         for resp, text in responses
#         if resp.status != 200
#     ]

#     if errors:
#         await _send_embed(ctx, prettify_discord_errors(errors))
#         return

#     public_key = (loads(responses[-1][1]))['verify_key']

#     userproxy.public_key = public_key

#     await userproxy.save()

#     app_request = await multi_request(
#         bot_token,
#         [
#             ('patch', f'applications/@me', app_patch)
#         ]
#     )

#     errors = [
#         text
#         for resp, text in app_request
#         if resp.status != 200
#     ]

#     if errors:
#         await _send_embed(ctx, prettify_discord_errors(errors))
#         return

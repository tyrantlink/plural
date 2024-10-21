from __future__ import annotations
from ..enums import InteractionCallbackType, MessageFlags
from aiohttp import ClientSession, ClientResponse
from ..component import TextInput, ActionRow
from src.helpers import create_multipart
from ..attachment import Attachment
from src.db import UserProxyMessage
from pydantic import BaseModel
from ..embed import Embed

session = ClientSession()
CALLBACK = 'https://discord.com/api/v10/interactions/{id}/{token}/callback'
FOLLOWUP = 'https://discord.com/api/v10/webhooks/{application_id}/{token}'


class InteractionResponse(BaseModel):
    id: str
    application_id: str
    token: str

    @property
    def _callback_url(self) -> str:
        return CALLBACK.format(id=self.id, token=self.token)

    @property
    def _followup_url(self) -> str:
        return FOLLOWUP.format(application_id=self.application_id, token=self.token)

    async def _request(
        self,
        method: str,
        url: str,
        json: dict,
    ) -> ClientResponse:
        return await session.request(
            method,
            url,
            json=json
        )

    async def _save_original_message_to_db(self) -> None:
        resp = await session.get(
            f'{self._followup_url}/messages/@original'
        )

        if resp.status != 200:
            raise Exception(f'Failed to fetch original message | {await resp.text()}')

        message_id = int((await resp.json())['id'])

        await UserProxyMessage(
            message_id=message_id,
            token=self.token
        ).save()

    async def pong(self) -> None:
        await self._request(
            'POST',
            self._callback_url,
            {'type': InteractionCallbackType.PONG.value}
        )

    async def send_message(
        self,
        content: str | None = None,
        *,
        embed: Embed | None = None,
        tts: bool = False,
        ephemeral: bool = True,
        attachment: Attachment | None = None,
    ) -> None:
        data = {}

        if content:
            data['content'] = content

        if tts:
            data['tts'] = tts

        if ephemeral:
            data['flags'] = MessageFlags.EPHEMERAL.value

        if embed:
            data['embeds'] = [embed.model_dump(mode='json')]

        if not attachment:
            await self._request(
                'POST',
                self._callback_url,
                {
                    'type': InteractionCallbackType.CHANNEL_MESSAGE_WITH_SOURCE.value,
                    'data': data
                }
            )
            return await self._save_original_message_to_db()

        data['attachments'] = [
            {
                'id': 0,
                'filename': attachment.filename,
                'content_type': attachment.content_type,
                'description': attachment.description,
                'title': attachment.title
            }
        ]

        url = attachment.proxy_url or attachment.url
        assert url is not None

        boundary, body = create_multipart(
            {
                'type': InteractionCallbackType.CHANNEL_MESSAGE_WITH_SOURCE.value,
                'data': data
            },
            [
                await (await session.get(url)).read()
            ]
        )

        await session.post(
            self._callback_url,
            data=body,
            headers={
                'Content-Type': f'multipart/form-data; boundary={boundary}'
            }
        )
        return await self._save_original_message_to_db()

    async def send_modal(
        self,
        title: str,
        custom_id: str,
        components: list[TextInput]
    ) -> None:
        await self._request(
            'POST',
            self._callback_url,
            {
                'type': InteractionCallbackType.MODAL.value,
                'data': {
                    'title': title,
                    'custom_id': custom_id,
                    'components': [
                        ActionRow(
                            components=components
                        ).model_dump(mode='json', exclude_none=True)
                    ],
                }
            }
        )

    async def edit_message(
        self,
        message_id: int,
        content: str
    ) -> None:
        message = await UserProxyMessage.find_one({'message_id': message_id})

        if message is None:
            await self.send_message('message not found\ndue to discord limitations, you can\'t edit messages that are older than 15 minutes')
            return

        followup = FOLLOWUP.format(
            application_id=self.application_id, token=message.token)

        resp = await self._request(
            'PATCH',
            f'{followup}/messages/{message_id}',
            {'content': content}
        )

        await self._request(
            'POST',
            self._callback_url,
            {
                'type': InteractionCallbackType.DEFERRED_UPDATE_MESSAGE.value
            }
        )

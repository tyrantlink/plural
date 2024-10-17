from discord import ApplicationContext, Option, SlashCommandGroup
from src.helpers import send_error, send_success, MemberConverter
from aiohttp import ClientSession, ClientResponse
import src.commands.autocomplete as autocomplete
from discord.utils import _bytes_to_base64_data
from src.commands.base import BaseCommands
from discord.errors import HTTPException
from src.db import Member, UserProxy
from src.models import project
from base64 import b64decode
from asyncio import gather

# ! /userproxy {new, delete, list}
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
                'required': True
            },
            {
                'name': 'queue_for_reply',
                'description': 'queue for reply message command (see /help)',
                'type': 5,
                'default': False,
                'required': False
            },
            {
                'name': 'attachment',
                'description': 'attachment to send',
                'type': 11,
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


class UserProxyCommands(BaseCommands):
    userproxy = SlashCommandGroup(
        name='userproxy',
        description='manage userproxies'
    )

    async def _multi_request(
        self,
        token: str,
        requests: list[tuple[str, str, dict]]
    ) -> list[ClientResponse]:
        responses: list[ClientResponse] = []
        async with ClientSession() as session:
            for method, endpoint, json in requests:
                resp = await session.request(
                    method,
                    f'https://discord.com/api/v10/{endpoint}',
                    headers={
                        'Authorization': f'Bot {token}'
                    },
                    json=json
                )

                if resp.status != 200:
                    raise HTTPException(resp, resp.reason)

                responses.append(resp)

        return responses

    @userproxy.command(
        name='help',
        description='information about userproxies')
    async def slash_userproxy_help(self, ctx: ApplicationContext) -> None:
        await send_error(ctx, 'not implemented yet')

    @userproxy.command(
        name='new',
        description='create a userproxy, use /userproxy help for more information',
        options=[
            Option(
                MemberConverter,
                name='member',
                description='member to create a userproxy for',
                autocomplete=autocomplete.members),
            Option(
                str,
                name='bot_token',
                description='bot token to use for the userproxy')])
    async def slash_userproxy_new(
        self,
        ctx: ApplicationContext,
        member: Member,
        bot_token: str
    ) -> None:
        assert ctx.interaction.user is not None

        await ctx.response.defer(ephemeral=True)

        #! remember to add validation here
        bot_id = int(b64decode(f'{bot_token.split('.')[0]}==').decode('utf-8'))

        userproxy = await self.client.db.userproxy(bot_id, member.id)

        if userproxy is not None:
            await send_error(ctx, 'userproxy already exists')
            return

        image_data = None

        if member.avatar:
            image = await self.client.db.image(member.avatar, True)
            if image is not None:
                image_data = _bytes_to_base64_data(image.data)

        # ? remember to add user descriptions to userproxy
        bot_patch = {
            'username': member.name,
            'description': f'userproxy for tyrantlink powered by /plu/ral\nhttps://github.com/tyrantlink/plural'
        }

        app_patch = {
            # 'interactions_endpoint_url': f'{project.api_url}/userproxy/interactions'
        }

        if image_data:
            bot_patch['avatar'] = image_data
            app_patch['icon'] = image_data

        responses = await self._multi_request(
            bot_token,
            [
                *[
                    (
                        'post',
                        f'applications/{bot_id}/commands',
                        command
                    )
                    for command in []
                ],
                # ('patch', 'users/@me', bot_patch),
                ('patch', 'applications/@me', app_patch)
            ]
        )

        public_key = (await responses[-1].json())['verify_key']

        await self.client.db.new.userproxy(
            bot_id=bot_id,
            user_id=ctx.interaction.user.id,
            member=member.id,
            public_key=public_key
        ).save()

        await send_success(ctx, 'userproxy created successfully')

    @userproxy.command(
        name='list',
        description='list all userproxies')
    async def slash_userproxy_list(self, ctx: ApplicationContext) -> None:
        assert ctx.interaction.user is not None

        userproxies = await self.client.db.userproxies(ctx.interaction.user.id)
        response = []
        for userproxy in userproxies:
            member = await self.client.db.member(userproxy.member)

            if member is None:
                continue

            response.append(f'{member.name} (<@{userproxy.bot_id}>)')

        await send_success(ctx, '\n'.join(response) or 'no userproxies created')

    @userproxy.command(
        name='delete',
        description='delete a userproxy',
        options=[
            Option(
                MemberConverter,
                name='member',
                description='member to delete the userproxy for',
                autocomplete=autocomplete.members)])
    async def slash_userproxy_delete(
        self,
        ctx: ApplicationContext,
        member: Member
    ) -> None:
        assert ctx.interaction.user is not None

        userproxy = await UserProxy.find_one({
            'user_id': ctx.interaction.user.id,
            'member': member.id
        })

        if userproxy is None:
            await send_error(ctx, 'userproxy does not exist')
            return

        await gather(
            userproxy.delete(),
            send_success(ctx, 'userproxy deleted successfully')
        )

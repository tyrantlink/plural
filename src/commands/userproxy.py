from src.helpers import send_error, send_success, sync_userproxy_with_member
from discord import ApplicationContext, Option, SlashCommandGroup
from src.converters import MemberConverter, UserProxyConverter
import src.commands.autocomplete as autocomplete
from src.commands.base import BaseCommands
from src.db import Member, UserProxy
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
                'required': False
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

    def _get_bot_id(self, token: str) -> int:
        #! do validation here too
        return int(b64decode(f'{token.split(".")[0]}==').decode('utf-8'))

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
                description='bot token to use for the userproxy'),
            Option(
                bool,
                name='autosync',
                description='REQUIRES STORING BOT TOKEN; sync the userproxy with the bot',
                default=False,
                required=False)])
    async def slash_userproxy_new(
        self,
        ctx: ApplicationContext,
        member: Member,
        bot_token: str,
        autosync: bool
    ) -> None:
        assert ctx.interaction.user is not None

        await ctx.response.defer(ephemeral=True)

        bot_id = self._get_bot_id(bot_token)

        userproxy = await self.client.db.userproxy(bot_id, member.id)

        if userproxy is not None:
            await send_error(ctx, 'userproxy already exists')
            return

        userproxy = UserProxy(
            bot_id=bot_id,
            user_id=ctx.interaction.user.id,
            member=member.id,
            public_key='',  # ? set by _sync_userproxy_with_member
            token=bot_token if autosync else None
        )

        await sync_userproxy_with_member(ctx, userproxy, bot_token, True)

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
                UserProxyConverter,
                name='userproxy',
                description='userproxy to delete',
                autocomplete=autocomplete.userproxies)])
    async def slash_userproxy_delete(
        self,
        ctx: ApplicationContext,
        userproxy: UserProxy
    ) -> None:
        await gather(
            userproxy.delete(),
            send_success(ctx, 'userproxy deleted successfully')
        )

    @userproxy.command(
        name='sync',
        description='sync userproxy with bot',
        options=[
            Option(
                UserProxyConverter,
                name='userproxy',
                description='userproxy to sync with attached member',
                autocomplete=autocomplete.userproxies),
            Option(
                str,
                name='bot_token',
                description='bot token to use to sync the userproxy')])
    async def slash_userproxy_sync(
        self,
        ctx: ApplicationContext,
        userproxy: UserProxy,
        bot_token: str
    ) -> None:
        await ctx.response.defer(ephemeral=True)

        await sync_userproxy_with_member(ctx, userproxy, bot_token, False)

        msg = 'userproxy synced successfully'

        if userproxy.autosync:
            msg += '\n\n**Warning:** userproxy is set to autosync, running /userproxy sync manually is usually unnecessary'

        await send_success(ctx, 'userproxy synced successfully')

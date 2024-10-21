from src.helpers import send_error, send_success, sync_userproxy_with_member
from discord import ApplicationContext, Option, SlashCommandGroup
from src.converters import MemberConverter, UserProxyConverter
import src.commands.autocomplete as autocomplete
from src.commands.base import BaseCommands
from src.db import Member, UserProxy
from re import match, IGNORECASE
from base64 import b64decode
from asyncio import gather


class UserProxyCommands(BaseCommands):
    userproxy = SlashCommandGroup(
        name='userproxy',
        description='manage userproxies'
    )

    def _get_bot_id(self, token: str) -> int:
        m = match(
            r'^(mfa\.[a-z0-9_-]{20,})|(([a-z0-9_-]{23,28})\.[a-z0-9_-]{6,7}\.(?:[a-z0-9_-]{27}|[a-z0-9_-]{38}))$',
            token,
            IGNORECASE
        )

        if m is None:
            raise ValueError('invalid token')

        return int(b64decode(f'{m.group(0)}==').decode('utf-8'))

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
                description='bot token to use to sync the userproxy',
                required=False),
            Option(
                bool,
                name='sync_commands',
                description='resync userproxy commands',
                default=False)])
    async def slash_userproxy_sync(
        self,
        ctx: ApplicationContext,
        userproxy: UserProxy,
        bot_token: str | None,
        sync_commands: bool
    ) -> None:
        await ctx.response.defer(ephemeral=True)

        if bot_token is None and userproxy.token is None:
            await send_error(ctx, 'you must provide a bot token if you did not store one when creating the userproxy')
            return

        token = bot_token or userproxy.token
        assert token is not None

        await sync_userproxy_with_member(ctx, userproxy, token, sync_commands)

        msg = 'userproxy synced successfully'

        if userproxy.autosync:
            msg += '\n\n**Warning:** userproxy is set to autosync, running /userproxy sync manually is usually unnecessary'

        await send_success(ctx, 'userproxy synced successfully')

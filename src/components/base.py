from src.discord import modal, TextInput, Interaction, TextInputStyle, Message, ButtonStyle, Embed
from src.db import ApiKey, Group, Message as DBMessage, Reply, UserProxyInteraction, Latch
from src.logic.proxy import get_proxy_webhook
from src.discord.components import button
from src.errors import InteractionError
from asyncio import gather

__all__ = (
    'modal_plural_edit',
    'button_api_key',
    'button_delete_all_data',
)


@modal(
    title='edit message',
    custom_id='modal_plural_edit',
    text_inputs=[
        TextInput(
            custom_id='new_message',
            style=TextInputStyle.LONG,
            max_length=2000,
            label='message',
            required=True)])
async def modal_plural_edit(
    interaction: Interaction,
    message: Message,
    new_message: str
) -> None:
    assert message.channel is not None

    if new_message == message.content:
        raise InteractionError('no changes were made')

    webhook = await get_proxy_webhook(message.channel)

    await gather(
        interaction.response.ack(),
        webhook.edit_message(
            message.id,
            content=new_message,
            thread_id=(
                message.channel.id
                if message.channel.is_thread else
                None
            )
        )
    )


@button(
    custom_id='button_api_key',
    label='reset token',
    style=ButtonStyle.RED)
async def button_api_key(
    interaction: Interaction
) -> None:
    assert interaction.user is not None

    api_key, token = ApiKey.new(interaction.user.id)

    embed = Embed(
        title='api token reset!',
        description='WARNING: this is the only time you will be able to see this token, make sure to save it somewhere safe!',
        color=0x69ff69)
    embed.add_field(name='token', value=f'`{token}`')

    await gather(
        api_key.save(),
        interaction.response.send_message(
            embeds=[embed]
        ))


@button(
    custom_id='button_delete_all_data',
    label='confirm',
    style=ButtonStyle.RED)
async def button_delete_all_data(
    interaction: Interaction
) -> None:
    assert interaction.user is not None

    await interaction.response.defer()

    images = []
    tasks = []
    userproxy_ids = set()

    groups = await Group.find({'accounts': interaction.user.id}).to_list()

    members = [
        member
        for group in groups
        for member in await group.get_members()
    ]

    for group in groups:
        if group.avatar:
            images.append(group.delete_avatar())

        tasks.append(group.delete())

    for member in members:
        if member.avatar:
            images.append(member.delete_avatar())

        if member.userproxy:
            userproxy_ids.add(member.userproxy.bot_id)

        tasks.append(member.delete())

    tasks.append(DBMessage.find({'author_id': interaction.user.id}).delete())

    tasks.append(Reply.find({'bot_id': {'$in': list(userproxy_ids)}}).delete())

    tasks.append(UserProxyInteraction.find(
        {'application_id': {'$in': list(userproxy_ids)}}).delete())

    tasks.append(Latch.find({'user': interaction.user.id}).delete())

    await gather(*images)

    await gather(
        *tasks,
        interaction.followup.send(
            embeds=[Embed.success('all data successfully deleted')]
        )
    )

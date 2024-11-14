from src.discord import modal, TextInput, Interaction, TextInputStyle, MessageFlag, Webhook, Embed, Message, Application
from src.logic.proxy import get_proxy_webhook
from src.errors import InteractionError
from src.models import USERPROXY_FOOTER
from src.db import ProxyMember
from asyncio import gather


__all__ = ('modal_plural_member_bio',)


@modal(
    custom_id='modal_plural_member_bio',
    text_inputs=[
        TextInput(
            custom_id='bio',
            style=TextInputStyle.LONG,
            max_length=2000,
            label='bio',
            required=True)])
async def modal_plural_member_bio(
    interaction: Interaction,
    member: ProxyMember,
    include_attribution: bool,
    bio: str
) -> None:
    assert member.userproxy is not None

    app = await Application.fetch_current(member.userproxy.token)

    if app is None:
        raise InteractionError('userproxy application not found')

    if include_attribution:
        bio += USERPROXY_FOOTER.format(username=interaction.author_name)

    if bio == app.description:
        raise InteractionError('no changes were made')

    await gather(
        app.patch(
            token=member.userproxy.token,
            description=bio),
        interaction.response.send_message(
            embeds=[Embed.success(
                title=f'{app.name} bio updated',
                message=bio.removesuffix(USERPROXY_FOOTER),
            )],
        )
    )

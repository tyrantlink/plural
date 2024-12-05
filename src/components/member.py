from src.discord import modal, TextInput, Interaction, TextInputStyle, Embed, Application
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
            required=False)])
async def modal_plural_member_bio(
    interaction: Interaction,
    member: ProxyMember,
    include_attribution: bool,
    bio: str = ''
) -> None:
    assert member.userproxy is not None

    app = await Application.fetch_current(member.userproxy.token)

    if app is None:
        raise InteractionError('userproxy application not found')

    if include_attribution:
        bio += USERPROXY_FOOTER.format(username=interaction.author_name)

    bio = bio.strip()

    if bio == app.description:
        raise InteractionError('no changes were made')

    if len(bio) > 400:
        raise InteractionError(
            'bio over character limit, this shouldn\'t happen')

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

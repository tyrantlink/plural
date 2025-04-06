from asyncio import gather

from plural.db import ProxyMember

from src.core.models import (
    USERPROXY_FOOTER,
    LEGACY_FOOTERS
)

from src.discord import (
    TextInputStyle,
    Interaction,
    TextInput,
    Embed,
    modal
)


PAGES = {
    'bio': lambda interaction, member: _bio(interaction, member)
}


@modal(
    custom_id='modal_set_bio',
    title='Set Bio',
    text_inputs=[])
async def modal_proxy(
    interaction: Interaction,
    member: ProxyMember,
    bio: str = ''
) -> None:
    from src.commands.userproxy import _userproxy_sync

    member.bio = bio.strip()

    embeds = [Embed.success(
        title=f'Updated {member.name}\'s bio',
        message=member.bio
    )]

    if member.userproxy:
        embeds[0].set_footer(
            'Userproxy sync in progress...'
        )

    await gather(
        member.save(),
        interaction.response.send_message(
            embeds=embeds
        )
    )

    if member.userproxy:
        await _userproxy_sync(
            interaction,
            member,
            {'description'},
            silent=True
        )

    embeds[0].set_footer(
        'You may need to restart your client '
        'to see changes to userproxies'
    )

    await interaction.followup.edit_message(
        '@original',
        embeds=embeds
    )


async def _bio(
    interaction: Interaction,
    member: ProxyMember
) -> None:
    current_bio = member.bio
    for footer in [*LEGACY_FOOTERS, USERPROXY_FOOTER]:
        current_bio = current_bio.removesuffix(
            footer.format(
                username=interaction.author_name
            ).strip()
        ).strip()

    max_length = (
        400
        if member.userproxy else
        4000
    )

    await interaction.response.send_modal(
        modal_proxy.with_overrides(
            title=f'Set {member.name}\'s bio',
            text_inputs=[TextInput(
                custom_id='bio',
                style=TextInputStyle.PARAGRAPH,
                label='Bio',
                min_length=0,
                max_length=max_length,
                required=False,
                value=current_bio[:max_length])],
            extra=[member]
        )
    )

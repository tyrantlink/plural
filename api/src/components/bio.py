from asyncio import gather

from plural.errors import InteractionError
from plural.missing import MISSING
from plural.db import ProxyMember

from src.core.models import (
    USERPROXY_FOOTER_LIMIT,
    USERPROXY_FOOTER,
    LEGACY_FOOTERS
)

from src.discord import (
    TextInputStyle,
    Application,
    Interaction,
    TextInput,
    Embed,
    modal
)


PAGES = {
    'bio': lambda interaction, userproxy, include_attribution: _bio(interaction, userproxy, include_attribution)
}


@modal(
    custom_id='modal_set_bio',
    title='Set Bio',
    text_inputs=[])
async def modal_proxy(
    interaction: Interaction,
    userproxy: ProxyMember,
    include_attribution: bool,
    bio: str = ''
) -> None:
    app = await Application.fetch(
        userproxy.userproxy.token,
        False
    )

    if include_attribution:
        bio += USERPROXY_FOOTER.format(
            username=interaction.author_name
        )

    bio = bio.strip()

    if bio == app.description:
        raise InteractionError('no changes were made')

    if len(bio) > 400:
        raise InteractionError(
            'Bio over character limit (400), '
            'this shouldn\'t be possible'
        )

    await gather(
        app.patch(
            userproxy.userproxy.token,
            {'description': bio}),
        interaction.response.send_message(
            embeds=[Embed.success(
                title=f'Updated {app.bot.username}\'s bio',
                message=bio
            ).set_footer(
                'Note: you may need to refresh your '
                'Discord client to see changes'
            )]
        )
    )


async def _bio(
    interaction: Interaction,
    userproxy: ProxyMember,
    include_attribution: bool
) -> None:
    app = await Application.fetch(
        userproxy.userproxy.token,
        False
    )

    current_bio = app.description

    for footer in [*LEGACY_FOOTERS, USERPROXY_FOOTER]:
        current_bio = current_bio.removesuffix(
            footer.format(
                username=interaction.author_name
            ).strip()
        ).strip()

    max_length = (
        USERPROXY_FOOTER_LIMIT
        if include_attribution else
        400
    )

    await interaction.response.send_modal(
        modal_proxy.with_overrides(
            title=f'Set {app.bot.username}\'s bio',
            text_inputs=[TextInput(
                custom_id='bio',
                style=TextInputStyle.PARAGRAPH,
                label='Bio',
                min_length=1,
                max_length=max_length,
                required=True,
                value=(
                    current_bio[:max_length]
                    if current_bio
                    else MISSING
                ))],
            extra=[
                userproxy,
                include_attribution
            ]
        )
    )

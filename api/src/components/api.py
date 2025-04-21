from textwrap import dedent
from asyncio import gather

from beanie import PydanticObjectId

from plural.db.enums import ApplicationScope
from plural.errors import InteractionError
from plural.db import Application

from src.discord import (
    TextInputStyle,
    Interaction,
    TextInput,
    Embed,
    modal,
    button,
    ButtonStyle,
    ActionRow,
    string_select,
    SelectMenu,
    Emoji
)

from .pagination import PAGINATION_STYLE_MAP
from .base import _send_or_update

PAGES = {
    'api': lambda interaction: _api(interaction),
    'application': lambda interaction, application_id, token, action: _application(interaction, application_id, token, action),
}


@string_select(
    custom_id='select_application',
    options=[],  # ? this should be overwritten
    placeholder='Edit an application')
async def select_application(
    interaction: Interaction,
    selected: list[str]
) -> None:
    await PAGES['application'](
        interaction,
        PydanticObjectId(selected[0]),
        None,
        None
    )


@modal(
    custom_id='modal_set_name_description',
    title='New Application',
    text_inputs=[
        TextInput(
            custom_id='name',
            label='Name',
            max_length=32,
            required=True,
            style=TextInputStyle.SHORT),
        TextInput(
            custom_id='description',
            label='Description',
            max_length=4000,
            required=False,
            style=TextInputStyle.PARAGRAPH)])
async def modal_set_name_description(
    interaction: Interaction,
    application_id: str | None = None,
    name: str = '',
    description: str = ''
) -> None:
    if name == '':
        raise InteractionError('Name is required')

    if application_id is not None:
        application = await Application.get(
            PydanticObjectId(application_id)
        )

        if application is None:
            raise InteractionError('Application not found')

        application.name = name
        application.description = description

        await application.save()

        await PAGES['application'](
            interaction,
            application_id,
            None,
            None
        )
        return

    if await Application.find({
        'developer': interaction.author_id
    }).count() >= 25:
        raise InteractionError(
            'You have reached the maximum number of applications (25)'
        )

    application, token = Application.new(
        name,
        description,
        interaction.author_id,
        ApplicationScope.NONE,
    )

    await application.save()

    await PAGES['application'](
        interaction,
        application.id,
        token,
        None
    )


@button(
    custom_id='button_new_application',
    label='New Application',
    style=ButtonStyle.SUCCESS)
async def button_new_application(interaction: Interaction) -> None:
    if await Application.find({
        'developer': interaction.author_id
    }).count() >= 25:
        raise InteractionError(
            'You have reached the maximum number of applications (25)'
        )

    await interaction.response.send_modal(
        modal_set_name_description
    )


@string_select(
    custom_id='select_scopes',
    options=[
        SelectMenu.Option(
            label=scope.pretty_name,
            value=str(scope.value),
            description=scope.description)
        for scope in ApplicationScope
        if not scope.approval_required],
    placeholder='Select scopes',
    min_values=0,
    max_values=len([
        scope
        for scope in
        ApplicationScope
        if not scope.approval_required]))
async def select_scopes(
    interaction: Interaction,
    selected: list[str],
    application_id: str
) -> None:
    application = await Application.get(
        PydanticObjectId(application_id)
    )

    application.scope = ApplicationScope(sum(
        int(scope)
        for scope in
        selected
    ))

    await application.save()

    await PAGES['application'](
        interaction,
        application_id,
        None,
        None
    )


@button(
    custom_id='button_back_application',
    label='<-',
    style=ButtonStyle.SECONDARY)
async def button_back_application(
    interaction: Interaction
) -> None:
    await PAGES['api'](interaction)


@button(
    custom_id='button_set_name_description',
    label='Set Name & Description',
    style=ButtonStyle.PRIMARY)
async def button_set_name_description(
    interaction: Interaction,
    application_id: str
) -> None:
    application = await Application.get(
        PydanticObjectId(application_id)
    )

    if application is None:
        raise InteractionError('Application not found')

    await interaction.response.send_modal(
        modal_set_name_description.with_overrides(
            text_inputs=[
                TextInput(
                    custom_id='name',
                    label='Name',
                    max_length=32,
                    required=True,
                    style=TextInputStyle.SHORT,
                    value=application.name),
                TextInput(
                    custom_id='description',
                    label='Description',
                    max_length=4000,
                    required=False,
                    style=TextInputStyle.PARAGRAPH,
                    value=application.description)],
            extra=[application_id]
        )
    )


@button(
    custom_id='button_set_endpoint',
    label='Set Endpoint',
    style=ButtonStyle.PRIMARY)
async def button_set_endpoint(
    interaction: Interaction,  # noqa: ARG001
    application_id: str  # noqa: ARG001
) -> None:
    raise InteractionError('User events are not implemented yet')


@button(
    custom_id='button_reset_token',
    label='Reset Token',
    style=ButtonStyle.DANGER)
async def button_reset_token(
    interaction: Interaction,
    application_id: str
) -> None:
    application = await Application.get(
        PydanticObjectId(application_id)
    )

    if application is None:
        raise InteractionError('Application not found')

    if interaction.message.components[2].components[0].label != 'Confirm':
        await PAGES['application'](
            interaction,
            application_id,
            None,
            'reset'
        )
        return

    token = await application.update_token()

    await PAGES['application'](
        interaction,
        application_id,
        token,
        None
    )


@button(
    custom_id='button_delete_application',
    label='Delete',
    style=ButtonStyle.DANGER)
async def button_delete_application(
    interaction: Interaction,
    application_id: str
) -> None:
    application, usergroup = await gather(
        Application.get(
            PydanticObjectId(application_id)),
        interaction.get_usergroup()
    )

    if application is None:
        raise InteractionError('Application not found')

    if interaction.message.components[2].components[1].label != 'Confirm':
        await PAGES['application'](
            interaction,
            application_id,
            None,
            'delete'
        )
        return

    await application.delete()

    arrow = PAGINATION_STYLE_MAP[
        usergroup.config.pagination_style
    ][0]

    await _send_or_update(
        interaction,
        embed=Embed(
            title='Application Deleted',
            description='The application has been deleted',
            color=0xff6969),
        components=[
            ActionRow(components=[
                button_back_application.with_overrides(
                    label=arrow if isinstance(arrow, str) else '',
                    emoji=arrow if isinstance(arrow, Emoji) else None
                )
            ])
        ]
    )


async def _api(
    interaction: Interaction
) -> None:
    applications = await Application.find({
        'developer': interaction.author_id
    }).to_list()

    await _send_or_update(
        interaction,
        embed=Embed(
            title='API',
            description=dedent("""
                This command is intended for developers looking to integrate their bots/applications with /plu/ral.

                Create a new application to get an API key, or edit an existing one.

                [API Docs](https://api.plural.gg/docs)"""),
            color=0x69ff69),
        components=[
            ActionRow(components=[
                select_application.with_overrides(
                    placeholder=(
                        'Edit an application'
                        if applications else
                        'No applications found'),
                    options=[
                        SelectMenu.Option(
                            label=application.name,
                            value=str(application.id),
                            description=(
                                application.description[:100] or
                                'No description provided')
                        ) for application in applications[:25]
                    ] or [SelectMenu.Option(label='0', value='0')],
                    disabled=not applications)]),
            ActionRow(components=[
                button_new_application.with_overrides(
                    disabled=len(applications) >= 25
                )
            ])
        ]
    )


async def _application(
    interaction: Interaction,
    application_id: PydanticObjectId,
    token: str | None,
    action: str | None
) -> None:
    application, usergroup = await gather(
        Application.get(application_id),
        interaction.get_usergroup()
    )

    if application is None:
        raise InteractionError('Application not found')

    embed = Embed(
        title=application.name,
        description=application.description or 'No description provided',
        color=0x69ff69
    ).add_field(
        name='Scopes',
        value='\n'.join(
            scope.pretty_name
            for scope in
            ApplicationScope
            if scope & application.scope)
        or 'No scopes selected',
        inline=False
    ).add_field(
        name='Endpoint',
        value=application.endpoint or 'No event endpoint set',
        inline=False
    )

    if token is not None:
        embed.add_field(
            name='API Token',
            value=f'This will only be shown once.\n||{token}||',
            inline=False
        )

    arrow = PAGINATION_STYLE_MAP[
        usergroup.config.pagination_style
    ][0]

    await _send_or_update(
        interaction,
        embed=embed,
        components=[
            ActionRow(components=[
                select_scopes.with_overrides(
                    options=[
                        SelectMenu.Option(
                            label=scope.pretty_name,
                            value=str(scope.value),
                            description=scope.description,
                            default=scope in application.scope)
                        for scope in ApplicationScope
                        if not scope.approval_required],
                    extra=[str(application.id)])]),
            ActionRow(components=[
                button_back_application.with_overrides(
                    label=arrow if isinstance(arrow, str) else '',
                    emoji=arrow if isinstance(arrow, Emoji) else None),
                button_set_name_description.with_overrides(
                    extra=[str(application.id)]),
                button_set_endpoint.with_overrides(
                    disabled=not bool(ApplicationScope.USER_EVENTS &
                                      application.scope),
                    extra=[str(application.id)])]),
            ActionRow(components=[
                button_reset_token.with_overrides(
                    label='Confirm' if action == 'reset' else 'Reset Token',
                    extra=[str(application.id)]),
                button_delete_application.with_overrides(
                    label='Confirm' if action == 'delete' else 'Delete',
                    extra=[str(application.id)]
                )
            ])
        ]
    )


@button(
    custom_id='button_authorize',
    label='Authorize',
    style=ButtonStyle.PRIMARY)
async def button_authorize(
    interaction: Interaction,
    app_id: str,
    scope: str
) -> None:
    application = await Application.get(
        PydanticObjectId(app_id)
    )

    if application is None:
        raise InteractionError('Application not found')

    usergroup = await interaction.get_usergroup()

    set_scope = ApplicationScope(int(scope))

    usergroup.data.applications[app_id] = set_scope

    await gather(
        usergroup.save(),
        interaction.response.update_message(
            components=[],
            embeds=[
                Embed.success(
                    title='Authorization Granted',
                    message=(
                        f'You have granted {application.name} '
                        'access to your /plu/ral data.')
                ).add_field(
                    'Scopes',
                    '\n'.join(
                        scope.pretty_name
                        for scope in
                        ApplicationScope
                        if scope & set_scope)
                    or 'None'
                )
            ]
        )
    )


@button(
    custom_id='button_deny',
    label='Deny',
    style=ButtonStyle.DANGER)
async def button_deny(
    interaction: Interaction
) -> None:
    await gather(
        interaction.response.ack(),
        interaction.message.delete()
    )

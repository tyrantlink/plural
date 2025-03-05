from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.core.http import request, Route

from src.discord.models.base import RawBaseModel

if TYPE_CHECKING:
    from plural.missing import Optional, Nullable
    from src.discord.types import Snowflake

    from src.discord.enums import (
        ApplicationIntegrationType,
        EventWebhooksStatus,
        EventWebhooksType,
        MembershipState,
        ApplicationFlag,
        Permission
    )

    from .expression import Emoji
    from .guild import Guild
    from .user import User

__all__ = (
    'Application',
    'Team',
)


class Team(RawBaseModel):
    class Member(RawBaseModel):
        membership_state: MembershipState
        """User's membership state on the team"""
        team_id: Snowflake
        """ID of the parent team of which they are a member"""
        user: User
        """Avatar, discriminator, ID, and username of the user"""
        role: str
        """Role of the team member"""

    icon: Nullable[str]
    """Hash of the image of the team's icon"""
    id: Snowflake
    """Unique ID of the team"""
    members: list[Team.Member]
    """Members of the team"""
    name: str
    """Name of the team"""
    owner_user_id: Snowflake
    """User ID of the current team owner"""


class Application(RawBaseModel):
    class InstallParams(RawBaseModel):
        scopes: list[str]
        """Scopes to add the application to the server with"""
        permissions: Permission
        """Permissions to request for the bot role"""

    class IntegrationTypeConfiguration(RawBaseModel):
        oauth2_install_params: Optional[Application.InstallParams]
        """Install params for each installation context's default in-app authorization link"""

    id: Snowflake
    """ID of the app"""
    name: str
    """Name of the app"""
    icon: Nullable[str]
    """Icon hash of the app"""
    description: str
    """Description of the app"""
    rpc_origins: Optional[list[str]]
    """List of RPC origin URLs, if RPC is enabled"""
    bot_public: bool
    """When `false`, only the app owner can add the app to guilds"""
    bot_require_code_grant: bool
    """When `true`, the app's bot will only join upon completion of the full OAuth2 code grant flow"""
    bot: User
    """Partial user object for the bot user associated with the app"""
    terms_of_service_url: Optional[str]
    """URL of the app's Terms of Service"""
    privacy_policy_url: Optional[str]
    """URL of the app's Privacy Policy"""
    owner: User
    """Partial user object for the owner of the app"""
    verify_key: str
    """Hex encoded key for verification in interactions and the GameSDK's GetTicket"""
    team: Nullable[Team]
    """If the app belongs to a team, this will be a list of the members of that team"""
    guild_id: Optional[Snowflake]
    """Guild associated with the app. For example, a developer support server."""
    guild: Optional[Guild]
    """Partial object of the associated guild"""
    primary_sku_id: Optional[Snowflake]
    """If this app is a game sold on Discord, this field will be the id of the "Game SKU" that is created, if exists"""
    slug: Optional[str]
    """If this app is a game sold on Discord, this field will be the URL slug that links to the store page"""
    cover_image: Optional[str]
    """App's default rich presence invite cover image hash"""
    flags: Optional[ApplicationFlag]
    """App's public flags"""
    approximate_guild_count: Optional[int]
    """Approximate count of guilds the app has been added to"""
    approximate_user_install_count: Optional[int]
    """Approximate count of users that have installed the app"""
    redirect_uris: Optional[list[str]]
    """Array of redirect URIs for the app"""
    interactions_endpoint_url: Optional[Nullable[str]]
    """Interactions endpoint URL for the app"""
    role_connections_verification_url: Optional[Nullable[str]]
    """Role connection verification URL for the app"""
    event_webhooks_url: Optional[Nullable[str]]
    """Event webhooks URL for the app to receive webhook events"""
    event_webhooks_status: Optional[EventWebhooksStatus]
    """If webhook events are enabled for the app. `1` (default) means disabled, `2` means enabled, and `3` means disabled by Discord"""
    event_webhooks_types: Optional[list[EventWebhooksType]]
    """List of Webhook event types the app subscribes to"""
    tags: Optional[list[str]]
    """List of tags describing the content and functionality of the app. Max of 5 tags."""
    install_params: Optional[Application.InstallParams]
    """Settings for the app's default in-app authorization link, if enabled"""
    integration_types_config: Optional[dict[
        ApplicationIntegrationType,
        Application.IntegrationTypeConfiguration]]
    """Default scopes and permissions for each supported installation context. Value for each key is an integration type configuration object"""
    custom_install_url: Optional[str]
    """Default custom authorization URL for the app, if enabled"""

    @classmethod
    async def fetch(
        cls,
        token: str,
        silent: bool
    ) -> Application:
        return cls.model_validate(await request(Route(
            'GET',
            '/applications/{application_id}',
            token=token,
            silent=silent,
        )))

    @classmethod
    async def list_emojis(
        cls,
        token: str
    ) -> list[Emoji]:
        from .expression import Emoji

        return [
            Emoji.model_validate(data)
            for data in (
                await request(Route(
                    'GET',
                    '/applications/{application_id}/emojis',
                    token=token))
            ).get('items', [])
        ]

    async def patch(
        self,
        token: str,
        patch: dict[str, Any]
    ) -> Application:
        return self.model_validate(await request(
            Route(
                'PATCH',
                '/applications/{application_id}',
                token=token),
            json=patch
        ))

from __future__ import annotations
from src.discord.http import request, Route, _bytes_to_base64_data
from src.models import project, MISSING, MissingOr, MissingNoneOr
from src.discord.types import Snowflake  # noqa: TC001
from typing import TYPE_CHECKING
from .base import RawBaseModel


if TYPE_CHECKING:
    from .enums import ApplicationIntegrationType
    from .guild import Guild
    from .user import User


class Application(RawBaseModel):
    id: Snowflake
    name: str
    icon: str | None = None
    description: str
    rpc_origins: list[str] | None = None
    bot_public: bool
    bot_require_code_grant: bool
    bot: User | None = None
    terms_of_service_url: str | None = None
    privacy_policy_url: str | None = None
    owner: User | None = None
    verify_key: str
    team: dict | None = None  # ? i don't care enough to model this
    guild_id: Snowflake | None = None
    guild: Guild | None = None
    primary_sku_id: Snowflake | None = None
    slug: str | None = None
    cover_image: str | None = None
    flags: int | None = None  # ? i don't care enough to model this
    approximate_guild_count: int | None = None
    approximate_user_install_count: int | None = None
    redirect_uris: list[str] | None = None
    interactions_endpoint_url: str | None = None
    role_connections_verification_url: str | None = None
    event_webhooks_url: str | None = None
    event_webhooks_status: int | None = None  # ? i don't care enough to model this
    event_webhooks_types: list[str] | None = None
    tags: list[str] | None = None
    install_params: dict | None = None  # ? i don't care enough to model this
    integration_types_config: dict[
        ApplicationIntegrationType,
        dict
    ] | None = None
    custom_install_url: str | None = None

    @classmethod
    async def fetch_current(
        cls,
        token: str | None = project.bot_token
    ) -> Application:
        return cls(
            **await request(
                Route(
                    'GET',
                    '/applications/@me'),
                token=token
            )
        )

    async def patch(
        self,
        token: str | None = project.bot_token,
        *,
        custom_install_url: MissingOr[str] = MISSING,
        description: MissingOr[str] = MISSING,
        role_connections_verification_url: MissingOr[str] = MISSING,
        install_params: MissingOr[dict] = MISSING,
        integration_types_config: MissingOr[dict] = MISSING,
        flags: MissingOr[int] = MISSING,
        icon: MissingNoneOr[bytes] = MISSING,
        cover_image: MissingNoneOr[bytes] = MISSING,
        interactions_endpoint_url: MissingOr[str] = MISSING,
        tags: MissingOr[list[str]] = MISSING,
        event_webhooks_url: MissingOr[str] = MISSING,
        event_webhooks_status: MissingOr[int] = MISSING,
        event_webhooks_types: MissingOr[list[str]] = MISSING
    ) -> Application:
        json = {}

        if custom_install_url is not MISSING:
            json['custom_install_url'] = custom_install_url

        if description is not MISSING:
            json['description'] = description

        if role_connections_verification_url is not MISSING:
            json['role_connections_verification_url'] = role_connections_verification_url

        if install_params is not MISSING:
            json['install_params'] = install_params

        if integration_types_config is not MISSING:
            json['integration_types_config'] = integration_types_config

        if flags is not MISSING:
            json['flags'] = flags

        if icon is not MISSING:
            assert isinstance(icon, bytes)
            json['icon'] = _bytes_to_base64_data(icon)

        if cover_image is not MISSING:
            assert isinstance(cover_image, bytes)
            json['cover_image'] = _bytes_to_base64_data(cover_image)

        if interactions_endpoint_url is not MISSING:
            json['interactions_endpoint_url'] = interactions_endpoint_url

        if tags is not MISSING:
            json['tags'] = tags

        if event_webhooks_url is not MISSING:
            json['event_webhooks_url'] = event_webhooks_url

        if event_webhooks_status is not MISSING:
            json['event_webhooks_status'] = event_webhooks_status

        if event_webhooks_types is not MISSING:
            json['event_webhooks_types'] = event_webhooks_types

        return self.__class__(
            **await request(
                Route(
                    'PATCH',
                    '/applications/@me'),
                json=json,
                token=token
            )
        )

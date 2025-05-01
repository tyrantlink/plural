from __future__ import annotations

from typing import TYPE_CHECKING

from src.discord.models.base import RawBaseModel

if TYPE_CHECKING:
    from datetime import datetime

    from plural.missing import Optional

    from src.discord.types import Snowflake
    from src.discord.enums import (
        ApplicationIntegrationType,
        EventWebhooksType,
        WebhookEventType
    )

    from src.discord.models.entitlement import Entitlement
    from src.discord.models.guild import Guild
    from src.discord.models.user import User


class ApplicationAuthorizedEvent(RawBaseModel):
    integration_type: Optional[ApplicationIntegrationType]
    """Installation context for the authorization."""
    user: User
    """Installation context for the authorization."""
    scopes: list[str]
    """List of scopes the user authorized"""
    guild: Optional[Guild]
    """Server which app was authorized for (when integration type is `0`)"""


class WebhookEvent(RawBaseModel):
    class WebhookEventBody(RawBaseModel):
        type: EventWebhooksType
        """Event type"""
        timestamp: datetime
        """Timestamp of when the event occurred in ISO8601 format"""
        data: ApplicationAuthorizedEvent | Entitlement
        """Data for the event. The shape depends on the event type"""

    version: int
    """Version scheme for the webhook event. Currently always `1`"""
    application_id: Snowflake
    """ID of your app"""
    type: WebhookEventType
    """Type of webhook, either `0` for PING or `1` for webhook events"""
    event: Optional[WebhookEventBody]
    """Event data payload"""

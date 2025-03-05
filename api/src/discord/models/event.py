from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.discord.models.base import RawBaseModel

if TYPE_CHECKING:
    from datetime import datetime

    from plural.missing import Optional

    from src.discord.enums import WebhookEventType, EventWebhooksType
    from src.discord.types import Snowflake


class WebhookEvent(RawBaseModel):
    class WebhookEventBody(RawBaseModel):
        type: EventWebhooksType
        """Event type"""
        timestamp: datetime
        """Timestamp of when the event occurred in ISO8601 format"""
        data: dict[str, Any]
        """Data for the event. The shape depends on the event type"""

    version: int
    """Version scheme for the webhook event. Currently always `1`"""
    application_id: Snowflake
    """ID of your app"""
    type: WebhookEventType
    """Type of webhook, either `0` for PING or `1` for webhook events"""
    event: Optional[WebhookEventBody]
    """Event data payload"""

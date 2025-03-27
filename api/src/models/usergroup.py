from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from beanie import PydanticObjectId  # noqa: TC002

from plural.db.enums import (
    ApplicationScope,
    PaginationStyle,
    SupporterTier,
    ReplyFormat
)


if TYPE_CHECKING:
    from plural.db import Usergroup as DBUsergroup

    from src.core.auth import TokenData


class Usergroup(BaseModel):
    class Config(BaseModel):
        reply_format: ReplyFormat = Field(
            default=ReplyFormat.INLINE,
            description='Format for message references in servers')
        groups_in_autocomplete: bool = Field(
            default=True,
            description='Whether to show groups in member autocomplete')
        pagination_style: PaginationStyle = Field(
            default=PaginationStyle.BASIC_ARROWS,
            description='The style of pagination buttons to use')
        roll_embed: bool = Field(
            default=True,
            description='Whether to show for dice rolls')
        tag_format: str = Field(
            default='{tag}',
            description='The format for group tags in member names')
        pronoun_format: str = Field(
            default='({pronouns})',
            description='The format for pronouns in member names')
        display_name_order: list[int] = Field(
            default_factory=lambda: [0, 1, 2],
            description='The order of display name components'
        )

    class UserproxyConfig(BaseModel):
        reply_format: ReplyFormat = Field(
            default=ReplyFormat.INLINE,
            description='Format for message references in servers')
        dm_reply_format: ReplyFormat = Field(
            default=ReplyFormat.INLINE,
            description='Format for message references in dms')
        ping_replies: bool = Field(
            default=False,
            description='Whether to ping when you reply to someone')
        include_group_tag: bool = Field(
            default=False,
            description='Whether to include the group tag in the member name')
        include_pronouns: bool = Field(
            default=False,
            description='Whether to include the pronouns in the member name')
        attachment_count: int = Field(
            default=1,
            description='The number of attachment options to include in the proxy command')
        self_hosted: bool = Field(
            default=False,
            description='Whether the userproxy is self-hosted')
        required_message_parameter: bool = Field(
            default=False,
            description='Whether the proxy command requires the message parameter')
        name_in_reply_command: bool = Field(
            default=True,
            description='Whether the name should be included in the reply command')
        include_attribution: bool = Field(
            default=True,
            description='Whether to include attribution at the end of bio')

    class Data(BaseModel):
        supporter_tier: SupporterTier = Field(
            default=SupporterTier.NONE,
            description='The supporter tier of the user')
        image_limit: int = Field(
            default=1000,
            description='The maximum number of images a user can upload')
        sp_token: str | None = Field(
            None,
            description='The simply plural token of the user')
        sp_id: str | None = Field(
            None,
            description='The simply plural system id of the user'
        )
    id: PydanticObjectId = Field(
        description='Internal usergroup ID')
    users: list[int] = Field(
        description='List of user IDs in the usergroup')
    config: Config = Field(
        description='Usergroup config')
    userproxy_config: UserproxyConfig = Field(
        description='Userproxy config')
    data: Data = Field(
        description='Usergroup data')

    @classmethod
    def from_usergroup(
        cls,
        usergroup: DBUsergroup,
        token: TokenData
    ) -> Usergroup:
        data = cls(**usergroup.model_dump(mode='json'))

        if token.internal:
            return data

        if not (
            usergroup.data.applications.get(
                str(token.app_id), ApplicationScope.NONE
            ).value &
            ApplicationScope.SP_TOKENS.value
        ):
            data.data.sp_token = None
            data.data.sp_id = None

        return data

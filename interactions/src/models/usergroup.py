from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator
from beanie import PydanticObjectId  # noqa: TC002

from plural.db.enums import (
    ApplicationScope,
    PaginationStyle,
    SupporterTier,
    ReplyFormat
)


if TYPE_CHECKING:
    from plural.db import Usergroup

    from src.core.auth import TokenData


class UsergroupModel(BaseModel):
    class Config(BaseModel):
        account_tag: str = Field(
            description='the global account tag; overridden by group tags')
        reply_format: ReplyFormat = Field(
            description='Format for message references in servers')
        ping_replies: bool = Field(
            description='Whether to ping when you reply to someone')
        groups_in_autocomplete: bool = Field(
            description='Whether to show groups in member autocomplete')
        pagination_style: PaginationStyle = Field(
            description='The style of pagination buttons to use')
        roll_embed: bool = Field(
            description='Whether to show for dice rolls')
        tag_format: str = Field(
            description='The format for account/group tags in member names')
        pronoun_format: str = Field(
            description='The format for pronouns in member names')
        display_name_order: list[int] = Field(
            description='The order of display name components (0 = name, 1 = tag, 2 = pronouns)')
        private_member_info: bool = Field(
            description='whether to show member details in the proxy info command'
        )

    class UserproxyConfig(BaseModel):
        reply_format: ReplyFormat = Field(
            description='Format for message references in servers')
        dm_reply_format: ReplyFormat = Field(
            description='Format for message references in dms')
        ping_replies: bool = Field(
            description='Whether to ping when you reply to someone')
        include_tag: bool = Field(
            description='Whether to include the account/group tag in the member name')
        include_pronouns: bool = Field(
            description='Whether to include the pronouns in the member name')
        attachment_count: int = Field(
            description='The number of attachment options to include in the proxy command')
        self_hosted: bool = Field(
            description='Whether the userproxy is self-hosted')
        required_message_parameter: bool = Field(
            description='Whether the proxy command requires the message parameter')
        name_in_reply_command: bool = Field(
            description='Whether the name should be included in the reply command')
        include_attribution: bool = Field(
            description='Whether to include attribution at the end of bio')

    class Data(BaseModel):
        supporter_tier: SupporterTier = Field(
            description='The supporter tier of the user')
        image_limit: int = Field(
            description='The maximum number of images a user can upload')
        sp_token: str | None = Field(
            description='The simply plural token of the user')
        sp_id: str | None = Field(
            description='The simply plural system id of the user'
        )

    @field_validator('users', mode='before')
    @classmethod
    def validate_users(cls, users: list[str | int]) -> list[str]:
        return [str(user_id) for user_id in users]

    id: PydanticObjectId = Field(
        description='usergroup ID')
    users: list[str] = Field(
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
        usergroup: Usergroup,
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

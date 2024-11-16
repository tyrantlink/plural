from __future__ import annotations
from src.discord.types import MissingOr, MissingNoneOr, MISSING
from pydantic import BaseModel
from typing import TYPE_CHECKING
from datetime import datetime
from .base import BaseExport
from enum import StrEnum

if TYPE_CHECKING:
    from .standard import StandardExport


class PrivacyLevel(StrEnum):
    public = 'public'
    private = 'private'


class PluralKitExport(BaseExport):
    class Privacy(BaseModel):
        name_privacy: PrivacyLevel
        avatar_privacy: PrivacyLevel
        description_privacy: PrivacyLevel
        pronoun_privacy: PrivacyLevel
        member_list_privacy: PrivacyLevel
        group_list_privacy: PrivacyLevel
        front_privacy: PrivacyLevel
        front_history_privacy: PrivacyLevel

    class Config(BaseModel):
        timezone: str
        pings_enabled: bool
        latch_timeout: int | None
        member_default_private: bool
        group_default_private: bool
        show_private_info: bool
        member_limit: int
        group_limit: int
        case_sensitive_proxy_tags: bool
        proxy_error_message_enabled: bool
        hid_display_split: bool
        hid_display_caps: bool
        hid_list_padding: str
        proxy_switch: MissingOr[bool] = MISSING
        name_format: MissingNoneOr[str] = MISSING  # ? unsure of type
        description_templates: list[str]  # ? unsure of type

    class Member(BaseModel):
        class ProxyTag(BaseModel):
            prefix: str | None
            suffix: str | None

        class Privacy(BaseModel):
            visibility: PrivacyLevel
            name_privacy: PrivacyLevel
            description_privacy: PrivacyLevel
            birthday_privacy: PrivacyLevel
            pronoun_privacy: PrivacyLevel
            avatar_privacy: PrivacyLevel
            metadata_privacy: PrivacyLevel
            proxy_privacy: PrivacyLevel

        id: str
        uuid: str
        system: MissingOr[str] = MISSING
        name: str
        display_name: str | None
        color: str | None
        birthday: str | None
        pronouns: str | None
        avatar_url: str | None
        webhook_avatar_url: str | None
        banner: str | None
        description: str | None
        created: datetime | None
        proxy_tags: list[ProxyTag]
        keep_proxy: bool
        tts: bool
        autoproxy_enabled: bool | None
        message_count: int | None
        last_message_timestamp: datetime | None
        privacy: Privacy

    class Group(BaseModel):
        class Privacy(BaseModel):
            name_privacy: PrivacyLevel
            description_privacy: PrivacyLevel
            icon_privacy: PrivacyLevel
            list_privacy: PrivacyLevel
            metadata_privacy: PrivacyLevel
            visibility: PrivacyLevel

        id: str
        uuid: str
        system: MissingOr[str] = MISSING
        name: str
        display_name: str | None
        description: str | None
        icon: str | None
        banner: str | None
        color: str | None
        privacy: Privacy
        members: list[str]

    class Switch(BaseModel):
        id: MissingOr[str] = MISSING
        timestamp: datetime
        members: list[str]

    version: int
    id: str
    uuid: str
    name: str | None
    description: str | None
    tag: str | None
    pronouns: str | None
    avatar_url: str | None
    banner: str | None
    color: str | None
    created: datetime
    webhook_url: str | None
    privacy: Privacy
    config: Config
    accounts: list[int]
    members: list[Member]
    groups: list[Group]
    switches: list[Switch]

    def to_standard(self) -> StandardExport:
        from .standard import StandardExport

        pk_id_to_index = {
            member.id: self.members.index(member)
            for member in self.members
        }

        groups = {
            group.id: StandardExport.Group(
                id=self.groups.index(group),
                name=group.display_name or group.name,
                avatar_url=group.icon,
                channels=[],
                tag=group.display_name,
                members=[
                    pk_id_to_index[member_id]
                    for member_id in group.members
                ])
            for group in self.groups
        }

        members = [
            StandardExport.Member(
                id=self.members.index(member),
                name=member.display_name or member.name,
                avatar_url=member.avatar_url,
                proxy_tags=[
                    StandardExport.Member.ProxyTag(
                        prefix=tag.prefix or '',
                        suffix=tag.suffix or '',
                        regex=False,
                        case_sensitive=self.config.case_sensitive_proxy_tags
                    )
                    for tag in member.proxy_tags
                ]
            )
            for member in self.members
        ]

        return StandardExport(
            groups=list(groups.values()),
            members=members
        )

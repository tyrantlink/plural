from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime  # noqa: TC003
from enum import StrEnum

from plural.missing import Optional, Nullable  # noqa: TC002

from .base import BaseExport, MissingBaseModel

if TYPE_CHECKING:
    from .standard import StandardExport


class PrivacyLevel(StrEnum):
    public = 'public'
    private = 'private'


class PluralKitExport(BaseExport):
    class Privacy(MissingBaseModel):
        name_privacy: PrivacyLevel
        avatar_privacy: PrivacyLevel
        description_privacy: PrivacyLevel
        pronoun_privacy: PrivacyLevel
        member_list_privacy: PrivacyLevel
        group_list_privacy: PrivacyLevel
        front_privacy: PrivacyLevel
        front_history_privacy: PrivacyLevel

    class Config(MissingBaseModel):
        timezone: str
        pings_enabled: bool
        latch_timeout: Nullable[int]
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
        # ? can sometimes be "new" and i don't know what that means
        proxy_switch: Optional[bool | str]
        name_format: Optional[Nullable[str]]  # ? unsure of type
        description_templates: list[str]  # ? unsure of type

    class Member(MissingBaseModel):
        class ProxyTag(MissingBaseModel):
            prefix: Nullable[str]
            suffix: Nullable[str]

        class Privacy(MissingBaseModel):
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
        system: Optional[str]
        name: str
        display_name: Nullable[str]
        color: Nullable[str]
        birthday: Nullable[str]
        pronouns: Nullable[str]
        avatar_url: Nullable[str]
        webhook_avatar_url: Nullable[str]
        banner: Nullable[str]
        description: Nullable[str]
        created: Nullable[datetime]
        proxy_tags: list[ProxyTag]
        keep_proxy: bool
        tts: bool
        autoproxy_enabled: Nullable[bool]
        message_count: Nullable[int]
        last_message_timestamp: Nullable[datetime]
        privacy: Privacy

    class Group(MissingBaseModel):
        class Privacy(MissingBaseModel):
            name_privacy: PrivacyLevel
            description_privacy: PrivacyLevel
            icon_privacy: PrivacyLevel
            list_privacy: PrivacyLevel
            metadata_privacy: PrivacyLevel
            visibility: PrivacyLevel

        id: str
        uuid: str
        system: Optional[str]
        name: str
        display_name: Nullable[str]
        description: Nullable[str]
        icon: Nullable[str]
        banner: Nullable[str]
        color: Nullable[str]
        privacy: Privacy
        members: list[str]

    class Switch(MissingBaseModel):
        id: Optional[str]
        timestamp: datetime
        members: list[str]

    version: int
    id: str
    uuid: str
    name: Nullable[str]
    description: Nullable[str]
    tag: Nullable[str]
    pronouns: Nullable[str]
    avatar_url: Nullable[str]
    banner: Nullable[str]
    color: Nullable[str]
    created: datetime
    webhook_url: Nullable[str]
    privacy: Privacy
    config: Config
    accounts: list[int]
    members: list[Member]
    groups: list[Group]
    switches: list[Switch]

    def to_standard(self) -> StandardExport:
        from .standard import StandardExport

        group_map = {
            member: index
            for index, group in enumerate(self.groups)
            for member in group.members
        }

        groups = {
            group.id: StandardExport.Group(
                id=index,
                name=group.display_name or group.name,
                avatar_url=group.icon,
                channels=[],
                tag=self.tag)
            for index, group in enumerate(self.groups)
        }

        _default_group_id = None

        def default_group_id() -> int:
            nonlocal _default_group_id

            if _default_group_id is None:
                try:
                    _default_group_id = next(
                        group.id
                        for group in groups.values()
                        if group.name == 'default')
                except StopIteration:
                    _default_group_id = len(groups)+1

                    groups[_default_group_id] = StandardExport.Group(
                        id=_default_group_id,
                        name='default',
                        avatar_url=None,
                        channels=[],
                        tag=None
                    )

            return _default_group_id

        def get_color(hex: str | None) -> int | None:
            if hex is None:
                return None

            try:
                return int(hex.removeprefix('#'), 16)
            except ValueError:
                return None

        members = [
            StandardExport.Member(
                id=index,
                name=member.display_name or member.name,
                pronouns=member.pronouns or '',
                bio=member.description or '',
                birthday=member.birthday or '',
                color=get_color(member.color),
                avatar_url=member.webhook_avatar_url or member.avatar_url,
                proxy_tags=[StandardExport.Member.ProxyTag(
                    prefix=proxy_tag.prefix or '',
                    suffix=proxy_tag.suffix or '',
                    regex=False,
                    case_sensitive=False)
                    for proxy_tag in member.proxy_tags],
                group_id=(
                    group_map[member.id]
                    if member.id in group_map
                    else default_group_id()))
            for index, member in enumerate(self.members)
        ]

        return StandardExport(
            groups=list(groups.values()),
            members=members
        )

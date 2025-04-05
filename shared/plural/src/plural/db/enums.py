from enum import Enum, Flag


__all__ = (
    'ApplicationScope',
    'AutoProxyMode',
    'GroupSharePermissionLevel',
    'PaginationStyle',
    'ReplyFormat',
    'ReplyType',
    'ShareType',
    'SupporterTier',
)


class ApplicationScope(Flag):
    NONE = 0
    USER_EVENTS = 1 << 0
    USER_WRITE = 1 << 1
    SEND_MESSAGES = 1 << 2  # ? requires user approval
    USERPROXY_TOKENS = 1 << 3  # ? requires user approval
    SP_TOKENS = 1 << 4  # ? requires user approval

    @property
    def pretty_name(self) -> str:
        return {
            ApplicationScope.USER_EVENTS: 'User Events',
            ApplicationScope.USER_WRITE: 'User Write',
            ApplicationScope.SEND_MESSAGES: 'Send Messages',
            ApplicationScope.USERPROXY_TOKENS: 'Userproxy Tokens',
            ApplicationScope.SP_TOKENS: 'SimplyPlural Tokens',
        }[self]

    @property
    def description(self) -> str:
        return {
            ApplicationScope.USER_EVENTS: 'Receive user update events',
            ApplicationScope.USER_WRITE: 'Modify user data',
            ApplicationScope.SEND_MESSAGES: 'Access to send messages',
            ApplicationScope.USERPROXY_TOKENS: 'Userproxy tokens will be included in user data',
            ApplicationScope.SP_TOKENS: 'SimplyPlural tokens will be included in user data',
        }[self]

    @property
    def approval_required(self) -> bool:
        return self in (
            ApplicationScope.SEND_MESSAGES,
            ApplicationScope.USERPROXY_TOKENS,
            ApplicationScope.SP_TOKENS,
        )


class AutoProxyMode(Enum):
    LATCH = 0
    FRONT = 1
    LOCKED = 2
    DISABLED = 3

    @property
    def description(self) -> str:
        return {
            AutoProxyMode.LATCH: 'Using proxy tags will switch the autoproxied member',
            AutoProxyMode.FRONT: 'Using proxy tags will not modify the autoproxied member',
            AutoProxyMode.LOCKED: 'Proxy tags will be ignored and the autoproxied member will always be used',
            AutoProxyMode.DISABLED: 'All proxying is disabled (including with proxy tags)',
        }[self]


class GroupSharePermissionLevel(Enum):
    PROXY_ONLY = 0
    FULL_ACCESS = 1


class PaginationStyle(Enum):
    BASIC_ARROWS = 0
    TEXT_ARROWS = 1
    REM_AND_RAM = 2


class ReplyFormat(Enum):
    NONE = 0
    INLINE = 1
    EMBED = 2


class ReplyType(Enum):
    QUEUE = 0
    """Used for userproxy queue for reply option"""
    REPLY = 1
    """Used to store the referenced message when using the reply command"""


class ShareType(Enum):
    USERGROUP = 0
    GROUP = 1


class SupporterTier(Enum):
    NONE = 0
    DEVELOPER = 1
    SUPPORTER = 2

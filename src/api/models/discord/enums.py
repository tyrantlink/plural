from enum import Enum


class InteractionType(Enum):
    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3
    APPLICATION_COMMAND_AUTOCOMPLETE = 4
    MODAL_SUBMIT = 5


class InteractionContextType(Enum):
    GUILD = 1
    BOT_DM = 2
    PRIVATE_CHANNEL = 3


class CommandType(Enum):
    CHAT_INPUT = 1
    USER = 2
    MESSAGE = 3
    PRIMARY_ENTRY_POINT = 4


class IntegrationType(Enum):
    GUILD_INSTALL = 0
    USER_INSTALL = 1

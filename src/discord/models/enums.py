from __future__ import annotations
from pydantic import GetJsonSchemaHandler, GetCoreSchemaHandler
from pydantic_core.core_schema import CoreSchema, int_schema
from pydantic.json_schema import JsonSchemaValue
from enum import Enum, StrEnum, IntFlag
from typing import Any

__all__ = (
    'GatewayOpCode',
    'GatewayEventName',
    'ReactionType',
    'GuildMemberFlag',
    'PremiumType',
    'UserFlag',
    'ChannelType',
    'MessageType',
    'MessageReferenceType',
    'MessageFlag',
    'ApplicationCommandType',
    'ApplicationCommandOptionType',
    'ApplicationIntegrationType',
    'InteractionContextType',
    'EntryPointCommandHandlerType',
    'WebhookType',
    'OverwriteType',
    'VideoQualityMode',
    'ChannelFlag',
    'StickerType',
    'StickerFormatType',
    'Permission',
)


class GatewayOpCode(Enum):
    DISPATCH = 0  # Receive
    HEARTBEAT = 1  # Send/Receive
    IDENTIFY = 2  # Send
    PRESENCE_UPDATE = 3  # Send
    VOICE_STATE_UPDATE = 4  # Send
    RESUME = 6  # Send
    RECONNECT = 7  # Receive
    REQUEST_GUILD_MEMBERS = 8  # Send
    INVALID_SESSION = 9  # Receive
    HELLO = 10  # Receive
    HEARTBEAT_ACK = 11  # Receive
    REQUEST_SOUNDBOARD_SOUNDS = 31  # Send


class GatewayEventName(StrEnum):
    IDENTIFY = 'IDENTIFY'
    RESUME = 'RESUME'
    HEARTBEAT = 'HEARTBEAT'
    REQUEST_GUILD_MEMBERS = 'REQUEST_GUILD_MEMBERS'
    REQUEST_SOUNDBOARD_SOUNDS = 'REQUEST_SOUNDBOARD_SOUNDS'
    UPDATE_VOICE_STATE = 'UPDATE_VOICE_STATE'
    UPDATE_PRESENCE = 'UPDATE_PRESENCE'
    HELLO = 'HELLO'
    READY = 'READY'
    RESUMED = 'RESUMED'
    RECONNECT = 'RECONNECT'
    INVALID_SESSION = 'INVALID_SESSION'
    APPLICATION_COMMAND_PERMISSIONS_UPDATE = 'APPLICATION_COMMAND_PERMISSIONS_UPDATE'
    AUTO_MODERATION_RULE_CREATE = 'AUTO_MODERATION_RULE_CREATE'
    AUTO_MODERATION_RULE_UPDATE = 'AUTO_MODERATION_RULE_UPDATE'
    AUTO_MODERATION_RULE_DELETE = 'AUTO_MODERATION_RULE_DELETE'
    AUTO_MODERATION_RULE_EXECUTION = 'AUTO_MODERATION_RULE_EXECUTION'
    CHANNEL_CREATE = 'CHANNEL_CREATE'
    CHANNEL_UPDATE = 'CHANNEL_UPDATE'
    CHANNEL_DELETE = 'CHANNEL_DELETE'
    CHANNEL_PINS_UPDATE = 'CHANNEL_PINS_UPDATE'
    THREAD_CREATE = 'THREAD_CREATE'
    THREAD_UPDATE = 'THREAD_UPDATE'
    THREAD_DELETE = 'THREAD_DELETE'
    THREAD_LIST_SYNC = 'THREAD_LIST_SYNC'
    THREAD_MEMBER_UPDATE = 'THREAD_MEMBER_UPDATE'
    THREAD_MEMBERS_UPDATE = 'THREAD_MEMBERS_UPDATE'
    ENTITLEMENT_CREATE = 'ENTITLEMENT_CREATE'
    ENTITLEMENT_UPDATE = 'ENTITLEMENT_UPDATE'
    ENTITLEMENT_DELETE = 'ENTITLEMENT_DELETE'
    GUILD_CREATE = 'GUILD_CREATE'
    GUILD_UPDATE = 'GUILD_UPDATE'
    GUILD_DELETE = 'GUILD_DELETE'
    GUILD_AUDIT_LOG_ENTRY_CREATE = 'GUILD_AUDIT_LOG_ENTRY_CREATE'
    GUILD_BAN_ADD = 'GUILD_BAN_ADD'
    GUILD_BAN_REMOVE = 'GUILD_BAN_REMOVE'
    GUILD_EMOJIS_UPDATE = 'GUILD_EMOJIS_UPDATE'
    GUILD_STICKERS_UPDATE = 'GUILD_STICKERS_UPDATE'
    GUILD_INTEGRATIONS_UPDATE = 'GUILD_INTEGRATIONS_UPDATE'
    GUILD_MEMBER_ADD = 'GUILD_MEMBER_ADD'
    GUILD_MEMBER_REMOVE = 'GUILD_MEMBER_REMOVE'
    GUILD_MEMBER_UPDATE = 'GUILD_MEMBER_UPDATE'
    GUILD_MEMBERS_CHUNK = 'GUILD_MEMBERS_CHUNK'
    GUILD_ROLE_CREATE = 'GUILD_ROLE_CREATE'
    GUILD_ROLE_UPDATE = 'GUILD_ROLE_UPDATE'
    GUILD_ROLE_DELETE = 'GUILD_ROLE_DELETE'
    GUILD_SCHEDULED_EVENT_CREATE = 'GUILD_SCHEDULED_EVENT_CREATE'
    GUILD_SCHEDULED_EVENT_UPDATE = 'GUILD_SCHEDULED_EVENT_UPDATE'
    GUILD_SCHEDULED_EVENT_DELETE = 'GUILD_SCHEDULED_EVENT_DELETE'
    GUILD_SCHEDULED_EVENT_USER_ADD = 'GUILD_SCHEDULED_EVENT_USER_ADD'
    GUILD_SCHEDULED_EVENT_USER_REMOVE = 'GUILD_SCHEDULED_EVENT_USER_REMOVE'
    GUILD_SOUNDBOARD_SOUND_CREATE = 'GUILD_SOUNDBOARD_SOUND_CREATE'
    GUILD_SOUNDBOARD_SOUND_UPDATE = 'GUILD_SOUNDBOARD_SOUND_UPDATE'
    GUILD_SOUNDBOARD_SOUND_DELETE = 'GUILD_SOUNDBOARD_SOUND_DELETE'
    GUILD_SOUNDBOARD_SOUNDS_UPDATE = 'GUILD_SOUNDBOARD_SOUNDS_UPDATE'
    SOUNDBOARD_SOUNDS = 'SOUNDBOARD_SOUNDS'
    INTEGRATION_CREATE = 'INTEGRATION_CREATE'
    INTEGRATION_UPDATE = 'INTEGRATION_UPDATE'
    INTEGRATION_DELETE = 'INTEGRATION_DELETE'
    INTERACTION_CREATE = 'INTERACTION_CREATE'
    INVITE_CREATE = 'INVITE_CREATE'
    INVITE_DELETE = 'INVITE_DELETE'
    MESSAGE_CREATE = 'MESSAGE_CREATE'
    MESSAGE_UPDATE = 'MESSAGE_UPDATE'
    MESSAGE_DELETE = 'MESSAGE_DELETE'
    MESSAGE_DELETE_BULK = 'MESSAGE_DELETE_BULK'
    MESSAGE_REACTION_ADD = 'MESSAGE_REACTION_ADD'
    MESSAGE_REACTION_REMOVE = 'MESSAGE_REACTION_REMOVE'
    MESSAGE_REACTION_REMOVE_ALL = 'MESSAGE_REACTION_REMOVE_ALL'
    MESSAGE_REACTION_REMOVE_EMOJI = 'MESSAGE_REACTION_REMOVE_EMOJI'
    PRESENCE_UPDATE = 'PRESENCE_UPDATE'
    STAGE_INSTANCE_CREATE = 'STAGE_INSTANCE_CREATE'
    STAGE_INSTANCE_UPDATE = 'STAGE_INSTANCE_UPDATE'
    STAGE_INSTANCE_DELETE = 'STAGE_INSTANCE_DELETE'
    SUBSCRIPTION_CREATE = 'SUBSCRIPTION_CREATE'
    SUBSCRIPTION_UPDATE = 'SUBSCRIPTION_UPDATE'
    SUBSCRIPTION_DELETE = 'SUBSCRIPTION_DELETE'
    TYPING_START = 'TYPING_START'
    USER_UPDATE = 'USER_UPDATE'
    VOICE_CHANNEL_EFFECT_SEND = 'VOICE_CHANNEL_EFFECT_SEND'
    VOICE_STATE_UPDATE = 'VOICE_STATE_UPDATE'
    VOICE_SERVER_UPDATE = 'VOICE_SERVER_UPDATE'
    WEBHOOKS_UPDATE = 'WEBHOOKS_UPDATE'
    MESSAGE_POLL_VOTE_ADD = 'MESSAGE_POLL_VOTE_ADD'
    MESSAGE_POLL_VOTE_REMOVE = 'MESSAGE_POLL_VOTE_REMOVE'


class ReactionType(Enum):
    NORMAL = 0
    BURST = 1


class GuildMemberFlag(IntFlag):
    NONE = 0
    DID_REJOIN = 1 << 0
    COMPLETED_ONBOARDING = 1 << 1
    BYPASSES_VERIFICATION = 1 << 2
    STARTED_ONBOARDING = 1 << 3
    IS_GUEST = 1 << 4
    STARTED_HOME_ACTIONS = 1 << 5
    COMPLETED_HOME_ACTIONS = 1 << 6
    AUTOMOD_QUARANTINED_USERNAME = 1 << 7
    DM_SETTINGS_UPSELL_ACKNOWLEDGED = 1 << 9


class PremiumType(Enum):
    NONE = 0
    NITRO_CLASSIC = 1
    NITRO = 2
    NITRO_BASIC = 3


class UserFlag(IntFlag):
    NONE = 0
    STAFF = 1 << 0
    PARTNER = 1 << 1
    HYPESQUAD = 1 << 2
    BUG_HUNTER_LEVEL_1 = 1 << 3
    HYPESQUAD_ONLINE_HOUSE_1 = 1 << 6
    HYPESQUAD_ONLINE_HOUSE_2 = 1 << 7
    HYPESQUAD_ONLINE_HOUSE_3 = 1 << 8
    PREMIUM_EARLY_SUPPORTER = 1 << 9
    TEAM_PSEUDO_USER = 1 << 10
    BUG_HUNTER_LEVEL_2 = 1 << 14
    VERIFIED_BOT = 1 << 16
    VERIFIED_DEVELOPER = 1 << 17
    CERTIFIED_MODERATOR = 1 << 18
    BOT_HTTP_INTERACTIONS = 1 << 19
    ACTIVE_DEVELOPER = 1 << 22


class ChannelType(Enum):
    GUILD_TEXT = 0
    DM = 1
    GUILD_VOICE = 2
    GROUP_DM = 3
    GUILD_CATEGORY = 4
    GUILD_ANNOUNCEMENT = 5
    ANNOUNCEMENT_THREAD = 10
    PUBLIC_THREAD = 11
    PRIVATE_THREAD = 12
    GUILD_STAGE_VOICE = 13
    GUILD_DIRECTORY = 14
    GUILD_FORUM = 15
    GUILD_MEDIA = 16


class MessageType(Enum):
    DEFAULT = 0
    RECIPIENT_ADD = 1
    RECIPIENT_REMOVE = 2
    CALL = 3
    CHANNEL_NAME_CHANGE = 4
    CHANNEL_ICON_CHANGE = 5
    CHANNEL_PINNED_MESSAGE = 6
    USER_JOIN = 7
    GUILD_BOOST = 8
    GUILD_BOOST_TIER_1 = 9
    GUILD_BOOST_TIER_2 = 10
    GUILD_BOOST_TIER_3 = 11
    CHANNEL_FOLLOW_ADD = 12
    GUILD_DISCOVERY_DISQUALIFIED = 14
    GUILD_DISCOVERY_REQUALIFIED = 15
    GUILD_DISCOVERY_GRACE_PERIOD_INITIAL_WARNING = 16
    GUILD_DISCOVERY_GRACE_PERIOD_FINAL_WARNING = 17
    THREAD_CREATED = 18
    REPLY = 19
    CHAT_INPUT_COMMAND = 20
    THREAD_STARTER_MESSAGE = 21
    GUILD_INVITE_REMINDER = 22
    CONTEXT_MENU_COMMAND = 23
    AUTO_MODERATION_ACTION = 24
    ROLE_SUBSCRIPTION_PURCHASE = 25
    INTERACTION_PREMIUM_UPSELL = 26
    STAGE_START = 27
    STAGE_END = 28
    STAGE_SPEAKER = 29
    STAGE_TOPIC = 31
    GUILD_APPLICATION_PREMIUM_SUBSCRIPTION = 32
    GUILD_INCIDENT_ALERT_MODE_ENABLED = 36
    GUILD_INCIDENT_ALERT_MODE_DISABLED = 37
    GUILD_INCIDENT_REPORT_RAID = 38
    GUILD_INCIDENT_REPORT_FALSE_ALARM = 39
    PURCHASE_NOTIFICATION = 44
    POLL_RESULT = 46


class MessageReferenceType(Enum):
    DEFAULT = 0
    FORWARD = 1


class MessageFlag(IntFlag):
    NONE = 0
    CROSSPOSTED = 1 << 0
    IS_CROSSPOST = 1 << 1
    SUPPRESS_EMBEDS = 1 << 2
    SOURCE_MESSAGE_DELETED = 1 << 3
    URGENT = 1 << 4
    HAS_THREAD = 1 << 5
    EPHEMERAL = 1 << 6
    LOADING = 1 << 7
    FAILED_TO_MENTION_SOME_ROLES_IN_THREAD = 1 << 8
    SUPPRESS_NOTIFICATIONS = 1 << 12
    IS_VOICE_MESSAGE = 1 << 13


class ApplicationCommandType(Enum):
    CHAT_INPUT = 1
    USER = 2
    MESSAGE = 3
    PRIMARY_ENTRY_POINT = 4


class ApplicationCommandOptionType(Enum):
    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9
    NUMBER = 10
    ATTACHMENT = 11


class ApplicationIntegrationType(Enum):
    GUILD_INSTALL = 0
    USER_INSTALL = 1

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: type[Any] | None,
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return int_schema()

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return {"type": "integer"}


class InteractionContextType(Enum):
    GUILD = 0
    BOT_DM = 1
    PRIVATE_CHANNEL = 2


class EntryPointCommandHandlerType(Enum):
    APP_HANDLER = 1
    DISCORD_LAUNCH_ACTIVITY = 2


class WebhookType(Enum):
    INCOMING = 1
    CHANNEL_FOLLOWER = 2
    APPLICATION = 3


class OverwriteType(Enum):
    ROLE = 0
    MEMBER = 1


class VideoQualityMode(Enum):
    AUTO = 1
    FULL = 2


class ChannelFlag(IntFlag):
    NONE = 0
    PINNED = 1 << 1
    REQUIRE_TAG = 1 << 4
    HIDE_MEDIA_DOWNLOAD_OPTIONS = 1 << 15


class StickerType(Enum):
    STANDARD = 1
    GUILD = 2


class StickerFormatType(Enum):
    PNG = 1
    APNG = 2
    LOTTIE = 3
    GIF = 4

    @property
    def file_extension(self) -> str:
        match self:
            case StickerFormatType.PNG | StickerFormatType.APNG:
                return 'png'
            case StickerFormatType.LOTTIE:
                return 'json'
            case StickerFormatType.GIF:
                return 'gif'
            case _:
                raise ValueError('Invalid sticker format type')


class Permission(IntFlag):
    NONE = 0
    CREATE_INSTANT_INVITE = 1 << 0
    KICK_MEMBERS = 1 << 1
    BAN_MEMBERS = 1 << 2
    ADMINISTRATOR = 1 << 3
    MANAGE_CHANNELS = 1 << 4
    MANAGE_GUILD = 1 << 5
    ADD_REACTIONS = 1 << 6
    VIEW_AUDIT_LOG = 1 << 7
    PRIORITY_SPEAKER = 1 << 8
    STREAM = 1 << 9
    VIEW_CHANNEL = 1 << 10
    SEND_MESSAGES = 1 << 11
    SEND_TTS_MESSAGES = 1 << 12
    MANAGE_MESSAGES = 1 << 13
    EMBED_LINKS = 1 << 14
    ATTACH_FILES = 1 << 15
    READ_MESSAGE_HISTORY = 1 << 16
    MENTION_EVERYONE = 1 << 17
    USE_EXTERNAL_EMOJIS = 1 << 18
    VIEW_GUILD_INSIGHTS = 1 << 19
    CONNECT = 1 << 20
    SPEAK = 1 << 21
    MUTE_MEMBERS = 1 << 22
    DEAFEN_MEMBERS = 1 << 23
    MOVE_MEMBERS = 1 << 24
    USE_VAD = 1 << 25
    CHANGE_NICKNAME = 1 << 26
    MANAGE_NICKNAMES = 1 << 27
    MANAGE_ROLES = 1 << 28
    MANAGE_WEBHOOKS = 1 << 29
    MANAGE_GUILD_EXPRESSIONS = 1 << 30
    USE_APPLICATION_COMMANDS = 1 << 31
    REQUEST_TO_SPEAK = 1 << 32
    MANAGE_EVENTS = 1 << 33
    MANAGE_THREADS = 1 << 34
    CREATE_PUBLIC_THREADS = 1 << 35
    CREATE_PRIVATE_THREADS = 1 << 36
    USE_EXTERNAL_STICKERS = 1 << 37
    SEND_MESSAGES_IN_THREADS = 1 << 38
    USE_EMBEDDED_ACTIVITIES = 1 << 39
    MODERATE_MEMBERS = 1 << 40
    VIEW_CREATOR_MONETIZATION_ANALYTICS = 1 << 41
    USE_SOUNDBOARD = 1 << 42
    CREATE_GUILD_EXPRESSIONS = 1 << 43
    CREATE_EVENTS = 1 << 44
    USE_EXTERNAL_SOUNDS = 1 << 45
    SEND_VOICE_MESSAGES = 1 << 46
    SEND_POLLS = 1 << 49
    USE_EXTERNAL_APPS = 1 << 50

    def with_overwrite(self, allow: int, deny: int) -> Permission:
        return (self & ~deny) | allow

    @classmethod
    def all(cls) -> Permission:
        result = cls(0)
        for perm in cls:
            result |= perm
        return result

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: type[Any] | None,
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return int_schema()

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return {"type": "integer"}


class VerificationLevel(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4


class DefaultMessageNotificationLevel(Enum):
    ALL_MESSAGES = 0
    ONLY_MENTIONS = 1


class ExplicitContentFilterLevel(Enum):
    DISABLED = 0
    MEMBERS_WITHOUT_ROLES = 1
    ALL_MEMBERS = 2


class GuildFeature(StrEnum):
    ANIMATED_BANNER = 'ANIMATED_BANNER'
    ANIMATED_ICON = 'ANIMATED_ICON'
    APPLICATION_COMMAND_PERMISSIONS_V2 = 'APPLICATION_COMMAND_PERMISSIONS_V2'
    AUTO_MODERATION = 'AUTO_MODERATION'
    BANNER = 'BANNER'
    COMMUNITY = 'COMMUNITY'
    CREATOR_MONETIZABLE_PROVISIONAL = 'CREATOR_MONETIZABLE_PROVISIONAL'
    CREATOR_STORE_PAGE = 'CREATOR_STORE_PAGE'
    DEVELOPER_SUPPORT_SERVER = 'DEVELOPER_SUPPORT_SERVER'
    DISCOVERABLE = 'DISCOVERABLE'
    FEATURABLE = 'FEATURABLE'
    INVITES_DISABLED = 'INVITES_DISABLED'
    INVITE_SPLASH = 'INVITE_SPLASH'
    MEMBER_VERIFICATION_GATE_ENABLED = 'MEMBER_VERIFICATION_GATE_ENABLED'
    MORE_SOUNDBOARD = 'MORE_SOUNDBOARD'
    MORE_STICKERS = 'MORE_STICKERS'
    NEWS = 'NEWS'
    PARTNERED = 'PARTNERED'
    PREVIEW_ENABLED = 'PREVIEW_ENABLED'
    RAID_ALERTS_DISABLED = 'RAID_ALERTS_DISABLED'
    ROLE_ICONS = 'ROLE_ICONS'
    ROLE_SUBSCRIPTIONS_AVAILABLE_FOR_PURCHASE = 'ROLE_SUBSCRIPTIONS_AVAILABLE_FOR_PURCHASE'
    ROLE_SUBSCRIPTIONS_ENABLED = 'ROLE_SUBSCRIPTIONS_ENABLED'
    SOUNDBOARD = 'SOUNDBOARD'
    TICKETED_EVENTS_ENABLED = 'TICKETED_EVENTS_ENABLED'
    VANITY_URL = 'VANITY_URL'
    VERIFIED = 'VERIFIED'
    VIP_REGIONS = 'VIP_REGIONS'
    WELCOME_SCREEN_ENABLED = 'WELCOME_SCREEN_ENABLED'
    # ? not in discord documentation
    NEW_THREAD_PERMISSIONS = 'NEW_THREAD_PERMISSIONS'
    ACTIVITY_FEED_DISABLED_BY_USER = 'ACTIVITY_FEED_DISABLED_BY_USER'
    CREATOR_ACCEPTED_NEW_TERMS = 'CREATOR_ACCEPTED_NEW_TERMS'
    CHANNEL_ICON_EMOJIS_GENERATED = 'CHANNEL_ICON_EMOJIS_GENERATED'


class MFALevel(Enum):
    NONE = 0
    ELEVATED = 1


class SystemChannelFlag(IntFlag):
    NONE = 0
    SUPPRESS_JOIN_NOTIFICATIONS = 1 << 0
    SUPPRESS_PREMIUM_SUBSCRIPTIONS = 1 << 1
    SUPPRESS_GUILD_REMINDER_NOTIFICATIONS = 1 << 2
    SUPPRESS_JOIN_NOTIFICATION_REPLIES = 1 << 3
    SUPPRESS_ROLE_SUBSCRIPTION_PURCHASE_NOTIFICATIONS = 1 << 4
    SUPPRESS_ROLE_SUBSCRIPTION_PURCHASE_NOTIFICATION_REPLIES = 1 << 5


class PremiumTier(Enum):
    NONE = 0
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3

    @property
    def emoji_limit(self) -> int:
        match self:
            case PremiumTier.NONE:
                return 50
            case PremiumTier.TIER_1:
                return 100
            case PremiumTier.TIER_2:
                return 150
            case PremiumTier.TIER_3:
                return 250
            case _:
                raise ValueError('Invalid premium tier')

    @property
    def sticker_limit(self) -> int:
        match self:
            case PremiumTier.NONE:
                return 5
            case PremiumTier.TIER_1:
                return 15
            case PremiumTier.TIER_2:
                return 30
            case PremiumTier.TIER_3:
                return 60
            case _:
                raise ValueError('Invalid premium tier')

    @property
    def bitrate_limit(self) -> int:
        match self:
            case PremiumTier.NONE:
                return 96_000
            case PremiumTier.TIER_1:
                return 128_000
            case PremiumTier.TIER_2:
                return 256_000
            case PremiumTier.TIER_3:
                return 384_000
            case _:
                raise ValueError('Invalid premium tier')

    @property
    def filesize_limit(self) -> int:
        match self:
            case PremiumTier.NONE:
                return 26_214_400
            case PremiumTier.TIER_1:
                return 26_214_400
            case PremiumTier.TIER_2:
                return 52_428_800
            case PremiumTier.TIER_3:
                return 104_857_600
            case _:
                raise ValueError('Invalid premium tier')


class NSFWLevel(Enum):
    DEFAULT = 0
    EXPLICIT = 1
    SAFE = 2
    AGE_RESTRICTED = 3


class RoleFlag(IntFlag):
    NONE = 0
    IN_PROMPT = 1 << 0


class AllowedMentionType(Enum):
    ROLES = 'roles'
    USERS = 'users'
    EVERYONE = 'everyone'


class AttachmentFlag(IntFlag):
    NONE = 0
    IS_REMIX = 1 << 2


class PollLayoutType(Enum):
    DEFAULT = 1


class InteractionType(Enum):
    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3
    APPLICATION_COMMAND_AUTOCOMPLETE = 4
    MODAL_SUBMIT = 5


class EntitlementType(Enum):
    PURCHASE = 1
    PREMIUM_SUBSCRIPTION = 2
    DEVELOPER_GIFT = 3
    TEST_MODE_PURCHASE = 4
    FREE_PURCHASE = 5
    USER_GIFT = 6
    PREMIUM_PURCHASE = 7
    APPLICATION_SUBSCRIPTION = 8


class InteractionCallbackType(Enum):
    PONG = 1
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5
    DEFERRED_UPDATE_MESSAGE = 6
    UPDATE_MESSAGE = 7
    APPLICATION_COMMAND_AUTOCOMPLETE_RESULT = 8
    MODAL = 9
    PREMIUM_REQUIRED = 10  # deprecated
    LAUNCH_ACTIVITY = 12

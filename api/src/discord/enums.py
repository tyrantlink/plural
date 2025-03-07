from __future__ import annotations

from typing import Self, TYPE_CHECKING, Any
from enum import Enum, Flag, EnumMeta

from pydantic_core.core_schema import (
    with_info_after_validator_function,
    enum_schema,
    int_schema,
    CoreSchema
)

if TYPE_CHECKING:
    from pydantic import GetJsonSchemaHandler, GetCoreSchemaHandler
    from pydantic.json_schema import JsonSchemaValue


# ? library enums
class ApplicationCommandScope(Enum):
    PRIMARY = 1
    """Command will be registered to the primary app (/plu/ral)"""
    USERPROXY = 2
    """Command will be registered to userproxies"""


class CharEnumMeta(EnumMeta):
    CHARS = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

    def __call__(
        cls,
        value: int | str,
        *args,  # noqa: ANN002
        **kwargs  # noqa: ANN003
    ) -> CharEnumMeta:
        if isinstance(value, int):
            return super().__call__(value, *args, **kwargs)

        return super().__call__(cls.CHARS.index(value), *args, **kwargs)


class CustomIdExtraType(Enum, metaclass=CharEnumMeta):
    NONE = 0
    STRING = 1
    INTEGER = 2
    BOOLEAN = 3
    USER = 4
    CHANNEL = 5
    MEMBER = 6
    GROUP = 7
    MESSAGE = 8

    def __str__(self) -> str:
        return CharEnumMeta.CHARS[self.value]


# ? discord enums
class ApplicationIntegrationType(Enum):
    GUILD_INSTALL = 0
    """App is installable to servers"""
    USER_INSTALL = 1
    """App is installable to users"""

    @classmethod
    def ALL(cls) -> list[Self]:  # noqa: N802
        return list(cls)

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: type[Any] | None,
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return enum_schema(cls, list(cls.__members__.values()), sub_type='int')

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return {"type": "integer"}


class Permission(Flag):
    CREATE_INSTANT_INVITE = 1 << 0
    """Allows creation of instant invites"""
    KICK_MEMBERS = 1 << 1
    """Allows kicking members"""
    BAN_MEMBERS = 1 << 2
    """Allows banning members"""
    ADMINISTRATOR = 1 << 3
    """Allows all permissions and bypasses channel permission overwrites"""
    MANAGE_CHANNELS = 1 << 4
    """Allows management and editing of channels"""
    MANAGE_GUILD = 1 << 5
    """Allows management and editing of the guild"""
    ADD_REACTIONS = 1 << 6
    """Allows for the addition of reactions to messages"""
    VIEW_AUDIT_LOG = 1 << 7
    """Allows for viewing of audit logs"""
    PRIORITY_SPEAKER = 1 << 8
    """Allows for using priority speaker in a voice channel"""
    STREAM = 1 << 9
    """Allows the user to go live"""
    VIEW_CHANNEL = 1 << 10
    """Allows guild members to view a channel, which includes reading messages in text channels and joining voice channels"""
    SEND_MESSAGES = 1 << 11
    """Allows for sending messages in a channel and creating threads in a forum (does not allow sending messages in threads)"""
    SEND_TTS_MESSAGES = 1 << 12
    """Allows for sending of `/tts` messages"""
    MANAGE_MESSAGES = 1 << 13
    """Allows for deletion of other users messages"""
    EMBED_LINKS = 1 << 14
    """Links sent by users with this permission will be auto-embedded"""
    ATTACH_FILES = 1 << 15
    """Allows for uploading images and files"""
    READ_MESSAGE_HISTORY = 1 << 16
    """Allows for reading of message history"""
    MENTION_EVERYONE = 1 << 17
    """Allows for using the `@everyone` tag to notify all users in a channel, and the `@here` tag to notify all online users in a channel"""
    USE_EXTERNAL_EMOJIS = 1 << 18
    """Allows the usage of custom emojis from other servers"""
    VIEW_GUILD_INSIGHTS = 1 << 19
    """Allows for viewing guild insights"""
    CONNECT = 1 << 20
    """Allows for joining of a voice channel"""
    SPEAK = 1 << 21
    """Allows for speaking in a voice channel"""
    MUTE_MEMBERS = 1 << 22
    """Allows for muting members in a voice channel"""
    DEAFEN_MEMBERS = 1 << 23
    """Allows for deafening of members in a voice channel"""
    MOVE_MEMBERS = 1 << 24
    """Allows for moving of members between voice channels"""
    USE_VAD = 1 << 25
    """Allows for using voice-activity-detection in a voice channel"""
    CHANGE_NICKNAME = 1 << 26
    """Allows for modification of own nickname"""
    MANAGE_NICKNAMES = 1 << 27
    """Allows for modification of other users nicknames"""
    MANAGE_ROLES = 1 << 28
    """Allows management and editing of roles"""
    MANAGE_WEBHOOKS = 1 << 29
    """Allows management and editing of webhooks"""
    MANAGE_GUILD_EXPRESSIONS = 1 << 30
    """Allows for editing and deleting emojis, stickers, and soundboard sounds created by all users"""
    USE_APPLICATION_COMMANDS = 1 << 31
    """Allows members to use application commands, including slash commands and context menu commands."""
    REQUEST_TO_SPEAK = 1 << 32
    """Allows for requesting to speak in stage channels."""
    MANAGE_EVENTS = 1 << 33
    """Allows for editing and deleting scheduled events created by all users"""
    MANAGE_THREADS = 1 << 34
    """Allows for deleting and archiving threads, and viewing all private threads"""
    CREATE_PUBLIC_THREADS = 1 << 35
    """Allows for creating public and announcement threads"""
    CREATE_PRIVATE_THREADS = 1 << 36
    """Allows for creating private threads"""
    USE_EXTERNAL_STICKERS = 1 << 37
    """Allows the usage of custom stickers from other servers"""
    SEND_MESSAGES_IN_THREADS = 1 << 38
    """Allows for sending messages in threads"""
    USE_EMBEDDED_ACTIVITIES = 1 << 39
    """Allows for using Activities (applications with the `EMBEDDED` flag) in a voice channel"""
    MODERATE_MEMBERS = 1 << 40
    """Allows for timing out users to prevent them from sending or reacting to messages in chat and threads, and from speaking in voice and stage channels"""
    VIEW_CREATOR_MONETIZATION_ANALYTICS = 1 << 41
    """Allows for viewing role subscription insights"""
    USE_SOUNDBOARD = 1 << 42
    """Allows for using soundboard in a voice channel"""
    CREATE_GUILD_EXPRESSIONS = 1 << 43
    """Allows for creating emojis, stickers, and soundboard sounds, and editing and deleting those created by the current user."""
    CREATE_EVENTS = 1 << 44
    """Allows for creating scheduled events, and editing and deleting those created by the current user."""
    USE_EXTERNAL_SOUNDS = 1 << 45
    """Allows the usage of custom soundboard sounds from other servers"""
    SEND_VOICE_MESSAGES = 1 << 46
    """Allows sending voice messages"""
    USE_CLYDE_AI = 1 << 47
    """Allows members to interact with the Clyde AI integration"""
    SET_VOICE_CHANNEL_STATUS = 1 << 48
    """Allows setting voice channel status"""
    SEND_POLLS = 1 << 49
    """Allows sending polls"""
    USE_EXTERNAL_APPS = 1 << 50
    """Allows user-installed apps to send public responses. When disabled, users will still be allowed to use their apps but the responses will be ephemeral. This only applies to apps not also installed to the server."""

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
        return with_info_after_validator_function(
            lambda x, _: cls(x),
            int_schema()
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        _core_schema: CoreSchema,
        _handler: GetJsonSchemaHandler,
    ) -> JsonSchemaValue:
        return {"type": "integer"}


class ApplicationFlag(Flag):
    EMBEDDED_RELEASED = 1 << 1
    """Embedded application is released to the public"""
    MANAGED_EMOJI = 1 << 2
    """Application can create managed emoji"""
    EMBEDDED_IAP = 1 << 3
    """Embedded application can use in-app purchases"""
    GROUP_DM_CREATE = 1 << 4
    """Application can create group DMs without limit"""
    RPC_PRIVATE_BETA = 1 << 5
    """This application can access the client RPC server"""
    APPLICATION_AUTO_MODERATION_RULE_CREATE_BADGE = 1 << 6
    """Indicates if an app uses the Auto Moderation API"""
    GAME_PROFILE_DISABLED = 1 << 7
    """Application has its game profile page disabled"""
    PUBLIC_OAUTH2_CLIENT = 1 << 8
    """Application's OAuth2 credentials are public"""
    CONTEXTLESS_ACTIVITY = 1 << 9
    """Embedded application's activity can be launched without a context"""
    ALLOW_ACTIVITY_ACTION_JOIN_REQUEST = 1 << 10
    """Application can enable activity join requests"""
    RPC_HAS_CONNECTED = 1 << 11
    """Application has accessed the client RPC server before"""
    GATEWAY_PRESENCE = 1 << 12
    """Intent required for bots in **100 or more servers** to receive `presence_update` events"""
    GATEWAY_PRESENCE_LIMITED = 1 << 13
    """Intent required for bots in under 100 servers to receive `presence_update` events, found on the **Bot** page in your app's settings"""
    GATEWAY_GUILD_MEMBERS = 1 << 14
    """Intent required for bots in **100 or more servers** to receive member-related events like `guild_member_add`. See the list of member-related events under `GUILD_MEMBERS`"""
    GATEWAY_GUILD_MEMBERS_LIMITED = 1 << 15
    """Intent required for bots in under 100 servers to receive member-related events like `guild_member_add`, found on the **Bot** page in your app's settings. See the list of member-related events under `GUILD_MEMBERS`"""
    VERIFICATION_PENDING_GUILD_LIMIT = 1 << 16
    """Indicates unusual growth of an app that prevents verification"""
    EMBEDDED = 1 << 17
    """Indicates if an app is embedded within the Discord client (currently unavailable publicly)"""
    GATEWAY_MESSAGE_CONTENT = 1 << 18
    """Intent required for bots in **100 or more servers** to receive message content"""
    GATEWAY_MESSAGE_CONTENT_LIMITED = 1 << 19
    """Intent required for bots in under 100 servers to receive message content, found on the **Bot** page in your app's settings"""
    EMBEDDED_FIRST_PARTY = 1 << 20
    """This embedded application is created by Discord"""
    APPLICATION_COMMAND_MIGRATED = 1 << 21
    """Unknown; likely migration to application command v2"""
    APPLICATION_COMMAND_BADGE = 1 << 23
    """Indicates if an app has registered global application commands"""
    ACTIVE = 1 << 24
    """Application has had at least one global application command used in the last 30 days"""
    ACTIVE_GRACE_PERIOD = 1 << 25
    """Application has not had any global application commands used in the last 30 days and has lost the `ACTIVE` flag"""
    IFRAME_MODAL = 1 << 26
    """Application can use IFrames within modals"""
    SOCIAL_LAYER_INTEGRATION = 1 << 27
    """Application can use the social layer integration"""
    UNDOCUMENTED_28 = 1 << 28
    """Unknown"""
    PROMOTED = 1 << 29
    """Application is promoted by Discord in the application directory"""
    PARTNER = 1 << 30
    """Application is a Discord partner"""


class EventWebhooksStatus(Enum):
    DISABLED = 1
    """Webhook events are disabled by developer"""
    ENABLED = 2
    """Webhook events are enabled by developer"""
    DISABLED_BY_DISCORD = 3
    """Webhook events are disabled by Discord, usually due to inactivity"""


class EventWebhooksType(Enum):
    APPLICATION_AUTHORIZED = 'APPLICATION_AUTHORIZED'
    """Sent when an app was authorized by a user to a server or their account"""
    ENTITLEMENT_CREATE = 'ENTITLEMENT_CREATE'
    """Entitlement was created"""
    QUEST_USER_ENROLLMENT = 'QUEST_USER_ENROLLMENT'
    """User was added to a Quest"""


class MembershipState(Enum):
    INVITED = 1
    ACCEPTED = 2


class AttachmentFlag(Flag):
    IS_CLIP = 1 << 0
    """This attachment is a clipped recording of a stream"""
    IS_THUMBNAIL = 1 << 1
    """This attachment is a thumbnail"""
    IS_REMIX = 1 << 2
    """This attachment has been remixed"""
    IS_SPOILER = 1 << 3
    """This attachment is a spoiler"""
    CONTAINS_EXPLICIT_MEDIA = 1 << 4
    """This attachment was flagged as sensitive content"""
    IS_ANIMATED = 1 << 5
    """This attachment is an animated image"""


class ChannelFlag(Flag):
    PINNED = 1 << 1
    """this thread is pinned to the top of its parent `GUILD_FORUM` or `GUILD_MEDIA` channel"""
    REQUIRE_TAG = 1 << 4
    """whether a tag is required to be specified when creating a thread in a `GUILD_FORUM` or a `GUILD_MEDIA` channel. Tags are specified in the `applied_tags` field."""
    HIDE_MEDIA_DOWNLOAD_OPTIONS = 1 << 15
    """when set hides the embedded media download options. Available only for media channels"""


class ChannelType(Enum):
    GUILD_TEXT = 0
    """a text channel within a server"""
    DM = 1
    """a direct message between users"""
    GUILD_VOICE = 2
    """a voice channel within a server"""
    GROUP_DM = 3
    """a direct message between multiple users"""
    GUILD_CATEGORY = 4
    """an organizational category that contains up to 50 channels"""
    GUILD_ANNOUNCEMENT = 5
    """a channel that users can follow and crosspost into their own server (formerly news channels)"""
    GUILD_STORE = 6
    """A channel in which game developers can sell their game on Discord"""
    GUILD_LFG = 7
    """A channel where users can match up for various games"""
    LFG_GUILD_DM = 8
    """A private channel between multiple users for a group within an LFG channel"""
    THREAD_ALPHA = 9
    """The first iteration of the threads feature, never widely used"""
    ANNOUNCEMENT_THREAD = 10
    """	a temporary sub-channel within a GUILD_ANNOUNCEMENT channel"""
    PUBLIC_THREAD = 11
    """a temporary sub-channel within a GUILD_TEXT or GUILD_FORUM channel"""
    PRIVATE_THREAD = 12
    """a temporary sub-channel within a GUILD_TEXT channel that is only viewable by those invited and those with the MANAGE_THREADS permission"""
    GUILD_STAGE_VOICE = 13
    """a stage channel for live audio streaming"""
    GUILD_DIRECTORY = 14
    """the channel in a hub containing the listed servers"""
    GUILD_FORUM = 15
    """	Channel that can only contain threads"""
    GUILD_MEDIA = 16
    """Channel that can only contain threads, similar to `GUILD_FORUM` channels"""
    LOBBY = 17
    """A game lobby channel"""
    EPHEMERAL_DM = 18
    """A private channel created by the social layer SDK"""


class ForumLayoutType(Enum):
    NOT_SET = 0
    """No defaul tha sbeen set for forum channel"""
    LIST_VIEW = 1
    """Display posts as a list"""
    GALLERY_VIEW = 2
    """Display posts as a gallery"""


class OverwriteType(Enum):
    ROLE = 0
    """role"""
    MEMBER = 1
    """member"""


class SortOrderType(Enum):
    LATEST_ACTIVITY = 0
    """Sort forum posts by activity"""
    CREATION_DATE = 1
    """Sort forum posts by creation time (from most recent to oldest)"""


class VideoQualityMode(Enum):
    AUTO = 1
    """Discord chooses the quality for optimal performance"""
    FULL = 2
    """720p"""


class ButtonStyle(Enum):
    PRIMARY = 1
    """blurple"""
    SECONDARY = 2
    """grey"""
    SUCCESS = 3
    """green"""
    DANGER = 4
    """red"""
    LINK = 5
    """grey, navigates to a URL"""
    PREMIUM = 6
    """blurple"""


class ComponentType(Enum):
    ACTION_ROW = 1
    """Container for other components"""
    BUTTON = 2
    """Button object"""
    STRING_SELECT = 3
    """Select menu for picking from defined text options"""
    TEXT_INPUT = 4
    """Text input object"""
    USER_SELECT = 5
    """Select menu for users"""
    ROLE_SELECT = 6
    """Select menu for roles"""
    MENTIONABLE_SELECT = 7
    """Select menu for mentionables (users *and* roles)"""
    CHANNEL_SELECT = 8
    """Select menu for channels"""


class DefaultValueType(Enum):
    USER = 'user'
    """user"""
    ROLE = 'role'
    """role"""
    CHANNEL = 'channel'
    """channel"""


class TextInputStyle(Enum):
    SHORT = 1
    """Single-line input"""
    PARAGRAPH = 2
    """Multi-line input"""


class EmbedType(Enum):
    RICH = 'rich'
    """generic embed rendered from embed attributes"""
    IMAGE = 'image'
    """image embed"""
    VIDEO = 'video'
    """video embed"""
    GIFV = 'gifv'
    """animated gif image embed rendered as a video embed"""
    ARTICLE = 'article'
    """article embed"""
    LINK = 'link'
    """link embed"""
    POLL_RESULT = 'poll_result'
    """poll result embed"""


class EntitlementType(Enum):
    PURCHASE = 1
    """Entitlement was purchased by user"""
    PREMIUM_SUBSCRIPTION = 2
    """Entitlement for Discord Nitro subscription"""
    DEVELOPER_GIFT = 3
    """Entitlement was gifted by developer"""
    TEST_MODE_PURCHASE = 4
    """Entitlement was purchased by a dev in application test mode"""
    FREE_PURCHASE = 5
    """Entitlement was granted when the SKU was free"""
    USER_GIFT = 6
    """Entitlement was gifted by another user"""
    PREMIUM_PURCHASE = 7
    """Entitlement was claimed by user for free as a Nitro Subscriber"""
    APPLICATION_SUBSCRIPTION = 8
    """Entitlement was purchased as an app subscription"""


class StickerFormatType(Enum):
    PNG = 1
    APNG = 2
    LOTTIE = 3
    GIF = 4


class StickerType(Enum):
    STANDARD = 1
    """an official sticker in a pack"""
    GUILD = 2
    """a sticker uploaded to a guild for the guild's members"""


class DefaultMessageNotificationLevel(Enum):
    ALL_MESSAGES = 0
    """members will receive notifications for all messages by default"""
    ONLY_MENTIONS = 1
    """members will receive notifications only for messages that @mention them by default"""


class ExplicitContentFilterLevel(Enum):
    DISABLED = 0
    """media content will not be scanned"""
    MEMBERS_WITHOUT_ROLES = 1
    """media content sent by members without roles will be scanned"""
    ALL_MEMBERS = 2
    """media content sent by all members will be scanned"""


class MFALevel(Enum):
    NONE = 0
    """guild has no MFA/2FA requirement for moderation actions"""
    ELEVATED = 1
    """guild has a 2FA requirement for moderation actions"""


class NSFWLevel(Enum):
    DEFAULT = 0
    EXPLICIT = 1
    SAFE = 2
    AGE_RESTRICTED = 3


class PremiumTier(Enum):
    NONE = 0
    """guild has not unlocked any Server Boost perks"""
    TIER_1 = 1
    """guild has unlocked Server Boost level 1 perks"""
    TIER_2 = 2
    """guild has unlocked Server Boost level 2 perks"""
    TIER_3 = 3
    """guild has unlocked Server Boost level 3 perks"""

    @property
    def filesize_limit(self) -> int:
        match self:
            case PremiumTier.NONE:
                return 10_485_760
            case PremiumTier.TIER_1:
                return 26_214_400
            case PremiumTier.TIER_2:
                return 52_428_800
            case PremiumTier.TIER_3:
                return 104_857_600
            case _:
                raise ValueError('Invalid premium tier')


class SystemChannelFlag(Flag):
    SUPPRESS_JOIN_NOTIFICATIONS = 1 << 0
    """Suppress member join notifications"""
    SUPPRESS_PREMIUM_SUBSCRIPTIONS = 1 << 1
    """Suppress server boost notifications"""
    SUPPRESS_GUILD_REMINDER_NOTIFICATIONS = 1 << 2
    """Suppress server setup tips"""
    SUPPRESS_JOIN_NOTIFICATION_REPLIES = 1 << 3
    """Hide member join sticker reply buttons"""
    SUPPRESS_ROLE_SUBSCRIPTION_PURCHASE_NOTIFICATIONS = 1 << 4
    """Suppress role subscription purchase and renewal notifications"""
    SUPPRESS_ROLE_SUBSCRIPTION_PURCHASE_NOTIFICATION_REPLIES = 1 << 5
    """Hide role subscription sticker reply buttons"""


class VerificationLevel(Enum):
    NONE = 0
    """unrestricted"""
    LOW = 1
    """must have verified email on account"""
    MEDIUM = 2
    """must be registered on Discord for longer than 5 minutes"""
    HIGH = 3
    """must be a member of the server for longer than 10 minutes"""
    VERY_HIGH = 4
    """must have a verified phone number"""


class ApplicationCommandOptionType(Enum):
    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    """Any integer between -2^53 and 2^53"""
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    """Includes all channel types + categories"""
    ROLE = 8
    MENTIONABLE = 9
    """Includes users and roles"""
    NUMBER = 10
    """Any double between -2^53 and 2^53"""
    ATTACHMENT = 11
    """attachment object"""


class ApplicationCommandType(Enum):
    CHAT_INPUT = 1
    """Slash commands; a text-based command that shows up when a user types `/`"""
    USER = 2
    """A UI-based command that shows up when you right click or tap on a user"""
    MESSAGE = 3
    """A UI-based command that shows up when you right click or tap on a message"""
    PRIMARY_ENTRY_POINT = 4
    """A UI-based command that represents the primary way to invoke an app's Activity"""

    def __str__(self) -> str:
        match self:
            case ApplicationCommandType.CHAT_INPUT:
                return '/'
            case ApplicationCommandType.USER:
                return 'USER '
            case ApplicationCommandType.MESSAGE:
                return 'MESSAGE '
            case _:
                return super().__str__()


class InteractionCallbackType(Enum):
    PONG = 1
    """ACK a `Ping`"""
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    """Respond to an interaction with a message"""
    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5
    """ACK an interaction and edit a response later, the user sees a loading state"""
    DEFERRED_UPDATE_MESSAGE = 6
    """For components, ACK an interaction and edit the original message later; the user does not see a loading state\n
    Only valid for component-based interactions"""
    UPDATE_MESSAGE = 7
    """For components, edit the message the component was attached to\n
    Only valid for component-based interactions"""
    APPLICATION_COMMAND_AUTOCOMPLETE_RESULT = 8
    """Respond to an autocomplete interaction with suggested choices"""
    MODAL = 9
    """Respond to an interaction with a popup moda\n
    Not available for `MODAL_SUBMIT` and `PING` interactions."""
    PREMIUM_REQUIRED = 10
    """Deprecated; respond to an interaction with an upgrade button, only available for apps with monetization enabled"""
    LAUNCH_ACTIVITY = 12
    """Launch the Activity associated with the app. Only available for apps with Activities enabled"""


class InteractionContextType(Enum):
    GUILD = 0
    """Interaction can be used within servers"""
    BOT_DM = 1
    """Interaction can be used within DMs with the app's bot user"""
    PRIVATE_CHANNEL = 2
    """Interaction can be used within Group DMs and DMs other than the app's bot user"""

    @classmethod
    def ALL(cls) -> list[Self]:  # noqa: N802
        return list(cls)


class InteractionType(Enum):
    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3
    APPLICATION_COMMAND_AUTOCOMPLETE = 4
    MODAL_SUBMIT = 5


class MemberFlag(Flag):
    DID_REJOIN = 1 << 0
    """Member has left and rejoined the guild"""
    COMPLETED_ONBOARDING = 1 << 1
    """Member has completed onboarding"""
    BYPASSES_VERIFICATION = 1 << 2
    """Member is exempt from guild verification requirements"""
    STARTED_ONBOARDING = 1 << 3
    """Member has started onboarding"""
    IS_GUEST = 1 << 4
    """Member is a guest and can only access the voice channel they were invited to"""
    STARTED_HOME_ACTIONS = 1 << 5
    """Member has started Server Guide new member actions"""
    COMPLETED_HOME_ACTIONS = 1 << 6
    """Member has completed Server Guide new member actions"""
    AUTOMOD_QUARANTINED_USERNAME = 1 << 7
    """Member's username, display name, or nickname is blocked by AutoMod"""
    DM_SETTINGS_UPSELL_ACKNOWLEDGED = 1 << 9
    """Member has dismissed the DM settings upsell"""


class AllowedMentionType(Enum):
    ROLES = 'roles'
    """Controls role mentions"""
    USERS = 'users'
    """Controls user mentions"""
    EVERYONE = 'everyone'
    """Controls @everyone and @here mentions"""


class MessageFlag(Flag):
    NONE = 0
    """no flags set"""
    CROSSPOSTED = 1 << 0
    """this message has been published to subscribed channels (via Channel Following)"""
    IS_CROSSPOST = 1 << 1
    """this message originated from a message in another channel (via Channel Following)"""
    SUPPRESS_EMBEDS = 1 << 2
    """do not include any embeds when serializing this message"""
    SOURCE_MESSAGE_DELETED = 1 << 3
    """the source message for this crosspost has been deleted (via Channel Following)"""
    URGENT = 1 << 4
    """this message came from the urgent message system"""
    HAS_THREAD = 1 << 5
    """this message has an associated thread, with the same id as the message"""
    EPHEMERAL = 1 << 6
    """this message is only visible to the user who invoked the Interaction"""
    LOADING = 1 << 7
    """this message is an Interaction Response and the bot is "thinking"""
    FAILED_TO_MENTION_SOME_ROLES_IN_THREAD = 1 << 8
    """this message failed to mention some roles and add their members to the thread"""
    SUPPRESS_NOTIFICATIONS = 1 << 12
    """this message will not trigger push and desktop notifications"""
    IS_VOICE_MESSAGE = 1 << 13
    """this message is a voice message"""


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


class PollLayoutType(Enum):
    DEFAULT = 1
    """The, uhm, default layout type."""


class RoleFlag(Flag):
    IN_PROMPT = 1 << 0
    """role can be selected by members in an onboarding prompt"""


class PremiumType(Enum):
    NONE = 0
    NITRO_CLASSIC = 1
    NITRO = 2
    NITRO_BASIC = 3


class UserFlag(Flag):
    STAFF = 1 << 0
    """Discord Employee"""
    PARTNER = 1 << 1
    """Partnered Server Owner"""
    HYPESQUAD = 1 << 2
    """HypeSquad Events Member"""
    BUG_HUNTER_LEVEL_1 = 1 << 3
    """Bug Hunter Level 1"""
    MFA_SMS = 1 << 4
    """SMS enabled as a multi-factor authentication backup"""
    PREMIUM_PROMO_DISMISSED = 1 << 5
    """User has dismissed the current premium (Nitro) promotion"""
    HYPESQUAD_ONLINE_HOUSE_1 = 1 << 6
    """House Bravery Member"""
    HYPESQUAD_ONLINE_HOUSE_2 = 1 << 7
    """House Brilliance Member"""
    HYPESQUAD_ONLINE_HOUSE_3 = 1 << 8
    """House Balance Member"""
    PREMIUM_EARLY_SUPPORTER = 1 << 9
    """Early Nitro Supporter"""
    TEAM_PSEUDO_USER = 1 << 10
    """User is a team"""
    HUBSPOT_CONTACT = 1 << 11
    """User is a member of an official Discord program (e.g. partner)"""
    SYSTEM = 1 << 12
    """User is a system user (i.e. official Discord account)"""
    HAS_UNREAD_URGENT_MESSAGES = 1 << 13
    """User has unread urgent system messages; an urgent message is one sent from Trust and Safety"""
    BUG_HUNTER_LEVEL_2 = 1 << 14
    """Bug Hunter Level 2"""
    UNDERAGE_DELETED = 1 << 15
    """User is scheduled for deletion for being under the minimum required age"""
    VERIFIED_BOT = 1 << 16
    """Verified Bot"""
    VERIFIED_DEVELOPER = 1 << 17
    """Early Verified Bot Developer"""
    CERTIFIED_MODERATOR = 1 << 18
    """Moderator Programs Alumni"""
    BOT_HTTP_INTERACTIONS = 1 << 19
    """Bot uses only HTTP interactions and is shown in the online member list"""
    SPAMMER = 1 << 20
    """User is marked as a spammer and has their messages collapsed in the UI"""
    DISABLE_PREMIUM = 1 << 21
    """User has manually disabled premium (Nitro) features"""
    ACTIVE_DEVELOPER = 1 << 22
    """User is an Active Developer"""


class WebhookType(Enum):
    INCOMING = 1
    """Incoming Webhooks can post messages to channels with a generated token"""
    CHANNEL_FOLLOWER = 2
    """Channel Follower Webhooks are internal webhooks used with Channel Following to post new messages into channels"""
    APPLICATION = 3
    """Application webhooks are webhooks used with Interactions"""


class WebhookEventType(Enum):
    PING = 0
    """PING event sent to verify your Webhook Event URL is active"""
    EVENT = 1
    """Webhook event (details for event in event body object)"""

from datetime import datetime  # noqa: F401

from pydantic._internal._model_construction import ModelMetaclass
from pydantic import BaseModel

from plural.missing import Optional, Nullable  # noqa: F401

from .types import Snowflake

from .enums import (
    # Library Enums
    ApplicationCommandScope,
    CustomIdExtraType,
    # Shared
    ApplicationIntegrationType,
    Permission,
    # Application
    ApplicationFlag,
    EventWebhooksStatus,
    EventWebhooksType,
    MembershipState,
    # Attachment
    AttachmentFlag,
    # Channel
    ChannelFlag,
    ChannelType,
    ForumLayoutType,
    OverwriteType,
    SortOrderType,
    VideoQualityMode,
    # Component
    ButtonStyle,
    ComponentType,
    DefaultValueType,
    TextInputStyle,
    # Embed
    EmbedType,
    # Entitlement
    EntitlementType,
    # Event
    WebhookEventType,
    # Expression
    StickerFormatType,
    StickerType,
    # Guild
    DefaultMessageNotificationLevel,
    ExplicitContentFilterLevel,
    MFALevel,
    NSFWLevel,
    PremiumTier,
    SystemChannelFlag,
    VerificationLevel,
    # Interaction
    ApplicationCommandOptionType,
    ApplicationCommandType,
    InteractionCallbackType,
    InteractionContextType,
    InteractionType,
    # Member
    MemberFlag,
    # Message
    AllowedMentionType,
    MessageFlag,
    MessageType,
    # Poll
    PollLayoutType,
    # Role
    RoleFlag,
    # User
    PremiumType,
    UserFlag,
    # Webhook
    WebhookType,
)

from .models import (
    ActionRow,
    AllowedMentions,
    Application,
    ApplicationCommand,
    ApplicationCommandInteractionData,
    Attachment,
    AvatarDecorationData,
    Button,
    Channel,
    ChannelMention,
    Component,
    Embed,
    Emoji,
    Entitlement,
    Guild,
    Interaction,
    InteractionCallback,
    Member,
    Message,
    MessageComponent,
    MessageComponentInteractionData,
    Modal,
    ModalSubmitInteractionData,
    Poll,
    Reaction,
    Resolved,
    Role,
    SelectMenu,
    Sticker,
    StickerItem,
    Team,
    TextInput,
    User,
    Webhook,
    WebhookEvent,
)

from .commands import (
    insert_cmd_ref,
    message_command,
    slash_command,
    SlashCommandGroup,
)

from .components import (
    button,
    modal,
    string_select,
)


# ? sorted by category,
# ? then objects alphabetically,
# ? then enums alphabetically
__all__ = (  # noqa: RUF022
    # Library Functions and Classes
    'button',
    'insert_cmd_ref',
    'message_command',
    'modal',
    'slash_command',
    'SlashCommandGroup',
    'string_select',
    # Types
    'Snowflake',
    # Library Enums
    'ApplicationCommandScope',
    'CustomIdExtraType',
    # Shared Enums
    'ApplicationIntegrationType',
    'Permission',
    # Application
    'Application',
    'Team',
    'ApplicationFlag',
    'EventWebhooksStatus',
    'EventWebhooksType',
    'MembershipState',
    # Attachment
    'Attachment',
    'AttachmentFlag',
    # AvatarDecorationData
    'AvatarDecorationData',
    # Channel
    'Channel',
    'ChannelMention',
    'ChannelFlag',
    'ChannelType',
    'ForumLayoutType',
    'OverwriteType',
    'SortOrderType',
    'VideoQualityMode',
    # Command
    'ApplicationCommand',
    'InteractionCallback',
    # Component
    'ActionRow',
    'Button',
    'Component',
    'MessageComponent',
    'Modal',
    'SelectMenu',
    'TextInput',
    'ButtonStyle',
    'ComponentType',
    'DefaultValueType',
    'TextInputStyle',
    # Embed
    'Embed',
    'EmbedType',
    # Entitlement
    'Entitlement',
    'EntitlementType',
    # Event
    'WebhookEvent',
    'WebhookEventType',
    # Expression
    'Emoji',
    'Reaction',
    'Sticker',
    'StickerItem',
    'StickerFormatType',
    'StickerType',
    # Guild
    'Guild',
    'DefaultMessageNotificationLevel',
    'ExplicitContentFilterLevel',
    'MFALevel',
    'NSFWLevel',
    'PremiumTier',
    'SystemChannelFlag',
    'VerificationLevel',
    # Interaction
    'ApplicationCommandInteractionData',
    'Interaction',
    'MessageComponentInteractionData',
    'ModalSubmitInteractionData',
    'ApplicationCommandOptionType',
    'ApplicationCommandType',
    'InteractionCallbackType',
    'InteractionContextType',
    'InteractionType',
    # Member
    'Member',
    'MemberFlag',
    # Message
    'AllowedMentions',
    'Message',
    'AllowedMentionType',
    'MessageFlag',
    'MessageType',
    # Poll
    'Poll',
    'PollLayoutType',
    # Resolved
    'Resolved',
    # Role
    'Role',
    'RoleFlag',
    # User
    'User',
    'PremiumType',
    'UserFlag',
    # Webhook
    'Webhook',
    'WebhookType',
)

Interaction.model_rebuild(force=True)
ApplicationCommand.model_rebuild(force=True)

# ? handle missing imports, and the MISSING type
for model_name in __all__:
    model = globals().get(model_name)

    if not isinstance(model, ModelMetaclass):
        continue

    # ? it is the meta class but also still base model
    model: BaseModel

    model.model_rebuild(force=True)

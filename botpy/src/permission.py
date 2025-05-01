from typing import Self, NamedTuple
from enum import Flag

from .cache import Cache


class Permission(Flag):
    NONE = 0
    """No permissions"""
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

    @classmethod
    def all(cls) -> Self:
        result = cls(0)
        for perm in cls:
            result |= perm
        return result

    @classmethod
    async def for_member(
        cls,
        event: dict,
        debug_log: list[str],
        member_id: str
    ) -> Self:
        channel = await Cache.get(
            f'discord:channel:{event['channel_id']}'
        )

        guild = await Cache.get(
            f'discord:guild:{event['guild_id']}'
        )

        member = await Cache.get(
            f'discord:member:{event['guild_id']}:{member_id}'
        )

        if channel is None:
            debug_log.append('Channel not found in cache')
            return cls(0)

        if guild is None:
            debug_log.append('Guild not found in cache')
            return cls(0)

        if member is None:
            debug_log.append('Member not found in cache')
            return cls(0)

        if guild.data.get('owner_id') == str(member_id):
            return cls.all()

        roles = await guild.fetch_meta('roles')

        # ? everyone role as base
        permissions = next(
            Permission(int(role.data['permissions']))
            for role in roles
            if role.data.get('id') == guild.data.get('id')
        )

        for role in [
            role
            for role in roles
            if role.data.get('id') in
            member.data.get('roles', [])
        ]:
            permissions |= Permission(int(role.data['permissions']))

        if permissions & cls.ADMINISTRATOR:
            return cls.all()

        if channel.data.get('type') in {11, 12}:
            channel = await Cache.get(
                f'discord:channel:{channel.data.get("parent_id")}'
            )

            if channel is None:
                debug_log.append('Parent channel not found in cache')
                return cls(0)

        overwrites = {
            overwrite.id: overwrite
            for overwrite in [
                Overwrite(
                    id=data.get('id'),
                    type=data.get('type'),
                    allow=Permission(int(data.get('allow', 0))),
                    deny=Permission(int(data.get('deny', 0)))
                )
                for data in
                channel.data.get('permission_overwrites', [])
            ]
        }

        # ? @everyone first
        if (overwrite := overwrites.pop(guild.data.get('id'), None)) is not None:
            permissions &= ~overwrite.deny
            permissions |= overwrite.allow

        allow = Permission.NONE
        deny = Permission.NONE

        for role_id in member.data.get('roles', []):
            if (overwrite := overwrites.pop(role_id, None)) is not None:
                allow |= overwrite.allow
                deny |= overwrite.deny

        permissions &= ~deny
        permissions |= allow

        if (overwrite := overwrites.pop(member_id, None)) is not None:
            permissions &= ~overwrite.deny
            permissions |= overwrite.allow

        return permissions


class Overwrite(NamedTuple):
    id: str
    type: int
    allow: Permission
    deny: Permission

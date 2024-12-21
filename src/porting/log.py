from enum import StrEnum


class LogMessage(StrEnum):
    CREATED_GROUP = 'I: created group {group_name}'
    GROUP_EXISTS = 'I: group {group_name} already exists; skipping'
    CREATED_MEMBER = 'I: created member {member_name} in group {group_name}'
    MEMBER_EXISTS = 'E: member {member_name} already exists in group {group_name}; skipping'
    TOO_MANY_TAGS = 'E: member {member_name} has more than 15 proxy tags; only the first 15 will be imported'
    TAG_TOO_LONG = 'E: member {member_name} tag "{prefix}text{suffix}" is too long; skipping'
    TAG_NO_PREFIX_OR_SUFFIX = 'E: member {member_name} tag has no prefix or suffix; skipping'
    MEMBER_NAME_TOO_LONG = 'E: member name "{member_name}" is too long; skipping'
    GROUP_NAME_TOO_LONG = 'E: group name "{group_name}" is too long; skipping'
    AVATAR_FAILED = 'E: failed to download avatar for {object_type} {object_name}'
    GROUP_TAG_TOO_LONG = 'E: group "{group_name}" tag "{tag}" is too long; skipping'
    NOTHING_IMPORTED = 'E: nothing was imported'
    AVATAR_TOO_LARGE = 'E: avatar for {object_type} {object_name} is too large (max 8mb); skipping'
    IMAGE_LIMIT_EXCEEDED = 'E: image limit exceeded; only the first 1000 images will be imported'

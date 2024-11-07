from src.db import Group, Member, UserProxy, ApiKey, Latch, Message, Reply, DatalessImage
from pydantic import BaseModel, Field
from datetime import datetime


class ExportGroup(BaseModel):
    id: int
    name: str
    accounts: list[str]
    avatar: str | None
    channels: list[str]
    tag: str | None
    members: list[int]


class ExportProxyTag(BaseModel):
    prefix: str
    suffix: str
    regex: bool = False
    case_sensitive: bool = False


class ExportMember(BaseModel):
    id: int
    name: str
    description: str | None
    avatar: str | None
    proxy_tags: list[ExportProxyTag]
    group: int


class UserDataExport(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    groups: list[ExportGroup] = Field(default_factory=list)
    members: list[ExportMember] = Field(default_factory=list)


class CompleteRawExport(BaseModel):
    api_keys: list[ApiKey]
    groups: list[Group]
    members: list[Member]
    messages: list[Message]
    latches: list[Latch]
    userproxies: list[UserProxy]
    replies: list[Reply]
    images: list[DatalessImage]

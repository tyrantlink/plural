from __future__ import annotations
from .userproxy import UserProxyCommands
from .importer import ImportCommand
from .member import MemberCommands
from .group import GroupCommands
from .base import BaseCommands


class Commands(MemberCommands, GroupCommands, ImportCommand, UserProxyCommands, BaseCommands):
    ...

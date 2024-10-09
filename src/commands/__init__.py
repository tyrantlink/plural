from __future__ import annotations
from .importer import ImportCommand
from .member import MemberCommands
from .group import GroupCommands
from .base import BaseCommands


class Commands(MemberCommands, GroupCommands, ImportCommand, BaseCommands):
    ...

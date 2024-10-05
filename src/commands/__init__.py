from __future__ import annotations
from discord import slash_command, ApplicationContext, Option, message_command, InteractionContextType, Message, InputTextStyle
from src.helpers import CustomModal, send_error, send_success
import src.commands.autocomplete as autocomplete
from .importer import ImportCommand
from .member import MemberCommands
from discord.ui import InputText
from .group import GroupCommands
from .base import BaseCommands
from asyncio import gather


class Commands(MemberCommands, GroupCommands, ImportCommand, BaseCommands):
    ...

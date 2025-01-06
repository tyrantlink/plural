from src.core.auth import discord_key_validator
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from .discord import post__interaction
from src.discord import Interaction


router = APIRouter(prefix='/userproxy', include_in_schema=False)


@router.post(
    '/interaction',
    include_in_schema=False,
    dependencies=[Depends(discord_key_validator)])
async def post__interaction(
    interaction: Interaction
) -> Response:
    return await post__interaction(interaction)

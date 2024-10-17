from src.api.models.discord import Interaction, InteractionType
from fastapi.responses import JSONResponse
from fastapi import APIRouter

router = APIRouter(prefix='/userproxy', tags=['UserProxy'])

PONG = JSONResponse(content={'type': 1})


@router.post(
    '/interaction')
async def post__latch(
    payload: Interaction
) -> JSONResponse:
    if payload.type == InteractionType.PING:
        return PONG
    # return JSONResponse

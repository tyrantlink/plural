from datetime import timedelta

from fastapi import APIRouter, Security, Response
from orjson import dumps

from src.core.auth import TokenData, api_key_validator
from src.core.ratelimit import ratelimit
from src.core.route import name

from src.models import ApplicationModel

from src.docs import (
    application_response
)


router = APIRouter(prefix='/application', tags=['Applications'])


@router.get(
    '/',
    name='Get Current Application',
    description="""
    Get the current application""",
    responses={200: application_response})
@name('/members/:id')
@ratelimit(5, timedelta(seconds=30))
async def get__application(
    token: TokenData = Security(api_key_validator),  # noqa: B008
) -> Response:
    return Response(
        status_code=200,
        media_type='application/json',
        content=dumps(ApplicationModel.from_application(
            token.application
        ).model_dump(mode='json'))
    )

from fastapi.responses import Response
from fastapi import APIRouter

router = APIRouter(prefix='/userproxy', tags=['UserProxy'])


@router.post(
    '/interaction')
async def post__latch(
    data: dict
) -> Response:
    print(data)

    return Response()

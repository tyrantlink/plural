from fastapi.responses import JSONResponse
from fastapi import HTTPException, Query
from fastapi import APIRouter
from src.db import Message

router = APIRouter(prefix='/messages', tags=['Message'])


@router.get('/{message_id}')
async def get_message(
    message_id: int,
    only_check_existence: bool = Query(default=False)
) -> JSONResponse:
    message = await Message.find_one(
        {
            '$or':
            [
                {'original_id': message_id},
                {'proxy_id': message_id}
            ]
        }
    )

    if only_check_existence:
        return JSONResponse(
            content=message is not None
        )

    if message is None:
        raise HTTPException(status_code=404, detail='message not found')

    return JSONResponse(
        content=message.model_dump_json()
    )

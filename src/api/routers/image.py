from fastapi.responses import Response
from src.api.docs import image as docs
from beanie import PydanticObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from mimetypes import guess_type
from fastapi import APIRouter
from src.db import Image

router = APIRouter(prefix='/images', tags=['Image'])


@router.get(
    '/{image_id}',
    responses=docs.get__image)
async def get__image(image_id: str) -> Response:
    try:
        oid = PydanticObjectId(image_id.rsplit('.', 1)[0])
    except InvalidId:
        raise HTTPException(400, 'invalid image id')

    image = await Image.find_one({'_id': oid})

    if image is None:
        raise HTTPException(404, 'image not found')

    return Response(
        content=image.data,
        media_type=guess_type(image_id)[0]
    )

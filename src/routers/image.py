from fastapi import HTTPException, APIRouter
from fastapi.responses import Response
from beanie import PydanticObjectId
from src.docs import image as docs
from mimetypes import guess_type
from src.db import Image

router = APIRouter(prefix='/image', tags=['Image'])


@router.get(
    '/{image_id}.{extension}',
    responses=docs.get__image)
async def get__image(image_id: PydanticObjectId, extension: str) -> Response:
    image = await Image.find_one({'_id': image_id})

    if image is None:
        raise HTTPException(404, 'image not found')

    return Response(
        content=image.data,
        media_type=guess_type(f'{image_id}.{image.extension}')[0]
    )

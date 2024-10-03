from fastapi.responses import Response
from beanie import PydanticObjectId
from mimetypes import guess_type
from fastapi import APIRouter
from src.db import Image

router = APIRouter(prefix='/images', tags=['Image'])


@router.get('/{image_id}')
async def get_image(image_id: str) -> Response:
    try:
        oid = PydanticObjectId(image_id.rsplit('.', 1)[0])
    except ValueError:
        return Response(status_code=400)

    image = await Image.find_one({'_id': oid})

    if image is None:
        return Response(status_code=404)

    return Response(
        content=image.data,
        media_type=guess_type(image_id)[0]
    )

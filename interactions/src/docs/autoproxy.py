from beanie import PydanticObjectId

from plural.db.enums import AutoproxyMode

from src.models.autoproxy import AutoproxyModel, AutoproxyPutModel

from .base import Example, response, request


autoproxy_response = response(
    description='Autoproxy Found',
    model=AutoproxyModel,
    examples=[
        Example(
            name='Global Autoproxy',
            value=AutoproxyModel(
                user=PydanticObjectId('67cab28fe3188a0a7807c8f4'),
                guild=None,
                mode=AutoproxyMode.LATCH,
                member=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                ts=None
            ).model_dump(mode='json')),
        Example(
            name='Guild Autoproxy',
            value=AutoproxyModel(
                user=PydanticObjectId('67cab28fe3188a0a7807c8f4'),
                guild='844127424526680084',
                mode=AutoproxyMode.LATCH,
                member=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                ts=None
            ).model_dump(mode='json')),
        Example(
            name='Global Autoproxy (with expiration)',
            value=AutoproxyModel(
                user=PydanticObjectId('67cab28fe3188a0a7807c8f4'),
                guild=None,
                mode=AutoproxyMode.LATCH,
                member=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                ts='2026-05-29T13:33:07.749000'
            ).model_dump(mode='json')),
        Example(
            name='Global Autoproxy (without member)',
            value=AutoproxyModel(
                user=PydanticObjectId('67cab28fe3188a0a7807c8f4'),
                guild=None,
                mode=AutoproxyMode.LATCH,
                member=None,
                ts=None
            ).model_dump(mode='json')
        )
    ]
)


autoproxy_put_request = request([
    Example(
        name='Set Global Autoproxy',
        value=AutoproxyPutModel(
            guild=None,
            mode=AutoproxyMode.LATCH,
            member=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
            ts=None
        ).model_dump(mode='json')),
    Example(
        name='Set Global Autoproxy (with expiration)',
        value=AutoproxyPutModel(
            guild=None,
            mode=AutoproxyMode.LATCH,
            member=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
            ts='2026-05-29T13:33:07.749000'
        ).model_dump(mode='json')),
    Example(
        name='Set Guild Autoproxy',
        value=AutoproxyPutModel(
            guild='844127424526680084',
            mode=AutoproxyMode.LATCH,
            member=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
            ts=None
        ).model_dump(mode='json')),
    Example(
        name='Set Guild Autoproxy (with expiration)',
        value=AutoproxyPutModel(
            guild='844127424526680084',
            mode=AutoproxyMode.LATCH,
            member=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
            ts='2026-05-29T13:33:07.749000'
        ).model_dump(mode='json')
    )
])

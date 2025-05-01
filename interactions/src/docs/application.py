from beanie import PydanticObjectId

from plural.db.enums import ApplicationScope

from src.models.application import ApplicationModel

from .base import Example, response


application_response = response(
    description='Application Found',
    model=ApplicationModel,
    examples=[Example(
        name='Application',
        value=ApplicationModel(
            id=PydanticObjectId('67ed033e09e93d2165ffb428'),
            name='Test Application',
            description='Test Application',
            icon=None,
            developer='250797109022818305',
            scope=ApplicationScope.NONE,
            endpoint='',
            authorized_count=1
        ).model_dump(mode='json')
    )]
)

from beanie import PydanticObjectId

from src.models.group import GroupModel

from .base import Example, response

_examples = [
    Example(
        name='Basic Group',
        value=GroupModel(
            id=PydanticObjectId('67cab2a55f8b2e7fd3d27d06'),
            name='default',
            account=PydanticObjectId('67cab28fe3188a0a7807c8f4'),
            users={'815769382629277746': 0},
            avatar=None,
            channels=set(),
            tag=None,
            members={
                PydanticObjectId('6765429d5eaf2f525aeb8131'),
                PydanticObjectId('670f500e8773629a1410d85b'),
                PydanticObjectId('670f500e8773629a1410d859'),
                PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                PydanticObjectId('670f500e8773629a1410d85c'),
                PydanticObjectId('670f500e8773629a1410d85a'),
                PydanticObjectId('67653a581cebd303f7cf190b'),
                PydanticObjectId('67cab28fe3188a0a7807c8fe')}
        ).model_dump(mode='json')),
    Example(
        name='Restricted Group',
        value=GroupModel(
            id=PydanticObjectId('6712a0aca5ba2d14f562a660'),
            name='restrict_test',
            account=PydanticObjectId('67cab28fe3188a0a7807c8f4'),
            users={},
            avatar=None,
            channels={'1046826118696669229'},
            tag='restricted',
            members=set()
        ).model_dump(mode='json')
    )
]


group_response = response(
    description='Group Found',
    model=GroupModel,
    examples=_examples
)

multi_group_response = response(
    description='Groups Found',
    model=list[GroupModel],
    examples=[
        Example(
            name=example.name,
            value=[example.value],
            mimetype=example.mimetype)
        for example in _examples
    ]
)

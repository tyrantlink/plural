from beanie import PydanticObjectId

from src.models.message import MessageModel, AuthorModel

from .base import Example, response


message_response = response(
    description='Message Found',
    model=MessageModel,
    examples=[
        Example(
            name='Webhook proxy',
            value=MessageModel(
                original_id='1353206395104923681',
                proxy_id='1353206397420179466',
                author_id='250797109022818305',
                channel_id='1307354421394669608',
                member_id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                reason='Matched proxy tag ​`text`​`--steve`',
                webhook_id='1347606225851912263',
                reference_id=None,
                member=None
            ).model_dump(mode='json', exclude={'member'})),
        Example(
            name='Userproxy bot proxy',
            value=MessageModel(
                original_id='1353202123797430272',
                proxy_id='1353202124502073398',
                author_id='250797109022818305',
                channel_id='1292096869974937736',
                member_id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                reason='Matched proxy tag ​`text`​`--steve`',
                webhook_id=None,
                reference_id=None,
                member=None
            ).model_dump(mode='json', exclude={'member'})),
        Example(
            name='Userproxy command',
            value=MessageModel(
                original_id=None,
                proxy_id='1353212365616709693',
                author_id='250797109022818305',
                channel_id='1307354421394669608',
                member_id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                reason='Userproxy /proxy command',
                webhook_id=None,
                reference_id=None,
                member=None
            ).model_dump(mode='json', exclude={'member'})),
        Example(
            name='Webhook proxy (api)',
            value=MessageModel(
                original_id=None,
                proxy_id='1353206397420179466',
                author_id='250797109022818305',
                channel_id='1307354421394669608',
                member_id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                reason='Matched proxy tag ​`text`​`--steve`',
                webhook_id='1347606225851912263',
                reference_id=None,
                member=None
            ).model_dump(mode='json', exclude={'member'})),
        Example(
            name='Userproxy bot proxy (api)',
            value=MessageModel(
                original_id=None,
                proxy_id='1353202124502073398',
                author_id='250797109022818305',
                channel_id='1292096869974937736',
                member_id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                reason='Matched proxy tag ​`text`​`--steve`',
                webhook_id=None,
                reference_id=None,
                member=None
            ).model_dump(mode='json', exclude={'member'})),
        Example(
            name='?member=true',
            value=MessageModel(
                original_id='1353206395104923681',
                proxy_id='1353206397420179466',
                author_id='250797109022818305',
                channel_id='1307354421394669608',
                member_id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                reason='Matched proxy tag ​`text`​`--steve`',
                webhook_id='1347606225851912263',
                reference_id=None,
                member=AuthorModel(
                    id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                    name='steve',
                    pronouns='any/all',
                    bio='example bio',
                    birthday='01/01/2000',
                    color=16777065,
                    avatar_url='https://cdn.plural.gg/images/670f500e8773629a1410d859/142267ca260696d14ea7c6b99d2af140.webp',
                    supporter=False,
                    private=False
                ).model_dump(mode='json')
            ).model_dump(mode='json')),
        Example(
            name='?member=true (but member was deleted)',
            value=MessageModel(
                original_id='1353206395104923681',
                proxy_id='1353206397420179466',
                author_id='250797109022818305',
                channel_id='1307354421394669608',
                member_id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                reason='Matched proxy tag ​`text`​`--steve`',
                webhook_id='1347606225851912263',
                reference_id=None,
                member=None
            ).model_dump(mode='json')),
        Example(
            name='?member=true (Member is private)',
            value=MessageModel(
                original_id='1353206395104923681',
                proxy_id='1353206397420179466',
                author_id='250797109022818305',
                channel_id='1307354421394669608',
                member_id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                reason='Matched proxy tag ​`text`​`--steve`',
                webhook_id='1347606225851912263',
                reference_id=None,
                member=AuthorModel(
                    id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                    name='steve',
                    pronouns='',
                    bio='',
                    birthday='',
                    color=None,
                    avatar_url='https://cdn.plural.gg/images/670f500e8773629a1410d859/142267ca260696d14ea7c6b99d2af140.webp',
                    supporter=False,
                    private=True
                ).model_dump(mode='json')
            ).model_dump(mode='json')
        )
    ]
)


author_response = response(
    description='Message Author Found',
    model=AuthorModel,
    examples=[
        Example(
            name='Message Author',
            value=AuthorModel(
                id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                name='steve',
                pronouns='any/all',
                bio='example bio',
                birthday='01/01/2000',
                color=16777065,
                avatar_url='https://cdn.plural.gg/images/670f500e8773629a1410d859/142267ca260696d14ea7c6b99d2af140.webp',
                supporter=False,
                private=False
            ).model_dump(mode='json')),
        Example(
            name='Message Author (Private)',
            value=AuthorModel(
                id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                name='steve',
                pronouns='',
                bio='',
                birthday='',
                color=None,
                avatar_url='https://cdn.plural.gg/images/670f500e8773629a1410d859/142267ca260696d14ea7c6b99d2af140.webp',
                supporter=False,
                private=True
            ).model_dump(mode='json')
        )
    ]
)

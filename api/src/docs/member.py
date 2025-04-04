from beanie import PydanticObjectId

from src.models.member import MemberModel

from .base import Example, response


member_response = response(
    description='Member Found',
    model=MemberModel,
    examples=[
        Example(
            name='Member with Userproxy (No Token Scope)',
            value=MemberModel(
                id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                name='steve',
                meta='',
                pronouns='any/all',
                bio='example bio',
                birthday='01/01/2000',
                color=16777065,
                avatar='f873c5cff5608ff4952cfe8b80f1a86c',
                proxy_tags=[
                    MemberModel.ProxyTag(
                        id=PydanticObjectId('67cab28fe3188a0a7807c8fd'),
                        prefix='s;',
                        suffix='',
                        regex=False,
                        case_sensitive=False,
                        avatar=None),
                    MemberModel.ProxyTag(
                        id=PydanticObjectId('67cab28fe3188a0a7807c8fe'),
                        prefix='',
                        suffix='--steve',
                        regex=False,
                        case_sensitive=False,
                        avatar=None)],
                userproxy=MemberModel.UserProxy(
                    bot_id='1297857704512978984',
                    public_key='',
                    token='',
                    command='st',
                    guilds=['844127424526680084']),
                simplyplural_id=None
            ).model_dump(mode='json')),
        Example(
            name='Member with Userproxy (With Token Scope)',
            value=MemberModel(
                id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                name='steve',
                meta='',
                pronouns='any/all',
                bio='example bio',
                birthday='01/01/2000',
                color=16777065,
                avatar='f873c5cff5608ff4952cfe8b80f1a86c',
                proxy_tags=[
                    MemberModel.ProxyTag(
                        id=PydanticObjectId('67cab28fe3188a0a7807c8fd'),
                        prefix='s;',
                        suffix='',
                        regex=False,
                        case_sensitive=False,
                        avatar=None),
                    MemberModel.ProxyTag(
                        id=PydanticObjectId('67cab28fe3188a0a7807c8fe'),
                        prefix='',
                        suffix='--steve',
                        regex=False,
                        case_sensitive=False,
                        avatar=None)],
                userproxy=MemberModel.UserProxy(
                    bot_id='1297857704512978984',
                    public_key='267b5eb2ebdbe0620160b0cd99630420cce9f1fa271feaf16bee8a20988dc682',
                    token='MTI5Nzg1NzcwNDUxMjk3ODk4NA.GYv_Xp.mM-h1AoambBtN4JApr0NPQT1twx2fo-kuKvH0o',
                    command='st',
                    guilds=['844127424526680084']),
                simplyplural_id=None
            ).model_dump(mode='json')),
        Example(
            name='Member without Userproxy',
            value=MemberModel(
                id=PydanticObjectId('67cab2a55f8b2e7fd3d27d0c'),
                name='steve',
                meta='',
                pronouns='any/all',
                bio='example bio',
                birthday='01/01/2000',
                color=16777065,
                avatar='f873c5cff5608ff4952cfe8b80f1a86c',
                proxy_tags=[
                    MemberModel.ProxyTag(
                        id=PydanticObjectId('67cab28fe3188a0a7807c8fd'),
                        prefix='s;',
                        suffix='',
                        regex=False,
                        case_sensitive=False,
                        avatar=None),
                    MemberModel.ProxyTag(
                        id=PydanticObjectId('67cab28fe3188a0a7807c8fe'),
                        prefix='',
                        suffix='--steve',
                        regex=False,
                        case_sensitive=False,
                        avatar=None)],
                userproxy=None,
                simplyplural_id=None
            ).model_dump(mode='json')
        )
    ]
)

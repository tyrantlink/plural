from beanie import PydanticObjectId

from plural.db.enums import ReplyFormat, PaginationStyle, SupporterTier

from src.models.usergroup import UsergroupModel

from .base import Example, response


usergroup_response = response(
    description='User Found',
    model=UsergroupModel,
    examples=[Example(
        name='Usergroup',
        value=UsergroupModel(
            id=PydanticObjectId('67cab28fe3188a0a7807c8f4'),
            users=[
                '250797109022818305',
                '815769382629277746'],
            config=UsergroupModel.Config(
                account_tag='',
                reply_format=ReplyFormat.INLINE,
                ping_replies=False,
                groups_in_autocomplete=True,
                pagination_style=PaginationStyle.REM_AND_RAM,
                roll_embed=False,
                tag_format='{tag}',
                pronoun_format='({pronouns})',
                display_name_order=[0, 1, 2],
                private_member_info=False),
            userproxy_config=UsergroupModel.UserproxyConfig(
                reply_format=ReplyFormat.INLINE,
                dm_reply_format=ReplyFormat.INLINE,
                ping_replies=False,
                include_tag=True,
                include_pronouns=True,
                attachment_count=1,
                self_hosted=False,
                required_message_parameter=False,
                name_in_reply_command=True,
                include_attribution=True),
            data=UsergroupModel.Data(
                supporter_tier=SupporterTier.DEVELOPER,
                image_limit=5000,
                sp_token=None,
                sp_id=None
            )
        )
    )]
)

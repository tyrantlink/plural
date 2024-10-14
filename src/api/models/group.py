from pydantic import BaseModel, Field
from beanie import PydanticObjectId

# {
#     "id": "67018b8f74900a4cd3235555",
#     "name": "test",
#     "accounts": [
#         250797109022818300
#     ],
#     "avatar": null,
#     "channels": [],
#     "tag": null,
#     "members": [
#         "67018b8f74900a4cd3235556"
#     ]
# }


class GroupModel(BaseModel):
    id: PydanticObjectId = Field(description='the id of the group')
    name: str = Field(
        description='the name of the group',
        min_length=1, max_length=32)
    accounts: list[int] = Field(description='the accounts of the group')
    avatar: PydanticObjectId | None = Field(
        description='the avatar uuid of the group'
    )
    channels: list[int] = Field(description='the channels of the group')
    tag: str | None = Field(
        description='the tag of the group'
    )
    members: list[PydanticObjectId] = Field(
        description='the members of the group'
    )


class GroupUpdateModel(BaseModel):
    name: str = Field(
        None, description='the name of the group', min_length=1, max_length=32)
    avatar: PydanticObjectId | None = Field(
        None,
        description='the avatar uuid of the group'
    )
    channels: list[int] = Field(
        None,
        description='the channels of the group'
    )
    tag: str | None = Field(
        None,
        description='the tag of the group'
    )


class CreateGroupModel(BaseModel):
    name: str = Field(
        description='the name of the group',
        min_length=1, max_length=32)
    avatar: PydanticObjectId | None = Field(
        None,
        description='the avatar uuid of the group'
    )
    channels: list[int] = Field(description='the channels of the group')
    tag: str | None = Field(
        None,
        description='the tag of the group'
    )

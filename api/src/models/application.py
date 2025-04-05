from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator
from beanie import PydanticObjectId

from plural.db.enums import ApplicationScope  # noqa: TC002

if TYPE_CHECKING:
    from plural.db import Application


class ApplicationModel(BaseModel):
    @field_validator('developer', mode='before')
    @classmethod
    def validate_developer(cls, developer: str | int) -> str:
        return str(developer)

    id: PydanticObjectId = Field(
        default_factory=PydanticObjectId,
        description='the id of the application')
    name: str = Field(
        description='the name of the application')
    description: str = Field(
        description='the description of the application')
    icon: str | None = Field(
        description='the icon hash of the application')
    developer: str = Field(
        description='the user id of the developer')
    scope: ApplicationScope = Field(
        description='the scope of the application')
    endpoint: str = Field(
        description='the endpoint of the application')
    authorized_count: int = Field(
        description='the number of users who have authorized the application'
    )

    @classmethod
    def from_application(
        cls,
        application: Application
    ) -> Application:
        return cls(**application.model_dump(mode='json'))

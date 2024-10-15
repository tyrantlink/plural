from datetime import timedelta
from beanie import Document
from pydantic import Field


class Webhook(Document):
    def __eq__(self, other: object) -> bool:
        return isinstance(other, type(self)) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    class Settings:
        name = 'webhooks'
        use_cache = True
        validate_on_save = True
        use_state_management = True
        cache_expiration_time = timedelta(minutes=30)

    id: int = Field(
        description='channel id of the webhook'
    )
    guild: int | None = Field(
        None,  # ? only setting to none during migration from not having guild
        description='guild id of the webhook'
    )
    url: str = Field(description='the url of the webhook')

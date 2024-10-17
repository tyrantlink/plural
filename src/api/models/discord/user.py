from pydantic import BaseModel
from typing import Any


class User(BaseModel):
    id: str
    username: str
    discriminator: str
    global_name: str | None = None
    avatar: str | None = None
    public_flags: int
    avatar_decoration_data: dict | None = None
    clan: Any | None = None  # ? not listed in the discord api docs

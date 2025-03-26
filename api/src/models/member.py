from pydantic import BaseModel


class UserproxySync(BaseModel):
    author_id: int
    patch_filter: set[str]

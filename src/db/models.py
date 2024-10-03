from pydantic import BaseModel


class ProxyTag(BaseModel):
    prefix: str
    suffix: str
    regex: bool

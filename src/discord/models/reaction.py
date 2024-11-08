from .base import RawBaseModel
from .emoji import Emoji


__all__ = (
    'CountDetails',
    'Reaction',
)


class CountDetails(RawBaseModel):
    burst: int
    normal: int


class Reaction(RawBaseModel):
    count: int
    count_details: CountDetails
    me: bool
    me_burst: bool
    emoji: Emoji
    burst_colors: list[int]

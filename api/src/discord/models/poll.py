from __future__ import annotations

from typing import TYPE_CHECKING

from src.discord.models.base import RawBaseModel

if TYPE_CHECKING:
    from datetime import datetime

    from plural.missing import Optional, Nullable

    from src.discord.enums import PollLayoutType

    from .expression import Emoji


__all__ = (
    'Poll',
)


class Poll(RawBaseModel):
    class Media(RawBaseModel):
        text: Optional[str]
        """The text of the field"""
        emoji: Optional[Emoji]
        """The emoji of the field"""

    class Answer(RawBaseModel):
        answer_id: Optional[int]
        """The ID of the answer"""
        poll_media: Poll.Media
        """The data of the answer"""

    class AnswerCount(RawBaseModel):
        id: int
        """The `answer_id`"""
        count: int
        """The number of votes for this answer"""
        me_voted: bool
        """Whether the current user voted for this answer"""

    class Results(RawBaseModel):
        is_finalized: bool
        """Whether the votes have been precisely counted"""
        answer_counts: list[Poll.AnswerCount]
        """The counts for each answer"""

    question: Poll.Media
    """The question of the poll. Only `text` is supported."""
    answers: list[Poll.Answer]
    """Each of the answers available in the poll."""
    expiry: Nullable[datetime]
    """The time when the poll ends."""
    allow_multiselect: bool
    """Whether a user can select multiple answers"""
    layout_type: PollLayoutType
    """The layout type of the poll"""
    results: Optional[Poll.Results]
    """The results of the poll"""

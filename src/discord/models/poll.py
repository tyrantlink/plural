from datetime import datetime, timezone
from pydantic import model_validator
from .enums import PollLayoutType
from .base import RawBaseModel
from .emoji import Emoji


__all__ = ('Poll',)


class PollMedia(RawBaseModel):
    text: str | None = None
    emoji: Emoji | None = None


class PollAnswer(RawBaseModel):
    answer_id: int
    poll_media: PollMedia


class PollAnswerCount(RawBaseModel):
    id: int
    count: int
    me_voted: bool


class PollResults(RawBaseModel):
    is_finalized: bool
    answer_counts: list[PollAnswerCount]


class Poll(RawBaseModel):
    question: PollMedia
    answers: list[PollAnswer]
    expiry: datetime | None
    duration: int
    allow_multiselect: bool
    layout_type: PollLayoutType
    results: PollResults | None = None

    @model_validator(mode='before')
    @classmethod
    def fill_duration(cls, data: dict) -> dict:
        if data.get('expiry') is not None:
            data['duration'] = round((
                datetime.fromisoformat(
                    data['expiry']
                ) - datetime.now(timezone.utc)
            ).total_seconds() / 60 / 60)

        return data

    def as_create_request(self) -> dict:
        return {
            'question': self.question.model_dump(mode='json'),
            'answers': [answer.model_dump(mode='json') for answer in self.answers],
            'duration': self.duration,
            'allow_multiselect': self.allow_multiselect,
            'layout_type': self.layout_type.value
        }

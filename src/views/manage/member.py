from .base import BaseManageView
from src.models import ManageTargetType


class MemberManageView(BaseManageView):
    target_type = ManageTargetType.MEMBER

    # def __post_init__(self):
    #     ...

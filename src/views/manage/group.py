from .base import BaseManageView
from src.models import ManageTargetType


class GroupManageView(BaseManageView):
    target_type = ManageTargetType.GROUP

    # def __post_init__(self):
    #     ...

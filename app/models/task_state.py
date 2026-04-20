from __future__ import annotations

from enum import Enum


class TaskStatus(str, Enum):
    QUEUED = "QUEUED"
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"

    @classmethod
    def terminal(cls) -> set["TaskStatus"]:
        return {cls.SUCCESS, cls.FAILURE}

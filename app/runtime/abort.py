import asyncio
from enum import Enum
from typing import Optional


class AbortReason(str, Enum):
    USER_INTERRUPT = "user_interrupt"
    RUNTIME_ERROR = "runtime_error"
    TASK_CANCELLED = "task_cancelled"


class RunAbortController:
    def __init__(self) -> None:
        self._abort_event = asyncio.Event()
        self.reason: Optional[AbortReason] = None
        self.message: Optional[str] = None

    def clear(self) -> None:
        self._abort_event = asyncio.Event()
        self.reason = None
        self.message = None

    def request_abort(self, reason: AbortReason, message: Optional[str] = None) -> None:
        if self.reason is None:
            self.reason = reason
            self.message = message
        self._abort_event.set()

    def is_aborted(self) -> bool:
        return self._abort_event.is_set()

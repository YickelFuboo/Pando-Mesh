from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Optional
from app.runtime.abort import RunAbortController
from app.runtime.message import Message

NotifyUserCallback = Callable[[Message], Awaitable[None]]
PushHistoryMessageCallback = Callable[[Message], Awaitable[None]]


@dataclass
class AgentContext:
    user_id: str = ""
    session_id: str = ""
    workspace_path: str = ""
    requirement_id: str = ""
    params: dict[str, Any] = field(default_factory=dict)

    def params_dict(self) -> dict[str, Any]:
        return dict(self.params)


@dataclass
class RuntimeContext:
    abort_controller: Optional[RunAbortController] = None
    params: dict[str, Any] = field(default_factory=dict)
    actor_id: str = ""
    notify_user_callback: Optional[NotifyUserCallback] = field(default=None, compare=False, repr=False)
    push_history_callback: Optional[PushHistoryMessageCallback] = field(default=None, compare=False, repr=False)

    def is_aborted(self) -> bool:
        ctrl = self.abort_controller
        return ctrl is not None and ctrl.is_aborted()

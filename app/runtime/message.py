from datetime import datetime
import json
import re
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Function(BaseModel):
    name: str
    arguments: Dict[str, Any]

    def model_dump(self) -> Dict[str, Any]:
        return {"name": self.name, "arguments": self.arguments}


class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: Function

    def model_dump(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "function": self.function.model_dump(),
        }


def _strip_ansi(text: str) -> str:
    if not text:
        return text
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


class Message(BaseModel):
    role: Role
    content: str = ""
    tool_calls: Optional[List[ToolCall]] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    create_time: Optional[datetime] = None

    @property
    def is_tool_result(self) -> bool:
        return self.role == Role.TOOL and self.name is not None and self.tool_call_id is not None

    @property
    def is_assistant_tool_calls(self) -> bool:
        return self.role == Role.ASSISTANT and bool(self.tool_calls)

    @classmethod
    def user_message(cls, content: str) -> "Message":
        return cls(role=Role.USER, content=content, create_time=datetime.now())

    @classmethod
    def assistant_message(cls, content: Optional[str] = None) -> "Message":
        return cls(role=Role.ASSISTANT, content=content or "", create_time=datetime.now())

    @classmethod
    def tool_result_message(
        cls,
        content: str,
        name: str,
        tool_call_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Message":
        return cls(
            role=Role.TOOL,
            content=content,
            name=name,
            tool_call_id=tool_call_id,
            metadata=metadata,
            create_time=datetime.now(),
        )

    def to_user_message(self) -> Dict[str, Any]:
        if self.is_tool_result:
            payload = {
                "kind": "tool_result",
                "tool_name": (self.name or "") + " Executed",
                "tool_result": _strip_ansi(self.content or ""),
            }
            content = json.dumps(payload, ensure_ascii=False)
        elif self.is_assistant_tool_calls:
            tools = [
                {"tool_name": tc.function.name, "tool_params": dict(tc.function.arguments or {})}
                for tc in (self.tool_calls or [])
            ]
            content = json.dumps({"kind": "tool_call", "tools": tools, "text": self.content or ""}, ensure_ascii=False)
        else:
            content = self.content or ""
        return {
            "role": self.role.value,
            "content": content,
            "create_time": (self.create_time or datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
        }

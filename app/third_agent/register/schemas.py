from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.third_agent.register.types import AgentKind


class AgentRegisterRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    name: str = ""
    kind: str = AgentKind.CLAUDE_CODE_CLI.value
    description: str = ""
    executor_template: Dict[str, Any] = Field(default_factory=dict)
    session_config: Dict[str, Any] = Field(default_factory=dict)
    history_config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    kind: Optional[str] = None
    description: Optional[str] = None
    executor_template: Optional[Dict[str, Any]] = None
    session_config: Optional[Dict[str, Any]] = None
    history_config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None

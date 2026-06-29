from dataclasses import dataclass, field
from typing import Any, Dict
from app.register.executor_config import extract_history_config, extract_session_config, normalize_executor_template
from app.register.types import AgentKind


@dataclass
class AgentRegistration:
    """Agent 注册元数据；executor_template 为唯一执行配置源。"""
    agent_id: str
    name: str
    kind: AgentKind
    description: str = ""
    executor_template: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    builtin: bool = False

    def to_storage_dict(self) -> Dict[str, Any]:
        payload = {
            "agent_id": self.agent_id,
            "name": self.name,
            "kind": self.kind.value,
            "description": self.description,
            "executor_template": dict(self.executor_template),
            "enabled": self.enabled,
        }
        if self.builtin:
            payload["builtin"] = True
        return payload

    def to_api_dict(self) -> Dict[str, Any]:
        payload = self.to_storage_dict()
        if str(self.executor_template.get("kind") or "").strip().lower() == "cli":
            payload["session_config"] = extract_session_config(self.executor_template)
            payload["history_config"] = extract_history_config(self.executor_template)
        else:
            payload["session_config"] = {}
            payload["history_config"] = {}
        return payload

    @classmethod
    def from_storage_dict(cls, raw: Dict[str, Any]) -> "AgentRegistration":
        kind_raw = str(raw.get("kind") or AgentKind.NATIVE.value).strip().lower()
        try:
            kind = AgentKind(kind_raw)
        except ValueError:
            kind = AgentKind.NATIVE
        executor = normalize_executor_template(
            dict(raw.get("executor_template") or {}),
            dict(raw.get("session_config") or {}),
            dict(raw.get("history_config") or {}),
        )
        return cls(
            agent_id=str(raw.get("agent_id") or "").strip(),
            name=str(raw.get("name") or "").strip(),
            kind=kind,
            description=str(raw.get("description") or "").strip(),
            executor_template=executor,
            enabled=bool(raw.get("enabled", True)),
            builtin=bool(raw.get("builtin", False)),
        )

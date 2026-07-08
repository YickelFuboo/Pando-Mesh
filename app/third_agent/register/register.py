from typing import Dict, List, Optional
from app.third_agent.register.defaults import default_template_for_kind, load_factory_agent, parse_agent_kind
from app.third_agent.register.models import AgentRegistration
from app.third_agent.register.store import AgentStore
from app.third_agent.register.types import AgentKind
from app.third_agent.register.utils import (
    extract_history_config,
    extract_session_config,
    normalize_executor_template,
)


class AgentRegistry:
    """Agent 注册服务：出厂默认见 data/agents/_defaults/；运行时见 data/agents/*.json。"""

    def __init__(self, store: Optional[AgentStore] = None) -> None:
        self._store = store or AgentStore()
        self._agents: Dict[str, AgentRegistration] = self._store.load_all()

    @property
    def store(self) -> AgentStore:
        return self._store

    def reload(self) -> None:
        self._agents = self._store.load_all()

    def list(self, *, enabled_only: bool = True) -> List[AgentRegistration]:
        agents = list(self._agents.values())
        if enabled_only:
            agents = [a for a in agents if a.enabled]
        return sorted(agents, key=lambda a: a.agent_id)

    def get(self, agent_id: str) -> Optional[AgentRegistration]:
        return self._agents.get((agent_id or "").strip())

    def is_factory_modified(self, agent_id: str) -> bool:
        return self._store.is_factory_modified(agent_id)

    def default_template(self, kind: str) -> Dict[str, object]:
        return default_template_for_kind(kind, self._store.data_root)

    def register(
        self,
        *,
        agent_id: str,
        name: str = "",
        kind: str = AgentKind.CLAUDE_CODE_CLI.value,
        description: str = "",
        executor_template: Optional[Dict[str, object]] = None,
        session_config: Optional[Dict[str, object]] = None,
        history_config: Optional[Dict[str, object]] = None,
        enabled: bool = True,
    ) -> AgentRegistration:
        aid = (agent_id or "").strip()
        if not aid:
            raise ValueError("agent_id 不能为空")
        if aid in self._agents:
            raise ValueError(f"Agent 已存在: {aid}")
        agent_kind = parse_agent_kind(kind)
        executor = normalize_executor_template(
            dict(executor_template or {}),
            dict(session_config or {}),
            dict(history_config or {}),
        )
        registration = AgentRegistration(
            agent_id=aid,
            name=(name or aid).strip() or aid,
            kind=agent_kind,
            description=(description or "").strip(),
            executor_template=executor,
            enabled=bool(enabled),
            builtin=False,
        )
        self._agents[aid] = registration
        self._store.save(registration)
        return registration

    def update(
        self,
        agent_id: str,
        *,
        name: Optional[str] = None,
        kind: Optional[str] = None,
        description: Optional[str] = None,
        executor_template: Optional[Dict[str, object]] = None,
        session_config: Optional[Dict[str, object]] = None,
        history_config: Optional[Dict[str, object]] = None,
        enabled: Optional[bool] = None,
    ) -> Optional[AgentRegistration]:
        reg = self.get(agent_id)
        if reg is None:
            return None
        next_kind = parse_agent_kind(kind) if kind is not None else reg.kind
        base_executor = dict(executor_template) if executor_template is not None else dict(reg.executor_template)
        next_session = dict(session_config) if session_config is not None else None
        next_history = dict(history_config) if history_config is not None else None
        if next_session is None and next_history is None:
            next_executor = base_executor
        else:
            if next_session is None:
                next_session = extract_session_config(base_executor)
            if next_history is None:
                next_history = extract_history_config(base_executor)
            next_executor = normalize_executor_template(base_executor, next_session, next_history)
        updated = AgentRegistration(
            agent_id=reg.agent_id,
            name=(name.strip() if name is not None else reg.name) or reg.agent_id,
            kind=next_kind,
            description=description.strip() if description is not None else reg.description,
            executor_template=next_executor,
            enabled=reg.enabled if enabled is None else bool(enabled),
            builtin=reg.builtin,
        )
        self._agents[reg.agent_id] = updated
        self._store.save(updated)
        return updated

    def unregister(self, agent_id: str) -> bool:
        reg = self.get(agent_id)
        if reg is None or reg.builtin:
            return False
        del self._agents[reg.agent_id]
        return self._store.delete(reg.agent_id)

    def reset_builtin(self, agent_id: str) -> Optional[AgentRegistration]:
        aid = (agent_id or "").strip()
        reg = self.get(aid)
        if reg is None or not reg.builtin:
            return None
        self._store.reset_factory(aid)
        fresh = load_factory_agent(aid, self._store.data_root)
        self._agents[aid] = fresh
        return fresh

    def catalog_text(self) -> str:
        lines = []
        for agent in self.list():
            lines.append(
                f"- {agent.agent_id}: {agent.name} — {agent.description}（kind={agent.kind.value}）"
            )
        return "\n".join(lines)

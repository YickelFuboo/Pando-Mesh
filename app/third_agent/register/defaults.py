"""Agent 出厂默认：data/agents/_defaults/ 为出厂默认值（git 跟踪）。"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.config.paths import DEFAULT_DATA_DIR
from app.config.settings import settings
from app.third_agent.register.models import AgentRegistration
from app.third_agent.register.types import AgentKind

FACTORY_DIR_NAME = "_defaults"


def agents_dir(data_root: Optional[Path] = None) -> Path:
    base = data_root or settings.data_dir
    return base / "agents"


def factory_dir(data_root: Optional[Path] = None) -> Path:
    return agents_dir(data_root) / FACTORY_DIR_NAME


def shipped_factory_dir() -> Path:
    return DEFAULT_DATA_DIR / "agents" / FACTORY_DIR_NAME


def resolve_factory_dir(data_root: Optional[Path] = None) -> Path:
    runtime = factory_dir(data_root)
    if any(runtime.glob("*.json")):
        return runtime
    shipped = shipped_factory_dir()
    if shipped.is_dir() and any(shipped.glob("*.json")):
        return shipped
    return runtime


def parse_agent_kind(kind: str) -> AgentKind:
    try:
        return AgentKind(str(kind or AgentKind.CLAUDE_CODE_CLI.value).strip().lower())
    except ValueError as e:
        raise ValueError(f"未知 Agent 类型: {kind}") from e


def factory_agent_ids(data_root: Optional[Path] = None) -> frozenset[str]:
    root = resolve_factory_dir(data_root)
    return frozenset(path.stem for path in sorted(root.glob("*.json")))


def _load_factory_raw(agent_id: str, data_root: Optional[Path] = None) -> Dict[str, Any]:
    path = resolve_factory_dir(data_root) / f"{agent_id.strip()}.json"
    if not path.is_file():
        raise ValueError(f"出厂 Agent 不存在: {agent_id}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"出厂 Agent 配置无效: {agent_id}")
    return raw


def load_factory_agent(agent_id: str, data_root: Optional[Path] = None) -> AgentRegistration:
    reg = AgentRegistration.from_storage_dict(_load_factory_raw(agent_id, data_root))
    if reg.agent_id not in factory_agent_ids(data_root):
        raise ValueError(f"出厂 Agent 不存在: {agent_id}")
    return reg


def list_factory_agents(data_root: Optional[Path] = None) -> List[AgentRegistration]:
    return [load_factory_agent(aid, data_root) for aid in sorted(factory_agent_ids(data_root))]


def default_template_for_kind(kind: str, data_root: Optional[Path] = None) -> Dict[str, Any]:
    agent_kind = parse_agent_kind(kind)
    for agent in list_factory_agents(data_root):
        if agent.kind == agent_kind:
            return dict(agent.executor_template)
    raise ValueError(f"无出厂 Agent 默认模板: {agent_kind.value}")

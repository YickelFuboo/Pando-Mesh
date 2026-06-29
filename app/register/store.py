import json
import logging
from dataclasses import replace
from pathlib import Path
from typing import Dict, Optional
from app.config.settings import settings
from app.register.models import AgentRegistration
from app.register.seed import builtin_agent_ids, default_agents

logger = logging.getLogger(__name__)

LEGACY_REGISTRY_FILE = "registry.json"


def agents_dir(root: Optional[Path] = None) -> Path:
    base = root or settings.data_dir
    return base / "agents"


class AgentStore:
    """Agent 持久化：内置默认来自 seed.py；data/agents/{id}.json 仅存用户覆盖或自定义 Agent。"""

    def __init__(self, root: Optional[Path] = None) -> None:
        self._root = agents_dir(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._builtin_ids = builtin_agent_ids()

    def agent_path(self, agent_id: str) -> Path:
        return self._root / f"{agent_id.strip()}.json"

    def has_override(self, agent_id: str) -> bool:
        return self.agent_path(agent_id).is_file()

    def load_all(self) -> Dict[str, AgentRegistration]:
        self._migrate_legacy_registry()
        agents = {agent.agent_id: agent for agent in default_agents()}
        for path in sorted(self._root.glob("*.json")):
            if path.stem.startswith("registry"):
                continue
            overlay = self._read_file(path)
            if overlay is None:
                continue
            aid = overlay.agent_id
            if aid in self._builtin_ids:
                agents[aid] = replace(overlay, agent_id=aid, builtin=True)
            else:
                agents[aid] = replace(overlay, builtin=False)
        return agents

    def save(self, registration: AgentRegistration) -> None:
        path = self.agent_path(registration.agent_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(registration.to_storage_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def delete(self, agent_id: str) -> bool:
        path = self.agent_path(agent_id)
        if not path.is_file():
            return False
        path.unlink()
        return True

    def reset_builtin(self, agent_id: str) -> bool:
        aid = (agent_id or "").strip()
        if aid not in self._builtin_ids:
            return False
        return self.delete(aid)

    def _read_file(self, path: Path) -> Optional[AgentRegistration]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("跳过无效 Agent 文件 %s: %s", path, e)
            return None
        if not isinstance(raw, dict):
            return None
        reg = AgentRegistration.from_storage_dict(raw)
        if not reg.agent_id:
            return None
        return reg

    def _migrate_legacy_registry(self) -> None:
        legacy = self._root / LEGACY_REGISTRY_FILE
        if not legacy.is_file():
            return
        try:
            raw = json.loads(legacy.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("迁移旧 registry.json 失败: %s", e)
            return
        items = raw if isinstance(raw, list) else raw.get("agents") or []
        if not isinstance(items, list):
            return
        migrated = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            reg = AgentRegistration.from_storage_dict(item)
            if not reg.agent_id:
                continue
            target = self.agent_path(reg.agent_id)
            if target.is_file():
                continue
            self.save(reg)
            migrated += 1
        overrides = raw.get("overrides") if isinstance(raw, dict) else {}
        if isinstance(overrides, dict):
            for agent_id, patch in overrides.items():
                if not isinstance(patch, dict) or "enabled" not in patch:
                    continue
                aid = str(agent_id).strip()
                if aid not in self._builtin_ids:
                    continue
                base = next(a for a in default_agents() if a.agent_id == aid)
                enabled = bool(patch["enabled"])
                if enabled == base.enabled:
                    continue
                self.save(replace(base, enabled=enabled))
        backup = legacy.with_suffix(".json.bak")
        try:
            legacy.rename(backup)
            logger.info("已迁移 %s 个 Agent 覆盖文件，旧 registry 备份为 %s", migrated, backup.name)
        except OSError:
            logger.info("已迁移 %s 个 Agent 覆盖文件", migrated)

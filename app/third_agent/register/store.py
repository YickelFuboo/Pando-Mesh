import json
import logging
import shutil
from dataclasses import replace
from pathlib import Path
from typing import Dict, Optional
from app.config.paths import DEFAULT_DATA_DIR
from app.config.settings import settings
from app.third_agent.register.defaults import (
    agents_dir,
    factory_agent_ids,
    factory_dir,
    list_factory_agents,
    load_factory_agent,
    shipped_factory_dir,
)
from app.third_agent.register.models import AgentRegistration

logger = logging.getLogger(__name__)

LEGACY_REGISTRY_FILE = "registry.json"


class AgentStore:
    """Agent 存储：_defaults 为出厂目录，agents/*.json 为运行时配置。"""

    def __init__(self, data_root: Optional[Path] = None) -> None:
        self._data_root = data_root or settings.data_dir
        self._root = agents_dir(self._data_root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._sync_factory_catalog()
        self._factory_ids = factory_agent_ids(self._data_root)

    @property
    def data_root(self) -> Path:
        return self._data_root

    def agent_path(self, agent_id: str) -> Path:
        return self._root / f"{agent_id.strip()}.json"

    def is_factory_modified(self, agent_id: str) -> bool:
        aid = (agent_id or "").strip()
        if aid not in self._factory_ids:
            return False
        runtime = self._read_file(self.agent_path(aid))
        if runtime is None:
            return False
        try:
            factory = load_factory_agent(aid, self._data_root)
        except ValueError:
            return True
        return runtime.to_storage_dict() != factory.to_storage_dict()

    def load_all(self) -> Dict[str, AgentRegistration]:
        self._migrate_legacy_registry()
        self._ensure_runtime_agents()
        agents: Dict[str, AgentRegistration] = {}
        for path in sorted(self._root.glob("*.json")):
            if path.stem.startswith("registry"):
                continue
            reg = self._read_file(path)
            if reg is None:
                continue
            aid = reg.agent_id
            builtin = aid in self._factory_ids
            agents[aid] = replace(reg, agent_id=aid, builtin=builtin)
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

    def reset_factory(self, agent_id: str) -> bool:
        aid = (agent_id or "").strip()
        if aid not in self._factory_ids:
            return False
        self.save(load_factory_agent(aid, self._data_root))
        return True

    def _sync_factory_catalog(self) -> None:
        target = factory_dir(self._data_root)
        shipped = shipped_factory_dir()
        if not shipped.is_dir():
            return
        target.mkdir(parents=True, exist_ok=True)
        for path in sorted(shipped.glob("*.json")):
            dest = target / path.name
            if not dest.is_file():
                shutil.copy2(path, dest)

    def _ensure_runtime_agents(self) -> None:
        for aid in sorted(self._factory_ids):
            if self.agent_path(aid).is_file():
                continue
            self.save(load_factory_agent(aid, self._data_root))

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
                if aid not in self._factory_ids:
                    continue
                base = next(a for a in list_factory_agents(self._data_root) if a.agent_id == aid)
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

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.config.paths import resolve_data_dir
from app.config.settings import settings
from app.graph.plan_graph import (
    PLAN_GRAPH_METADATA_KEY,
    DirectExecGraph,
    PlanGraphState,
)
from app.session.plan_mode import normalize_plan_mode


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class WorkflowRecord:
    workflow_id: str
    name: str = ""
    description: str = ""
    workspace_path: str = ""
    requirement_id: str = ""
    plan_mode: str = "template"
    template_id: str = ""
    user_goal: str = ""
    llm_provider: str = ""
    llm_model: str = ""
    judge_mode: str = ""
    plan_state: PlanGraphState = field(default_factory=PlanGraphState)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "workspace_path": self.workspace_path,
            "requirement_id": self.requirement_id,
            "plan_mode": self.plan_mode,
            "template_id": self.template_id,
            "user_goal": self.user_goal,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "judge_mode": self.judge_mode,
            "metadata": {PLAN_GRAPH_METADATA_KEY: self.plan_state.to_metadata()},
            "messages": list(self.messages),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowRecord":
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        plan_state = PlanGraphState.from_metadata(metadata) or PlanGraphState()
        plan_state.user_goal = str(data.get("user_goal") or plan_state.user_goal or "")
        plan_mode_raw = str(data.get("plan_mode") or "").strip().lower()
        template_id = str(data.get("template_id") or "").strip()
        if plan_mode_raw in ("template", "dynamic"):
            plan_mode = plan_mode_raw
        elif template_id:
            plan_mode = "template"
        else:
            plan_mode = "dynamic"
        return cls(
            workflow_id=str(data.get("workflow_id") or ""),
            name=str(data.get("name") or ""),
            description=str(data.get("description") or ""),
            workspace_path=str(data.get("workspace_path") or ""),
            requirement_id=str(data.get("requirement_id") or ""),
            plan_mode=plan_mode,
            template_id=template_id,
            user_goal=str(data.get("user_goal") or ""),
            llm_provider=str(data.get("llm_provider") or ""),
            llm_model=str(data.get("llm_model") or ""),
            judge_mode=str(data.get("judge_mode") or ""),
            plan_state=plan_state,
            messages=list(data.get("messages") or []),
            created_at=str(data.get("created_at") or _now_iso()),
            updated_at=str(data.get("updated_at") or _now_iso()),
        )


class WorkflowStore:
    def __init__(self, root_dir: Optional[str] = None) -> None:
        base = resolve_data_dir(root_dir) if root_dir else settings.data_dir
        self._root = base / "workflows"
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _path(self, workflow_id: str) -> Path:
        return self._root / f"{workflow_id}.json"

    async def create(
        self,
        *,
        name: str = "",
        description: str = "",
        workspace_path: str = "",
        requirement_id: str = "",
        plan_mode: str = "template",
        template_id: str = "",
        user_goal: str = "",
        graph_spec: Optional[Dict[str, Any]] = None,
    ) -> WorkflowRecord:
        workflow_id = f"wf_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        plan_state = PlanGraphState(user_goal=user_goal)
        mode = str(plan_mode or "template").strip().lower()
        if mode not in ("template", "dynamic"):
            mode = "template"
        tpl_id = str(template_id or "").strip()
        if graph_spec and mode == "dynamic":
            graph = DirectExecGraph.from_dict(graph_spec)
            if graph is None:
                raise ValueError("拓扑无效")
            plan_state.plan_graph = graph
        req_id = requirement_id.strip()
        record = WorkflowRecord(
            workflow_id=workflow_id,
            name=name.strip() or (req_id or workflow_id),
            description=description.strip(),
            workspace_path=workspace_path.strip(),
            requirement_id=req_id,
            plan_mode=mode,
            template_id=tpl_id,
            user_goal=user_goal.strip(),
            plan_state=plan_state,
        )
        await self.save(record)
        return record

    async def save(self, record: WorkflowRecord) -> None:
        record.updated_at = _now_iso()
        path = self._path(record.workflow_id)
        async with self._lock:
            path.write_text(json.dumps(record.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    async def get(self, workflow_id: str) -> Optional[WorkflowRecord]:
        path = self._path(workflow_id)
        if not path.is_file():
            return None
        async with self._lock:
            data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return WorkflowRecord.from_dict(data)

    async def list_all(self) -> List[WorkflowRecord]:
        items: List[WorkflowRecord] = []
        for path in sorted(self._root.glob("wf_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(data, dict):
                items.append(WorkflowRecord.from_dict(data))
        return items

    async def find_by_requirement(
        self,
        workspace_path: str,
        requirement_id: str,
    ) -> Optional[WorkflowRecord]:
        from app.workspace.paths import paths_equal
        req_id = str(requirement_id or "").strip()
        if not req_id:
            return None
        for record in await self.list_all():
            if record.requirement_id != req_id:
                continue
            if paths_equal(record.workspace_path, workspace_path):
                return record
        return None

    async def delete(self, workflow_id: str) -> bool:
        path = self._path(workflow_id)
        if not path.is_file():
            return False
        async with self._lock:
            path.unlink()
        return True

    async def update_topology(self, workflow_id: str, graph_spec: Dict[str, Any]) -> WorkflowRecord:
        record = await self.get(workflow_id)
        if record is None:
            raise KeyError(workflow_id)
        if normalize_plan_mode(record.plan_mode) == "template":
            raise ValueError("模板模式下不可修改 Session 拓扑，请在模板管理中编辑")
        graph = DirectExecGraph.from_dict(graph_spec)
        if graph is None:
            raise ValueError("拓扑无效")
        record.plan_state.plan_graph = graph
        await self.save(record)
        return record

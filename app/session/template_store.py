import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.config.paths import resolve_data_dir
from app.config.settings import settings
from app.graph.plan_graph import DirectExecGraph
from app.session.workflow_store import WorkflowRecord


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class WorkflowTemplate:
    template_id: str
    name: str = ""
    description: str = ""
    user_goal: str = ""
    judge_mode: str = ""
    category: str = ""
    graph: Dict[str, Any] = field(default_factory=dict)
    source_workflow_id: str = ""
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "user_goal": self.user_goal,
            "judge_mode": self.judge_mode,
            "category": self.category,
            "graph": dict(self.graph or {}),
            "source_workflow_id": self.source_workflow_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowTemplate":
        graph_raw = data.get("graph")
        graph = dict(graph_raw) if isinstance(graph_raw, dict) else {}
        return cls(
            template_id=str(data.get("template_id") or ""),
            name=str(data.get("name") or ""),
            description=str(data.get("description") or ""),
            user_goal=str(data.get("user_goal") or ""),
            judge_mode=str(data.get("judge_mode") or ""),
            category=str(data.get("category") or ""),
            graph=graph,
            source_workflow_id=str(data.get("source_workflow_id") or ""),
            created_at=str(data.get("created_at") or _now_iso()),
            updated_at=str(data.get("updated_at") or _now_iso()),
        )

    def node_count(self) -> int:
        nodes = self.graph.get("nodes") if isinstance(self.graph, dict) else None
        return len(nodes) if isinstance(nodes, list) else 0


class WorkflowTemplateStore:
    def __init__(self, root_dir: Optional[str] = None) -> None:
        base = resolve_data_dir(root_dir) if root_dir else settings.data_dir
        self._root = base / "workflow_templates"
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    def _path(self, template_id: str) -> Path:
        return self._root / f"{template_id}.json"

    async def create(
        self,
        *,
        name: str,
        description: str = "",
        user_goal: str = "",
        judge_mode: str = "",
        category: str = "",
        graph: Optional[Dict[str, Any]] = None,
        source_workflow_id: str = "",
    ) -> WorkflowTemplate:
        graph_spec = graph or {}
        if graph_spec:
            parsed = DirectExecGraph.from_dict(graph_spec)
            if parsed is None:
                raise ValueError("拓扑无效")
            graph_spec = parsed.to_dict()
        template_id = f"tpl_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        item = WorkflowTemplate(
            template_id=template_id,
            name=name.strip() or template_id,
            description=description.strip(),
            user_goal=user_goal.strip(),
            judge_mode=judge_mode.strip(),
            category=category.strip(),
            graph=graph_spec,
            source_workflow_id=source_workflow_id.strip(),
        )
        await self.save(item)
        return item

    async def save(self, item: WorkflowTemplate) -> None:
        item.updated_at = _now_iso()
        path = self._path(item.template_id)
        async with self._lock:
            path.write_text(json.dumps(item.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    async def get(self, template_id: str) -> Optional[WorkflowTemplate]:
        path = self._path(template_id)
        if not path.is_file():
            return None
        async with self._lock:
            data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return WorkflowTemplate.from_dict(data)

    async def list_all(self) -> List[WorkflowTemplate]:
        items: List[WorkflowTemplate] = []
        for path in sorted(self._root.glob("tpl_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(data, dict):
                items.append(WorkflowTemplate.from_dict(data))
        return items

    async def delete(self, template_id: str) -> bool:
        path = self._path(template_id)
        if not path.is_file():
            return False
        async with self._lock:
            path.unlink()
        return True

    async def update(
        self,
        template_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        user_goal: Optional[str] = None,
        judge_mode: Optional[str] = None,
        category: Optional[str] = None,
        graph: Optional[Dict[str, Any]] = None,
    ) -> WorkflowTemplate:
        item = await self.get(template_id)
        if item is None:
            raise KeyError(template_id)
        if name is not None:
            item.name = name.strip() or item.name
        if description is not None:
            item.description = description.strip()
        if user_goal is not None:
            item.user_goal = user_goal.strip()
        if judge_mode is not None:
            item.judge_mode = judge_mode.strip()
        if category is not None:
            item.category = category.strip()
        if graph is not None:
            parsed = DirectExecGraph.from_dict(graph)
            if parsed is None:
                raise ValueError("拓扑无效")
            item.graph = parsed.to_dict()
        await self.save(item)
        return item


def template_from_workflow(
    record: WorkflowRecord,
    *,
    name: str,
    description: str = "",
) -> WorkflowTemplate:
    graph_dict = record.plan_state.plan_graph_topology_dict() or {}
    if not graph_dict:
        raise ValueError("当前 Session 无有效拓扑，无法保存为模板")
    parsed = DirectExecGraph.from_dict(graph_dict)
    if parsed is None:
        raise ValueError("当前 Session 拓扑无效")
    return WorkflowTemplate(
        template_id="",
        name=name.strip() or record.name or record.workflow_id,
        description=description.strip(),
        user_goal=record.user_goal.strip(),
        judge_mode=record.judge_mode.strip(),
        graph=parsed.to_dict(),
        source_workflow_id=record.workflow_id,
    )


def apply_template_to_record(record: WorkflowRecord, template: WorkflowTemplate) -> None:
    graph = DirectExecGraph.from_dict(template.graph)
    if graph is None:
        raise ValueError("模板拓扑无效")
    record.plan_state.plan_graph = graph
    if template.judge_mode:
        record.judge_mode = template.judge_mode
    if template.user_goal and not record.user_goal.strip():
        record.user_goal = template.user_goal
        record.plan_state.user_goal = template.user_goal
    record.plan_state.clear_history(clear_session_id=True)

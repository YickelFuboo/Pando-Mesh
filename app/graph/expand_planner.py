import json
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.config.paths import resolve_data_dir
from app.config.settings import settings
from app.graph.node_config import GraphNodeExpandConfig
from app.graph.plan_graph import DirectExecGraph, END_NODE, GraphNode, START_NODE
from app.maas.fallback import call_with_llm_fallback
from app.maas.chat_models.models_config import models_config
from app.maas.prompts.prompt_template_load import get_prompt_template
from app.runtime.abort import RunAbortController
from app.runtime.context import AgentContext
from app.workspace.refs import expand_session_placeholders, expand_workspace_ref_paths

logger = logging.getLogger(__name__)

EXPAND_PLANNER_PROMPT_USER = "EXPAND_PLANNER_USER.md"
EXPAND_PLANNER_PROMPT_SYSTEM = "AGENT.md"
_LLM_ABORT_POLL_SEC = 0.2

ExpandPlannerCallback = Callable[
    [DirectExecGraph, GraphNode, GraphNodeExpandConfig, AgentContext, Dict[str, str]],
    Awaitable[str],
]


def _templates_root() -> Path:
    return resolve_data_dir(settings.data_dir) / "workflow_templates"


def scan_expand_doc_paths(
    *,
    workspace_path: str,
    requirement_id: str,
    doc_paths: List[str],
) -> List[str]:
    seen: set[str] = set()
    results: List[str] = []
    ws = (workspace_path or "").strip()
    req = (requirement_id or "").strip()
    for raw in doc_paths or []:
        text = (raw or "").strip()
        if not text:
            continue
        try:
            matches = expand_workspace_ref_paths(ws, req, text)
        except Exception:
            logger.exception("expand scan failed: %s", text)
            matches = []
        for path in matches:
            key = str(path).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            results.append(key)
    return sorted(results)


def load_template_catalog(template_ids: List[str], templates_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    root = templates_root or _templates_root()
    catalog: List[Dict[str, Any]] = []
    for tid in template_ids:
        key = (tid or "").strip()
        if not key:
            continue
        path = root / f"{key}.json"
        if not path.is_file():
            catalog.append({"template_id": key, "name": key, "description": "(模板文件不存在)", "node_ids": []})
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            catalog.append({"template_id": key, "name": key, "description": "(模板读取失败)", "node_ids": []})
            continue
        graph_spec = data.get("graph") if isinstance(data, dict) else {}
        node_ids: List[str] = []
        if isinstance(graph_spec, dict):
            for raw in graph_spec.get("nodes") or []:
                if isinstance(raw, dict):
                    nid = str(raw.get("id") or "").strip()
                    if nid:
                        node_ids.append(nid)
        catalog.append(
            {
                "template_id": key,
                "name": str(data.get("name") or key),
                "description": str(data.get("description") or ""),
                "template_role": str(data.get("template_role") or ""),
                "node_ids": node_ids,
            }
        )
    return catalog


def summarize_graph_context(
    graph: DirectExecGraph,
    expand_node_id: str,
    *,
    node_outputs: Optional[Dict[str, str]] = None,
) -> str:
    expand_id = (expand_node_id or "").strip()
    lines: List[str] = [f"entry: {graph.entry_node_id}", f"expand 节点: {expand_id}"]
    preds = graph.predecessor_ids(expand_id)
    if preds:
        lines.append(f"上游: {', '.join(preds)}")
    downstream: List[str] = []
    for edge in graph.outgoing_edges(expand_id):
        if edge.to_id not in (END_NODE, START_NODE):
            downstream.append(edge.to_id)
    if downstream:
        lines.append(f"下游: {', '.join(downstream)}")
    outputs = node_outputs or {}
    executed: List[str] = []
    for nid, node in graph.nodes.items():
        if nid == expand_id:
            continue
        if nid in outputs and (outputs[nid] or "").strip():
            label = node.label or nid
            executed.append(f"- {label} ({nid}): 已执行")
    if executed:
        lines.append("已执行步骤:")
        lines.extend(executed[:20])
    lines.append("当前骨架节点:")
    for nid, node in graph.nodes.items():
        kind = node.executor.kind if node.executor else ""
        if node.is_expand():
            lines.append(f"- {node.label or nid} ({nid}) [expand]")
        elif nid != expand_id:
            lines.append(f"- {node.label or nid} ({nid}) [{kind}]")
    return "\n".join(lines)


def format_template_catalog(catalog: List[Dict[str, Any]]) -> str:
    if not catalog:
        return "(无)"
    lines: List[str] = []
    for item in catalog:
        node_ids = item.get("node_ids") or []
        nodes_text = " → ".join(node_ids) if node_ids else "(无节点)"
        lines.append(
            f"- {item.get('template_id')}: {item.get('name') or ''} — {item.get('description') or ''}\n"
            f"  节点链: {nodes_text}"
        )
    return "\n".join(lines)


def format_scanned_files(paths: List[str]) -> str:
    if not paths:
        return "(未扫描到文件)"
    return "\n".join(f"- {p}" for p in paths)


def resolve_catalog_template_ids(expand_cfg: GraphNodeExpandConfig) -> List[str]:
    ids: List[str] = []
    for tid in expand_cfg.catalog_templates:
        key = (tid or "").strip()
        if key and key not in ids:
            ids.append(key)
    default_tid = (expand_cfg.default_lane_template_id or "").strip()
    if default_tid and default_tid not in ids:
        ids.insert(0, default_tid)
    return ids


def uses_native_llm_planner(expand_cfg: Optional[GraphNodeExpandConfig]) -> bool:
    if expand_cfg is None:
        return False
    planner = (expand_cfg.planner or "").strip().lower()
    if planner == "native_llm":
        return True
    if planner == "source":
        return False
    if expand_cfg.catalog_templates or expand_cfg.default_lane_template_id:
        return True
    return False


class ExpandPlannerService:
    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        abort_controller: Optional[RunAbortController] = None,
    ) -> None:
        self._provider = provider
        self._model = model
        self._abort_controller = abort_controller

    def is_available(self) -> bool:
        return models_config.is_available()

    def _model_pairs(self) -> List[Tuple[str, str]]:
        return models_config.fallback_pairs(self._provider, self._model)

    def _is_aborted(self) -> bool:
        ctrl = self._abort_controller
        return ctrl is not None and ctrl.is_aborted()

    def _prompt_dir(self) -> str:
        return str(settings.prompts_dir)

    def _system_prompt(self) -> str:
        return get_prompt_template(self._prompt_dir(), EXPAND_PLANNER_PROMPT_SYSTEM, {}).strip()

    async def plan_expansion(
        self,
        *,
        graph: DirectExecGraph,
        expand_node: GraphNode,
        expand_cfg: GraphNodeExpandConfig,
        agent_ctx: AgentContext,
        node_outputs: Dict[str, str],
    ) -> str:
        if not self.is_available():
            raise RuntimeError("扩展规划需要 LLM，但当前未配置可用模型")
        workspace_path = (agent_ctx.workspace_path or "").strip()
        requirement_id = (agent_ctx.requirement_id or "").strip()
        expand_task = expand_session_placeholders(
            (expand_node.task or "").strip(),
            workspace_path=workspace_path,
            requirement_id=requirement_id,
        )
        scanned = scan_expand_doc_paths(
            workspace_path=workspace_path,
            requirement_id=requirement_id,
            doc_paths=list(expand_node.input_doc_paths or []),
        )
        catalog_ids = resolve_catalog_template_ids(expand_cfg)
        catalog = load_template_catalog(catalog_ids)
        graph_context = summarize_graph_context(
            graph,
            expand_node.id,
            node_outputs=node_outputs,
        )
        params = {
            "expand_task": expand_task or "(无扩展任务说明)",
            "requirement_id": requirement_id or "(未设置)",
            "workspace_path": workspace_path or "(未设置)",
            "default_lane_template_id": (expand_cfg.default_lane_template_id or "").strip() or "(未设置)",
            "graph_context": graph_context,
            "scanned_files": format_scanned_files(scanned),
            "template_catalog": format_template_catalog(catalog),
        }
        user_prompt = get_prompt_template(self._prompt_dir(), EXPAND_PLANNER_PROMPT_USER, params).strip()

        async def _call(llm: Any) -> str:
            return await self._plan_with_llm(llm, user_prompt)

        raw, _ = await call_with_llm_fallback(self._model_pairs(), _call)
        if not (raw or "").strip():
            raise RuntimeError("扩展规划 LLM 未返回有效内容")
        return raw.strip()

    async def _plan_with_llm(self, llm: Any, user_prompt: str) -> str:
        import asyncio

        system_prompt = self._system_prompt()
        if not system_prompt:
            raise RuntimeError(f"扩展规划 system prompt 缺失: {settings.prompts_dir / EXPAND_PLANNER_PROMPT_SYSTEM}")
        llm_task = asyncio.create_task(
            self._collect_stream(
                llm.chat_stream(
                    system_prompt=system_prompt,
                    user_question=user_prompt,
                    history=[],
                    temperature=0.2,
                )
            )
        )
        try:
            while not llm_task.done():
                if self._is_aborted():
                    llm_task.cancel()
                    try:
                        await llm_task
                    except asyncio.CancelledError:
                        pass
                    raise RuntimeError("扩展规划已中止")
                await asyncio.sleep(_LLM_ABORT_POLL_SEC)
            chunks = llm_task.result()
        except asyncio.CancelledError:
            raise RuntimeError("扩展规划已中止") from None
        if self._is_aborted():
            raise RuntimeError("扩展规划已中止")
        return "".join(chunks)

    async def _collect_stream(self, stream: Any) -> List[str]:
        chunks: List[str] = []
        async for chunk in stream:
            if self._is_aborted():
                break
            if isinstance(chunk, str) and chunk:
                chunks.append(chunk)
        return chunks


def build_expand_planner_callback(
    *,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    abort_controller: Optional[RunAbortController] = None,
) -> ExpandPlannerCallback:
    service = ExpandPlannerService(
        provider=llm_provider,
        model=llm_model,
        abort_controller=abort_controller,
    )

    async def _callback(
        graph: DirectExecGraph,
        expand_node: GraphNode,
        expand_cfg: GraphNodeExpandConfig,
        agent_ctx: AgentContext,
        node_outputs: Dict[str, str],
    ) -> str:
        return await service.plan_expansion(
            graph=graph,
            expand_node=expand_node,
            expand_cfg=expand_cfg,
            agent_ctx=agent_ctx,
            node_outputs=node_outputs,
        )

    return _callback

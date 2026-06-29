import re
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple
from app.common.json_utils import extract_json_object
from app.graph.node_config import GraphNodeCliConfig, GraphNodeExecutor, PLANNING_EXECUTOR_CLI
from app.graph.plan_graph import DirectExecGraph, END_NODE, EdgeCondition, GraphEdge, GraphNode, START_NODE

DEFAULT_TASK_CLI: Dict[str, Any] = {
    "commands": [{"command": "python", "args": ["-c", "print('ok')"]}],
    "input": "arg",
    "cwd": "{workspace}",
    "timeout_sec": 3600,
    "output_mode": "stdout",
    "result_json_key": "result",
    "session": {"enabled": False},
}


def _slug_node_id(raw: str, *, prefix: str, used: set[str]) -> str:
    base = re.sub(r"[^a-zA-Z0-9_]+", "_", (raw or "").strip()).strip("_").lower()
    if not base:
        base = prefix
    if base[0].isdigit():
        base = f"{prefix}_{base}"
    candidate = base
    idx = 2
    while candidate in used:
        candidate = f"{base}_{idx}"
        idx += 1
    used.add(candidate)
    return candidate


def parse_tasks_from_output(text: str) -> List[Dict[str, Any]]:
    parsed = extract_json_object(text or "")
    if parsed is None:
        raise ValueError("无法从产出中解析 JSON 任务列表")
    tasks_raw: Any = parsed.get("tasks") if isinstance(parsed, dict) else parsed
    if not isinstance(tasks_raw, list) or not tasks_raw:
        raise ValueError("任务列表为空或格式无效，需要 {\"tasks\": [{\"id\",\"label\",\"task\"}, ...]}")
    tasks: List[Dict[str, Any]] = []
    for item in tasks_raw:
        if not isinstance(item, dict):
            continue
        task_text = str(item.get("task") or item.get("description") or "").strip()
        label = str(item.get("label") or item.get("name") or "").strip()
        node_id = str(item.get("id") or "").strip()
        if not task_text and not label:
            continue
        payload: Dict[str, Any] = {
            "id": node_id,
            "label": label or node_id or "子任务",
            "task": task_text or label,
        }
        if isinstance(item.get("executor"), dict):
            payload["executor"] = item["executor"]
        tasks.append(payload)
    if not tasks:
        raise ValueError("未解析到有效任务项")
    return tasks


def _task_executor(raw: Optional[Dict[str, Any]]) -> GraphNodeExecutor:
    if isinstance(raw, dict):
        executor = GraphNodeExecutor.from_dict(raw)
        if executor.is_cli() or executor.is_human() or executor.is_expand() or executor.is_fork():
            return executor
    cli = GraphNodeCliConfig.from_dict(deepcopy(DEFAULT_TASK_CLI))
    if cli is None:
        raise ValueError("默认任务 CLI 配置无效")
    return GraphNodeExecutor.from_cli(cli)


def expand_tasks_into_graph(
    graph: DirectExecGraph,
    *,
    expand_node_id: str,
    tasks: List[Dict[str, Any]],
    merge_label: str = "任务汇聚",
    task_executor: Optional[Dict[str, Any]] = None,
) -> Tuple[DirectExecGraph, str]:
    expand_id = (expand_node_id or "").strip()
    if expand_id not in graph.nodes:
        raise ValueError(f"分裂节点不存在: {expand_id}")
    preds = graph.predecessor_ids(expand_id)
    if not preds:
        raise ValueError("分裂节点没有上游步骤，无法挂接任务")
    source_id = preds[0]
    downstream: List[str] = []
    for edge in graph.outgoing_edges(expand_id):
        if edge.to_id in (END_NODE, START_NODE):
            continue
        if edge.condition in (EdgeCondition.ALWAYS, EdgeCondition.PASS):
            downstream.append(edge.to_id)
    if not downstream:
        downstream = [END_NODE]

    used_ids = set(graph.nodes.keys())
    fork_id = _slug_node_id(f"fork_{source_id}", prefix="fork", used=used_ids)
    merge_id = _slug_node_id(f"merge_{source_id}", prefix="merge", used=used_ids)

    nodes = dict(graph.nodes)
    edges = [e for e in graph.edges if e.from_id != expand_id and e.to_id != expand_id and e.from_id != fork_id and e.to_id != fork_id]
    nodes.pop(expand_id, None)

    nodes[fork_id] = GraphNode(
        id=fork_id,
        label="并行分发",
        task="将上游任务分裂为并行子步骤",
        max_iterations=1,
        executor=GraphNodeExecutor.from_fork(),
    )
    nodes[merge_id] = GraphNode(
        id=merge_id,
        label=merge_label,
        task="等待全部分支完成后继续",
        max_iterations=1,
        executor=GraphNodeExecutor.from_fork(),
    )

    template_executor = _task_executor(task_executor)
    task_node_ids: List[str] = []
    for item in tasks:
        tid = _slug_node_id(str(item.get("id") or item.get("label") or "task"), prefix="task", used=used_ids)
        label = str(item.get("label") or tid).strip()
        task_text = str(item.get("task") or label).strip()
        executor = _task_executor(item.get("executor") if isinstance(item.get("executor"), dict) else None)
        if not item.get("executor") and template_executor.is_cli():
            executor = template_executor
        nodes[tid] = GraphNode(
            id=tid,
            label=label,
            task=task_text,
            max_iterations=int(item.get("max_iterations") or 3),
            executor=executor,
        )
        task_node_ids.append(tid)

    new_edges: List[GraphEdge] = []
    replaced_source_out = False
    for edge in edges:
        if edge.from_id == source_id and edge.to_id == expand_id:
            new_edges.append(GraphEdge(from_id=source_id, to_id=fork_id, condition=EdgeCondition.ALWAYS))
            replaced_source_out = True
            continue
        new_edges.append(edge)
    if not replaced_source_out:
        new_edges.append(GraphEdge(from_id=source_id, to_id=fork_id, condition=EdgeCondition.ALWAYS))

    for tid in task_node_ids:
        new_edges.append(GraphEdge(from_id=fork_id, to_id=tid, condition=EdgeCondition.ALWAYS))
        new_edges.append(GraphEdge(from_id=tid, to_id=merge_id, condition=EdgeCondition.ALWAYS))

    for target in downstream:
        new_edges.append(GraphEdge(from_id=merge_id, to_id=target, condition=EdgeCondition.ALWAYS))

    new_graph = DirectExecGraph(nodes=nodes, edges=new_edges, entry_node_id=graph.entry_node_id)
    if not new_graph.is_valid():
        raise ValueError("分裂后拓扑无效，请检查原图结构")
    return new_graph, fork_id

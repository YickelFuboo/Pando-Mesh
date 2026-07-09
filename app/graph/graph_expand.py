import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from app.utils import extract_json_object
from app.config.paths import resolve_data_dir
from app.config.settings import settings
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


def _replace_placeholders(text: str, placeholders: Dict[str, str]) -> str:
    result = str(text or "")
    for key, value in placeholders.items():
        token = str(key or "").strip()
        if not token:
            continue
        result = result.replace(f"{{{token}}}", str(value))
    return result


def _replace_placeholders_in_node(
    node: GraphNode,
    placeholders: Dict[str, str],
    *,
    node_id: Optional[str] = None,
) -> GraphNode:
    return GraphNode(
        id=(node_id or node.id),
        label=_replace_placeholders(node.label, placeholders),
        task=_replace_placeholders(node.task, placeholders),
        phase=node.phase,
        node_role=node.node_role,
        input_doc_paths=[_replace_placeholders(p, placeholders) for p in node.input_doc_paths],
        output_doc_paths=[_replace_placeholders(p, placeholders) for p in node.output_doc_paths],
        max_iterations=node.max_iterations,
        executor=node.executor,
    )


def load_lane_template_graph(template_id: str, templates_root: Optional[Path] = None) -> DirectExecGraph:
    tid = (template_id or "").strip()
    if not tid:
        raise ValueError("lane 模板 id 为空")
    root = templates_root or (resolve_data_dir(settings.data_dir) / "workflow_templates")
    path = root / f"{tid}.json"
    if not path.is_file():
        raise ValueError(f"Lane 模板不存在: {tid}")
    data = json.loads(path.read_text(encoding="utf-8"))
    graph_spec = data.get("graph") if isinstance(data, dict) else None
    if not isinstance(graph_spec, dict):
        raise ValueError(f"Lane 模板拓扑无效: {tid}")
    graph = DirectExecGraph.from_dict(graph_spec)
    if graph is None:
        raise ValueError(f"Lane 模板拓扑无效: {tid}")
    return graph


def parse_lanes_from_output(
    text: str,
    *,
    default_lane_template_id: str = "",
) -> List[Dict[str, Any]]:
    parsed = extract_json_object(text or "")
    if parsed is None:
        raise ValueError("无法从产出中解析 JSON Lane 列表")
    lanes_raw: Any = parsed.get("lanes") if isinstance(parsed, dict) else None
    if not isinstance(lanes_raw, list) or not lanes_raw:
        raise ValueError("Lane 列表为空或格式无效，需要 {\"lanes\": [{\"id\",\"label\",\"template_id\", ...}, ...]}")
    default_template = (default_lane_template_id or "").strip()
    lanes: List[Dict[str, Any]] = []
    for item in lanes_raw:
        if not isinstance(item, dict):
            continue
        lane_id = str(item.get("id") or item.get("branch_id") or "").strip()
        label = str(item.get("label") or lane_id or "Lane").strip()
        template_id = str(item.get("template_id") or default_template).strip()
        if not lane_id or not template_id:
            continue
        placeholders_raw = item.get("placeholders") if isinstance(item.get("placeholders"), dict) else {}
        placeholders = {str(k): str(v) for k, v in placeholders_raw.items()}
        if "branch_id" not in placeholders:
            placeholders["branch_id"] = lane_id
        skip_nodes = item.get("skip_nodes") if isinstance(item.get("skip_nodes"), list) else []
        node_overrides = item.get("node_overrides") if isinstance(item.get("node_overrides"), dict) else {}
        lanes.append(
            {
                "id": lane_id,
                "label": label,
                "template_id": template_id,
                "placeholders": placeholders,
                "skip_nodes": [str(x).strip() for x in skip_nodes if str(x).strip()],
                "node_overrides": node_overrides,
            }
        )
    if not lanes:
        raise ValueError("未解析到有效 Lane 项")
    return lanes


def parse_expansion_result(
    text: str,
    *,
    mode: str = "auto",
    default_lane_template_id: str = "",
) -> Dict[str, Any]:
    mode_key = (mode or "auto").strip().lower()
    parsed = extract_json_object(text or "")
    has_lanes = isinstance(parsed, dict) and isinstance(parsed.get("lanes"), list) and bool(parsed.get("lanes"))
    if mode_key == "lane" or (mode_key == "auto" and has_lanes):
        lanes = parse_lanes_from_output(text, default_lane_template_id=default_lane_template_id)
        return {"mode": "lane", "lanes": lanes}
    tasks = parse_tasks_from_output(text)
    return {"mode": "task", "tasks": tasks}


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


def _prepare_expand_shell(
    graph: DirectExecGraph,
    *,
    expand_node_id: str,
    merge_label: str,
) -> Tuple[str, List[str], Dict[str, GraphNode], List[GraphEdge], set[str], str, str]:
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
    edges = [
        e
        for e in graph.edges
        if e.from_id != expand_id and e.to_id != expand_id and e.from_id != fork_id and e.to_id != fork_id
    ]
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
    return source_id, downstream, nodes, edges, used_ids, fork_id, merge_id


def _clone_lane_subgraph(
    lane_graph: DirectExecGraph,
    *,
    branch_id: str,
    lane_label: str,
    placeholders: Dict[str, str],
    skip_nodes: List[str],
    node_overrides: Dict[str, Any],
    used_ids: set[str],
) -> Tuple[Dict[str, GraphNode], List[GraphEdge], str, List[str]]:
    skip_set = set(skip_nodes or [])
    id_map: Dict[str, str] = {}
    for old_id in lane_graph.nodes:
        if old_id in skip_set:
            continue
        new_id = _slug_node_id(f"{branch_id}__{old_id}", prefix="lane", used=used_ids)
        id_map[old_id] = new_id

    def _incoming_edges(node_id: str) -> List[GraphEdge]:
        return [e for e in lane_graph.edges if e.to_id == node_id]

    def _add_exit(mapped_id: str) -> None:
        if mapped_id and mapped_id not in seen_exits:
            exit_ids.append(mapped_id)
            seen_exits.add(mapped_id)

    def _outgoing_follows(incoming: EdgeCondition, outgoing: EdgeCondition) -> bool:
        if incoming == EdgeCondition.ALWAYS:
            return outgoing in (EdgeCondition.ALWAYS, EdgeCondition.PASS)
        if outgoing == EdgeCondition.ALWAYS:
            return True
        return incoming == outgoing

    def _resolve_skip_bridge(
        skip_id: str,
        incoming: EdgeCondition,
        visited: Optional[set[str]] = None,
    ) -> Tuple[bool, List[str]]:
        if skip_id not in skip_set:
            mapped = id_map.get(skip_id)
            return (False, [mapped] if mapped else [])
        if visited is None:
            visited = set()
        if skip_id in visited:
            return (False, [])
        visited.add(skip_id)
        exits_end = False
        internal: List[str] = []
        for out_edge in lane_graph.outgoing_edges(skip_id):
            if not _outgoing_follows(incoming, out_edge.condition):
                continue
            if out_edge.to_id == END_NODE:
                exits_end = True
            elif out_edge.to_id in skip_set:
                sub_end, sub_internal = _resolve_skip_bridge(out_edge.to_id, out_edge.condition, visited)
                exits_end = exits_end or sub_end
                internal.extend(sub_internal)
            elif out_edge.to_id in id_map:
                internal.append(id_map[out_edge.to_id])
        return exits_end, internal

    def _add_exits_before_skip(skip_id: str, visited: Optional[set[str]] = None) -> None:
        if visited is None:
            visited = set()
        if skip_id in visited:
            return
        visited.add(skip_id)
        for pred_edge in _incoming_edges(skip_id):
            if pred_edge.from_id in skip_set:
                _add_exits_before_skip(pred_edge.from_id, visited)
            elif pred_edge.from_id in id_map:
                _add_exit(id_map[pred_edge.from_id])

    new_nodes: Dict[str, GraphNode] = {}
    for old_id, new_id in id_map.items():
        node = lane_graph.nodes[old_id]
        merged = dict(placeholders)
        node = _replace_placeholders_in_node(node, merged, node_id=new_id)
        override = node_overrides.get(old_id) if isinstance(node_overrides, dict) else None
        if isinstance(override, dict):
            if override.get("label"):
                node.label = _replace_placeholders(str(override["label"]), merged)
            if override.get("task"):
                node.task = _replace_placeholders(str(override["task"]), merged)
            if isinstance(override.get("executor"), dict):
                node.executor = GraphNodeExecutor.from_dict(override["executor"])
            if isinstance(override.get("input_doc_paths"), list):
                node.input_doc_paths = [_replace_placeholders(str(p), merged) for p in override["input_doc_paths"]]
            if isinstance(override.get("output_doc_paths"), list):
                node.output_doc_paths = [_replace_placeholders(str(p), merged) for p in override["output_doc_paths"]]
        if lane_label and old_id == lane_graph.entry_node_id:
            node.label = f"{lane_label} · {node.label}" if node.label else lane_label
        new_nodes[new_id] = node

    entry_id = id_map.get(lane_graph.entry_node_id, "")
    if not entry_id and lane_graph.entry_node_id in skip_set:
        _, bridged = _resolve_skip_bridge(lane_graph.entry_node_id, EdgeCondition.ALWAYS)
        if bridged:
            entry_id = bridged[0]
            if lane_label and entry_id in new_nodes:
                node = new_nodes[entry_id]
                node.label = f"{lane_label} · {node.label}" if node.label else lane_label
    if not entry_id:
        raise ValueError(f"Lane 入口无效: {branch_id}")

    new_edges: List[GraphEdge] = []
    exit_ids: List[str] = []
    seen_exits: set[str] = set()
    for edge in lane_graph.edges:
        if edge.from_id == START_NODE or edge.to_id == START_NODE:
            continue
        if edge.to_id == END_NODE:
            if edge.from_id in skip_set:
                _add_exits_before_skip(edge.from_id)
            else:
                mapped_from = id_map.get(edge.from_id)
                if mapped_from:
                    _add_exit(mapped_from)
            continue
        if edge.to_id in skip_set:
            src = id_map.get(edge.from_id)
            if not src:
                continue
            exits_end, internal_targets = _resolve_skip_bridge(edge.to_id, edge.condition)
            if exits_end:
                _add_exit(src)
            seen_dst: set[str] = set()
            for dst in internal_targets:
                if dst and dst not in seen_dst:
                    new_edges.append(GraphEdge(from_id=src, to_id=dst, condition=edge.condition))
                    seen_dst.add(dst)
            continue
        if edge.from_id in skip_set:
            continue
        src = id_map.get(edge.from_id)
        dst = id_map.get(edge.to_id)
        if src and dst:
            new_edges.append(GraphEdge(from_id=src, to_id=dst, condition=edge.condition))

    if not exit_ids:
        for old_id, new_id in id_map.items():
            internal = [e for e in lane_graph.outgoing_edges(old_id) if e.to_id in lane_graph.nodes and e.to_id not in skip_set]
            if not internal:
                exit_ids.append(new_id)
    if not exit_ids:
        raise ValueError(f"Lane 缺少出口节点: {branch_id}")
    return new_nodes, new_edges, entry_id, exit_ids


def expand_lanes_into_graph(
    graph: DirectExecGraph,
    *,
    expand_node_id: str,
    lanes: List[Dict[str, Any]],
    merge_label: str = "任务汇聚",
    global_placeholders: Optional[Dict[str, str]] = None,
    templates_root: Optional[Path] = None,
) -> Tuple[DirectExecGraph, str]:
    source_id, downstream, nodes, edges, used_ids, fork_id, merge_id = _prepare_expand_shell(
        graph,
        expand_node_id=expand_node_id,
        merge_label=merge_label,
    )
    branch_entries: List[str] = []
    branch_exits: List[List[str]] = []
    for lane in lanes:
        branch_id = str(lane.get("id") or "").strip()
        template_id = str(lane.get("template_id") or "").strip()
        if not branch_id or not template_id:
            raise ValueError("Lane 缺少 id 或 template_id")
        lane_graph = load_lane_template_graph(template_id, templates_root=templates_root)
        placeholders = dict(global_placeholders or {})
        placeholders.update({str(k): str(v) for k, v in (lane.get("placeholders") or {}).items()})
        lane_nodes, lane_edges, entry_id, exit_ids = _clone_lane_subgraph(
            lane_graph,
            branch_id=branch_id,
            lane_label=str(lane.get("label") or branch_id).strip(),
            placeholders=placeholders,
            skip_nodes=list(lane.get("skip_nodes") or []),
            node_overrides=lane.get("node_overrides") if isinstance(lane.get("node_overrides"), dict) else {},
            used_ids=used_ids,
        )
        nodes.update(lane_nodes)
        edges.extend(lane_edges)
        branch_entries.append(entry_id)
        branch_exits.append(exit_ids)

    new_edges: List[GraphEdge] = list(edges)
    replaced_source_out = False
    for idx, edge in enumerate(new_edges):
        if edge.from_id == source_id and edge.to_id == expand_node_id:
            new_edges[idx] = GraphEdge(from_id=source_id, to_id=fork_id, condition=EdgeCondition.ALWAYS)
            replaced_source_out = True
    if not replaced_source_out:
        new_edges.append(GraphEdge(from_id=source_id, to_id=fork_id, condition=EdgeCondition.ALWAYS))
    for entry_id in branch_entries:
        new_edges.append(GraphEdge(from_id=fork_id, to_id=entry_id, condition=EdgeCondition.ALWAYS))
    for exits in branch_exits:
        for exit_id in exits:
            new_edges.append(GraphEdge(from_id=exit_id, to_id=merge_id, condition=EdgeCondition.ALWAYS))
    for target in downstream:
        new_edges.append(GraphEdge(from_id=merge_id, to_id=target, condition=EdgeCondition.ALWAYS))

    new_graph = DirectExecGraph(nodes=nodes, edges=new_edges, entry_node_id=graph.entry_node_id)
    if not new_graph.is_valid():
        raise ValueError("Lane 分裂后拓扑无效，请检查模板与 Lane 计划")
    return dedupe_graph_edges(new_graph), fork_id


def expand_tasks_into_graph(
    graph: DirectExecGraph,
    *,
    expand_node_id: str,
    tasks: List[Dict[str, Any]],
    merge_label: str = "任务汇聚",
    task_executor: Optional[Dict[str, Any]] = None,
) -> Tuple[DirectExecGraph, str]:
    source_id, downstream, nodes, edges, used_ids, fork_id, merge_id = _prepare_expand_shell(
        graph,
        expand_node_id=expand_node_id,
        merge_label=merge_label,
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

    new_edges: List[GraphEdge] = list(edges)
    replaced_source_out = False
    for idx, edge in enumerate(new_edges):
        if edge.from_id == source_id and edge.to_id == expand_node_id:
            new_edges[idx] = GraphEdge(from_id=source_id, to_id=fork_id, condition=EdgeCondition.ALWAYS)
            replaced_source_out = True
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


def apply_expansion_to_graph(
    graph: DirectExecGraph,
    *,
    expand_node_id: str,
    expansion: Dict[str, Any],
    merge_label: str = "任务汇聚",
    global_placeholders: Optional[Dict[str, str]] = None,
    templates_root: Optional[Path] = None,
) -> Tuple[DirectExecGraph, str]:
    mode = str(expansion.get("mode") or "task").strip().lower()
    if mode == "lane":
        lanes = expansion.get("lanes") or []
        if not lanes:
            raise ValueError("Lane 展开计划为空")
        return expand_lanes_into_graph(
            graph,
            expand_node_id=expand_node_id,
            lanes=lanes,
            merge_label=merge_label,
            global_placeholders=global_placeholders,
            templates_root=templates_root,
        )
    tasks = expansion.get("tasks") or []
    if not tasks:
        raise ValueError("任务展开计划为空")
    return expand_tasks_into_graph(
        graph,
        expand_node_id=expand_node_id,
        tasks=tasks,
        merge_label=merge_label,
    )


def dedupe_graph_edges(graph: DirectExecGraph) -> DirectExecGraph:
    seen: set[tuple[str, str, EdgeCondition]] = set()
    unique: List[GraphEdge] = []
    for edge in graph.edges:
        key = (edge.from_id, edge.to_id, edge.condition)
        if key in seen:
            continue
        seen.add(key)
        unique.append(edge)
    if len(unique) == len(graph.edges):
        return graph
    return DirectExecGraph(nodes=dict(graph.nodes), edges=unique, entry_node_id=graph.entry_node_id)


def graph_has_duplicate_edges(graph: DirectExecGraph) -> bool:
    seen: set[tuple[str, str, EdgeCondition]] = set()
    for edge in graph.edges:
        key = (edge.from_id, edge.to_id, edge.condition)
        if key in seen:
            return True
        seen.add(key)
    return False


def _is_branch_lane_node(nid: str, branch_ids: set[str]) -> bool:
    return any(nid.startswith(f"{branch_id}__") for branch_id in branch_ids if branch_id)


def graph_has_missing_node_refs(graph: DirectExecGraph) -> bool:
    node_ids = set(graph.nodes.keys())
    for edge in graph.edges:
        for nid in (edge.from_id, edge.to_id):
            if nid in (START_NODE, END_NODE):
                continue
            if nid not in node_ids:
                return True
    return False


def _outgoing_always_targets_from_edges(from_id: str, edges: List[GraphEdge]) -> List[str]:
    return [
        e.to_id
        for e in edges
        if e.from_id == from_id and e.condition != EdgeCondition.REJECT
    ]


def _collect_reachable_from_graph(start_id: str, graph: DirectExecGraph) -> set[str]:
    seen: set[str] = set()
    queue = [start_id]
    while queue:
        nid = queue.pop(0)
        if nid in seen:
            continue
        seen.add(nid)
        for to_id in _outgoing_always_targets_from_edges(nid, graph.edges):
            if to_id in (START_NODE, END_NODE):
                continue
            if to_id not in seen:
                queue.append(to_id)
    return seen


def graph_has_disconnected_nodes(graph: DirectExecGraph) -> bool:
    if not graph.entry_node_id or not graph.nodes:
        return False
    reachable = _collect_reachable_from_graph(graph.entry_node_id, graph)
    return len(reachable) < len(graph.nodes)


def _collect_post_merge_reachable(merge_id: str, edges: List[GraphEdge]) -> set[str]:
    seen: set[str] = set()
    queue = list(_outgoing_always_targets_from_edges(merge_id, edges))
    while queue:
        nid = queue.pop(0)
        if nid in (START_NODE, END_NODE) or nid in seen:
            continue
        seen.add(nid)
        for to_id in _outgoing_always_targets_from_edges(nid, edges):
            if to_id not in seen:
                queue.append(to_id)
    return seen


def _find_lane_expand_fork_id(graph: DirectExecGraph) -> Optional[str]:
    try:
        fork_id, _ = find_lane_fork_merge(graph)
        return fork_id
    except ValueError:
        return None


def _remap_reference_node_id(node_id: str, graph: DirectExecGraph) -> str:
    if node_id != "expand_sr":
        return node_id
    fork_id = _find_lane_expand_fork_id(graph)
    return fork_id or node_id


def graph_needs_post_merge_restore(graph: DirectExecGraph, anchor_node_id: str = "gate_ar_confirm") -> bool:
    anchor = (anchor_node_id or "").strip()
    if not anchor:
        return False
    if anchor in graph.nodes:
        return not _outgoing_always_targets_from_edges(anchor, graph.edges)
    try:
        _, merge_id = find_lane_fork_merge(graph)
    except ValueError:
        return False
    return not _outgoing_always_targets_from_edges(merge_id, graph.edges)


def restore_post_merge_flow(
    graph: DirectExecGraph,
    reference: DirectExecGraph,
    *,
    anchor_node_id: str = "gate_ar_confirm",
) -> DirectExecGraph:
    anchor = (anchor_node_id or "").strip()
    if not anchor or anchor not in reference.nodes:
        return graph

    nodes = dict(graph.nodes)
    edges = list(graph.edges)
    seen_edges: set[tuple[str, str, EdgeCondition]] = {
        (e.from_id, e.to_id, e.condition) for e in edges
    }

    if anchor not in nodes:
        try:
            _, merge_id = find_lane_fork_merge(graph)
        except ValueError:
            return graph
        nodes[anchor] = reference.nodes[anchor]
        key = (merge_id, anchor, EdgeCondition.ALWAYS)
        if key not in seen_edges:
            edges.append(GraphEdge(from_id=merge_id, to_id=anchor, condition=EdgeCondition.ALWAYS))
            seen_edges.add(key)
    elif not graph_needs_post_merge_restore(graph, anchor):
        return graph

    queue = [anchor]
    visited: set[str] = set()
    while queue:
        nid = queue.pop(0)
        if nid in visited:
            continue
        visited.add(nid)
        if nid not in nodes and nid in reference.nodes:
            nodes[nid] = reference.nodes[nid]
        for edge in reference.outgoing_edges(nid):
            if edge.condition == EdgeCondition.REJECT:
                continue
            if edge.to_id in (START_NODE, END_NODE):
                continue
            dst = _remap_reference_node_id(edge.to_id, graph)
            if dst not in reference.nodes and dst not in nodes:
                continue
            src = _remap_reference_node_id(edge.from_id, graph)
            if src not in nodes:
                continue
            if dst not in nodes and dst in reference.nodes:
                nodes[dst] = reference.nodes[dst]
            key = (src, dst, edge.condition)
            if key not in seen_edges:
                edges.append(GraphEdge(from_id=src, to_id=dst, condition=edge.condition))
                seen_edges.add(key)
            if dst not in visited:
                queue.append(dst)
        for edge in reference.outgoing_edges(nid):
            if edge.condition != EdgeCondition.REJECT:
                continue
            if edge.to_id in (START_NODE, END_NODE):
                continue
            dst = _remap_reference_node_id(edge.to_id, graph)
            src = _remap_reference_node_id(edge.from_id, graph)
            if src not in nodes:
                continue
            if dst not in nodes and dst in reference.nodes:
                nodes[dst] = reference.nodes[dst]
            key = (src, dst, edge.condition)
            if key not in seen_edges:
                edges.append(GraphEdge(from_id=src, to_id=dst, condition=edge.condition))
                seen_edges.add(key)

    restored = dedupe_graph_edges(
        DirectExecGraph(nodes=nodes, edges=edges, entry_node_id=graph.entry_node_id)
    )
    if not restored.is_valid():
        raise ValueError("合并后主流程修复无效")
    return restored


def _find_direct_merge_node(children: List[str], edges: List[GraphEdge]) -> Optional[str]:
    counts: Dict[str, int] = {}
    for cid in children:
        for to_id in _outgoing_always_targets_from_edges(cid, edges):
            counts[to_id] = counts.get(to_id, 0) + 1
    for mid, count in counts.items():
        if count == len(children):
            return mid
    return None


def _is_fork_merge_node(node_id: str, graph: DirectExecGraph) -> bool:
    if node_id not in graph.nodes:
        return False
    node = graph.nodes[node_id]
    if not node.is_fork():
        return False
    ins = [
        e
        for e in graph.edges
        if e.to_id == node_id and e.condition != EdgeCondition.REJECT
    ]
    outs = _outgoing_always_targets_from_edges(node_id, graph.edges)
    return len(ins) > 1 and len(outs) <= 1


def _find_branch_merge_node(children: List[str], graph: DirectExecGraph) -> Optional[str]:
    direct = _find_direct_merge_node(children, graph.edges)
    if direct:
        return direct
    if not children:
        return None
    reachable_sets = [_collect_reachable_from_graph(cid, graph) for cid in children]
    common = set(reachable_sets[0])
    for reachable in reachable_sets[1:]:
        common &= reachable
    merge_candidates = sorted(
        [nid for nid in common if _is_fork_merge_node(nid, graph)],
        key=lambda x: x,
    )
    return merge_candidates[0] if merge_candidates else None


def find_lane_fork_merge(graph: DirectExecGraph) -> Tuple[str, str]:
    for fork_id, node in graph.nodes.items():
        if not node.is_fork():
            continue
        children = _outgoing_always_targets_from_edges(fork_id, graph.edges)
        if len(children) <= 1:
            continue
        merge_id = _find_branch_merge_node(children, graph)
        if merge_id:
            return fork_id, merge_id
    raise ValueError("未找到 Lane fork/merge 节点")


def infer_lanes_from_expand_outputs(node_outputs: Dict[str, str]) -> List[Dict[str, Any]]:
    for text in (node_outputs or {}).values():
        raw = str(text or "").strip()
        if not raw:
            continue
        try:
            result = parse_expansion_result(raw, mode="auto")
        except ValueError:
            continue
        if result.get("mode") == "lane" and result.get("lanes"):
            return list(result["lanes"])
    return []


def repair_lane_expand_graph(
    graph: DirectExecGraph,
    *,
    lanes: List[Dict[str, Any]],
    global_placeholders: Optional[Dict[str, str]] = None,
    fork_id: Optional[str] = None,
    merge_id: Optional[str] = None,
    templates_root: Optional[Path] = None,
) -> DirectExecGraph:
    if not lanes:
        raise ValueError("Lane 修复计划为空")
    resolved_fork_id, resolved_merge_id = find_lane_fork_merge(graph) if not fork_id or not merge_id else (fork_id, merge_id)
    fork_id = resolved_fork_id
    merge_id = resolved_merge_id

    branch_ids = {str(lane.get("id") or "").strip() for lane in lanes if str(lane.get("id") or "").strip()}
    lane_template_node_ids: set[str] = set()
    for lane in lanes:
        template_id = str(lane.get("template_id") or "").strip()
        if not template_id:
            continue
        lane_template_node_ids.update(load_lane_template_graph(template_id, templates_root=templates_root).nodes.keys())

    post_merge_nodes = _collect_post_merge_reachable(merge_id, graph.edges)
    remove_ids: set[str] = set()
    for nid in graph.nodes:
        if nid in (fork_id, merge_id):
            continue
        if any(nid.startswith(f"{branch_id}__") for branch_id in branch_ids):
            remove_ids.add(nid)
        elif nid in lane_template_node_ids and nid not in post_merge_nodes:
            remove_ids.add(nid)

    nodes = {nid: node for nid, node in graph.nodes.items() if nid not in remove_ids}
    edges = [
        e
        for e in graph.edges
        if e.from_id not in remove_ids
        and e.to_id not in remove_ids
        and not (e.from_id == fork_id and _is_branch_lane_node(e.to_id, branch_ids))
        and not (e.to_id == merge_id and _is_branch_lane_node(e.from_id, branch_ids))
    ]
    used_ids = set(nodes.keys())

    branch_entries: List[str] = []
    branch_exits: List[List[str]] = []
    for lane in lanes:
        branch_id = str(lane.get("id") or "").strip()
        template_id = str(lane.get("template_id") or "").strip()
        if not branch_id or not template_id:
            raise ValueError("Lane 缺少 id 或 template_id")
        lane_graph = load_lane_template_graph(template_id, templates_root=templates_root)
        placeholders = dict(global_placeholders or {})
        placeholders.update({str(k): str(v) for k, v in (lane.get("placeholders") or {}).items()})
        lane_nodes, lane_edges, entry_id, exit_ids = _clone_lane_subgraph(
            lane_graph,
            branch_id=branch_id,
            lane_label=str(lane.get("label") or branch_id).strip(),
            placeholders=placeholders,
            skip_nodes=list(lane.get("skip_nodes") or []),
            node_overrides=lane.get("node_overrides") if isinstance(lane.get("node_overrides"), dict) else {},
            used_ids=used_ids,
        )
        nodes.update(lane_nodes)
        edges.extend(lane_edges)
        branch_entries.append(entry_id)
        branch_exits.append(exit_ids)

    edges = [
        e
        for e in edges
        if not (e.from_id == fork_id and e.to_id in branch_entries)
        and not (e.from_id in {exit_id for exits in branch_exits for exit_id in exits} and e.to_id == merge_id)
    ]
    for entry_id in branch_entries:
        edges.append(GraphEdge(from_id=fork_id, to_id=entry_id, condition=EdgeCondition.ALWAYS))
    for exits in branch_exits:
        for exit_id in exits:
            edges.append(GraphEdge(from_id=exit_id, to_id=merge_id, condition=EdgeCondition.ALWAYS))

    repaired = dedupe_graph_edges(
        DirectExecGraph(nodes=nodes, edges=edges, entry_node_id=graph.entry_node_id)
    )
    if not repaired.is_valid():
        raise ValueError("Lane 拓扑修复后无效")
    return repaired

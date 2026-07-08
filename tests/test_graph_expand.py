import json
from pathlib import Path

import pytest
from app.graph.graph_expand import (
    apply_expansion_to_graph,
    expand_lanes_into_graph,
    expand_tasks_into_graph,
    parse_expansion_result,
    parse_lanes_from_output,
    parse_tasks_from_output,
    infer_lanes_from_expand_outputs,
)
from app.graph.node_config import GraphNodeExecutor
from app.graph.plan_graph import DirectExecGraph, END_NODE, EdgeCondition, GraphEdge, GraphNode, START_NODE


def _linear_graph():
    nodes = {
        "gen": GraphNode(id="gen", label="生成任务", task="gen", executor=GraphNodeExecutor.from_human()),
        "expand": GraphNode(id="expand", label="分裂", task="expand", executor=GraphNodeExecutor.from_expand()),
    }
    edges = [
        GraphEdge(from_id=START_NODE, to_id="gen", condition=EdgeCondition.ALWAYS),
        GraphEdge(from_id="gen", to_id="expand", condition=EdgeCondition.ALWAYS),
        GraphEdge(from_id="expand", to_id=END_NODE, condition=EdgeCondition.ALWAYS),
    ]
    return DirectExecGraph(nodes=nodes, edges=edges, entry_node_id="gen")


def _lane_template_dir(tmp_path: Path) -> Path:
    lane_graph = {
        "entry": "step_a",
        "nodes": [
            {
                "id": "step_a",
                "label": "A",
                "task": "do {sr_id}",
                "max_iterations": 1,
                "executor": {"kind": "human"},
            },
            {
                "id": "step_b",
                "label": "B",
                "task": "check {sr_doc}",
                "max_iterations": 1,
                "executor": {"kind": "human"},
            },
        ],
        "edges": [
            {"from": "START", "to": "step_a", "condition": "always"},
            {"from": "step_a", "to": "step_b", "condition": "always"},
            {"from": "step_b", "to": "END", "condition": "pass"},
        ],
    }
    payload = {
        "template_id": "tpl_test_lane",
        "graph": lane_graph,
    }
    root = tmp_path / "workflow_templates"
    root.mkdir(parents=True)
    (root / "tpl_test_lane.json").write_text(json.dumps(payload), encoding="utf-8")
    return root


def test_parse_tasks_from_output():
    tasks = parse_tasks_from_output('{"tasks":[{"id":"a","label":"A","task":"do a"}]}')
    assert len(tasks) == 1
    assert tasks[0]["id"] == "a"


def test_parse_lanes_from_output():
    lanes = parse_lanes_from_output(
        '{"lanes":[{"id":"sr_001","label":"SR-001","template_id":"tpl_sr_to_ar","placeholders":{"sr_id":"SR-001","sr_doc":"a.md"}}]}',
        default_lane_template_id="tpl_sr_to_ar",
    )
    assert len(lanes) == 1
    assert lanes[0]["template_id"] == "tpl_sr_to_ar"
    assert lanes[0]["placeholders"]["sr_id"] == "SR-001"


def test_parse_expansion_result_auto_detects_lanes():
    result = parse_expansion_result(
        '{"lanes":[{"id":"sr_001","label":"SR-001","template_id":"tpl_sr_to_ar"}]}',
        mode="auto",
        default_lane_template_id="tpl_sr_to_ar",
    )
    assert result["mode"] == "lane"
    assert len(result["lanes"]) == 1


def test_parse_expansion_result_auto_detects_tasks():
    result = parse_expansion_result('{"tasks":[{"id":"a","label":"A","task":"do a"}]}', mode="auto")
    assert result["mode"] == "task"
    assert len(result["tasks"]) == 1


def test_expand_tasks_into_graph():
    graph = _linear_graph()
    new_graph, fork_id = expand_tasks_into_graph(
        graph,
        expand_node_id="expand",
        tasks=[
            {"id": "code_a", "label": "改 A", "task": "patch A"},
            {"id": "code_b", "label": "改 B", "task": "patch B"},
        ],
    )
    assert "expand" not in new_graph.nodes
    assert fork_id in new_graph.nodes
    assert "code_a" in new_graph.nodes
    assert "code_b" in new_graph.nodes
    fork_edges = [e.to_id for e in new_graph.outgoing_edges(fork_id)]
    assert "code_a" in fork_edges
    assert "code_b" in fork_edges


def test_expand_lanes_skip_gate_before_end(tmp_path):
    templates_root = _lane_template_dir(tmp_path)
    gate_graph = {
        "entry": "step_a",
        "nodes": [
            {
                "id": "step_a",
                "label": "A",
                "task": "do {sr_id}",
                "max_iterations": 1,
                "executor": {"kind": "human"},
            },
            {
                "id": "step_qc",
                "label": "QC",
                "task": "check {sr_doc}",
                "max_iterations": 1,
                "executor": {"kind": "human"},
            },
            {
                "id": "gate_confirm",
                "label": "Confirm",
                "task": "confirm",
                "max_iterations": 1,
                "executor": {"kind": "human"},
            },
        ],
        "edges": [
            {"from": "START", "to": "step_a", "condition": "always"},
            {"from": "step_a", "to": "step_qc", "condition": "always"},
            {"from": "step_qc", "to": "gate_confirm", "condition": "pass"},
            {"from": "step_qc", "to": "step_a", "condition": "reject"},
            {"from": "gate_confirm", "to": "END", "condition": "pass"},
            {"from": "gate_confirm", "to": "step_a", "condition": "reject"},
        ],
    }
    payload = {
        "template_id": "tpl_gate_lane",
        "graph": gate_graph,
    }
    (templates_root / "tpl_gate_lane.json").write_text(json.dumps(payload), encoding="utf-8")

    graph = _linear_graph()
    new_graph, fork_id = expand_lanes_into_graph(
        graph,
        expand_node_id="expand",
        lanes=[
            {
                "id": "sr_001",
                "label": "SR-001",
                "template_id": "tpl_gate_lane",
                "placeholders": {"sr_id": "SR-001", "sr_doc": "requirements/a.md"},
                "skip_nodes": ["gate_confirm"],
            },
        ],
        templates_root=templates_root,
    )
    assert new_graph.is_valid()
    lane_nodes = [nid for nid in new_graph.nodes if nid.startswith("sr_001__")]
    assert len(lane_nodes) == 2
    qc_nodes = [nid for nid in lane_nodes if "step_qc" in nid]
    assert len(qc_nodes) == 1
    merge_edges = [e for e in new_graph.edges if e.from_id == qc_nodes[0] and e.to_id.startswith("merge_")]
    assert merge_edges


def test_expand_lanes_clone_node_ids_match_keys(tmp_path):
    templates_root = _lane_template_dir(tmp_path)
    graph = _linear_graph()
    new_graph, _fork_id = expand_lanes_into_graph(
        graph,
        expand_node_id="expand",
        lanes=[
            {
                "id": "sr_001",
                "label": "SR-001",
                "template_id": "tpl_test_lane",
                "placeholders": {"sr_id": "SR-001", "sr_doc": "requirements/a.md"},
            },
            {
                "id": "sr_002",
                "label": "SR-002",
                "template_id": "tpl_test_lane",
                "placeholders": {"sr_id": "SR-002", "sr_doc": "requirements/b.md"},
            },
        ],
        templates_root=templates_root,
    )
    for node_id, node in new_graph.nodes.items():
        assert node.id == node_id
    exported = new_graph.to_dict()
    exported_ids = [str(item.get("id") or "") for item in exported.get("nodes") or []]
    assert len(exported_ids) == len(set(exported_ids))


def test_expand_lanes_skip_gate_ar_confirm(tmp_path):
    from app.config.paths import resolve_data_dir
    from app.config.settings import settings

    templates_root = resolve_data_dir(settings.data_dir) / "workflow_templates"
    graph = _linear_graph()
    new_graph, _fork_id = expand_lanes_into_graph(
        graph,
        expand_node_id="expand",
        lanes=[
            {
                "id": "sr_001",
                "label": "SR-001-会话建立携带UE位置",
                "template_id": "tpl_sr_to_ar",
                "placeholders": {
                    "sr_id": "SR-001",
                    "sr_doc": "requirements/REQ-001/feature_changes/SR-001.md",
                },
                "skip_nodes": ["gate_ar_confirm"],
            },
        ],
        templates_root=templates_root,
    )
    assert new_graph.is_valid()
    qc_nodes = [nid for nid in new_graph.nodes if nid.startswith("sr_001__") and "step_arch_qc" in nid]
    assert len(qc_nodes) == 1


def test_expand_lanes_into_graph(tmp_path):
    templates_root = _lane_template_dir(tmp_path)
    graph = _linear_graph()
    new_graph, fork_id = expand_lanes_into_graph(
        graph,
        expand_node_id="expand",
        lanes=[
            {
                "id": "sr_001",
                "label": "SR-001",
                "template_id": "tpl_test_lane",
                "placeholders": {"sr_id": "SR-001", "sr_doc": "requirements/a.md"},
            },
            {
                "id": "sr_002",
                "label": "SR-002",
                "template_id": "tpl_test_lane",
                "placeholders": {"sr_id": "SR-002", "sr_doc": "requirements/b.md"},
            },
        ],
        templates_root=templates_root,
    )
    assert "expand" not in new_graph.nodes
    assert fork_id in new_graph.nodes
    lane_a_nodes = [nid for nid in new_graph.nodes if nid.startswith("sr_001__")]
    lane_b_nodes = [nid for nid in new_graph.nodes if nid.startswith("sr_002__")]
    assert len(lane_a_nodes) == 2
    assert len(lane_b_nodes) == 2
    assert any("SR-001" in new_graph.nodes[nid].task for nid in lane_a_nodes)


def test_apply_expansion_to_graph_lane_mode(tmp_path):
    templates_root = _lane_template_dir(tmp_path)
    graph = _linear_graph()
    new_graph, _fork_id = apply_expansion_to_graph(
        graph,
        expand_node_id="expand",
        expansion={
            "mode": "lane",
            "lanes": [
                {
                    "id": "sr_001",
                    "label": "SR-001",
                    "template_id": "tpl_test_lane",
                    "placeholders": {"sr_id": "SR-001", "sr_doc": "requirements/a.md"},
                }
            ],
        },
        templates_root=templates_root,
    )
    assert new_graph.is_valid()


def test_repair_lane_expand_graph_with_missing_prefixed_ids(tmp_path):
    from app.graph.graph_expand import (
        expand_lanes_into_graph,
        graph_has_missing_node_refs,
        repair_lane_expand_graph,
    )

    templates_root = _lane_template_dir(tmp_path)
    graph = _linear_graph()
    lanes = [
        {
            "id": "sr_001",
            "label": "SR-001",
            "template_id": "tpl_test_lane",
            "placeholders": {"sr_id": "SR-001", "sr_doc": "requirements/a.md"},
        },
        {
            "id": "sr_002",
            "label": "SR-002",
            "template_id": "tpl_test_lane",
            "placeholders": {"sr_id": "SR-002", "sr_doc": "requirements/b.md"},
        },
    ]
    expanded, fork_id = expand_lanes_into_graph(
        graph,
        expand_node_id="expand",
        lanes=lanes,
        templates_root=templates_root,
    )
    broken_nodes = {}
    for node_id, node in expanded.nodes.items():
        if "__" in node_id:
            broken_nodes[node_id.split("__", 1)[1]] = node
        else:
            broken_nodes[node_id] = node
    broken = DirectExecGraph(
        nodes=broken_nodes,
        edges=list(expanded.edges),
        entry_node_id=expanded.entry_node_id,
    )
    assert graph_has_missing_node_refs(broken)
    repaired = repair_lane_expand_graph(
        broken,
        lanes=lanes,
        global_placeholders={"requirement_id": "REQ-001", "workspace": "/tmp/ws"},
        templates_root=templates_root,
    )
    assert not graph_has_missing_node_refs(repaired)
    assert repaired.is_valid()
    for node_id, node in repaired.nodes.items():
        assert node.id == node_id
    assert fork_id in repaired.nodes


def test_infer_lanes_from_expand_outputs():
    lanes = infer_lanes_from_expand_outputs(
        {
            "expand_sr": '{"lanes":[{"id":"sr_001","label":"SR-001","template_id":"tpl_sr_to_ar","placeholders":{"sr_id":"SR-001"}}]}',
        }
    )
    assert len(lanes) == 1
    assert lanes[0]["id"] == "sr_001"


def test_tpl_sr_to_ar_template_valid():
    from app.config.paths import resolve_data_dir
    from app.config.settings import settings

    path = resolve_data_dir(settings.data_dir) / "workflow_templates" / "tpl_sr_to_ar.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    graph = DirectExecGraph.from_dict(data["graph"])
    assert graph is not None
    assert graph.is_valid()
    assert "{sr_id}" in graph.nodes["step_arch_impact"].task


def test_tpl_ar_to_code_template_valid():
    from app.config.paths import resolve_data_dir
    from app.config.settings import settings

    path = resolve_data_dir(settings.data_dir) / "workflow_templates" / "tpl_ar_to_code.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    graph = DirectExecGraph.from_dict(data["graph"])
    assert graph is not None
    assert graph.is_valid()
    assert "{repo_id}" in graph.nodes["step_codegen"].task


def test_repair_lane_expand_graph_preserves_post_merge_parent_nodes(tmp_path):
    from app.graph.graph_expand import (
        expand_lanes_into_graph,
        graph_has_disconnected_nodes,
        repair_lane_expand_graph,
        restore_post_merge_flow,
    )
    from app.config.paths import resolve_data_dir
    from app.config.settings import settings

    e2e_path = resolve_data_dir(settings.data_dir) / "workflow_templates" / "tpl_ir_e2e.json"
    e2e_data = json.loads(e2e_path.read_text(encoding="utf-8"))
    reference = DirectExecGraph.from_dict(e2e_data["graph"])
    assert reference is not None

    templates_root = resolve_data_dir(settings.data_dir) / "workflow_templates"
    graph = DirectExecGraph.from_dict(e2e_data["graph"])
    lanes = [
        {
            "id": "sr_001",
            "label": "SR-001",
            "template_id": "tpl_sr_to_ar",
            "placeholders": {"sr_id": "SR-001", "sr_doc": "requirements/a.md"},
            "skip_nodes": ["gate_ar_confirm"],
        },
        {
            "id": "sr_002",
            "label": "SR-002",
            "template_id": "tpl_sr_to_ar",
            "placeholders": {"sr_id": "SR-002", "sr_doc": "requirements/b.md"},
            "skip_nodes": ["gate_ar_confirm"],
        },
    ]
    expanded, _fork_id = expand_lanes_into_graph(
        graph,
        expand_node_id="expand_sr",
        lanes=lanes,
        templates_root=templates_root,
    )
    assert "gate_ar_confirm" in expanded.nodes
    repaired = repair_lane_expand_graph(
        expanded,
        lanes=lanes,
        global_placeholders={"requirement_id": "REQ-001", "workspace": "/tmp/ws"},
        templates_root=templates_root,
    )
    assert "gate_ar_confirm" in repaired.nodes
    assert not graph_has_disconnected_nodes(repaired)

    broken = DirectExecGraph(
        nodes={nid: node for nid, node in repaired.nodes.items() if nid != "gate_ar_confirm"},
        edges=[e for e in repaired.edges if e.to_id != "gate_ar_confirm" and e.from_id != "gate_ar_confirm"],
        entry_node_id=repaired.entry_node_id,
    )
    assert graph_has_disconnected_nodes(broken)
    restored = restore_post_merge_flow(broken, reference)
    assert "gate_ar_confirm" in restored.nodes
    assert not graph_has_disconnected_nodes(restored)


def test_tpl_ir_e2e_template_valid():
    from app.config.paths import resolve_data_dir
    from app.config.settings import settings

    path = resolve_data_dir(settings.data_dir) / "workflow_templates" / "tpl_ir_e2e.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    graph = DirectExecGraph.from_dict(data["graph"])
    assert graph is not None
    assert graph.is_valid()
    assert "step_arch_impact" not in graph.nodes
    assert "step_sr_decompose" not in graph.nodes
    assert "step_ar_decompose" not in graph.nodes
    assert "step_repo_decompose" not in graph.nodes
    assert "expand_ar" not in graph.nodes
    expand_sr = graph.nodes.get("expand_sr")
    assert expand_sr is not None
    assert expand_sr.executor.expand.planner == "native_llm"
    assert expand_sr.executor.expand.default_lane_template_id == "tpl_sr_to_ar"
    expand_repo = graph.nodes.get("expand_repo")
    assert expand_repo is not None
    assert expand_repo.executor.expand.default_lane_template_id == "tpl_ar_to_code"

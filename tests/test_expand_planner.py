from app.graph.expand_planner import (
    load_template_catalog,
    resolve_catalog_template_ids,
    scan_expand_doc_paths,
    summarize_graph_context,
    uses_native_llm_planner,
)
from app.graph.node_config import GraphNodeExpandConfig, GraphNodeExecutor
from app.graph.plan_graph import DirectExecGraph, END_NODE, EdgeCondition, GraphEdge, GraphNode, START_NODE


def _sample_graph():
    nodes = {
        "gen": GraphNode(id="gen", label="生成", task="gen", executor=GraphNodeExecutor.from_human()),
        "expand": GraphNode(
            id="expand",
            label="扩展",
            task="扩展 SR",
            executor=GraphNodeExecutor.from_expand(
                GraphNodeExpandConfig(
                    planner="native_llm",
                    default_lane_template_id="tpl_sr_to_ar",
                    catalog_templates=("tpl_sr_to_ar",),
                )
            ),
            input_doc_paths=["requirements/{requirement_id}/feature_changes/{*}/{*}.md"],
        ),
    }
    edges = [
        GraphEdge(from_id=START_NODE, to_id="gen", condition=EdgeCondition.ALWAYS),
        GraphEdge(from_id="gen", to_id="expand", condition=EdgeCondition.ALWAYS),
        GraphEdge(from_id="expand", to_id=END_NODE, condition=EdgeCondition.ALWAYS),
    ]
    return DirectExecGraph(nodes=nodes, edges=edges, entry_node_id="gen")


def test_uses_native_llm_planner():
    cfg = GraphNodeExpandConfig(planner="native_llm")
    assert uses_native_llm_planner(cfg) is True
    cfg2 = GraphNodeExpandConfig(planner="source", catalog_templates=("tpl_sr_to_ar",))
    assert uses_native_llm_planner(cfg2) is False
    cfg3 = GraphNodeExpandConfig(planner="", catalog_templates=("tpl_sr_to_ar",))
    assert uses_native_llm_planner(cfg3) is True


def test_resolve_catalog_template_ids():
    cfg = GraphNodeExpandConfig(
        default_lane_template_id="tpl_sr_to_ar",
        catalog_templates=("tpl_ar_to_code",),
    )
    ids = resolve_catalog_template_ids(cfg)
    assert ids[0] == "tpl_sr_to_ar"
    assert "tpl_ar_to_code" in ids


def test_load_template_catalog():
    catalog = load_template_catalog(["tpl_sr_to_ar"])
    assert len(catalog) == 1
    assert catalog[0]["template_id"] == "tpl_sr_to_ar"
    assert "step_arch_impact" in catalog[0]["node_ids"]


def test_summarize_graph_context():
    graph = _sample_graph()
    text = summarize_graph_context(graph, "expand", node_outputs={"gen": "done"})
    assert "expand 节点: expand" in text
    assert "gen" in text


def test_scan_expand_doc_paths_empty_without_workspace():
    paths = scan_expand_doc_paths(workspace_path="", requirement_id="REQ-1", doc_paths=[])
    assert paths == []

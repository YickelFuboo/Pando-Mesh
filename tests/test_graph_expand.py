import pytest
from app.graph.graph_expand import expand_tasks_into_graph, parse_tasks_from_output
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


def test_parse_tasks_from_output():
    tasks = parse_tasks_from_output('{"tasks":[{"id":"a","label":"A","task":"do a"}]}')
    assert len(tasks) == 1
    assert tasks[0]["id"] == "a"


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

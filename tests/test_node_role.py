from app.graph.plan_graph import DirectExecGraph, END_NODE, NodeRole, START_NODE


def test_graph_node_role_roundtrip():
    graph = DirectExecGraph.from_dict({
        "nodes": [
            {
                "id": "step_dev",
                "label": "开发",
                "node_role": "execute",
                "executor": {"kind": "cli", "cli": {"commands": [{"command": "echo", "args": ["ok"]}]}},
            },
            {
                "id": "step_review",
                "label": "代码审查",
                "node_role": "check",
                "executor": {"kind": "human"},
            },
        ],
        "edges": [
            {"from": START_NODE, "to": "step_dev", "condition": "always"},
            {"from": "step_dev", "to": "step_review", "condition": "always"},
            {"from": "step_review", "to": END_NODE, "condition": "always"},
        ],
        "entry": "step_dev",
    })
    assert graph is not None
    assert graph.nodes["step_dev"].node_role == NodeRole.EXECUTE.value
    assert graph.nodes["step_review"].node_role == NodeRole.CHECK.value
    assert graph.nodes["step_review"].is_check() is True
    payload = graph.to_dict()
    by_id = {n["id"]: n for n in payload["nodes"]}
    assert by_id["step_dev"]["node_role"] == "execute"
    assert by_id["step_review"]["node_role"] == "check"


def test_graph_node_role_defaults_to_execute():
    graph = DirectExecGraph.from_dict({
        "nodes": [
            {
                "id": "step_a",
                "label": "步骤",
                "executor": {"kind": "cli", "cli": {"commands": [{"command": "echo", "args": ["ok"]}]}},
            },
        ],
        "edges": [
            {"from": START_NODE, "to": "step_a", "condition": "always"},
            {"from": "step_a", "to": END_NODE, "condition": "always"},
        ],
        "entry": "step_a",
    })
    assert graph is not None
    assert graph.nodes["step_a"].node_role == NodeRole.EXECUTE.value
